from pyledger.accounts import ChartOfAccounts, AccountType

def balance_sheet(chart: ChartOfAccounts) -> dict:
    """
    Returns a dict with assets, liabilities, and equity balances.
    """
    assets = {a.code: a.balance for a in chart.accounts.values() if a.type == AccountType.ASSET}
    liabilities = {a.code: a.balance for a in chart.accounts.values() if a.type == AccountType.LIABILITY}
    equity = {a.code: a.balance for a in chart.accounts.values() if a.type == AccountType.EQUITY}
    return {"assets": assets, "liabilities": liabilities, "equity": equity}

def income_statement(chart: ChartOfAccounts) -> dict:
    """
    Returns a dict with revenues, expenses, and net income.
    """
    revenues = {a.code: a.balance for a in chart.accounts.values() if a.type == AccountType.REVENUE}
    expenses = {a.code: a.balance for a in chart.accounts.values() if a.type == AccountType.EXPENSE}
    net_income = sum(revenues.values()) - sum(expenses.values())
    return {"revenues": revenues, "expenses": expenses, "net_income": net_income}

def cash_flow_report(chart: ChartOfAccounts) -> dict:
    """
    Returns a simple cash flow report (change in cash accounts).
    """
    cash_accounts = {a.code: a.balance for a in chart.accounts.values() if 'cash' in a.name.lower()}
    total_cash = sum(cash_accounts.values())
    return {"cash_accounts": cash_accounts, "total_cash": total_cash}