import argparse
import json
from accounts import AccountType, ChartOfAccounts
from journal import JournalLine, JournalEntry, Ledger
from reports import balance_sheet, income_statement, cash_flow_report
from db import (
    get_connection, init_db, add_account as db_add_account, list_accounts as db_list_accounts,
    add_journal_entry as db_add_journal_entry, list_journal_entries as db_list_journal_entries,
    get_journal_lines as db_get_journal_lines
)

ACCOUNT_TYPE_CHOICES = [t.name for t in AccountType]

ACCOUNTS_FILE = 'accounts.json'
ENTRIES_FILE = 'entries.json'
DB_FILE = 'pyledger.db'

def setup_sample_data(chart, ledger):
    # Add sample accounts
    chart.add_account('1000', 'Cash', AccountType.ASSET)
    chart.add_account('2000', 'Accounts Payable', AccountType.LIABILITY)
    chart.add_account('3000', 'Owner Equity', AccountType.EQUITY)
    chart.add_account('4000', 'Sales Revenue', AccountType.REVENUE)
    chart.add_account('5000', 'Office Supplies Expense', AccountType.EXPENSE)
    # Add a sample journal entry
    entry = JournalEntry(
        'Owner invests cash',
        [
            JournalLine('1000', 1000.0, True),  # Debit Cash
            JournalLine('3000', 1000.0, False), # Credit Equity
        ]
    )
    ledger.post_entry(entry)

def add_account_interactive(chart):
    code = input('Account code: ')
    name = input('Account name: ')
    print(f"Account types: {', '.join(ACCOUNT_TYPE_CHOICES)}")
    type_str = input('Account type: ').upper()
    if type_str not in ACCOUNT_TYPE_CHOICES:
        print('Invalid account type.')
        return
    chart.add_account(code, name, AccountType[type_str])
    print('Account added.')

def list_accounts(chart):
    print('Accounts:')
    for acc in chart.accounts.values():
        print(f"{acc.code}: {acc.name} ({acc.type.name}) Balance: {acc.balance}")

def add_journal_entry_interactive(chart, ledger):
    description = input('Entry description: ')
    lines = []
    while True:
        code = input('Account code (or blank to finish): ')
        if not code:
            break
        amount = float(input('Amount: '))
        dc = input('Debit or Credit (d/c): ').lower()
        is_debit = dc == 'd'
        lines.append(JournalLine(code, amount, is_debit))
    try:
        entry = JournalEntry(description, lines)
        ledger.post_entry(entry)
        print('Journal entry posted.')
    except Exception as e:
        print(f'Error: {e}')

def list_journal_entries(ledger):
    print('Journal Entries:')
    for i, entry in enumerate(ledger.entries, 1):
        print(f"{i}. {entry.description}")
        for line in entry.lines:
            dc = 'Debit' if line.is_debit else 'Credit'
            print(f"   {dc} {line.account_code}: {line.amount}")

def save_data(chart, ledger, accounts_file=ACCOUNTS_FILE, entries_file=ENTRIES_FILE):
    with open(accounts_file, 'w') as f:
        json.dump(chart.to_dict(), f, indent=2)
    with open(entries_file, 'w') as f:
        json.dump(ledger.to_dict(), f, indent=2)
    print(f"Data saved to {accounts_file} and {entries_file}.")

def load_data(accounts_file=ACCOUNTS_FILE, entries_file=ENTRIES_FILE):
    with open(accounts_file, 'r') as f:
        chart = ChartOfAccounts.from_dict(json.load(f))
    with open(entries_file, 'r') as f:
        ledger = Ledger.from_dict(json.load(f), chart)
    print(f"Data loaded from {accounts_file} and {entries_file}.")
    return chart, ledger

# --- Database-backed CLI operations ---
def db_add_account_interactive():
    conn = get_connection()
    code = input('Account code: ')
    name = input('Account name: ')
    print(f"Account types: {', '.join(ACCOUNT_TYPE_CHOICES)}")
    type_str = input('Account type: ').upper()
    if type_str not in ACCOUNT_TYPE_CHOICES:
        print('Invalid account type.')
        return
    db_add_account(conn, code, name, AccountType[type_str])
    print('Account added to database.')
    conn.close()

