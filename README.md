# PyLedger - Professional Double-Entry Accounting System

A comprehensive, headless Python accounting application that implements double-entry bookkeeping with CLI, REST API, and MCP (Model Context Protocol) interfaces. **Now with full GAAP compliance!**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GAAP Compliant](https://img.shields.io/badge/GAAP-Compliant-green.svg)](https://en.wikipedia.org/wiki/Generally_Accepted_Accounting_Principles)

## 🚀 Features

### Core Accounting
- **Multi-Entity Support**: Manage multiple companies/organizations with isolated data
- **Double-Entry Accounting**: Full implementation of double-entry bookkeeping principles
- **Enhanced Account Management**: Opening balances, opening dates, and comprehensive account structure
- **Comprehensive Transaction Types**: Cash sales, cash purchases, opening balances, and standard journal entries
- **Advanced Journal Entries**: Narration, quantity tracking, unit prices, and tax rate support
- **Tax Handling**: Automatic tax calculations with dedicated tax payable/receivable accounts

### Business Document Management
- **Invoice Management**: Complete invoice system with customer management, line items, and payment tracking
- **Purchase Order Management**: Full purchase order system with supplier management, receipt tracking, and status management
- **Payment Clearing**: Advanced payment clearing with aging schedules and reconciliation
- **Financial Reports**: Balance Sheet, Income Statement, and Cash Flow reporting

### GAAP Compliance ⭐ **NEW**
- **Revenue Recognition (ASC 606)**: Point-in-time and over-time recognition methods
- **Expense Matching**: Links expenses to related revenues with matching ratios
- **Materiality**: Automatic assessment with customizable thresholds (default: 5% of total assets)
- **Consistency**: Method consistency tracking with change justification
- **Conservatism**: Understate assets, overstate liabilities for prudent reporting
- **Going Concern**: Assets vs. liabilities validation for financial viability
- **Audit Trails**: Complete transaction history with principle-based categorization

### Technical Features
- **Multiple Interfaces**: CLI, REST API, and MCP server for AI assistant integration
- **Database Persistence**: SQLite database with automatic balance updates
- **Professional Testing**: Comprehensive test suite validating accounting principles
- **PDF Generation**: Professional invoice PDF generation with modern design
- **Modern Python**: Leverages Python 3.12+ features for better performance and type safety

## 📦 Installation

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

## 🎯 Quick Start

### 1. Initialize the System
```bash
# Initialize database
python3 -m pyledger.main db-init

# Add your first entity
python3 -m pyledger.main db-add-entity
```

### 2. Set Up Chart of Accounts
```bash
# Add accounts with opening balances
python3 -m pyledger.main db-add-account
```

### 3. Create Your First Transaction
```bash
# Create a cash sale
python3 -m pyledger.main db-cash-sale

# Or create a journal entry
python3 -m pyledger.main db-add-entry
```

### 4. Test Everything Works
```bash
# Run accounting tests to verify everything works
python3 -m pyledger.accounting_tests

# Test GAAP compliance
python3 -m pyledger.gaap_compliance_tests
```

### 5. Start the API Server
```bash
# Start the REST API server
uvicorn pyledger.api:app --reload --host 0.0.0.0 --port 8000
```

## 📋 Usage

### CLI Interface

#### Database Management
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
```

#### Journal Entries & Transactions
```bash
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
```

#### Invoice Management
```bash
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
```

#### Purchase Order Management
```bash
# Add purchase order
python3 -m pyledger.main db-add-po

# List purchase orders
python3 -m pyledger.main db-list-pos

# Get purchase order details
python3 -m pyledger.main db-get-po

# Record purchase order receipt
python3 -m pyledger.main db-record-po-receipt
```

#### Testing & Validation
```bash
# Run accounting tests
python3 -m pyledger.accounting_tests

# Run GAAP compliance tests
python3 -m pyledger.gaap_compliance_tests
```

### REST API

Start the API server:
```bash
uvicorn pyledger.api:app --reload --host 0.0.0.0 --port 8000
```

#### Core API Endpoints

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

#### GAAP Compliance API Endpoints ⭐ **NEW**

**Revenue Recognition**
- `POST /gaap/revenue_recognition` - Validate revenue recognition per ASC 606
- `PUT /gaap/revenue_recognition/{invoice_number}` - Update revenue recognition

**Expense Matching**
- `POST /gaap/expense_matching` - Validate expense matching principle

**Materiality & Conservatism**
- `POST /gaap/materiality_assessment` - Assess materiality of transactions
- `POST /gaap/conservatism` - Apply conservatism principle

**Compliance Reporting**
- `GET /gaap/going_concern` - Validate going concern assumption
- `GET /gaap/compliance_report` - Generate GAAP compliance report
- `GET /gaap/audit_trail` - Get audit trail entries

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

# GAAP Compliance - Revenue Recognition
curl -X POST "http://localhost:8000/gaap/revenue_recognition" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "INV-2024-001",
    "recognition_method": "point_in_time",
    "performance_obligations": ["Delivery of goods"],
    "start_date": "2024-01-15",
    "end_date": "2024-01-15"
  }'

# GAAP Compliance - Materiality Assessment
curl -X POST "http://localhost:8000/gaap/materiality_assessment" \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_type": "journal_entry",
    "actual_amount": 5000.0
  }'

# Get GAAP compliance report
curl "http://localhost:8000/gaap/compliance_report"
```

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

## 🏗️ Project Structure

```
pyledger/
├── accounts.py              # Account and Chart of Accounts classes
├── journal.py               # Journal entries and ledger
├── transaction_types.py     # Transaction type management (cash sales, purchases, etc.)
├── invoices.py              # Invoice management system
├── purchase_orders.py       # Purchase order management system
├── payment_clearing.py      # Payment clearing and aging schedules
├── reports.py               # Financial reporting functions
├── db.py                    # Database operations
├── api.py                   # FastAPI REST API
├── mcp_server.py            # MCP server implementation
├── main.py                  # CLI interface
├── gaap_compliance.py       # GAAP compliance module ⭐ NEW
├── gaap_compliance_tests.py # GAAP compliance test suite ⭐ NEW
├── accounting_tests.py      # Professional accounting test suite
├── test_db.py               # Database function tests
├── test_mcp.py              # MCP server tests
├── test_pyledger.py         # Core functionality tests
└── test_enhanced_features.py # Enhanced features test suite
```

## 📊 Accounting Principles

The system implements standard double-entry accounting:

- **Accounting Equation**: Assets = Liabilities + Equity
- **Double-Entry**: Every transaction affects at least two accounts
- **Balance Validation**: All journal entries must balance (debits = credits)
- **Account Types**: Assets, Liabilities, Equity, Revenue, Expense
- **Closing Entries**: Proper period-end closing procedures

## ⚖️ GAAP Compliance

PyLedger includes comprehensive GAAP (Generally Accepted Accounting Principles) compliance features:

### GAAP Principles Implemented

- **Revenue Recognition (ASC 606)**: Point-in-time and over-time recognition methods
- **Expense Matching**: Links expenses to related revenues with matching ratios
- **Materiality**: Automatic assessment with customizable thresholds (default: 5% of total assets)
- **Consistency**: Method consistency tracking with change justification
- **Conservatism**: Understate assets, overstate liabilities for prudent reporting
- **Going Concern**: Assets vs. liabilities validation for financial viability
- **Audit Trails**: Complete transaction history with principle-based categorization

### GAAP Compliance Features

- **Automated Validation**: All transactions validated against GAAP principles
- **Real-Time Monitoring**: Continuous compliance checking
- **Comprehensive Audit Trails**: Complete transaction history with before/after values
- **Compliance Reporting**: Detailed GAAP compliance reports
- **API Integration**: Full REST API support for GAAP compliance operations

### GAAP Compliance Testing

```bash
# Run GAAP compliance tests
python3 -m pyledger.gaap_compliance_tests
```

The GAAP compliance test suite validates:
- Revenue recognition per ASC 606
- Expense matching principle
- Materiality assessment
- Consistency checks
- Conservatism principle
- Going concern assumption
- Audit trail functionality
- Compliance report generation

For detailed GAAP compliance documentation, see [GAAP_COMPLIANCE_DOCUMENTATION.md](GAAP_COMPLIANCE_DOCUMENTATION.md).

## 🇺🇸 IRS Form 5472 / Pro-Forma 1120 Filing (Foreign-Owned US LLCs)

PyLedger prepares the annual IRS compliance filing required of foreign-owned
US single-member LLCs (and 25%+ foreign-owned corporations) under IRC §6038A —
the filing that carries a **$25,000 penalty per form per year** if missed.

### What it does

- **Filing-requirement check**: determines whether Form 5472 + pro-forma 1120
  is required for an entity and tax year, with deadline (April 15 /
  extended October 15) and penalty-exposure estimates
- **Ledger scan**: suggests reportable transactions (capital contributions,
  distributions, owner loans, expenses paid by owner, formation costs) from
  your journal entries, by account mapping or keyword heuristics
- **Official IRS PDFs**: downloads and fills the genuine `f5472.pdf`,
  `f1120.pdf` (with the required "Foreign-owned U.S. DE" banner across the
  top), and `f7004.pdf` extension templates from irs.gov
- **Attachments**: generates the Part V statement for DE transactions and
  reasonable-cause statements for late filings
- **Audit trail**: every entity, owner, transaction, and generated filing is
  logged in `tax_audit_trail`

Foreign-owned DEs cannot e-file this filing; the generated package is
print-ready for fax (855-887-7737) or mail (IRS Ogden, UT).

### CLI

```bash
pyledger tax-5472-wizard        # interactive guided preparation
pyledger tax-check --entity-id 1 --tax-year 2025
pyledger tax-5472-generate --entity-id 1 --tax-year 2025 --extension
pyledger tax-7004-generate --entity-id 1 --tax-year 2025
pyledger tax-list-transactions --entity-id 1 --tax-year 2025
```

### Python API

```python
from pyledger import Form5472Filing
from pyledger.db import get_connection, init_db

conn = get_connection("pyledger.db")
init_db(conn)
filing = Form5472Filing(conn)

entity_id = filing.add_entity("Acme LLC", "foreign_owned_de",
                              "123 Main St", "Dover", state="DE",
                              ein="12-3456789", formation_date="2025-03-01")
filing.add_foreign_owner(entity_id, "Hans Mueller", "Germany",
                         "Hauptstrasse 1", "Berlin", foreign_tin="DE123")
filing.add_reportable_transaction(entity_id, 2025, "capital_contribution", 5000.0)

print(filing.check_filing_requirement(entity_id, 2025))
result = filing.generate_filing(entity_id, 2025, "filings/")
```

The same operations are exposed as REST endpoints (`/tax/...`), MCP tools,
and AI-agent tools (`check_filing_requirements`, `prepare_form_5472`, ...).

> **Disclaimer**: PyLedger assists with form preparation and is not tax
> advice. Review all generated filings with a qualified tax professional.

### Claude Code skill

This repo doubles as a [Claude Code plugin marketplace](https://code.claude.com/docs/en/discover-plugins)
serving a `form-5472-filing` skill that walks Claude through the full annual
filing workflow (entity setup → ledger scan → validation → PDF generation):

```shell
/plugin marketplace add dickhfchan/pyledger
/plugin install pyledger-tax-filing@pyledger
```

The skill requires the `pyledger` package installed and must be run from a
project root containing `pyledger.db`. When working inside this repository
itself, the skill is picked up automatically from `.claude/skills/` — no
install needed.

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all accounting tests
python3 -m pyledger.accounting_tests

# Run GAAP compliance tests
python3 -m pyledger.gaap_compliance_tests

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
- **GAAP compliance** with all major principles
- **Accounting equation compliance**
- **Double-entry validation**
- **Revenue/expense tracking**
- **Balance sheet accuracy**
- **Income statement accuracy**
- **Real-world business scenarios**

## 🗄️ Database Schema

The SQLite database includes:

### Core Tables
- `entities` table: Multi-entity support with company/organization data
- `accounts` table: Account information with opening balances and dates
- `journal_entries` table: Journal entry metadata with transaction types
- `journal_lines` table: Individual debit/credit lines with narration, quantities, and tax rates
- `invoices` table: Invoice management with customer data
- `invoice_lines` table: Invoice line items with quantities and prices
- `purchase_orders` table: Purchase order management with supplier data
- `purchase_order_lines` table: Purchase order line items with quantities and prices

### GAAP Compliance Tables ⭐ **NEW**
- `gaap_audit_trail` table: Complete audit trail with principle-based categorization
- `revenue_recognition` table: Revenue recognition tracking per ASC 606
- `expense_matching` table: Expense matching with ratios and periods
- `materiality_assessments` table: Materiality assessments with thresholds
- `consistency_checks` table: Method consistency tracking and changes

## 🛠️ Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes
3. Add tests
4. Run test suite: `python3 -m pyledger.accounting_tests`
5. Commit and push: `git commit -m "Add new feature" && git push`

### Key Benefits

1. **Professional Standards**: Full GAAP compliance for professional accounting
2. **Audit Readiness**: Complete audit trails and compliance reporting
3. **Risk Mitigation**: Materiality assessment and conservatism principles
4. **Automated Validation**: Real-time GAAP compliance checking
5. **Comprehensive Reporting**: Detailed GAAP compliance reports
6. **Multi-Interface Support**: CLI, REST API, and MCP server
7. **Modern Python**: Leverages Python 3.12+ features
8. **Open Source**: MIT license with full code access

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 🆘 Support

For issues and questions, please open an issue on GitHub.

## 📊 Comparison with Other Systems

For detailed comparisons between PyLedger and other accounting systems:

- **PyLedger vs Odoo**: See [ODOO_COMPARISON.md](ODOO_COMPARISON.md)
- **PyLedger vs Python-Accounting**: See [PYTHON_ACCOUNTING_COMPARISON.md](PYTHON_ACCOUNTING_COMPARISON.md)

## 🎯 Use Cases

### Perfect For:
- **Small to Medium Businesses**: Cost-effective accounting solution
- **Developers**: API-first approach with programmatic access
- **AI Integration**: Built-in MCP server for AI assistant interaction
- **Multi-Entity Operations**: Managing multiple companies/organizations
- **Professional Accounting**: Full GAAP compliance for audit readiness
- **Automation Projects**: Integrating accounting with other business processes
- **Headless Applications**: Building applications without web interfaces

### Key Advantages:
- **Modern Architecture**: API-first design with CLI and MCP interfaces
- **GAAP Compliant**: Professional accounting standards
- **Multi-Entity Support**: Full support for multiple companies/organizations
- **Enhanced Features**: Opening balances, advanced journal entries, tax handling
- **AI Integration**: Built-in MCP server for AI assistant interaction
- **Lightweight**: Simple SQLite database, easy deployment
- **Open Source**: MIT license with full code access

## 🚀 Getting Started with GAAP Compliance

### Quick GAAP Compliance Setup

```python
from pyledger.gaap_compliance import GAAPCompliance, RevenueRecognitionMethod

# Initialize GAAP compliance
gaap = GAAPCompliance(conn)

# Revenue recognition
gaap.validate_revenue_recognition(
    invoice_number='INV-2024-001',
    recognition_method=RevenueRecognitionMethod.POINT_IN_TIME,
    performance_obligations=["Delivery of goods"]
)

# Materiality assessment
assessment = gaap.assess_materiality(
    assessment_type="journal_entry",
    actual_amount=5000.0
)

# Conservatism principle
gaap.apply_conservatism(
    account_code='1100',
    adjustment_amount=1000.0,
    reason="Conservative estimate for doubtful accounts"
)

# Generate compliance report
report = gaap.get_gaap_compliance_report()
```

### GAAP Compliance Testing

```bash
# Run comprehensive GAAP compliance tests
python3 -m pyledger.gaap_compliance_tests

# Expected output:
# 🧪 Running GAAP Compliance Test Suite
# ✅ All GAAP compliance tests passed!
# 📊 GAAP Compliance Test Results:
#    ✅ Passed: 10
#    ❌ Failed: 0
#    📈 Success Rate: 100.0%
```

---

**PyLedger** - Professional accounting with full GAAP compliance, modern Python, and comprehensive testing. Perfect for developers, small businesses, and professional accounting practices! 🎉 