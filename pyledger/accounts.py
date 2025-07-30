from enum import Enum
from typing import Dict

class AccountType(Enum):
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"

class Account:
    """
    Represents an account in the chart of accounts.
    """
    def __init__(self, code: str, name: str, type: AccountType, balance: float = 0.0):
        self.code = code
        self.name = name
        self.type = type
        self.balance = balance

    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'type': self.type.name,
            'balance': self.balance
        }

    @staticmethod
    def from_dict(data):
        return Account(
            code=data['code'],
            name=data['name'],
            type=AccountType[data['type']],
            balance=data.get('balance', 0.0)
        )

class ChartOfAccounts:
    """
    Holds all accounts in the ledger.
    """
    def __init__(self):
        self.accounts: Dict[str, Account] = {}

    def add_account(self, code: str, name: str, type: AccountType):
        if code in self.accounts:
            raise ValueError(f"Account code {code} already exists.")
        self.accounts[code] = Account(code, name, type)

    def get_account(self, code: str) -> Account:
        return self.accounts[code]

    def to_dict(self):
        return {'accounts': [acc.to_dict() for acc in self.accounts.values()]}

    @staticmethod
    def from_dict(data):
        chart = ChartOfAccounts()
        for acc_data in data.get('accounts', []):
            acc = Account.from_dict(acc_data)
            chart.accounts[acc.code] = acc
        return chart