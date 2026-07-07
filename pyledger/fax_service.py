"""
Fax transmission for IRS filings (Notifyre-backed).

Sends the generated Form 5472 / pro-forma 1120 package to the IRS fax line
and records proof of transmission in the fax_transmissions table and the
tax audit trail. On confirmed delivery the filing is marked as filed.

The provider is a thin adapter (FaxProvider) so Notifyre can be swapped
out; fax APIs have a history of being acquired or discontinued.
NotifyreProvider talks to the Notifyre REST API with the API key from the
NOTIFY_API_KEY environment variable (falling back to a .env file in the
working directory). Notifyre sends in three steps: upload the PDF for
conversion, poll the conversion, then submit the fax to the recipient.

Statuses are normalized to provider-neutral values: queued, in_progress,
completed, failure. The package PDFs are merged into a single PDF before
sending so the IRS receives one transmission in the correct page order.

The `requests` import is lazy so core pyledger works without it installed.
"""

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pyledger.tax_filing import Form5472Filing, IRS_FAX_NUMBER, TaxPrinciple

NOTIFYRE_API_KEY_ENV = "NOTIFY_API_KEY"
# API version segment matches Notifyre's official SDKs.
NOTIFYRE_BASE_URL = "https://api.notifyre.com/20220711"

# Provider-neutral statuses; everything not terminal means "still in flight".
TERMINAL_STATUSES = {"completed", "failure"}

# Notifyre sent-fax status values -> provider-neutral values.
_NOTIFYRE_STATUS_MAP = {
    "accepted": "queued",
    "queued": "queued",
    "in_progress": "in_progress",
    "successful": "completed",
    "failed": "failure",
}

# How far back get_status searches Notifyre's sent-fax list for our fax id.
_STATUS_LOOKBACK_DAYS = 90


class FaxError(Exception):
    """Fax provider configuration or transmission error."""


def load_dotenv_value(name: str, path: str = ".env") -> Optional[str]:
    """Minimal .env reader: returns the value of `name`, or None."""
    if not os.path.isfile(path):
        return None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == name:
                return value.strip().strip("'\"") or None
    return None


def to_e164(number: str, default_country_code: str = "1") -> str:
    """Normalize a fax number like '855-887-7737' to '+18558877737'."""
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        raise FaxError(f"No digits in fax number: {number!r}")
    if number.strip().startswith("+"):
        return "+" + digits
    if len(digits) == 10:
        return f"+{default_country_code}{digits}"
    return "+" + digits


def merge_pdfs(paths: List[str], output_path: str) -> str:
    """Merge PDFs into one file, in order. Returns output_path."""
    from pypdf import PdfWriter  # Lazy, like the other PDF deps.
    writer = PdfWriter()
    for path in paths:
        writer.append(path)
    with open(output_path, "wb") as fh:
        writer.write(fh)
    return output_path


@dataclass
class FaxStatus:
    """Provider-neutral snapshot of a fax's delivery state."""
    provider_fax_id: str
    status: str
    num_pages: Optional[int] = None
    completed_at: Optional[str] = None
    failed_message: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_success(self) -> bool:
        return self.status == "completed"


class FaxProvider:
    """Interface for fax providers."""

    name = "abstract"

    def send(self, to_number: str, file_path: str,
             reference: Optional[str] = None) -> str:
        """Send one PDF as a fax. Returns the provider's fax id."""
        raise NotImplementedError

    def get_status(self, provider_fax_id: str) -> FaxStatus:
        """Fetch the current delivery status of a fax."""
        raise NotImplementedError


