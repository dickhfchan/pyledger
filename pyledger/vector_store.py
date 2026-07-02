"""
Vector Embeddings for Semantic Search in PyLedger
Enables natural language search across transactions, invoices, and documents.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import date
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class AccountingVectorStore:
    """Vector embeddings for semantic search across accounting data."""

    def __init__(
        self,
        db_path: str = "./chroma_db",
        collection_name: str = "pyledger_accounting",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.db_path = db_path
        self.collection_name = collection_name
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model
        self.encoder = SentenceTransformer(embedding_model)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "PyLedger accounting data embeddings"}
        )

    def _generate_id(self, doc_type: str, identifier: str) -> str:
        """Generate unique ID for document."""
        return f"{doc_type}_{identifier}"

    def index_journal_entry(
        self,
        entry_id: int,
        description: str,
        lines: List[Dict[str, Any]],
        entry_date: str,
        entity_id: Optional[str] = None
    ) -> None:
        """Embed and index a journal entry for semantic search."""
        # Build searchable text
        lines_text = " ".join([
            f"{line.get('account_code', '')} {line.get('amount', 0)} {'debit' if line.get('is_debit') else 'credit'} {line.get('narration', '')}"
            for line in lines
        ])
        
        text = f"Journal Entry: {description}. Date: {entry_date}. Lines: {lines_text}"
        
        # Generate embedding
        embedding = self.encoder.encode(text).tolist()
        
        # Metadata for filtering
        metadata = {
            "type": "journal_entry",
            "entry_id": entry_id,
            "date": entry_date,
            "description": description[:500],  # Truncate for metadata
            "total_amount": sum(abs(line.get('amount', 0)) for line in lines),
            "entity_id": entity_id or "default"
        }
        
        self.collection.add(
            ids=[self._generate_id("entry", str(entry_id))],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def index_invoice(
        self,
        invoice_number: str,
        customer_name: str,
        customer_address: str,
        issue_date: str,
        due_date: str,
        lines: List[Dict[str, Any]],
        total_amount: float,
        status: str,
        entity_id: Optional[str] = None
    ) -> None:
        """Embed and index an invoice for semantic search."""
        lines_text = " ".join([
            f"{line.get('description', '')} qty:{line.get('quantity', 0)} @ ${line.get('unit_price', 0)}"
            for line in lines
        ])
        
        text = (
            f"Invoice {invoice_number} for {customer_name} ({customer_address}). "
            f"Issued: {issue_date}, Due: {due_date}. Status: {status}. "
            f"Items: {lines_text}. Total: ${total_amount:.2f}"
        )
        
        embedding = self.encoder.encode(text).tolist()
        
        metadata = {
            "type": "invoice",
            "invoice_number": invoice_number,
            "customer_name": customer_name,
            "issue_date": issue_date,
            "due_date": due_date,
            "status": status,
            "total_amount": total_amount,
            "entity_id": entity_id or "default"
        }
        
        self.collection.add(
            ids=[self._generate_id("invoice", invoice_number)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def index_purchase_order(
        self,
        po_number: str,
        supplier_name: str,
        supplier_address: str,
        order_date: str,
        expected_delivery_date: str,
        lines: List[Dict[str, Any]],
        total_amount: float,
        status: str,
        entity_id: Optional[str] = None
    ) -> None:
        """Embed and index a purchase order for semantic search."""
        lines_text = " ".join([
            f"{line.get('description', '')} qty:{line.get('quantity', 0)} @ ${line.get('unit_price', 0)}"
            for line in lines
        ])
        
        text = (
            f"Purchase Order {po_number} from {supplier_name} ({supplier_address}). "
            f"Ordered: {order_date}, Expected: {expected_delivery_date}. Status: {status}. "
            f"Items: {lines_text}. Total: ${total_amount:.2f}"
        )
        
        embedding = self.encoder.encode(text).tolist()
        
        metadata = {
            "type": "purchase_order",
            "po_number": po_number,
            "supplier_name": supplier_name,
            "order_date": order_date,
            "expected_delivery_date": expected_delivery_date,
            "status": status,
            "total_amount": total_amount,
            "entity_id": entity_id or "default"
        }
        
        self.collection.add(
            ids=[self._generate_id("po", po_number)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def index_account(
        self,
        account_code: str,
        account_name: str,
        account_type: str,
        balance: float,
        description: str = "",
        entity_id: Optional[str] = None
    ) -> None:
        """Embed and index an account for semantic search."""
        text = f"Account {account_code}: {account_name} ({account_type}). Balance: ${balance:.2f}. {description}"
        
        embedding = self.encoder.encode(text).tolist()
        
        metadata = {
            "type": "account",
            "account_code": account_code,
            "account_name": account_name,
            "account_type": account_type,
            "balance": balance,
            "entity_id": entity_id or "default"
        }
        
        self.collection.add(
            ids=[self._generate_id("account", account_code)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def index_document(
        self,
        doc_id: str,
        doc_type: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Generic document indexing for any text content."""
        embedding = self.encoder.encode(content).tolist()
        
        meta = {"type": doc_type, "doc_id": doc_id}
        meta.update(metadata)
        
        self.collection.add(
            ids=[self._generate_id(doc_type, doc_id)],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta]
        )

    def semantic_search(
        self,
        query: str,
        n_results: int = 10,
        filter_type: Optional[str] = None,
        filter_entity: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar accounting documents using natural language.
        
        Args:
            query: Natural language search query
            n_results: Maximum number of results
            filter_type: Filter by document type (journal_entry, invoice, purchase_order, account)
            filter_entity: Filter by entity ID
            date_from: Filter by date (YYYY-MM-DD)
            date_to: Filter by date (YYYY-MM-DD)
        """
        query_embedding = self.encoder.encode(query).tolist()
        
        # Build where clause
        where_clause = {}
        if filter_type:
            where_clause["type"] = filter_type
        if filter_entity:
            where_clause["entity_id"] = filter_entity
        
        # Note: ChromaDB doesn't support date range filters directly in where clause
        # We'll filter post-query for date ranges
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                item = {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None
                }
                
                # Post-filter by date range if specified
                if date_from or date_to:
                    item_date = item["metadata"].get("date") or item["metadata"].get("issue_date") or item["metadata"].get("order_date")
                    if item_date:
                        if date_from and item_date < date_from:
                            continue
                        if date_to and item_date > date_to:
                            continue
                    else:
                        continue
                
                formatted.append(item)
        
        return formatted

    def search_similar_transactions(
        self,
        description: str,
        amount: float,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find transactions similar to a given description and amount."""
        query = f"{description} amount ${amount:.2f}"
        return self.semantic_search(query, n_results=n_results, filter_type="journal_entry")

    def search_invoices_by_customer(
        self,
        customer_name: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search invoices by customer name."""
        return self.semantic_search(
            f"customer {customer_name}",
            n_results=n_results,
            filter_type="invoice"
        )

    def search_accounts_by_name(
        self,
        account_name: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search accounts by name or description."""
        return self.semantic_search(
            f"account {account_name}",
            n_results=n_results,
            filter_type="account"
        )

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        count = self.collection.count()
        
        # Get type distribution
        all_data = self.collection.get(include=["metadatas"])
        type_counts = {}
        for meta in all_data.get("metadatas", []):
            doc_type = meta.get("type", "unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        return {
            "total_documents": count,
            "type_distribution": type_counts
        }

    def delete_document(self, doc_type: str, identifier: str) -> None:
        """Delete a document from the vector store."""
        self.collection.delete(ids=[self._generate_id(doc_type, identifier)])

    def clear_all(self) -> None:
        """Clear all documents from the vector store."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "PyLedger accounting data embeddings"}
        )


class TransactionEmbedder:
    """Helper to embed transactions from database into vector store."""

    def __init__(self, vector_store: AccountingVectorStore, db_conn):
        self.vector_store = vector_store
        self.conn = db_conn

    def sync_all_journal_entries(self, entity_id: Optional[str] = None) -> int:
        """Sync all journal entries from database to vector store."""
        from pyledger.db import list_journal_entries, get_journal_lines
        
        entries = list_journal_entries(self.conn)
        count = 0
        
        for entry_id, description, entry_date in entries:
            lines = get_journal_lines(self.conn, entry_id)
            lines_data = [
                {
                    "account_code": line[1],
                    "amount": line[2],
                    "is_debit": line[3]
                }
                for line in lines
            ]
            
            self.vector_store.index_journal_entry(
                entry_id=entry_id,
                description=description,
                lines=lines_data,
                entry_date=entry_date,
                entity_id=entity_id
            )
            count += 1
        
        return count

    def sync_all_invoices(self, entity_id: Optional[str] = None) -> int:
        """Sync all invoices from database to vector store."""
        from pyledger.db import list_invoices, get_invoice, get_invoice_lines
        
        invoices = list_invoices(self.conn)
        count = 0
        
        for invoice_row in invoices:
            invoice_number = invoice_row[0]
            invoice_detail = get_invoice(self.conn, invoice_number)
            lines = get_invoice_lines(self.conn, invoice_number)
            
            lines_data = [
                {
                    "description": line[1],
                    "quantity": line[2],
                    "unit_price": line[3],
                    "tax_rate": line[4]
                }
                for line in lines
            ]
            
            self.vector_store.index_invoice(
                invoice_number=invoice_detail[0],
                customer_name=invoice_detail[1],
                customer_address=invoice_detail[2],
                issue_date=invoice_detail[3],
                due_date=invoice_detail[4],
                lines=lines_data,
                total_amount=invoice_detail[9],
                status=invoice_detail[5],
                entity_id=entity_id
            )
            count += 1
        
        return count

    def sync_all_accounts(self, entity_id: Optional[str] = None) -> int:
        """Sync all accounts from database to vector store."""
        from pyledger.db import list_accounts
        
        accounts = list_accounts(self.conn)
        count = 0
        
        for code, name, type_str, balance in accounts:
            self.vector_store.index_account(
                account_code=code,
                account_name=name,
                account_type=type_str,
                balance=balance,
                entity_id=entity_id
            )
            count += 1
        
        return count

    def full_sync(self, entity_id: Optional[str] = None) -> Dict[str, int]:
        """Perform full sync of all accounting data to vector store."""
        return {
            "journal_entries": self.sync_all_journal_entries(entity_id),
            "invoices": self.sync_all_invoices(entity_id),
            "accounts": self.sync_all_accounts(entity_id)
        }