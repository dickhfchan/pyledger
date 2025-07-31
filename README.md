# PyLedger - Professional Double-Entry Accounting System

A comprehensive, headless Python accounting application that implements double-entry bookkeeping with CLI, REST API, and MCP (Model Context Protocol) interfaces.

## Features

- **Double-Entry Accounting**: Full implementation of double-entry bookkeeping principles
- **Chart of Accounts**: Comprehensive account management with standard accounting categories
- **Journal Entries**: Transaction recording with automatic balance validation
- **Invoice Management**: Complete invoice system with customer management, line items, and payment tracking
- **Purchase Order Management**: Full purchase order system with supplier management, receipt tracking, and status management
- **Financial Reports**: Balance Sheet, Income Statement, and Cash Flow reporting
- **Multiple Interfaces**: CLI, REST API, and MCP server for AI assistant integration
- **Database Persistence**: SQLite database with automatic balance updates
- **Professional Testing**: Comprehensive test suite validating accounting principles

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup
```bash
# Clone the repository
git clone git@github.com:dickhfchan/pyledger.git
cd pyledger

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic mcp
```

## Usage

### CLI Interface

```bash
# Initialize database
python3 -m pyledger.main db-init

# Add accounts
python3 -m pyledger.main db-add-account

# Add journal entries
python3 -m pyledger.main db-add-entry

# List accounts
python3 -m pyledger.main db-list-accounts

# List journal entries
python3 -m pyledger.main db-list-entries

# View entry details
python3 -m pyledger.main db-entry-lines <entry_id>

# Add invoice
python3 -m pyledger.main db-add-invoice

# List invoices
python3 -m pyledger.main db-list-invoices

# Get invoice details
python3 -m pyledger.main db-get-invoice

# Record invoice payment
python3 -m pyledger.main db-record-invoice-payment

# Add purchase order
python3 -m pyledger.main db-add-po

# List purchase orders
python3 -m pyledger.main db-list-pos

# Get purchase order details
python3 -m pyledger.main db-get-po

# Record purchase order receipt
python3 -m pyledger.main db-record-po-receipt

# Run accounting tests
python3 -m pyledger.accounting_tests
```

### REST API

Start the API server:
```bash
uvicorn pyledger.api:app --reload --host 0.0.0.0 --port 8000
```

#### API Endpoints

**Accounts**
- `GET /accounts` - List all accounts
- `POST /accounts` - Create new account
- `GET /accounts/{code}` - Get account details

**Journal Entries**
- `GET /journal_entries` - List all journal entries
- `POST /journal_entries` - Create new journal entry
- `GET /journal_entries/{id}` - Get journal entry details

**Invoices**
- `GET /invoices` - List all invoices
- `POST /invoices` - Create new invoice
- `GET /invoices/{invoice_number}` - Get invoice details
- `GET /invoices/{invoice_number}/lines` - Get invoice line items
- `POST /invoices/{invoice_number}/payment` - Record invoice payment

**Purchase Orders**
- `GET /purchase_orders` - List all purchase orders
- `POST /purchase_orders` - Create new purchase order
- `GET /purchase_orders/{po_number}` - Get purchase order details
- `GET /purchase_orders/{po_number}/lines` - Get purchase order line items
- `POST /purchase_orders/{po_number}/receipt` - Record purchase order receipt

**Reports**
- `GET /reports/balance_sheet` - Generate balance sheet
- `GET /reports/income_statement` - Generate income statement
- `GET /reports/cash_flow` - Generate cash flow report

#### Example API Usage

