# PyLedger - Professional Double-Entry Accounting System

A comprehensive, headless Python accounting application that implements double-entry bookkeeping with CLI, REST API, and MCP (Model Context Protocol) interfaces.

## Features

- **Multi-Entity Support**: Manage multiple companies/organizations with isolated data
- **Double-Entry Accounting**: Full implementation of double-entry bookkeeping principles
- **Enhanced Account Management**: Opening balances, opening dates, and comprehensive account structure
- **Comprehensive Transaction Types**: Cash sales, cash purchases, opening balances, and standard journal entries
- **Advanced Journal Entries**: Narration, quantity tracking, unit prices, and tax rate support
- **Tax Handling**: Automatic tax calculations with dedicated tax payable/receivable accounts
- **Invoice Management**: Complete invoice system with customer management, line items, and payment tracking
- **Purchase Order Management**: Full purchase order system with supplier management, receipt tracking, and status management
- **Financial Reports**: Balance Sheet, Income Statement, and Cash Flow reporting
- **Multiple Interfaces**: CLI, REST API, and MCP server for AI assistant integration
- **Database Persistence**: SQLite database with automatic balance updates
- **Professional Testing**: Comprehensive test suite validating accounting principles

## Installation

### Prerequisites
- Python 3.12+ (required for modern type hints and features)
- pip

**Note**: This project requires Python 3.12 or higher to take advantage of modern Python features, improved type hints, and better performance. The CI/CD pipeline tests against Python 3.12 and 3.13.

### Setup
```bash
# Clone the repository
git clone git@github.com:dickhfchan/pyledger.git
cd pyledger

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## Usage

### CLI Interface

```bash
# Initialize database
python3 -m pyledger.main db-init

# Add entities
python3 -m pyledger.main db-add-entity

# List entities
python3 -m pyledger.main db-list-entities

# Add accounts with opening balances
python3 -m pyledger.main db-add-account

# List accounts
python3 -m pyledger.main db-list-accounts

# Add journal entries
python3 -m pyledger.main db-add-entry

# List journal entries
python3 -m pyledger.main db-list-entries

# View entry details
python3 -m pyledger.main db-entry-lines <entry_id>

# Create cash sale transaction
python3 -m pyledger.main db-cash-sale

# Create cash purchase transaction
python3 -m pyledger.main db-cash-purchase

# Create opening balance transaction
python3 -m pyledger.main db-opening-balance

# Add invoice
python3 -m pyledger.main db-add-invoice

# List invoices
python3 -m pyledger.main db-list-invoices

# Get invoice details
python3 -m pyledger.main db-get-invoice

# Record invoice payment
python3 -m pyledger.main db-record-invoice-payment

# Generate PDF invoice
python3 -m pyledger.main db-generate-invoice-pdf

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

**Entities**
- `GET /entities` - List all entities
- `POST /entities` - Create new entity
- `GET /entities/{id}` - Get entity details

**Accounts**
- `GET /accounts` - List all accounts
- `POST /accounts` - Create new account with opening balance
- `GET /accounts/{code}` - Get account details
- `GET /accounts/{code}/balance` - Get account balance history

**Journal Entries**
- `GET /journal_entries` - List all journal entries
- `POST /journal_entries` - Create new journal entry
- `GET /journal_entries/{id}` - Get journal entry details
- `GET /journal_entries/{id}/lines` - Get journal entry lines

**Transaction Types**
- `POST /transactions/cash-sale` - Create cash sale transaction
- `POST /transactions/cash-purchase` - Create cash purchase transaction
- `POST /transactions/opening-balance` - Create opening balance transaction

**Invoices**
- `GET /invoices` - List all invoices
- `POST /invoices` - Create new invoice
- `GET /invoices/{invoice_number}` - Get invoice details
- `GET /invoices/{invoice_number}/lines` - Get invoice line items
- `POST /invoices/{invoice_number}/payment` - Record invoice payment
- `GET /invoices/{invoice_number}/pdf` - Generate PDF invoice

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
# Create an entity
curl -X POST "http://localhost:8000/entities" \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corporation", "code": "ACME", "description": "Test company"}'

