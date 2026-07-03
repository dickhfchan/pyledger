import argparse
import json
import os
from pyledger.accounts import AccountType, ChartOfAccounts
from pyledger.journal import JournalLine, JournalEntry, Ledger
from pyledger.reports import balance_sheet, income_statement, cash_flow_report
from pyledger.db import (
    get_connection, init_db, add_account as db_add_account, list_accounts as db_list_accounts,
    add_journal_entry as db_add_journal_entry, list_journal_entries as db_list_journal_entries,
    get_journal_lines as db_get_journal_lines,
    add_invoice, get_invoice, list_invoices, get_invoice_lines, update_invoice_payment,
    add_purchase_order, get_purchase_order, list_purchase_orders, get_purchase_order_lines, update_purchase_order_receipt
)

ACCOUNT_TYPE_CHOICES = [t.name for t in AccountType]

ACCOUNTS_FILE = 'accounts.json'
ENTRIES_FILE = 'entries.json'
DB_FILE = 'pyledger.db'

def setup_sample_data(chart, ledger):
    # Add sample accounts
    chart.add_account('1000', 'Cash', AccountType.ASSET)
    chart.add_account('2000', 'Accounts Payable', AccountType.LIABILITY)
    chart.add_account('3000', 'Owner Equity', AccountType.EQUITY)
    chart.add_account('4000', 'Sales Revenue', AccountType.REVENUE)
    chart.add_account('5000', 'Office Supplies Expense', AccountType.EXPENSE)
    # Add a sample journal entry
    entry = JournalEntry(
        'Owner invests cash',
        [
            JournalLine('1000', 1000.0, True),  # Debit Cash
            JournalLine('3000', 1000.0, False), # Credit Equity
        ]
    )
    ledger.post_entry(entry)

def add_account_interactive(chart):
    code = input('Account code: ')
    name = input('Account name: ')
    print(f"Account types: {', '.join(ACCOUNT_TYPE_CHOICES)}")
    type_str = input('Account type: ').upper()
    if type_str not in ACCOUNT_TYPE_CHOICES:
        print('Invalid account type.')
        return
    chart.add_account(code, name, AccountType[type_str])
    print('Account added.')

def list_accounts(chart):
    print('Accounts:')
    for acc in chart.accounts.values():
        print(f"{acc.code}: {acc.name} ({acc.type.name}) Balance: {acc.balance}")

def add_journal_entry_interactive(chart, ledger):
    description = input('Entry description: ')
    lines = []
    while True:
        code = input('Account code (or blank to finish): ')
        if not code:
            break
        amount = float(input('Amount: '))
        dc = input('Debit or Credit (d/c): ').lower()
        is_debit = dc == 'd'
        lines.append(JournalLine(code, amount, is_debit))
    try:
        entry = JournalEntry(description, lines)
        ledger.post_entry(entry)
        print('Journal entry posted.')
    except Exception as e:
        print(f'Error: {e}')

def list_journal_entries(ledger):
    print('Journal Entries:')
    for i, entry in enumerate(ledger.entries, 1):
        print(f"{i}. {entry.description}")
        for line in entry.lines:
            dc = 'Debit' if line.is_debit else 'Credit'
            print(f"   {dc} {line.account_code}: {line.amount}")

def save_data(chart, ledger, accounts_file=ACCOUNTS_FILE, entries_file=ENTRIES_FILE):
    with open(accounts_file, 'w') as f:
        json.dump(chart.to_dict(), f, indent=2)
    with open(entries_file, 'w') as f:
        json.dump(ledger.to_dict(), f, indent=2)
    print(f"Data saved to {accounts_file} and {entries_file}.")

def load_data(accounts_file=ACCOUNTS_FILE, entries_file=ENTRIES_FILE):
    with open(accounts_file, 'r') as f:
        chart = ChartOfAccounts.from_dict(json.load(f))
    with open(entries_file, 'r') as f:
        ledger = Ledger.from_dict(json.load(f), chart)
    print(f"Data loaded from {accounts_file} and {entries_file}.")
    return chart, ledger

