"""
IRS form field maps for Form 5472, Form 1120, and Form 7004.

Pure data module: maps semantic field names to the qualified AcroForm field
names inside the official IRS PDF templates, keyed by form revision. Field
names were extracted from the official PDFs at https://www.irs.gov/pub/irs-pdf/
with pypdf's PdfReader.get_fields() and verified against the rendered forms.

No third-party imports — importable everywhere, trivially testable.
"""

from typing import Any, Dict, Optional


IRS_FORM_URLS: Dict[str, str] = {
    "f5472": "https://www.irs.gov/pub/irs-pdf/f5472.pdf",
    "f1120": "https://www.irs.gov/pub/irs-pdf/f1120.pdf",
    "f7004": "https://www.irs.gov/pub/irs-pdf/f7004.pdf",
}

# SHA256 of the template PDFs the field maps below were built against.
# A mismatch is a warning (IRS revises forms), not an error: the field-map
# compatibility check in irs_pdf.verify_field_map is the real gate.
EXPECTED_SHA256: Dict[str, str] = {
    "f5472": "7ac5b2c3ea1c1184cde04f52b6f2faa88d30124d8617beda350da1be5e0c2c1d",
    "f1120": "016c7fb4042a565c23a98014b17019af7ddc89e3260dd3f926b84d6688b7be6e",
    "f7004": "9fc3dbf661741266974b29444c5649993d0105531b56fe34b5dc14c37a89f932",
}

# ---------------------------------------------------------------------------
# Form 5472 (Rev. December 2023)
# ---------------------------------------------------------------------------

FORM_5472_REVISION = "2023-12"

_P1 = "topmostSubform[0].Page1[0]"
_P2 = "topmostSubform[0].Page2[0]"

FORM_5472_FIELDS: Dict[str, Dict[str, str]] = {
    "2023-12": {
        # Header: tax year beginning / ending
        "tax_year_begin": f"{_P1}.Pg1Header[0].f1_1[0]",
        "tax_year_begin_yy": f"{_P1}.Pg1Header[0].f1_2[0]",
        "tax_year_end": f"{_P1}.Pg1Header[0].f1_3[0]",
        "tax_year_end_yy": f"{_P1}.Pg1Header[0].f1_4[0]",
        # Part I — Reporting Corporation
        "reporting_corp_name": f"{_P1}.Line1a[0].f1_5[0]",
        "reporting_corp_street": f"{_P1}.Line1a[0].f1_6[0]",
        "reporting_corp_city_state_zip": f"{_P1}.Line1a[0].f1_7[0]",
        "reporting_corp_ein": f"{_P1}.f1_8[0]",                 # 1b
        "total_assets": f"{_P1}.f1_9[0]",                       # 1c
        "principal_business_activity": f"{_P1}.f1_10[0]",       # 1d
        "principal_business_activity_code": f"{_P1}.f1_11[0]",  # 1e
        "total_gross_payments_this_form": f"{_P1}.Line1f_ReadOrder[0].f1_12[0]",  # 1f
        "total_forms_5472_filed": f"{_P1}.f1_13[0]",            # 1g
        "total_gross_payments_all_forms": f"{_P1}.f1_14[0]",    # 1h
        "total_parts_viii": f"{_P1}.f1_15[0]",                  # 1k
        "country_of_incorporation": f"{_P1}.f1_16[0]",          # 1l
        "date_of_incorporation": f"{_P1}.f1_17[0]",             # 1m
        "country_filing_as_resident": f"{_P1}.f1_18[0]",        # 1n
        "principal_country_business": f"{_P1}.f1_19[0]",        # 1o
        # Part II — 25% Foreign Shareholder (direct shareholder #1, 4a-4e)
        "shareholder_name_address": f"{_P1}.f1_20[0]",          # 4a
        "shareholder_us_tin": f"{_P1}.f1_21[0]",                # 4b(1)
        "shareholder_reference_id": f"{_P1}.f1_22[0]",          # 4b(2)
        "shareholder_ftin": f"{_P1}.f1_23[0]",                  # 4b(3)
        "shareholder_country_business": f"{_P1}.f1_24[0]",      # 4c
        "shareholder_country_citizenship": f"{_P1}.f1_25[0]",   # 4d
        "shareholder_country_tax_resident": f"{_P1}.f1_26[0]",  # 4e
        # Part III — Related Party (8a-8g)
        "related_party_name_address": f"{_P2}.f2_1[0]",         # 8a
        "related_party_us_tin": f"{_P2}.f2_2[0]",               # 8b(1)
        "related_party_reference_id": f"{_P2}.f2_3[0]",         # 8b(2)
        "related_party_ftin": f"{_P2}.f2_4[0]",                 # 8b(3)
        "related_party_business_activity": f"{_P2}.f2_5[0]",    # 8c
        "related_party_business_code": f"{_P2}.f2_6[0]",        # 8d
        "related_party_country_business": f"{_P2}.f2_7[0]",     # 8f
        "related_party_country_tax_resident": f"{_P2}.f2_8[0]", # 8g
    }
}

