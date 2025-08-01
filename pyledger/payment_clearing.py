"""
Advanced Payment Clearing Module for PyLedger

This module provides sophisticated payment clearing capabilities including:
- Partial and full payment clearing
- Multiple invoice clearing with single payment
- Aging schedule generation
- Payment summaries and reports
- Advanced payment tracking
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pyledger.db import get_connection, add_payment_clearing, get_payment_clearings
from pyledger.db import clear_invoice_payment, clear_purchase_order_payment
from pyledger.db import add_aging_schedule, get_aging_schedule, generate_aging_report
from pyledger.db import get_payment_summary, list_invoices, list_purchase_orders

class PaymentClearingManager:
    """
    Advanced payment clearing manager for PyLedger.
    """
    
    def __init__(self, db_file: str = 'pyledger.db'):
        self.db_file = db_file
    
    def clear_single_invoice_payment(self, invoice_number: str, payment_amount: float,
                                   payment_date: str, payment_reference: str,
                                   clearing_method: str = 'partial') -> Dict:
        """
        Clear payment for a single invoice with advanced tracking.
        
        Args:
            invoice_number: Invoice number to clear
            payment_amount: Amount being paid
            payment_date: Date of payment
            payment_reference: Payment reference number
            clearing_method: 'full', 'partial', or 'multiple'
        
        Returns:
            Dictionary with clearing details
        """
        conn = get_connection(self.db_file)
        
        try:
            # Get invoice details before clearing
            invoices = list_invoices(conn, status='unpaid')
            invoice = None
            for inv in invoices:
                if inv[0] == invoice_number:
                    invoice = inv
                    break
            
            if not invoice:
                raise ValueError(f"Invoice {invoice_number} not found or already paid")
            
            # Clear the payment
            clear_invoice_payment(
                conn=conn,
                invoice_number=invoice_number,
                payment_amount=payment_amount,
                payment_date=payment_date,
                payment_reference=payment_reference,
                clearing_method=clearing_method
            )
            
            # Get updated invoice details
            updated_invoices = list_invoices(conn, status='unpaid')
            updated_invoice = None
            for inv in updated_invoices:
                if inv[0] == invoice_number:
                    updated_invoice = inv
                    break
            
            return {
                'success': True,
                'invoice_number': invoice_number,
                'payment_amount': payment_amount,
                'payment_date': payment_date,
                'payment_reference': payment_reference,
                'clearing_method': clearing_method,
                'original_amount': invoice[8],  # total_amount
                'previous_paid': invoice[10],   # paid_amount
                'new_paid_amount': updated_invoice[10] if updated_invoice else invoice[10] + payment_amount,
                'remaining_balance': updated_invoice[8] - updated_invoice[10] if updated_invoice else 0
            }
            
        finally:
            conn.close()
    
    def clear_multiple_invoices_payment(self, invoice_numbers: List[str], total_payment_amount: float,
                                      payment_date: str, payment_reference: str,
                                      allocation_method: str = 'proportional') -> Dict:
        """
        Clear payment across multiple invoices with intelligent allocation.
        
        Args:
            invoice_numbers: List of invoice numbers to clear
            total_payment_amount: Total payment amount to allocate
            payment_date: Date of payment
            payment_reference: Payment reference number
            allocation_method: 'proportional', 'oldest_first', or 'largest_first'
        
        Returns:
            Dictionary with clearing details for each invoice
        """
        conn = get_connection(self.db_file)
        
        try:
            # Get all invoices and their outstanding amounts
            invoices = []
            total_outstanding = 0
            
            for inv_num in invoice_numbers:
                inv_list = list_invoices(conn, status='unpaid')
                for inv in inv_list:
                    if inv[0] == inv_num:
                        outstanding = inv[8] - inv[10]  # total_amount - paid_amount
                        invoices.append({
                            'invoice_number': inv_num,
                            'outstanding': outstanding,
                            'total_amount': inv[8],
                            'paid_amount': inv[10],
                            'issue_date': inv[3]
                        })
                        total_outstanding += outstanding
                        break
            
            if not invoices:
                raise ValueError("No valid invoices found for clearing")
            
            # Allocate payment based on method
            allocations = self._allocate_payment(invoices, total_payment_amount, allocation_method)
            
            # Clear payments for each invoice
            results = []
            for allocation in allocations:
                if allocation['amount'] > 0:
                    result = self.clear_single_invoice_payment(
                        invoice_number=allocation['invoice_number'],
                        payment_amount=allocation['amount'],
                        payment_date=payment_date,
                        payment_reference=f"{payment_reference}-{allocation['invoice_number']}",
                        clearing_method='multiple'
                    )
                    results.append(result)
            
            return {
                'success': True,
                'total_payment_amount': total_payment_amount,
                'payment_date': payment_date,
                'payment_reference': payment_reference,
                'allocation_method': allocation_method,
                'invoices_cleared': len(results),
                'allocations': allocations,
                'results': results
            }
            
        finally:
            conn.close()
    
    def _allocate_payment(self, invoices: List[Dict], total_amount: float, method: str) -> List[Dict]:
        """
        Allocate payment amount across multiple invoices.
        """
        if method == 'proportional':
            return self._allocate_proportional(invoices, total_amount)
        elif method == 'oldest_first':
            return self._allocate_oldest_first(invoices, total_amount)
        elif method == 'largest_first':
            return self._allocate_largest_first(invoices, total_amount)
        else:
            raise ValueError(f"Unknown allocation method: {method}")
    
    def _allocate_proportional(self, invoices: List[Dict], total_amount: float) -> List[Dict]:
        """
        Allocate payment proportionally based on outstanding amounts.
        """
        total_outstanding = sum(inv['outstanding'] for inv in invoices)
        allocations = []
        
        for invoice in invoices:
            if total_outstanding > 0:
                proportion = invoice['outstanding'] / total_outstanding
                allocated_amount = min(total_amount * proportion, invoice['outstanding'])
            else:
                allocated_amount = 0
            
            allocations.append({
                'invoice_number': invoice['invoice_number'],
                'amount': allocated_amount,
                'proportion': proportion if total_outstanding > 0 else 0
            })
        
        return allocations
    
    def _allocate_oldest_first(self, invoices: List[Dict], total_amount: float) -> List[Dict]:
        """
        Allocate payment to oldest invoices first.
        """
        sorted_invoices = sorted(invoices, key=lambda x: x['issue_date'])
        allocations = []
        remaining_amount = total_amount
        
        for invoice in sorted_invoices:
            if remaining_amount <= 0:
                allocations.append({
                    'invoice_number': invoice['invoice_number'],
                    'amount': 0
                })
            else:
                allocated_amount = min(remaining_amount, invoice['outstanding'])
                allocations.append({
                    'invoice_number': invoice['invoice_number'],
                    'amount': allocated_amount
                })
                remaining_amount -= allocated_amount
        
        return allocations
    
    def _allocate_largest_first(self, invoices: List[Dict], total_amount: float) -> List[Dict]:
        """
        Allocate payment to largest outstanding invoices first.
        """
        sorted_invoices = sorted(invoices, key=lambda x: x['outstanding'], reverse=True)
        allocations = []
        remaining_amount = total_amount
        
        for invoice in sorted_invoices:
            if remaining_amount <= 0:
                allocations.append({
                    'invoice_number': invoice['invoice_number'],
                    'amount': 0
                })
            else:
                allocated_amount = min(remaining_amount, invoice['outstanding'])
                allocations.append({
                    'invoice_number': invoice['invoice_number'],
                    'amount': allocated_amount
                })
                remaining_amount -= allocated_amount
        
        return allocations
    
    def generate_aging_report(self, report_date: str = None, schedule_type: str = 'receivable') -> Dict:
        """
        Generate an aging report for receivables or payables.
        
        Args:
            report_date: Date for the aging report (defaults to today)
            schedule_type: 'receivable' or 'payable'
        
        Returns:
            Dictionary with aging report data
        """
        if report_date is None:
            report_date = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_connection(self.db_file)
        
        try:
            # Generate aging schedule
            items_processed = generate_aging_report(conn, report_date, schedule_type)
            
            # Get aging data
            aging_data = get_aging_schedule(conn, schedule_type=schedule_type)
            
            # Group by aging period
            aging_summary = {
                'current': {'count': 0, 'amount': 0},
                '30_days': {'count': 0, 'amount': 0},
                '60_days': {'count': 0, 'amount': 0},
                '90_days': {'count': 0, 'amount': 0},
                'over_90_days': {'count': 0, 'amount': 0}
            }
            
            for item in aging_data:
                period = item[9]  # aging_period
                amount = item[7]   # current_balance
                
                if period in aging_summary:
                    aging_summary[period]['count'] += 1
                    aging_summary[period]['amount'] += amount
            
            total_amount = sum(period['amount'] for period in aging_summary.values())
            total_count = sum(period['count'] for period in aging_summary.values())
            
            return {
                'report_date': report_date,
                'schedule_type': schedule_type,
                'items_processed': items_processed,
                'aging_summary': aging_summary,
                'total_amount': total_amount,
                'total_count': total_count,
                'detailed_data': aging_data
            }
            
        finally:
            conn.close()
    
    def get_payment_summary(self, payment_type: str, start_date: str, end_date: str) -> Dict:
        """
        Get payment summary for a date range.
        
        Args:
            payment_type: 'receivable' or 'payable'
            start_date: Start date for summary
            end_date: End date for summary
        
        Returns:
            Dictionary with payment summary
        """
        conn = get_connection(self.db_file)
        
        try:
            return get_payment_summary(conn, payment_type, start_date, end_date)
        finally:
            conn.close()
    
    def get_outstanding_invoices(self, customer_name: str = None) -> List[Dict]:
        """
        Get list of outstanding invoices.
        
        Args:
            customer_name: Optional customer name filter
        
        Returns:
            List of outstanding invoice dictionaries
        """
        conn = get_connection(self.db_file)
        
        try:
            invoices = list_invoices(conn, status='unpaid')
            outstanding = []
            
            for invoice in invoices:
                if customer_name is None or invoice[1] == customer_name:
                    outstanding_amount = invoice[8] - invoice[10]  # total_amount - paid_amount
                    if outstanding_amount > 0:
                        outstanding.append({
                            'invoice_number': invoice[0],
                            'customer_name': invoice[1],
                            'issue_date': invoice[3],
                            'due_date': invoice[4],
                            'total_amount': invoice[8],
                            'paid_amount': invoice[10],
                            'outstanding_amount': outstanding_amount,
                            'days_overdue': (datetime.now() - datetime.strptime(invoice[4], '%Y-%m-%d')).days
                        })
            
            return sorted(outstanding, key=lambda x: x['days_overdue'], reverse=True)
            
        finally:
            conn.close()
    
    def get_outstanding_purchase_orders(self, supplier_name: str = None) -> List[Dict]:
        """
        Get list of outstanding purchase orders.
        
        Args:
            supplier_name: Optional supplier name filter
        
        Returns:
            List of outstanding purchase order dictionaries
        """
        conn = get_connection(self.db_file)
        
        try:
            purchase_orders = list_purchase_orders(conn, status='received')
            outstanding = []
            
            for po in purchase_orders:
                if supplier_name is None or po[1] == supplier_name:
                    outstanding_amount = po[8] - po[11]  # total_amount - received_total
                    if outstanding_amount > 0:
                        outstanding.append({
                            'po_number': po[0],
                            'supplier_name': po[1],
                            'order_date': po[3],
                            'expected_delivery_date': po[4],
                            'total_amount': po[8],
                            'received_total': po[11],
                            'outstanding_amount': outstanding_amount,
                            'days_overdue': (datetime.now() - datetime.strptime(po[4], '%Y-%m-%d')).days
                        })
            
            return sorted(outstanding, key=lambda x: x['days_overdue'], reverse=True)
            
        finally:
            conn.close() 