# --- Database-backed CLI operations ---
def db_add_account_interactive():
    conn = get_connection()
    code = input('Account code: ')
    name = input('Account name: ')
    print(f"Account types: {', '.join(ACCOUNT_TYPE_CHOICES)}")
    type_str = input('Account type: ').upper()
    if type_str not in ACCOUNT_TYPE_CHOICES:
        print('Invalid account type.')
        return
    db_add_account(conn, code, name, AccountType[type_str])
    print('Account added to database.')
    conn.close()

def db_list_accounts_cmd():
    conn = get_connection()
    print('Accounts in database:')
    for code, name, type_str, balance in db_list_accounts(conn):
        print(f"{code}: {name} ({type_str}) Balance: {balance}")
    conn.close()

def db_add_entry_interactive():
    conn = get_connection()
    description = input('Entry description: ')
    lines = []
    while True:
        code = input('Account code (or blank to finish): ')
        if not code:
            break
        amount = float(input('Amount: '))
        dc = input('Debit or Credit (d/c): ').lower()
        is_debit = dc == 'd'
        lines.append((code, amount, is_debit))
    # Check balance
    total_debits = sum(amount for code, amount, is_debit in lines if is_debit)
    total_credits = sum(amount for code, amount, is_debit in lines if not is_debit)
    if abs(total_debits - total_credits) > 1e-6:
        print('Error: Entry is not balanced.')
        conn.close()
        return
    db_add_journal_entry(conn, description, lines)
    print('Journal entry added to database.')
    conn.close()

def db_list_entries_cmd():
    conn = get_connection()
    print('Journal entries in database:')
    for eid, desc, date in db_list_journal_entries(conn):
        print(f"{eid}: {desc} ({date})")
    conn.close()

def db_entry_lines_cmd():
    conn = get_connection()
    entry_id = int(input('Entry ID: '))
    print(f'Lines for entry {entry_id}:')
    for line_id, account_code, amount, is_debit in db_get_journal_lines(conn, entry_id):
        dc = 'Debit' if is_debit else 'Credit'
        print(f"{line_id}: {dc} {account_code} {amount}")
    conn.close()

def db_init_cmd():
    conn = get_connection()
    init_db(conn)
    print('Database initialized.')
    conn.close()

# --- Invoice CLI Functions ---
def db_add_invoice_interactive():
    conn = get_connection()
    invoice_number = input('Invoice number: ')
    customer_name = input('Customer name: ')
    customer_address = input('Customer address: ')
    issue_date = input('Issue date (YYYY-MM-DD): ')
    due_date = input('Due date (YYYY-MM-DD): ')
    notes = input('Notes (optional): ')
    
    lines = []
    while True:
        description = input('Item description (or blank to finish): ')
        if not description:
            break
        quantity = float(input('Quantity: '))
        unit_price = float(input('Unit price: '))
        tax_rate = float(input('Tax rate (0.0-1.0): '))
        lines.append((description, quantity, unit_price, tax_rate))
    
    if not lines:
        print('Error: Invoice must have at least one line.')
        conn.close()
        return
    
    add_invoice(conn, invoice_number, customer_name, customer_address, issue_date, due_date, 'Draft', notes, lines)
    print('Invoice added to database.')
    conn.close()

def db_list_invoices_cmd():
    conn = get_connection()
    print('Invoices in database:')
    for row in list_invoices(conn):
        print(f"{row[0]}: {row[1]} - {row[5]} - ${row[9]:.2f}")
    conn.close()