FORM_5472_CHECKBOXES: Dict[str, Dict[str, tuple]] = {
    "2023-12": {
        # (qualified name, on-state export value)
        "initial_year": (f"{_P1}.Line1j_ReadOrder[0].c1_2[0]", "/1"),  # 1j
        "fifty_pct_foreign_owned": (f"{_P1}.c1_3[0]", "/1"),           # 2
        "foreign_owned_de": (f"{_P1}.c1_4[0]", "/1"),                  # 3
        "related_party_foreign_person": (f"{_P2}.c2_1[0]", "/1"),      # 8 box
        "related_party_is_25pct_shareholder": (f"{_P2}.c2_4[0]", "/1"),# 8e
        "part_v_statement_attached": (f"{_P2}.PartV[0].c2_6[0]", "/1"),
    }
}

# Part IV monetary lines (Rev. Dec 2023: lines 9-36) -> qualified field name.
# "Received" block is lines 9-21 (total 22); "Paid" block is 23-35 (total 36).
FORM_5472_PART_IV_FIELDS: Dict[str, Dict[str, str]] = {
    "2023-12": {
        "9": f"{_P2}.f2_9[0]",     # Sales of stock in trade (inventory)
        "10": f"{_P2}.f2_10[0]",   # Sales of tangible property
        "11": f"{_P2}.f2_11[0]",   # Platform contribution payments received
        "12": f"{_P2}.f2_12[0]",   # Cost sharing payments received
        "13a": f"{_P2}.f2_13[0]",  # Rents received
        "13b": f"{_P2}.f2_14[0]",  # Royalties received
        "14": f"{_P2}.f2_15[0]",   # Sales/leases/licenses of intangibles
        "15": f"{_P2}.f2_16[0]",   # Consideration received for services
        "16": f"{_P2}.f2_17[0]",   # Commissions received
        "17a": f"{_P2}.f2_18[0]",  # Amounts borrowed - beginning balance
        "17b": f"{_P2}.f2_19[0]",  # Amounts borrowed - ending balance
        "18": f"{_P2}.f2_20[0]",   # Interest received
        "19": f"{_P2}.f2_21[0]",   # Premiums received
        "20": f"{_P2}.f2_22[0]",   # Loan guarantee fees received
        "21": f"{_P2}.f2_23[0]",   # Other amounts received
        "22": f"{_P2}.f2_24[0]",   # TOTAL received (lines 9-21)
        "23": f"{_P2}.f2_25[0]",   # Purchases of stock in trade
        "24": f"{_P2}.f2_26[0]",   # Purchases of tangible property
        "25": f"{_P2}.f2_27[0]",   # Platform contribution payments paid
        "26": f"{_P2}.f2_28[0]",   # Cost sharing payments paid
        "27a": f"{_P2}.f2_29[0]",  # Rents paid
        "27b": f"{_P2}.f2_30[0]",  # Royalties paid
        "28": f"{_P2}.f2_31[0]",   # Purchases/leases of intangibles
        "29": f"{_P2}.f2_32[0]",   # Consideration paid for services
        "30": f"{_P2}.f2_33[0]",   # Commissions paid
        "31a": f"{_P2}.f2_34[0]",  # Amounts loaned - beginning balance
        "31b": f"{_P2}.f2_35[0]",  # Amounts loaned - ending balance
        "32": f"{_P2}.f2_36[0]",   # Interest paid
        "33": f"{_P2}.f2_37[0]",   # Premiums paid
        "34": f"{_P2}.f2_38[0]",   # Loan guarantee fees paid
        "35": f"{_P2}.f2_39[0]",   # Other amounts paid
        "36": f"{_P2}.f2_40[0]",   # TOTAL paid (lines 23-35)
    }
}

# Lines belonging to the "received" block (totalled on line 22); everything
# else in Part IV totals on line 36.
PART_IV_RECEIVED_LINES = {"9", "10", "11", "12", "13a", "13b", "14", "15",
                          "16", "17a", "17b", "18", "19", "20", "21"}

# ---------------------------------------------------------------------------
# Form 1120 (2025 revision) — pro-forma header fields only
# ---------------------------------------------------------------------------

FORM_1120_REVISION = "2025"

_H = "topmostSubform[0].Page1[0]"

