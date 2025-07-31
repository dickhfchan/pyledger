from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

class InvoiceStatus(Enum):
    DRAFT = "Draft"
    SENT = "Sent"
    PAID = "Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"

class InvoiceLine:
    """
    Represents a line item in an invoice.
    """
    def __init__(self, description: str, quantity: float, unit_price: float, tax_rate: float = 0.0):
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

    @property
    def tax_amount(self) -> float:
        return self.subtotal * self.tax_rate

    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount

    def to_dict(self):
        return {
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'tax_rate': self.tax_rate,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total': self.total
        }

    @staticmethod
    def from_dict(data):
        return InvoiceLine(
            description=data['description'],
            quantity=data['quantity'],
            unit_price=data['unit_price'],
            tax_rate=data.get('tax_rate', 0.0)
        )

class Invoice:
    """
    Represents a customer invoice.
    """
    def __init__(self, 
                 invoice_number: str,
                 customer_name: str,
                 customer_address: str,
                 issue_date: date,
                 due_date: date,
                 lines: List[InvoiceLine],
                 status: InvoiceStatus = InvoiceStatus.DRAFT,
                 notes: str = ""):
        self.invoice_number = invoice_number
        self.customer_name = customer_name
        self.customer_address = customer_address
        self.issue_date = issue_date
        self.due_date = due_date
        self.lines = lines
        self.status = status
        self.notes = notes
        self.paid_amount = 0.0
        self.paid_date: Optional[date] = None

    @property
    def subtotal(self) -> float:
        return sum(line.subtotal for line in self.lines)

    @property
    def total_tax(self) -> float:
        return sum(line.tax_amount for line in self.lines)

    @property
    def total_amount(self) -> float:
        return self.subtotal + self.total_tax

    @property
    def balance_due(self) -> float:
        return self.total_amount - self.paid_amount

    @property
    def is_paid(self) -> bool:
        return self.balance_due <= 0

    @property
    def is_overdue(self) -> bool:
        return not self.is_paid and self.due_date < date.today()

    def mark_as_paid(self, amount: float, paid_date: Optional[date] = None):
        """Mark invoice as paid with specified amount."""
        self.paid_amount += amount
        if paid_date:
            self.paid_date = paid_date
        else:
            self.paid_date = date.today()
        
        if self.is_paid:
            self.status = InvoiceStatus.PAID
        elif self.is_overdue:
            self.status = InvoiceStatus.OVERDUE

    def to_dict(self):
        return {
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_address': self.customer_address,
            'issue_date': self.issue_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'lines': [line.to_dict() for line in self.lines],
            'status': self.status.value,
            'notes': self.notes,
            'subtotal': self.subtotal,
            'total_tax': self.total_tax,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'balance_due': self.balance_due,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None
        }

    def generate_pdf(self, output_path: str = None, company_info: Dict[str, str] = None) -> str:
        """
        Generate a PDF invoice in A4 format with professional layout.
        
        Args:
            output_path: Path to save the PDF file. If None, uses invoice number.
            company_info: Dictionary with company details (name, address, phone, email, website)
        
        Returns:
            Path to the generated PDF file
        """
        if output_path is None:
            output_path = f"invoice_{self.invoice_number}.pdf"
        
        # Default company info if not provided
        if company_info is None:
            company_info = {
                'name': 'Your Company Name',
                'address': '123 Business Street\nCity, State 12345',
                'phone': '+1 (555) 123-4567',
                'email': 'info@yourcompany.com',
                'website': 'www.yourcompany.com'
            }
        
        # Create the PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Professional styles
        company_name_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Heading1'],
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=5,
            alignment=TA_RIGHT
        )
        
        invoice_title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=TA_RIGHT
        )
        
        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=15
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=3
        )
        
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Helvetica',
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=2
        )
        
        # Header section with two-column layout
        header_data = [
            [
                # Left column - Logo placeholder and company info
                Paragraph(f"<b>{company_info['name']}</b><br/>{company_info['address']}<br/>Phone: {company_info['phone']}<br/>Email: {company_info['email']}<br/>Website: {company_info['website']}", normal_style),
                # Right column - Invoice title and details
                Paragraph(f"<b>INVOICE</b><br/><br/>Invoice Number: {self.invoice_number}<br/>Issue Date: {self.issue_date.strftime('%B %d, %Y')}<br/>Due Date: {self.due_date.strftime('%B %d, %Y')}<br/>Status: {self.status.value}", normal_style)
            ]
        ]
        
        header_table = Table(header_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))
        
        # Billing information section
        story.append(Paragraph("BILL TO", section_heading_style))
        story.append(Paragraph(f"<b>{self.customer_name}</b>", normal_style))
        story.append(Paragraph(self.customer_address, normal_style))
        story.append(Spacer(1, 20))
        
        # Line items table with professional styling
        if self.lines:
            # Table headers
            headers = ['Items', 'Quantity', 'Price', 'Amount']
            table_data = [headers]
            
            # Add line items
            for line in self.lines:
                table_data.append([
                    line.description,
                    f"{line.quantity:.0f}" if line.quantity.is_integer() else f"{line.quantity:.2f}",
                    f"${line.unit_price:.2f}",
                    f"${line.total:.2f}"
                ])
            
            # Add summary section
            table_data.append(['', '', '', ''])
            table_data.append(['', '', 'Total:', f"${self.total_amount:.2f}"])
            
            # Add payment information if applicable
            if self.paid_amount > 0:
                payment_date_str = self.paid_date.strftime('%B %d, %Y') if self.paid_date else 'N/A'
                table_data.append(['', '', f'Payment on {payment_date_str}:', f"${self.paid_amount:.2f}"])
                table_data.append(['', '', 'Amount Due:', f"${self.balance_due:.2f}"])
            
            # Create table with professional styling
            col_widths = [doc.width * 0.5, doc.width * 0.15, doc.width * 0.15, doc.width * 0.2]
            
            line_items_table = Table(table_data, colWidths=col_widths)
            line_items_table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Content styling
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Items column left-aligned
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Quantity center-aligned
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Price right-aligned
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Amount right-aligned
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Summary section styling
                ('FONTNAME', (0, -4), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -4), (-1, -1), colors.HexColor('#ecf0f1')),
                
                # Grid styling
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#34495e')),
                ('LINEBELOW', (0, -5), (-1, -5), 1, colors.HexColor('#34495e')),
            ]))
            story.append(line_items_table)
        
        story.append(Spacer(1, 20))
        
        # Notes section
        if self.notes:
            story.append(Paragraph("Notes / Terms", section_heading_style))
            story.append(Paragraph(self.notes, normal_style))
            story.append(Spacer(1, 15))
        
        # Payment instructions (if applicable)
        if self.paid_amount == 0:
            story.append(Paragraph("Payment Instructions", section_heading_style))
            payment_instructions = f"""
            Please make payment to:<br/>
            <b>{company_info['name']}</b><br/>
            Bank: Your Bank Name<br/>
            Account: 123-456-789<br/>
            Reference: {self.invoice_number}
            """
            story.append(Paragraph(payment_instructions, normal_style))
        
        # Professional footer
        footer_text = f"Thank you for your business! | Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        story.append(Spacer(1, 30))
        story.append(Paragraph(footer_text, small_style))
        
        # Build PDF
        doc.build(story)
        return output_path

    @staticmethod
    def from_dict(data):
        lines = [InvoiceLine.from_dict(l) for l in data['lines']]
        invoice = Invoice(
            invoice_number=data['invoice_number'],
            customer_name=data['customer_name'],
            customer_address=data['customer_address'],
            issue_date=date.fromisoformat(data['issue_date']),
            due_date=date.fromisoformat(data['due_date']),
            lines=lines,
            status=InvoiceStatus(data['status']),
            notes=data.get('notes', '')
        )
        invoice.paid_amount = data.get('paid_amount', 0.0)
        if data.get('paid_date'):
            invoice.paid_date = date.fromisoformat(data['paid_date'])
        return invoice

