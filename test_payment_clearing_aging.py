#!/usr/bin/env python3
"""
Advanced Payment Clearing and Aging Test Suite

This test demonstrates the sophisticated payment clearing capabilities of PyLedger:
- Single invoice payment clearing
- Multiple invoice payment clearing with intelligent allocation
- Aging schedule generation
- Payment summaries and reports
- Outstanding invoice and purchase order tracking
"""

import sqlite3
from datetime import datetime, timedelta
from pyledger.db import get_connection, init_db, add_invoice, add_purchase_order
from pyledger.payment_clearing import PaymentClearingManager

def setup_test_data():
    """Set up test data with invoices and purchase orders."""
    conn = get_connection()
    init_db(conn)
    
    # Add test invoices
    invoices = [
        {
            'invoice_number': 'INV-2024-001',
            'customer_name': 'Acme Corp',
            'customer_address': '123 Business St, City, State 12345',
            'issue_date': '2024-01-15',
            'due_date': '2024-02-15',
            'status': 'unpaid',
            'notes': 'Web development services',
            'lines': [('Web Development', 40, 150.0, 0.1)]
        },
        {
            'invoice_number': 'INV-2024-002',
            'customer_name': 'TechStart Inc',
            'customer_address': '456 Innovation Ave, Tech City, TC 67890',
            'issue_date': '2024-01-20',
            'due_date': '2024-02-20',
            'status': 'unpaid',
            'notes': 'Consulting services',
            'lines': [('Consulting', 20, 200.0, 0.1)]
        },
        {
            'invoice_number': 'INV-2024-003',
            'customer_name': 'Acme Corp',
            'customer_address': '123 Business St, City, State 12345',
            'issue_date': '2024-02-01',
            'due_date': '2024-03-01',
            'status': 'unpaid',
            'notes': 'Database optimization',
            'lines': [('Database Optimization', 15, 180.0, 0.1)]
        },
        {
            'invoice_number': 'INV-2024-004',
            'customer_name': 'Global Solutions',
            'customer_address': '789 Enterprise Blvd, Metro City, MC 11111',
            'issue_date': '2024-01-10',
            'due_date': '2024-02-10',
            'status': 'unpaid',
            'notes': 'System integration',
            'lines': [('System Integration', 50, 120.0, 0.1)]
        }
    ]
    
    for invoice in invoices:
        add_invoice(
            conn=conn,
            invoice_number=invoice['invoice_number'],
            customer_name=invoice['customer_name'],
            customer_address=invoice['customer_address'],
            issue_date=invoice['issue_date'],
            due_date=invoice['due_date'],
            status=invoice['status'],
            notes=invoice['notes'],
            lines=invoice['lines']
        )
    
    # Add test purchase orders
    purchase_orders = [
        {
            'po_number': 'PO-2024-001',
            'supplier_name': 'Office Supplies Co',
            'supplier_address': '100 Supply St, Vendor City, VC 22222',
            'order_date': '2024-01-15',
            'expected_delivery_date': '2024-02-15',
            'status': 'received',
            'notes': 'Office supplies',
            'lines': [('Office Chairs', 10, 250.0, 0.08)]
        },
        {
            'po_number': 'PO-2024-002',
            'supplier_name': 'Tech Equipment Ltd',
            'supplier_address': '200 Tech Ave, Equipment City, EC 33333',
            'order_date': '2024-01-20',
            'expected_delivery_date': '2024-02-20',
            'status': 'received',
            'notes': 'Computer equipment',
            'lines': [('Laptops', 5, 1200.0, 0.08)]
        }
    ]
    
    for po in purchase_orders:
        add_purchase_order(
            conn=conn,
            po_number=po['po_number'],
            supplier_name=po['supplier_name'],
            supplier_address=po['supplier_address'],
            order_date=po['order_date'],
            expected_delivery_date=po['expected_delivery_date'],
            status=po['status'],
            notes=po['notes'],
            lines=po['lines']
        )
    
    conn.close()
    print("✅ Test data setup completed")

