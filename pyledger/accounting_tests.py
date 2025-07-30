import json
import os
from pyledger.db import (
    get_connection, init_db, add_account, list_accounts, add_journal_entry, 
    list_journal_entries, get_journal_lines
)
from pyledger.accounts import AccountType, ChartOfAccounts
from pyledger.reports import balance_sheet, income_statement, cash_flow_report

class AccountingTestSuite:
    """Professional accounting test suite for PyLedger"""
    
    def setup_chart_of_accounts(self, conn):
        """Set up a standard chart of accounts for testing"""
        # Assets
        add_account(conn, '1000', 'Cash', AccountType.ASSET)
        add_account(conn, '1100', 'Accounts Receivable', AccountType.ASSET)
        add_account(conn, '1200', 'Inventory', AccountType.ASSET)
        add_account(conn, '1300', 'Equipment', AccountType.ASSET)
        
        # Liabilities
        add_account(conn, '2000', 'Accounts Payable', AccountType.LIABILITY)
        add_account(conn, '2100', 'Notes Payable', AccountType.LIABILITY)
        
        # Equity
        add_account(conn, '3000', 'Owner Equity', AccountType.EQUITY)
        add_account(conn, '3100', 'Retained Earnings', AccountType.EQUITY)
        
        # Revenue
        add_account(conn, '4000', 'Sales Revenue', AccountType.REVENUE)
        add_account(conn, '4100', 'Service Revenue', AccountType.REVENUE)
        
        # Expenses
        add_account(conn, '5000', 'Cost of Goods Sold', AccountType.EXPENSE)
        add_account(conn, '5100', 'Rent Expense', AccountType.EXPENSE)
        add_account(conn, '5200', 'Utilities Expense', AccountType.EXPENSE)
        add_account(conn, '5300', 'Salaries Expense', AccountType.EXPENSE)

def test_1_accounting_equation():
    """Test: Assets = Liabilities + Equity (Fundamental Accounting Equation)"""
    print("Testing Accounting Equation...")
    
    # Clean setup
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    # Set up accounts
    test_suite = AccountingTestSuite()
    test_suite.setup_chart_of_accounts(conn)
    
    # Initial investment
    add_journal_entry(conn, 'Owner investment', [
        ('1000', 10000.0, True),   # Debit Cash
        ('3000', 10000.0, False),  # Credit Owner Equity
    ])
    
    # Verify accounting equation
    accounts = list_accounts(conn)
    assets = sum(balance for code, name, type_str, balance in accounts if type_str == 'ASSET')
    liabilities = sum(balance for code, name, type_str, balance in accounts if type_str == 'LIABILITY')
    equity = sum(balance for code, name, type_str, balance in accounts if type_str == 'EQUITY')
    
    assert abs(assets - (liabilities + equity)) < 0.01, f"Accounting equation violated: Assets({assets}) != Liabilities({liabilities}) + Equity({equity})"
    print("✅ Accounting equation validated: Assets = Liabilities + Equity")
    
    conn.close()
    os.remove('test_accounting.db')

def test_2_double_entry_validation():
    """Test: All journal entries must balance (debits = credits)"""
    print("Testing Double-Entry Validation...")
    
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    # Valid balanced entry
    add_journal_entry(conn, 'Purchase equipment', [
        ('1300', 5000.0, True),    # Debit Equipment
        ('1000', 5000.0, False),   # Credit Cash
    ])
    
    # Test unbalanced entry (should fail)
    try:
        add_journal_entry(conn, 'Invalid entry', [
            ('1000', 1000.0, True),   # Debit Cash
            ('3000', 500.0, False),   # Credit Equity (unbalanced)
        ])
        assert False, "Unbalanced entry should have failed"
    except Exception as e:
        assert "not balanced" in str(e) or "balanced" in str(e)
        print("✅ Double-entry validation working: Unbalanced entries rejected")
    
    conn.close()
    os.remove('test_accounting.db')

