"""
IRS PDF generation engine for PyLedger tax filings.

Fills the official IRS PDF templates (Form 5472, Form 1120, Form 7004) via
pypdf AcroForm filling. The IRS PDFs are AcroForm/XFA hybrids; after filling
the AcroForm layer we strip the /XFA key and set NeedAppearances so viewers
(including Adobe Reader) render the filled values.

A reportlab overlay engine handles text that is not a form field — notably
the "Foreign-owned U.S. DE" banner across the top of the pro-forma 1120 —
and serves as the fallback path if a future IRS revision drops AcroForm.

All pypdf/reportlab imports live in this module so that core pyledger can be
imported without the PDF dependencies installed.
"""

import hashlib
import io
import logging
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, DictionaryObject

PathLike = Union[str, Path]

from pyledger.irs_form_maps import (
    IRS_FORM_URLS,
    EXPECTED_SHA256,
    FORM_5472_FIELDS,
    FORM_5472_CHECKBOXES,
    FORM_5472_PART_IV_FIELDS,
    FORM_5472_REVISION,
    PART_IV_RECEIVED_LINES,
    FORM_1120_FIELDS,
    FORM_1120_CHECKBOXES,
    FORM_1120_OVERLAY,
    FORM_1120_DE_BANNER_TEXT,
    FORM_1120_REVISION,
    FORM_1120_SIGNATURE,
    FORM_7004_FIELDS,
    FORM_7004_REVISION,
    FORM_7004_CODE_1120,
)
from pyledger.tax_filing import (
    DISCLAIMER,
    PART_IV_LINE_FOR_TYPE,
    ReportableTransactionType,
)

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".pyledger" / "irs_forms"
TEMPLATE_DIR_ENV = "PYLEDGER_IRS_TEMPLATE_DIR"


class TemplateFieldMismatchError(Exception):
    """The template's AcroForm fields don't match the shipped field map.

    Usually means the IRS published a new form revision. Update the field
    maps in pyledger/irs_form_maps.py for the new revision (dump field names
    with pypdf's PdfReader.get_fields()).
    """


class IRSTemplateManager:
    """Downloads and caches the official IRS PDF templates."""

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        env_dir = os.environ.get(TEMPLATE_DIR_ENV)
        self.cache_dir = Path(cache_dir or env_dir or DEFAULT_CACHE_DIR)

    def get_template(self, form: str) -> Path:
        """Return the local path of a template, downloading if missing."""
        if form not in IRS_FORM_URLS:
            raise ValueError(f"Unknown form: {form}")
        path = self.cache_dir / f"{form}.pdf"
        if not path.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            url = IRS_FORM_URLS[form]
            logger.info("Downloading %s from %s", form, url)
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            path.write_bytes(data)
        self._check_hash(form, path)
        return path

    def _check_hash(self, form: str, path: Path) -> None:
        """Warn (not fail) if the template differs from the known revision."""
        expected = EXPECTED_SHA256.get(form)
        if not expected:
            return
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            logger.warning(
                "%s differs from the revision the field maps were built "
                "against (sha256 %s != %s). The IRS may have published a new "
                "revision; field-map verification will catch incompatibility.",
                path, actual[:12], expected[:12])


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Form5472Data:
    """Data needed to fill Form 5472."""
    entity: Dict[str, Any]
    owner: Dict[str, Any]
    tax_year: int
    totals_by_type: Dict[str, float]
    is_de: bool
    is_initial_year: bool = False


@dataclass
class Form1120ProFormaData:
    """Data needed to fill the pro-forma Form 1120 header."""
    entity: Dict[str, Any]
    tax_year: int
    is_initial_return: bool = False


@dataclass
class Form7004Data:
    """Data needed to fill Form 7004 (extension)."""
    entity: Dict[str, Any]
    tax_year: int


@dataclass
class OverlayItem:
    """A piece of text drawn on top of a PDF page."""
    page: int
    x: float
    y: float
    text: str
    size: float = 10.0
    font: str = "Helvetica-Bold"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def verify_field_map(reader: PdfReader,
                     field_map: Dict[str, str]) -> List[str]:
    """Return semantic names whose qualified field is missing from the PDF."""
    fields = reader.get_fields() or {}
    return [sem for sem, qualified in field_map.items()
            if qualified not in fields]


