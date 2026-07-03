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


# --- Tax filing (Form 5472 / pro-forma 1120) parameter models ---

class RegisterFilingEntityParams(BaseModel):
    name: str = Field(description="Legal name of the US entity (LLC or corporation)")
    entity_kind: str = Field(description="'foreign_owned_de' (single-member LLC) or 'foreign_owned_corporation'")
    address_line1: str = Field(description="Street address")
    city: str = Field(description="City")
    state: Optional[str] = Field(default=None, description="US state, e.g. DE")
    postal_code: Optional[str] = Field(default=None, description="ZIP code")
    ein: Optional[str] = Field(default=None, description="EIN in NN-NNNNNNN format")
    formation_date: Optional[str] = Field(default=None, description="Formation date (YYYY-MM-DD)")
    principal_business_activity: Optional[str] = Field(default=None, description="Principal business activity")


class AddForeignOwnerParams(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    name: str = Field(description="Owner's full legal name")
    country: str = Field(description="Owner's country of residence")
    address_line1: str = Field(description="Owner street address")
    city: str = Field(description="Owner city")
    postal_code: Optional[str] = Field(default=None, description="Postal code")
    us_tin: Optional[str] = Field(default=None, description="US TIN/SSN/ITIN if any")
    foreign_tin: Optional[str] = Field(default=None, description="Foreign tax ID if any")
    ownership_pct: float = Field(default=100.0, description="Ownership percentage")


class CheckFilingRequirementsParams(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    tax_year: int = Field(description="Tax year, e.g. 2025")


class SuggestReportableTransactionsParams(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    tax_year: int = Field(description="Tax year to scan the ledger for")


class RecordReportableTransactionParams(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    tax_year: int = Field(description="Tax year")
    txn_type: str = Field(description="Reportable transaction type, e.g. capital_contribution, distribution, loan_from_owner, service_fees_paid, expenses_paid_by_owner, formation_dissolution_costs")
    amount: float = Field(description="Transaction amount in USD (positive)")
    txn_date: Optional[str] = Field(default=None, description="Transaction date (YYYY-MM-DD)")
    description: Optional[str] = Field(default=None, description="Description")


class ListReportableTransactionsParams(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    tax_year: int = Field(description="Tax year")


class PrepareForm5472Params(BaseModel):
    entity_id: int = Field(description="Filing entity ID")
    tax_year: int = Field(description="Tax year to file for")
    output_dir: str = Field(default="filings", description="Directory to write the PDFs")
    include_extension: bool = Field(default=False, description="Also generate Form 7004 extension")
    reasonable_cause_text: Optional[str] = Field(default=None, description="Reasonable-cause statement text for late filings")


class EstimateFilingPenaltyParams(BaseModel):
    tax_year: int = Field(description="Tax year the filing covers")
    filed_date: Optional[str] = Field(default=None, description="Actual/planned filing date (YYYY-MM-DD)")
    irs_notice_date: Optional[str] = Field(default=None, description="Date of IRS failure-to-file notice, if received (YYYY-MM-DD)")
    num_forms: int = Field(default=1, description="Number of Forms 5472")


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
            "name": "register_filing_entity",
            "description": "Register a US entity (foreign-owned single-member LLC or 25%+ foreign-owned corporation) for IRS Form 5472 tax filing.",
            "parameters": RegisterFilingEntityParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_foreign_owner",
            "description": "Register the foreign owner (25%+ shareholder) of a filing entity for Form 5472 reporting.",
            "parameters": AddForeignOwnerParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_filing_requirements",
            "description": "Check whether IRS Form 5472 + pro-forma 1120 filing is required for an entity and tax year; returns deadline, submission instructions (fax/mail), and penalty exposure.",
            "parameters": CheckFilingRequirementsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_reportable_transactions",
            "description": "Scan the ledger for transactions that look like Form 5472 reportable transactions (capital contributions, distributions, owner loans, etc.).",
            "parameters": SuggestReportableTransactionsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_reportable_transaction",
            "description": "Record a Form 5472 reportable transaction between the entity and its foreign owner.",
            "parameters": RecordReportableTransactionParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reportable_transactions",
            "description": "List recorded Form 5472 reportable transactions for an entity and tax year.",
            "parameters": ListReportableTransactionsParams.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_form_5472",
            "description": "Generate the complete IRS filing package: filled Form 5472, pro-forma Form 1120 with 'Foreign-owned U.S. DE' banner, optional Form 7004 extension, and attachment statements.",
            "parameters": PrepareForm5472Params.model_json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_filing_penalty",
            "description": "Estimate the IRC 6038A penalty exposure for a late or missed Form 5472 filing ($25,000 per form plus continuation penalties).",
            "parameters": EstimateFilingPenaltyParams.model_json_schema()
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