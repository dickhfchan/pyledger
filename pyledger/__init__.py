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

# AI-Native modules are imported lazily so that core accounting works
# without the optional (heavy) AI dependencies installed. Install with:
#   pip install "pyledger[ai]"
_AI_EXPORTS = {
    "ACCOUNTING_TOOLS": "pyledger.llm_tools",
    "get_tools_for_provider": "pyledger.llm_tools",
    "AccountingVectorStore": "pyledger.vector_store",
    "TransactionEmbedder": "pyledger.vector_store",
    "AccountingAgent": "pyledger.agent",
    "AgentContext": "pyledger.agent",
    "create_agent": "pyledger.agent",
}


def __getattr__(name):
    """Lazily import AI-native symbols on first access (PEP 562)."""
    module_path = _AI_EXPORTS.get(name)
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
]