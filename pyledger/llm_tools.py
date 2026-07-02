"""
LLM Function Calling Tools for PyLedger
Provides OpenAI/Anthropic compatible tool definitions for accounting operations.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class JournalLineIn(BaseModel):
    account_code: str = Field(description="Account code to debit/credit")
    amount: float = Field(description="Amount to debit/credit")
    is_debit: bool = Field(description="True for debit, False for credit")


class CreateJournalEntryParams(BaseModel):
    description: str = Field(description="Description of the journal entry")
    lines: List[JournalLineIn] = Field(description="List of journal lines (must balance)")


class QueryFinancialsParams(BaseModel):
    question: str = Field(description="Natural language question about financial data")
    period: Optional[str] = Field(default="YTD", description="Period: MTD, QTD, YTD, or custom")


class ReconcileBankStatementParams(BaseModel):
    bank_statement_path: str = Field(description="Path to bank statement PDF/CSV")
    account_code: str = Field(description="Cash/bank account code to reconcile")


class ListAccountsParams(BaseModel):
    account_type: Optional[str] = Field(default=None, description="Filter by type: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE")


class GetAccountBalanceParams(BaseModel):
    account_code: str = Field(description="Account code to get balance for")
    as_of_date: Optional[str] = Field(default=None, description="Date for balance (YYYY-MM-DD)")


class CreateInvoiceParams(BaseModel):
    invoice_number: str = Field(description="Unique invoice number")
    customer_name: str = Field(description="Customer name")
    customer_address: str = Field(description="Customer address")
    issue_date: str = Field(description="Issue date (YYYY-MM-DD)")
    due_date: str = Field(description="Due date (YYYY-MM-DD)")
    lines: List[Dict[str, Any]] = Field(description="Invoice lines: description, quantity, unit_price, tax_rate")
    notes: str = Field(default="", description="Optional notes")


class RecordPaymentParams(BaseModel):
    invoice_number: str = Field(description="Invoice number")
    paid_amount: float = Field(description="Amount paid")
    paid_date: Optional[str] = Field(default=None, description="Payment date (YYYY-MM-DD)")


class GenerateReportParams(BaseModel):
    report_type: str = Field(description="Report type: balance_sheet, income_statement, cash_flow")
    as_of_date: Optional[str] = Field(default=None, description="Report date (YYYY-MM-DD)")


class AgingReportParams(BaseModel):
    schedule_type: str = Field(description="receivable or payable")
    report_date: Optional[str] = Field(default=None, description="Report date (YYYY-MM-DD)")


class SearchTransactionsParams(BaseModel):
    query: str = Field(description="Natural language search query")
    limit: int = Field(default=10, description="Maximum results")


class SuggestAccountMappingParams(BaseModel):
    transaction_description: str = Field(description="Description of the transaction")
    amount: float = Field(description="Transaction amount")


ACCOUNTING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_journal_entry",
            "description": "Create a balanced journal entry in the accounting system. Debits must equal credits.",
            "parameters": CreateJournalEntryParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_financials",
            "description": "Query financial data using natural language. Returns structured financial information.",
            "parameters": QueryFinancialsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reconcile_bank_statement",
            "description": "AI-powered bank reconciliation. Matches bank statement transactions to ledger entries.",
            "parameters": ReconcileBankStatementParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_accounts",
            "description": "List all accounts in the chart of accounts, optionally filtered by type.",
            "parameters": ListAccountsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_balance",
            "description": "Get the current balance of a specific account.",
            "parameters": GetAccountBalanceParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_invoice",
            "description": "Create a new invoice with line items.",
            "parameters": CreateInvoiceParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_invoice_payment",
            "description": "Record a payment against an invoice.",
            "parameters": RecordPaymentParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_financial_report",
            "description": "Generate a financial report (balance sheet, income statement, or cash flow).",
            "parameters": GenerateReportParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_aging_report",
            "description": "Generate an aging report for receivables or payables.",
            "parameters": AgingReportParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_transactions",
            "description": "Semantic search for transactions using natural language.",
            "parameters": SearchTransactionsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_account_mapping",
            "description": "AI-suggested account codes for a transaction based on description and amount.",
            "parameters": SuggestAccountMappingParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_gaap_compliance",
            "description": "Validate GAAP compliance for a specific transaction or period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_type": {"type": "string", "enum": ["revenue_recognition", "expense_matching", "materiality", "consistency", "conservatism", "going_concern"]},
                    "entity_id": {"type": "string", "description": "Optional entity ID"},
                    "period": {"type": "string", "description": "Period to check (e.g., 2024-Q1)"}
                },
                "required": ["check_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_audit_trail",
            "description": "Get GAAP/IFRS audit trail entries for a period or principle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "principle": {"type": "string", "description": "Optional principle filter"},
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "default": 50}
                }
            }
        }
    }
]


def get_tools_for_provider(provider: str = "openai") -> List[Dict[str, Any]]:
    """Get tools formatted for specific LLM provider."""
    if provider.lower() in ["openai", "azure"]:
        return ACCOUNTING_TOOLS
    elif provider.lower() == "anthropic":
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"]
            }
            for tool in ACCOUNTING_TOOLS
        ]
    else:
        return ACCOUNTING_TOOLS