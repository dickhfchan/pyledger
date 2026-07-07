"""
Tests for the fax transmission service (fax_service.py).

No network access: FilingFaxService is exercised with an in-memory fake
provider, and NotifyreProvider with a stubbed HTTP session. Package PDFs
are tiny real PDFs built with pypdf so the merge step runs for real.
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

import pytest

import pyledger.db as db
from pyledger.tax_filing import Form5472Filing, IRS_FAX_NUMBER
from pyledger.fax_service import (
    FaxError,
    FaxProvider,
    FaxStatus,
    FilingFaxService,
    NotifyreProvider,
    load_dotenv_value,
    merge_pdfs,
    to_e164,
)


def make_pdf(path, pages=1):
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    with open(path, "wb") as fh:
        writer.write(fh)
    return str(path)


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
def generated_filing(filing, tmp_path):
    """An entity with a generated filing whose PDFs exist on disk."""
    eid = filing.add_entity(
        "Acme Consulting LLC", "foreign_owned_de", "123 Main St", "Dover",
        state="DE", postal_code="19901", ein="12-3456789")
    filing.add_foreign_owner(
        eid, "Hans Mueller", "Germany", "Hauptstrasse 1", "Berlin")
    filing.add_reportable_transaction(eid, 2025, "capital_contribution", 5000.0)

    paths = {
        "form_5472_path": make_pdf(tmp_path / "f5472_2025.pdf", pages=2),
        "form_1120_path": make_pdf(tmp_path / "f1120_proforma_2025.pdf"),
        "part_v_statement_path": make_pdf(tmp_path / "part_v_2025.pdf"),
    }
    c = filing.conn.cursor()
    c.execute('''
        INSERT INTO form_filings
        (entity_id, tax_year, status, form_5472_path, form_1120_path,
         part_v_statement_path, generated_at)
        VALUES (?, 2025, 'generated', ?, ?, ?, '2026-04-01T00:00:00')
    ''', (eid, paths["form_5472_path"], paths["form_1120_path"],
          paths["part_v_statement_path"]))
    filing.conn.commit()
    return eid, paths


class FakeProvider(FaxProvider):
    """In-memory provider with a scriptable status sequence."""

    name = "fake"

    def __init__(self, statuses: Optional[List[str]] = None):
        self.sent: List[Dict[str, Any]] = []
        self.statuses = statuses or ["completed"]
        self._polls = 0

    def send(self, to_number, file_path, reference=None):
        self.sent.append({"to": to_number, "file_path": file_path,
                          "reference": reference})
        return f"fax-{len(self.sent)}"

    def get_status(self, provider_fax_id):
        status = self.statuses[min(self._polls, len(self.statuses) - 1)]
        self._polls += 1
        done = status == "completed"
        return FaxStatus(
            provider_fax_id=provider_fax_id, status=status,
            num_pages=4 if done else None,
            completed_at="2026-04-02T10:00:00+00:00" if done else None,
            failed_message="line busy" if status == "failure" else None,
            raw={"id": provider_fax_id, "status": status})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestToE164:
    def test_irs_number(self):
        assert to_e164(IRS_FAX_NUMBER) == "+18558877737"

    def test_already_e164(self):
        assert to_e164("+49 30 1234567") == "+49301234567"

    def test_eleven_digits(self):
        assert to_e164("1-855-887-7737") == "+18558877737"

    def test_no_digits(self):
        with pytest.raises(FaxError):
            to_e164("no digits")


def test_merge_pdfs(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", pages=2)
    b = make_pdf(tmp_path / "b.pdf", pages=3)
    out = merge_pdfs([a, b], str(tmp_path / "merged.pdf"))
    from pypdf import PdfReader
    assert len(PdfReader(out).pages) == 5


def test_load_dotenv_value(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nFAX_NUMBER=123\nNOTIFY_API_KEY='sk_test'\n")
    assert load_dotenv_value("NOTIFY_API_KEY", str(env)) == "sk_test"
    assert load_dotenv_value("MISSING", str(env)) is None
    assert load_dotenv_value("NOTIFY_API_KEY", str(tmp_path / "no")) is None


# ---------------------------------------------------------------------------
# FilingFaxService
# ---------------------------------------------------------------------------

class TestFilingFaxService:
    def test_package_order_and_no_7004(self, filing, generated_filing):
        eid, paths = generated_filing
        service = FilingFaxService(filing, FakeProvider())
        files = service.package_files(eid, 2025)
        # 1120 on top, then 5472, then Part V; no 7004 in the package.
        assert files == [paths["form_1120_path"], paths["form_5472_path"],
                         paths["part_v_statement_path"]]

    def test_send_requires_generated_filing(self, filing):
        eid = filing.add_entity("No Filing LLC", "foreign_owned_de",
                                "1 St", "Dover")
        service = FilingFaxService(filing, FakeProvider())
        with pytest.raises(FaxError, match="No generated filing"):
            service.send_filing(eid, 2025, allow_unsigned=True)

    def test_send_fails_on_missing_pdfs(self, filing, generated_filing):
        eid, paths = generated_filing
        import os
        os.remove(paths["form_5472_path"])
        service = FilingFaxService(filing, FakeProvider())
        with pytest.raises(FaxError, match="missing on disk"):
            service.send_filing(eid, 2025, allow_unsigned=True)

    def test_send_merges_package_and_defaults_to_irs(self, filing,
                                                     generated_filing):
        eid, _ = generated_filing
        provider = FakeProvider()
        service = FilingFaxService(filing, provider)
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        assert record["status"] == "queued"
        assert record["provider_fax_id"] == "fax-1"
        assert record["to_number"] == "+18558877737"
        assert provider.sent[0]["reference"] == f"5472-{eid}-2025"
        # A single merged PDF with all package pages went to the provider.
        assert provider.sent[0]["file_path"] == record["package_path"]
        from pypdf import PdfReader
        assert len(PdfReader(record["package_path"]).pages) == 4

    def test_success_marks_filed_with_confirmation(self, filing,
                                                   generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider(["completed"]))
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        record = service.refresh_status(record["id"])
        assert record["status"] == "completed"
        assert record["num_pages"] == 4
        assert json.loads(record["confirmation"])["status"] == "completed"

        c = filing.conn.cursor()
        c.execute('''SELECT status, filed_date, filing_method
                     FROM form_filings WHERE entity_id = ? AND tax_year = 2025''',
                  (eid,))
        status, filed_date, method = c.fetchone()
        assert status == "filed"
        assert filed_date == "2026-04-02"
        assert method == "fax"

    def test_failure_does_not_mark_filed(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider(["failure"]))
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        record = service.refresh_status(record["id"])
        assert record["status"] == "failure"
        assert record["failed_message"] == "line busy"
        c = filing.conn.cursor()
        c.execute("SELECT status FROM form_filings WHERE entity_id = ?", (eid,))
        assert c.fetchone()[0] == "generated"

    def test_wait_polls_until_terminal(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing,
                                   FakeProvider(["in_progress", "completed"]))
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        record = service.wait_for_completion(record["id"], timeout=5,
                                             poll_interval=0)
        assert record["status"] == "completed"

    def test_repeat_success_refresh_does_not_refile(self, filing,
                                                    generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider(["completed"]))
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        service.refresh_status(record["id"])
        service.refresh_status(record["id"])  # must not raise or double-log
        c = filing.conn.cursor()
        c.execute('''SELECT COUNT(*) FROM tax_audit_trail
                     WHERE action = 'FAX_CONFIRMED' ''')
        assert c.fetchone()[0] == 1

    def test_audit_trail_written(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider())
        service.send_filing(eid, 2025, allow_unsigned=True)
        c = filing.conn.cursor()
        c.execute("SELECT COUNT(*) FROM tax_audit_trail WHERE action = 'FAX_QUEUED'")
        assert c.fetchone()[0] == 1

    def test_list_transmissions(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider())
        service.send_filing(eid, 2025, allow_unsigned=True)
        records = service.list_transmissions(eid, 2025)
        assert len(records) == 1
        assert len(records[0]["files"]) == 3


# ---------------------------------------------------------------------------
# NotifyreProvider (stubbed HTTP session)
# ---------------------------------------------------------------------------

def envelope(payload, success=True, status_code=200, message="OK"):
    return {"success": success, "statusCode": status_code,
            "message": message, "payload": payload}


class StubResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class StubSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: List[Dict[str, Any]] = []

    def post(self, url, **kwargs):
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self.responses.pop(0)


class TestNotifyreProvider:
    def _provider(self, responses):
        return NotifyreProvider(api_key="sk_test",
                                conversion_poll_interval=0,
                                session=StubSession(responses))

    def test_requires_credentials(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NOTIFY_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # no .env here
        with pytest.raises(FaxError, match="API key missing"):
            NotifyreProvider(session=StubSession([]))

    def test_api_key_from_dotenv(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NOTIFY_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("NOTIFY_API_KEY=sk_from_dotenv\n")
        provider = NotifyreProvider(session=StubSession([]))
        assert provider.api_key == "sk_from_dotenv"

    def test_send_full_flow(self, tmp_path):
        pdf = make_pdf(tmp_path / "package.pdf")
        provider = self._provider([
            # 1. upload for conversion
            StubResponse(200, envelope({"fileID": "file-1",
                                        "fileName": "package-conv"})),
            # 2. poll conversion: converting, then successful
            StubResponse(200, envelope({"id": "doc-9", "status": "converting",
                                        "fileName": "package-conv"})),
            StubResponse(200, envelope({"id": "doc-9", "status": "successful",
                                        "fileName": "package-conv",
                                        "pages": 4})),
            # 3. submit fax
            StubResponse(200, envelope({"faxID": "fax-123",
                                        "friendlyID": "AB12"})),
        ])
        fax_id = provider.send(IRS_FAX_NUMBER, pdf, reference="5472-1-2025")
        assert fax_id == "fax-123"

        reqs = provider._session.requests
        assert reqs[0]["url"].endswith("/fax/send/conversion")
        assert reqs[0]["headers"]["x-api-token"] == "sk_test"
        assert reqs[0]["json"]["contentType"] == "application/pdf"
        assert reqs[0]["json"]["base64Str"]
        assert reqs[1]["url"].endswith("/fax/send/conversion/package-conv")
        assert reqs[3]["url"].endswith("/fax/send")
        faxes = reqs[3]["json"]["faxes"]
        assert faxes["files"] == ["doc-9"]
        assert faxes["recipients"] == [{"type": "fax_number",
                                        "value": "+18558877737"}]
        assert faxes["clientReference"] == "5472-1-2025"
        assert faxes["isHighQuality"] is True

    def test_send_conversion_failure(self, tmp_path):
        pdf = make_pdf(tmp_path / "f.pdf")
        provider = self._provider([
            StubResponse(200, envelope({"fileID": "f1", "fileName": "conv"})),
            StubResponse(200, envelope({"id": "d", "status": "failed",
                                        "fileName": "conv"})),
        ])
        with pytest.raises(FaxError, match="conversion failed"):
            provider.send(IRS_FAX_NUMBER, pdf)

    def test_send_missing_file(self):
        provider = self._provider([])
        with pytest.raises(FaxError, match="not found"):
            provider.send(IRS_FAX_NUMBER, "/nonexistent.pdf")

    def test_send_api_error(self, tmp_path):
        pdf = make_pdf(tmp_path / "f.pdf")
        provider = self._provider([
            StubResponse(400, envelope(None, success=False,
                                       message="Invalid recipient"))])
        with pytest.raises(FaxError, match="Invalid recipient"):
            provider.send("000", pdf)

    def test_get_status_successful(self):
        provider = self._provider([
            StubResponse(200, envelope({"faxes": [
                {"id": "other", "status": "queued"},
                {"id": "fax-123", "status": "successful", "pages": 4,
                 "lastModifiedDateUtc": 1775124000,
                 "failedMessage": ""},
            ], "total": 2}))])
        status = provider.get_status("fax-123")
        assert status.is_terminal and status.is_success
        assert status.status == "completed"
        assert status.num_pages == 4
        assert status.completed_at.startswith("2026-04-02")
        req = provider._session.requests[0]
        assert req["url"].endswith("/fax/send")
        assert req["params"]["limit"] == 100

    def test_get_status_failed_maps_failure(self):
        provider = self._provider([
            StubResponse(200, envelope({"faxes": [
                {"id": "fax-123", "status": "failed",
                 "failedMessage": "line busy"}], "total": 1}))])
        status = provider.get_status("fax-123")
        assert status.status == "failure"
        assert not status.is_success
        assert status.failed_message == "line busy"

    def test_get_status_not_found(self):
        provider = self._provider([
            StubResponse(200, envelope({"faxes": [], "total": 0}))])
        with pytest.raises(FaxError, match="not found"):
            provider.get_status("fax-999")


# ---------------------------------------------------------------------------
# Electronic signature / declaration gate
# ---------------------------------------------------------------------------

class TestSignature:
    def _sign(self, filing, eid, **kwargs):
        return filing.sign_filing(eid, 2025, "Hans Mueller", "Owner",
                                  signed_date="2026-04-01", **kwargs)

    def test_sign_creates_signed_1120_and_declaration(self, filing,
                                                      generated_filing):
        from pyledger.tax_filing import PERJURY_DECLARATION
        eid, paths = generated_filing
        result = self._sign(filing, eid)

        assert result["signed_1120_path"].endswith(
            "f1120_proforma_2025_signed.pdf")
        from pypdf import PdfReader
        text = PdfReader(result["signed_1120_path"]).pages[0].extract_text()
        assert "/s/ Hans Mueller" in text
        assert "2026-04-01" in text
        assert "Owner" in text  # title fallback overlay (no AcroForm here)

        declaration = filing.get_declaration(eid, 2025)
        assert declaration["declaration_text"] == PERJURY_DECLARATION
        assert declaration["signer_name"] == "Hans Mueller"
        assert declaration["signature_kind"] == "typed"
        # Hashes cover the signed 1120 and the rest of the package.
        assert set(declaration["files_sha256"]) == {
            result["signed_1120_path"], paths["form_5472_path"],
            paths["part_v_statement_path"]}

        c = filing.conn.cursor()
        c.execute("SELECT form_1120_path FROM form_filings WHERE entity_id = ?",
                  (eid,))
        assert c.fetchone()[0] == result["signed_1120_path"]
        for action in ("DECLARATION_ACCEPTED", "FORM_SIGNED"):
            c.execute("SELECT COUNT(*) FROM tax_audit_trail WHERE action = ?",
                      (action,))
            assert c.fetchone()[0] == 1

    def test_sign_requires_generated_filing(self, filing):
        eid = filing.add_entity("No Filing LLC", "foreign_owned_de",
                                "1 St", "Dover")
        with pytest.raises(ValueError, match="No filing found"):
            self._sign(filing, eid)

    def test_sign_requires_1120(self, filing, generated_filing):
        eid, _ = generated_filing
        c = filing.conn.cursor()
        c.execute("UPDATE form_filings SET form_1120_path = NULL "
                  "WHERE entity_id = ?", (eid,))
        filing.conn.commit()
        with pytest.raises(ValueError, match="no pro-forma 1120"):
            self._sign(filing, eid)

    def test_resign_starts_from_unsigned_original(self, filing,
                                                  generated_filing):
        eid, _ = generated_filing
        self._sign(filing, eid)
        result = self._sign(filing, eid)  # sign again
        from pypdf import PdfReader
        text = PdfReader(result["signed_1120_path"]).pages[0].extract_text()
        assert text.count("/s/ Hans Mueller") == 1  # no stacked overlays

    def test_fax_refuses_unsigned(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider())
        with pytest.raises(FaxError, match="not signed"):
            service.send_filing(eid, 2025)

    def test_fax_sends_signed_package(self, filing, generated_filing):
        eid, _ = generated_filing
        self._sign(filing, eid)
        provider = FakeProvider()
        service = FilingFaxService(filing, provider)
        record = service.send_filing(eid, 2025)
        assert record["status"] == "queued"
        # The signed 1120 is what got merged and sent.
        assert any(p.endswith("_signed.pdf") for p in record["files"])

    def test_fax_detects_tampering_after_signature(self, filing,
                                                   generated_filing):
        eid, paths = generated_filing
        self._sign(filing, eid)
        make_pdf(paths["form_5472_path"], pages=3)  # regenerate != signed
        service = FilingFaxService(filing, FakeProvider())
        with pytest.raises(FaxError, match="changed after it was signed"):
            service.send_filing(eid, 2025)

    def test_unsigned_escape_hatch(self, filing, generated_filing):
        eid, _ = generated_filing
        service = FilingFaxService(filing, FakeProvider())
        record = service.send_filing(eid, 2025, allow_unsigned=True)
        assert record["status"] == "queued"