def test_3_revenue_and_expense_tracking():
    """Test: Revenue and expense recognition"""
    print("Testing Revenue and Expense Tracking...")
    
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    test_suite = AccountingTestSuite()
    test_suite.setup_chart_of_accounts(conn)
    
    # Record sales revenue
    add_journal_entry(conn, 'Sales on account', [
        ('1100', 5000.0, True),    # Debit Accounts Receivable
        ('4000', 5000.0, False),   # Credit Sales Revenue
    ])
    
    # Record expense
    add_journal_entry(conn, 'Pay rent', [
        ('5100', 2000.0, True),    # Debit Rent Expense
        ('1000', 2000.0, False),   # Credit Cash
    ])
    
    # Verify revenue and expense recording
    accounts = list_accounts(conn)
    revenue = sum(balance for code, name, type_str, balance in accounts if type_str == 'REVENUE')
    expenses = sum(balance for code, name, type_str, balance in accounts if type_str == 'EXPENSE')
    
    assert revenue == 5000.0, f"Revenue not properly recorded: {revenue}"
    assert expenses == 2000.0, f"Expense not properly recorded: {expenses}"
    print("✅ Revenue and expense tracking working correctly")
    
    conn.close()
    os.remove('test_accounting.db')

def test_4_balance_sheet_accuracy():
    """Test: Balance sheet reports accurate financial position"""
    print("Testing Balance Sheet Accuracy...")
    
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    test_suite = AccountingTestSuite()
    test_suite.setup_chart_of_accounts(conn)
    
    # Set up test data
    add_journal_entry(conn, 'Owner investment', [
        ('1000', 15000.0, True),   # Debit Cash
        ('3000', 15000.0, False),  # Credit Owner Equity
    ])
    
    add_journal_entry(conn, 'Purchase equipment', [
        ('1300', 8000.0, True),    # Debit Equipment
        ('1000', 8000.0, False),   # Credit Cash
    ])
    
    # Generate balance sheet
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    
    bs = balance_sheet(chart)
    
    # Verify balance sheet components
    total_assets = sum(bs['assets'].values())
    total_liabilities = sum(bs['liabilities'].values())
    total_equity = sum(bs['equity'].values())
    
    assert total_assets == 15000.0, f"Total assets incorrect: {total_assets}"
    assert total_equity == 15000.0, f"Total equity incorrect: {total_equity}"
    assert abs(total_assets - (total_liabilities + total_equity)) < 0.01, "Balance sheet not balanced"
    print("✅ Balance sheet accuracy validated")
    
    conn.close()
    os.remove('test_accounting.db')

def test_5_income_statement_accuracy():
    """Test: Income statement reports accurate profit/loss"""
    print("Testing Income Statement Accuracy...")
    
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    test_suite = AccountingTestSuite()
    test_suite.setup_chart_of_accounts(conn)
    
    # Set up test data
    add_journal_entry(conn, 'Sales revenue', [
        ('1000', 10000.0, True),   # Debit Cash
        ('4000', 10000.0, False),  # Credit Sales Revenue
    ])
    
    add_journal_entry(conn, 'Cost of goods sold', [
        ('5000', 6000.0, True),    # Debit COGS
        ('1000', 6000.0, False),   # Credit Cash
    ])
    
    add_journal_entry(conn, 'Operating expenses', [
        ('5100', 2000.0, True),    # Debit Rent Expense
        ('1000', 2000.0, False),   # Credit Cash
    ])
    
    # Generate income statement
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    
    is_report = income_statement(chart)
    
    # Verify income statement
    total_revenue = sum(is_report['revenues'].values())
    total_expenses = sum(is_report['expenses'].values())
    net_income = is_report['net_income']
    
    assert total_revenue == 10000.0, f"Revenue incorrect: {total_revenue}"
    assert total_expenses == 8000.0, f"Expenses incorrect: {total_expenses}"
    assert net_income == 2000.0, f"Net income incorrect: {net_income}"
    print("✅ Income statement accuracy validated")
    
    conn.close()
    os.remove('test_accounting.db')

