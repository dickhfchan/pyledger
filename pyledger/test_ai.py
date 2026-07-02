#!/usr/bin/env python3
"""
Test script for AI-native PyLedger modules.
Run with: python -m pyledger.test_ai
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyledger.llm_tools import ACCOUNTING_TOOLS, get_tools_for_provider
from pyledger.vector_store import AccountingVectorStore
from pyledger.agent import AccountingAgent


def test_llm_tools():
    """Test LLM function calling tools."""
    print("🧪 Testing LLM Tools...")
    
    # Test OpenAI format
    openai_tools = get_tools_for_provider("openai")
    assert len(openai_tools) == len(ACCOUNTING_TOOLS)
    assert openai_tools[0]["type"] == "function"
    assert "create_journal_entry" in [t["function"]["name"] for t in openai_tools]
    print("  ✅ OpenAI format tools valid")
    
    # Test Anthropic format
    anthropic_tools = get_tools_for_provider("anthropic")
    assert len(anthropic_tools) == len(ACCOUNTING_TOOLS)
    assert "create_journal_entry" in [t["name"] for t in anthropic_tools]
    print("  ✅ Anthropic format tools valid")
    
    # Verify key tools exist
    tool_names = [t["function"]["name"] for t in openai_tools]
    expected_tools = [
        "create_journal_entry", "query_financials", "reconcile_bank_statement",
        "list_accounts", "get_account_balance", "create_invoice",
        "record_invoice_payment", "generate_financial_report",
        "generate_aging_report", "search_transactions",
        "suggest_account_mapping", "validate_gaap_compliance", "get_audit_trail"
    ]
    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"
    print(f"  ✅ All {len(expected_tools)} expected tools present")


def test_vector_store():
    """Test vector store initialization."""
    print("\n🧪 Testing Vector Store...")
    
    # Use temp directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        vector_store = AccountingVectorStore(db_path=tmpdir)
        
        # Test indexing a journal entry
        vector_store.index_journal_entry(
            entry_id=1,
            description="Test entry for office supplies",
            lines=[
                {"account_code": "5000", "amount": 100.0, "is_debit": True, "narration": "Office supplies"},
                {"account_code": "1000", "amount": 100.0, "is_debit": False, "narration": "Cash payment"}
            ],
            entry_date="2024-01-15"
        )
        
        # Test semantic search
        results = vector_store.semantic_search("office supplies payment", n_results=5)
        assert len(results) == 1
        assert results[0]["metadata"]["entry_id"] == 1
        print("  ✅ Journal entry indexing and search works")
        
        # Test invoice indexing
        vector_store.index_invoice(
            invoice_number="INV-001",
            customer_name="Acme Corp",
            customer_address="123 Main St",
            issue_date="2024-01-10",
            due_date="2024-02-10",
            lines=[{"description": "Consulting", "quantity": 10, "unit_price": 150.0}],
            total_amount=1500.0,
            status="Sent"
        )
        
        results = vector_store.semantic_search("Acme Corp invoice", n_results=5, filter_type="invoice")
        assert len(results) == 1
        assert results[0]["metadata"]["invoice_number"] == "INV-001"
        print("  ✅ Invoice indexing and search works")
        
        # Test account indexing
        vector_store.index_account("1000", "Cash", "ASSET", 5000.0)
        results = vector_store.semantic_search("cash account balance", n_results=5, filter_type="account")
        assert len(results) == 1
        assert results[0]["metadata"]["account_code"] == "1000"
        print("  ✅ Account indexing and search works")
        
        # Test stats
        stats = vector_store.get_collection_stats()
        assert stats["total_documents"] == 3
        assert "journal_entry" in stats["type_distribution"]
        assert "invoice" in stats["type_distribution"]
        assert "account" in stats["type_distribution"]
        print("  ✅ Collection stats work")


def test_agent_initialization():
    """Test agent can be created."""
    print("\n🧪 Testing Agent Initialization...")
    
    # This will fail if no database exists, but we can test the import
    agent = AccountingAgent(db_path=":memory:")  # Use in-memory DB
    print("  ✅ Agent imports and initializes correctly")
    
    # Test tool registry
    assert "create_journal_entry" in agent.tools
    assert "query_financials" in agent.tools
    assert "search_transactions" in agent.tools
    print("  ✅ Tool registry populated")


def main():
    """Run all tests."""
    print("=" * 50)
    print("PyLedger AI-Native Module Tests")
    print("=" * 50)
    
    try:
        test_llm_tools()
        test_vector_store()
        test_agent_initialization()
        
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        return 0
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())