"""
GAAP Compliance Test Suite

This module tests the GAAP compliance features of PyLedger:
- Revenue Recognition (ASC 606)
- Expense Matching (Matching Principle)
- Materiality
- Consistency
- Audit Trails
- Conservatism
- Going Concern
"""

import os
import json
from datetime import datetime, date
from pyledger.db import get_connection, init_db, add_account, add_journal_entry, add_invoice
from pyledger.accounts import AccountType
from pyledger.gaap_compliance import (
    GAAPCompliance, GAAPPrinciple, RevenueRecognitionMethod
)

class GAAPComplianceTestSuite:
    """Comprehensive GAAP compliance test suite"""
    
    def setup_test_accounts(self, conn):
        """Set up test accounts for GAAP compliance testing"""
        # Assets
        add_account(conn, '1000', 'Cash', AccountType.ASSET, 50000.0)
        add_account(conn, '1100', 'Accounts Receivable', AccountType.ASSET, 25000.0)
        add_account(conn, '1200', 'Inventory', AccountType.ASSET, 15000.0)
        add_account(conn, '1300', 'Equipment', AccountType.ASSET, 30000.0)
        
        # Liabilities
        add_account(conn, '2000', 'Accounts Payable', AccountType.LIABILITY, 20000.0)
        add_account(conn, '2100', 'Notes Payable', AccountType.LIABILITY, 50000.0)
        
        # Equity
        add_account(conn, '3000', 'Owner Equity', AccountType.EQUITY, 100000.0)
        add_account(conn, '3100', 'Retained Earnings', AccountType.EQUITY, 25000.0)
        
        # Revenue
        add_account(conn, '4000', 'Sales Revenue', AccountType.REVENUE, 0.0)
        add_account(conn, '4100', 'Service Revenue', AccountType.REVENUE, 0.0)
        
        # Expenses
        add_account(conn, '5000', 'Cost of Goods Sold', AccountType.EXPENSE, 0.0)
        add_account(conn, '5100', 'Rent Expense', AccountType.EXPENSE, 0.0)
        add_account(conn, '5200', 'Utilities Expense', AccountType.EXPENSE, 0.0)
        add_account(conn, '5300', 'Salaries Expense', AccountType.EXPENSE, 0.0)

def test_1_revenue_recognition_asc606():
    """Test: Revenue Recognition per ASC 606"""
    print("Testing Revenue Recognition (ASC 606)...")
    
    # Clean setup
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    # Set up accounts
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    # Create test invoice
    add_invoice(conn, 'INV-2024-001', 'Test Customer', '123 Test St', 
                '2024-01-15', '2024-02-15', 'pending', 'Test invoice',
                [('Product A', 10, 100.0, 0.08), ('Service B', 5, 200.0, 0.08)])
    
    # Test GAAP compliance
    gaap = GAAPCompliance(conn)
    
    # Test point-in-time recognition
    result = gaap.validate_revenue_recognition(
        invoice_number='INV-2024-001',
        recognition_method=RevenueRecognitionMethod.POINT_IN_TIME,
        performance_obligations=["Delivery of goods/services"],
        start_date='2024-01-15',
        end_date='2024-01-15'
    )
    
    assert result == True, "Revenue recognition validation failed"
    print("✅ Revenue recognition (ASC 606) validated")
    
    conn.close()
    os.remove('test_gaap.db')

