import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp import ServerSession, StdioServerParameters
from mcp.types import (
    CallToolRequest, CallToolResult, ListToolsRequest, ListToolsResult,
    Tool, TextContent, ImageContent, EmbeddedResource
)
from pyledger.db import (
    get_connection, init_db, add_account, list_accounts, add_journal_entry, 
    list_journal_entries, get_journal_lines,
    add_invoice, get_invoice, list_invoices, get_invoice_lines, update_invoice_payment,
    add_purchase_order, get_purchase_order, list_purchase_orders, get_purchase_order_lines, update_purchase_order_receipt
)
from pyledger.accounts import AccountType
from pyledger.reports import balance_sheet, income_statement, cash_flow_report

# Initialize database on startup
conn = get_connection()
init_db(conn)
conn.close()

class PyLedgerMCPServer:
    def __init__(self):
        self.tools = [
            Tool(
                name="list_accounts",
                description="List all accounts in the accounting system",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="add_account",
                description="Add a new account to the chart of accounts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Account code (e.g., '1000')"},
                        "name": {"type": "string", "description": "Account name (e.g., 'Cash')"},
                        "type": {"type": "string", "description": "Account type: ASSET, LIABILITY, EQUITY, REVENUE, or EXPENSE"}
                    },
                    "required": ["code", "name", "type"]
                }
            ),
            Tool(
                name="add_journal_entry",
                description="Add a new journal entry with balanced debits and credits",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Description of the journal entry"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "account_code": {"type": "string", "description": "Account code to debit/credit"},
                                    "amount": {"type": "number", "description": "Amount to debit/credit"},
                                    "is_debit": {"type": "boolean", "description": "True for debit, False for credit"}
                                },
                                "required": ["account_code", "amount", "is_debit"]
                            },
                            "description": "List of journal lines (must balance)"
                        }
                    },
                    "required": ["description", "lines"]
                }
            ),
            Tool(
                name="list_journal_entries",
                description="List all journal entries in the system",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_journal_lines",
                description="Get the lines for a specific journal entry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entry_id": {"type": "integer", "description": "Journal entry ID"}
                    },
                    "required": ["entry_id"]
                }
            ),
            Tool(
                name="balance_sheet",
                description="Generate a balance sheet report",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="income_statement",
                description="Generate an income statement report",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="cash_flow_report",
                description="Generate a cash flow report",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            # Invoice tools
            Tool(
                name="add_invoice",
                description="Add a new invoice to the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string", "description": "Invoice number"},
                        "customer_name": {"type": "string", "description": "Customer name"},
                        "customer_address": {"type": "string", "description": "Customer address"},
                        "issue_date": {"type": "string", "description": "Issue date (YYYY-MM-DD)"},
                        "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                        "notes": {"type": "string", "description": "Optional notes"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string", "description": "Item description"},
                                    "quantity": {"type": "number", "description": "Quantity"},
                                    "unit_price": {"type": "number", "description": "Unit price"},
                                    "tax_rate": {"type": "number", "description": "Tax rate (0.0-1.0)"}
                                },
                                "required": ["description", "quantity", "unit_price"]
                            },
                            "description": "List of invoice line items"
                        }
                    },
                    "required": ["invoice_number", "customer_name", "customer_address", "issue_date", "due_date", "lines"]
                }
            ),
            Tool(
                name="list_invoices",
                description="List all invoices in the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Optional status filter"}
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_invoice",
                description="Get details for a specific invoice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string", "description": "Invoice number"}
                    },
                    "required": ["invoice_number"]
                }
            ),
            Tool(
                name="record_invoice_payment",
                description="Record a payment for an invoice",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string", "description": "Invoice number"},
                        "paid_amount": {"type": "number", "description": "Amount paid"},
                        "paid_date": {"type": "string", "description": "Payment date (YYYY-MM-DD)"}
                    },
                    "required": ["invoice_number", "paid_amount"]
                }
            ),
            Tool(
                name="generate_invoice_pdf",
                description="Generate a PDF invoice in A4 format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "invoice_number": {"type": "string", "description": "Invoice number"},
                        "company_info": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Company name"},
                                "address": {"type": "string", "description": "Company address"},
                                "phone": {"type": "string", "description": "Company phone"},
                                "email": {"type": "string", "description": "Company email"},
                                "website": {"type": "string", "description": "Company website"}
                            },
                            "description": "Optional company information for the PDF header"
                        }
                    },
                    "required": ["invoice_number"]
                }
            ),
            # Purchase order tools
            Tool(
                name="add_purchase_order",
                description="Add a new purchase order to the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Purchase order number"},
                        "supplier_name": {"type": "string", "description": "Supplier name"},
                        "supplier_address": {"type": "string", "description": "Supplier address"},
                        "order_date": {"type": "string", "description": "Order date (YYYY-MM-DD)"},
                        "expected_delivery_date": {"type": "string", "description": "Expected delivery date (YYYY-MM-DD)"},
                        "notes": {"type": "string", "description": "Optional notes"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string", "description": "Item description"},
                                    "quantity": {"type": "number", "description": "Quantity"},
                                    "unit_price": {"type": "number", "description": "Unit price"},
                                    "tax_rate": {"type": "number", "description": "Tax rate (0.0-1.0)"}
                                },
                                "required": ["description", "quantity", "unit_price"]
                            },
                            "description": "List of purchase order line items"
                        }
                    },
                    "required": ["po_number", "supplier_name", "supplier_address", "order_date", "expected_delivery_date", "lines"]
                }
            ),
            Tool(
                name="list_purchase_orders",
                description="List all purchase orders in the system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Optional status filter"}
                    },
                    "required": []
                }
            ),
            Tool(
                name="get_purchase_order",
                description="Get details for a specific purchase order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Purchase order number"}
                    },
                    "required": ["po_number"]
                }
            ),
            Tool(
                name="record_purchase_order_receipt",
                description="Record receipt of items for a purchase order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "po_number": {"type": "string", "description": "Purchase order number"},
                        "line_id": {"type": "integer", "description": "Line ID to update"},
                        "received_quantity": {"type": "number", "description": "Quantity received"},
                        "received_date": {"type": "string", "description": "Receipt date (YYYY-MM-DD)"}
                    },
                    "required": ["po_number", "line_id", "received_quantity"]
                }
            )
        ]

    async def handle_list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        return ListToolsResult(tools=self.tools)

    async def handle_call_tool(self, request: CallToolRequest) -> CallToolResult:
        tool_name = request.params.name
        args = request.params.arguments

        try:
            if tool_name == "list_accounts":
                conn = get_connection()
                accounts = list_accounts(conn)
                conn.close()
                
                result = []
                for code, name, type_str, balance in accounts:
                    result.append({
                        "code": code,
                        "name": name,
                        "type": type_str,
                        "balance": balance
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "add_account":
                conn = get_connection()
                code = args["code"]
                name = args["name"]
                type_str = args["type"].upper()
                
                if type_str not in [t.name for t in AccountType]:
                    raise ValueError(f"Invalid account type: {type_str}")
                
                add_account(conn, code, name, AccountType[type_str])
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Account {code} ({name}) added successfully")]
                )

            elif tool_name == "add_journal_entry":
                conn = get_connection()
                description = args["description"]
                lines_data = args["lines"]
                
                # Validate balance
                total_debits = sum(line["amount"] for line in lines_data if line["is_debit"])
                total_credits = sum(line["amount"] for line in lines_data if not line["is_debit"])
                
                if abs(total_debits - total_credits) > 1e-6:
                    raise ValueError("Journal entry is not balanced")
                
                lines = [(line["account_code"], line["amount"], line["is_debit"]) for line in lines_data]
                entry_id = add_journal_entry(conn, description, lines)
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Journal entry {entry_id} added successfully")]
                )

            elif tool_name == "list_journal_entries":
                conn = get_connection()
                entries = list_journal_entries(conn)
                conn.close()
                
                result = []
                for entry_id, description, date in entries:
                    result.append({
                        "id": entry_id,
                        "description": description,
                        "date": date
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "get_journal_lines":
                conn = get_connection()
                entry_id = args["entry_id"]
                lines = get_journal_lines(conn, entry_id)
                conn.close()
                
                result = []
                for line_id, account_code, amount, is_debit in lines:
                    result.append({
                        "id": line_id,
                        "account_code": account_code,
                        "amount": amount,
                        "is_debit": is_debit
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "balance_sheet":
                conn = get_connection()
                from pyledger.accounts import ChartOfAccounts
                chart = ChartOfAccounts()
                for code, name, type_str, balance in list_accounts(conn):
                    chart.add_account(code, name, AccountType[type_str])
                    chart.accounts[code].balance = balance
                conn.close()
                
                report = balance_sheet(chart)
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(report, indent=2))]
                )

            elif tool_name == "income_statement":
                conn = get_connection()
                from pyledger.accounts import ChartOfAccounts
                chart = ChartOfAccounts()
                for code, name, type_str, balance in list_accounts(conn):
                    chart.add_account(code, name, AccountType[type_str])
                    chart.accounts[code].balance = balance
                conn.close()
                
                report = income_statement(chart)
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(report, indent=2))]
                )

            elif tool_name == "cash_flow_report":
                conn = get_connection()
                from pyledger.accounts import ChartOfAccounts
                chart = ChartOfAccounts()
                for code, name, type_str, balance in list_accounts(conn):
                    chart.add_account(code, name, AccountType[type_str])
                    chart.accounts[code].balance = balance
                conn.close()
                
                report = cash_flow_report(chart)
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(report, indent=2))]
                )

            # Invoice tools
            elif tool_name == "add_invoice":
                conn = get_connection()
                invoice_number = args["invoice_number"]
                customer_name = args["customer_name"]
                customer_address = args["customer_address"]
                issue_date = args["issue_date"]
                due_date = args["due_date"]
                notes = args.get("notes", "")
                lines_data = args["lines"]
                
                lines = [(line["description"], line["quantity"], line["unit_price"], line.get("tax_rate", 0.0)) 
                        for line in lines_data]
                
                add_invoice(conn, invoice_number, customer_name, customer_address, issue_date, due_date, "Draft", notes, lines)
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Invoice {invoice_number} added successfully")]
                )

            elif tool_name == "list_invoices":
                conn = get_connection()
                status = args.get("status")
                invoices = list_invoices(conn, status)
                conn.close()
                
                result = []
                for row in invoices:
                    result.append({
                        "invoice_number": row[0],
                        "customer_name": row[1],
                        "customer_address": row[2],
                        "issue_date": row[3],
                        "due_date": row[4],
                        "status": row[5],
                        "notes": row[6],
                        "subtotal": row[7],
                        "total_tax": row[8],
                        "total_amount": row[9],
                        "paid_amount": row[10],
                        "paid_date": row[11]
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "get_invoice":
                conn = get_connection()
                invoice_number = args["invoice_number"]
                row = get_invoice(conn, invoice_number)
                conn.close()
                
                if not row:
                    raise ValueError(f"Invoice {invoice_number} not found")
                
                result = {
                    "invoice_number": row[0],
                    "customer_name": row[1],
                    "customer_address": row[2],
                    "issue_date": row[3],
                    "due_date": row[4],
                    "status": row[5],
                    "notes": row[6],
                    "subtotal": row[7],
                    "total_tax": row[8],
                    "total_amount": row[9],
                    "paid_amount": row[10],
                    "paid_date": row[11]
                }
                
                # Get invoice lines
                conn = get_connection()
                lines = get_invoice_lines(conn, invoice_number)
                conn.close()
                
                result["lines"] = []
                for line_row in lines:
                    result["lines"].append({
                        "id": line_row[0],
                        "description": line_row[1],
                        "quantity": line_row[2],
                        "unit_price": line_row[3],
                        "tax_rate": line_row[4],
                        "subtotal": line_row[5],
                        "tax_amount": line_row[6],
                        "total": line_row[7]
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "record_invoice_payment":
                conn = get_connection()
                invoice_number = args["invoice_number"]
                paid_amount = args["paid_amount"]
                paid_date = args.get("paid_date", "")
                
                update_invoice_payment(conn, invoice_number, paid_amount, paid_date)
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Payment of ${paid_amount} recorded for invoice {invoice_number}")]
                )

            elif tool_name == "generate_invoice_pdf":
                from datetime import date
                from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus
                
                conn = get_connection()
                invoice_number = args["invoice_number"]
                company_info = args.get("company_info")
                
                try:
                    # Get invoice data
                    invoice_data = get_invoice(conn, invoice_number)
                    if not invoice_data:
                        raise ValueError(f"Invoice {invoice_number} not found")
                        
                    lines_data = get_invoice_lines(conn, invoice_number)
                    
                    # Create Invoice object
                    lines = [InvoiceLine(
                        description=line[1],  # description is at index 1
                        quantity=line[2],     # quantity is at index 2
                        unit_price=line[3],   # unit_price is at index 3
                        tax_rate=line[4]      # tax_rate is at index 4
                    ) for line in lines_data]
                    
                    invoice = Invoice(
                        invoice_number=invoice_data[0],      # invoice_number is at index 0
                        customer_name=invoice_data[1],       # customer_name is at index 1
                        customer_address=invoice_data[2],    # customer_address is at index 2
                        issue_date=date.fromisoformat(invoice_data[3]),  # issue_date is at index 3
                        due_date=date.fromisoformat(invoice_data[4]),    # due_date is at index 4
                        lines=lines,
                        status=InvoiceStatus(invoice_data[5]),  # status is at index 5
                        notes=invoice_data[6]                   # notes is at index 6
                    )
                    invoice.paid_amount = invoice_data[10]    # paid_amount is at index 10
                    if invoice_data[11]:                      # paid_date is at index 11
                        invoice.paid_date = date.fromisoformat(invoice_data[11])
                    
                    # Generate PDF
                    pdf_path = invoice.generate_pdf(company_info=company_info)
                    
                    result = {
                        "message": "PDF generated successfully",
                        "pdf_path": pdf_path,
                        "invoice_number": invoice_number
                    }
                    
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                    )
                    
                except Exception as e:
                    raise ValueError(f"Error generating PDF: {e}")
                finally:
                    conn.close()

            # Purchase order tools
            elif tool_name == "add_purchase_order":
                conn = get_connection()
                po_number = args["po_number"]
                supplier_name = args["supplier_name"]
                supplier_address = args["supplier_address"]
                order_date = args["order_date"]
                expected_delivery_date = args["expected_delivery_date"]
                notes = args.get("notes", "")
                lines_data = args["lines"]
                
                lines = [(line["description"], line["quantity"], line["unit_price"], line.get("tax_rate", 0.0)) 
                        for line in lines_data]
                
                add_purchase_order(conn, po_number, supplier_name, supplier_address, order_date, expected_delivery_date, "Draft", notes, lines)
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Purchase order {po_number} added successfully")]
                )

            elif tool_name == "list_purchase_orders":
                conn = get_connection()
                status = args.get("status")
                purchase_orders = list_purchase_orders(conn, status)
                conn.close()
                
                result = []
                for row in purchase_orders:
                    result.append({
                        "po_number": row[0],
                        "supplier_name": row[1],
                        "supplier_address": row[2],
                        "order_date": row[3],
                        "expected_delivery_date": row[4],
                        "status": row[5],
                        "notes": row[6],
                        "subtotal": row[7],
                        "total_tax": row[8],
                        "total_amount": row[9],
                        "received_subtotal": row[10],
                        "received_tax": row[11],
                        "received_total": row[12],
                        "received_date": row[13]
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "get_purchase_order":
                conn = get_connection()
                po_number = args["po_number"]
                row = get_purchase_order(conn, po_number)
                conn.close()
                
                if not row:
                    raise ValueError(f"Purchase order {po_number} not found")
                
                result = {
                    "po_number": row[0],
                    "supplier_name": row[1],
                    "supplier_address": row[2],
                    "order_date": row[3],
                    "expected_delivery_date": row[4],
                    "status": row[5],
                    "notes": row[6],
                    "subtotal": row[7],
                    "total_tax": row[8],
                    "total_amount": row[9],
                    "received_subtotal": row[10],
                    "received_tax": row[11],
                    "received_total": row[12],
                    "received_date": row[13]
                }
                
                # Get purchase order lines
                conn = get_connection()
                lines = get_purchase_order_lines(conn, po_number)
                conn.close()
                
                result["lines"] = []
                for line_row in lines:
                    result["lines"].append({
                        "id": line_row[0],
                        "description": line_row[1],
                        "quantity": line_row[2],
                        "unit_price": line_row[3],
                        "tax_rate": line_row[4],
                        "received_quantity": line_row[5],
                        "subtotal": line_row[6],
                        "tax_amount": line_row[7],
                        "total": line_row[8],
                        "received_subtotal": line_row[9],
                        "received_tax_amount": line_row[10],
                        "received_total": line_row[11]
                    })
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )

            elif tool_name == "record_purchase_order_receipt":
                conn = get_connection()
                po_number = args["po_number"]
                line_id = args["line_id"]
                received_quantity = args["received_quantity"]
                received_date = args.get("received_date", "")
                
                update_purchase_order_receipt(conn, po_number, line_id, received_quantity, received_date)
                conn.close()
                
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Receipt of {received_quantity} items recorded for purchase order {po_number}")]
                )

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")]
            )

async def main():
    server = PyLedgerMCPServer()
    params = StdioServerParameters(
        name="pyledger",
        version="1.0.0"
    )
    
    async with ServerSession(params) as session:
        session.set_list_tools_handler(server.handle_list_tools)
        session.set_call_tool_handler(server.handle_call_tool)
        await session.run()

if __name__ == "__main__":
    asyncio.run(main()) 