def _fill_acroform(template: PathLike, values: Dict[str, str],
                   checkboxes: Dict[str, str], out: PathLike,
                   overlays: Optional[List[OverlayItem]] = None) -> None:
    """Fill AcroForm fields, strip XFA, set NeedAppearances, write output.

    values/checkboxes are keyed by *qualified* field name; checkbox values
    are the on-state export value (e.g. "/1").
    """
    reader = PdfReader(str(template))
    if reader.get_fields() is None:
        raise TemplateFieldMismatchError(
            f"{template} has no AcroForm fields (pure-XFA or flattened "
            "revision). Switch this form to the overlay backend by adding "
            "coordinates to pyledger/irs_form_maps.py.")

    writer = PdfWriter()
    writer.append(reader)

    text_values = {k: v for k, v in values.items() if v}
    checkbox_values = {k: NameObject(v) for k, v in checkboxes.items()}
    all_values: Dict[str, Any] = {**text_values, **checkbox_values}
    for page in writer.pages:
        if "/Annots" in page:
            writer.update_page_form_field_values(
                page, all_values)

    # Strip the XFA layer so viewers render the filled AcroForm layer, and
    # ask viewers to regenerate field appearances.
    root = writer._root_object
    if "/AcroForm" in root:
        acro = root["/AcroForm"]
        assert isinstance(acro, DictionaryObject)
        if "/XFA" in acro:
            del acro["/XFA"]
        acro[NameObject("/NeedAppearances")] = BooleanObject(True)

    if overlays:
        _merge_overlays(writer, overlays)

    with open(out, "wb") as fh:
        writer.write(fh)


def _merge_overlays(writer: PdfWriter, items: List[OverlayItem]) -> None:
    """Draw overlay text onto writer pages via reportlab + merge_page."""
    from reportlab.pdfgen import canvas

    by_page: Dict[int, List[OverlayItem]] = {}
    for item in items:
        by_page.setdefault(item.page, []).append(item)

    for page_idx, page_items in by_page.items():
        page = writer.pages[page_idx]
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        for item in page_items:
            c.setFont(item.font, item.size)
            c.drawString(item.x, item.y, item.text)
        c.save()
        buf.seek(0)
        overlay_page = PdfReader(buf).pages[0]
        page.merge_page(overlay_page)


def _dollars(amount: float) -> str:
    """Whole-dollar formatting per Form 5472 convention (no $ sign)."""
    return f"{round(amount):,}"


def _entity_city_line(entity: Dict[str, Any]) -> str:
    parts = [entity.get("city") or "", entity.get("state") or "",
             entity.get("postal_code") or ""]
    line = ", ".join(p for p in parts[:2] if p)
    if parts[2]:
        line = f"{line} {parts[2]}" if line else parts[2]
    country = entity.get("country") or ""
    if country and country.upper() not in ("US", "USA", "UNITED STATES"):
        line = f"{line}, {country}"
    return line


def _owner_address_block(owner: Dict[str, Any]) -> str:
    lines = [owner["name"], owner["address_line1"]]
    if owner.get("address_line2"):
        lines.append(owner["address_line2"])
    city_parts = [owner.get("city") or "",
                  owner.get("state_or_province") or "",
                  owner.get("postal_code") or ""]
    lines.append(" ".join(p for p in city_parts if p))
    lines.append(owner["country"])
    return "\n".join(l for l in lines if l)


# ---------------------------------------------------------------------------
# Form fillers
# ---------------------------------------------------------------------------

