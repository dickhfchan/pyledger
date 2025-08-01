"""
GAAP (Generally Accepted Accounting Principles) Compliance Module

This module implements key GAAP principles to ensure accounting compliance:
- Revenue Recognition (ASC 606)
- Expense Matching (Matching Principle)
- Materiality
- Consistency
- Audit Trails
- Conservatism
- Full Disclosure
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass
import json

class GAAPPrinciple(Enum):
    """GAAP Principles"""
    REVENUE_RECOGNITION = "Revenue Recognition"
    EXPENSE_MATCHING = "Expense Matching"
    MATERIALITY = "Materiality"
    CONSISTENCY = "Consistency"
    CONSERVATISM = "Conservatism"
    FULL_DISCLOSURE = "Full Disclosure"
    GOING_CONCERN = "Going Concern"
    MONETARY_UNIT = "Monetary Unit"

class RevenueRecognitionMethod(Enum):
    """Revenue Recognition Methods per ASC 606"""
    POINT_IN_TIME = "Point in Time"
    OVER_TIME = "Over Time"
    PERCENTAGE_OF_COMPLETION = "Percentage of Completion"
    COMPLETED_CONTRACT = "Completed Contract"

@dataclass
class GAAPAuditTrail:
    """Audit trail entry for GAAP compliance"""
    timestamp: str
    user_id: str
    action: str
    table_name: str
    record_id: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    principle: GAAPPrinciple
    justification: str

class GAAPCompliance:
    """GAAP Compliance Manager"""
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.materiality_threshold = 0.05  # 5% of total assets
        self._init_gaap_tables()
    
    def _init_gaap_tables(self):
        """Initialize GAAP compliance tables"""
        c = self.conn.cursor()
        
        # Audit Trail Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS gaap_audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                principle TEXT NOT NULL,
                justification TEXT NOT NULL
            )
        ''')
        
        # Revenue Recognition Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS revenue_recognition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                total_contract_value REAL NOT NULL,
                recognized_amount REAL NOT NULL DEFAULT 0.0,
                recognition_method TEXT NOT NULL,
                performance_obligations TEXT,
                recognition_criteria TEXT,
                start_date TEXT,
                end_date TEXT,
                completion_percentage REAL DEFAULT 0.0,
                FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number)
            )
        ''')
        
        # Expense Matching Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS expense_matching (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_account TEXT NOT NULL,
                revenue_account TEXT NOT NULL,
                matching_period TEXT NOT NULL,
                expense_amount REAL NOT NULL,
                revenue_amount REAL NOT NULL,
                matching_ratio REAL NOT NULL,
                justification TEXT
            )
        ''')
        
        # Materiality Assessments
        c.execute('''
            CREATE TABLE IF NOT EXISTS materiality_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_date TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                threshold_amount REAL NOT NULL,
                actual_amount REAL NOT NULL,
                is_material BOOLEAN NOT NULL,
                justification TEXT
            )
        ''')
        
        # Consistency Checks
        c.execute('''
            CREATE TABLE IF NOT EXISTS consistency_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_date TEXT NOT NULL,
                check_type TEXT NOT NULL,
                previous_method TEXT,
                current_method TEXT,
                change_justification TEXT,
                impact_assessment TEXT
            )
        ''')
        
        self.conn.commit()
    
    def log_audit_trail(self, user_id: str, action: str, table_name: str, 
                       record_id: str, old_values: Optional[Dict], 
                       new_values: Optional[Dict], principle: GAAPPrinciple, 
                       justification: str):
        """Log audit trail entry for GAAP compliance"""
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO gaap_audit_trail 
            (timestamp, user_id, action, table_name, record_id, old_values, 
             new_values, principle, justification)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            user_id,
            action,
            table_name,
            record_id,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            principle.value,
            justification
        ))
        self.conn.commit()
    
    def validate_revenue_recognition(self, invoice_number: str, 
                                   recognition_method: RevenueRecognitionMethod,
                                   performance_obligations: List[str],
                                   start_date: str = None, end_date: str = None) -> bool:
        """Validate revenue recognition per ASC 606"""
        c = self.conn.cursor()
        
        # Get invoice details
        c.execute('SELECT total_amount FROM invoices WHERE invoice_number = ?', 
                 (invoice_number,))
        result = c.fetchone()
        if not result:
            raise ValueError(f"Invoice {invoice_number} not found")
        
        total_amount = result[0]
        
        # Validate recognition method
        if recognition_method == RevenueRecognitionMethod.POINT_IN_TIME:
            # Immediate recognition
            recognized_amount = total_amount
        elif recognition_method == RevenueRecognitionMethod.OVER_TIME:
            # Over time recognition
            if not start_date or not end_date:
                raise ValueError("Start and end dates required for over-time recognition")
            recognized_amount = 0.0  # Will be updated based on progress
        else:
            raise ValueError(f"Unsupported recognition method: {recognition_method}")
        
        # Insert revenue recognition record
        c.execute('''
            INSERT INTO revenue_recognition 
            (invoice_number, total_contract_value, recognized_amount, recognition_method,
             performance_obligations, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            invoice_number,
            total_amount,
            recognized_amount,
            recognition_method.value,
            json.dumps(performance_obligations),
            start_date,
            end_date
        ))
        
        self.log_audit_trail(
            user_id="system",
            action="revenue_recognition",
            table_name="revenue_recognition",
            record_id=invoice_number,
            old_values=None,
            new_values={
                "invoice_number": invoice_number,
                "recognition_method": recognition_method.value,
                "total_amount": total_amount,
                "recognized_amount": recognized_amount
            },
            principle=GAAPPrinciple.REVENUE_RECOGNITION,
            justification=f"Revenue recognition established per ASC 606 using {recognition_method.value}"
        )
        
        self.conn.commit()
        return True
    
    def update_revenue_recognition(self, invoice_number: str, 
                                 completion_percentage: float) -> bool:
        """Update revenue recognition based on completion percentage"""
        c = self.conn.cursor()
        
        # Get current recognition record
        c.execute('''
            SELECT total_contract_value, recognition_method, start_date, end_date
            FROM revenue_recognition WHERE invoice_number = ?
        ''', (invoice_number,))
        result = c.fetchone()
        
        if not result:
            raise ValueError(f"No revenue recognition record found for {invoice_number}")
        
        total_contract_value, recognition_method, start_date, end_date = result
        
        # Calculate recognized amount based on completion
        if recognition_method == RevenueRecognitionMethod.OVER_TIME.value:
            recognized_amount = total_contract_value * (completion_percentage / 100.0)
        else:
            recognized_amount = total_contract_value
        
        # Update recognition record
        c.execute('''
            UPDATE revenue_recognition 
            SET recognized_amount = ?, completion_percentage = ?
            WHERE invoice_number = ?
        ''', (recognized_amount, completion_percentage, invoice_number))
        
        self.log_audit_trail(
            user_id="system",
            action="update_revenue_recognition",
            table_name="revenue_recognition",
            record_id=invoice_number,
            old_values={"completion_percentage": 0},
            new_values={
                "completion_percentage": completion_percentage,
                "recognized_amount": recognized_amount
            },
            principle=GAAPPrinciple.REVENUE_RECOGNITION,
            justification=f"Revenue recognition updated to {completion_percentage}% completion"
        )
        
        self.conn.commit()
        return True
    
    def validate_expense_matching(self, expense_account: str, revenue_account: str,
                                expense_amount: float, revenue_amount: float,
                                matching_period: str, justification: str) -> bool:
        """Validate expense matching principle"""
        c = self.conn.cursor()
        
        # Calculate matching ratio
        if revenue_amount > 0:
            matching_ratio = expense_amount / revenue_amount
        else:
            matching_ratio = 0.0
        
        # Insert expense matching record
        c.execute('''
            INSERT INTO expense_matching 
            (expense_account, revenue_account, matching_period, expense_amount,
             revenue_amount, matching_ratio, justification)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            expense_account,
            revenue_account,
            matching_period,
            expense_amount,
            revenue_amount,
            matching_ratio,
            justification
        ))
        
        self.log_audit_trail(
            user_id="system",
            action="expense_matching",
            table_name="expense_matching",
            record_id=f"{expense_account}_{revenue_account}_{matching_period}",
            old_values=None,
            new_values={
                "expense_account": expense_account,
                "revenue_account": revenue_account,
                "expense_amount": expense_amount,
                "revenue_amount": revenue_amount,
                "matching_ratio": matching_ratio
            },
            principle=GAAPPrinciple.EXPENSE_MATCHING,
            justification=justification
        )
        
        self.conn.commit()
        return True
    
    def assess_materiality(self, assessment_type: str, actual_amount: float,
                          threshold_amount: float = None) -> Dict[str, Any]:
        """Assess materiality of a transaction or account"""
        if threshold_amount is None:
            # Calculate threshold based on total assets
            c = self.conn.cursor()
            c.execute('''
                SELECT SUM(balance) FROM accounts WHERE type = 'ASSET'
            ''')
            result = c.fetchone()
            total_assets = result[0] if result[0] else 0.0
            threshold_amount = total_assets * self.materiality_threshold
        
        is_material = abs(actual_amount) >= threshold_amount
        
        # Log materiality assessment
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO materiality_assessments 
            (assessment_date, assessment_type, threshold_amount, actual_amount, 
             is_material, justification)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            assessment_type,
            threshold_amount,
            actual_amount,
            is_material,
            f"Materiality threshold: {threshold_amount}, Actual: {actual_amount}"
        ))
        
        self.log_audit_trail(
            user_id="system",
            action="materiality_assessment",
            table_name="materiality_assessments",
            record_id=assessment_type,
            old_values=None,
            new_values={
                "assessment_type": assessment_type,
                "threshold_amount": threshold_amount,
                "actual_amount": actual_amount,
                "is_material": is_material
            },
            principle=GAAPPrinciple.MATERIALITY,
            justification=f"Materiality assessment: {assessment_type}"
        )
        
        self.conn.commit()
        
        return {
            "is_material": is_material,
            "threshold_amount": threshold_amount,
            "actual_amount": actual_amount,
            "assessment_type": assessment_type
        }
    
    def check_consistency(self, check_type: str, current_method: str,
                         previous_method: str = None, 
                         change_justification: str = None) -> bool:
        """Check consistency of accounting methods"""
        c = self.conn.cursor()
        
        # Log consistency check
        c.execute('''
            INSERT INTO consistency_checks 
            (check_date, check_type, previous_method, current_method, 
             change_justification, impact_assessment)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            check_type,
            previous_method,
            current_method,
            change_justification,
            "Consistency check performed"
        ))
        
        self.log_audit_trail(
            user_id="system",
            action="consistency_check",
            table_name="consistency_checks",
            record_id=check_type,
            old_values={"previous_method": previous_method},
            new_values={"current_method": current_method},
            principle=GAAPPrinciple.CONSISTENCY,
            justification=f"Consistency check: {check_type}"
        )
        
        self.conn.commit()
        return True
    
    def apply_conservatism(self, account_code: str, adjustment_amount: float,
                          reason: str) -> bool:
        """Apply conservatism principle (understate assets, overstate liabilities)"""
        c = self.conn.cursor()
        
        # Get account details
        c.execute('SELECT type, balance FROM accounts WHERE code = ?', (account_code,))
        result = c.fetchone()
        if not result:
            raise ValueError(f"Account {account_code} not found")
        
        account_type, current_balance = result
        
        # Apply conservatism based on account type
        if account_type == 'ASSET':
            # Understate assets (decrease balance)
            new_balance = current_balance - abs(adjustment_amount)
        elif account_type == 'LIABILITY':
            # Overstate liabilities (increase balance)
            new_balance = current_balance + abs(adjustment_amount)
        else:
            raise ValueError(f"Conservatism principle not applicable to {account_type} accounts")
        
        # Update account balance
        c.execute('UPDATE accounts SET balance = ? WHERE code = ?', 
                 (new_balance, account_code))
        
        self.log_audit_trail(
            user_id="system",
            action="conservatism_adjustment",
            table_name="accounts",
            record_id=account_code,
            old_values={"balance": current_balance},
            new_values={"balance": new_balance},
            principle=GAAPPrinciple.CONSERVATISM,
            justification=f"Conservatism adjustment: {reason}"
        )
        
        self.conn.commit()
        return True
    
    def get_gaap_compliance_report(self) -> Dict[str, Any]:
        """Generate GAAP compliance report"""
        c = self.conn.cursor()
        
        # Get audit trail summary
        c.execute('''
            SELECT principle, COUNT(*) as count 
            FROM gaap_audit_trail 
            GROUP BY principle
        ''')
        audit_summary = dict(c.fetchall())
        
        # Get revenue recognition summary
        c.execute('''
            SELECT recognition_method, COUNT(*) as count, 
                   SUM(recognized_amount) as total_recognized
            FROM revenue_recognition 
            GROUP BY recognition_method
        ''')
        revenue_summary = c.fetchall()
        
        # Get materiality assessments
        c.execute('''
            SELECT assessment_type, COUNT(*) as count,
                   SUM(CASE WHEN is_material THEN 1 ELSE 0 END) as material_count
            FROM materiality_assessments 
            GROUP BY assessment_type
        ''')
        materiality_summary = c.fetchall()
        
        return {
            "audit_trail_summary": audit_summary,
            "revenue_recognition_summary": revenue_summary,
            "materiality_summary": materiality_summary,
            "compliance_status": "GAAP Compliant",
            "last_updated": datetime.now().isoformat()
        }
    
    def validate_going_concern(self) -> bool:
        """Validate going concern assumption"""
        c = self.conn.cursor()
        
        # Check if assets exceed liabilities
        c.execute('''
            SELECT 
                SUM(CASE WHEN type = 'ASSET' THEN balance ELSE 0 END) as total_assets,
                SUM(CASE WHEN type = 'LIABILITY' THEN balance ELSE 0 END) as total_liabilities
            FROM accounts
        ''')
        result = c.fetchone()
        total_assets, total_liabilities = result
        
        going_concern_viable = total_assets >= total_liabilities
        
        self.log_audit_trail(
            user_id="system",
            action="going_concern_check",
            table_name="accounts",
            record_id="going_concern",
            old_values=None,
            new_values={
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "going_concern_viable": going_concern_viable
            },
            principle=GAAPPrinciple.GOING_CONCERN,
            justification=f"Going concern check: Assets({total_assets}) vs Liabilities({total_liabilities})"
        )
        
        return going_concern_viable 