# Create an account with opening balance
curl -X POST "http://localhost:8000/accounts" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "1000", 
    "name": "Cash", 
    "type": "ASSET", 
    "balance": 0.0,
    "opening_balance": 10000.0,
    "opening_date": "2024-01-01"
  }'

# Create a cash sale transaction
curl -X POST "http://localhost:8000/transactions/cash-sale" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Sale of consulting services",
    "entry_date": "2024-01-15",
    "cash_account": "1000",
    "revenue_account": "4000",
    "amount": 5000.0,
    "tax_rate": 0.1,
    "reference": "INV-001"
  }'

# Create a journal entry with enhanced features
curl -X POST "http://localhost:8000/journal_entries" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Owner investment",
    "entry_date": "2024-01-01",
    "transaction_type": "journal_entry",
    "reference": "INV-001",
    "lines": [
      {
        "account_code": "1000", 
        "amount": 1000.0, 
        "is_debit": true,
        "narration": "Owner investment",
        "quantity": 1.0,
        "unit_price": 1000.0,
        "tax_rate": 0.0
      },
      {
        "account_code": "3000", 
        "amount": 1000.0, 
        "is_debit": false,
        "narration": "Owner equity",
        "quantity": 1.0,
        "unit_price": 1000.0,
        "tax_rate": 0.0
      }
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

**Entities & Accounts**
- `list_entities` - List all entities
- `add_entity` - Create new entity
- `list_accounts` - List all accounts
- `add_account` - Create new account with opening balance
- `get_account_balance` - Get account balance history

**Journal Entries & Transactions**
- `add_journal_entry` - Create journal entry with enhanced features
- `list_journal_entries` - List all journal entries
- `get_journal_lines` - Get journal entry details
- `create_cash_sale` - Create cash sale transaction
- `create_cash_purchase` - Create cash purchase transaction
- `create_opening_balance` - Create opening balance transaction

**Invoices**
- `add_invoice` - Create new invoice
- `list_invoices` - List all invoices
- `get_invoice` - Get invoice details
- `record_invoice_payment` - Record invoice payment
- `generate_invoice_pdf` - Generate PDF invoice in A4 format

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
├── transaction_types.py # Transaction type management (cash sales, purchases, etc.)
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
├── test_pyledger.py    # Core functionality tests
└── test_enhanced_features.py # Enhanced features test suite
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

# Run enhanced features tests
python3 test_enhanced_features.py

# Run specific test modules
python3 -m pyledger.test_db
python3 -m pyledger.test_mcp
python3 -m pyledger.test_pyledger
```

The test suite validates:
- **Multi-entity support** with data isolation
- **Enhanced account management** with opening balances
- **Comprehensive transaction types** (cash sales, purchases, opening balances)
- **Advanced journal entries** with narration, quantities, and tax rates
- **Tax handling** with automatic calculations
- **Accounting equation compliance**
- **Double-entry validation**
- **Revenue/expense tracking**
- **Balance sheet accuracy**
- **Income statement accuracy**
- **Real-world business scenarios**

## Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes
3. Add tests
4. Run test suite: `python3 -m pyledger.accounting_tests`
5. Commit and push: `git commit -m "Add new feature" && git push`

### Database Schema

The SQLite database includes:
- `entities` table: Multi-entity support with company/organization data
- `accounts` table: Account information with opening balances and dates
- `journal_entries` table: Journal entry metadata with transaction types
- `journal_lines` table: Individual debit/credit lines with narration, quantities, and tax rates
- `invoices` table: Invoice management with customer data
- `invoice_lines` table: Invoice line items with quantities and prices
- `purchase_orders` table: Purchase order management with supplier data
- `purchase_order_lines` table: Purchase order line items with quantities and prices

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

## Comparison with Other Systems

For detailed comparisons between PyLedger and other accounting systems:

- **PyLedger vs Odoo**: See [ODOO_COMPARISON.md](ODOO_COMPARISON.md)
- **PyLedger vs Python-Accounting**: See [PYTHON_ACCOUNTING_COMPARISON.md](PYTHON_ACCOUNTING_COMPARISON.md) 