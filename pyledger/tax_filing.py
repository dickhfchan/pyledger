"""
IRS Form 5472 / Pro-Forma 1120 Tax Filing Module

Compliance support for foreign-owned US entities under IRC §6038A/§6038C:
- Foreign-owned single-member LLCs (disregarded entities) must file Form 5472
  attached to a pro-forma Form 1120 for any year with reportable transactions,
  even with zero income. They cannot e-file: fax 855-887-7737 or mail to
  IRS Ogden, UT (M/S 6112, Attn: PIN Unit).
- 25%+ foreign-owned US corporations attach Form 5472 to their regular 1120.

Penalty for non-filing: $25,000 per form per year (IRC §6038A(d)), plus
$25,000 per 30-day period continuing beyond 90 days after IRS notice.

DISCLAIMER: This module assists with form preparation and is not tax advice.
Consult a qualified tax professional for your specific situation.
"""

import hashlib
import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


DISCLAIMER = (
    "This document was prepared with PyLedger software assistance. "
    "It is not tax advice. Review with a qualified tax professional before filing."
)

# The Form 1120 jurat. Accepting it is the taxpayer's personal legal act:
# software must display it verbatim and record the acceptance, never accept
# it on the signer's behalf.
PERJURY_DECLARATION = (
    "Under penalties of perjury, I declare that I have examined this "
    "return, including accompanying schedules and statements, and to the "
    "best of my knowledge and belief, it is true, correct, and complete. "
    "Declaration of preparer (other than taxpayer) is based on all "
    "information of which preparer has any knowledge."
)

# IRC §6038A(d) — flat statutory amounts, not inflation-indexed.
BASE_PENALTY_PER_FORM = 25000.0
CONTINUATION_PENALTY_PER_PERIOD = 25000.0
CONTINUATION_GRACE_DAYS = 90
CONTINUATION_PERIOD_DAYS = 30

IRS_FAX_NUMBER = "855-887-7737"
IRS_MAILING_ADDRESS = (
    "Internal Revenue Service, 1973 Rulon White Blvd, "
    "M/S 6112 Attn: PIN Unit, Ogden, UT 84201"
)


class EntityKind(Enum):
    """Kind of US entity subject to Form 5472 reporting."""
    FOREIGN_OWNED_DE = "foreign_owned_de"
    FOREIGN_OWNED_CORPORATION = "foreign_owned_corporation"


class FilingStatus(Enum):
    """Lifecycle status of a filing for one entity + tax year."""
    DRAFT = "draft"
    GENERATED = "generated"
    FILED = "filed"


class ReportableTransactionType(Enum):
    """Form 5472 reportable transaction categories (Part IV / Part V)."""
    SALES_TO_RELATED = "sales_to_related"
    PURCHASES_FROM_RELATED = "purchases_from_related"
    RENTS_ROYALTIES_RECEIVED = "rents_royalties_received"
    RENTS_ROYALTIES_PAID = "rents_royalties_paid"
    SERVICE_FEES_RECEIVED = "service_fees_received"
    SERVICE_FEES_PAID = "service_fees_paid"
    INTEREST_RECEIVED = "interest_received"
    INTEREST_PAID = "interest_paid"
    LOAN_FROM_OWNER = "loan_from_owner"
    LOAN_TO_OWNER = "loan_to_owner"
    CAPITAL_CONTRIBUTION = "capital_contribution"
    DISTRIBUTION = "distribution"
    EXPENSES_PAID_BY_OWNER = "expenses_paid_by_owner"
    FORMATION_DISSOLUTION_COSTS = "formation_dissolution_costs"
    OTHER = "other"


class TaxPrinciple(Enum):
    """Tax-compliance audit-trail taxonomy (mirrors GAAPPrinciple usage)."""
    INFORMATION_REPORTING = "Information Reporting (IRC 6038A)"
    RECORD_KEEPING = "Record Keeping"
    FILING = "Filing"


# Form 5472 Part IV monetary lines (Rev. Dec 2023: received = lines 9-21,
# totalled on 22; paid = lines 23-35, totalled on 36). None => not a Part IV
# line; DE-typical items (contributions, distributions, formation costs,
# expenses paid by owner) are described in a Part V attachment statement.
PART_IV_LINE_FOR_TYPE: Dict[ReportableTransactionType, Optional[str]] = {
    ReportableTransactionType.SALES_TO_RELATED: "9",
    ReportableTransactionType.RENTS_ROYALTIES_RECEIVED: "13a",
    ReportableTransactionType.SERVICE_FEES_RECEIVED: "15",
    ReportableTransactionType.INTEREST_RECEIVED: "18",
    ReportableTransactionType.LOAN_FROM_OWNER: "17b",
    ReportableTransactionType.PURCHASES_FROM_RELATED: "23",
    ReportableTransactionType.RENTS_ROYALTIES_PAID: "27a",
    ReportableTransactionType.SERVICE_FEES_PAID: "29",
    ReportableTransactionType.INTEREST_PAID: "32",
    ReportableTransactionType.LOAN_TO_OWNER: "31b",
    ReportableTransactionType.CAPITAL_CONTRIBUTION: None,
    ReportableTransactionType.DISTRIBUTION: None,
    ReportableTransactionType.EXPENSES_PAID_BY_OWNER: None,
    ReportableTransactionType.FORMATION_DISSOLUTION_COSTS: None,
    ReportableTransactionType.OTHER: None,
}