def db_get_invoice_cmd():
    conn = get_connection()
    invoice_number = input('Invoice number: ')
    row = get_invoice(conn, invoice_number)
    if not row:
        print('Invoice not found.')
        conn.close()
        return
    
    print(f'Invoice: {row[0]}')
    print(f'Customer: {row[1]}')
    print(f'Address: {row[2]}')
    print(f'Issue date: {row[3]}')
    print(f'Due date: {row[4]}')
    print(f'Status: {row[5]}')
    print(f'Total: ${row[9]:.2f}')
    print(f'Paid: ${row[10]:.2f}')
    print(f'Balance: ${row[9] - row[10]:.2f}')
    
    print('\nInvoice lines:')
    for line_row in get_invoice_lines(conn, invoice_number):
        print(f"  {line_row[1]}: {line_row[2]} x ${line_row[3]:.2f} = ${line_row[6]:.2f}")
    
    conn.close()

def db_record_invoice_payment_cmd():
    conn = get_connection()
    invoice_number = input('Invoice number: ')
    paid_amount = float(input('Paid amount: '))
    update_invoice_payment(conn, invoice_number, paid_amount, '')
    print('Payment recorded.')
    conn.close()

def db_generate_invoice_pdf_cmd():
    """Generate a PDF invoice."""
    from datetime import date
    from pyledger.invoices import Invoice, InvoiceLine, InvoiceStatus
    
    invoice_number = input('Invoice number: ')
    
    # Get company info
    print("Enter company information (or press Enter for defaults):")
    company_name = input('Company name: ') or 'Your Company Name'
    company_address = input('Company address: ') or '123 Business Street\nCity, State 12345'
    company_phone = input('Company phone: ') or '+1 (555) 123-4567'
    company_email = input('Company email: ') or 'info@yourcompany.com'
    company_website = input('Company website: ') or 'www.yourcompany.com'
    
    company_info = {
        'name': company_name,
        'address': company_address,
        'phone': company_phone,
        'email': company_email,
        'website': company_website
    }
    
    conn = get_connection()
    try:
        # Get invoice data
        invoice_data = get_invoice(conn, invoice_number)
        if not invoice_data:
            print(f"❌ Invoice {invoice_number} not found")
            return
            
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
        print(f"✅ PDF generated successfully: {pdf_path}")
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
    finally:
        conn.close()

# --- Purchase Order CLI Functions ---
def db_add_purchase_order_interactive():
    conn = get_connection()
    po_number = input('Purchase order number: ')
    supplier_name = input('Supplier name: ')
    supplier_address = input('Supplier address: ')
    order_date = input('Order date (YYYY-MM-DD): ')
    expected_delivery_date = input('Expected delivery date (YYYY-MM-DD): ')
    notes = input('Notes (optional): ')
    
    lines = []
    while True:
        description = input('Item description (or blank to finish): ')
        if not description:
            break
        quantity = float(input('Quantity: '))
        unit_price = float(input('Unit price: '))
        tax_rate = float(input('Tax rate (0.0-1.0): '))
        lines.append((description, quantity, unit_price, tax_rate))
    
    if not lines:
        print('Error: Purchase order must have at least one line.')
        conn.close()
        return
    
    add_purchase_order(conn, po_number, supplier_name, supplier_address, order_date, expected_delivery_date, 'Draft', notes, lines)
    print('Purchase order added to database.')
    conn.close()

def db_list_purchase_orders_cmd():
    conn = get_connection()
    print('Purchase orders in database:')
    for row in list_purchase_orders(conn):
        print(f"{row[0]}: {row[1]} - {row[5]} - ${row[9]:.2f}")
    conn.close()

def db_get_purchase_order_cmd():
    conn = get_connection()
    po_number = input('Purchase order number: ')
    row = get_purchase_order(conn, po_number)
    if not row:
        print('Purchase order not found.')
        conn.close()
        return
    
    print(f'Purchase Order: {row[0]}')
    print(f'Supplier: {row[1]}')
    print(f'Address: {row[2]}')
    print(f'Order date: {row[3]}')
    print(f'Expected delivery: {row[4]}')
    print(f'Status: {row[5]}')
    print(f'Total: ${row[9]:.2f}')
    print(f'Received: ${row[12]:.2f}')
    
    print('\nPurchase order lines:')
    for line_row in get_purchase_order_lines(conn, po_number):
        print(f"  {line_row[1]}: {line_row[2]} x ${line_row[3]:.2f} (received: {line_row[5]})")
    
    conn.close()

