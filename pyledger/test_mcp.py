import asyncio
import json
import os
from pyledger.mcp_server import PyLedgerMCPServer
from pyledger.db import get_connection, init_db

async def test_mcp_server():
    """Test the MCP server functionality."""
    # Initialize database
    if os.path.exists('pyledger.db'):
        os.remove('pyledger.db')
    conn = get_connection()
    init_db(conn)
    conn.close()
    
    server = PyLedgerMCPServer()
    
    # Test listing tools
    from mcp.types import ListToolsRequest
    tools_result = await server.handle_list_tools(ListToolsRequest(method="tools/list"))
    print("Available tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Test listing accounts
    from mcp.types import CallToolRequest, CallToolResult
    request = CallToolRequest(
        method="tools/call", 
        params={"name": "list_accounts", "arguments": {}}
    )
    result = await server.handle_call_tool(request)
    
    print("\nAccounts in the system:")
    print(result.content[0].text)
    
    # Test adding an account
    print("\n=== Testing Account Management ===")
    add_account_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "add_account",
            "arguments": {
                "code": "1000",
                "name": "Cash",
                "type": "ASSET"
            }
        }
    )
    result = await server.handle_call_tool(add_account_request)
    print("Add account result:", result.content[0].text)
    
    # Test invoice functionality
    print("\n=== Testing Invoice Management ===")
    
    # Add invoice
    add_invoice_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "add_invoice",
            "arguments": {
                "invoice_number": "INV-001",
                "customer_name": "Acme Corp",
                "customer_address": "123 Main St, City, State",
                "issue_date": "2024-01-15",
                "due_date": "2024-02-15",
                "notes": "Test invoice",
                "lines": [
                    {
                        "description": "Web Development Services",
                        "quantity": 40,
                        "unit_price": 100.0,
                        "tax_rate": 0.1
                    },
                    {
                        "description": "Consulting",
                        "quantity": 10,
                        "unit_price": 150.0,
                        "tax_rate": 0.1
                    }
                ]
            }
        }
    )
    result = await server.handle_call_tool(add_invoice_request)
    print("Add invoice result:", result.content[0].text)
    
    # List invoices
    list_invoices_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "list_invoices",
            "arguments": {}
        }
    )
    result = await server.handle_call_tool(list_invoices_request)
    print("\nInvoices in the system:")
    print(result.content[0].text)
    
    # Get specific invoice
    get_invoice_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "get_invoice",
            "arguments": {
                "invoice_number": "INV-001"
            }
        }
    )
    result = await server.handle_call_tool(get_invoice_request)
    print("\nInvoice details:")
    print(result.content[0].text)
    
    # Record invoice payment
    record_payment_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "record_invoice_payment",
            "arguments": {
                "invoice_number": "INV-001",
                "paid_amount": 2000.0,
                "paid_date": "2024-01-20"
            }
        }
    )
    result = await server.handle_call_tool(record_payment_request)
    print("\nPayment recording result:", result.content[0].text)
    
    # Test purchase order functionality
    print("\n=== Testing Purchase Order Management ===")
    
    # Add purchase order
    add_po_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "add_purchase_order",
            "arguments": {
                "po_number": "PO-001",
                "supplier_name": "Office Supplies Co",
                "supplier_address": "456 Business Ave, City, State",
                "order_date": "2024-01-10",
                "expected_delivery_date": "2024-01-20",
                "notes": "Test purchase order",
                "lines": [
                    {
                        "description": "Office Chairs",
                        "quantity": 5,
                        "unit_price": 200.0,
                        "tax_rate": 0.08
                    },
                    {
                        "description": "Desks",
                        "quantity": 3,
                        "unit_price": 300.0,
                        "tax_rate": 0.08
                    }
                ]
            }
        }
    )
    result = await server.handle_call_tool(add_po_request)
    print("Add purchase order result:", result.content[0].text)
    
    # List purchase orders
    list_pos_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "list_purchase_orders",
            "arguments": {}
        }
    )
    result = await server.handle_call_tool(list_pos_request)
    print("\nPurchase orders in the system:")
    print(result.content[0].text)
    
    # Get specific purchase order
    get_po_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "get_purchase_order",
            "arguments": {
                "po_number": "PO-001"
            }
        }
    )
    result = await server.handle_call_tool(get_po_request)
    print("\nPurchase order details:")
    print(result.content[0].text)
    
    # Record purchase order receipt
    record_receipt_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "record_purchase_order_receipt",
            "arguments": {
                "po_number": "PO-001",
                "line_id": 1,
                "received_quantity": 3,
                "received_date": "2024-01-15"
            }
        }
    )
    result = await server.handle_call_tool(record_receipt_request)
    print("\nReceipt recording result:", result.content[0].text)
    
    # Test journal entry functionality
    print("\n=== Testing Journal Entry Management ===")
    
    # Add journal entry
    add_entry_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "add_journal_entry",
            "arguments": {
                "description": "Test journal entry",
                "lines": [
                    {
                        "account_code": "1000",
                        "amount": 1000.0,
                        "is_debit": True
                    },
                    {
                        "account_code": "3000",
                        "amount": 1000.0,
                        "is_debit": False
                    }
                ]
            }
        }
    )
    result = await server.handle_call_tool(add_entry_request)
    print("Add journal entry result:", result.content[0].text)
    
    # List journal entries
    list_entries_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "list_journal_entries",
            "arguments": {}
        }
    )
    result = await server.handle_call_tool(list_entries_request)
    print("\nJournal entries in the system:")
    print(result.content[0].text)
    
    # Test reports
    print("\n=== Testing Reports ===")
    
    # Balance sheet
    balance_sheet_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "balance_sheet",
            "arguments": {}
        }
    )
    result = await server.handle_call_tool(balance_sheet_request)
    print("\nBalance sheet:")
    print(result.content[0].text)
    
    # Income statement
    income_statement_request = CallToolRequest(
        method="tools/call",
        params={
            "name": "income_statement",
            "arguments": {}
        }
    )
    result = await server.handle_call_tool(income_statement_request)
    print("\nIncome statement:")
    print(result.content[0].text)
    
    print("\n🎉 All MCP tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 