def fill_form_5472(template: PathLike, data: Form5472Data, out: PathLike,
                   revision: str = FORM_5472_REVISION) -> None:
    """Fill Form 5472 for a foreign-owned entity."""
    fmap = FORM_5472_FIELDS[revision]
    cmap = FORM_5472_CHECKBOXES[revision]
    part_iv = FORM_5472_PART_IV_FIELDS[revision]

    reader = PdfReader(str(template))
    missing = verify_field_map(reader, fmap)
    if missing:
        raise TemplateFieldMismatchError(
            f"Form 5472 template is missing expected fields {missing}. "
            "The IRS likely published a new revision; update "
            "pyledger/irs_form_maps.py.")

    entity = data.entity
    owner = data.owner
    yy = str(data.tax_year)[-2:]

    # Map transaction-type totals onto Part IV lines and compute block totals.
    line_amounts: Dict[str, float] = {}
    part_v_total = 0.0
    for type_value, amount in data.totals_by_type.items():
        txn_type = ReportableTransactionType(type_value)
        line = PART_IV_LINE_FOR_TYPE[txn_type]
        if line is None:
            part_v_total += amount
        else:
            line_amounts[line] = line_amounts.get(line, 0.0) + amount
    received_total = sum(v for k, v in line_amounts.items()
                         if k in PART_IV_RECEIVED_LINES)
    paid_total = sum(v for k, v in line_amounts.items()
                     if k not in PART_IV_RECEIVED_LINES)
    # 1f/1h: total value of gross payments (all reportable transactions).
    gross_total = received_total + paid_total + part_v_total

    us_tin = owner.get("us_tin") or ""
    ftin = owner.get("foreign_tin") or ""
    if not us_tin and not ftin:
        # Per Form 5472 instructions for owners with no TIN of any kind.
        us_tin = "FOREIGNUS"

    values: Dict[str, str] = {
        fmap["tax_year_begin"]: f"January 1",
        fmap["tax_year_begin_yy"]: yy,
        fmap["tax_year_end"]: f"December 31",
        fmap["tax_year_end_yy"]: yy,
        fmap["reporting_corp_name"]: entity["name"],
        fmap["reporting_corp_street"]: " ".join(
            p for p in (entity.get("address_line1"),
                        entity.get("address_line2")) if p),
        fmap["reporting_corp_city_state_zip"]: _entity_city_line(entity),
        fmap["reporting_corp_ein"]: entity.get("ein") or "",
        fmap["total_assets"]: "",
        fmap["principal_business_activity"]:
            entity.get("principal_business_activity") or "",
        fmap["principal_business_activity_code"]:
            entity.get("principal_business_activity_code") or "",
        fmap["total_gross_payments_this_form"]: _dollars(gross_total),
        fmap["total_forms_5472_filed"]: "1",
        fmap["total_gross_payments_all_forms"]: _dollars(gross_total),
        fmap["total_parts_viii"]: "0",
        fmap["country_of_incorporation"]:
            entity.get("country_of_organization") or "US",
        fmap["date_of_incorporation"]: entity.get("formation_date") or "",
        fmap["country_filing_as_resident"]:
            entity.get("country_of_organization") or "US",
        fmap["principal_country_business"]: "United States",
        # Part II — direct 25% foreign shareholder
        fmap["shareholder_name_address"]: _owner_address_block(owner),
        fmap["shareholder_us_tin"]: us_tin,
        fmap["shareholder_reference_id"]: "",
        fmap["shareholder_ftin"]: ftin,
        fmap["shareholder_country_business"]:
            owner.get("country_of_tax_residence") or owner["country"],
        fmap["shareholder_country_citizenship"]:
            owner.get("country_of_citizenship_or_organization")
            or owner["country"],
        fmap["shareholder_country_tax_resident"]:
            owner.get("country_of_tax_residence") or owner["country"],
        # Part III — related party (the foreign owner)
        fmap["related_party_name_address"]: _owner_address_block(owner),
        fmap["related_party_us_tin"]: us_tin,
        fmap["related_party_reference_id"]: "",
        fmap["related_party_ftin"]: ftin,
        fmap["related_party_business_activity"]: "",
        fmap["related_party_business_code"]: "",
        fmap["related_party_country_business"]:
            owner.get("country_of_tax_residence") or owner["country"],
        fmap["related_party_country_tax_resident"]:
            owner.get("country_of_tax_residence") or owner["country"],
    }

    for line, amount in line_amounts.items():
        values[part_iv[line]] = _dollars(amount)
    if received_total:
        values[part_iv["22"]] = _dollars(received_total)
    if paid_total:
        values[part_iv["36"]] = _dollars(paid_total)

    checkboxes: Dict[str, str] = {}

    def check(name: str) -> None:
        qualified, on_value = cmap[name]
        checkboxes[qualified] = on_value

    check("related_party_foreign_person")
    check("related_party_is_25pct_shareholder")
    if data.is_de:
        check("foreign_owned_de")
    if owner.get("ownership_pct", 0) >= 50.0:
        check("fifty_pct_foreign_owned")
    if data.is_initial_year:
        check("initial_year")
    if part_v_total > 0 and data.is_de:
        check("part_v_statement_attached")

    _fill_acroform(template, values, checkboxes, out)