def db_list_accounts_cmd():
    conn = get_connection()
    print('Accounts in database:')
    for code, name, type_str, balance in db_list_accounts(conn):
        print(f"{code}: {name} ({type_str}) Balance: {balance}")
    conn.close()

def db_add_entry_interactive():
    conn = get_connection()
    description = input('Entry description: ')
    lines = []
    while True:
        code = input('Account code (or blank to finish): ')
        if not code:
            break
        amount = float(input('Amount: '))
        dc = input('Debit or Credit (d/c): ').lower()
        is_debit = dc == 'd'
        lines.append((code, amount, is_debit))
    # Check balance
    total_debits = sum(amount for code, amount, is_debit in lines if is_debit)
    total_credits = sum(amount for code, amount, is_debit in lines if not is_debit)
    if abs(total_debits - total_credits) > 1e-6:
        print('Error: Entry is not balanced.')
        conn.close()
        return
    db_add_journal_entry(conn, description, lines)
    print('Journal entry added to database.')
    conn.close()

def db_list_entries_cmd():
    conn = get_connection()
    print('Journal entries in database:')
    for eid, desc, date in db_list_journal_entries(conn):
        print(f"{eid}: {desc} ({date})")
    conn.close()

def db_entry_lines_cmd():
    conn = get_connection()
    entry_id = int(input('Entry ID: '))
    print(f'Lines for entry {entry_id}:')
    for line_id, account_code, amount, is_debit in db_get_journal_lines(conn, entry_id):
        dc = 'Debit' if is_debit else 'Credit'
        print(f"{line_id}: {dc} {account_code} {amount}")
    conn.close()

def db_init_cmd():
    conn = get_connection()
    init_db(conn)
    print('Database initialized.')
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='PyLedger Accounting CLI')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('sample', help='Load sample data')
    subparsers.add_parser('balance-sheet', help='Print balance sheet')
    subparsers.add_parser('income-statement', help='Print income statement')
    subparsers.add_parser('cash-flow', help='Print cash flow report')
    subparsers.add_parser('add-account', help='Add a new account interactively')
    subparsers.add_parser('list-accounts', help='List all accounts')
    subparsers.add_parser('add-entry', help='Add a new journal entry interactively')
    subparsers.add_parser('list-entries', help='List all journal entries')
    subparsers.add_parser('save', help='Save accounts and entries to JSON files')
    subparsers.add_parser('load', help='Load accounts and entries from JSON files')
    # Database-backed commands
    subparsers.add_parser('db-init', help='Initialize the database')
    subparsers.add_parser('db-add-account', help='Add a new account to the database')
    subparsers.add_parser('db-list-accounts', help='List all accounts in the database')
    subparsers.add_parser('db-add-entry', help='Add a new journal entry to the database')
    subparsers.add_parser('db-list-entries', help='List all journal entries in the database')
    subparsers.add_parser('db-entry-lines', help='Show lines for a specific journal entry in the database')

    args = parser.parse_args()

    # By default, start with empty chart and ledger
    chart = ChartOfAccounts()
    ledger = Ledger(chart)

    if args.command == 'load':
        chart, ledger = load_data()
    elif args.command == 'sample':
        setup_sample_data(chart, ledger)
        print('Sample data loaded.')
    elif args.command == 'add-account':
        add_account_interactive(chart)
    elif args.command == 'list-accounts':
        list_accounts(chart)
    elif args.command == 'add-entry':
        add_journal_entry_interactive(chart, ledger)
    elif args.command == 'list-entries':
        list_journal_entries(ledger)
    elif args.command == 'balance-sheet':
        print('Balance Sheet:')
        print(balance_sheet(chart))
    elif args.command == 'income-statement':
        print('Income Statement:')
        print(income_statement(chart))
    elif args.command == 'cash-flow':
        print('Cash Flow Report:')
        print(cash_flow_report(chart))
    elif args.command == 'save':
        save_data(chart, ledger)
    # Database-backed commands
    elif args.command == 'db-init':
        db_init_cmd()
    elif args.command == 'db-add-account':
        db_add_account_interactive()
    elif args.command == 'db-list-accounts':
        db_list_accounts_cmd()
    elif args.command == 'db-add-entry':
        db_add_entry_interactive()
    elif args.command == 'db-list-entries':
        db_list_entries_cmd()
    elif args.command == 'db-entry-lines':
        db_entry_lines_cmd()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()