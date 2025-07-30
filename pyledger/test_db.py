from db import get_connection, init_db, add_account, list_accounts, add_journal_entry, list_journal_entries, get_journal_lines
from accounts import AccountType
import os

DB_FILE = 'pyledger.db'

def main():
    # Remove old db for clean test
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    conn = get_connection()
    print('Initializing database...')
    init_db(conn)

    print('\nAdding accounts...')
    add_account(conn, '1000', 'Cash', AccountType.ASSET)
    add_account(conn, '2000', 'Accounts Payable', AccountType.LIABILITY)
    add_account(conn, '3000', 'Owner Equity', AccountType.EQUITY)

    print('\nListing accounts:')
    for code, name, type_str, balance in list_accounts(conn):
        print(f"{code}: {name} ({type_str}) Balance: {balance}")

    print('\nAdding a journal entry...')
    entry_id = add_journal_entry(conn, 'Owner invests cash', [
        ('1000', 1000.0, True),   # Debit Cash
        ('3000', 1000.0, False),  # Credit Owner Equity
    ])
    print(f"Journal entry ID: {entry_id}")

    print('\nListing journal entries:')
    for eid, desc, date in list_journal_entries(conn):
        print(f"{eid}: {desc} ({date})")

    print(f'\nJournal lines for entry {entry_id}:')
    for line_id, account_code, amount, is_debit in get_journal_lines(conn, entry_id):
        dc = 'Debit' if is_debit else 'Credit'
        print(f"{line_id}: {dc} {account_code} {amount}")

    print('\nFinal account balances:')
    for code, name, type_str, balance in list_accounts(conn):
        print(f"{code}: {name} ({type_str}) Balance: {balance}")

    conn.close()
    print('\nDatabase demo complete.')

if __name__ == '__main__':
    main()