class NotifyreProvider(FaxProvider):
    """Notifyre REST API provider.

    Auth is the `x-api-token` header. A custom `session` (anything with
    requests' post/get signature) can be injected for tests.

    high_quality defaults to True: IRS form text is small and standard
    fax resolution can render it illegible.
    """

    name = "notifyre"

    def __init__(self, api_key: Optional[str] = None,
                 base_url: str = NOTIFYRE_BASE_URL,
                 high_quality: bool = True,
                 conversion_timeout: float = 180,
                 conversion_poll_interval: float = 5,
                 session: Any = None) -> None:
        self.api_key = (api_key
                        or os.environ.get(NOTIFYRE_API_KEY_ENV)
                        or load_dotenv_value(NOTIFYRE_API_KEY_ENV))
        if not self.api_key:
            raise FaxError(
                f"Notifyre API key missing. Set {NOTIFYRE_API_KEY_ENV} in "
                "the environment or a .env file (create a key in the "
                "Notifyre dashboard under Settings > API Tokens).")
        self.base_url = base_url.rstrip("/")
        self.high_quality = high_quality
        self.conversion_timeout = conversion_timeout
        self.conversion_poll_interval = conversion_poll_interval
        if session is None:
            import requests  # Lazy: core pyledger works without requests.
            session = requests.Session()
        self._session = session

    @property
    def _headers(self) -> Dict[str, str]:
        return {"x-api-token": self.api_key}

    def _check(self, resp: Any) -> Dict[str, Any]:
        """Unwrap Notifyre's {success, statusCode, message, payload} envelope."""
        try:
            body = resp.json()
        except ValueError:
            raise FaxError(
                f"Notifyre returned non-JSON (HTTP {resp.status_code})")
        if resp.status_code >= 400 or not body.get("success", False):
            raise FaxError(f"Notifyre error (HTTP {resp.status_code}): "
                           f"{body.get('message', 'unknown error')}")
        return body.get("payload") or {}

    def _upload_document(self, file_path: str) -> str:
        """Upload the PDF for conversion; return the converted document id."""
        with open(file_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        payload = self._check(self._session.post(
            f"{self.base_url}/fax/send/conversion",
            headers=self._headers,
            json={"base64Str": b64, "contentType": "application/pdf"},
            timeout=120))
        file_name = payload["fileName"]

        deadline = time.monotonic() + self.conversion_timeout
        while True:
            status = self._check(self._session.get(
                f"{self.base_url}/fax/send/conversion/{file_name}",
                headers=self._headers, timeout=60))
            if status.get("status") == "successful":
                return status["id"]
            if status.get("status") == "failed":
                raise FaxError(f"Notifyre document conversion failed "
                               f"for {os.path.basename(file_path)}")
            if time.monotonic() >= deadline:
                raise FaxError("Timed out waiting for Notifyre document "
                               "conversion")
            time.sleep(self.conversion_poll_interval)

    def send(self, to_number: str, file_path: str,
             reference: Optional[str] = None) -> str:
        if not os.path.isfile(file_path):
            raise FaxError(f"Fax attachment not found: {file_path}")
        document_id = self._upload_document(file_path)
        payload = self._check(self._session.post(
            f"{self.base_url}/fax/send",
            headers=self._headers,
            json={
                "templateName": "",
                "faxes": {
                    "clientReference": reference or "",
                    "files": [document_id],
                    "header": "",
                    "isHighQuality": self.high_quality,
                    "recipients": [{"type": "fax_number",
                                    "value": to_e164(to_number)}],
                    "scheduledDate": None,
                    "sendFrom": "",
                    "senderID": "",
                    "subject": reference or "",
                },
            },
            timeout=120))
        fax_id = str(payload.get("faxID", ""))
        if not fax_id:
            raise FaxError(f"Notifyre response has no faxID: {payload}")
        return fax_id

    def get_status(self, provider_fax_id: str) -> FaxStatus:
        now = datetime.now(timezone.utc)
        params = {
            "fromDate": int((now - timedelta(days=_STATUS_LOOKBACK_DAYS))
                            .timestamp()),
            "toDate": int((now + timedelta(days=1)).timestamp()),
            "sort": "desc",
            "limit": 100,
            "skip": 0,
        }
        payload = self._check(self._session.get(
            f"{self.base_url}/fax/send", headers=self._headers,
            params=params, timeout=60))
        for fax in payload.get("faxes", []):
            if str(fax.get("id")) == str(provider_fax_id):
                completed_at = None
                if fax.get("lastModifiedDateUtc"):
                    completed_at = datetime.fromtimestamp(
                        fax["lastModifiedDateUtc"],
                        timezone.utc).isoformat()
                return FaxStatus(
                    provider_fax_id=str(fax["id"]),
                    status=_NOTIFYRE_STATUS_MAP.get(fax.get("status", ""),
                                                    "in_progress"),
                    num_pages=fax.get("pages"),
                    completed_at=completed_at,
                    failed_message=fax.get("failedMessage") or None,
                    raw=fax)
        raise FaxError(
            f"Fax {provider_fax_id} not found in Notifyre sent faxes "
            f"(searched the last {_STATUS_LOOKBACK_DAYS} days)")


class FilingFaxService:
    """Sends a generated filing package by fax and records the outcome.

    Wraps a Form5472Filing (for filing lookups, mark_filed, and the audit
    trail) and a FaxProvider. Every transmission is persisted so the
    confirmation survives as proof of transmission.
    """

    def __init__(self, filing: Form5472Filing, provider: FaxProvider) -> None:
        self.filing = filing
        self.provider = provider
        self._init_table()

    def _init_table(self) -> None:
        c = self.filing.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS fax_transmissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
                tax_year INTEGER NOT NULL,
                provider TEXT NOT NULL,
                provider_fax_id TEXT,
                to_number TEXT NOT NULL,
                files TEXT NOT NULL,
                package_path TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                num_pages INTEGER,
                failed_message TEXT,
                completed_at TEXT,
                confirmation TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.filing.conn.commit()

    def package_files(self, entity_id: int, tax_year: int) -> List[str]:
        """The generated PDFs to fax, in IRS package order.

        Pro-forma 1120 goes on top, then Form 5472, then attachment
        statements. Form 7004 is excluded — the extension is its own
        separate transmission.
        """
        c = self.filing.conn.cursor()
        c.execute('''
            SELECT status, form_1120_path, form_5472_path,
                   part_v_statement_path, reasonable_cause_path
            FROM form_filings WHERE entity_id = ? AND tax_year = ?
        ''', (entity_id, tax_year))
        row = c.fetchone()
        if row is None or row[0] == "draft":
            raise FaxError(
                f"No generated filing for entity {entity_id}, year {tax_year}."
                " Run generate_filing first.")
        files = [p for p in row[1:] if p]
        missing = [p for p in files if not os.path.isfile(p)]
        if missing:
            raise FaxError(
                "Filing PDFs missing on disk (regenerate the filing): "
                + ", ".join(missing))
        if not files:
            raise FaxError("Filing has no PDFs recorded.")
        return files

    def _check_signature(self, entity_id: int, tax_year: int,
                         files: List[str]) -> None:
        """Require an accepted declaration covering exactly these files.

        An unsigned pro-forma 1120 is legally not a filed return, so the
        default path refuses to transmit one. The hashes recorded at
        signature time must match the files being sent — this ties the
        perjury declaration to the exact pages that reach the IRS.
        """
        declaration = self.filing.get_declaration(entity_id, tax_year)
        if declaration is None:
            raise FaxError(
                "Filing is not signed. Run 'pyledger tax-5472-sign' to "
                "accept the declaration and sign the pro-forma 1120, or "
                "pass allow_unsigned=True / --unsigned if the package was "
                "signed manually outside PyLedger.")
        recorded = declaration["files_sha256"]
        for path in files:
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if recorded.get(path) != digest:
                raise FaxError(
                    f"{path} changed after it was signed. Re-run "
                    "'pyledger tax-5472-sign' so the declaration covers "
                    "the current documents.")

    def send_filing(self, entity_id: int, tax_year: int,
                    to_number: str = IRS_FAX_NUMBER,
                    allow_unsigned: bool = False,
                    user_id: str = "system") -> Dict[str, Any]:
        """Merge the package into one PDF and queue it with the provider."""
        files = self.package_files(entity_id, tax_year)
        if not allow_unsigned:
            self._check_signature(entity_id, tax_year, files)
        package_path = os.path.join(
            os.path.dirname(files[0]),
            f"fax_package_{entity_id}_{tax_year}.pdf")
        merge_pdfs(files, package_path)

        c = self.filing.conn.cursor()
        c.execute('''
            INSERT INTO fax_transmissions
            (entity_id, tax_year, provider, to_number, files, package_path,
             status)
            VALUES (?, ?, ?, ?, ?, ?, 'queued')
        ''', (entity_id, tax_year, self.provider.name, to_e164(to_number),
              json.dumps(files), package_path))
        self.filing.conn.commit()
        transmission_id = int(c.lastrowid or 0)

        provider_fax_id = self.provider.send(
            to_number, package_path, reference=f"5472-{entity_id}-{tax_year}")

        c.execute('''
            UPDATE fax_transmissions SET provider_fax_id = ? WHERE id = ?
        ''', (provider_fax_id, transmission_id))
        self.filing.conn.commit()
        self.filing.log_audit_trail(
            user_id, "FAX_QUEUED", "fax_transmissions", str(transmission_id),
            None, {"entity_id": entity_id, "tax_year": tax_year,
                   "provider": self.provider.name,
                   "provider_fax_id": provider_fax_id,
                   "package_path": package_path, "files": files},
            TaxPrinciple.FILING, "Queued filing package for fax transmission")
        return self.get_transmission(transmission_id)

    def refresh_status(self, transmission_id: int,
                       user_id: str = "system") -> Dict[str, Any]:
        """Poll the provider and persist the latest status.

        On confirmed success the filing is marked as filed (method 'fax')
        and the provider confirmation is stored as proof of transmission.
        """
        record = self.get_transmission(transmission_id)
        if record is None:
            raise FaxError(f"Transmission {transmission_id} not found")
        if not record["provider_fax_id"]:
            raise FaxError(f"Transmission {transmission_id} was never queued "
                           "with the provider")
        previous_status = record["status"]
        status = self.provider.get_status(record["provider_fax_id"])

        c = self.filing.conn.cursor()
        c.execute('''
            UPDATE fax_transmissions
            SET status = ?, num_pages = ?, failed_message = ?,
                completed_at = ?, confirmation = ?
            WHERE id = ?
        ''', (status.status, status.num_pages, status.failed_message,
              status.completed_at, json.dumps(status.raw), transmission_id))
        self.filing.conn.commit()

        if status.is_success and previous_status != "completed":
            filed_date = (status.completed_at or datetime.now().isoformat())[:10]
            self.filing.mark_filed(record["entity_id"], record["tax_year"],
                                   filed_date, "fax", user_id=user_id)
            self.filing.log_audit_trail(
                user_id, "FAX_CONFIRMED", "fax_transmissions",
                str(transmission_id), {"status": previous_status},
                {"status": status.status, "num_pages": status.num_pages,
                 "completed_at": status.completed_at},
                TaxPrinciple.FILING,
                "Fax delivery confirmed; filing marked as filed")
        return self.get_transmission(transmission_id)

    def wait_for_completion(self, transmission_id: int, timeout: float = 600,
                            poll_interval: float = 15,
                            user_id: str = "system") -> Dict[str, Any]:
        """Poll until the fax reaches a terminal status or timeout elapses."""
        deadline = time.monotonic() + timeout
        while True:
            record = self.refresh_status(transmission_id, user_id=user_id)
            if record["status"] in TERMINAL_STATUSES:
                return record
            if time.monotonic() >= deadline:
                return record
            time.sleep(poll_interval)

    def get_transmission(self, transmission_id: int) -> Optional[Dict[str, Any]]:
        c = self.filing.conn.cursor()
        c.execute("SELECT * FROM fax_transmissions WHERE id = ?",
                  (transmission_id,))
        row = c.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in c.description]
        record = dict(zip(cols, row))
        record["files"] = json.loads(record["files"])
        return record

    def list_transmissions(self, entity_id: int,
                           tax_year: int) -> List[Dict[str, Any]]:
        c = self.filing.conn.cursor()
        c.execute('''
            SELECT * FROM fax_transmissions
            WHERE entity_id = ? AND tax_year = ? ORDER BY id
        ''', (entity_id, tax_year))
        cols = [d[0] for d in c.description]
        records = [dict(zip(cols, row)) for row in c.fetchall()]
        for record in records:
            record["files"] = json.loads(record["files"])
        return records
