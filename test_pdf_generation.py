#!/usr/bin/env python3
"""
Test script for PDF invoice generation functionality.
"""

from datetime import date
from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus

def test_pdf_generation():
    """Test PDF invoice generation."""
    print("Testing PDF invoice generation...")
    
    # Create a sample invoice
    lines = [
        InvoiceLine("Web Development Services", 40, 100.0, 0.1),
        InvoiceLine("Consulting", 10, 150.0, 0.1),
        InvoiceLine("Domain Registration", 1, 50.0, 0.0)
    ]
    
    invoice = Invoice(
        invoice_number="INV-2024-001",
        customer_name="Acme Corporation",
        customer_address="123 Business Ave\nSuite 100\nNew York, NY 10001",
        issue_date=date(2024, 1, 15),
        due_date=date(2024, 2, 15),
        lines=lines,
        status=InvoiceStatus.SENT,
        notes="Payment is due within 30 days. Late payments may incur additional fees."
    )
    
    # Custom company info
    company_info = {
        'name': 'Tech Solutions Inc.',
        'address': '456 Innovation Drive\nSan Francisco, CA 94105',
        'phone': '+1 (415) 555-0123',
        'email': 'billing@techsolutions.com',
        'website': 'www.techsolutions.com'
    }
    
    # Generate PDF
    pdf_path = invoice.generate_pdf(company_info=company_info)
    print(f"✅ PDF generated successfully: {pdf_path}")
    
    # Test with payment information
    invoice.mark_as_paid(2000.0, date(2024, 1, 20))
    pdf_path_with_payment = invoice.generate_pdf("invoice_with_payment.pdf", company_info)
    print(f"✅ PDF with payment info generated: {pdf_path_with_payment}")
    
    print("PDF generation test completed successfully!")

if __name__ == "__main__":
    test_pdf_generation() 