FORM_1120_FIELDS: Dict[str, Dict[str, str]] = {
    "2025": {
        "name": f"{_H}.NameFieldsReadOrder[0].f1_4[0]",
        "street": f"{_H}.NameFieldsReadOrder[0].f1_5[0]",
        "room_suite": f"{_H}.NameFieldsReadOrder[0].f1_6[0]",
        "city": f"{_H}.NameFieldsReadOrder[0].f1_7[0]",
        "state": f"{_H}.NameFieldsReadOrder[0].f1_8[0]",
        "country": f"{_H}.NameFieldsReadOrder[0].f1_9[0]",
        "zip": f"{_H}.NameFieldsReadOrder[0].f1_10[0]",
        "ein": f"{_H}.f1_11[0]",             # Item B
        "date_incorporated": f"{_H}.f1_12[0]",  # Item C
        "total_assets": f"{_H}.f1_13[0]",       # Item D
    }
}

FORM_1120_CHECKBOXES: Dict[str, Dict[str, tuple]] = {
    "2025": {
        "initial_return": (f"{_H}.c1_6[0]", "/1"),   # E(1)
        "final_return": (f"{_H}.c1_7[0]", "/1"),     # E(2)
        "name_change": (f"{_H}.c1_8[0]", "/1"),      # E(3)
        "address_change": (f"{_H}.c1_9[0]", "/1"),   # E(4)
    }
}

# "Foreign-owned U.S. DE" banner across the top of page 1 — not a form field,
# drawn as a reportlab overlay. Coordinates in PDF points (origin bottom-left).
FORM_1120_OVERLAY: Dict[str, Dict[str, float]] = {
    # Centered in the whitespace above the form title (topmost print y≈747,
    # page height 792).
    "de_banner": {"page": 0, "x": 210.0, "y": 768.0, "size": 13.0},
}
FORM_1120_DE_BANNER_TEXT = "Foreign-owned U.S. DE"

# "Sign Here" block on page 1. The officer signature line and Date column
# are not form fields (drawn as overlays just above the line at y≈90);
# Title is the AcroForm field f1_58. Coordinates verified against the 2025
# template ("Signature of officer" caption prints at x=74, y=82.4; the
# Title field rect is [324, 90, 460.8, 102]).
FORM_1120_SIGNATURE: Dict[str, Dict[str, Any]] = {
    "2025": {
        "name": {"page": 0, "x": 70.0, "y": 92.0, "size": 11.0},
        "date": {"page": 0, "x": 282.0, "y": 92.0, "size": 8.0},
        "title_field":
            "topmostSubform[0].Page1[0].SignHere-ReadOrder[0].f1_58[0]",
        "title_fallback": {"page": 0, "x": 328.0, "y": 92.0, "size": 8.0},
        # Bounding box for an optional handwritten-signature image.
        "image_box": {"page": 0, "x": 70.0, "y": 88.0,
                      "w": 150.0, "h": 26.0},
    }
}

# ---------------------------------------------------------------------------
# Form 7004 (Rev. December 2018, current)
# ---------------------------------------------------------------------------

FORM_7004_REVISION = "2018-12"

_F = "topmostSubform[0].Page1[0]"

FORM_7004_FIELDS: Dict[str, Dict[str, str]] = {
    "2018-12": {
        "name": f"{_F}.f1_1[0]",
        "identifying_number": f"{_F}.f1_2[0]",
        "street": f"{_F}.f1_3[0]",
        "room_suite": f"{_F}.f1_4[0]",
        "city": f"{_F}.f1_5[0]",
        "state": f"{_F}.f1_6[0]",
        "country": f"{_F}.f1_7[0]",
        "zip": f"{_F}.f1_8[0]",
        # Part I line 1: form code, two single-character comb boxes.
        "form_code_digit1": f"{_F}.f1_9[0]",
        "form_code_digit2": f"{_F}.f1_10[0]",
        # Part II line 5a: calendar year
        "calendar_year": f"{_F}.f1_11[0]",
        # Part II lines 6-8
        "tentative_tax": f"{_F}.f1_16[0]",
        "total_payments": f"{_F}.f1_17[0]",
        "balance_due": f"{_F}.f1_18[0]",
    }
}

# Form 7004 Part I line 1 code for Form 1120.
FORM_7004_CODE_1120 = "12"


def get_field_map(form: str, revision: Optional[str] = None) -> Dict[str, str]:
    """Return the semantic-name -> qualified-name map for a form revision."""
    maps = {
        "f5472": (FORM_5472_FIELDS, FORM_5472_REVISION),
        "f1120": (FORM_1120_FIELDS, FORM_1120_REVISION),
        "f7004": (FORM_7004_FIELDS, FORM_7004_REVISION),
    }
    if form not in maps:
        raise ValueError(f"Unknown form: {form}")
    table, default_rev = maps[form]
    return table[revision or default_rev]
