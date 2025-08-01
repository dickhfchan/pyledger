from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from pyledger.accounts import AccountType
from pyledger.db import (
    get_connection, init_db, add_account, list_accounts, add_journal_entry, list_journal_entries, get_journal_lines,
    add_invoice, get_invoice, list_invoices, get_invoice_lines, update_invoice_payment,
    add_purchase_order, get_purchase_order, list_purchase_orders, get_purchase_order_lines, update_purchase_order_receipt
)
from pyledger.reports import balance_sheet, income_statement, cash_flow_report
from pyledger.accounts import ChartOfAccounts
from pyledger.invoices import InvoiceStatus, Invoice, InvoiceLine
from pyledger.purchase_orders import PurchaseOrderStatus
from pyledger.payment_clearing import PaymentClearingManager
from pyledger.gaap_compliance import GAAPCompliance, GAAPPrinciple, RevenueRecognitionMethod

app = FastAPI(title="PyLedger Accounting API")

# --- Pydantic models ---
class AccountIn(BaseModel):
    code: str
    name: str
    type: AccountType

class AccountOut(AccountIn):
    balance: float

class JournalLineIn(BaseModel):
    account_code: str
    amount: float
    is_debit: bool

class JournalEntryIn(BaseModel):
    description: str
    lines: List[JournalLineIn]

class JournalEntryOut(BaseModel):
    id: int
    description: str
    date: str

class JournalLineOut(BaseModel):
    id: int
    account_code: str
    amount: float
    is_debit: bool

# --- Invoice Models ---
class InvoiceLineIn(BaseModel):
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0

class InvoiceIn(BaseModel):
    invoice_number: str
    customer_name: str
    customer_address: str
    issue_date: date
    due_date: date
    lines: List[InvoiceLineIn]
    status: InvoiceStatus = InvoiceStatus.DRAFT
    notes: str = ""

class InvoiceOut(BaseModel):
    invoice_number: str
    customer_name: str
    customer_address: str
    issue_date: date
    due_date: date
    status: str
    notes: str
    subtotal: float
    total_tax: float
    total_amount: float
    paid_amount: float
    balance_due: float
    paid_date: Optional[date] = None