def test_6_real_world_business_scenario():
    """Test: Complete business cycle scenario"""
    print("Testing Real-World Business Scenario...")
    
    if os.path.exists('test_accounting.db'):
        os.remove('test_accounting.db')
    
    conn = get_connection('test_accounting.db')
    init_db(conn)
    
    test_suite = AccountingTestSuite()
    test_suite.setup_chart_of_accounts(conn)
    
    # 1. Owner invests $50,000
    add_journal_entry(conn, 'Owner investment', [
        ('1000', 50000.0, True),   # Debit Cash
        ('3000', 50000.0, False),  # Credit Owner Equity
    ])
    
    # 2. Purchase equipment for $20,000
    add_journal_entry(conn, 'Purchase equipment', [
        ('1300', 20000.0, True),   # Debit Equipment
        ('1000', 20000.0, False),  # Credit Cash
    ])
    
    # 3. Purchase inventory on credit $15,000
    add_journal_entry(conn, 'Purchase inventory on credit', [
        ('1200', 15000.0, True),   # Debit Inventory
        ('2000', 15000.0, False),  # Credit Accounts Payable
    ])
    
    # 4. Sell inventory for $25,000 cash
    add_journal_entry(conn, 'Sale of inventory', [
        ('1000', 25000.0, True),   # Debit Cash
        ('4000', 25000.0, False),  # Credit Sales Revenue
    ])
    
    # 5. Record cost of goods sold $12,000
    add_journal_entry(conn, 'Cost of goods sold', [
        ('5000', 12000.0, True),   # Debit COGS
        ('1200', 12000.0, False),  # Credit Inventory
    ])
    
    # 6. Pay rent $3,000
    add_journal_entry(conn, 'Pay rent', [
        ('5100', 3000.0, True),    # Debit Rent Expense
        ('1000', 3000.0, False),   # Credit Cash
    ])
    
    # 7. Pay salaries $8,000
    add_journal_entry(conn, 'Pay salaries', [
        ('5300', 8000.0, True),    # Debit Salaries Expense
        ('1000', 8000.0, False),   # Credit Cash
    ])

    # Check net income before closing
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    is_report = income_statement(chart)
    net_income = is_report['net_income']
    expected_net_income = 25000 - 12000 - 3000 - 8000  # Revenue - COGS - Rent - Salaries
    assert net_income == expected_net_income, f"Net income incorrect before closing: {net_income}, expected: {expected_net_income}"
    print(f"Net income before closing: {net_income}")

    # Closing entry: close revenues and expenses to Retained Earnings
    add_journal_entry(conn, 'Close income statement to retained earnings', [
        ('4000', 25000.0, True),    # Debit Sales Revenue
        ('5000', 12000.0, False),   # Credit COGS
        ('5100', 3000.0, False),    # Credit Rent Expense
        ('5300', 8000.0, False),    # Credit Salaries Expense
        ('3100', 2000.0, False),    # Credit Retained Earnings (net income)
    ])

    # Verify final financial position after closing
    chart = ChartOfAccounts()
    for code, name, type_str, balance in list_accounts(conn):
        chart.add_account(code, name, AccountType[type_str])
        chart.accounts[code].balance = balance
    bs = balance_sheet(chart)
    is_report = income_statement(chart)

    # Print all account balances for debugging
    print("\nAccount Balances after closing:")
    for code, name, type_str, balance in list_accounts(conn):
        print(f"{code} | {name} | {type_str} | {balance}")

    # Verify accounting equation still holds
    total_assets = sum(bs['assets'].values())
    total_liabilities = sum(bs['liabilities'].values())
    total_equity = sum(bs['equity'].values())
    print(f"\nTotals: Assets={total_assets}, Liabilities={total_liabilities}, Equity={total_equity}")
    print(f"Assets - (Liabilities + Equity) = {total_assets - (total_liabilities + total_equity)}")
    assert abs(total_assets - (total_liabilities + total_equity)) < 0.01, "Accounting equation violated"

    # After closing, net income should be 0
    net_income_after = is_report['net_income']
    assert net_income_after == 0.0, f"Net income after closing should be 0, got {net_income_after}"
    # Retained Earnings should be 2000
    retained_earnings = chart.accounts['3100'].balance
    assert retained_earnings == 2000.0, f"Retained Earnings should be 2000, got {retained_earnings}"

    print("✅ Real-world business scenario validated")
    
    conn.close()
    os.remove('test_accounting.db')

def run_accounting_tests():
    """Run all accounting tests"""
    print("🧮 Running Professional Accounting Test Suite for PyLedger")
    print("=" * 60)
    
    tests = [
        test_1_accounting_equation,
        test_2_double_entry_validation,
        test_3_revenue_and_expense_tracking,
        test_4_balance_sheet_accuracy,
        test_5_income_statement_accuracy,
        test_6_real_world_business_scenario
    ]
    
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__} PASSED")
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
    
    print("=" * 60)
    print("🎉 Accounting test suite completed!")

if __name__ == "__main__":
    run_accounting_tests() 