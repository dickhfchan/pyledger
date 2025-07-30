import sqlite3
from typing import List, Optional, Tuple
from pyledger.accounts import AccountType

DB_FILE = 'pyledger.db'

def get_connection(db_file: str = DB_FILE):
    return sqlite3.connect(db_file)

def init_db(conn: sqlite3.Connection):
    """
    Create tables for accounts, journal_entries, and journal_lines.
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