# Keyword heuristics for classifying ledger activity as reportable transactions.
# Order matters: first match wins. (phrase, txn_type, confidence)
_CLASSIFICATION_RULES: List[tuple] = [
    ("capital contribution", ReportableTransactionType.CAPITAL_CONTRIBUTION, "high"),
    ("owner contribution", ReportableTransactionType.CAPITAL_CONTRIBUTION, "high"),
    ("member contribution", ReportableTransactionType.CAPITAL_CONTRIBUTION, "high"),
    ("paid-in capital", ReportableTransactionType.CAPITAL_CONTRIBUTION, "medium"),
    ("distribution", ReportableTransactionType.DISTRIBUTION, "high"),
    ("owner draw", ReportableTransactionType.DISTRIBUTION, "high"),
    ("member draw", ReportableTransactionType.DISTRIBUTION, "high"),
    ("dividend", ReportableTransactionType.DISTRIBUTION, "medium"),
    ("loan from owner", ReportableTransactionType.LOAN_FROM_OWNER, "high"),
    ("loan from member", ReportableTransactionType.LOAN_FROM_OWNER, "high"),
    ("due to member", ReportableTransactionType.LOAN_FROM_OWNER, "medium"),
    ("due to owner", ReportableTransactionType.LOAN_FROM_OWNER, "medium"),
    ("loan to owner", ReportableTransactionType.LOAN_TO_OWNER, "high"),
    ("loan to member", ReportableTransactionType.LOAN_TO_OWNER, "high"),
    ("due from member", ReportableTransactionType.LOAN_TO_OWNER, "medium"),
    ("due from owner", ReportableTransactionType.LOAN_TO_OWNER, "medium"),
    ("formation", ReportableTransactionType.FORMATION_DISSOLUTION_COSTS, "high"),
    ("incorporation", ReportableTransactionType.FORMATION_DISSOLUTION_COSTS, "high"),
    ("registered agent", ReportableTransactionType.FORMATION_DISSOLUTION_COSTS, "medium"),
    ("dissolution", ReportableTransactionType.FORMATION_DISSOLUTION_COSTS, "high"),
    ("paid by owner", ReportableTransactionType.EXPENSES_PAID_BY_OWNER, "high"),
    ("paid by member", ReportableTransactionType.EXPENSES_PAID_BY_OWNER, "high"),
    ("owner", ReportableTransactionType.OTHER, "low"),
    ("member", ReportableTransactionType.OTHER, "low"),
]


@dataclass
class TaxAuditTrail:
    """Audit trail entry for tax filing compliance."""
    timestamp: str
    user_id: str
    action: str
    table_name: str
    record_id: str
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    principle: TaxPrinciple
    justification: str