def db_record_purchase_order_receipt_cmd():
    conn = get_connection()
    po_number = input('Purchase order number: ')
    line_id = int(input('Line ID: '))
    received_quantity = float(input('Received quantity: '))
    update_purchase_order_receipt(conn, po_number, line_id, received_quantity, '')
    print('Receipt recorded.')
    conn.close()

# --- Tax filing commands (Form 5472 / pro-forma 1120) ---

def _tax_filing():
    from pyledger.tax_filing import Form5472Filing
    conn = get_connection()
    init_db(conn)
    return conn, Form5472Filing(conn)

def _arg_or_input(args, name, prompt, cast=str):
    value = getattr(args, name.replace('-', '_'), None)
    if value is None:
        value = input(prompt)
    return cast(value)

def tax_check_cmd(args):
    conn, filing = _tax_filing()
    entity_id = _arg_or_input(args, 'entity-id', 'Entity ID: ', int)
    tax_year = _arg_or_input(args, 'tax-year', 'Tax year: ', int)
    result = filing.check_filing_requirement(entity_id, tax_year)
    print(f"Filing required: {'YES' if result['required'] else 'NO'}")
    for reason in result['reasons']:
        print(f"  - {reason}")
    print(f"Forms needed: {', '.join(result['forms_needed']) or 'none'}")
    print(f"Deadline: {result['deadline']} (extended: {result['extended_deadline']})")
    print(f"E-file allowed: {'yes' if result['can_efile'] else 'NO — fax or mail only'}")
    print(f"Fax: {result['submission']['fax']}")
    print(f"Mail: {result['submission']['mail']}")
    penalty = filing.estimate_penalty(tax_year)
    print(f"Penalty exposure if unfiled today: ${penalty['total']:,.0f}")
    print(f"\n{result['disclaimer']}")
    conn.close()

def tax_list_transactions_cmd(args):
    conn, filing = _tax_filing()
    entity_id = _arg_or_input(args, 'entity-id', 'Entity ID: ', int)
    tax_year = _arg_or_input(args, 'tax-year', 'Tax year: ', int)
    txns = filing.list_reportable_transactions(entity_id, tax_year)
    if not txns:
        print('No reportable transactions recorded.')
    for t in txns:
        print(f"#{t['id']} {t['txn_date'] or 'n/a'} {t['txn_type']} "
              f"${t['amount']:,.2f} [{t['source']}] {t['description'] or ''}")
    conn.close()

def tax_5472_generate_cmd(args):
    conn, filing = _tax_filing()
    entity_id = _arg_or_input(args, 'entity-id', 'Entity ID: ', int)
    tax_year = _arg_or_input(args, 'tax-year', 'Tax year: ', int)
    output_dir = getattr(args, 'output_dir', None) or 'filings'
    cause_text = None
    if getattr(args, 'reasonable_cause_file', None):
        with open(args.reasonable_cause_file) as fh:
            cause_text = fh.read().strip()
    result = filing.generate_filing(
        entity_id, tax_year, output_dir,
        include_extension=bool(getattr(args, 'extension', False)),
        reasonable_cause_text=cause_text,
        template_dir=getattr(args, 'template_dir', None))
    if not result['success']:
        print('Validation failed:')
        for e in result['validation']['errors']:
            print(f"  ERROR: {e}")
        conn.close()
        return
    for w in result['validation']['warnings']:
        print(f"  WARNING: {w}")
    print('Generated:')
    for k, v in result['paths'].items():
        print(f"  {k}: {v}")
    print('Next steps:')
    for step in result['next_steps']:
        print(f"  - {step}")
    print(f"\n{result['disclaimer']}")
    conn.close()

