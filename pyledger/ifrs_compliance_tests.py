"""
IFRS Compliance Test Suite

This module tests the IFRS compliance features including:
- Fair Value Measurement (IFRS 13)
- Impairment Testing (IAS 36)
- Revenue Recognition (IFRS 15)
- Leases (IFRS 16)
- Financial Instruments (IFRS 9)
- Consolidation (IFRS 10)
- Presentation Requirements (IAS 1)
"""

import sqlite3
import tempfile
import os
from datetime import datetime
from .ifrs_compliance import (
    IFRSCompliance, IFRSPrinciple, FairValueLevel, ImpairmentType
)

class IFRSComplianceTestSuite:
    """Test suite for IFRS compliance features"""
    
    def __init__(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        self.conn = sqlite3.connect(self.db_path)
        self.ifrs = IFRSCompliance(self.conn)
        self.setup_test_data()
    
    def setup_test_data(self):
        """Set up test accounts and data"""
        c = self.conn.cursor()
        
        # Create test accounts
        accounts = [
            ('1000', 'Cash', 'ASSET', 10000.0),
            ('1100', 'Accounts Receivable', 'ASSET', 5000.0),
            ('1200', 'Inventory', 'ASSET', 15000.0),
            ('1300', 'Property, Plant & Equipment', 'ASSET', 50000.0),
            ('1400', 'Goodwill', 'ASSET', 25000.0),
            ('2000', 'Accounts Payable', 'LIABILITY', 8000.0),
            ('2100', 'Lease Liability', 'LIABILITY', 0.0),
            ('3000', 'Common Stock', 'EQUITY', 50000.0),
            ('4000', 'Revenue', 'REVENUE', 0.0),
            ('5000', 'Cost of Goods Sold', 'EXPENSE', 0.0),
            ('5100', 'Depreciation Expense', 'EXPENSE', 0.0),
            ('5200', 'Impairment Loss', 'EXPENSE', 0.0)
        ]
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_number TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                total_amount REAL NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        
        for code, name, type_, balance in accounts:
            c.execute('INSERT OR REPLACE INTO accounts (code, name, type, balance) VALUES (?, ?, ?, ?)',
                     (code, name, type_, balance))
        
        # Add test entities
        entities = [
            ('Parent Corp', 'Parent'),
            ('Subsidiary Inc', 'Subsidiary')
        ]
        
        for name, type_ in entities:
            c.execute('INSERT OR REPLACE INTO entities (name, type) VALUES (?, ?)',
                     (name, type_))
        
        # Add test invoice
        c.execute('''
            INSERT OR REPLACE INTO invoices (invoice_number, customer_name, total_amount, date)
            VALUES ('INV-001', 'Test Customer', 10000.0, '2024-01-01')
        ''')
        
        self.conn.commit()
    
    def test_fair_value_measurement(self):
        """Test fair value measurement per IFRS 13"""
        print("Testing Fair Value Measurement (IFRS 13)...")
        
        # Test Level 1 fair value measurement
        result = self.ifrs.measure_fair_value(
            asset_code='1000',
            fair_value=10500.0,
            fair_value_level=FairValueLevel.LEVEL_1,
            valuation_technique="Market Price",
            key_inputs={"market_price": 10500.0, "source": "Active Market"}
        )
        
        assert result == True, "Fair value measurement failed"
        
        # Verify the measurement was recorded
        c = self.conn.cursor()
        c.execute('SELECT fair_value, fair_value_level FROM fair_value_measurements WHERE asset_code = ?', ('1000',))
        result = c.fetchone()
        assert result[0] == 10500.0, "Fair value not recorded correctly"
        assert result[1] == FairValueLevel.LEVEL_1.value, "Fair value level not recorded correctly"
        
        print("✅ Fair Value Measurement test passed")
    
    def test_impairment_testing(self):
        """Test impairment testing per IAS 36"""
        print("Testing Impairment Testing (IAS 36)...")
        
        # Test goodwill impairment
        result = self.ifrs.test_impairment(
            asset_code='1400',
            impairment_type=ImpairmentType.GOODWILL,
            carrying_amount=25000.0,
            recoverable_amount=20000.0,
            assumptions={"discount_rate": 0.10, "growth_rate": 0.05}
        )
        
        assert result["impairment_loss"] == 5000.0, "Impairment loss calculation incorrect"
        assert result["is_impaired"] == True, "Impairment not detected"
        assert result["next_test_date"] is not None, "Next test date not set for goodwill"
        
        # Test PP&E impairment
        result = self.ifrs.test_impairment(
            asset_code='1300',
            impairment_type=ImpairmentType.PROPERTY_PLANT_EQUIPMENT,
            carrying_amount=50000.0,
            recoverable_amount=45000.0,
            assumptions={"value_in_use": 45000.0, "fair_value": 44000.0}
        )
        
        assert result["impairment_loss"] == 5000.0, "PP&E impairment loss calculation incorrect"
        assert result["is_impaired"] == True, "PP&E impairment not detected"
        
        print("✅ Impairment Testing test passed")
    
    def test_revenue_recognition_ifrs15(self):
        """Test revenue recognition per IFRS 15"""
        print("Testing Revenue Recognition (IFRS 15)...")
        
        result = self.ifrs.recognize_revenue_ifrs15(
            contract_id='INV-001',
            performance_obligation_id='PO-001',
            total_contract_value=10000.0,
            allocated_transaction_price=10000.0,
            satisfaction_method='Point in Time',
            satisfaction_date='2024-01-01'
        )
        
        assert result == True, "IFRS 15 revenue recognition failed"
        
        # Verify the recognition was recorded
        c = self.conn.cursor()
        c.execute('''
            SELECT total_contract_value, allocated_transaction_price, satisfaction_method 
            FROM ifrs_revenue_recognition WHERE contract_id = ?
        ''', ('INV-001',))
        result = c.fetchone()
        assert result[0] == 10000.0, "Contract value not recorded correctly"
        assert result[1] == 10000.0, "Allocated transaction price not recorded correctly"
        assert result[2] == 'Point in Time', "Satisfaction method not recorded correctly"
        
        print("✅ Revenue Recognition (IFRS 15) test passed")
    
    def test_lease_accounting_ifrs16(self):
        """Test lease accounting per IFRS 16"""
        print("Testing Lease Accounting (IFRS 16)...")
        
        result = self.ifrs.account_for_lease_ifrs16(
            lease_id='2100',
            lease_type='Operating Lease',
            lease_term_months=60,
            lease_payments=12000.0,
            discount_rate=0.08,
            commencement_date='2024-01-01'
        )
        
        assert result["right_of_use_asset"] > 0, "Right-of-use asset not calculated"
        assert result["lease_liability"] > 0, "Lease liability not calculated"
        assert result["lease_term_months"] == 60, "Lease term not recorded correctly"
        
        # Verify the lease accounting was recorded
        c = self.conn.cursor()
        c.execute('''
            SELECT right_of_use_asset, lease_liability, lease_type 
            FROM lease_accounting WHERE lease_id = ?
        ''', ('2100',))
        result = c.fetchone()
        assert result[0] > 0, "Right-of-use asset not recorded"
        assert result[1] > 0, "Lease liability not recorded"
        assert result[2] == 'Operating Lease', "Lease type not recorded correctly"
        
        print("✅ Lease Accounting (IFRS 16) test passed")
    
    def test_financial_instruments_ifrs9(self):
        """Test financial instruments classification per IFRS 9"""
        print("Testing Financial Instruments (IFRS 9)...")
        
        result = self.ifrs.classify_financial_instrument_ifrs9(
            instrument_id='1100',
            instrument_type='Trade Receivable',
            classification='Amortized Cost',
            measurement_basis='Amortized Cost',
            amortized_cost=5000.0
        )
        
        assert result == True, "IFRS 9 classification failed"
        
        # Verify the classification was recorded
        c = self.conn.cursor()
        c.execute('''
            SELECT classification, measurement_basis, instrument_type 
            FROM financial_instruments WHERE instrument_id = ?
        ''', ('1100',))
        result = c.fetchone()
        assert result[0] == 'Amortized Cost', "Classification not recorded correctly"
        assert result[1] == 'Amortized Cost', "Measurement basis not recorded correctly"
        assert result[2] == 'Trade Receivable', "Instrument type not recorded correctly"
        
        print("✅ Financial Instruments (IFRS 9) test passed")
    
    def test_consolidation_ifrs10(self):
        """Test consolidation per IFRS 10"""
        print("Testing Consolidation (IFRS 10)...")
        
        result = self.ifrs.consolidate_entities_ifrs10(
            parent_entity='Parent Corp',
            subsidiary_entity='Subsidiary Inc',
            ownership_percentage=80.0,
            control_assessment='Control Exists',
            consolidation_method='Full Consolidation'
        )
        
        assert result == True, "IFRS 10 consolidation failed"
        
        # Verify the consolidation was recorded
        c = self.conn.cursor()
        c.execute('''
            SELECT ownership_percentage, control_assessment, consolidation_method 
            FROM consolidation WHERE parent_entity = ? AND subsidiary_entity = ?
        ''', ('Parent Corp', 'Subsidiary Inc'))
        result = c.fetchone()
        assert result[0] == 80.0, "Ownership percentage not recorded correctly"
        assert result[1] == 'Control Exists', "Control assessment not recorded correctly"
        assert result[2] == 'Full Consolidation', "Consolidation method not recorded correctly"
        
        print("✅ Consolidation (IFRS 10) test passed")
    
    def test_ifrs_presentation_validation(self):
        """Test IFRS presentation requirements per IAS 1"""
        print("Testing IFRS Presentation Validation (IAS 1)...")
        
        result = self.ifrs.validate_ifrs_presentation()
        
        assert "presentation_compliant" in result, "Presentation validation failed"
        assert "disclosure_count" in result, "Disclosure count not included"
        assert "fair_value_count" in result, "Fair value count not included"
        assert "impairment_count" in result, "Impairment count not included"
        assert "lease_count" in result, "Lease count not included"
        
        print("✅ IFRS Presentation Validation test passed")
    
    def test_ifrs_compliance_report(self):
        """Test IFRS compliance report generation"""
        print("Testing IFRS Compliance Report Generation...")
        
        report = self.ifrs.get_ifrs_compliance_report()
        
        assert "compliance_status" in report, "Compliance status not included"
        assert report["compliance_status"] == "IFRS Compliant", "Compliance status incorrect"
        assert "jurisdiction" in report, "Jurisdiction not included"
        assert report["jurisdiction"] == "International", "Jurisdiction incorrect"
        assert "ifrs_audit_trail_summary" in report, "Audit trail summary not included"
        assert "fair_value_summary" in report, "Fair value summary not included"
        assert "impairment_summary" in report, "Impairment summary not included"
        assert "lease_summary" in report, "Lease summary not included"
        assert "financial_instruments_summary" in report, "Financial instruments summary not included"
        
        print("✅ IFRS Compliance Report test passed")
    
    def test_audit_trail_functionality(self):
        """Test IFRS audit trail functionality"""
        print("Testing IFRS Audit Trail Functionality...")
        
        # Verify audit trail entries were created
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM ifrs_audit_trail')
        audit_count = c.fetchone()[0]
        assert audit_count > 0, "No audit trail entries created"
        
        # Check for specific principles
        c.execute('SELECT principle FROM ifrs_audit_trail WHERE principle = ?', 
                 (IFRSPrinciple.FAIR_VALUE.value,))
        fair_value_entries = c.fetchall()
        assert len(fair_value_entries) > 0, "No fair value audit trail entries"
        
        c.execute('SELECT principle FROM ifrs_audit_trail WHERE principle = ?', 
                 (IFRSPrinciple.IMPAIRMENT.value,))
        impairment_entries = c.fetchall()
        assert len(impairment_entries) > 0, "No impairment audit trail entries"
        
        print("✅ IFRS Audit Trail test passed")
    
    def test_integration_with_gaap(self):
        """Test integration with GAAP compliance"""
        print("Testing Integration with GAAP Compliance...")
        
        # Test that IFRS compliance extends GAAP compliance
        assert hasattr(self.ifrs, 'gaap_compliance'), "IFRS compliance should extend GAAP"
        assert self.ifrs.gaap_compliance is not None, "GAAP compliance not initialized"
        
        # Test that both audit trails work
        c = self.conn.cursor()
        c.execute('SELECT COUNT(*) FROM gaap_audit_trail')
        gaap_audit_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM ifrs_audit_trail')
        ifrs_audit_count = c.fetchone()[0]
        
        assert gaap_audit_count >= 0, "GAAP audit trail should exist"
        assert ifrs_audit_count > 0, "IFRS audit trail should have entries"
        
        print("✅ Integration with GAAP test passed")
    
    def test_comprehensive_ifrs_scenario(self):
        """Test comprehensive IFRS compliance scenario"""
        print("Testing Comprehensive IFRS Compliance Scenario...")
        
        # Simulate a comprehensive IFRS compliance scenario
        # 1. Fair value measurement
        self.ifrs.measure_fair_value(
            asset_code='1200',
            fair_value=16000.0,
            fair_value_level=FairValueLevel.LEVEL_2,
            valuation_technique="Discounted Cash Flow",
            key_inputs={"discount_rate": 0.12, "growth_rate": 0.03}
        )
        
        # 2. Impairment testing
        self.ifrs.test_impairment(
            asset_code='1300',
            impairment_type=ImpairmentType.PROPERTY_PLANT_EQUIPMENT,
            carrying_amount=50000.0,
            recoverable_amount=48000.0,
            assumptions={"value_in_use": 48000.0}
        )
        
        # 3. Revenue recognition
        self.ifrs.recognize_revenue_ifrs15(
            contract_id='INV-001',
            performance_obligation_id='PO-002',
            total_contract_value=10000.0,
            allocated_transaction_price=8000.0,
            satisfaction_method='Over Time',
            progress_measurement='Output Method'
        )
        
        # 4. Lease accounting
        self.ifrs.account_for_lease_ifrs16(
            lease_id='2100',
            lease_type='Finance Lease',
            lease_term_months=36,
            lease_payments=8000.0,
            discount_rate=0.10,
            commencement_date='2024-01-01'
        )
        
        # 5. Financial instruments
        self.ifrs.classify_financial_instrument_ifrs9(
            instrument_id='1100',
            instrument_type='Trade Receivable',
            classification='Amortized Cost',
            measurement_basis='Amortized Cost',
            amortized_cost=5000.0
        )
        
        # 6. Consolidation
        self.ifrs.consolidate_entities_ifrs10(
            parent_entity='Parent Corp',
            subsidiary_entity='Subsidiary Inc',
            ownership_percentage=75.0,
            control_assessment='Control Exists',
            consolidation_method='Full Consolidation'
        )
        
        # 7. Generate comprehensive report
        report = self.ifrs.get_ifrs_compliance_report()
        
        # Verify comprehensive compliance
        assert report["compliance_status"] == "IFRS Compliant", "Should be IFRS compliant"
        assert len(report["fair_value_summary"]) > 0, "Should have fair value measurements"
        assert len(report["impairment_summary"]) > 0, "Should have impairment tests"
        assert len(report["lease_summary"]) > 0, "Should have lease accounting"
        assert len(report["financial_instruments_summary"]) > 0, "Should have financial instruments"
        
        print("✅ Comprehensive IFRS Scenario test passed")
    
    def cleanup(self):
        """Clean up test resources"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

def run_ifrs_compliance_tests():
    """Run all IFRS compliance tests"""
    print("🧪 Running IFRS Compliance Tests...")
    print("=" * 50)
    
    test_suite = IFRSComplianceTestSuite()
    
    try:
        # Run all tests
        test_suite.test_fair_value_measurement()
        test_suite.test_impairment_testing()
        test_suite.test_revenue_recognition_ifrs15()
        test_suite.test_lease_accounting_ifrs16()
        test_suite.test_financial_instruments_ifrs9()
        test_suite.test_consolidation_ifrs10()
        test_suite.test_ifrs_presentation_validation()
        test_suite.test_ifrs_compliance_report()
        test_suite.test_audit_trail_functionality()
        test_suite.test_integration_with_gaap()
        test_suite.test_comprehensive_ifrs_scenario()
        
        print("=" * 50)
        print("✅ All IFRS Compliance Tests Passed!")
        print("🎯 IFRS Compliance Features Validated:")
        print("   • Fair Value Measurement (IFRS 13)")
        print("   • Impairment Testing (IAS 36)")
        print("   • Revenue Recognition (IFRS 15)")
        print("   • Lease Accounting (IFRS 16)")
        print("   • Financial Instruments (IFRS 9)")
        print("   • Consolidation (IFRS 10)")
        print("   • Presentation Requirements (IAS 1)")
        print("   • Audit Trail Functionality")
        print("   • Integration with GAAP Compliance")
        print("   • Comprehensive IFRS Compliance")
        
        return True
        
    except Exception as e:
        print(f"❌ IFRS Compliance Test Failed: {e}")
        return False
        
    finally:
        test_suite.cleanup()

if __name__ == "__main__":
    run_ifrs_compliance_tests() 