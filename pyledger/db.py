import sqlite3
from typing import List, Optional, Tuple
from pyledger.accounts import AccountType

DB_FILE = 'pyledger.db'

def get_connection(db_file: str = DB_FILE):
    return sqlite3.connect(db_file)

def init_db(conn: sqlite3.Connection):
    """
    Create tables for accounts, journal_entries, journal_lines, invoices, and purchase_orders.
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
    """
    c = conn.cursor()
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