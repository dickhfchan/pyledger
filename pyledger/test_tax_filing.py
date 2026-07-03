"""
Tests for the IRS Form 5472 / pro-forma 1120 tax filing modules.

PDF tests run against synthetic AcroForm templates built with reportlab, so
no network access is needed. Integration tests against the real IRS
templates are gated behind PYLEDGER_IRS_NETWORK_TESTS=1.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

import pytest

import pyledger.db as db
from pyledger.tax_filing import (
    Form5472Filing,
    ReportableTransactionType,
    PART_IV_LINE_FOR_TYPE,
    BASE_PENALTY_PER_FORM,
)


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    db.init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def filing(conn):
    return Form5472Filing(conn)


@pytest.fixture
def de_entity(filing):
    """A foreign-owned DE with a German owner and 2025 transactions."""
    eid = filing.add_entity(
        "Acme Consulting LLC", "foreign_owned_de", "123 Main St", "Dover",
        state="DE", postal_code="19901", ein="12-3456789",
        formation_date="2025-03-01",
        principal_business_activity="Management consulting",
        principal_business_activity_code="541610")
    filing.add_foreign_owner(
        eid, "Hans Mueller", "Germany", "Hauptstrasse 1", "Berlin",
        postal_code="10115", foreign_tin="DE123456789")
    filing.add_reportable_transaction(
        eid, 2025, "capital_contribution", 5000.0, txn_date="2025-03-05")
    filing.add_reportable_transaction(
        eid, 2025, "service_fees_paid", 1200.0, txn_date="2025-06-10")
    return eid


# ---------------------------------------------------------------------------
# Rules: deadlines and penalties
# ---------------------------------------------------------------------------

class TestDeadlines:
    def test_calendar_year_deadline(self, filing):
        assert filing.get_deadline(2025) == date(2026, 4, 15)

    def test_extended_deadline(self, filing):
        assert filing.get_deadline(2025, extended=True) == date(2026, 10, 15)

    def test_fiscal_year_deadline(self, filing):
        # Fiscal year ending June 30, 2025 -> due Oct 15, 2025
        assert filing.get_deadline(2025, tax_year_end="06-30") == \
            date(2025, 10, 15)


class TestPenalties:
    def test_on_time_no_penalty(self, filing):
        result = filing.estimate_penalty(2025, as_of=date(2026, 3, 1))
        assert result["is_late"] is False
        assert result["total"] == 0.0

    def test_late_base_penalty(self, filing):
        result = filing.estimate_penalty(2025, as_of=date(2026, 6, 1))
        assert result["is_late"] is True
        assert result["total"] == BASE_PENALTY_PER_FORM

    def test_continuation_penalty_after_notice(self, filing):
        # Notice 2026-05-01; 90-day grace ends 2026-07-30; as_of 2026-09-05
        # is 37 days past grace -> 2 periods of 30 days (ceil).
        result = filing.estimate_penalty(
            2025, as_of=date(2026, 9, 5), irs_notice_date=date(2026, 5, 1))
        assert result["continuation_periods"] == 2
        assert result["total"] == BASE_PENALTY_PER_FORM + 2 * 25000.0

    def test_multiple_forms(self, filing):
        result = filing.estimate_penalty(
            2025, as_of=date(2026, 6, 1), num_forms=3)
        assert result["base_penalty"] == 3 * BASE_PENALTY_PER_FORM


# ---------------------------------------------------------------------------
# Rules: filing requirement matrix
# ---------------------------------------------------------------------------

class TestFilingRequirement:
    def test_de_with_transactions_required(self, filing, de_entity):
        result = filing.check_filing_requirement(de_entity, 2025)
        assert result["required"] is True
        assert result["can_efile"] is False
        assert result["forms_needed"] == ["5472", "1120-proforma"]
        assert result["deadline"] == "2026-04-15"
        assert "855-887-7737" in result["submission"]["fax"]
        assert "Ogden" in result["submission"]["mail"]

    def test_de_without_transactions_not_required(self, filing):
        eid = filing.add_entity(
            "Idle LLC", "foreign_owned_de", "1 Elm St", "Austin")
        filing.add_foreign_owner(eid, "Marie Curie", "France",
                                 "Rue de Paris 5", "Paris")
        result = filing.check_filing_requirement(eid, 2025)
        assert result["required"] is False
        assert result["has_reportable_transactions"] is False

    def test_de_without_owner_not_required(self, filing):
        eid = filing.add_entity(
            "Domestic LLC", "foreign_owned_de", "1 Oak St", "Miami")
        result = filing.check_filing_requirement(eid, 2025)
        assert result["required"] is False

    def test_corporation_can_efile(self, filing):
        eid = filing.add_entity(
            "BigCorp Inc", "foreign_owned_corporation", "1 Wall St",
            "New York", ein="98-7654321")
        filing.add_foreign_owner(eid, "Foreign Holdco", "Japan",
                                 "1 Tokyo St", "Tokyo",
                                 owner_kind="corporation", ownership_pct=40.0)
        filing.add_reportable_transaction(eid, 2025, "interest_paid", 900.0)
        result = filing.check_filing_requirement(eid, 2025)
        assert result["required"] is True
        assert result["can_efile"] is True
        assert result["forms_needed"] == ["5472"]

    def test_corporation_below_25pct_not_required(self, filing):
        eid = filing.add_entity(
            "MinorCorp Inc", "foreign_owned_corporation", "2 Wall St",
            "New York")
        filing.add_foreign_owner(eid, "Small Holder", "UK", "1 London Rd",
                                 "London", ownership_pct=10.0)
        filing.add_reportable_transaction(eid, 2025, "interest_paid", 900.0)
        result = filing.check_filing_requirement(eid, 2025)
        assert result["required"] is False

    def test_unknown_entity_raises(self, filing):
        with pytest.raises(ValueError):
            filing.check_filing_requirement(999, 2025)


# ---------------------------------------------------------------------------
# Classification and ledger suggestions
# ---------------------------------------------------------------------------

class TestClassification:
    @pytest.mark.parametrize("text,expected,confidence", [
        ("Owner capital contribution wire", "capital_contribution", "high"),
        ("Q4 distribution to member", "distribution", "high"),
        ("Loan from owner for equipment", "loan_from_owner", "high"),
        ("Delaware formation filing fee", "formation_dissolution_costs",
         "high"),
        ("Rent paid by owner on behalf of LLC", "expenses_paid_by_owner",
         "high"),
        ("Office supplies from Staples", None, "low"),
    ])
    def test_keyword_classification(self, filing, text, expected, confidence):
        result = filing.classify_transaction(text)
        assert result["suggested_type"] == expected
        assert result["confidence"] == confidence

    def test_part_iv_line_map_covers_all_types(self):
        assert set(PART_IV_LINE_FOR_TYPE) == set(ReportableTransactionType)


class TestLedgerSuggestions:
    @pytest.fixture
    def ledger_entity(self, conn, filing):
        from pyledger.accounts import AccountType
        db.add_account(conn, "1000", "Cash", AccountType.ASSET)
        db.add_account(conn, "3000", "Owner Capital", AccountType.EQUITY)
        db.add_account(conn, "5000", "Office Expense", AccountType.EXPENSE)
        year = str(date.today().year)
        db.add_journal_entry(conn, "Owner capital contribution",
                             [("1000", 5000.0, True), ("3000", 5000.0, False)])
        db.add_journal_entry(conn, "Office supplies purchase",
                             [("5000", 100.0, True), ("1000", 100.0, False)])
        eid = filing.add_entity(
            "Ledger LLC", "foreign_owned_de", "1 Pine St", "Dover")
        filing.add_foreign_owner(eid, "Jean Blanc", "France", "Rue 1",
                                 "Lyon")
        return eid

    def test_keyword_suggestion_found(self, filing, ledger_entity):
        year = date.today().year
        suggestions = filing.suggest_reportable_transactions(
            ledger_entity, year)
        types = {s["suggested_type"] for s in suggestions}
        assert "capital_contribution" in types
        # Office supplies entry has no owner keyword -> not suggested.
        descs = {s["description"] for s in suggestions}
        assert "Office supplies purchase" not in descs

    def test_mapped_account_high_confidence(self, filing, ledger_entity):
        year = date.today().year
        filing.map_account(ledger_entity, "3000", "capital_contribution")
        suggestions = filing.suggest_reportable_transactions(
            ledger_entity, year)
        mapped = [s for s in suggestions if s["account_code"] == "3000"]
        assert mapped and mapped[0]["confidence"] == "high"

    def test_confirm_then_dedup(self, filing, ledger_entity):
        year = date.today().year
        suggestions = filing.suggest_reportable_transactions(
            ledger_entity, year)
        first = suggestions[0]
        filing.confirm_suggested_transaction(
            ledger_entity, year, first["journal_entry_id"],
            first["suggested_type"], first["amount"])
        after = filing.suggest_reportable_transactions(ledger_entity, year)
        assert all(s["journal_entry_id"] != first["journal_entry_id"]
                   for s in after)
        recorded = filing.list_reportable_transactions(ledger_entity, year)
        assert recorded[0]["source"] == "ledger_confirmed"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_valid_entity(self, filing, de_entity):
        result = filing.validate_filing_data(de_entity, 2025)
        assert result["valid"] is True

    def test_missing_ein(self, filing):
        eid = filing.add_entity(
            "NoEIN LLC", "foreign_owned_de", "1 Ash St", "Reno")
        filing.add_foreign_owner(eid, "Ana Silva", "Brazil", "Rua 2",
                                 "Sao Paulo", foreign_tin="BR123")
        result = filing.validate_filing_data(eid, 2025)
        assert result["valid"] is False
        assert any("EIN" in e for e in result["errors"])

    def test_bad_ein_format(self, filing):
        eid = filing.add_entity(
            "BadEIN LLC", "foreign_owned_de", "1 Ash St", "Reno",
            ein="1234")
        filing.add_foreign_owner(eid, "Ana Silva", "Brazil", "Rua 2",
                                 "Sao Paulo", foreign_tin="BR123")
        result = filing.validate_filing_data(eid, 2025)
        assert any("format" in e for e in result["errors"])

    def test_no_owner_error(self, filing):
        eid = filing.add_entity(
            "Orphan LLC", "foreign_owned_de", "1 Ash St", "Reno",
            ein="12-3456789")
        result = filing.validate_filing_data(eid, 2025)
        assert any("foreign owner" in e for e in result["errors"])

    def test_no_tin_warns_foreignus(self, filing):
        eid = filing.add_entity(
            "NoTIN LLC", "foreign_owned_de", "1 Ash St", "Reno",
            ein="12-3456789")
        filing.add_foreign_owner(eid, "Li Wei", "China", "Street 9",
                                 "Shanghai")
        result = filing.validate_filing_data(eid, 2025)
        assert result["valid"] is True
        assert any("FOREIGNUS" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# Audit trail and filing lifecycle
# ---------------------------------------------------------------------------

class TestAuditAndLifecycle:
    def test_crud_writes_audit_trail(self, conn, filing, de_entity):
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tax_audit_trail")
        # entity + owner + 2 transactions = 4 audit rows
        assert c.fetchone()[0] == 4

    def test_mark_filed_requires_generated_filing(self, filing, de_entity):
        with pytest.raises(ValueError):
            filing.mark_filed(de_entity, 2025, "2026-04-01", "fax")

    def test_mark_filed_bad_method(self, filing, de_entity):
        with pytest.raises(ValueError):
            filing.mark_filed(de_entity, 2025, "2026-04-01", "carrier-pigeon")

    def test_amount_must_be_positive(self, filing, de_entity):
        with pytest.raises(ValueError):
            filing.add_reportable_transaction(
                de_entity, 2025, "distribution", -5.0)

    def test_invalid_txn_type_rejected(self, filing, de_entity):
        with pytest.raises(ValueError):
            filing.add_reportable_transaction(
                de_entity, 2025, "not_a_type", 10.0)


# ---------------------------------------------------------------------------
# PDF generation against synthetic templates (no network)
# ---------------------------------------------------------------------------

def _build_synthetic_template(path, text_fields, checkbox_fields):
    """Build a minimal AcroForm PDF exposing the given qualified names."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import LETTER

    c = canvas.Canvas(str(path), pagesize=LETTER)
    pages = 3
    per_page = -(-len(text_fields) // pages) if text_fields else 1
    i = 0
    for p in range(pages):
        y = 740
        for name in text_fields[p * per_page:(p + 1) * per_page]:
            c.acroForm.textfield(name=name, x=40, y=y, width=300, height=12,
                                 borderWidth=0)
            y -= 16
        if p == 0:
            for name in checkbox_fields:
                c.acroForm.checkbox(name=name, x=380, y=y, size=10)
                y -= 16
        c.showPage()
    c.save()


@pytest.fixture
def synthetic_maps(tmp_path, monkeypatch):
    """Synthetic templates + patched checkbox on-values ('/Yes')."""
    from pyledger import irs_pdf, irs_form_maps

    # --- f5472
    fmap = irs_form_maps.FORM_5472_FIELDS["2023-12"]
    part_iv = irs_form_maps.FORM_5472_PART_IV_FIELDS["2023-12"]
    cmap = irs_form_maps.FORM_5472_CHECKBOXES["2023-12"]
    patched_cmap = {"2023-12": {k: (v[0], "/Yes") for k, v in cmap.items()}}
    monkeypatch.setattr(irs_pdf, "FORM_5472_CHECKBOXES", patched_cmap)
    _build_synthetic_template(
        tmp_path / "f5472.pdf",
        list(fmap.values()) + list(part_iv.values()),
        [v[0] for v in cmap.values()])

    # --- f1120
    fmap_1120 = irs_form_maps.FORM_1120_FIELDS["2025"]
    cmap_1120 = irs_form_maps.FORM_1120_CHECKBOXES["2025"]
    patched_1120 = {"2025": {k: (v[0], "/Yes")
                             for k, v in cmap_1120.items()}}
    monkeypatch.setattr(irs_pdf, "FORM_1120_CHECKBOXES", patched_1120)
    _build_synthetic_template(
        tmp_path / "f1120.pdf", list(fmap_1120.values()),
        [v[0] for v in cmap_1120.values()])

    # --- f7004
    fmap_7004 = irs_form_maps.FORM_7004_FIELDS["2018-12"]
    _build_synthetic_template(tmp_path / "f7004.pdf",
                              list(fmap_7004.values()), [])

    return tmp_path


class TestPdfGeneration:
    def test_fill_form_5472_synthetic(self, tmp_path, synthetic_maps,
                                      filing, de_entity):
        from pypdf import PdfReader
        from pyledger import irs_pdf

        entity = filing.get_entity(de_entity)
        owner = filing.list_foreign_owners(de_entity)[0]
        totals = filing.transaction_totals_by_type(de_entity, 2025)
        data = irs_pdf.Form5472Data(entity=entity, owner=owner,
                                    tax_year=2025, totals_by_type=totals,
                                    is_de=True, is_initial_year=True)
        out = tmp_path / "out_5472.pdf"
        irs_pdf.fill_form_5472(synthetic_maps / "f5472.pdf", data, out)

        fields = PdfReader(str(out)).get_fields()
        from pyledger.irs_form_maps import (FORM_5472_FIELDS,
                                            FORM_5472_PART_IV_FIELDS,
                                            FORM_5472_CHECKBOXES)
        fmap = FORM_5472_FIELDS["2023-12"]
        part_iv = FORM_5472_PART_IV_FIELDS["2023-12"]
        assert fields[fmap["reporting_corp_name"]].get("/V") == \
            "Acme Consulting LLC"
        assert fields[fmap["reporting_corp_ein"]].get("/V") == "12-3456789"
        # 5000 contribution (Part V) + 1200 service fees paid (line 29)
        assert fields[fmap["total_gross_payments_this_form"]].get("/V") == \
            "6,200"
        assert fields[part_iv["29"]].get("/V") == "1,200"
        assert fields[part_iv["36"]].get("/V") == "1,200"
        # DE + initial year + part V checkboxes set (synthetic on-value /Yes)
        cmap = FORM_5472_CHECKBOXES["2023-12"]
        assert fields[cmap["foreign_owned_de"][0]].get("/V") == "/Yes"
        assert fields[cmap["initial_year"][0]].get("/V") == "/Yes"
        assert fields[cmap["part_v_statement_attached"][0]].get("/V") == \
            "/Yes"

    def test_fill_1120_proforma_banner(self, tmp_path, synthetic_maps,
                                       filing, de_entity):
        from pypdf import PdfReader
        from pyledger import irs_pdf
        from pyledger.irs_form_maps import FORM_1120_FIELDS

        entity = filing.get_entity(de_entity)
        data = irs_pdf.Form1120ProFormaData(entity=entity, tax_year=2025,
                                            is_initial_return=True)
        out = tmp_path / "out_1120.pdf"
        irs_pdf.fill_form_1120_proforma(synthetic_maps / "f1120.pdf",
                                        data, out)
        reader = PdfReader(str(out))
        fields = reader.get_fields()
        fmap = FORM_1120_FIELDS["2025"]
        assert fields[fmap["ein"]].get("/V") == "12-3456789"
        assert "Foreign-owned U.S. DE" in reader.pages[0].extract_text()

    def test_fill_7004(self, tmp_path, synthetic_maps, filing, de_entity):
        from pypdf import PdfReader
        from pyledger import irs_pdf
        from pyledger.irs_form_maps import FORM_7004_FIELDS

        entity = filing.get_entity(de_entity)
        data = irs_pdf.Form7004Data(entity=entity, tax_year=2025)
        out = tmp_path / "out_7004.pdf"
        irs_pdf.fill_form_7004(synthetic_maps / "f7004.pdf", data, out)
        fields = PdfReader(str(out)).get_fields()
        fmap = FORM_7004_FIELDS["2018-12"]
        assert fields[fmap["form_code_digit1"]].get("/V") == "1"
        assert fields[fmap["form_code_digit2"]].get("/V") == "2"
        assert fields[fmap["tentative_tax"]].get("/V") == "0"

    def test_field_mismatch_raises(self, tmp_path, filing, de_entity):
        from pyledger import irs_pdf

        # Template with a single unrelated field -> mismatch error.
        _build_synthetic_template(tmp_path / "bogus.pdf", ["some_field"], [])
        entity = filing.get_entity(de_entity)
        owner = filing.list_foreign_owners(de_entity)[0]
        data = irs_pdf.Form5472Data(entity=entity, owner=owner,
                                    tax_year=2025, totals_by_type={},
                                    is_de=True)
        with pytest.raises(irs_pdf.TemplateFieldMismatchError):
            irs_pdf.fill_form_5472(tmp_path / "bogus.pdf", data,
                                   tmp_path / "out.pdf")

    def test_statements(self, tmp_path, filing, de_entity):
        from pyledger import irs_pdf

        entity = filing.get_entity(de_entity)
        owner = filing.list_foreign_owners(de_entity)[0]
        txns = filing.list_reportable_transactions(de_entity, 2025)

        rc = tmp_path / "rc.pdf"
        irs_pdf.render_reasonable_cause_statement(
            entity, 2025, "Owner was unaware of the requirement.", rc)
        assert rc.read_bytes()[:5] == b"%PDF-"

        pv = tmp_path / "pv.pdf"
        irs_pdf.render_part_v_statement(entity, owner, txns, pv)
        assert pv.read_bytes()[:5] == b"%PDF-"

    def test_generate_filing_full_pipeline(self, tmp_path, synthetic_maps,
                                           filing, de_entity):
        result = filing.generate_filing(
            de_entity, 2025, str(tmp_path / "filings"),
            include_extension=True,
            reasonable_cause_text="Testing cause.",
            template_dir=str(synthetic_maps))
        assert result["success"] is True
        assert set(result["paths"]) == {
            "form_5472_path", "form_1120_path", "form_7004_path",
            "reasonable_cause_path", "part_v_statement_path"}
        for path in result["paths"].values():
            assert os.path.getsize(path) > 0
        # Filing row persisted; mark as filed.
        filing.mark_filed(de_entity, 2025, "2026-04-01", "fax")

    def test_generate_filing_invalid_data_fails(self, filing, tmp_path):
        eid = filing.add_entity(
            "Broken LLC", "foreign_owned_de", "1 Elm St", "Austin")
        result = filing.generate_filing(eid, 2025, str(tmp_path))
        assert result["success"] is False
        assert result["validation"]["errors"]


# ---------------------------------------------------------------------------
# Real-template integration (network / cached templates required)
# ---------------------------------------------------------------------------

needs_network = pytest.mark.skipif(
    not os.environ.get("PYLEDGER_IRS_NETWORK_TESTS"),
    reason="Set PYLEDGER_IRS_NETWORK_TESTS=1 to run real-template tests")


@needs_network
class TestRealTemplates:
    def test_real_template_field_maps_valid(self, tmp_path):
        from pypdf import PdfReader
        from pyledger import irs_pdf
        from pyledger.irs_form_maps import get_field_map

        manager = irs_pdf.IRSTemplateManager()
        for form in ("f5472", "f1120", "f7004"):
            template = manager.get_template(form)
            reader = PdfReader(str(template))
            missing = irs_pdf.verify_field_map(reader, get_field_map(form))
            assert not missing, f"{form} missing fields: {missing}"

    def test_real_template_generate_filing(self, filing, de_entity,
                                           tmp_path):
        result = filing.generate_filing(
            de_entity, 2025, str(tmp_path), include_extension=True)
        assert result["success"] is True
