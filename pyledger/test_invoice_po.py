#!/usr/bin/env python3
"""
Test script for invoice and purchase order functionality.
"""

import os
import sys
from datetime import date
from pyledger.db import (
    get_connection, init_db, add_invoice, get_invoice, list_invoices, get_invoice_lines,
    add_purchase_order, get_purchase_order, list_purchase_orders, get_purchase_order_lines
)
from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus
from pyledger.purchase_orders import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus

def test_invoice_functionality():
    """Test invoice creation and retrieval."""
    print("Testing Invoice Functionality...")
    
    # Remove existing database
    if os.path.exists('pyledger.db'):
        os.remove('pyledger.db')
    
    conn = get_connection()
    init_db(conn)
    
    # Create test invoice
    invoice_lines = [
        ("Web Development Services", 40, 100.0, 0.1),
        ("Consulting", 10, 150.0, 0.1)
    ]
    
    add_invoice(conn, "INV-001", "Acme Corp", "123 Main St", 
                "2024-01-15", "2024-02-15", "Draft", "Test invoice", invoice_lines)
    
    # Retrieve invoice
    row = get_invoice(conn, "INV-001")
    assert row is not None, "Invoice should be found"
    assert row[0] == "INV-001", "Invoice number should match"
    assert row[1] == "Acme Corp", "Customer name should match"
    # Calculate expected total: (40 * 100) + (10 * 150) = 4000 + 1500 = 5500
    # Tax: 5500 * 0.1 = 550
    # Total: 5500 + 550 = 6050
    assert row[9] == 6050.0, f"Total amount should be 6050.0, got {row[9]}"
    
    # Get invoice lines
    lines = get_invoice_lines(conn, "INV-001")
    assert len(lines) == 2, "Should have 2 invoice lines"
    
    print("✓ Invoice functionality test passed")
    conn.close()

def test_purchase_order_functionality():
    """Test purchase order creation and retrieval."""
    print("Testing Purchase Order Functionality...")
    
    # Remove existing database
    if os.path.exists('pyledger.db'):
        os.remove('pyledger.db')
    
    conn = get_connection()
    init_db(conn)
    
    # Create test purchase order
    po_lines = [
        ("Office Chairs", 5, 200.0, 0.08),
        ("Desks", 3, 300.0, 0.08)
    ]
    
    add_purchase_order(conn, "PO-001", "Office Supplies Co", "456 Business Ave",
                      "2024-01-10", "2024-01-20", "Draft", "Test PO", po_lines)
    
    # Retrieve purchase order
    row = get_purchase_order(conn, "PO-001")
    assert row is not None, "Purchase order should be found"
    assert row[0] == "PO-001", "PO number should match"
    assert row[1] == "Office Supplies Co", "Supplier name should match"
    # Calculate expected total: (5 * 200) + (3 * 300) = 1000 + 900 = 1900
    # Tax: 1900 * 0.08 = 152
    # Total: 1900 + 152 = 2052
    assert row[9] == 2052.0, f"Total amount should be 2052.0, got {row[9]}"
    
    # Get purchase order lines
    lines = get_purchase_order_lines(conn, "PO-001")
    assert len(lines) == 2, "Should have 2 PO lines"
    
    print("✓ Purchase order functionality test passed")
    conn.close()

def test_invoice_classes():
    """Test invoice class functionality."""
    print("Testing Invoice Classes...")
    
    # Create invoice line
    line = InvoiceLine("Test Service", 10, 100.0, 0.1)
    assert line.subtotal == 1000.0, "Subtotal should be 1000.0"
    assert line.tax_amount == 100.0, "Tax amount should be 100.0"
    assert line.total == 1100.0, "Total should be 1100.0"
    
    # Create invoice
    invoice = Invoice(
        "INV-002", "Test Customer", "Test Address",
        date(2024, 1, 15), date(2024, 2, 15),
        [line], InvoiceStatus.DRAFT
    )
    
    assert invoice.subtotal == 1000.0, "Invoice subtotal should be 1000.0"
    assert invoice.total_tax == 100.0, "Invoice tax should be 100.0"
    assert invoice.total_amount == 1100.0, "Invoice total should be 1100.0"
    assert invoice.balance_due == 1100.0, "Balance due should be 1100.0"
    
    # Test payment
    invoice.mark_as_paid(500.0)
    assert invoice.paid_amount == 500.0, "Paid amount should be 500.0"
    assert invoice.balance_due == 600.0, "Balance due should be 600.0"
    
    print("✓ Invoice classes test passed")

def test_purchase_order_classes():
    """Test purchase order class functionality."""
    print("Testing Purchase Order Classes...")
    
    # Create PO line
    line = PurchaseOrderLine("Test Item", 5, 50.0, 0.08)
    assert line.subtotal == 250.0, "Subtotal should be 250.0"
    assert line.tax_amount == 20.0, "Tax amount should be 20.0"
    assert line.total == 270.0, "Total should be 270.0"
    
    # Create purchase order
    po = PurchaseOrder(
        "PO-002", "Test Supplier", "Test Address",
        date(2024, 1, 10), date(2024, 1, 20),
        [line], PurchaseOrderStatus.DRAFT
    )
    
    assert po.subtotal == 250.0, "PO subtotal should be 250.0"
    assert po.total_tax == 20.0, "PO tax should be 20.0"
    assert po.total_amount == 270.0, "PO total should be 270.0"
    
    # Test receipt
    po.receive_items(0, 3)
    assert po.lines[0].received_quantity == 3, "Received quantity should be 3"
    assert po.received_subtotal == 150.0, "Received subtotal should be 150.0"
    
    print("✓ Purchase order classes test passed")

def main():
    """Run all tests."""
    print("Running Invoice and Purchase Order Tests...\n")
    
    try:
        test_invoice_classes()
        test_purchase_order_classes()
        test_invoice_functionality()
        test_purchase_order_functionality()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 