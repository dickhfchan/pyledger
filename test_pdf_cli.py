#!/usr/bin/env python3
"""
Test script for PDF invoice generation CLI functionality.
"""

from datetime import date
from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus
from pyledger.db import get_connection, add_invoice, get_invoice, get_invoice_lines

def test_pdf_generation_cli():
    """Test PDF invoice generation via CLI functionality."""
    print("Testing PDF invoice generation CLI...")
    
    # Create a test invoice in the database
    conn = get_connection()
    
    # Add test invoice
    lines = [
        ("Web Development Services", 40, 100.0, 0.1),
        ("Consulting", 10, 150.0, 0.1),
        ("Domain Registration", 1, 50.0, 0.0)
    ]
    
    add_invoice(conn, "TEST-INV-003", "Test Customer", "123 Test St\nTest City, TC 12345",
                "2024-01-15", "2024-02-15", "Draft", "Test invoice for PDF generation", lines)
    
    print("✅ Test invoice created in database")
    
    # Test PDF generation
    from pyledger.main import db_generate_invoice_pdf_cmd
    
    # Mock input for testing
    import builtins
    original_input = builtins.input
    
    def mock_input(prompt):
        if "Invoice number" in prompt:
            return "TEST-INV-003"
        elif "Company name" in prompt:
            return "Test Company"
        elif "Company address" in prompt:
            return "456 Test Ave\nTest City, TC 12345"
        elif "Company phone" in prompt:
            return "+1 (555) 999-8888"
        elif "Company email" in prompt:
            return "test@testcompany.com"
        elif "Company website" in prompt:
            return "www.testcompany.com"
        else:
            return ""
    
    try:
        builtins.input = mock_input
        db_generate_invoice_pdf_cmd()
        print("✅ PDF generation CLI test completed successfully!")
    finally:
        builtins.input = original_input
        conn.close()

if __name__ == "__main__":
    test_pdf_generation_cli() 