# Advanced Payment Clearing System Documentation

## Overview

PyLedger's Advanced Payment Clearing System provides sophisticated payment management capabilities for both receivables and payables. This system enables businesses to handle complex payment scenarios with intelligent allocation, comprehensive tracking, and detailed reporting.

## 🎯 Key Features

### 1. **Single Invoice Payment Clearing**
- Clear payments for individual invoices with detailed tracking
- Support for partial and full payment clearing
- Automatic balance calculation and remaining amount tracking
- Comprehensive audit trail with payment references

### 2. **Multiple Invoice Payment Clearing**
- Clear multiple invoices with a single payment
- Intelligent allocation methods:
  - **Proportional**: Allocate based on outstanding amounts
  - **Oldest First**: Prioritize oldest invoices
  - **Largest First**: Prioritize largest outstanding amounts
- Automatic payment distribution and tracking

### 3. **Aging Schedule Generation**
- Generate aging reports for receivables and payables
- Categorize outstanding amounts by aging periods:
  - Current (0-30 days)
  - 30 Days (31-60 days)
  - 60 Days (61-90 days)
  - 90 Days (91-120 days)
  - Over 90 Days (120+ days)
- Comprehensive aging analysis and reporting

### 4. **Payment Summaries and Reports**
- Payment summaries by date range
- Breakdown by payment methods
- Statistical analysis of payment patterns
- Average payment calculations

### 5. **Outstanding Item Tracking**
- Track outstanding invoices and purchase orders
- Customer-specific outstanding invoice queries
- Days overdue calculations
- Outstanding amount tracking

## 🗄️ Database Schema

### Payment Clearings Table
```sql
CREATE TABLE payment_clearings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clearing_date DATE NOT NULL,
    payment_type TEXT NOT NULL, -- 'receivable' or 'payable'
    payment_reference TEXT NOT NULL,
    invoice_number TEXT,
    po_number TEXT,
    customer_supplier_name TEXT NOT NULL,
    original_amount REAL NOT NULL,
    cleared_amount REAL NOT NULL,
    remaining_amount REAL NOT NULL,
    clearing_method TEXT NOT NULL, -- 'full', 'partial', 'multiple'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number),
    FOREIGN KEY(po_number) REFERENCES purchase_orders(po_number)
)
```

### Aging Schedules Table
```sql
CREATE TABLE aging_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_date DATE NOT NULL,
    schedule_type TEXT NOT NULL, -- 'receivable' or 'payable'
    customer_supplier_name TEXT NOT NULL,
    invoice_number TEXT,
    po_number TEXT,
    original_amount REAL NOT NULL,
    current_balance REAL NOT NULL,
    days_overdue INTEGER NOT NULL,
    aging_period TEXT NOT NULL, -- 'current', '30_days', '60_days', '90_days', 'over_90_days'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number),
    FOREIGN KEY(po_number) REFERENCES purchase_orders(po_number)
)
```

## 🔧 Usage Examples

### Python API Usage

#### 1. Single Invoice Payment Clearing
```python
from pyledger.payment_clearing import PaymentClearingManager

manager = PaymentClearingManager()

# Clear payment for a single invoice
result = manager.clear_single_invoice_payment(
    invoice_number='INV-2024-001',
    payment_amount=3000.0,
    payment_date='2024-02-20',
    payment_reference='PAY-001',
    clearing_method='partial'
)

print(f"Payment cleared: ${result['payment_amount']:.2f}")
print(f"Remaining balance: ${result['remaining_balance']:.2f}")
```

#### 2. Multiple Invoice Payment Clearing
```python
# Clear multiple invoices with proportional allocation
result = manager.clear_multiple_invoices_payment(
    invoice_numbers=['INV-2024-002', 'INV-2024-003'],
    total_payment_amount=5000.0,
    payment_date='2024-02-25',
    payment_reference='PAY-002',
    allocation_method='proportional'
)

print(f"Invoices cleared: {result['invoices_cleared']}")
for allocation in result['allocations']:
    print(f"  {allocation['invoice_number']}: ${allocation['amount']:.2f}")
```

#### 3. Aging Report Generation
```python
# Generate aging report for receivables
aging_report = manager.generate_aging_report(
    report_date='2024-03-01',
    schedule_type='receivable'
)

print(f"Total outstanding: ${aging_report['total_amount']:.2f}")
for period, data in aging_report['aging_summary'].items():
    if data['count'] > 0:
        print(f"  {period}: {data['count']} items, ${data['amount']:.2f}")
```

#### 4. Payment Summary
```python
# Get payment summary for a date range
summary = manager.get_payment_summary(
    payment_type='receivable',
    start_date='2024-02-01',
    end_date='2024-03-01'
)

print(f"Total payments: {summary['total_payments']}")
print(f"Total cleared: ${summary['total_cleared']:.2f}")
print(f"Average payment: ${summary['avg_payment']:.2f}")
```

#### 5. Outstanding Items
```python
# Get outstanding invoices
outstanding_invoices = manager.get_outstanding_invoices()

for invoice in outstanding_invoices:
    print(f"Invoice {invoice['invoice_number']}: "
          f"${invoice['outstanding_amount']:.2f} "
          f"({invoice['days_overdue']} days overdue)")

# Get customer-specific outstanding invoices
acme_invoices = manager.get_outstanding_invoices('Acme Corp')
```

## 🌐 REST API Endpoints

### Payment Clearing Endpoints

#### 1. Single Invoice Payment Clearing
```http
POST /payment_clearing/single
Content-Type: application/json

{
    "invoice_number": "INV-2024-001",
    "payment_amount": 3000.0,
    "payment_date": "2024-02-20",
    "payment_reference": "PAY-001",
    "clearing_method": "partial"
}
```