```bash
# Create an account
curl -X POST "http://localhost:8000/accounts" \
  -H "Content-Type: application/json" \
  -d '{"code": "1000", "name": "Cash", "type": "ASSET", "balance": 0.0}'

# Create a journal entry
curl -X POST "http://localhost:8000/journal_entries" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Initial investment",
    "lines": [
      {"account_code": "1000", "amount": 10000.0, "is_debit": true},
      {"account_code": "3000", "amount": 10000.0, "is_debit": false}
    ]
  }'

# Get balance sheet
curl "http://localhost:8000/reports/balance_sheet"

# Create an invoice
curl -X POST "http://localhost:8000/invoices" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "INV-001",
    "customer_name": "Acme Corp",
    "customer_address": "123 Main St, City, State",
    "issue_date": "2024-01-15",
    "due_date": "2024-02-15",
    "lines": [
      {"description": "Web Development Services", "quantity": 40, "unit_price": 100.0, "tax_rate": 0.1}
    ]
  }'

# Record invoice payment
curl -X POST "http://localhost:8000/invoices/INV-001/payment" \
  -H "Content-Type: application/json" \
  -d '{"paid_amount": 4400.0}'

# Create a purchase order
curl -X POST "http://localhost:8000/purchase_orders" \
  -H "Content-Type: application/json" \
  -d '{
    "po_number": "PO-001",
    "supplier_name": "Office Supplies Co",
    "supplier_address": "456 Business Ave, City, State",
    "order_date": "2024-01-10",
    "expected_delivery_date": "2024-01-20",
    "lines": [
      {"description": "Office Chairs", "quantity": 5, "unit_price": 200.0, "tax_rate": 0.08}
    ]
  }'

# Record purchase order receipt
curl -X POST "http://localhost:8000/purchase_orders/PO-001/receipt" \
  -H "Content-Type: application/json" \
  -d '{"line_id": 1, "received_quantity": 3}'

### MCP Server

The MCP (Model Context Protocol) server allows AI assistants to interact with the accounting system.

Start the MCP server:
```bash
python3 -m pyledger.mcp_server
```

#### Available MCP Tools

**Accounts & Journal Entries**
- `list_accounts` - List all accounts
- `add_account` - Create new account
- `add_journal_entry` - Create journal entry
- `list_journal_entries` - List all journal entries
- `get_journal_lines` - Get journal entry details

**Invoices**
- `add_invoice` - Create new invoice
- `list_invoices` - List all invoices
- `get_invoice` - Get invoice details
- `record_invoice_payment` - Record invoice payment

**Purchase Orders**
- `add_purchase_order` - Create new purchase order
- `list_purchase_orders` - List all purchase orders
- `get_purchase_order` - Get purchase order details
- `record_purchase_order_receipt` - Record purchase order receipt

**Reports**
- `balance_sheet` - Generate balance sheet
- `income_statement` - Generate income statement
- `cash_flow_report` - Generate cash flow report

## Project Structure

```
pyledger/
├── accounts.py          # Account and Chart of Accounts classes
├── journal.py           # Journal entries and ledger
├── invoices.py          # Invoice management system
├── purchase_orders.py   # Purchase order management system
├── reports.py           # Financial reporting functions
├── db.py               # Database operations
├── api.py              # FastAPI REST API
├── mcp_server.py       # MCP server implementation
├── main.py             # CLI interface
├── accounting_tests.py  # Professional accounting test suite
├── test_db.py          # Database function tests
├── test_mcp.py         # MCP server tests
└── test_pyledger.py    # Core functionality tests
```

## Accounting Principles

The system implements standard double-entry accounting:

- **Accounting Equation**: Assets = Liabilities + Equity
- **Double-Entry**: Every transaction affects at least two accounts
- **Balance Validation**: All journal entries must balance (debits = credits)
- **Account Types**: Assets, Liabilities, Equity, Revenue, Expense
- **Closing Entries**: Proper period-end closing procedures

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python3 -m pyledger.accounting_tests

# Run specific test modules
python3 -m pyledger.test_db
python3 -m pyledger.test_mcp
python3 -m pyledger.test_pyledger
```

The test suite validates:
- Accounting equation compliance
- Double-entry validation
- Revenue/expense tracking
- Balance sheet accuracy
- Income statement accuracy
- Real-world business scenarios

## Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes
3. Add tests
4. Run test suite: `python3 -m pyledger.accounting_tests`
5. Commit and push: `git commit -m "Add new feature" && git push`

### Database Schema

The SQLite database includes:
- `accounts` table: Account information and balances
- `journal_entries` table: Journal entry metadata
- `journal_lines` table: Individual debit/credit lines

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub. 