class InvoiceLineOut(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    subtotal: float
    tax_amount: float
    total: float

class InvoicePaymentIn(BaseModel):
    paid_amount: float
    paid_date: Optional[date] = None

# --- Purchase Order Models ---
class PurchaseOrderLineIn(BaseModel):
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0

class PurchaseOrderIn(BaseModel):
    po_number: str
    supplier_name: str
    supplier_address: str
    order_date: date
    expected_delivery_date: date
    lines: List[PurchaseOrderLineIn]
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    notes: str = ""

class PurchaseOrderOut(BaseModel):
    po_number: str
    supplier_name: str
    supplier_address: str
    order_date: date
    expected_delivery_date: date
    status: str
    notes: str
    subtotal: float
    total_tax: float
    total_amount: float
    received_subtotal: float
    received_tax: float
    received_total: float
    received_date: Optional[date] = None

class PurchaseOrderLineOut(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: float
    tax_rate: float
    received_quantity: float
    subtotal: float
    tax_amount: float
    total: float
    received_subtotal: float
    received_tax_amount: float
    received_total: float

class PurchaseOrderReceiptIn(BaseModel):
    line_id: int
    received_quantity: float
    received_date: Optional[date] = None

# --- Payment Clearing Models ---
class PaymentClearingIn(BaseModel):
    invoice_number: str
    payment_amount: float
    payment_date: date
    payment_reference: str
    clearing_method: str = "partial"

class MultiplePaymentClearingIn(BaseModel):
    invoice_numbers: List[str]
    total_payment_amount: float
    payment_date: date
    payment_reference: str
    allocation_method: str = "proportional"

class AgingReportOut(BaseModel):
    report_date: str
    schedule_type: str
    items_processed: int
    aging_summary: dict
    total_amount: float
    total_count: int

class PaymentSummaryOut(BaseModel):
    payment_type: str
    start_date: str
    end_date: str
    total_payments: int
    total_cleared: float
    total_original: float
    avg_payment: float
    methods: dict

class OutstandingInvoiceOut(BaseModel):
    invoice_number: str
    customer_name: str
    issue_date: str
    due_date: str
    total_amount: float
    paid_amount: float
    outstanding_amount: float
    days_overdue: int

class OutstandingPurchaseOrderOut(BaseModel):
    po_number: str
    supplier_name: str
    order_date: str
    expected_delivery_date: str
    total_amount: float
    received_total: float
    outstanding_amount: float
    days_overdue: int

# --- GAAP Compliance Models ---
class RevenueRecognitionIn(BaseModel):
    invoice_number: str
    recognition_method: str
    performance_obligations: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class RevenueRecognitionUpdateIn(BaseModel):
    completion_percentage: float

class ExpenseMatchingIn(BaseModel):
    expense_account: str
    revenue_account: str
    expense_amount: float
    revenue_amount: float
    matching_period: str
    justification: str

class MaterialityAssessmentIn(BaseModel):
    assessment_type: str
    actual_amount: float
    threshold_amount: Optional[float] = None

class ConservatismAdjustmentIn(BaseModel):
    account_code: str
    adjustment_amount: float
    reason: str

class GAAPComplianceReportOut(BaseModel):
    compliance_status: str
    audit_trail_summary: dict
    revenue_recognition_summary: List[tuple]
    materiality_summary: List[tuple]
    last_updated: str

# --- Startup: ensure DB is initialized ---
@app.on_event("startup")
def startup_event():
    conn = get_connection()
    init_db(conn)
    conn.close()

# --- Accounts ---
@app.post("/accounts", response_model=AccountOut)
def api_add_account(account: AccountIn):
    """Add a new account."""
    conn = get_connection()
    add_account(conn, account.code, account.name, account.type)
    # Fetch the account back
    row = [r for r in list_accounts(conn) if r[0] == account.code][0]
    conn.close()
    return AccountOut(code=row[0], name=row[1], type=AccountType[row[2]], balance=row[3])

@app.get("/accounts", response_model=List[AccountOut])
def api_list_accounts():
    """List all accounts."""
    conn = get_connection()
    rows = list_accounts(conn)
    conn.close()
    return [AccountOut(code=r[0], name=r[1], type=AccountType[r[2]], balance=r[3]) for r in rows]

# --- Journal Entries ---
@app.post("/journal_entries", response_model=JournalEntryOut)
def api_add_journal_entry(entry: JournalEntryIn):
    """Add a new journal entry."""
    # Check balance
    total_debits = sum(line.amount for line in entry.lines if line.is_debit)
    total_credits = sum(line.amount for line in entry.lines if not line.is_debit)
    if abs(total_debits - total_credits) > 1e-6:
        raise HTTPException(status_code=400, detail="Entry is not balanced.")
    conn = get_connection()
    lines = [(l.account_code, l.amount, l.is_debit) for l in entry.lines]
    entry_id = add_journal_entry(conn, entry.description, lines)
    # Fetch the entry back
    row = [r for r in list_journal_entries(conn) if r[0] == entry_id][0]
    conn.close()
    return JournalEntryOut(id=row[0], description=row[1], date=row[2])

@app.get("/journal_entries", response_model=List[JournalEntryOut])
def api_list_journal_entries():
    """List all journal entries."""
    conn = get_connection()
    rows = list_journal_entries(conn)
    conn.close()
    return [JournalEntryOut(id=r[0], description=r[1], date=r[2]) for r in rows]

@app.get("/journal_entries/{entry_id}/lines", response_model=List[JournalLineOut])
def api_get_journal_lines(entry_id: int):
    """Get all lines for a journal entry."""
    conn = get_connection()
    rows = get_journal_lines(conn, entry_id)
    conn.close()
    return [JournalLineOut(id=r[0], account_code=r[1], amount=r[2], is_debit=r[3]) for r in rows]

# --- Invoice Endpoints ---
@app.post("/invoices", response_model=InvoiceOut)
def api_add_invoice(invoice: InvoiceIn):
    """Add a new invoice."""
    conn = get_connection()
    lines = [(l.description, l.quantity, l.unit_price, l.tax_rate) for l in invoice.lines]
    add_invoice(conn, invoice.invoice_number, invoice.customer_name, invoice.customer_address,
                invoice.issue_date.isoformat(), invoice.due_date.isoformat(), invoice.status.value,
                invoice.notes, lines)
    
    # Fetch the invoice back
    row = get_invoice(conn, invoice.invoice_number)
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found after creation")
    
    return InvoiceOut(
        invoice_number=row[0], customer_name=row[1], customer_address=row[2],
        issue_date=date.fromisoformat(row[3]), due_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        paid_amount=row[10], balance_due=row[9] - row[10],
        paid_date=date.fromisoformat(row[11]) if row[11] else None
    )

@app.get("/invoices", response_model=List[InvoiceOut])
def api_list_invoices(status: Optional[str] = None):
    """List all invoices, optionally filtered by status."""
    conn = get_connection()
    rows = list_invoices(conn, status)
    conn.close()
    
    return [InvoiceOut(
        invoice_number=row[0], customer_name=row[1], customer_address=row[2],
        issue_date=date.fromisoformat(row[3]), due_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        paid_amount=row[10], balance_due=row[9] - row[10],
        paid_date=date.fromisoformat(row[11]) if row[11] else None
    ) for row in rows]

@app.get("/invoices/{invoice_number}", response_model=InvoiceOut)
def api_get_invoice(invoice_number: str):
    """Get an invoice by number."""
    conn = get_connection()
    row = get_invoice(conn, invoice_number)
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return InvoiceOut(
        invoice_number=row[0], customer_name=row[1], customer_address=row[2],
        issue_date=date.fromisoformat(row[3]), due_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        paid_amount=row[10], balance_due=row[9] - row[10],
        paid_date=date.fromisoformat(row[11]) if row[11] else None
    )

@app.get("/invoices/{invoice_number}/lines", response_model=List[InvoiceLineOut])
def api_get_invoice_lines(invoice_number: str):
    """Get all lines for an invoice."""
    conn = get_connection()
    rows = get_invoice_lines(conn, invoice_number)
    conn.close()
    
    return [InvoiceLineOut(
        id=row[0], description=row[1], quantity=row[2], unit_price=row[3],
        tax_rate=row[4], subtotal=row[5], tax_amount=row[6], total=row[7]
    ) for row in rows]

@app.post("/invoices/{invoice_number}/payment")
def api_record_invoice_payment(invoice_number: str, payment: InvoicePaymentIn):
    """Record a payment for an invoice."""
    conn = get_connection()
    update_invoice_payment(conn, invoice_number, payment.paid_amount,
                          payment.paid_date.isoformat() if payment.paid_date else date.today().isoformat())
    conn.close()
    return {"message": "Payment recorded successfully"}

@app.get("/invoices/{invoice_number}/pdf")
def api_generate_invoice_pdf(invoice_number: str, company_info: Optional[dict] = None):
    """Generate a PDF invoice."""
    conn = get_connection()
    try:
        # Get invoice data
        invoice_data = get_invoice(conn, invoice_number)
        lines_data = get_invoice_lines(conn, invoice_number)
        
        # Create Invoice object
        lines = [InvoiceLine(
            description=line['description'],
            quantity=line['quantity'],
            unit_price=line['unit_price'],
            tax_rate=line['tax_rate']
        ) for line in lines_data]
        
        invoice = Invoice(
            invoice_number=invoice_data['invoice_number'],
            customer_name=invoice_data['customer_name'],
            customer_address=invoice_data['customer_address'],
            issue_date=date.fromisoformat(invoice_data['issue_date']),
            due_date=date.fromisoformat(invoice_data['due_date']),
            lines=lines,
            status=InvoiceStatus(invoice_data['status']),
            notes=invoice_data['notes']
        )
        invoice.paid_amount = invoice_data['paid_amount']
        if invoice_data['paid_date']:
            invoice.paid_date = date.fromisoformat(invoice_data['paid_date'])
        
        # Generate PDF
        pdf_path = invoice.generate_pdf(company_info=company_info)
        
        # Return file path for download
        return {
            "message": f"PDF generated successfully",
            "pdf_path": pdf_path,
            "invoice_number": invoice_number
        }
    finally:
        conn.close()

# --- Purchase Order Endpoints ---
@app.post("/purchase_orders", response_model=PurchaseOrderOut)
def api_add_purchase_order(po: PurchaseOrderIn):
    """Add a new purchase order."""
    conn = get_connection()
    lines = [(l.description, l.quantity, l.unit_price, l.tax_rate) for l in po.lines]
    add_purchase_order(conn, po.po_number, po.supplier_name, po.supplier_address,
                      po.order_date.isoformat(), po.expected_delivery_date.isoformat(),
                      po.status.value, po.notes, lines)
    
    # Fetch the purchase order back
    row = get_purchase_order(conn, po.po_number)
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Purchase order not found after creation")
    
    return PurchaseOrderOut(
        po_number=row[0], supplier_name=row[1], supplier_address=row[2],
        order_date=date.fromisoformat(row[3]), expected_delivery_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        received_subtotal=row[10], received_tax=row[11], received_total=row[12],
        received_date=date.fromisoformat(row[13]) if row[13] else None
    )

@app.get("/purchase_orders", response_model=List[PurchaseOrderOut])
def api_list_purchase_orders(status: Optional[str] = None):
    """List all purchase orders, optionally filtered by status."""
    conn = get_connection()
    rows = list_purchase_orders(conn, status)
    conn.close()
    
    return [PurchaseOrderOut(
        po_number=row[0], supplier_name=row[1], supplier_address=row[2],
        order_date=date.fromisoformat(row[3]), expected_delivery_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        received_subtotal=row[10], received_tax=row[11], received_total=row[12],
        received_date=date.fromisoformat(row[13]) if row[13] else None
    ) for row in rows]

@app.get("/purchase_orders/{po_number}", response_model=PurchaseOrderOut)
def api_get_purchase_order(po_number: str):
    """Get a purchase order by number."""
    conn = get_connection()
    row = get_purchase_order(conn, po_number)
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    return PurchaseOrderOut(
        po_number=row[0], supplier_name=row[1], supplier_address=row[2],
        order_date=date.fromisoformat(row[3]), expected_delivery_date=date.fromisoformat(row[4]),
        status=row[5], notes=row[6], subtotal=row[7], total_tax=row[8], total_amount=row[9],
        received_subtotal=row[10], received_tax=row[11], received_total=row[12],
        received_date=date.fromisoformat(row[13]) if row[13] else None
    )

@app.get("/purchase_orders/{po_number}/lines", response_model=List[PurchaseOrderLineOut])
def api_get_purchase_order_lines(po_number: str):
    """Get all lines for a purchase order."""
    conn = get_connection()
    rows = get_purchase_order_lines(conn, po_number)
    conn.close()
    
    return [PurchaseOrderLineOut(
        id=row[0], description=row[1], quantity=row[2], unit_price=row[3],
        tax_rate=row[4], received_quantity=row[5], subtotal=row[6], tax_amount=row[7],
        total=row[8], received_subtotal=row[9], received_tax_amount=row[10], received_total=row[11]
    ) for row in rows]

@app.post("/purchase_orders/{po_number}/receipt")
def api_record_purchase_order_receipt(po_number: str, receipt: PurchaseOrderReceiptIn):
    """Record receipt of items for a purchase order."""
    conn = get_connection()
    update_purchase_order_receipt(conn, po_number, receipt.line_id, receipt.received_quantity,
                                receipt.received_date.isoformat() if receipt.received_date else date.today().isoformat())
    conn.close()
    return {"message": "Receipt recorded successfully"}

# --- Reports ---
@app.get("/reports/balance_sheet")
def api_balance_sheet():
    """Get the balance sheet report."""
    conn = get_connection()
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    conn.close()
    return balance_sheet(chart)

@app.get("/reports/income_statement")
def api_income_statement():
    """Get the income statement report."""
    conn = get_connection()
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    conn.close()
    return income_statement(chart)

@app.get("/reports/cash_flow")
def api_cash_flow():
    """Get the cash flow report."""
    conn = get_connection()
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    conn.close()
    return cash_flow_report(chart)

# --- Payment Clearing Endpoints ---

@app.post("/payment_clearing/single")
def api_clear_single_invoice_payment(clearing: PaymentClearingIn):
    """Clear payment for a single invoice with advanced tracking."""
    try:
        manager = PaymentClearingManager()
        result = manager.clear_single_invoice_payment(
            invoice_number=clearing.invoice_number,
            payment_amount=clearing.payment_amount,
            payment_date=clearing.payment_date.isoformat(),
            payment_reference=clearing.payment_reference,
            clearing_method=clearing.clearing_method
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment clearing failed: {str(e)}")

@app.post("/payment_clearing/multiple")
def api_clear_multiple_invoices_payment(clearing: MultiplePaymentClearingIn):
    """Clear payment across multiple invoices with intelligent allocation."""
    try:
        manager = PaymentClearingManager()
        result = manager.clear_multiple_invoices_payment(
            invoice_numbers=clearing.invoice_numbers,
            total_payment_amount=clearing.total_payment_amount,
            payment_date=clearing.payment_date.isoformat(),
            payment_reference=clearing.payment_reference,
            allocation_method=clearing.allocation_method
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multiple payment clearing failed: {str(e)}")

@app.get("/payment_clearing/aging_report", response_model=AgingReportOut)
def api_generate_aging_report(schedule_type: str = "receivable", report_date: Optional[str] = None):
    """Generate an aging report for receivables or payables."""
    try:
        manager = PaymentClearingManager()
        result = manager.generate_aging_report(
            report_date=report_date,
            schedule_type=schedule_type
        )
        return AgingReportOut(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aging report generation failed: {str(e)}")

@app.get("/payment_clearing/summary", response_model=PaymentSummaryOut)
def api_get_payment_summary(payment_type: str, start_date: str, end_date: str):
    """Get payment summary for a date range."""
    try:
        manager = PaymentClearingManager()
        result = manager.get_payment_summary(payment_type, start_date, end_date)
        return PaymentSummaryOut(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment summary generation failed: {str(e)}")

@app.get("/payment_clearing/outstanding_invoices", response_model=List[OutstandingInvoiceOut])
def api_get_outstanding_invoices(customer_name: Optional[str] = None):
    """Get list of outstanding invoices."""
    try:
        manager = PaymentClearingManager()
        invoices = manager.get_outstanding_invoices(customer_name)
        return [OutstandingInvoiceOut(**invoice) for invoice in invoices]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get outstanding invoices: {str(e)}")

@app.get("/payment_clearing/outstanding_purchase_orders", response_model=List[OutstandingPurchaseOrderOut])
def api_get_outstanding_purchase_orders(supplier_name: Optional[str] = None):
    """Get list of outstanding purchase orders."""
    try:
        manager = PaymentClearingManager()
        purchase_orders = manager.get_outstanding_purchase_orders(supplier_name)
        return [OutstandingPurchaseOrderOut(**po) for po in purchase_orders]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get outstanding purchase orders: {str(e)}")

@app.get("/payment_clearing/clearings")
def api_get_payment_clearings(payment_type: Optional[str] = None, customer_supplier_name: Optional[str] = None):
    """Get payment clearing records with optional filtering."""
    try:
        conn = get_connection()
        from pyledger.db import get_payment_clearings
        clearings = get_payment_clearings(conn, payment_type, customer_supplier_name)
        conn.close()
        
        return [{
            'id': clearing[0],
            'clearing_date': clearing[1],
            'payment_type': clearing[2],
            'payment_reference': clearing[3],
            'invoice_number': clearing[4],
            'po_number': clearing[5],
            'customer_supplier_name': clearing[6],
            'original_amount': clearing[7],
            'cleared_amount': clearing[8],
            'remaining_amount': clearing[9],
            'clearing_method': clearing[10],
            'notes': clearing[11],
            'created_at': clearing[12]
        } for clearing in clearings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment clearings: {str(e)}")

@app.get("/payment_clearing/aging_schedule")
def api_get_aging_schedule(schedule_type: Optional[str] = None, 
                          customer_supplier_name: Optional[str] = None,
                          aging_period: Optional[str] = None):
    """Get aging schedule records with optional filtering."""
    try:
        conn = get_connection()
        from pyledger.db import get_aging_schedule
        schedule = get_aging_schedule(conn, schedule_type, customer_supplier_name, aging_period)
        conn.close()
        
        return [{
            'id': item[0],
            'schedule_date': item[1],
            'schedule_type': item[2],
            'customer_supplier_name': item[3],
            'invoice_number': item[4],
            'po_number': item[5],
            'original_amount': item[6],
            'current_balance': item[7],
            'days_overdue': item[8],
            'aging_period': item[9],
            'notes': item[10],
            'created_at': item[11]
        } for item in schedule]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get aging schedule: {str(e)}")

# --- GAAP Compliance Endpoints ---

@app.post("/gaap/revenue_recognition")
def api_validate_revenue_recognition(recognition: RevenueRecognitionIn):
    """Validate revenue recognition per ASC 606."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        # Convert string to enum
        method_map = {
            "point_in_time": RevenueRecognitionMethod.POINT_IN_TIME,
            "over_time": RevenueRecognitionMethod.OVER_TIME,
            "percentage_of_completion": RevenueRecognitionMethod.PERCENTAGE_OF_COMPLETION,
            "completed_contract": RevenueRecognitionMethod.COMPLETED_CONTRACT
        }
        
        recognition_method = method_map.get(recognition.recognition_method.lower())
        if not recognition_method:
            raise ValueError(f"Invalid recognition method: {recognition.recognition_method}")
        
        result = gaap.validate_revenue_recognition(
            invoice_number=recognition.invoice_number,
            recognition_method=recognition_method,
            performance_obligations=recognition.performance_obligations,
            start_date=recognition.start_date.isoformat() if recognition.start_date else None,
            end_date=recognition.end_date.isoformat() if recognition.end_date else None
        )
        
        conn.close()
        return {"success": True, "message": "Revenue recognition validated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revenue recognition validation failed: {str(e)}")

@app.put("/gaap/revenue_recognition/{invoice_number}")
def api_update_revenue_recognition(invoice_number: str, update: RevenueRecognitionUpdateIn):
    """Update revenue recognition based on completion percentage."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        result = gaap.update_revenue_recognition(
            invoice_number=invoice_number,
            completion_percentage=update.completion_percentage
        )
        
        conn.close()
        return {"success": True, "message": "Revenue recognition updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Revenue recognition update failed: {str(e)}")

@app.post("/gaap/expense_matching")
def api_validate_expense_matching(matching: ExpenseMatchingIn):
    """Validate expense matching principle."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        result = gaap.validate_expense_matching(
            expense_account=matching.expense_account,
            revenue_account=matching.revenue_account,
            expense_amount=matching.expense_amount,
            revenue_amount=matching.revenue_amount,
            matching_period=matching.matching_period,
            justification=matching.justification
        )
        
        conn.close()
        return {"success": True, "message": "Expense matching validated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Expense matching validation failed: {str(e)}")

@app.post("/gaap/materiality_assessment")
def api_assess_materiality(assessment: MaterialityAssessmentIn):
    """Assess materiality of a transaction or account."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        result = gaap.assess_materiality(
            assessment_type=assessment.assessment_type,
            actual_amount=assessment.actual_amount,
            threshold_amount=assessment.threshold_amount
        )
        
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Materiality assessment failed: {str(e)}")

@app.post("/gaap/conservatism")
def api_apply_conservatism(adjustment: ConservatismAdjustmentIn):
    """Apply conservatism principle (understate assets, overstate liabilities)."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        result = gaap.apply_conservatism(
            account_code=adjustment.account_code,
            adjustment_amount=adjustment.adjustment_amount,
            reason=adjustment.reason
        )
        
        conn.close()
        return {"success": True, "message": "Conservatism principle applied"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conservatism application failed: {str(e)}")

@app.get("/gaap/going_concern")
def api_validate_going_concern():
    """Validate going concern assumption."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        result = gaap.validate_going_concern()
        
        conn.close()
        return {"going_concern_viable": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Going concern validation failed: {str(e)}")

@app.get("/gaap/compliance_report", response_model=GAAPComplianceReportOut)
def api_get_gaap_compliance_report():
    """Generate GAAP compliance report."""
    try:
        conn = get_connection()
        gaap = GAAPCompliance(conn)
        
        report = gaap.get_gaap_compliance_report()
        
        conn.close()
        return GAAPComplianceReportOut(**report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GAAP compliance report generation failed: {str(e)}")

@app.get("/gaap/audit_trail")
def api_get_audit_trail(principle: Optional[str] = None, user_id: Optional[str] = None):
    """Get GAAP audit trail entries."""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        query = "SELECT * FROM gaap_audit_trail WHERE 1=1"
        params = []
        
        if principle:
            query += " AND principle = ?"
            params.append(principle)
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY timestamp DESC"
        
        c.execute(query, params)
        entries = c.fetchall()
        
        conn.close()
        
        return [{
            'id': entry[0],
            'timestamp': entry[1],
            'user_id': entry[2],
            'action': entry[3],
            'table_name': entry[4],
            'record_id': entry[5],
            'old_values': json.loads(entry[6]) if entry[6] else None,
            'new_values': json.loads(entry[7]) if entry[7] else None,
            'principle': entry[8],
            'justification': entry[9]
        } for entry in entries]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit trail: {str(e)}")