def test_2_expense_matching_principle():
    """Test: Expense Matching Principle"""
    print("Testing Expense Matching Principle...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test expense matching
    result = gaap.validate_expense_matching(
        expense_account='5000',  # Cost of Goods Sold
        revenue_account='4000',  # Sales Revenue
        expense_amount=5000.0,
        revenue_amount=10000.0,
        matching_period='2024-Q1',
        justification='COGS matched to sales revenue for Q1 2024'
    )
    
    assert result == True, "Expense matching validation failed"
    print("✅ Expense matching principle validated")
    
    conn.close()
    os.remove('test_gaap.db')

def test_3_materiality_assessment():
    """Test: Materiality Assessment"""
    print("Testing Materiality Assessment...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test materiality assessment
    assessment = gaap.assess_materiality(
        assessment_type="journal_entry",
        actual_amount=5000.0
    )
    
    assert 'is_material' in assessment, "Materiality assessment failed"
    assert 'threshold_amount' in assessment, "Threshold calculation failed"
    print(f"✅ Materiality assessment: {assessment['is_material']} (Threshold: {assessment['threshold_amount']})")
    
    conn.close()
    os.remove('test_gaap.db')

def test_4_consistency_checks():
    """Test: Consistency Checks"""
    print("Testing Consistency Checks...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test consistency check
    result = gaap.check_consistency(
        check_type="revenue_recognition",
        current_method="Point in Time",
        previous_method="Point in Time",
        change_justification="No change in method"
    )
    
    assert result == True, "Consistency check failed"
    print("✅ Consistency check validated")
    
    conn.close()
    os.remove('test_gaap.db')

def test_5_conservatism_principle():
    """Test: Conservatism Principle"""
    print("Testing Conservatism Principle...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test conservatism (understate assets, overstate liabilities)
    result = gaap.apply_conservatism(
        account_code='1100',  # Accounts Receivable (Asset)
        adjustment_amount=1000.0,
        reason="Conservative estimate for doubtful accounts"
    )
    
    assert result == True, "Conservatism principle application failed"
    print("✅ Conservatism principle validated")
    
    conn.close()
    os.remove('test_gaap.db')

def test_6_going_concern_assumption():
    """Test: Going Concern Assumption"""
    print("Testing Going Concern Assumption...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test going concern validation
    going_concern_viable = gaap.validate_going_concern()
    
    assert isinstance(going_concern_viable, bool), "Going concern validation failed"
    print(f"✅ Going concern assumption: {going_concern_viable}")
    
    conn.close()
    os.remove('test_gaap.db')

def test_7_audit_trail():
    """Test: Audit Trail Functionality"""
    print("Testing Audit Trail...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Test audit trail logging
    gaap.log_audit_trail(
        user_id="test_user",
        action="test_action",
        table_name="accounts",
        record_id="1000",
        old_values={"balance": 50000.0},
        new_values={"balance": 55000.0},
        principle=GAAPPrinciple.CONSISTENCY,
        justification="Test audit trail entry"
    )
    
    # Verify audit trail entry
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM gaap_audit_trail')
    count = c.fetchone()[0]
    
    assert count > 0, "Audit trail entry not created"
    print(f"✅ Audit trail: {count} entries logged")
    
    conn.close()
    os.remove('test_gaap.db')

def test_8_gaap_compliance_report():
    """Test: GAAP Compliance Report Generation"""
    print("Testing GAAP Compliance Report...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # Create some test data
    add_invoice(conn, 'INV-2024-002', 'Customer B', '456 Test Ave', 
                '2024-01-20', '2024-02-20', 'pending', 'Test invoice 2',
                [('Product C', 5, 150.0, 0.08)])
    
    gaap.validate_revenue_recognition(
        invoice_number='INV-2024-002',
        recognition_method=RevenueRecognitionMethod.POINT_IN_TIME,
        performance_obligations=["Delivery of goods"],
        start_date='2024-01-20',
        end_date='2024-01-20'
    )
    
    # Generate compliance report
    report = gaap.get_gaap_compliance_report()
    
    assert 'compliance_status' in report, "Compliance report missing status"
    assert 'audit_trail_summary' in report, "Compliance report missing audit summary"
    assert 'revenue_recognition_summary' in report, "Compliance report missing revenue summary"
    
    print(f"✅ GAAP Compliance Report: {report['compliance_status']}")
    print(f"   Audit Trail Entries: {len(report['audit_trail_summary'])}")
    print(f"   Revenue Recognition Methods: {len(report['revenue_recognition_summary'])}")
    
    conn.close()
    os.remove('test_gaap.db')

def test_9_double_entry_gaap_validation():
    """Test: Double-Entry Validation with GAAP Compliance"""
    print("Testing Double-Entry Validation with GAAP...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    # Test valid balanced entry
    add_journal_entry(conn, 'Equipment purchase', [
        ('1300', 5000.0, True),    # Debit Equipment
        ('1000', 5000.0, False),   # Credit Cash
    ])
    
    # Test unbalanced entry (should fail)
    try:
        add_journal_entry(conn, 'Invalid entry', [
            ('1000', 1000.0, True),   # Debit Cash
            ('3000', 500.0, False),   # Credit Equity (unbalanced)
        ])
        assert False, "Unbalanced entry should have failed"
    except ValueError as e:
        assert "not balanced" in str(e) or "balanced" in str(e)
        print("✅ Double-entry validation with GAAP: Unbalanced entries rejected")
    
    conn.close()
    os.remove('test_gaap.db')

def test_10_comprehensive_gaap_scenario():
    """Test: Comprehensive GAAP Compliance Scenario"""
    print("Testing Comprehensive GAAP Scenario...")
    
    if os.path.exists('test_gaap.db'):
        os.remove('test_gaap.db')
    
    conn = get_connection('test_gaap.db')
    init_db(conn)
    
    test_suite = GAAPComplianceTestSuite()
    test_suite.setup_test_accounts(conn)
    
    gaap = GAAPCompliance(conn)
    
    # 1. Create revenue transaction
    add_invoice(conn, 'INV-2024-003', 'Major Customer', '789 Business Blvd', 
                '2024-01-25', '2024-02-25', 'pending', 'Large contract',
                [('Consulting Services', 100, 500.0, 0.08)])
    
    # 2. Apply revenue recognition
    gaap.validate_revenue_recognition(
        invoice_number='INV-2024-003',
        recognition_method=RevenueRecognitionMethod.OVER_TIME,
        performance_obligations=["Consulting services over 3 months"],
        start_date='2024-01-25',
        end_date='2024-04-25'
    )
    
    # 3. Update revenue recognition (33% completion)
    gaap.update_revenue_recognition('INV-2024-003', 33.33)
    
    # 4. Apply expense matching
    gaap.validate_expense_matching(
        expense_account='5300',  # Salaries Expense
        revenue_account='4100',  # Service Revenue
        expense_amount=15000.0,
        revenue_amount=50000.0,
        matching_period='2024-Q1',
        justification='Salaries matched to consulting revenue'
    )
    
    # 5. Assess materiality
    materiality = gaap.assess_materiality(
        assessment_type="large_contract",
        actual_amount=50000.0
    )
    
    # 6. Apply conservatism
    gaap.apply_conservatism(
        account_code='1100',  # Accounts Receivable
        adjustment_amount=2500.0,
        reason="Conservative estimate for large customer"
    )
    
    # 7. Check going concern
    going_concern = gaap.validate_going_concern()
    
    # 8. Generate compliance report
    report = gaap.get_gaap_compliance_report()
    
    # Validate comprehensive scenario
    assert report['compliance_status'] == "GAAP Compliant", "Comprehensive scenario failed compliance"
    assert going_concern == True, "Going concern assumption violated"
    assert materiality['is_material'] == True, "Large contract should be material"
    
    print("✅ Comprehensive GAAP scenario validated")
    print(f"   Compliance Status: {report['compliance_status']}")
    print(f"   Going Concern: {going_concern}")
    print(f"   Materiality: {materiality['is_material']}")
    
    conn.close()
    os.remove('test_gaap.db')

def run_gaap_compliance_tests():
    """Run all GAAP compliance tests"""
    print("🧪 Running GAAP Compliance Test Suite")
    print("=" * 50)
    
    tests = [
        test_1_revenue_recognition_asc606,
        test_2_expense_matching_principle,
        test_3_materiality_assessment,
        test_4_consistency_checks,
        test_5_conservatism_principle,
        test_6_going_concern_assumption,
        test_7_audit_trail,
        test_8_gaap_compliance_report,
        test_9_double_entry_gaap_validation,
        test_10_comprehensive_gaap_scenario
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {str(e)}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 GAAP Compliance Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("🎉 All GAAP compliance tests passed!")
    else:
        print("⚠️  Some GAAP compliance tests failed. Review the implementation.")
    
    return passed, failed

if __name__ == "__main__":
    run_gaap_compliance_tests() 