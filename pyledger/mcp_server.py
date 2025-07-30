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
    list_journal_entries, get_journal_lines
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