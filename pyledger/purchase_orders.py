from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal

class PurchaseOrderStatus(Enum):
    DRAFT = "Draft"
    SENT = "Sent"
    RECEIVED = "Received"
    PARTIALLY_RECEIVED = "Partially Received"
    CANCELLED = "Cancelled"

class PurchaseOrderLine:
    """
    Represents a line item in a purchase order.
    """
    def __init__(self, description: str, quantity: float, unit_price: float, tax_rate: float = 0.0):
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate
        self.received_quantity = 0.0

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

    @property
    def tax_amount(self) -> float:
        return self.subtotal * self.tax_rate

    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount

    @property
    def received_subtotal(self) -> float:
        return self.received_quantity * self.unit_price

    @property
    def received_tax_amount(self) -> float:
        return self.received_subtotal * self.tax_rate

    @property
    def received_total(self) -> float:
        return self.received_subtotal + self.received_tax_amount

    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.received_quantity

    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.quantity

    def receive_quantity(self, quantity: float):
        """Mark quantity as received."""
        if quantity > self.remaining_quantity:
            raise ValueError(f"Cannot receive {quantity}, only {self.remaining_quantity} remaining")
        self.received_quantity += quantity

    def to_dict(self):
        return {
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'tax_rate': self.tax_rate,
            'received_quantity': self.received_quantity,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total': self.total,
            'received_subtotal': self.received_subtotal,
            'received_tax_amount': self.received_tax_amount,
            'received_total': self.received_total,
            'remaining_quantity': self.remaining_quantity
        }

    @staticmethod
    def from_dict(data):
        line = PurchaseOrderLine(
            description=data['description'],
            quantity=data['quantity'],
            unit_price=data['unit_price'],
            tax_rate=data.get('tax_rate', 0.0)
        )
        line.received_quantity = data.get('received_quantity', 0.0)
        return line

class PurchaseOrder:
    """
    Represents a purchase order to suppliers.
    """
    def __init__(self, 
                 po_number: str,
                 supplier_name: str,
                 supplier_address: str,
                 order_date: date,
                 expected_delivery_date: date,
                 lines: List[PurchaseOrderLine],
                 status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT,
                 notes: str = ""):
        self.po_number = po_number
        self.supplier_name = supplier_name
        self.supplier_address = supplier_address
        self.order_date = order_date
        self.expected_delivery_date = expected_delivery_date
        self.lines = lines
        self.status = status
        self.notes = notes
        self.received_date: Optional[date] = None

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
    def received_subtotal(self) -> float:
        return sum(line.received_subtotal for line in self.lines)

    @property
    def received_tax(self) -> float:
        return sum(line.received_tax_amount for line in self.lines)

    @property
    def received_total(self) -> float:
        return self.received_subtotal + self.received_tax

    @property
    def is_fully_received(self) -> bool:
        return all(line.is_fully_received for line in self.lines)

    @property
    def is_partially_received(self) -> bool:
        return any(line.received_quantity > 0 for line in self.lines) and not self.is_fully_received

    def receive_items(self, line_index: int, quantity: float, received_date: Optional[date] = None):
        """Mark items as received for a specific line."""
        if line_index >= len(self.lines):
            raise ValueError(f"Invalid line index {line_index}")
        
        self.lines[line_index].receive_quantity(quantity)
        
        if received_date:
            self.received_date = received_date
        else:
            self.received_date = date.today()

        # Update status
        if self.is_fully_received:
            self.status = PurchaseOrderStatus.RECEIVED
        elif self.is_partially_received:
            self.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

    def to_dict(self):
        return {
            'po_number': self.po_number,
            'supplier_name': self.supplier_name,
            'supplier_address': self.supplier_address,
            'order_date': self.order_date.isoformat(),
            'expected_delivery_date': self.expected_delivery_date.isoformat(),
            'lines': [line.to_dict() for line in self.lines],
            'status': self.status.value,
            'notes': self.notes,
            'subtotal': self.subtotal,
            'total_tax': self.total_tax,
            'total_amount': self.total_amount,
            'received_subtotal': self.received_subtotal,
            'received_tax': self.received_tax,
            'received_total': self.received_total,
            'received_date': self.received_date.isoformat() if self.received_date else None
        }

    @staticmethod
    def from_dict(data):
        lines = [PurchaseOrderLine.from_dict(l) for l in data['lines']]
        po = PurchaseOrder(
            po_number=data['po_number'],
            supplier_name=data['supplier_name'],
            supplier_address=data['supplier_address'],
            order_date=date.fromisoformat(data['order_date']),
            expected_delivery_date=date.fromisoformat(data['expected_delivery_date']),
            lines=lines,
            status=PurchaseOrderStatus(data['status']),
            notes=data.get('notes', '')
        )
        if data.get('received_date'):
            po.received_date = date.fromisoformat(data['received_date'])
        return po

class PurchaseOrderManager:
    """
    Manages a collection of purchase orders.
    """
    def __init__(self):
        self.purchase_orders: Dict[str, PurchaseOrder] = {}

    def add_purchase_order(self, po: PurchaseOrder):
        """Add a purchase order to the manager."""
        if po.po_number in self.purchase_orders:
            raise ValueError(f"Purchase order number {po.po_number} already exists.")
        self.purchase_orders[po.po_number] = po

    def get_purchase_order(self, po_number: str) -> PurchaseOrder:
        """Get a purchase order by number."""
        if po_number not in self.purchase_orders:
            raise ValueError(f"Purchase order {po_number} not found.")
        return self.purchase_orders[po_number]

    def list_purchase_orders(self, status: Optional[PurchaseOrderStatus] = None) -> List[PurchaseOrder]:
        """List all purchase orders, optionally filtered by status."""
        if status:
            return [po for po in self.purchase_orders.values() if po.status == status]
        return list(self.purchase_orders.values())

    def get_pending_receipt_orders(self) -> List[PurchaseOrder]:
        """Get all purchase orders that are not fully received."""
        return [po for po in self.purchase_orders.values() if not po.is_fully_received]

    def to_dict(self):
        return {'purchase_orders': [po.to_dict() for po in self.purchase_orders.values()]}

    @staticmethod
    def from_dict(data):
        manager = PurchaseOrderManager()
        for po_data in data.get('purchase_orders', []):
            po = PurchaseOrder.from_dict(po_data)
            manager.purchase_orders[po.po_number] = po
        return manager 