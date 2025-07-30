import os
import json
from accounts import AccountType, ChartOfAccounts
from journal import JournalLine, JournalEntry, Ledger
from reports import balance_sheet, income_statement, cash_flow_report

ACCOUNTS_FILE = 'test_accounts.json'
ENTRIES_FILE = 'test_entries.json'

def test_sample_data():
    chart = ChartOfAccounts()
    ledger = Ledger(chart)
    # Add sample accounts and entry
    chart.add_account('1000', 'Cash', AccountType.ASSET)
    chart.add_account('2000', 'Accounts Payable', AccountType.LIABILITY)
    chart.add_account('3000', 'Owner Equity', AccountType.EQUITY)
    chart.add_account('4000', 'Sales Revenue', AccountType.REVENUE)
    chart.add_account('5000', 'Office Supplies Expense', AccountType.EXPENSE)
    entry = JournalEntry(
        'Owner invests cash',
        [
            JournalLine('1000', 1000.0, True),
            JournalLine('3000', 1000.0, False),
        ]
    )
    ledger.post_entry(entry)
    assert len(chart.accounts) == 5
    assert len(ledger.entries) == 1
    print('Sample data test passed.')
    return chart, ledger

def test_save_load(chart, ledger):
    # Save
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(chart.to_dict(), f, indent=2)
    with open(ENTRIES_FILE, 'w') as f:
        json.dump(ledger.to_dict(), f, indent=2)
    # Load
    from accounts import ChartOfAccounts
    from journal import Ledger
    with open(ACCOUNTS_FILE, 'r') as f:
        loaded_chart = ChartOfAccounts.from_dict(json.load(f))
    with open(ENTRIES_FILE, 'r') as f:
        loaded_ledger = Ledger.from_dict(json.load(f), loaded_chart)
    assert len(loaded_chart.accounts) == len(chart.accounts)
    assert len(loaded_ledger.entries) == len(ledger.entries)
    print('Save/load test passed.')
    return loaded_chart, loaded_ledger

def test_add_account_entry(chart, ledger):
    chart.add_account('6000', 'Bank', AccountType.ASSET)
    entry = JournalEntry(
        'Deposit to bank',
        [
            JournalLine('6000', 500.0, True),
            JournalLine('1000', 500.0, False),
        ]
    )
    ledger.post_entry(entry)
    assert '6000' in chart.accounts
    assert len(ledger.entries) == 2
    print('Add account/entry test passed.')

def test_reports(chart):
    bs = balance_sheet(chart)
    is_ = income_statement(chart)
    cf = cash_flow_report(chart)
    assert 'assets' in bs and 'liabilities' in bs and 'equity' in bs
    assert 'revenues' in is_ and 'expenses' in is_ and 'net_income' in is_
    assert 'cash_accounts' in cf and 'total_cash' in cf
    print('Report generation test passed.')

def cleanup():
    if os.path.exists(ACCOUNTS_FILE):
        os.remove(ACCOUNTS_FILE)
    if os.path.exists(ENTRIES_FILE):
        os.remove(ENTRIES_FILE)
    print('Cleanup complete.')

def run_all_tests():
    print('Running PyLedger automated tests...')
    chart, ledger = test_sample_data()
    loaded_chart, loaded_ledger = test_save_load(chart, ledger)
    test_add_account_entry(loaded_chart, loaded_ledger)
    test_reports(loaded_chart)
    cleanup()
    print('All tests passed!')

if __name__ == '__main__':
    run_all_tests()