class Form5472Filing:
    """Form 5472 / pro-forma 1120 filing manager.

    Mirrors the GAAPCompliance pattern: takes a live sqlite3 connection,
    owns its schema, and writes an audit trail for every mutation.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._init_tax_tables()

    def _init_tax_tables(self) -> None:
        """Initialize tax filing tables."""
        c = self.conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS filing_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ein TEXT,
                entity_kind TEXT NOT NULL CHECK(entity_kind IN
                    ('foreign_owned_de','foreign_owned_corporation')),
                address_line1 TEXT NOT NULL,
                address_line2 TEXT,
                city TEXT NOT NULL,
                state TEXT,
                postal_code TEXT,
                country TEXT NOT NULL DEFAULT 'US',
                formation_date TEXT,
                country_of_organization TEXT NOT NULL DEFAULT 'US',
                tax_year_end TEXT NOT NULL DEFAULT '12-31',
                principal_business_activity TEXT,
                principal_business_activity_code TEXT,
                functional_currency TEXT NOT NULL DEFAULT 'USD',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS foreign_owners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                name TEXT NOT NULL,
                owner_kind TEXT NOT NULL DEFAULT 'individual',
                address_line1 TEXT NOT NULL,
                address_line2 TEXT,
                city TEXT NOT NULL,
                state_or_province TEXT,
                postal_code TEXT,
                country TEXT NOT NULL,
                country_of_citizenship_or_organization TEXT NOT NULL,
                country_of_tax_residence TEXT NOT NULL,
                us_tin TEXT,
                foreign_tin TEXT,
                ownership_pct REAL NOT NULL,
                is_direct_owner INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS reportable_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                tax_year INTEGER NOT NULL,
                txn_type TEXT NOT NULL,
                amount REAL NOT NULL,
                txn_date TEXT,
                description TEXT,
                journal_entry_id INTEGER REFERENCES journal_entries(id),
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS tax_account_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                account_code TEXT NOT NULL REFERENCES accounts(code),
                txn_type TEXT NOT NULL,
                UNIQUE(entity_id, account_code)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS form_filings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                tax_year INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                form_5472_path TEXT,
                form_1120_path TEXT,
                form_7004_path TEXT,
                reasonable_cause_path TEXT,
                part_v_statement_path TEXT,
                generated_at TEXT,
                filed_date TEXT,
                filing_method TEXT,
                UNIQUE(entity_id, tax_year)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS filing_declarations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                tax_year INTEGER NOT NULL,
                declaration_text TEXT NOT NULL,
                signer_name TEXT NOT NULL,
                signer_title TEXT NOT NULL,
                signature_kind TEXT NOT NULL DEFAULT 'typed',
                signed_date TEXT NOT NULL,
                accepted_at TEXT NOT NULL,
                files_sha256 TEXT NOT NULL,
                UNIQUE(entity_id, tax_year)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS tax_audit_trail (
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

        self.conn.commit()

    def log_audit_trail(self, user_id: str, action: str, table_name: str,
                        record_id: str, old_values: Optional[Dict[str, Any]],
                        new_values: Optional[Dict[str, Any]],
                        principle: TaxPrinciple, justification: str) -> None:
        """Log audit trail entry for tax compliance."""
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO tax_audit_trail
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

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_entity(self, name: str, entity_kind: str, address_line1: str,
                   city: str, country: str = "US", ein: Optional[str] = None,
                   address_line2: Optional[str] = None,
                   state: Optional[str] = None,
                   postal_code: Optional[str] = None,
                   formation_date: Optional[str] = None,
                   country_of_organization: str = "US",
                   tax_year_end: str = "12-31",
                   principal_business_activity: Optional[str] = None,
                   principal_business_activity_code: Optional[str] = None,
                   functional_currency: str = "USD",
                   user_id: str = "system") -> int:
        """Register a filing entity (LLC or corporation). Returns entity id."""
        EntityKind(entity_kind)  # validate
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO filing_entities
            (name, ein, entity_kind, address_line1, address_line2, city, state,
             postal_code, country, formation_date, country_of_organization,
             tax_year_end, principal_business_activity,
             principal_business_activity_code, functional_currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, ein, entity_kind, address_line1, address_line2, city,
              state, postal_code, country, formation_date,
              country_of_organization, tax_year_end,
              principal_business_activity, principal_business_activity_code,
              functional_currency))
        self.conn.commit()
        entity_id = int(c.lastrowid or 0)
        self.log_audit_trail(
            user_id, "CREATE", "filing_entities", str(entity_id), None,
            {"name": name, "entity_kind": entity_kind, "ein": ein},
            TaxPrinciple.RECORD_KEEPING, "Registered filing entity")
        return entity_id

    def get_entity(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a filing entity as a dict, or None."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM filing_entities WHERE id = ?", (entity_id,))
        row = c.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))

    def list_entities(self) -> List[Dict[str, Any]]:
        """List all filing entities."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM filing_entities ORDER BY id")
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def add_foreign_owner(self, entity_id: int, name: str, country: str,
                          address_line1: str, city: str,
                          country_of_citizenship_or_organization: Optional[str] = None,
                          country_of_tax_residence: Optional[str] = None,
                          owner_kind: str = "individual",
                          address_line2: Optional[str] = None,
                          state_or_province: Optional[str] = None,
                          postal_code: Optional[str] = None,
                          us_tin: Optional[str] = None,
                          foreign_tin: Optional[str] = None,
                          ownership_pct: float = 100.0,
                          is_direct_owner: bool = True,
                          user_id: str = "system") -> int:
        """Register a foreign owner for an entity. Returns owner id."""
        citizenship = country_of_citizenship_or_organization or country
        residence = country_of_tax_residence or country
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO foreign_owners
            (entity_id, name, owner_kind, address_line1, address_line2, city,
             state_or_province, postal_code, country,
             country_of_citizenship_or_organization, country_of_tax_residence,
             us_tin, foreign_tin, ownership_pct, is_direct_owner)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entity_id, name, owner_kind, address_line1, address_line2, city,
              state_or_province, postal_code, country, citizenship, residence,
              us_tin, foreign_tin, ownership_pct, int(is_direct_owner)))
        self.conn.commit()
        owner_id = int(c.lastrowid or 0)
        self.log_audit_trail(
            user_id, "CREATE", "foreign_owners", str(owner_id), None,
            {"entity_id": entity_id, "name": name,
             "ownership_pct": ownership_pct},
            TaxPrinciple.RECORD_KEEPING, "Registered foreign owner")
        return owner_id

    def list_foreign_owners(self, entity_id: int) -> List[Dict[str, Any]]:
        """List foreign owners for an entity."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM foreign_owners WHERE entity_id = ? ORDER BY id",
                  (entity_id,))
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def map_account(self, entity_id: int, account_code: str, txn_type: str,
                    user_id: str = "system") -> int:
        """Map a ledger account to a reportable transaction type."""
        ReportableTransactionType(txn_type)  # validate
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO tax_account_mappings (entity_id, account_code, txn_type)
            VALUES (?, ?, ?)
            ON CONFLICT(entity_id, account_code) DO UPDATE SET txn_type = excluded.txn_type
        ''', (entity_id, account_code, txn_type))
        self.conn.commit()
        mapping_id = int(c.lastrowid or 0)
        self.log_audit_trail(
            user_id, "UPSERT", "tax_account_mappings", str(mapping_id), None,
            {"entity_id": entity_id, "account_code": account_code,
             "txn_type": txn_type},
            TaxPrinciple.RECORD_KEEPING, "Mapped account to transaction type")
        return mapping_id

    def add_reportable_transaction(self, entity_id: int, tax_year: int,
                                   txn_type: str, amount: float,
                                   txn_date: Optional[str] = None,
                                   description: Optional[str] = None,
                                   journal_entry_id: Optional[int] = None,
                                   source: str = "manual",
                                   user_id: str = "system") -> int:
        """Record a reportable transaction. Returns transaction id."""
        ReportableTransactionType(txn_type)  # validate
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO reportable_transactions
            (entity_id, tax_year, txn_type, amount, txn_date, description,
             journal_entry_id, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entity_id, tax_year, txn_type, amount, txn_date, description,
              journal_entry_id, source))
        self.conn.commit()
        txn_id = int(c.lastrowid or 0)
        self.log_audit_trail(
            user_id, "CREATE", "reportable_transactions", str(txn_id), None,
            {"entity_id": entity_id, "tax_year": tax_year,
             "txn_type": txn_type, "amount": amount},
            TaxPrinciple.INFORMATION_REPORTING, "Recorded reportable transaction")
        return txn_id

    def list_reportable_transactions(self, entity_id: int,
                                     tax_year: int) -> List[Dict[str, Any]]:
        """List reportable transactions for an entity and tax year."""
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM reportable_transactions
            WHERE entity_id = ? AND tax_year = ? ORDER BY id
        ''', (entity_id, tax_year))
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def transaction_totals_by_type(self, entity_id: int,
                                   tax_year: int) -> Dict[str, float]:
        """Sum reportable transaction amounts grouped by type."""
        c = self.conn.cursor()
        c.execute('''
            SELECT txn_type, SUM(amount) FROM reportable_transactions
            WHERE entity_id = ? AND tax_year = ? GROUP BY txn_type
        ''', (entity_id, tax_year))
        return {row[0]: float(row[1]) for row in c.fetchall()}

    # ------------------------------------------------------------------
    # Rules engine
    # ------------------------------------------------------------------

    def get_deadline(self, tax_year: int, extended: bool = False,
                     tax_year_end: str = "12-31") -> date:
        """Filing deadline: 15th day of the 4th month after year end.

        Calendar-year filers: April 15 of the following year; extension via
        Form 7004 adds 6 months (October 15).
        """
        end_month, end_day = (int(p) for p in tax_year_end.split("-"))
        # Year in which this tax year ends.
        end_date = date(tax_year, end_month, end_day)
        # 15th day of the 4th month after year end.
        month = end_month + 4
        year = end_date.year
        if month > 12:
            month -= 12
            year += 1
        deadline = date(year, month, 15)
        if extended:
            month = deadline.month + 6
            year = deadline.year
            if month > 12:
                month -= 12
                year += 1
            deadline = date(year, month, 15)
        return deadline

    def estimate_penalty(self, tax_year: int,
                         as_of: Optional[date] = None,
                         filed_date: Optional[date] = None,
                         irs_notice_date: Optional[date] = None,
                         num_forms: int = 1,
                         extended: bool = False) -> Dict[str, Any]:
        """Estimate IRC §6038A(d) penalty exposure for a late/missed filing."""
        as_of = as_of or date.today()
        deadline = self.get_deadline(tax_year, extended=extended)
        effective = filed_date or as_of
        is_late = effective > deadline

        base = BASE_PENALTY_PER_FORM * num_forms if is_late else 0.0
        continuation_periods = 0
        continuation = 0.0
        if is_late and irs_notice_date is not None:
            grace_end = irs_notice_date + timedelta(days=CONTINUATION_GRACE_DAYS)
            if effective > grace_end:
                days_over = (effective - grace_end).days
                continuation_periods = -(-days_over // CONTINUATION_PERIOD_DAYS)
                continuation = (CONTINUATION_PENALTY_PER_PERIOD
                                * continuation_periods * num_forms)

        total = base + continuation
        if not is_late:
            explanation = f"Filing is on time (deadline {deadline.isoformat()})."
        else:
            explanation = (
                f"Late filing: deadline was {deadline.isoformat()}. Base penalty "
                f"${base:,.0f} ({num_forms} form(s) x ${BASE_PENALTY_PER_FORM:,.0f}"
                f" per IRC 6038A(d))."
            )
            if continuation_periods:
                explanation += (
                    f" Plus {continuation_periods} continuation period(s) of "
                    f"${CONTINUATION_PENALTY_PER_PERIOD:,.0f} beyond 90 days "
                    f"after IRS notice: ${continuation:,.0f}."
                )
            explanation += (
                " A reasonable-cause statement may support penalty abatement."
            )
        return {
            "is_late": is_late,
            "deadline": deadline.isoformat(),
            "base_penalty": base,
            "continuation_periods": continuation_periods,
            "continuation_penalty": continuation,
            "total": total,
            "explanation": explanation,
        }

    def check_filing_requirement(self, entity_id: int,
                                 tax_year: int) -> Dict[str, Any]:
        """Determine whether Form 5472 (+ pro-forma 1120) is required."""
        entity = self.get_entity(entity_id)
        if entity is None:
            raise ValueError(f"Entity {entity_id} not found")
        owners = self.list_foreign_owners(entity_id)
        transactions = self.list_reportable_transactions(entity_id, tax_year)
        kind = EntityKind(entity["entity_kind"])

        reasons: List[str] = []
        required = False
        forms_needed: List[str] = []

        if kind is EntityKind.FOREIGN_OWNED_DE:
            has_foreign_owner = len(owners) > 0
            if has_foreign_owner and transactions:
                required = True
                forms_needed = ["5472", "1120-proforma"]
                reasons.append(
                    "Foreign-owned US disregarded entity with reportable "
                    "transactions must file Form 5472 attached to a pro-forma "
                    "Form 1120 (required even with zero income)."
                )
            elif has_foreign_owner:
                reasons.append(
                    "No reportable transactions recorded for this tax year. "
                    "Note: formation costs, capital contributions, and expenses "
                    "paid by the owner all count as reportable transactions — "
                    "verify none occurred before skipping the filing."
                )
            else:
                reasons.append("No foreign owner registered for this entity.")
            can_efile = False
        else:
            qualifying = [o for o in owners if o["ownership_pct"] >= 25.0]
            if qualifying and transactions:
                required = True
                forms_needed = ["5472"]
                reasons.append(
                    "US corporation that is 25%+ foreign-owned with reportable "
                    "transactions must attach Form 5472 to its Form 1120."
                )
            elif qualifying:
                reasons.append(
                    "No reportable transactions recorded for this tax year."
                )
            else:
                reasons.append(
                    "No 25%+ foreign shareholder registered for this entity."
                )
            can_efile = True

        deadline = self.get_deadline(tax_year,
                                     tax_year_end=entity["tax_year_end"])
        extended = self.get_deadline(tax_year, extended=True,
                                     tax_year_end=entity["tax_year_end"])
        return {
            "required": required,
            "reasons": reasons,
            "entity_kind": kind.value,
            "has_reportable_transactions": bool(transactions),
            "transaction_count": len(transactions),
            "foreign_owner_count": len(owners),
            "can_efile": can_efile,
            "forms_needed": forms_needed,
            "deadline": deadline.isoformat(),
            "extended_deadline": extended.isoformat(),
            "submission": {
                "fax": IRS_FAX_NUMBER,
                "mail": IRS_MAILING_ADDRESS,
            },
            "disclaimer": DISCLAIMER,
        }

    def classify_transaction(self, description: str,
                             account_code: Optional[str] = None,
                             amount: float = 0.0,
                             is_debit: bool = True) -> Dict[str, Any]:
        """Suggest a reportable transaction type from free text heuristics."""
        text = description.lower()
        for phrase, txn_type, confidence in _CLASSIFICATION_RULES:
            if phrase in text:
                return {
                    "suggested_type": txn_type.value,
                    "confidence": confidence,
                    "rationale": f"Description matches '{phrase}'",
                }
        return {
            "suggested_type": None,
            "confidence": "low",
            "rationale": "No owner/related-party keywords found",
        }

    def suggest_reportable_transactions(self, entity_id: int,
                                        tax_year: int) -> List[Dict[str, Any]]:
        """Scan the ledger for likely reportable transactions.

        Mapped accounts yield high-confidence suggestions; unmapped entries are
        classified by keyword heuristics. Entries already confirmed for this
        entity/year are skipped.
        """
        c = self.conn.cursor()

        c.execute('''
            SELECT account_code, txn_type FROM tax_account_mappings
            WHERE entity_id = ?
        ''', (entity_id,))
        mappings = dict(c.fetchall())

        c.execute('''
            SELECT journal_entry_id FROM reportable_transactions
            WHERE entity_id = ? AND tax_year = ? AND journal_entry_id IS NOT NULL
        ''', (entity_id, tax_year))
        already_linked = {row[0] for row in c.fetchall()}

        c.execute('''
            SELECT je.id, je.description, je.date, jl.account_code, jl.amount,
                   jl.is_debit, a.name
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            LEFT JOIN accounts a ON a.code = jl.account_code
            WHERE substr(je.date, 1, 4) = ?
            ORDER BY je.id
        ''', (str(tax_year),))

        suggestions: List[Dict[str, Any]] = []
        seen: set = set()
        # Mapped-account lines take priority over keyword matches from other
        # lines of the same entry, so process them first.
        rows = sorted(c.fetchall(),
                      key=lambda r: (r[3] not in mappings, r[0]))
        for (entry_id, description, entry_date, account_code, amount,
             is_debit, account_name) in rows:
            if entry_id in already_linked:
                continue

            if account_code in mappings:
                suggestion_type = mappings[account_code]
                confidence = "high"
                rationale = f"Account {account_code} is mapped to this type"
            else:
                text = f"{description or ''} {account_name or ''}"
                result = self.classify_transaction(
                    text, account_code, amount, bool(is_debit))
                if result["suggested_type"] is None:
                    continue
                suggestion_type = result["suggested_type"]
                confidence = result["confidence"]
                rationale = result["rationale"]

            key = (entry_id, suggestion_type)
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({
                "journal_entry_id": entry_id,
                "description": description,
                "date": entry_date,
                "account_code": account_code,
                "amount": abs(float(amount)),
                "suggested_type": suggestion_type,
                "confidence": confidence,
                "rationale": rationale,
            })
        return suggestions

    def confirm_suggested_transaction(self, entity_id: int, tax_year: int,
                                      journal_entry_id: int, txn_type: str,
                                      amount: float,
                                      user_id: str = "system") -> int:
        """Persist a ledger suggestion as a confirmed reportable transaction."""
        c = self.conn.cursor()
        c.execute("SELECT description, date FROM journal_entries WHERE id = ?",
                  (journal_entry_id,))
        row = c.fetchone()
        description, txn_date = (row if row else (None, None))
        return self.add_reportable_transaction(
            entity_id, tax_year, txn_type, amount,
            txn_date=txn_date, description=description,
            journal_entry_id=journal_entry_id,
            source="ledger_confirmed", user_id=user_id)

    def validate_filing_data(self, entity_id: int,
                             tax_year: int) -> Dict[str, Any]:
        """Validate that the data needed to generate the forms is complete."""
        import re

        errors: List[str] = []
        warnings: List[str] = []

        entity = self.get_entity(entity_id)
        if entity is None:
            return {"valid": False,
                    "errors": [f"Entity {entity_id} not found"],
                    "warnings": []}

        if not entity["ein"]:
            errors.append("Entity has no EIN. An EIN is required to file "
                          "Form 5472 (apply with Form SS-4).")
        elif not re.match(r"^\d{2}-?\d{7}$", entity["ein"]):
            errors.append(f"EIN '{entity['ein']}' is not in NN-NNNNNNN format.")

        for field in ("address_line1", "city"):
            if not entity[field]:
                errors.append(f"Entity {field} is missing.")

        owners = self.list_foreign_owners(entity_id)
        if not owners:
            errors.append("No foreign owner registered.")
        else:
            if not any(o["ownership_pct"] >= 25.0 for o in owners):
                errors.append("No owner with ownership >= 25% registered.")
            for o in owners:
                if not o["us_tin"] and not o["foreign_tin"]:
                    warnings.append(
                        f"Owner '{o['name']}' has no US or foreign TIN; "
                        "'FOREIGNUS' will be printed per Form 5472 instructions.")
                for field in ("address_line1", "city", "country"):
                    if not o[field]:
                        errors.append(f"Owner '{o['name']}' {field} is missing.")

        transactions = self.list_reportable_transactions(entity_id, tax_year)
        if not transactions:
            warnings.append("No reportable transactions recorded for "
                            f"{tax_year}; filing may not be required.")
        for t in transactions:
            if t["amount"] <= 0:
                errors.append(
                    f"Transaction {t['id']} has non-positive amount.")

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_filing(self, entity_id: int, tax_year: int, output_dir: str,
                        include_extension: bool = False,
                        reasonable_cause_text: Optional[str] = None,
                        user_id: str = "system",
                        template_dir: Optional[str] = None) -> Dict[str, Any]:
        """Generate the filing package PDFs for an entity + tax year.

        Produces the filled Form 5472, pro-forma Form 1120 (with the
        'Foreign-owned U.S. DE' banner), optional Form 7004 extension,
        optional reasonable-cause statement, and the Part V attachment
        statement for DE-typical transactions.
        """
        import os
        # Lazy import so core pyledger works without pypdf/reportlab installed.
        from pyledger import irs_pdf

        validation = self.validate_filing_data(entity_id, tax_year)
        if not validation["valid"]:
            return {"success": False, "validation": validation}

        entity = self.get_entity(entity_id)
        assert entity is not None
        owners = self.list_foreign_owners(entity_id)
        owner = max(owners, key=lambda o: o["ownership_pct"])
        transactions = self.list_reportable_transactions(entity_id, tax_year)
        totals = self.transaction_totals_by_type(entity_id, tax_year)

        os.makedirs(output_dir, exist_ok=True)
        templates = irs_pdf.IRSTemplateManager(
            cache_dir=template_dir)

        paths: Dict[str, Optional[str]] = {
            "form_5472_path": None,
            "form_1120_path": None,
            "form_7004_path": None,
            "reasonable_cause_path": None,
            "part_v_statement_path": None,
        }

        is_de = entity["entity_kind"] == EntityKind.FOREIGN_OWNED_DE.value

        data_5472 = irs_pdf.Form5472Data(
            entity=entity, owner=owner, tax_year=tax_year,
            totals_by_type=totals, is_de=is_de,
            is_initial_year=self._is_initial_return(entity, tax_year))
        out_5472 = os.path.join(output_dir, f"f5472_{tax_year}.pdf")
        irs_pdf.fill_form_5472(templates.get_template("f5472"),
                               data_5472, out_5472)
        paths["form_5472_path"] = out_5472

        if is_de:
            data_1120 = irs_pdf.Form1120ProFormaData(
                entity=entity, tax_year=tax_year,
                is_initial_return=self._is_initial_return(entity, tax_year))
            out_1120 = os.path.join(output_dir,
                                    f"f1120_proforma_{tax_year}.pdf")
            irs_pdf.fill_form_1120_proforma(templates.get_template("f1120"),
                                            data_1120, out_1120)
            paths["form_1120_path"] = out_1120

        if include_extension:
            data_7004 = irs_pdf.Form7004Data(entity=entity, tax_year=tax_year)
            out_7004 = os.path.join(output_dir, f"f7004_{tax_year}.pdf")
            irs_pdf.fill_form_7004(templates.get_template("f7004"),
                                   data_7004, out_7004)
            paths["form_7004_path"] = out_7004

        if reasonable_cause_text:
            out_rc = os.path.join(output_dir,
                                  f"reasonable_cause_{tax_year}.pdf")
            irs_pdf.render_reasonable_cause_statement(
                entity, tax_year, reasonable_cause_text, out_rc)
            paths["reasonable_cause_path"] = out_rc

        part_v_types = {t for t, line in PART_IV_LINE_FOR_TYPE.items()
                        if line is None}
        part_v_txns = [t for t in transactions
                       if ReportableTransactionType(t["txn_type"])
                       in part_v_types]
        if is_de and part_v_txns:
            out_pv = os.path.join(output_dir,
                                  f"part_v_statement_{tax_year}.pdf")
            irs_pdf.render_part_v_statement(entity, owner, part_v_txns, out_pv)
            paths["part_v_statement_path"] = out_pv

        now = datetime.now().isoformat()
        c = self.conn.cursor()
        c.execute('''
            INSERT INTO form_filings
            (entity_id, tax_year, status, form_5472_path, form_1120_path,
             form_7004_path, reasonable_cause_path, part_v_statement_path,
             generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, tax_year) DO UPDATE SET
                status = excluded.status,
                form_5472_path = excluded.form_5472_path,
                form_1120_path = excluded.form_1120_path,
                form_7004_path = excluded.form_7004_path,
                reasonable_cause_path = excluded.reasonable_cause_path,
                part_v_statement_path = excluded.part_v_statement_path,
                generated_at = excluded.generated_at
        ''', (entity_id, tax_year, FilingStatus.GENERATED.value,
              paths["form_5472_path"], paths["form_1120_path"],
              paths["form_7004_path"], paths["reasonable_cause_path"],
              paths["part_v_statement_path"], now))
        self.conn.commit()

        self.log_audit_trail(
            user_id, "GENERATE", "form_filings",
            f"{entity_id}/{tax_year}", None,
            {k: v for k, v in paths.items() if v},
            TaxPrinciple.FILING, "Generated filing package")

        next_steps = [
            "Print the generated forms and review every field.",
            "Sign the pro-forma Form 1120 (the 5472 itself is not signed "
            "for a DE filing)." if is_de else
            "Attach Form 5472 to the corporation's Form 1120.",
        ]
        if is_de:
            next_steps.append(
                f"Fax the package to the IRS at {IRS_FAX_NUMBER}, or mail "
                f"it to: {IRS_MAILING_ADDRESS}. Foreign-owned DEs cannot "
                "e-file this filing.")
        next_steps.append(
            "Keep copies and proof of transmission for your records.")

        return {
            "success": True,
            "validation": validation,
            "paths": {k: v for k, v in paths.items() if v},
            "next_steps": next_steps,
            "disclaimer": DISCLAIMER,
        }

    def _is_initial_return(self, entity: Dict[str, Any],
                           tax_year: int) -> bool:
        """First filing year if the entity was formed during the tax year."""
        formation = entity.get("formation_date")
        if not formation:
            return False
        try:
            return int(formation[:4]) == tax_year
        except (ValueError, TypeError):
            return False

    # ------------------------------------------------------------------
    # Electronic signature / declaration
    # ------------------------------------------------------------------

    def _package_paths(self, entity_id: int, tax_year: int) -> Dict[str, str]:
        """Filing package PDF paths currently on record (existing files)."""
        c = self.conn.cursor()
        c.execute('''
            SELECT form_1120_path, form_5472_path, part_v_statement_path,
                   reasonable_cause_path
            FROM form_filings WHERE entity_id = ? AND tax_year = ?
        ''', (entity_id, tax_year))
        row = c.fetchone()
        if row is None:
            raise ValueError(
                f"No filing found for entity {entity_id}, year {tax_year}. "
                "Generate the filing first.")
        keys = ("form_1120_path", "form_5472_path", "part_v_statement_path",
                "reasonable_cause_path")
        return {k: p for k, p in zip(keys, row) if p}

    @staticmethod
    def _sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def sign_filing(self, entity_id: int, tax_year: int, signer_name: str,
                    signer_title: str, signed_date: Optional[str] = None,
                    signature_image: Optional[str] = None,
                    user_id: str = "system") -> Dict[str, Any]:
        """Apply an e-signature to the pro-forma 1120 and record the jurat.

        The caller MUST have displayed PERJURY_DECLARATION to the signer and
        obtained their explicit acceptance before calling this. Writes the
        signed 1120 alongside the original, points the filing at it, and
        stores SHA-256 hashes of every package PDF so a later transmission
        can prove it sent exactly what was declared.
        """
        import os
        from pyledger import irs_pdf

        paths = self._package_paths(entity_id, tax_year)
        if "form_1120_path" not in paths:
            raise ValueError(
                "This filing has no pro-forma 1120 to sign. (25%-foreign-"
                "owned corporations sign their own Form 1120 return.)")

        source_1120 = paths["form_1120_path"]
        directory = os.path.dirname(source_1120)
        signed_path = os.path.join(
            directory, f"f1120_proforma_{tax_year}_signed.pdf")
        if source_1120 == signed_path:
            # Re-signing: start from the unsigned original if it survives,
            # to avoid stacking signature overlays.
            original = os.path.join(directory,
                                    f"f1120_proforma_{tax_year}.pdf")
            if os.path.isfile(original):
                source_1120 = original

        missing = [p for p in {**paths, "form_1120_path": source_1120}.values()
                   if not os.path.isfile(p)]
        if missing:
            raise ValueError("Filing PDFs missing on disk (regenerate the "
                             "filing): " + ", ".join(missing))

        signed_date = signed_date or date.today().isoformat()
        irs_pdf.sign_form_1120(source_1120, signed_path, signer_name,
                               signer_title, signed_date,
                               signature_image=signature_image)

        c = self.conn.cursor()
        c.execute('''
            UPDATE form_filings SET form_1120_path = ?
            WHERE entity_id = ? AND tax_year = ?
        ''', (signed_path, entity_id, tax_year))

        paths["form_1120_path"] = signed_path
        hashes = {p: self._sha256(p) for p in paths.values()}
        accepted_at = datetime.now().isoformat()
        signature_kind = "image" if signature_image else "typed"
        c.execute('''
            INSERT INTO filing_declarations
            (entity_id, tax_year, declaration_text, signer_name,
             signer_title, signature_kind, signed_date, accepted_at,
             files_sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, tax_year) DO UPDATE SET
                declaration_text = excluded.declaration_text,
                signer_name = excluded.signer_name,
                signer_title = excluded.signer_title,
                signature_kind = excluded.signature_kind,
                signed_date = excluded.signed_date,
                accepted_at = excluded.accepted_at,
                files_sha256 = excluded.files_sha256
        ''', (entity_id, tax_year, PERJURY_DECLARATION, signer_name,
              signer_title, signature_kind, signed_date, accepted_at,
              json.dumps(hashes)))
        self.conn.commit()

        self.log_audit_trail(
            user_id, "DECLARATION_ACCEPTED", "filing_declarations",
            f"{entity_id}/{tax_year}", None,
            {"signer_name": signer_name, "signer_title": signer_title,
             "accepted_at": accepted_at,
             "declaration_sha256": hashlib.sha256(
                 PERJURY_DECLARATION.encode()).hexdigest()},
            TaxPrinciple.FILING,
            "Signer accepted the penalty-of-perjury declaration")
        self.log_audit_trail(
            user_id, "FORM_SIGNED", "form_filings",
            f"{entity_id}/{tax_year}", None,
            {"signed_1120_path": signed_path,
             "signature_kind": signature_kind, "files_sha256": hashes},
            TaxPrinciple.FILING,
            "Applied electronic signature to pro-forma Form 1120")

        return {
            "signed_1120_path": signed_path,
            "signer_name": signer_name,
            "signer_title": signer_title,
            "signed_date": signed_date,
            "signature_kind": signature_kind,
            "accepted_at": accepted_at,
            "files_sha256": hashes,
            "declaration_text": PERJURY_DECLARATION,
        }

    def get_declaration(self, entity_id: int,
                        tax_year: int) -> Optional[Dict[str, Any]]:
        """The recorded declaration for an entity + tax year, or None."""
        c = self.conn.cursor()
        c.execute('''
            SELECT * FROM filing_declarations
            WHERE entity_id = ? AND tax_year = ?
        ''', (entity_id, tax_year))
        row = c.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in c.description]
        record = dict(zip(cols, row))
        record["files_sha256"] = json.loads(record["files_sha256"])
        return record

    def mark_filed(self, entity_id: int, tax_year: int, filed_date: str,
                   method: str, user_id: str = "system") -> None:
        """Mark a generated filing as filed (method: 'mail' or 'fax')."""
        if method not in ("mail", "fax"):
            raise ValueError("Filing method must be 'mail' or 'fax'")
        c = self.conn.cursor()
        c.execute('''
            UPDATE form_filings
            SET status = ?, filed_date = ?, filing_method = ?
            WHERE entity_id = ? AND tax_year = ?
        ''', (FilingStatus.FILED.value, filed_date, method,
              entity_id, tax_year))
        if c.rowcount == 0:
            raise ValueError(
                f"No filing found for entity {entity_id}, year {tax_year}. "
                "Generate the filing first.")
        self.conn.commit()
        self.log_audit_trail(
            user_id, "FILE", "form_filings", f"{entity_id}/{tax_year}", None,
            {"filed_date": filed_date, "method": method},
            TaxPrinciple.FILING, "Marked filing as filed")