def tax_7004_generate_cmd(args):
    from pyledger import irs_pdf
    conn, filing = _tax_filing()
    entity_id = _arg_or_input(args, 'entity-id', 'Entity ID: ', int)
    tax_year = _arg_or_input(args, 'tax-year', 'Tax year: ', int)
    output_dir = getattr(args, 'output_dir', None) or 'filings'
    entity = filing.get_entity(entity_id)
    if entity is None:
        print(f'Entity {entity_id} not found.')
        conn.close()
        return
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f'f7004_{tax_year}.pdf')
    templates = irs_pdf.IRSTemplateManager(
        cache_dir=getattr(args, 'template_dir', None))
    irs_pdf.fill_form_7004(templates.get_template('f7004'),
                           irs_pdf.Form7004Data(entity=entity, tax_year=tax_year),
                           out)
    deadline = filing.get_deadline(tax_year, extended=True,
                                   tax_year_end=entity['tax_year_end'])
    print(f'Generated: {out}')
    print(f'File by the regular deadline to extend filing to {deadline.isoformat()}.')
    conn.close()

def tax_5472_wizard_cmd(args):
    conn, filing = _tax_filing()
    print('=== Form 5472 / Pro-Forma 1120 Filing Wizard ===')
    print('This wizard prepares the annual filing for a foreign-owned')
    print('single-member US LLC (disregarded entity).\n')

    # 1. Entity
    entities = filing.list_entities()
    if entities:
        print('Existing entities:')
        for e in entities:
            print(f"  {e['id']}: {e['name']} ({e['entity_kind']}, EIN {e['ein'] or 'none'})")
        choice = input('Entity ID to use (or ENTER to create new): ').strip()
    else:
        choice = ''
    if choice:
        entity_id = int(choice)
    else:
        print('\n-- New entity --')
        name = input('LLC legal name: ')
        ein = input('EIN (NN-NNNNNNN, ENTER if none yet): ').strip() or None
        address1 = input('Street address: ')
        city = input('City: ')
        state = input('State (e.g. DE): ').strip() or None
        postal = input('ZIP code: ').strip() or None
        formed = input('Formation date (YYYY-MM-DD, ENTER to skip): ').strip() or None
        activity = input('Principal business activity: ').strip() or None
        entity_id = filing.add_entity(
            name, 'foreign_owned_de', address1, city, ein=ein, state=state,
            postal_code=postal, formation_date=formed,
            principal_business_activity=activity)
        print(f'Created entity #{entity_id}')

    # 2. Owner
    owners = filing.list_foreign_owners(entity_id)
    if owners:
        print(f"\nForeign owner on file: {owners[0]['name']} ({owners[0]['country']})")
    else:
        print('\n-- Foreign owner --')
        oname = input('Owner full name: ')
        ocountry = input('Country of residence: ')
        oaddr = input('Street address: ')
        ocity = input('City: ')
        opostal = input('Postal code: ').strip() or None
        oftin = input('Foreign tax ID (ENTER if none): ').strip() or None
        ustin = input('US TIN/SSN/ITIN (ENTER if none): ').strip() or None
        filing.add_foreign_owner(entity_id, oname, ocountry, oaddr, ocity,
                                 postal_code=opostal, foreign_tin=oftin,
                                 us_tin=ustin)

    tax_year = int(input('\nTax year to file for: '))

    # 3. Ledger suggestions
    suggestions = filing.suggest_reportable_transactions(entity_id, tax_year)
    if suggestions:
        print(f'\nFound {len(suggestions)} possible reportable transaction(s) in the ledger:')
        for s in suggestions:
            answer = input(
                f"  {s['date'] or 'n/a'} '{s['description']}' ${s['amount']:,.2f} "
                f"-> {s['suggested_type']} ({s['confidence']}). Confirm? [y/N] ")
            if answer.strip().lower() == 'y':
                filing.confirm_suggested_transaction(
                    entity_id, tax_year, s['journal_entry_id'],
                    s['suggested_type'], s['amount'])
                print('    recorded.')

    # 4. Manual transactions
    from pyledger.tax_filing import ReportableTransactionType
    print('\n-- Additional reportable transactions --')
    print('Types:', ', '.join(t.value for t in ReportableTransactionType))
    while True:
        ttype = input('Transaction type (ENTER to finish): ').strip()
        if not ttype:
            break
        amount = float(input('Amount (USD): '))
        desc = input('Description: ').strip() or None
        tdate = input('Date (YYYY-MM-DD, ENTER to skip): ').strip() or None
        filing.add_reportable_transaction(entity_id, tax_year, ttype, amount,
                                          txn_date=tdate, description=desc)
        print('  recorded.')

    # 5. Validate + generate
    validation = filing.validate_filing_data(entity_id, tax_year)
    for w in validation['warnings']:
        print(f'WARNING: {w}')
    if not validation['valid']:
        print('Cannot generate yet — fix these first:')
        for e in validation['errors']:
            print(f'  ERROR: {e}')
        conn.close()
        return
    if input('\nGenerate the filing package now? [Y/n] ').strip().lower() in ('', 'y'):
        output_dir = input('Output directory [filings]: ').strip() or 'filings'
        include_ext = input('Also generate Form 7004 extension? [y/N] ').strip().lower() == 'y'
        result = filing.generate_filing(entity_id, tax_year, output_dir,
                                        include_extension=include_ext)
        print('Generated:')
        for k, v in result['paths'].items():
            print(f'  {k}: {v}')
        print('Next steps:')
        for step in result['next_steps']:
            print(f'  - {step}')
        print(f"\n{result['disclaimer']}")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='PyLedger Accounting CLI')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('sample', help='Load sample data')
    subparsers.add_parser('balance-sheet', help='Print balance sheet')
    subparsers.add_parser('income-statement', help='Print income statement')
    subparsers.add_parser('cash-flow', help='Print cash flow report')
    subparsers.add_parser('add-account', help='Add a new account interactively')
    subparsers.add_parser('list-accounts', help='List all accounts')
    subparsers.add_parser('add-entry', help='Add a new journal entry interactively')
    subparsers.add_parser('list-entries', help='List all journal entries')
    subparsers.add_parser('save', help='Save accounts and entries to JSON files')
    subparsers.add_parser('load', help='Load accounts and entries from JSON files')
    # Database-backed commands
    subparsers.add_parser('db-init', help='Initialize the database')
    subparsers.add_parser('db-add-account', help='Add a new account to the database')
    subparsers.add_parser('db-list-accounts', help='List all accounts in the database')
    subparsers.add_parser('db-add-entry', help='Add a new journal entry to the database')
    subparsers.add_parser('db-list-entries', help='List all journal entries in the database')
    subparsers.add_parser('db-entry-lines', help='Show lines for a specific journal entry in the database')
    # Invoice commands
    subparsers.add_parser('db-add-invoice', help='Add a new invoice to the database')
    subparsers.add_parser('db-list-invoices', help='List all invoices in the database')
    subparsers.add_parser('db-get-invoice', help='Get details for a specific invoice')
    subparsers.add_parser('db-record-invoice-payment', help='Record a payment for an invoice')
    subparsers.add_parser('db-generate-invoice-pdf', help='Generate a PDF invoice')
    # Purchase order commands
    subparsers.add_parser('db-add-po', help='Add a new purchase order to the database')
    subparsers.add_parser('db-list-pos', help='List all purchase orders in the database')
    subparsers.add_parser('db-get-po', help='Get details for a specific purchase order')
    subparsers.add_parser('db-record-po-receipt', help='Record receipt of items for a purchase order')
    # Tax filing commands (Form 5472 / pro-forma 1120)
    p_check = subparsers.add_parser('tax-check', help='Check Form 5472 filing requirement, deadline, and penalty exposure')
    p_check.add_argument('--entity-id', type=int)
    p_check.add_argument('--tax-year', type=int)
    subparsers.add_parser('tax-5472-wizard', help='Interactive wizard: prepare a Form 5472 + pro-forma 1120 filing')
    p_gen = subparsers.add_parser('tax-5472-generate', help='Generate the Form 5472 filing package (non-interactive)')
    p_gen.add_argument('--entity-id', type=int)
    p_gen.add_argument('--tax-year', type=int)
    p_gen.add_argument('--output-dir', default='filings')
    p_gen.add_argument('--extension', action='store_true', help='Also generate Form 7004')
    p_gen.add_argument('--reasonable-cause-file', help='Text file with reasonable-cause statement for late filing')
    p_gen.add_argument('--template-dir', help='Directory with cached IRS PDF templates')
    p_7004 = subparsers.add_parser('tax-7004-generate', help='Generate Form 7004 extension request')
    p_7004.add_argument('--entity-id', type=int)
    p_7004.add_argument('--tax-year', type=int)
    p_7004.add_argument('--output-dir', default='filings')
    p_7004.add_argument('--template-dir')
    p_list = subparsers.add_parser('tax-list-transactions', help='List reportable transactions for an entity/year')
    p_list.add_argument('--entity-id', type=int)
    p_list.add_argument('--tax-year', type=int)

    args = parser.parse_args()

    # By default, start with empty chart and ledger
    chart = ChartOfAccounts()
    ledger = Ledger(chart)

    if args.command == 'load':
        chart, ledger = load_data()
    elif args.command == 'sample':
        setup_sample_data(chart, ledger)
        print('Sample data loaded.')
    elif args.command == 'add-account':
        add_account_interactive(chart)
    elif args.command == 'list-accounts':
        list_accounts(chart)
    elif args.command == 'add-entry':
        add_journal_entry_interactive(chart, ledger)
    elif args.command == 'list-entries':
        list_journal_entries(ledger)
    elif args.command == 'balance-sheet':
        print('Balance Sheet:')
        print(balance_sheet(chart))
    elif args.command == 'income-statement':
        print('Income Statement:')
        print(income_statement(chart))
    elif args.command == 'cash-flow':
        print('Cash Flow Report:')
        print(cash_flow_report(chart))
    elif args.command == 'save':
        save_data(chart, ledger)
    # Database-backed commands
    elif args.command == 'db-init':
        db_init_cmd()
    elif args.command == 'db-add-account':
        db_add_account_interactive()
    elif args.command == 'db-list-accounts':
        db_list_accounts_cmd()
    elif args.command == 'db-add-entry':
        db_add_entry_interactive()
    elif args.command == 'db-list-entries':
        db_list_entries_cmd()
    elif args.command == 'db-entry-lines':
        db_entry_lines_cmd()
    # Invoice commands
    elif args.command == 'db-add-invoice':
        db_add_invoice_interactive()
    elif args.command == 'db-list-invoices':
        db_list_invoices_cmd()
    elif args.command == 'db-get-invoice':
        db_get_invoice_cmd()
    elif args.command == 'db-record-invoice-payment':
        db_record_invoice_payment_cmd()
    elif args.command == 'db-generate-invoice-pdf':
        db_generate_invoice_pdf_cmd()
    # Purchase order commands
    elif args.command == 'db-add-po':
        db_add_purchase_order_interactive()
    elif args.command == 'db-list-pos':
        db_list_purchase_orders_cmd()
    elif args.command == 'db-get-po':
        db_get_purchase_order_cmd()
    elif args.command == 'db-record-po-receipt':
        db_record_purchase_order_receipt_cmd()
    # Tax filing commands
    elif args.command == 'tax-check':
        tax_check_cmd(args)
    elif args.command == 'tax-5472-wizard':
        tax_5472_wizard_cmd(args)
    elif args.command == 'tax-5472-generate':
        tax_5472_generate_cmd(args)
    elif args.command == 'tax-7004-generate':
        tax_7004_generate_cmd(args)
    elif args.command == 'tax-list-transactions':
        tax_list_transactions_cmd(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()