def fill_form_1120_proforma(template: PathLike, data: Form1120ProFormaData,
                            out: PathLike,
                            revision: str = FORM_1120_REVISION) -> None:
    """Fill the pro-forma Form 1120 header with the DE banner overlay.

    Per the Form 5472 instructions, a foreign-owned U.S. DE files a pro-forma
    1120 containing only the entity's name, address, items B and E, and
    "Foreign-owned U.S. DE" written across the top.
    """
    fmap = FORM_1120_FIELDS[revision]
    cmap = FORM_1120_CHECKBOXES[revision]

    reader = PdfReader(str(template))
    missing = verify_field_map(reader, fmap)
    if missing:
        raise TemplateFieldMismatchError(
            f"Form 1120 template is missing expected fields {missing}. "
            "Update pyledger/irs_form_maps.py for the new revision.")

    entity = data.entity
    country = entity.get("country") or "US"
    is_domestic = country.upper() in ("US", "USA", "UNITED STATES")

    values = {
        fmap["name"]: entity["name"],
        fmap["street"]: entity.get("address_line1") or "",
        fmap["room_suite"]: entity.get("address_line2") or "",
        fmap["city"]: entity.get("city") or "",
        fmap["state"]: entity.get("state") or "",
        fmap["country"]: "" if is_domestic else country,
        fmap["zip"]: entity.get("postal_code") or "",
        fmap["ein"]: entity.get("ein") or "",
        fmap["date_incorporated"]: entity.get("formation_date") or "",
    }

    checkboxes: Dict[str, str] = {}
    if data.is_initial_return:
        qualified, on_value = cmap["initial_return"]
        checkboxes[qualified] = on_value

    banner = FORM_1120_OVERLAY["de_banner"]
    overlays = [OverlayItem(page=int(banner["page"]), x=banner["x"],
                            y=banner["y"], size=banner["size"],
                            text=FORM_1120_DE_BANNER_TEXT)]

    _fill_acroform(template, values, checkboxes, out, overlays=overlays)


def sign_form_1120(pdf_path: PathLike, out: PathLike, signer_name: str,
                   signer_title: str, date_str: str,
                   signature_image: Optional[str] = None,
                   revision: str = FORM_1120_REVISION) -> None:
    """Apply an electronic signature to a filled (pro-forma) Form 1120.

    Draws the signature on the "Sign Here" block of page 1: the signer's
    typed name in the conventional /s/ notation (or a handwritten-signature
    image if provided) above the officer signature line, the date in the
    Date column, and the title via the Title AcroForm field (overlay
    fallback if the field is absent, e.g. on synthetic test templates).

    The e-signature itself is only the visible mark; the legal acceptance
    of the perjury declaration is recorded by the caller (see
    Form5472Filing.sign_filing).
    """
    sig = FORM_1120_SIGNATURE[revision]

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append(reader)

    overlays: List[OverlayItem] = []
    if not signature_image:
        name_spec = sig["name"]
        overlays.append(OverlayItem(
            page=int(name_spec["page"]), x=name_spec["x"], y=name_spec["y"],
            size=name_spec["size"], font="Helvetica-Oblique",
            text=f"/s/ {signer_name}"))
    date_spec = sig["date"]
    overlays.append(OverlayItem(
        page=int(date_spec["page"]), x=date_spec["x"], y=date_spec["y"],
        size=date_spec["size"], font="Helvetica", text=date_str))

    fields = reader.get_fields() or {}
    if sig["title_field"] in fields:
        for page in writer.pages:
            if "/Annots" in page:
                writer.update_page_form_field_values(
                    page, {sig["title_field"]: signer_title})
        root = writer._root_object
        if "/AcroForm" in root:
            acro = root["/AcroForm"]
            assert isinstance(acro, DictionaryObject)
            acro[NameObject("/NeedAppearances")] = BooleanObject(True)
    else:
        t = sig["title_fallback"]
        overlays.append(OverlayItem(
            page=int(t["page"]), x=t["x"], y=t["y"], size=t["size"],
            font="Helvetica", text=signer_title))

    _merge_overlays(writer, overlays)

    if signature_image:
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        box = sig["image_box"]
        page = writer.pages[int(box["page"])]
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        c.drawImage(ImageReader(signature_image), box["x"], box["y"],
                    width=box["w"], height=box["h"],
                    preserveAspectRatio=True, anchor="sw", mask="auto")
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])

    with open(out, "wb") as fh:
        writer.write(fh)


def fill_form_7004(template: PathLike, data: Form7004Data, out: PathLike,
                   revision: str = FORM_7004_REVISION) -> None:
    """Fill Form 7004 requesting a 6-month extension for the (pro-forma) 1120."""
    fmap = FORM_7004_FIELDS[revision]

    reader = PdfReader(str(template))
    missing = verify_field_map(reader, fmap)
    if missing:
        raise TemplateFieldMismatchError(
            f"Form 7004 template is missing expected fields {missing}. "
            "Update pyledger/irs_form_maps.py for the new revision.")

    entity = data.entity
    values = {
        fmap["name"]: entity["name"],
        fmap["identifying_number"]: entity.get("ein") or "",
        fmap["street"]: entity.get("address_line1") or "",
        fmap["room_suite"]: entity.get("address_line2") or "",
        fmap["city"]: entity.get("city") or "",
        fmap["state"]: entity.get("state") or "",
        fmap["country"]: "",
        fmap["zip"]: entity.get("postal_code") or "",
        fmap["form_code_digit1"]: FORM_7004_CODE_1120[0],
        fmap["form_code_digit2"]: FORM_7004_CODE_1120[1],
        fmap["calendar_year"]: str(data.tax_year)[-2:],
        fmap["tentative_tax"]: "0",
        fmap["total_payments"]: "0",
        fmap["balance_due"]: "0",
    }

    _fill_acroform(template, values, {}, out)