def test_single_invoice_payment_clearing():
    """Test single invoice payment clearing."""
    print("\n🔍 Testing Single Invoice Payment Clearing")
    
    manager = PaymentClearingManager()
    
    # Clear payment for a single invoice
    result = manager.clear_single_invoice_payment(
        invoice_number='INV-2024-001',
        payment_amount=3000.0,
        payment_date='2024-02-20',
        payment_reference='PAY-001',
        clearing_method='partial'
    )
    
    print(f"✅ Single payment clearing completed:")
    print(f"   Invoice: {result['invoice_number']}")
    print(f"   Payment Amount: ${result['payment_amount']:.2f}")
    print(f"   Payment Date: {result['payment_date']}")
    print(f"   Payment Reference: {result['payment_reference']}")
    print(f"   Original Amount: ${result['original_amount']:.2f}")
    print(f"   Previous Paid: ${result['previous_paid']:.2f}")
    print(f"   New Paid Amount: ${result['new_paid_amount']:.2f}")
    print(f"   Remaining Balance: ${result['remaining_balance']:.2f}")

def test_multiple_invoice_payment_clearing():
    """Test multiple invoice payment clearing with different allocation methods."""
    print("\n🔍 Testing Multiple Invoice Payment Clearing")
    
    manager = PaymentClearingManager()
    
    # Test proportional allocation
    result_proportional = manager.clear_multiple_invoices_payment(
        invoice_numbers=['INV-2024-002', 'INV-2024-003'],
        total_payment_amount=5000.0,
        payment_date='2024-02-25',
        payment_reference='PAY-002',
        allocation_method='proportional'
    )
    
    print(f"✅ Multiple payment clearing (proportional) completed:")
    print(f"   Total Payment Amount: ${result_proportional['total_payment_amount']:.2f}")
    print(f"   Payment Date: {result_proportional['payment_date']}")
    print(f"   Payment Reference: {result_proportional['payment_reference']}")
    print(f"   Allocation Method: {result_proportional['allocation_method']}")
    print(f"   Invoices Cleared: {result_proportional['invoices_cleared']}")
    
    print("\n   Allocations:")
    for allocation in result_proportional['allocations']:
        print(f"     Invoice {allocation['invoice_number']}: ${allocation['amount']:.2f}")
    
    # Test oldest first allocation
    result_oldest = manager.clear_multiple_invoices_payment(
        invoice_numbers=['INV-2024-004', 'INV-2024-002'],
        total_payment_amount=3000.0,
        payment_date='2024-02-28',
        payment_reference='PAY-003',
        allocation_method='oldest_first'
    )
    
    print(f"\n✅ Multiple payment clearing (oldest first) completed:")
    print(f"   Total Payment Amount: ${result_oldest['total_payment_amount']:.2f}")
    print(f"   Allocation Method: {result_oldest['allocation_method']}")
    print(f"   Invoices Cleared: {result_oldest['invoices_cleared']}")

def test_aging_report_generation():
    """Test aging report generation."""
    print("\n🔍 Testing Aging Report Generation")
    
    manager = PaymentClearingManager()
    
    # Generate aging report for receivables
    aging_report = manager.generate_aging_report(
        report_date='2024-03-01',
        schedule_type='receivable'
    )
    
    print(f"✅ Aging report generated:")
    print(f"   Report Date: {aging_report['report_date']}")
    print(f"   Schedule Type: {aging_report['schedule_type']}")
    print(f"   Items Processed: {aging_report['items_processed']}")
    print(f"   Total Amount: ${aging_report['total_amount']:.2f}")
    print(f"   Total Count: {aging_report['total_count']}")
    
    print("\n   Aging Summary:")
    for period, data in aging_report['aging_summary'].items():
        if data['count'] > 0:
            print(f"     {period.replace('_', ' ').title()}: {data['count']} items, ${data['amount']:.2f}")

