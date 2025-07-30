from typing import List, Dict
from pyledger.accounts import ChartOfAccounts, AccountType

class JournalLine:
    """
    Represents a single debit or credit in a journal entry.
    """
    def __init__(self, account_code: str, amount: float, is_debit: bool):
        self.account_code = account_code
        self.amount = amount
        self.is_debit = is_debit

    def to_dict(self):
        return {
            'account_code': self.account_code,
            'amount': self.amount,
            'is_debit': self.is_debit
        }

    @staticmethod
    def from_dict(data):
        return JournalLine(
            account_code=data['account_code'],
            amount=data['amount'],
            is_debit=data['is_debit']
        )

class JournalEntry:
    """
    Represents a double-entry accounting journal entry.
    """
    def __init__(self, description: str, lines: List[JournalLine]):
        self.description = description
        self.lines = lines
        if not self.is_balanced():
            raise ValueError("Journal entry is not balanced.")

    def is_balanced(self) -> bool:
        total_debits = sum(line.amount for line in self.lines if line.is_debit)
        total_credits = sum(line.amount for line in self.lines if not line.is_debit)
        return abs(total_debits - total_credits) < 1e-6

    def to_dict(self):
        return {
            'description': self.description,
            'lines': [line.to_dict() for line in self.lines]
        }

    @staticmethod
    def from_dict(data):
        lines = [JournalLine.from_dict(l) for l in data['lines']]
        return JournalEntry(data['description'], lines)

class Ledger:
    """
    Holds all journal entries and updates account balances.
    """
    def __init__(self, chart: ChartOfAccounts):
        self.chart = chart
        self.entries: List[JournalEntry] = []

    def post_entry(self, entry: JournalEntry):
        for line in entry.lines:
            account = self.chart.get_account(line.account_code)
            if line.is_debit:
                if account.type in [AccountType.ASSET, AccountType.EXPENSE]:
                    account.balance += line.amount
                else:
                    account.balance -= line.amount
            else:
                if account.type in [AccountType.ASSET, AccountType.EXPENSE]:
                    account.balance -= line.amount
                else:
                    account.balance += line.amount
        self.entries.append(entry)

    def to_dict(self):
        return {'entries': [entry.to_dict() for entry in self.entries]}

    @staticmethod
    def from_dict(data, chart: ChartOfAccounts):
        ledger = Ledger(chart)
        for entry_data in data.get('entries', []):
            entry = JournalEntry.from_dict(entry_data)
            ledger.post_entry(entry)
        return ledger