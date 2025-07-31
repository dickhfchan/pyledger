from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal

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