def test_payment_summary():
    """Test payment summary generation."""
    print("\n🔍 Testing Payment Summary")
    
    manager = PaymentClearingManager()
    
    # Get payment summary for receivables
    summary = manager.get_payment_summary(
        payment_type='receivable',
        start_date='2024-02-01',
        end_date='2024-03-01'
    )
    
    print(f"✅ Payment summary generated:")
    print(f"   Payment Type: {summary['payment_type']}")
    print(f"   Start Date: {summary['start_date']}")
    print(f"   End Date: {summary['end_date']}")
    print(f"   Total Payments: {summary['total_payments']}")
    print(f"   Total Cleared: ${summary['total_cleared']:.2f}")
    print(f"   Total Original: ${summary['total_original']:.2f}")
    print(f"   Average Payment: ${summary['avg_payment']:.2f}")
    
    print("\n   Payment Methods:")
    for method, data in summary['methods'].items():
        print(f"     {method}: {data['count']} payments, ${data['amount']:.2f}")

def test_outstanding_items():
    """Test outstanding invoices and purchase orders."""
    print("\n🔍 Testing Outstanding Items")
    
    manager = PaymentClearingManager()
    
    # Get outstanding invoices
    outstanding_invoices = manager.get_outstanding_invoices()
    
    print(f"✅ Outstanding invoices found: {len(outstanding_invoices)}")
    for invoice in outstanding_invoices:
        print(f"   Invoice {invoice['invoice_number']}: ${invoice['outstanding_amount']:.2f} "
              f"({invoice['days_overdue']} days overdue)")
    
    # Get outstanding purchase orders
    outstanding_pos = manager.get_outstanding_purchase_orders()
    
    print(f"\n✅ Outstanding purchase orders found: {len(outstanding_pos)}")
    for po in outstanding_pos:
        print(f"   PO {po['po_number']}: ${po['outstanding_amount']:.2f} "
              f"({po['days_overdue']} days overdue)")

def test_customer_specific_outstanding():
    """Test customer-specific outstanding invoices."""
    print("\n🔍 Testing Customer-Specific Outstanding Invoices")
    
    manager = PaymentClearingManager()
    
    # Get outstanding invoices for Acme Corp
    acme_invoices = manager.get_outstanding_invoices('Acme Corp')
    
    print(f"✅ Outstanding invoices for Acme Corp: {len(acme_invoices)}")
    total_outstanding = sum(inv['outstanding_amount'] for inv in acme_invoices)
    print(f"   Total outstanding: ${total_outstanding:.2f}")
    
    for invoice in acme_invoices:
        print(f"     Invoice {invoice['invoice_number']}: ${invoice['outstanding_amount']:.2f} "
              f"({invoice['days_overdue']} days overdue)")

def main():
    """Run all payment clearing tests."""
    print("🚀 Advanced Payment Clearing Test Suite")
    print("=" * 50)
    
    # Setup test data
    setup_test_data()
    
    # Run tests
    test_single_invoice_payment_clearing()
    test_multiple_invoice_payment_clearing()
    test_aging_report_generation()
    test_payment_summary()
    test_outstanding_items()
    test_customer_specific_outstanding()
    
    print("\n" + "=" * 50)
    print("✅ All payment clearing tests completed successfully!")
    print("\n🎯 Advanced Payment Clearing Features Demonstrated:")
    print("   • Single invoice payment clearing with tracking")
    print("   • Multiple invoice payment clearing with intelligent allocation")
    print("   • Proportional, oldest-first, and largest-first allocation methods")
    print("   • Aging schedule generation and reporting")
    print("   • Payment summaries with method breakdowns")
    print("   • Outstanding invoice and purchase order tracking")
    print("   • Customer-specific outstanding invoice queries")
    print("   • Comprehensive payment clearing audit trail")

if __name__ == "__main__":
    main() 