# ---------------------------------------------------------------------------
# Statement rendering (reportlab, following the invoices.py story pattern)
# ---------------------------------------------------------------------------

def _statement_doc(out: PathLike, title: str,
                   paragraphs: List[str]) -> None:
    """Render a simple statement PDF with a title and body paragraphs."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    doc = SimpleDocTemplate(str(out), pagesize=LETTER,
                            topMargin=1 * inch, bottomMargin=1 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("StmtTitle", parent=styles["Heading1"],
                                 fontSize=14, spaceAfter=18)
    body = ParagraphStyle("StmtBody", parent=styles["Normal"],
                          fontSize=10, leading=14, spaceAfter=10)
    small = ParagraphStyle("StmtSmall", parent=styles["Normal"],
                           fontSize=8, leading=10, textColor="#555555")

    story: List[Any] = [Paragraph(title, title_style)]
    for p in paragraphs:
        story.append(Paragraph(p, body))
    story.append(Spacer(1, 24))
    story.append(Paragraph(DISCLAIMER, small))
    doc.build(story)


def render_reasonable_cause_statement(entity: Dict[str, Any], tax_year: int,
                                      cause_text: str, out: PathLike) -> None:
    """Render a reasonable-cause statement for late-filing penalty relief."""
    header = (
        f"Taxpayer: {entity['name']} | EIN: {entity.get('ein') or 'N/A'} | "
        f"Tax year: {tax_year}"
    )
    paragraphs = [
        header,
        "<b>Statement of Reasonable Cause — Request for Penalty Relief "
        "(Form 5472 / Pro-Forma Form 1120)</b>",
        "The taxpayer respectfully requests abatement of penalties under "
        "IRC §6038A for the late filing of Form 5472 and the attached "
        "pro-forma Form 1120 for the tax year referenced above, on the "
        "grounds of reasonable cause as described below:",
        cause_text,
        "The taxpayer has acted in good faith, and the failure to file "
        "timely was not due to willful neglect. The required forms are "
        "being filed together with this statement.",
    ]
    _statement_doc(out, "Reasonable Cause Statement", paragraphs)


def render_part_v_statement(entity: Dict[str, Any], owner: Dict[str, Any],
                            transactions: List[Dict[str, Any]],
                            out: PathLike) -> None:
    """Render the Form 5472 Part V attachment for a foreign-owned U.S. DE.

    Describes DE-typical reportable transactions (capital contributions,
    distributions, formation costs, expenses paid by the owner) as required
    by the Part V instructions.
    """
    type_labels = {
        "capital_contribution": "Capital contribution from foreign owner",
        "distribution": "Distribution to foreign owner",
        "expenses_paid_by_owner": "Entity expense paid by foreign owner",
        "formation_dissolution_costs": "Formation/dissolution cost",
        "other": "Other reportable transaction",
    }
    header = (
        f"Reporting corporation: {entity['name']} | "
        f"EIN: {entity.get('ein') or 'N/A'} | "
        f"Related party: {owner['name']} ({owner['country']})"
    )
    paragraphs = [
        header,
        "<b>Form 5472, Part V — Reportable Transactions of a Reporting "
        "Corporation That Is a Foreign-Owned U.S. DE</b>",
        "The following reportable transactions occurred between the "
        "reporting corporation (a foreign-owned U.S. disregarded entity) "
        "and its foreign owner during the tax year:",
    ]
    total = 0.0
    for t in transactions:
        label = type_labels.get(t["txn_type"], t["txn_type"])
        desc = f" — {t['description']}" if t.get("description") else ""
        when = f" on {t['txn_date'][:10]}" if t.get("txn_date") else ""
        paragraphs.append(
            f"• {label}{when}: ${round(t['amount']):,}{desc}")
        total += t["amount"]
    paragraphs.append(f"<b>Total: ${round(total):,}</b>")
    _statement_doc(out, "Form 5472 — Part V Attachment", paragraphs)