class InvoiceManager:
    """
    Manages a collection of invoices.
    """
    def __init__(self):
        self.invoices: Dict[str, Invoice] = {}

    def add_invoice(self, invoice: Invoice):
        """Add an invoice to the manager."""
        if invoice.invoice_number in self.invoices:
            raise ValueError(f"Invoice number {invoice.invoice_number} already exists.")
        self.invoices[invoice.invoice_number] = invoice

    def get_invoice(self, invoice_number: str) -> Invoice:
        """Get an invoice by number."""
        if invoice_number not in self.invoices:
            raise ValueError(f"Invoice {invoice_number} not found.")
        return self.invoices[invoice_number]

    def list_invoices(self, status: Optional[InvoiceStatus] = None) -> List[Invoice]:
        """List all invoices, optionally filtered by status."""
        if status:
            return [inv for inv in self.invoices.values() if inv.status == status]
        return list(self.invoices.values())

    def get_overdue_invoices(self) -> List[Invoice]:
        """Get all overdue invoices."""
        return [inv for inv in self.invoices.values() if inv.is_overdue]

    def get_unpaid_invoices(self) -> List[Invoice]:
        """Get all unpaid invoices."""
        return [inv for inv in self.invoices.values() if not inv.is_paid]

    def to_dict(self):
        return {'invoices': [inv.to_dict() for inv in self.invoices.values()]}

    @staticmethod
    def from_dict(data):
        manager = InvoiceManager()
        for inv_data in data.get('invoices', []):
            invoice = Invoice.from_dict(inv_data)
            manager.invoices[invoice.invoice_number] = invoice
        return manager 