"""
AI Agent for PyLedger - Natural Language Interface
Provides conversational accounting operations using LLMs.
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import date, datetime
import sqlite3

from pyledger.db import get_connection
from pyledger.llm_tools import ACCOUNTING_TOOLS, get_tools_for_provider
from pyledger.vector_store import AccountingVectorStore, TransactionEmbedder


@dataclass
class AgentContext:
    """Context for the accounting agent."""
    entity_id: Optional[str] = None
    user_id: str = "ai_agent"
    session_id: str = ""
    conversation_history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []


class AccountingAgent:
    """
    AI-powered accounting agent with natural language interface.
    Integrates LLM function calling, vector search, and accounting operations.
    """
    
    def __init__(
        self,
        db_path: str = "pyledger.db",
        vector_db_path: str = "./chroma_db",
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o",
        api_key: Optional[str] = None
    ):
        self.db_path = db_path
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        
        # Database connection
        self.conn = get_connection(db_path)
        
        # Vector store for semantic search
        self.vector_store = AccountingVectorStore(db_path=vector_db_path)
        self.embedder = TransactionEmbedder(self.vector_store, self.conn)
        
        # LLM client (initialized lazily)
        self._llm_client = None
        self._api_key = api_key
        
        # Tool registry - maps tool names to handler functions
        self.tools = {
            "create_journal_entry": self._handle_create_journal_entry,
            "query_financials": self._handle_query_financials,
            "reconcile_bank_statement": self._handle_reconcile_bank_statement,
            "list_accounts": self._handle_list_accounts,
            "get_account_balance": self._handle_get_account_balance,
            "create_invoice": self._handle_create_invoice,
            "record_invoice_payment": self._handle_record_invoice_payment,
            "generate_financial_report": self._handle_generate_financial_report,
            "generate_aging_report": self._handle_generate_aging_report,
            "search_transactions": self._handle_search_transactions,
            "suggest_account_mapping": self._handle_suggest_account_mapping,
            "validate_gaap_compliance": self._handle_validate_gaap_compliance,
            "get_audit_trail": self._handle_get_audit_trail,
            # Tax filing (Form 5472 / pro-forma 1120)
            "register_filing_entity": self._handle_register_filing_entity,
            "add_foreign_owner": self._handle_add_foreign_owner,
            "check_filing_requirements": self._handle_check_filing_requirements,
            "suggest_reportable_transactions": self._handle_suggest_reportable_transactions,
            "record_reportable_transaction": self._handle_record_reportable_transaction,
            "list_reportable_transactions": self._handle_list_reportable_transactions,
            "prepare_form_5472": self._handle_prepare_form_5472,
            "estimate_filing_penalty": self._handle_estimate_filing_penalty,
        }
        
        # Context
        self.context = AgentContext()

    @property
    def llm_client(self):
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            if self.llm_provider.lower() in ["openai", "azure"]:
                from openai import OpenAI
                self._llm_client = OpenAI(api_key=self._api_key)
            elif self.llm_provider.lower() == "anthropic":
                from anthropic import Anthropic
                self._llm_client = Anthropic(api_key=self._api_key)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        return self._llm_client

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tool schemas for the current LLM provider."""
        return get_tools_for_provider(self.llm_provider)

    async def process_query(self, query: str, context: Optional[AgentContext] = None) -> Dict[str, Any]:
        """
        Process a natural language query using the LLM with function calling.
        
        Args:
            query: Natural language question or command
            context: Optional agent context
            
        Returns:
            Response with answer and any tool results
        """
        if context:
            self.context = context
        
        # Add to conversation history
        self.context.conversation_history.append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Build system prompt
        system_prompt = self._build_system_prompt()
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (last 10 messages)
        for msg in self.context.conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Call LLM with function calling
        response = await self._call_llm_with_tools(messages)
        
        # Add assistant response to history
        self.context.conversation_history.append({
            "role": "assistant",
            "content": response.get("content", ""),
            "timestamp": datetime.now().isoformat(),
            "tool_calls": response.get("tool_calls", [])
        })
        
        return response

    def _build_system_prompt(self) -> str:
        """Build system prompt with accounting context."""
        # Get current stats
        stats = self.vector_store.get_collection_stats()
        
        return f"""You are an expert AI accounting assistant for PyLedger, a professional double-entry accounting system.

CURRENT SYSTEM STATE:
- Vector store contains: {stats['total_documents']} documents ({stats['type_distribution']})
- Database: {self.db_path}
- Active entity: {self.context.entity_id or 'default'}

YOUR CAPABILITIES:
1. Create and manage journal entries (must balance: debits = credits)
2. Query financial data using natural language
3. Manage invoices, purchase orders, and payments
4. Generate financial reports (balance sheet, income statement, cash flow)
5. Search transactions semantically
6. Validate GAAP/IFRS compliance
7. Perform bank reconciliation
8. Suggest account mappings for transactions

ACCOUNTING RULES:
- All journal entries MUST balance (total debits = total credits)
- Account types: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
- Debits increase Assets/Expenses, decrease Liabilities/Equity/Revenue
- Credits increase Liabilities/Equity/Revenue, decrease Assets/Expenses
- GAAP compliance: Revenue Recognition (ASC 606), Expense Matching, Materiality, Consistency, Conservatism
- IFRS compliance: Fair Value (IFRS 13), Impairment (IAS 36), Revenue (IFRS 15), Leases (IFRS 16)

RESPONSE STYLE:
- Be concise but thorough
- Explain accounting rationale
- Ask clarifying questions when needed
- Provide structured responses with clear next steps
- Reference specific accounts, amounts, and dates"""

    async def _call_llm_with_tools(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Call LLM with function calling support."""
        tools = self.get_tools_schema()
        
        if self.llm_provider.lower() in ["openai", "azure"]:
            return await self._call_openai(messages, tools)
        elif self.llm_provider.lower() == "anthropic":
            return await self._call_anthropic(messages, tools)
        else:
            raise ValueError(f"Unsupported provider: {self.llm_provider}")

    async def _call_openai(self, messages: List[Dict], tools: List[Dict]) -> Dict[str, Any]:
        """Call OpenAI API with function calling."""
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        
        message = response.choices[0].message
        
        result = {
            "content": message.content or "",
            "tool_calls": []
        }
        
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Execute tool
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                result["tool_calls"].append({
                    "name": tool_name,
                    "arguments": tool_args,
                    "result": tool_result
                })
                
                # Add tool result to messages for follow-up
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })
            
            # Get final response after tool execution
            final_response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.1
            )
            result["content"] = final_response.choices[0].message.content or ""
        
        return result

    async def _call_anthropic(self, messages: List[Dict], tools: List[Dict]) -> Dict[str, Any]:
        """Call Anthropic API with tool use."""
        # Convert messages format
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]
        
        response = self.llm_client.messages.create(
            model=self.llm_model,
            system=system_msg,
            messages=user_messages,
            tools=tools,
            temperature=0.1,
            max_tokens=4000
        )
        
        result = {
            "content": "",
            "tool_calls": []
        }
        
        for content_block in response.content:
            if content_block.type == "text":
                result["content"] += content_block.text
            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_args = content_block.input
                
                tool_result = await self._execute_tool(tool_name, tool_args)
                
                result["tool_calls"].append({
                    "name": tool_name,
                    "arguments": tool_args,
                    "result": tool_result
                })
        
        return result

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with arguments."""
        handler = self.tools.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = await handler(args)
            return {"success": True, "data": result}
        except Exception as e:
            return {"error": str(e), "success": False}

    # Tool Handlers
    async def _handle_create_journal_entry(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a journal entry."""
        from pyledger.db import add_journal_entry
        from pyledger.accounts import AccountType
        
        description = args["description"]
        lines = args["lines"]
        
        # Validate balance
        total_debits = sum(line["amount"] for line in lines if line["is_debit"])
        total_credits = sum(line["amount"] for line in lines if not line["is_debit"])
        
        if abs(total_debits - total_credits) > 0.01:
            return {"error": f"Entry not balanced: Debits={total_debits}, Credits={total_credits}"}
        
        # Convert to DB format
        db_lines = [(line["account_code"], line["amount"], line["is_debit"]) for line in lines]
        
        entry_id = add_journal_entry(self.conn, description, db_lines)
        
        # Index in vector store
        self.vector_store.index_journal_entry(
            entry_id=entry_id,
            description=description,
            lines=lines,
            entry_date=date.today().isoformat(),
            entity_id=self.context.entity_id
        )
        
        return {"entry_id": entry_id, "message": "Journal entry created successfully"}

    async def _handle_query_financials(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Query financial data with natural language."""
        question = args["question"]
        period = args.get("period", "YTD")
        
        # Use vector search for relevant transactions
        search_results = self.vector_store.semantic_search(
            query=question,
            n_results=20,
            filter_entity=self.context.entity_id
        )
        
        # Build context from search results
        context = "\n".join([r["document"] for r in search_results[:10]])
        
        # Use LLM to answer based on context
        prompt = f"""Based on the following accounting data, answer: {question}

Period: {period}
Entity: {self.context.entity_id or 'default'}

Relevant Data:
{context}

Provide a clear, accurate answer with specific numbers and account references."""
        
        # Quick LLM call for synthesis
        if self.llm_provider.lower() in ["openai", "azure"]:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            answer = response.choices[0].message.content
        else:
            response = self.llm_client.messages.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            answer = response.content[0].text
        
        return {
            "answer": answer,
            "sources": [r["metadata"] for r in search_results[:5]],
            "period": period
        }

    async def _handle_reconcile_bank_statement(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered bank reconciliation."""
        # This would integrate with document_ai.py for PDF parsing
        # For now, return a structured response
        return {
            "message": "Bank reconciliation requires document AI integration",
            "bank_statement_path": args["bank_statement_path"],
            "account_code": args["account_code"],
            "status": "pending_document_ai"
        }

    async def _handle_list_accounts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List accounts."""
        from pyledger.db import list_accounts
        from pyledger.accounts import AccountType
        
        account_type = args.get("account_type")
        
        accounts = list_accounts(self.conn)
        
        if account_type:
            accounts = [a for a in accounts if a[2] == account_type.upper()]
        
        return {
            "accounts": [
                {"code": a[0], "name": a[1], "type": a[2], "balance": a[3]}
                for a in accounts
            ],
            "count": len(accounts)
        }

    async def _handle_get_account_balance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get account balance."""
        from pyledger.db import get_account
        
        account_code = args["account_code"]
        account = get_account(self.conn, account_code)
        
        if not account:
            return {"error": f"Account {account_code} not found"}
        
        return {
            "account_code": account[0],
            "name": account[1],
            "type": account[2],
            "balance": account[3],
            "as_of_date": args.get("as_of_date", date.today().isoformat())
        }

    async def _handle_create_invoice(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an invoice."""
        from pyledger.db import add_invoice
        
        lines = [(line["description"], line["quantity"], line["unit_price"], line.get("tax_rate", 0.0)) 
                 for line in args["lines"]]
        
        add_invoice(
            self.conn,
            args["invoice_number"],
            args["customer_name"],
            args["customer_address"],
            args["issue_date"],
            args["due_date"],
            "Draft",
            args.get("notes", ""),
            lines
        )
        
        # Index in vector store
        self.vector_store.index_invoice(
            invoice_number=args["invoice_number"],
            customer_name=args["customer_name"],
            customer_address=args["customer_address"],
            issue_date=args["issue_date"],
            due_date=args["due_date"],
            lines=args["lines"],
            total_amount=sum(l["quantity"] * l["unit_price"] * (1 + l.get("tax_rate", 0)) for l in args["lines"]),
            status="Draft",
            entity_id=self.context.entity_id
        )
        
        return {"message": f"Invoice {args['invoice_number']} created successfully"}

    async def _handle_record_invoice_payment(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Record invoice payment."""
        from pyledger.db import update_invoice_payment
        
        paid_date = args.get("paid_date") or date.today().isoformat()
        update_invoice_payment(self.conn, args["invoice_number"], args["paid_amount"], paid_date)
        
        return {"message": f"Payment of ${args['paid_amount']} recorded for invoice {args['invoice_number']}"}

    async def _handle_generate_financial_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate financial report."""
        from pyledger.reports import balance_sheet, income_statement, cash_flow_report
        from pyledger.accounts import ChartOfAccounts, AccountType
        from pyledger.db import list_accounts
        
        report_type = args["report_type"]
        
        # Build chart from database
        chart = ChartOfAccounts()
        for code, name, type_str, balance in list_accounts(self.conn):
            chart.add_account(code, name, AccountType[type_str])
            chart.accounts[code].balance = balance
        
        if report_type == "balance_sheet":
            report = balance_sheet(chart)
        elif report_type == "income_statement":
            report = income_statement(chart)
        elif report_type == "cash_flow":
            report = cash_flow_report(chart)
        else:
            return {"error": f"Unknown report type: {report_type}"}
        
        return {"report_type": report_type, "data": report}

    async def _handle_generate_aging_report(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate aging report."""
        from pyledger.payment_clearing import PaymentClearingManager
        
        manager = PaymentClearingManager(self.db_path)
        report_date = args.get("report_date") or date.today().isoformat()
        
        result = manager.generate_aging_report(
            report_date=report_date,
            schedule_type=args["schedule_type"]
        )
        
        return result

    async def _handle_search_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Semantic search for transactions."""
        query = args["query"]
        limit = args.get("limit", 10)
        
        results = self.vector_store.semantic_search(
            query=query,
            n_results=limit,
            filter_entity=self.context.entity_id
        )
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }

    async def _handle_suggest_account_mapping(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """AI-suggested account mapping for a transaction."""
        description = args["transaction_description"]
        amount = args["amount"]
        
        # Search for similar transactions to inform the suggestion
        similar = self.vector_store.search_similar_transactions(description, amount, n_results=5)

        # Use LLM to suggest accounts based on description
        prompt = f"""Suggest appropriate account codes for this transaction:
Description: {description}
Amount: ${amount:.2f}

Common account types: ASSET (1000-1999), LIABILITY (2000-2999), EQUITY (3000-3999), REVENUE (4000-4999), EXPENSE (5000-5999)

Return JSON array of suggestions with account_code, account_name, account_type, confidence (0-1), and reasoning."""
        
        if self.llm_provider.lower() in ["openai", "azure"]:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            suggestions = json.loads(response.choices[0].message.content)
        else:
            response = self.llm_client.messages.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            suggestions = json.loads(response.content[0].text)
        
        return {
            "description": description,
            "amount": amount,
            "suggestions": suggestions.get("suggestions", []),
            "similar_transactions": len(similar)
        }

    async def _handle_validate_gaap_compliance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GAAP compliance."""
        from pyledger.gaap_compliance import GAAPCompliance
        
        check_type = args["check_type"]
        gaap = GAAPCompliance(self.conn)
        
        if check_type == "going_concern":
            result = gaap.validate_going_concern()
            return {"check_type": check_type, "compliant": result}
        
        return {
            "check_type": check_type,
            "message": f"GAAP {check_type} validation requires specific parameters",
            "available_checks": ["revenue_recognition", "expense_matching", "materiality", "consistency", "conservatism", "going_concern"]
        }

    async def _handle_get_audit_trail(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get audit trail entries."""
        from pyledger.gaap_compliance import GAAPCompliance, GAAPPrinciple
        
        gaap = GAAPCompliance(self.conn)
        
        principle = args.get("principle")
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        limit = args.get("limit", 50)
        
        # Query audit trail
        c = self.conn.cursor()
        query = "SELECT * FROM gaap_audit_trail WHERE 1=1"
        params = []
        
        if principle:
            query += " AND principle = ?"
            params.append(principle)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, params)
        entries = c.fetchall()
        
        return {
            "entries": [
                {
                    "id": e[0],
                    "timestamp": e[1],
                    "user_id": e[2],
                    "action": e[3],
                    "table_name": e[4],
                    "record_id": e[5],
                    "old_values": json.loads(e[6]) if e[6] else None,
                    "new_values": json.loads(e[7]) if e[7] else None,
                    "principle": e[8],
                    "justification": e[9]
                }
                for e in entries
            ],
            "count": len(entries)
        }

    # Tax filing tool handlers (Form 5472 / pro-forma 1120)

    def _tax_filing_manager(self):
        from pyledger.tax_filing import Form5472Filing
        return Form5472Filing(self.conn)

    async def _handle_register_filing_entity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register a filing entity for Form 5472 reporting."""
        filing = self._tax_filing_manager()
        entity_id = filing.add_entity(
            args["name"], args["entity_kind"], args["address_line1"],
            args["city"], state=args.get("state"),
            postal_code=args.get("postal_code"), ein=args.get("ein"),
            formation_date=args.get("formation_date"),
            principal_business_activity=args.get("principal_business_activity"),
            user_id=self.context.user_id)
        return {"entity_id": entity_id,
                "message": f"Filing entity '{args['name']}' registered"}

    async def _handle_add_foreign_owner(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register a foreign owner for Form 5472 reporting."""
        filing = self._tax_filing_manager()
        owner_id = filing.add_foreign_owner(
            args["entity_id"], args["name"], args["country"],
            args["address_line1"], args["city"],
            postal_code=args.get("postal_code"),
            us_tin=args.get("us_tin"), foreign_tin=args.get("foreign_tin"),
            ownership_pct=args.get("ownership_pct", 100.0),
            user_id=self.context.user_id)
        return {"owner_id": owner_id,
                "message": f"Foreign owner '{args['name']}' registered"}

    async def _handle_check_filing_requirements(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check Form 5472 filing requirement for an entity/year."""
        filing = self._tax_filing_manager()
        result = filing.check_filing_requirement(
            args["entity_id"], args["tax_year"])
        result["penalty_if_unfiled"] = filing.estimate_penalty(
            args["tax_year"])
        return result

    async def _handle_suggest_reportable_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scan the ledger for likely reportable transactions."""
        filing = self._tax_filing_manager()
        suggestions = filing.suggest_reportable_transactions(
            args["entity_id"], args["tax_year"])
        return {"suggestions": suggestions, "count": len(suggestions)}

    async def _handle_record_reportable_transaction(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Record a reportable transaction."""
        filing = self._tax_filing_manager()
        txn_id = filing.add_reportable_transaction(
            args["entity_id"], args["tax_year"], args["txn_type"],
            args["amount"], txn_date=args.get("txn_date"),
            description=args.get("description"),
            user_id=self.context.user_id)
        return {"transaction_id": txn_id, "message": "Transaction recorded"}

    async def _handle_list_reportable_transactions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List reportable transactions for an entity/year."""
        filing = self._tax_filing_manager()
        transactions = filing.list_reportable_transactions(
            args["entity_id"], args["tax_year"])
        totals = filing.transaction_totals_by_type(
            args["entity_id"], args["tax_year"])
        return {"transactions": transactions, "totals_by_type": totals,
                "count": len(transactions)}

    async def _handle_prepare_form_5472(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the Form 5472 / pro-forma 1120 filing package."""
        filing = self._tax_filing_manager()
        return filing.generate_filing(
            args["entity_id"], args["tax_year"],
            args.get("output_dir", "filings"),
            include_extension=args.get("include_extension", False),
            reasonable_cause_text=args.get("reasonable_cause_text"),
            user_id=self.context.user_id)

    async def _handle_estimate_filing_penalty(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate IRC 6038A late-filing penalty exposure."""
        from datetime import date as _date
        filing = self._tax_filing_manager()

        def parse(key: str) -> Optional[Any]:
            value = args.get(key)
            return _date.fromisoformat(value) if value else None

        return filing.estimate_penalty(
            args["tax_year"], filed_date=parse("filed_date"),
            irs_notice_date=parse("irs_notice_date"),
            num_forms=args.get("num_forms", 1))

    def sync_vector_store(self) -> Dict[str, int]:
        """Sync all database data to vector store."""
        return self.embedder.full_sync(self.context.entity_id)

    def close(self):
        """Close database connection."""
        self.conn.close()


# Convenience function for quick usage
async def create_agent(
    db_path: str = "pyledger.db",
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    api_key: Optional[str] = None
) -> AccountingAgent:
    """Create and initialize an accounting agent."""
    agent = AccountingAgent(
        db_path=db_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        api_key=api_key
    )
    
    # Initial sync
    agent.sync_vector_store()
    
    return agent