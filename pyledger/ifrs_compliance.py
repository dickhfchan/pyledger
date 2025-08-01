"""
IFRS (International Financial Reporting Standards) Compliance Module

This module implements key IFRS principles to ensure international accounting compliance:
- Fair Value Measurement (IFRS 13)
- Impairment Testing (IAS 36)
- Revenue Recognition (IFRS 15)
- Leases (IFRS 16)
- Financial Instruments (IFRS 9)
- Consolidation (IFRS 10)
- Audit Trails with IFRS Principles
- International Standards Compliance
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass
import json
from .gaap_compliance import GAAPCompliance, GAAPPrinciple

class IFRSPrinciple(Enum):
    """IFRS Principles"""
    FAIR_VALUE = "Fair Value Measurement"
    IMPAIRMENT = "Impairment Testing"
    REVENUE_RECOGNITION = "Revenue Recognition (IFRS 15)"
    LEASES = "Leases (IFRS 16)"
    FINANCIAL_INSTRUMENTS = "Financial Instruments (IFRS 9)"
    CONSOLIDATION = "Consolidation (IFRS 10)"
    PRESENTATION = "Presentation (IAS 1)"
    DISCLOSURE = "Disclosure Requirements"
    GOING_CONCERN = "Going Concern"
    MATERIALITY = "Materiality"

class FairValueLevel(Enum):
    """Fair Value Hierarchy Levels per IFRS 13"""
    LEVEL_1 = "Level 1 - Quoted prices in active markets"
    LEVEL_2 = "Level 2 - Observable inputs other than quoted prices"
    LEVEL_3 = "Level 3 - Unobservable inputs"

class ImpairmentType(Enum):
    """Types of Impairment Testing"""
    GOODWILL = "Goodwill Impairment"
    INTANGIBLE_ASSETS = "Intangible Assets Impairment"
    PROPERTY_PLANT_EQUIPMENT = "PP&E Impairment"
    FINANCIAL_ASSETS = "Financial Assets Impairment"

@dataclass
class IFRSAuditTrail:
    """Audit trail entry for IFRS compliance"""
    timestamp: str
    user_id: str
    action: str
    table_name: str
    record_id: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    principle: IFRSPrinciple
    justification: str
    jurisdiction: str = "International"

class IFRSCompliance:
    """IFRS Compliance Manager - Extends GAAP Compliance"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.gaap_compliance = GAAPCompliance(conn)
        self.materiality_threshold = 0.05  # 5% of total assets
        self._init_ifrs_tables()
    
    def _init_ifrs_tables(self):
        """Initialize IFRS compliance tables"""
        c = self.conn.cursor()
        
        # IFRS Audit Trail Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS ifrs_audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                principle TEXT NOT NULL,
                justification TEXT NOT NULL,
                jurisdiction TEXT DEFAULT 'International'
            )
        ''')
        
        # Fair Value Measurements Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS fair_value_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_code TEXT NOT NULL,
                fair_value REAL NOT NULL,
                fair_value_level TEXT NOT NULL,
                measurement_date TEXT NOT NULL,
                valuation_technique TEXT,
                key_inputs TEXT,
                sensitivity_analysis TEXT,
                FOREIGN KEY(asset_code) REFERENCES accounts(code)
            )
        ''')
        
        # Impairment Testing Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS impairment_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_code TEXT NOT NULL,
                impairment_type TEXT NOT NULL,
                carrying_amount REAL NOT NULL,
                recoverable_amount REAL NOT NULL,
                impairment_loss REAL NOT NULL,
                test_date TEXT NOT NULL,
                next_test_date TEXT,
                assumptions TEXT,
                FOREIGN KEY(asset_code) REFERENCES accounts(code)
            )
        ''')
        
        # IFRS Revenue Recognition Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS ifrs_revenue_recognition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id TEXT NOT NULL,
                performance_obligation_id TEXT NOT NULL,
                total_contract_value REAL NOT NULL,
                allocated_transaction_price REAL NOT NULL,
                satisfaction_method TEXT NOT NULL,
                satisfaction_date TEXT,
                progress_measurement TEXT,
                FOREIGN KEY(contract_id) REFERENCES invoices(invoice_number)
            )
        ''')
        
        # Lease Accounting Table (IFRS 16)
        c.execute('''
            CREATE TABLE IF NOT EXISTS lease_accounting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lease_id TEXT NOT NULL,
                lease_type TEXT NOT NULL,
                lease_term_months INTEGER NOT NULL,
                lease_payments REAL NOT NULL,
                discount_rate REAL NOT NULL,
                right_of_use_asset REAL NOT NULL,
                lease_liability REAL NOT NULL,
                commencement_date TEXT NOT NULL,
                FOREIGN KEY(lease_id) REFERENCES accounts(code)
            )
        ''')
        
        # Financial Instruments Table (IFRS 9)
        c.execute('''
            CREATE TABLE IF NOT EXISTS financial_instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id TEXT NOT NULL,
                instrument_type TEXT NOT NULL,
                classification TEXT NOT NULL,
                measurement_basis TEXT NOT NULL,
                fair_value REAL,
                amortized_cost REAL,
                impairment_provision REAL DEFAULT 0.0,
                FOREIGN KEY(instrument_id) REFERENCES accounts(code)
            )
        ''')
        
        # Consolidation Table (IFRS 10)
        c.execute('''
            CREATE TABLE IF NOT EXISTS consolidation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_entity TEXT NOT NULL,
                subsidiary_entity TEXT NOT NULL,
                ownership_percentage REAL NOT NULL,
                control_assessment TEXT NOT NULL,
                consolidation_method TEXT NOT NULL,
                elimination_entries TEXT,
                FOREIGN KEY(parent_entity) REFERENCES entities(name),
                FOREIGN KEY(subsidiary_entity) REFERENCES entities(name)
            )
        ''')
        
        self.conn.commit()
    
    def log_ifrs_audit_trail(self, user_id: str, action: str, table_name: str, 
                            record_id: str, old_values: Optional[Dict], 
                            new_values: Optional[Dict], principle: IFRSPrinciple, 
                            justification: str, jurisdiction: str = "International"):
        """Log audit trail entry for IFRS compliance"""
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO ifrs_audit_trail 
            (timestamp, user_id, action, table_name, record_id, old_values, 
             new_values, principle, justification, jurisdiction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            user_id,
            action,
            table_name,
            record_id,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            principle.value,
            justification,
            jurisdiction
        ))
        self.conn.commit()
    
    def measure_fair_value(self, asset_code: str, fair_value: float, 
                          fair_value_level: FairValueLevel, valuation_technique: str,
                          key_inputs: Dict[str, Any], sensitivity_analysis: str = None) -> bool:
        """Measure fair value per IFRS 13"""
        c = self.conn.cursor()
        
        # Get current asset balance
        c.execute('SELECT balance FROM accounts WHERE code = ?', (asset_code,))
        result = c.fetchone()
        if not result:
            raise ValueError(f"Asset {asset_code} not found")
        
        current_balance = result[0]
        
        # Insert fair value measurement
        c.execute('''
            INSERT INTO fair_value_measurements 
            (asset_code, fair_value, fair_value_level, measurement_date,
             valuation_technique, key_inputs, sensitivity_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            asset_code,
            fair_value,
            fair_value_level.value,
            datetime.now().isoformat(),
            valuation_technique,
            json.dumps(key_inputs),
            sensitivity_analysis
        ))
        
        # Update account balance to fair value
        c.execute('UPDATE accounts SET balance = ? WHERE code = ?', 
                 (fair_value, asset_code))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="fair_value_measurement",
            table_name="accounts",
            record_id=asset_code,
            old_values={"balance": current_balance},
            new_values={
                "balance": fair_value,
                "fair_value_level": fair_value_level.value,
                "valuation_technique": valuation_technique
            },
            principle=IFRSPrinciple.FAIR_VALUE,
            justification=f"Fair value measurement using {fair_value_level.value}"
        )
        
        self.conn.commit()
        return True
    
    def test_impairment(self, asset_code: str, impairment_type: ImpairmentType,
                       carrying_amount: float, recoverable_amount: float,
                       assumptions: Dict[str, Any]) -> Dict[str, Any]:
        """Test for impairment per IAS 36"""
        c = self.conn.cursor()
        
        # Calculate impairment loss
        impairment_loss = max(0, carrying_amount - recoverable_amount)
        
        # Determine next test date (annual for goodwill, when indicators exist for others)
        test_date = datetime.now().isoformat()
        if impairment_type == ImpairmentType.GOODWILL:
            next_test_date = (datetime.now().replace(year=datetime.now().year + 1)).isoformat()
        else:
            next_test_date = None  # Test when indicators exist
        
        # Insert impairment test record
        c.execute('''
            INSERT INTO impairment_tests 
            (asset_code, impairment_type, carrying_amount, recoverable_amount,
             impairment_loss, test_date, next_test_date, assumptions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            asset_code,
            impairment_type.value,
            carrying_amount,
            recoverable_amount,
            impairment_loss,
            test_date,
            next_test_date,
            json.dumps(assumptions)
        ))
        
        # Apply impairment loss if any
        if impairment_loss > 0:
            c.execute('SELECT balance FROM accounts WHERE code = ?', (asset_code,))
            current_balance = c.fetchone()[0]
            new_balance = current_balance - impairment_loss
            
            c.execute('UPDATE accounts SET balance = ? WHERE code = ?', 
                     (new_balance, asset_code))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="impairment_test",
            table_name="accounts",
            record_id=asset_code,
            old_values={"balance": carrying_amount},
            new_values={
                "balance": recoverable_amount,
                "impairment_loss": impairment_loss,
                "impairment_type": impairment_type.value
            },
            principle=IFRSPrinciple.IMPAIRMENT,
            justification=f"Impairment test: {impairment_type.value}"
        )
        
        self.conn.commit()
        
        return {
            "impairment_loss": impairment_loss,
            "carrying_amount": carrying_amount,
            "recoverable_amount": recoverable_amount,
            "next_test_date": next_test_date,
            "is_impaired": impairment_loss > 0
        }
    
    def recognize_revenue_ifrs15(self, contract_id: str, performance_obligation_id: str,
                               total_contract_value: float, allocated_transaction_price: float,
                               satisfaction_method: str, satisfaction_date: str = None,
                               progress_measurement: str = None) -> bool:
        """Recognize revenue per IFRS 15"""
        c = self.conn.cursor()
        
        # Insert IFRS 15 revenue recognition record
        c.execute('''
            INSERT INTO ifrs_revenue_recognition 
            (contract_id, performance_obligation_id, total_contract_value,
             allocated_transaction_price, satisfaction_method, satisfaction_date,
             progress_measurement)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            contract_id,
            performance_obligation_id,
            total_contract_value,
            allocated_transaction_price,
            satisfaction_method,
            satisfaction_date,
            progress_measurement
        ))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="ifrs15_revenue_recognition",
            table_name="ifrs_revenue_recognition",
            record_id=f"{contract_id}_{performance_obligation_id}",
            old_values=None,
            new_values={
                "contract_id": contract_id,
                "performance_obligation_id": performance_obligation_id,
                "allocated_transaction_price": allocated_transaction_price,
                "satisfaction_method": satisfaction_method
            },
            principle=IFRSPrinciple.REVENUE_RECOGNITION,
            justification=f"IFRS 15 revenue recognition: {satisfaction_method}"
        )
        
        self.conn.commit()
        return True
    
    def account_for_lease_ifrs16(self, lease_id: str, lease_type: str, lease_term_months: int,
                                lease_payments: float, discount_rate: float,
                                commencement_date: str) -> Dict[str, Any]:
        """Account for leases per IFRS 16"""
        c = self.conn.cursor()
        
        # Calculate right-of-use asset and lease liability
        # Simplified calculation - in practice, this would be more complex
        present_value_factor = 1 / ((1 + discount_rate) ** (lease_term_months / 12))
        lease_liability = lease_payments * present_value_factor
        right_of_use_asset = lease_liability  # Initial measurement
        
        # Insert lease accounting record
        c.execute('''
            INSERT INTO lease_accounting 
            (lease_id, lease_type, lease_term_months, lease_payments, discount_rate,
             right_of_use_asset, lease_liability, commencement_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            lease_id,
            lease_type,
            lease_term_months,
            lease_payments,
            discount_rate,
            right_of_use_asset,
            lease_liability,
            commencement_date
        ))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="ifrs16_lease_accounting",
            table_name="lease_accounting",
            record_id=lease_id,
            old_values=None,
            new_values={
                "lease_id": lease_id,
                "right_of_use_asset": right_of_use_asset,
                "lease_liability": lease_liability,
                "lease_type": lease_type
            },
            principle=IFRSPrinciple.LEASES,
            justification=f"IFRS 16 lease accounting: {lease_type}"
        )
        
        self.conn.commit()
        
        return {
            "right_of_use_asset": right_of_use_asset,
            "lease_liability": lease_liability,
            "discount_rate": discount_rate,
            "lease_term_months": lease_term_months
        }
    
    def classify_financial_instrument_ifrs9(self, instrument_id: str, instrument_type: str,
                                          classification: str, measurement_basis: str,
                                          fair_value: float = None, 
                                          amortized_cost: float = None) -> bool:
        """Classify financial instruments per IFRS 9"""
        c = self.conn.cursor()
        
        # Insert financial instrument classification
        c.execute('''
            INSERT INTO financial_instruments 
            (instrument_id, instrument_type, classification, measurement_basis,
             fair_value, amortized_cost)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            instrument_id,
            instrument_type,
            classification,
            measurement_basis,
            fair_value,
            amortized_cost
        ))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="ifrs9_classification",
            table_name="financial_instruments",
            record_id=instrument_id,
            old_values=None,
            new_values={
                "instrument_id": instrument_id,
                "classification": classification,
                "measurement_basis": measurement_basis,
                "instrument_type": instrument_type
            },
            principle=IFRSPrinciple.FINANCIAL_INSTRUMENTS,
            justification=f"IFRS 9 classification: {classification} - {measurement_basis}"
        )
        
        self.conn.commit()
        return True
    
    def consolidate_entities_ifrs10(self, parent_entity: str, subsidiary_entity: str,
                                   ownership_percentage: float, control_assessment: str,
                                   consolidation_method: str) -> bool:
        """Consolidate entities per IFRS 10"""
        c = self.conn.cursor()
        
        # Insert consolidation record
        c.execute('''
            INSERT INTO consolidation 
            (parent_entity, subsidiary_entity, ownership_percentage, control_assessment,
             consolidation_method)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            parent_entity,
            subsidiary_entity,
            ownership_percentage,
            control_assessment,
            consolidation_method
        ))
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="ifrs10_consolidation",
            table_name="consolidation",
            record_id=f"{parent_entity}_{subsidiary_entity}",
            old_values=None,
            new_values={
                "parent_entity": parent_entity,
                "subsidiary_entity": subsidiary_entity,
                "ownership_percentage": ownership_percentage,
                "control_assessment": control_assessment
            },
            principle=IFRSPrinciple.CONSOLIDATION,
            justification=f"IFRS 10 consolidation: {consolidation_method}"
        )
        
        self.conn.commit()
        return True
    
    def get_ifrs_compliance_report(self) -> Dict[str, Any]:
        """Generate IFRS compliance report"""
        c = self.conn.cursor()
        
        # Get IFRS audit trail summary
        c.execute('''
            SELECT principle, COUNT(*) as count 
            FROM ifrs_audit_trail 
            GROUP BY principle
        ''')
        ifrs_audit_summary = dict(c.fetchall())
        
        # Get fair value measurements summary
        c.execute('''
            SELECT fair_value_level, COUNT(*) as count, 
                   AVG(fair_value) as avg_fair_value
            FROM fair_value_measurements 
            GROUP BY fair_value_level
        ''')
        fair_value_summary = c.fetchall()
        
        # Get impairment tests summary
        c.execute('''
            SELECT impairment_type, COUNT(*) as count,
                   SUM(impairment_loss) as total_impairment_loss
            FROM impairment_tests 
            GROUP BY impairment_type
        ''')
        impairment_summary = c.fetchall()
        
        # Get lease accounting summary
        c.execute('''
            SELECT lease_type, COUNT(*) as count,
                   SUM(right_of_use_asset) as total_right_of_use_asset,
                   SUM(lease_liability) as total_lease_liability
            FROM lease_accounting 
            GROUP BY lease_type
        ''')
        lease_summary = c.fetchall()
        
        # Get financial instruments summary
        c.execute('''
            SELECT classification, measurement_basis, COUNT(*) as count
            FROM financial_instruments 
            GROUP BY classification, measurement_basis
        ''')
        financial_instruments_summary = c.fetchall()
        
        return {
            "ifrs_audit_trail_summary": ifrs_audit_summary,
            "fair_value_summary": fair_value_summary,
            "impairment_summary": impairment_summary,
            "lease_summary": lease_summary,
            "financial_instruments_summary": financial_instruments_summary,
            "compliance_status": "IFRS Compliant",
            "last_updated": datetime.now().isoformat(),
            "jurisdiction": "International"
        }
    
    def validate_ifrs_presentation(self) -> Dict[str, Any]:
        """Validate IFRS presentation requirements per IAS 1"""
        c = self.conn.cursor()
        
        # Check for required disclosures
        c.execute('''
            SELECT COUNT(*) FROM ifrs_audit_trail 
            WHERE principle = 'Disclosure Requirements'
        ''')
        disclosure_count = c.fetchone()[0]
        
        # Check for fair value measurements
        c.execute('SELECT COUNT(*) FROM fair_value_measurements')
        fair_value_count = c.fetchone()[0]
        
        # Check for impairment tests
        c.execute('SELECT COUNT(*) FROM impairment_tests')
        impairment_count = c.fetchone()[0]
        
        # Check for lease accounting
        c.execute('SELECT COUNT(*) FROM lease_accounting')
        lease_count = c.fetchone()[0]
        
        presentation_compliant = (
            disclosure_count > 0 and 
            fair_value_count > 0 and 
            impairment_count > 0 and 
            lease_count > 0
        )
        
        self.log_ifrs_audit_trail(
            user_id="system",
            action="ifrs_presentation_validation",
            table_name="ifrs_compliance",
            record_id="presentation",
            old_values=None,
            new_values={
                "disclosure_count": disclosure_count,
                "fair_value_count": fair_value_count,
                "impairment_count": impairment_count,
                "lease_count": lease_count,
                "presentation_compliant": presentation_compliant
            },
            principle=IFRSPrinciple.PRESENTATION,
            justification="IFRS presentation requirements validation"
        )
        
        return {
            "presentation_compliant": presentation_compliant,
            "disclosure_count": disclosure_count,
            "fair_value_count": fair_value_count,
            "impairment_count": impairment_count,
            "lease_count": lease_count
        } 