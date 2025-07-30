from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pyledger.accounts import AccountType
from pyledger.db import (
    get_connection, init_db, add_account, list_accounts, add_journal_entry, list_journal_entries, get_journal_lines
)
from pyledger.reports import balance_sheet, income_statement, cash_flow_report
from pyledger.accounts import ChartOfAccounts

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