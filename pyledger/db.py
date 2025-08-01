import sqlite3
from typing import List, Optional, Tuple
from pyledger.accounts import AccountType
from pyledger.gaap_compliance import GAAPCompliance, GAAPPrinciple

DB_FILE = 'pyledger.db'

def get_connection(db_file: str = DB_FILE):
    return sqlite3.connect(db_file)

def init_db(conn: sqlite3.Connection):
    """
    Create tables for accounts, journal_entries, journal_lines, invoices, purchase_orders,
    payment_clearings, aging schedules, and GAAP compliance.
    """
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS journal_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            account_code TEXT NOT NULL,
            amount REAL NOT NULL,
            is_debit INTEGER NOT NULL,
            FOREIGN KEY(entry_id) REFERENCES journal_entries(id),
            FOREIGN KEY(account_code) REFERENCES accounts(code)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_number TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            subtotal REAL NOT NULL,
            total_tax REAL NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL NOT NULL DEFAULT 0.0,
            paid_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoice_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL,
            description TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            tax_rate REAL NOT NULL DEFAULT 0.0,
            subtotal REAL NOT NULL,
            tax_amount REAL NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_number TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            supplier_address TEXT NOT NULL,
            order_date TEXT NOT NULL,
            expected_delivery_date TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            subtotal REAL NOT NULL,
            total_tax REAL NOT NULL,
            total_amount REAL NOT NULL,
            received_subtotal REAL NOT NULL DEFAULT 0.0,
            received_tax REAL NOT NULL DEFAULT 0.0,
            received_total REAL NOT NULL DEFAULT 0.0,
            received_date TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_order_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT NOT NULL,
            description TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            tax_rate REAL NOT NULL DEFAULT 0.0,
            received_quantity REAL NOT NULL DEFAULT 0.0,
            subtotal REAL NOT NULL,
            tax_amount REAL NOT NULL,
            total REAL NOT NULL,
            received_subtotal REAL NOT NULL DEFAULT 0.0,
            received_tax_amount REAL NOT NULL DEFAULT 0.0,
            received_total REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY(po_number) REFERENCES purchase_orders(po_number)
        )
    ''')
    
    # Create payment_clearings table for advanced payment clearing
    c.execute('''
        CREATE TABLE IF NOT EXISTS payment_clearings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clearing_date DATE NOT NULL,
            payment_type TEXT NOT NULL, -- 'receivable' or 'payable'
            payment_reference TEXT NOT NULL,
            invoice_number TEXT,
            po_number TEXT,
            customer_supplier_name TEXT NOT NULL,
            original_amount REAL NOT NULL,
            cleared_amount REAL NOT NULL,
            remaining_amount REAL NOT NULL,
            clearing_method TEXT NOT NULL, -- 'full', 'partial', 'multiple'
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number),
            FOREIGN KEY(po_number) REFERENCES purchase_orders(po_number)
        )
    ''')
    
    # Create aging_schedules table for receivable and payable aging
    c.execute('''
        CREATE TABLE IF NOT EXISTS aging_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_date DATE NOT NULL,
            schedule_type TEXT NOT NULL, -- 'receivable' or 'payable'
            customer_supplier_name TEXT NOT NULL,
            invoice_number TEXT,
            po_number TEXT,
            original_amount REAL NOT NULL,
            current_balance REAL NOT NULL,
            days_overdue INTEGER NOT NULL,
            aging_period TEXT NOT NULL, -- 'current', '30_days', '60_days', '90_days', 'over_90_days'
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number),
            FOREIGN KEY(po_number) REFERENCES purchase_orders(po_number)
        )
    ''')
    
    # Initialize GAAP compliance
    gaap = GAAPCompliance(conn)
    
    conn.commit()

def add_account(conn: sqlite3.Connection, code: str, name: str, type: AccountType, balance: float = 0.0):
    """
    Add a new account to the database.
    """
    c = conn.cursor()
    c.execute('INSERT INTO accounts (code, name, type, balance) VALUES (?, ?, ?, ?)',
              (code, name, type.name, balance))
    conn.commit()

def get_account(conn: sqlite3.Connection, code: str) -> Optional[Tuple[str, str, str, float]]:
    """
    Get an account by code.
    """
    c = conn.cursor()
    c.execute('SELECT code, name, type, balance FROM accounts WHERE code = ?', (code,))
    return c.fetchone()

def list_accounts(conn: sqlite3.Connection) -> List[Tuple[str, str, str, float]]:
    """
    List all accounts.
    """
    c = conn.cursor()
    c.execute('SELECT code, name, type, balance FROM accounts ORDER BY code')
    return c.fetchall()

def add_journal_entry(conn: sqlite3.Connection, description: str, lines: List[Tuple[str, float, bool]]):
    """
    Add a journal entry and its lines. 'lines' is a list of (account_code, amount, is_debit).
    Includes GAAP compliance validation.
    """
    c = conn.cursor()
    
    # Validate double-entry principle (debits = credits)
    total_debits = sum(amount for _, amount, is_debit in lines if is_debit)
    total_credits = sum(amount for _, amount, is_debit in lines if not is_debit)
    
    if abs(total_debits - total_credits) > 0.01:
        raise ValueError(f"Journal entry not balanced: Debits({total_debits}) != Credits({total_credits})")
    
    # Initialize GAAP compliance
    gaap = GAAPCompliance(conn)
    
    # Assess materiality of the transaction
    total_amount = total_debits
    materiality_assessment = gaap.assess_materiality(
        assessment_type="journal_entry",
        actual_amount=total_amount
    )
    
    c.execute('INSERT INTO journal_entries (description) VALUES (?)', (description,))
    entry_id = c.lastrowid
    
    for account_code, amount, is_debit in lines:
        c.execute('INSERT INTO journal_lines (entry_id, account_code, amount, is_debit) VALUES (?, ?, ?, ?)',
                  (entry_id, account_code, amount, int(is_debit)))
        
        # Update account balance
        c.execute('SELECT type, balance FROM accounts WHERE code = ?', (account_code,))
        row = c.fetchone()
        if row:
            acc_type, balance = row
            old_balance = balance
            
            if is_debit:
                if acc_type in ['ASSET', 'EXPENSE']:
                    balance += amount
                else:
                    balance -= amount
            else:
                if acc_type in ['ASSET', 'EXPENSE']:
                    balance -= amount
                else:
                    balance += amount
            
            c.execute('UPDATE accounts SET balance = ? WHERE code = ?', (balance, account_code))
            
            # Log audit trail for significant changes
            if abs(amount) >= materiality_assessment['threshold_amount']:
                gaap.log_audit_trail(
                    user_id="system",
                    action="journal_entry",
                    table_name="accounts",
                    record_id=account_code,
                    old_values={"balance": old_balance},
                    new_values={"balance": balance},
                    principle=GAAPPrinciple.CONSISTENCY,
                    justification=f"Journal entry: {description}"
                )
    
    conn.commit()
    return entry_id

def list_journal_entries(conn: sqlite3.Connection) -> List[Tuple[int, str, str]]:
    """
    List all journal entries (id, description, date).
    """
    c = conn.cursor()
    c.execute('SELECT id, description, date FROM journal_entries ORDER BY id')
    return c.fetchall()

def get_journal_lines(conn: sqlite3.Connection, entry_id: int) -> List[Tuple[int, str, float, bool]]:
    """
    Get all lines for a journal entry.
    """
    c = conn.cursor()
    c.execute('SELECT id, account_code, amount, is_debit FROM journal_lines WHERE entry_id = ?', (entry_id,))
    return [(row[0], row[1], row[2], bool(row[3])) for row in c.fetchall()]

# --- Invoice Functions ---
def add_invoice(conn: sqlite3.Connection, invoice_number: str, customer_name: str, customer_address: str,
                issue_date: str, due_date: str, status: str, notes: str, lines: List[Tuple[str, float, float, float]]):
    """
    Add an invoice and its lines. 'lines' is a list of (description, quantity, unit_price, tax_rate).
    Includes GAAP revenue recognition.
    """
    c = conn.cursor()
    
    # Calculate totals
    subtotal = sum(quantity * unit_price for _, quantity, unit_price, _ in lines)
    total_tax = sum(quantity * unit_price * tax_rate for _, quantity, unit_price, tax_rate in lines)
    total_amount = subtotal + total_tax
    
    c.execute('''
        INSERT INTO invoices (invoice_number, customer_name, customer_address, issue_date, due_date, 
                             status, notes, subtotal, total_tax, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (invoice_number, customer_name, customer_address, issue_date, due_date, 
          status, notes, subtotal, total_tax, total_amount))
    
    # Add invoice lines
    for description, quantity, unit_price, tax_rate in lines:
        line_subtotal = quantity * unit_price
        line_tax = line_subtotal * tax_rate
        line_total = line_subtotal + line_tax
        
        c.execute('''
            INSERT INTO invoice_lines (invoice_number, description, quantity, unit_price, tax_rate,
                                     subtotal, tax_amount, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (invoice_number, description, quantity, unit_price, tax_rate,
              line_subtotal, line_tax, line_total))
    
    # Initialize GAAP compliance for revenue recognition
    from pyledger.gaap_compliance import GAAPCompliance, RevenueRecognitionMethod
    
    gaap = GAAPCompliance(conn)
    
    # Default to point-in-time recognition for standard invoices
    # This can be overridden for specific contracts
    gaap.validate_revenue_recognition(
        invoice_number=invoice_number,
        recognition_method=RevenueRecognitionMethod.POINT_IN_TIME,
        performance_obligations=["Delivery of goods/services"],
        start_date=issue_date,
        end_date=issue_date
    )
    
    conn.commit()

def get_invoice(conn: sqlite3.Connection, invoice_number: str) -> Optional[Tuple]:
    """
    Get an invoice by number.
    """
    c = conn.cursor()
    c.execute('''
        SELECT invoice_number, customer_name, customer_address, issue_date, due_date,
               status, notes, subtotal, total_tax, total_amount, paid_amount, paid_date
        FROM invoices WHERE invoice_number = ?
    ''', (invoice_number,))
    return c.fetchone()

def list_invoices(conn: sqlite3.Connection, status: Optional[str] = None) -> List[Tuple]:
    """
    List all invoices, optionally filtered by status.
    """
    c = conn.cursor()
    if status:
        c.execute('''
            SELECT invoice_number, customer_name, customer_address, issue_date, due_date,
                   status, notes, subtotal, total_tax, total_amount, paid_amount, paid_date
            FROM invoices WHERE status = ? ORDER BY issue_date DESC
        ''', (status,))
    else:
        c.execute('''
            SELECT invoice_number, customer_name, customer_address, issue_date, due_date,
                   status, notes, subtotal, total_tax, total_amount, paid_amount, paid_date
            FROM invoices ORDER BY issue_date DESC
        ''')
    return c.fetchall()

def get_invoice_lines(conn: sqlite3.Connection, invoice_number: str) -> List[Tuple]:
    """
    Get all lines for an invoice.
    """
    c = conn.cursor()
    c.execute('''
        SELECT id, description, quantity, unit_price, tax_rate, subtotal, tax_amount, total
        FROM invoice_lines WHERE invoice_number = ? ORDER BY id
    ''', (invoice_number,))
    return c.fetchall()

def update_invoice_payment(conn: sqlite3.Connection, invoice_number: str, paid_amount: float, paid_date: str):
    """
    Update invoice payment information.
    """
    c = conn.cursor()
    c.execute('''
        UPDATE invoices SET paid_amount = ?, paid_date = ? WHERE invoice_number = ?
    ''', (paid_amount, paid_date, invoice_number))
    conn.commit()

# --- Purchase Order Functions ---
def add_purchase_order(conn: sqlite3.Connection, po_number: str, supplier_name: str, supplier_address: str,
                      order_date: str, expected_delivery_date: str, status: str, notes: str,
                      lines: List[Tuple[str, float, float, float]]):
    """
    Add a purchase order and its lines. 'lines' is a list of (description, quantity, unit_price, tax_rate).
    """
    c = conn.cursor()
    
    # Calculate totals
    subtotal = sum(quantity * unit_price for _, quantity, unit_price, _ in lines)
    total_tax = sum(quantity * unit_price * tax_rate for _, quantity, unit_price, tax_rate in lines)
    total_amount = subtotal + total_tax
    
    c.execute('''
        INSERT INTO purchase_orders (po_number, supplier_name, supplier_address, order_date,
                                   expected_delivery_date, status, notes, subtotal, total_tax, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (po_number, supplier_name, supplier_address, order_date, expected_delivery_date,
          status, notes, subtotal, total_tax, total_amount))
    
    # Add purchase order lines
    for description, quantity, unit_price, tax_rate in lines:
        line_subtotal = quantity * unit_price
        line_tax = line_subtotal * tax_rate
        line_total = line_subtotal + line_tax
        
        c.execute('''
            INSERT INTO purchase_order_lines (po_number, description, quantity, unit_price, tax_rate,
                                            subtotal, tax_amount, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (po_number, description, quantity, unit_price, tax_rate,
              line_subtotal, line_tax, line_total))
    
    conn.commit()

def get_purchase_order(conn: sqlite3.Connection, po_number: str) -> Optional[Tuple]:
    """
    Get a purchase order by number.
    """
    c = conn.cursor()
    c.execute('''
        SELECT po_number, supplier_name, supplier_address, order_date, expected_delivery_date,
               status, notes, subtotal, total_tax, total_amount, received_subtotal, received_tax,
               received_total, received_date
        FROM purchase_orders WHERE po_number = ?
    ''', (po_number,))
    return c.fetchone()

def list_purchase_orders(conn: sqlite3.Connection, status: Optional[str] = None) -> List[Tuple]:
    """
    List all purchase orders, optionally filtered by status.
    """
    c = conn.cursor()
    if status:
        c.execute('''
            SELECT po_number, supplier_name, supplier_address, order_date, expected_delivery_date,
                   status, notes, subtotal, total_tax, total_amount, received_subtotal, received_tax,
                   received_total, received_date
            FROM purchase_orders WHERE status = ? ORDER BY order_date DESC
        ''', (status,))
    else:
        c.execute('''
            SELECT po_number, supplier_name, supplier_address, order_date, expected_delivery_date,
                   status, notes, subtotal, total_tax, total_amount, received_subtotal, received_tax,
                   received_total, received_date
            FROM purchase_orders ORDER BY order_date DESC
        ''')
    return c.fetchall()

def get_purchase_order_lines(conn: sqlite3.Connection, po_number: str) -> List[Tuple]:
    """
    Get all lines for a purchase order.
    """
    c = conn.cursor()
    c.execute('''
        SELECT id, description, quantity, unit_price, tax_rate, received_quantity,
               subtotal, tax_amount, total, received_subtotal, received_tax_amount, received_total
        FROM purchase_order_lines WHERE po_number = ? ORDER BY id
    ''', (po_number,))
    return c.fetchall()

def update_purchase_order_receipt(conn: sqlite3.Connection, po_number: str, line_id: int, 
                                received_quantity: float, received_date: str):
    """
    Update purchase order receipt information.
    """
    c = conn.cursor()
    
    # Update the specific line
    c.execute('''
        UPDATE purchase_order_lines 
        SET received_quantity = ?, received_subtotal = ? * unit_price,
            received_tax_amount = ? * unit_price * tax_rate,
            received_total = ? * unit_price * (1 + tax_rate)
        WHERE id = ?
    ''', (received_quantity, received_quantity, received_quantity, received_quantity, line_id))
    
    # Update purchase order totals
    c.execute('''
        UPDATE purchase_orders 
        SET received_subtotal = (
            SELECT SUM(received_subtotal) FROM purchase_order_lines WHERE po_number = ?
        ),
        received_tax = (
            SELECT SUM(received_tax_amount) FROM purchase_order_lines WHERE po_number = ?
        ),
        received_total = (
            SELECT SUM(received_total) FROM purchase_order_lines WHERE po_number = ?
        ),
        received_date = ?
        WHERE po_number = ?
    ''', (po_number, po_number, po_number, received_date, po_number))
    
    conn.commit()

# Advanced Payment Clearing Functions

def add_payment_clearing(conn: sqlite3.Connection, clearing_date: str, payment_type: str, 
                        payment_reference: str, customer_supplier_name: str, original_amount: float,
                        cleared_amount: float, remaining_amount: float, clearing_method: str,
                        invoice_number: str = None, po_number: str = None, notes: str = None):
    """
    Add a payment clearing record for advanced payment tracking.
    
    Args:
        clearing_date: Date of the payment clearing
        payment_type: 'receivable' or 'payable'
        payment_reference: Reference number for the payment
        customer_supplier_name: Name of customer or supplier
        original_amount: Original invoice/PO amount
        cleared_amount: Amount cleared by this payment
        remaining_amount: Remaining balance after clearing
        clearing_method: 'full', 'partial', or 'multiple'
        invoice_number: Associated invoice number (for receivables)
        po_number: Associated purchase order number (for payables)
        notes: Additional notes
    """
    c = conn.cursor()
    c.execute('''
        INSERT INTO payment_clearings (clearing_date, payment_type, payment_reference, invoice_number,
                                     po_number, customer_supplier_name, original_amount, cleared_amount,
                                     remaining_amount, clearing_method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (clearing_date, payment_type, payment_reference, invoice_number, po_number,
          customer_supplier_name, original_amount, cleared_amount, remaining_amount, clearing_method, notes))
    conn.commit()
    return c.lastrowid

def get_payment_clearings(conn: sqlite3.Connection, payment_type: Optional[str] = None, 
                         customer_supplier_name: Optional[str] = None) -> List[Tuple]:
    """
    Get payment clearing records with optional filtering.
    """
    c = conn.cursor()
    
    if payment_type and customer_supplier_name:
        c.execute('''
            SELECT id, clearing_date, payment_type, payment_reference, invoice_number, po_number,
                   customer_supplier_name, original_amount, cleared_amount, remaining_amount,
                   clearing_method, notes, created_at
            FROM payment_clearings 
            WHERE payment_type = ? AND customer_supplier_name = ?
            ORDER BY clearing_date DESC
        ''', (payment_type, customer_supplier_name))
    elif payment_type:
        c.execute('''
            SELECT id, clearing_date, payment_type, payment_reference, invoice_number, po_number,
                   customer_supplier_name, original_amount, cleared_amount, remaining_amount,
                   clearing_method, notes, created_at
            FROM payment_clearings 
            WHERE payment_type = ?
            ORDER BY clearing_date DESC
        ''', (payment_type,))
    elif customer_supplier_name:
        c.execute('''
            SELECT id, clearing_date, payment_type, payment_reference, invoice_number, po_number,
                   customer_supplier_name, original_amount, cleared_amount, remaining_amount,
                   clearing_method, notes, created_at
            FROM payment_clearings 
            WHERE customer_supplier_name = ?
            ORDER BY clearing_date DESC
        ''', (customer_supplier_name,))
    else:
        c.execute('''
            SELECT id, clearing_date, payment_type, payment_reference, invoice_number, po_number,
                   customer_supplier_name, original_amount, cleared_amount, remaining_amount,
                   clearing_method, notes, created_at
            FROM payment_clearings 
            ORDER BY clearing_date DESC
        ''')
    
    return c.fetchall()

def clear_invoice_payment(conn: sqlite3.Connection, invoice_number: str, payment_amount: float,
                         payment_date: str, payment_reference: str, clearing_method: str = 'partial'):
    """
    Clear an invoice payment with advanced tracking.
    """
    c = conn.cursor()
    
    # Get current invoice information
    c.execute('''
        SELECT customer_name, total_amount, paid_amount
        FROM invoices WHERE invoice_number = ?
    ''', (invoice_number,))
    invoice = c.fetchone()
    
    if not invoice:
        raise ValueError(f"Invoice {invoice_number} not found")
    
    customer_name, total_amount, current_paid = invoice
    new_paid_amount = current_paid + payment_amount
    remaining_amount = total_amount - new_paid_amount
    
    # Update invoice payment
    c.execute('''
        UPDATE invoices 
        SET paid_amount = ?, paid_date = ?
        WHERE invoice_number = ?
    ''', (new_paid_amount, payment_date, invoice_number))
    
    # Add payment clearing record
    add_payment_clearing(
        conn=conn,
        clearing_date=payment_date,
        payment_type='receivable',
        payment_reference=payment_reference,
        customer_supplier_name=customer_name,
        original_amount=total_amount,
        cleared_amount=payment_amount,
        remaining_amount=remaining_amount,
        clearing_method=clearing_method,
        invoice_number=invoice_number,
        notes=f"Payment clearing for invoice {invoice_number}"
    )
    
    conn.commit()

def clear_purchase_order_payment(conn: sqlite3.Connection, po_number: str, payment_amount: float,
                               payment_date: str, payment_reference: str, clearing_method: str = 'partial'):
    """
    Clear a purchase order payment with advanced tracking.
    """
    c = conn.cursor()
    
    # Get current PO information
    c.execute('''
        SELECT supplier_name, total_amount, received_total
        FROM purchase_orders WHERE po_number = ?
    ''', (po_number,))
    po = c.fetchone()
    
    if not po:
        raise ValueError(f"Purchase order {po_number} not found")
    
    supplier_name, total_amount, current_received = po
    new_received_amount = current_received + payment_amount
    remaining_amount = total_amount - new_received_amount
    
    # Update PO received amount
    c.execute('''
        UPDATE purchase_orders 
        SET received_total = ?, received_date = ?
        WHERE po_number = ?
    ''', (new_received_amount, payment_date, po_number))
    
    # Add payment clearing record
    add_payment_clearing(
        conn=conn,
        clearing_date=payment_date,
        payment_type='payable',
        payment_reference=payment_reference,
        customer_supplier_name=supplier_name,
        original_amount=total_amount,
        cleared_amount=payment_amount,
        remaining_amount=remaining_amount,
        clearing_method=clearing_method,
        po_number=po_number,
        notes=f"Payment clearing for PO {po_number}"
    )
    
    conn.commit()

def add_aging_schedule(conn: sqlite3.Connection, schedule_date: str, schedule_type: str,
                      customer_supplier_name: str, original_amount: float, current_balance: float,
                      days_overdue: int, aging_period: str, invoice_number: str = None,
                      po_number: str = None, notes: str = None):
    """
    Add an aging schedule record for receivables or payables.
    
    Args:
        schedule_date: Date of the aging schedule
        schedule_type: 'receivable' or 'payable'
        customer_supplier_name: Name of customer or supplier
        original_amount: Original invoice/PO amount
        current_balance: Current outstanding balance
        days_overdue: Number of days overdue
        aging_period: 'current', '30_days', '60_days', '90_days', 'over_90_days'
        invoice_number: Associated invoice number (for receivables)
        po_number: Associated purchase order number (for payables)
        notes: Additional notes
    """
    c = conn.cursor()
    c.execute('''
        INSERT INTO aging_schedules (schedule_date, schedule_type, customer_supplier_name,
                                   invoice_number, po_number, original_amount, current_balance,
                                   days_overdue, aging_period, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (schedule_date, schedule_type, customer_supplier_name, invoice_number, po_number,
          original_amount, current_balance, days_overdue, aging_period, notes))
    conn.commit()
    return c.lastrowid

def get_aging_schedule(conn: sqlite3.Connection, schedule_type: Optional[str] = None,
                      customer_supplier_name: Optional[str] = None, aging_period: Optional[str] = None) -> List[Tuple]:
    """
    Get aging schedule records with optional filtering.
    """
    c = conn.cursor()
    
    conditions = []
    params = []
    
    if schedule_type:
        conditions.append("schedule_type = ?")
        params.append(schedule_type)
    
    if customer_supplier_name:
        conditions.append("customer_supplier_name = ?")
        params.append(customer_supplier_name)
    
    if aging_period:
        conditions.append("aging_period = ?")
        params.append(aging_period)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    c.execute(f'''
        SELECT id, schedule_date, schedule_type, customer_supplier_name, invoice_number, po_number,
               original_amount, current_balance, days_overdue, aging_period, notes, created_at
        FROM aging_schedules 
        WHERE {where_clause}
        ORDER BY schedule_date DESC, customer_supplier_name
    ''', params)
    
    return c.fetchall()

def generate_aging_report(conn: sqlite3.Connection, schedule_date: str, schedule_type: str):
    """
    Generate an aging report for receivables or payables.
    """
    c = conn.cursor()
    
    if schedule_type == 'receivable':
        # Get unpaid invoices
        c.execute('''
            SELECT customer_name, invoice_number, total_amount, paid_amount,
                   (total_amount - paid_amount) as outstanding_balance,
                   julianday(?) - julianday(issue_date) as days_outstanding
            FROM invoices 
            WHERE paid_amount < total_amount
            ORDER BY customer_name, issue_date
        ''', (schedule_date,))
    else:  # payable
        # Get unpaid purchase orders
        c.execute('''
            SELECT supplier_name, po_number, total_amount, received_total,
                   (total_amount - received_total) as outstanding_balance,
                   julianday(?) - julianday(order_date) as days_outstanding
            FROM purchase_orders 
            WHERE received_total < total_amount
            ORDER BY supplier_name, order_date
        ''', (schedule_date,))
    
    items = c.fetchall()
    
    # Process each item and add to aging schedule
    for item in items:
        if schedule_type == 'receivable':
            customer_name, invoice_number, original_amount, paid_amount, current_balance, days_outstanding = item
            days_overdue = max(0, int(days_outstanding))
        else:
            supplier_name, po_number, original_amount, received_total, current_balance, days_outstanding = item
            customer_name = supplier_name
            invoice_number = None
            days_overdue = max(0, int(days_outstanding))
        
        # Determine aging period
        if days_overdue <= 0:
            aging_period = 'current'
        elif days_overdue <= 30:
            aging_period = '30_days'
        elif days_overdue <= 60:
            aging_period = '60_days'
        elif days_overdue <= 90:
            aging_period = '90_days'
        else:
            aging_period = 'over_90_days'
        
        # Add to aging schedule
        add_aging_schedule(
            conn=conn,
            schedule_date=schedule_date,
            schedule_type=schedule_type,
            customer_supplier_name=customer_name,
            original_amount=original_amount,
            current_balance=current_balance,
            days_overdue=days_overdue,
            aging_period=aging_period,
            invoice_number=invoice_number,
            po_number=po_number if schedule_type == 'payable' else None,
            notes=f"Auto-generated aging entry for {schedule_type}"
        )
    
    return len(items)

def get_payment_summary(conn: sqlite3.Connection, payment_type: str, start_date: str, end_date: str) -> dict:
    """
    Get payment summary for a date range.
    """
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            COUNT(*) as total_payments,
            SUM(cleared_amount) as total_cleared,
            SUM(original_amount) as total_original,
            AVG(cleared_amount) as avg_payment,
            clearing_method,
            COUNT(*) as method_count
        FROM payment_clearings 
        WHERE payment_type = ? AND clearing_date BETWEEN ? AND ?
        GROUP BY clearing_method
    ''', (payment_type, start_date, end_date))
    
    summary = {
        'payment_type': payment_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_payments': 0,
        'total_cleared': 0,
        'total_original': 0,
        'avg_payment': 0,
        'methods': {}
    }
    
    for row in c.fetchall():
        total_payments, total_cleared, total_original, avg_payment, method, method_count = row
        summary['total_payments'] += total_payments
        summary['total_cleared'] += total_cleared or 0
        summary['total_original'] += total_original or 0
        summary['methods'][method] = {
            'count': method_count,
            'amount': total_cleared or 0
        }
    
    if summary['total_payments'] > 0:
        summary['avg_payment'] = summary['total_cleared'] / summary['total_payments']
    
    return summary