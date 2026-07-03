"""
PyLedger - Professional Double-Entry Accounting System
Now with AI-native capabilities for LLM integration.
"""

from pyledger.accounts import AccountType, Account, ChartOfAccounts
from pyledger.journal import JournalLine, JournalEntry, Ledger
from pyledger.reports import balance_sheet, income_statement, cash_flow_report
from pyledger.db import (
    get_connection, init_db, add_account, list_accounts, add_journal_entry,
    list_journal_entries, get_journal_lines,
    add_invoice, get_invoice, list_invoices, get_invoice_lines, update_invoice_payment,
    add_purchase_order, get_purchase_order, list_purchase_orders, get_purchase_order_lines, update_purchase_order_receipt
)
from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus
from pyledger.purchase_orders import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus
from pyledger.payment_clearing import PaymentClearingManager
from pyledger.gaap_compliance import GAAPCompliance, GAAPPrinciple, RevenueRecognitionMethod
from pyledger.ifrs_compliance import IFRSCompliance, IFRSPrinciple, FairValueLevel, ImpairmentType

# AI-native and tax-filing modules are imported lazily so that core
# accounting works without their optional/heavy dependencies installed.
# AI: pip install "pyledger[ai]"   PDF generation: pypdf + reportlab.
_LAZY_EXPORTS = {
    # AI-native
    "ACCOUNTING_TOOLS": "pyledger.llm_tools",
    "get_tools_for_provider": "pyledger.llm_tools",
    "AccountingVectorStore": "pyledger.vector_store",
    "TransactionEmbedder": "pyledger.vector_store",
    "AccountingAgent": "pyledger.agent",
    "AgentContext": "pyledger.agent",
    "create_agent": "pyledger.agent",
    # Tax filing (IRS Form 5472 / pro-forma 1120)
    "Form5472Filing": "pyledger.tax_filing",
    "ReportableTransactionType": "pyledger.tax_filing",
    "EntityKind": "pyledger.tax_filing",
    "FilingStatus": "pyledger.tax_filing",
    "IRSTemplateManager": "pyledger.irs_pdf",
}


def __getattr__(name: str) -> object:
    """Lazily import optional-module symbols on first access (PEP 562)."""
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is not None:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "1.0.0"

__all__ = [
    # Core accounting
    "AccountType", "Account", "ChartOfAccounts",
    "JournalLine", "JournalEntry", "Ledger",
    "balance_sheet", "income_statement", "cash_flow_report",
    
    # Database
    "get_connection", "init_db", "add_account", "list_accounts",
    "add_journal_entry", "list_journal_entries", "get_journal_lines",
    "add_invoice", "get_invoice", "list_invoices", "get_invoice_lines", "update_invoice_payment",
    "add_purchase_order", "get_purchase_order", "list_purchase_orders", "get_purchase_order_lines", "update_purchase_order_receipt",
    
    # Documents
    "Invoice", "InvoiceLine", "InvoiceStatus",
    "PurchaseOrder", "PurchaseOrderLine", "PurchaseOrderStatus",
    
    # Payment clearing
    "PaymentClearingManager",
    
    # Compliance
    "GAAPCompliance", "GAAPPrinciple", "RevenueRecognitionMethod",
    "IFRSCompliance", "IFRSPrinciple", "FairValueLevel", "ImpairmentType",
    
    # AI-Native
    "ACCOUNTING_TOOLS", "get_tools_for_provider",
    "AccountingVectorStore", "TransactionEmbedder",
    "AccountingAgent", "AgentContext", "create_agent",

    # Tax filing (IRS Form 5472 / pro-forma 1120)
    "Form5472Filing", "ReportableTransactionType", "EntityKind",
    "FilingStatus", "IRSTemplateManager",
]