#### 2. Multiple Invoice Payment Clearing
```http
POST /payment_clearing/multiple
Content-Type: application/json

{
    "invoice_numbers": ["INV-2024-002", "INV-2024-003"],
    "total_payment_amount": 5000.0,
    "payment_date": "2024-02-25",
    "payment_reference": "PAY-002",
    "allocation_method": "proportional"
}
```

#### 3. Aging Report Generation
```http
GET /payment_clearing/aging_report?schedule_type=receivable&report_date=2024-03-01
```

#### 4. Payment Summary
```http
GET /payment_clearing/summary?payment_type=receivable&start_date=2024-02-01&end_date=2024-03-01
```

#### 5. Outstanding Invoices
```http
GET /payment_clearing/outstanding_invoices?customer_name=Acme%20Corp
```

#### 6. Outstanding Purchase Orders
```http
GET /payment_clearing/outstanding_purchase_orders?supplier_name=Office%20Supplies%20Co
```

#### 7. Payment Clearings History
```http
GET /payment_clearing/clearings?payment_type=receivable&customer_supplier_name=Acme%20Corp
```

#### 8. Aging Schedule
```http
GET /payment_clearing/aging_schedule?schedule_type=receivable&aging_period=30_days
```

## 📊 Allocation Methods

### 1. Proportional Allocation
- Allocates payment proportionally based on outstanding amounts
- Ensures fair distribution across multiple invoices
- Formula: `allocation = (outstanding_amount / total_outstanding) * payment_amount`

### 2. Oldest First Allocation
- Prioritizes invoices by issue date (oldest first)
- Useful for managing cash flow and reducing aging
- Clears oldest invoices completely before moving to newer ones

### 3. Largest First Allocation
- Prioritizes invoices by outstanding amount (largest first)
- Useful for reducing high-value outstanding amounts
- Clears largest invoices first

## 🔍 Reporting Features

### Aging Report Structure
```json
{
    "report_date": "2024-03-01",
    "schedule_type": "receivable",
    "items_processed": 9,
    "aging_summary": {
        "current": {"count": 0, "amount": 0},
        "30_days": {"count": 1, "amount": 2700.0},
        "60_days": {"count": 8, "amount": 44100.0},
        "90_days": {"count": 0, "amount": 0},
        "over_90_days": {"count": 0, "amount": 0}
    },
    "total_amount": 46800.0,
    "total_count": 9
}
```

### Payment Summary Structure
```json
{
    "payment_type": "receivable",
    "start_date": "2024-02-01",
    "end_date": "2024-03-01",
    "total_payments": 4,
    "total_cleared": 4270.0,
    "total_original": 20570.0,
    "avg_payment": 1067.5,
    "methods": {
        "multiple": {"count": 3, "amount": 1270.0},
        "partial": {"count": 1, "amount": 3000.0}
    }
}
```

## 🛡️ Error Handling

The system includes comprehensive error handling:

- **Invoice Not Found**: Returns 400 error for non-existent invoices
- **Invalid Payment Amount**: Validates payment amounts against outstanding balances
- **Database Errors**: Handles database connection and transaction errors
- **Invalid Allocation Methods**: Validates allocation method parameters

## 🔄 Integration with Existing Systems

### Journal Entry Integration
- Payment clearings automatically update invoice paid amounts
- Journal entries can be generated for payment transactions
- Maintains double-entry accounting integrity

### Invoice and Purchase Order Integration
- Seamlessly integrates with existing invoice and purchase order systems
- Updates payment status and amounts automatically
- Maintains referential integrity with foreign keys

## 🚀 Performance Considerations

- **Indexed Queries**: Database tables include proper indexes for efficient querying
- **Batch Processing**: Multiple invoice clearing supports batch operations
- **Connection Pooling**: Efficient database connection management
- **Caching**: Aging reports can be cached for improved performance

## 📈 Business Benefits

1. **Improved Cash Flow Management**: Better tracking of receivables and payables
2. **Reduced Manual Work**: Automated payment allocation and tracking
3. **Enhanced Reporting**: Comprehensive aging and payment reports
4. **Better Customer Relationships**: Detailed payment history and tracking
5. **Compliance**: Audit trail for all payment transactions
6. **Scalability**: Handles complex payment scenarios efficiently

## 🔧 Configuration

### Database Configuration
```python
# Default database file
DB_FILE = 'pyledger.db'

# Custom database file
manager = PaymentClearingManager(db_file='custom_database.db')
```

### API Configuration
```python
# FastAPI app with payment clearing endpoints
from pyledger.api import app

# Run with uvicorn
# uvicorn pyledger.api:app --reload --port 8000
```

## 📝 Best Practices

1. **Regular Aging Reports**: Generate aging reports monthly for better cash flow management
2. **Payment References**: Use meaningful payment reference numbers for easy tracking
3. **Allocation Strategy**: Choose allocation methods based on business priorities
4. **Data Backup**: Regular database backups for payment clearing data
5. **Audit Trail**: Maintain comprehensive audit trails for compliance
6. **Performance Monitoring**: Monitor query performance for large datasets

## 🔮 Future Enhancements

1. **Multi-Currency Support**: Handle payments in different currencies
2. **Payment Gateway Integration**: Direct integration with payment processors
3. **Automated Payment Scheduling**: Schedule recurring payments
4. **Advanced Analytics**: Machine learning for payment prediction
5. **Mobile Support**: Mobile app for payment management
6. **Real-time Notifications**: WebSocket notifications for payment updates

---

*This documentation covers the complete Advanced Payment Clearing System implementation in PyLedger. For additional support or feature requests, please refer to the project repository.* 