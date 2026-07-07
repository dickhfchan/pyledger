---
name: form-5472-filing
description: Prepare IRS Form 5472 / pro-forma 1120 filings for foreign-owned US entities using pyledger's tax_filing module. Use when asked to prepare, generate, check, or file Form 5472, a pro-forma 1120, or a Form 7004 extension; check filing requirements or deadlines; estimate IRC 6038A penalties; or record, scan for, or classify reportable transactions between a US entity and its foreign owner.
---

# Form 5472 / Pro-Forma 1120 Filing (pyledger)

Prepare the annual IRS information filing for foreign-owned US entities:

- **Foreign-owned single-member LLC (disregarded entity, "DE")**: files Form 5472 attached to a pro-forma Form 1120 — required even with zero income, cannot e-file (fax or mail only).
- **25%+ foreign-owned US corporation**: attaches Form 5472 to its regular Form 1120.

Code lives in `pyledger/tax_filing.py` (workflow + rules engine), `pyledger/irs_pdf.py` (PDF filling), and `pyledger/irs_form_maps.py` (AcroForm field maps per IRS form revision). Data is stored in `pyledger.db` (SQLite, in the working directory) alongside the ledger, so run everything from the repo root.

Always surface the module's disclaimer to the user: output assists with form preparation and is not tax advice.

## Workflow

Follow these steps in order for an annual filing. Steps 1–2 are one-time setup per entity.

### 1. Register the entity and foreign owner (Python API)

There is no non-interactive CLI for this — use the Python API. (`tax-5472-wizard` exists but is interactive; do not use it in an agent context.)

```python
import sqlite3
from pyledger.db import init_db
from pyledger.tax_filing import Form5472Filing

conn = sqlite3.connect("pyledger.db")
init_db(conn)
filing = Form5472Filing(conn)

entity_id = filing.add_entity(
    name="Acme LLC", entity_kind="foreign_owned_de",  # or "foreign_owned_corporation"
    address_line1="123 Main St", city="Dover", state="DE", postal_code="19901",
    ein="98-7654321",                 # required to generate; NN-NNNNNNN
    formation_date="2025-03-14",      # enables the "initial return" checkbox
    principal_business_activity="Software consulting",
)
filing.add_foreign_owner(
    entity_id, name="Jane Kwok", country="HK",
    address_line1="1 Queen's Rd", city="Hong Kong",
    foreign_tin="A1234567", ownership_pct=100.0,
)
```

Check for existing records first with `filing.list_entities()` / `filing.list_foreign_owners(entity_id)`.

### 2. (Optional) Map ledger accounts

`filing.map_account(entity_id, account_code, txn_type)` makes every ledger line on that account a high-confidence suggestion in step 3 (e.g. map the owner-loan liability account to `loan_from_owner`).

### 3. Gather reportable transactions

Scan the ledger and confirm suggestions, then add anything the ledger missed:

```python
for s in filing.suggest_reportable_transactions(entity_id, tax_year):
    # Review each with the user: s["description"], s["amount"], s["suggested_type"], s["confidence"], s["rationale"]
    filing.confirm_suggested_transaction(entity_id, tax_year,
        s["journal_entry_id"], s["suggested_type"], s["amount"])

filing.add_reportable_transaction(entity_id, tax_year,
    "capital_contribution", 50000.0, txn_date="2025-04-01",
    description="Initial funding from owner")
```

Present low/medium-confidence suggestions to the user before confirming. Amounts must be positive. Valid `txn_type` values and which Form 5472 line each lands on: see [references/transaction-types.md](references/transaction-types.md).

### 4. Check requirement and validate

```bash
pyledger tax-check --entity-id 1 --tax-year 2025        # requirement, deadline, penalty exposure
pyledger tax-list-transactions --entity-id 1 --tax-year 2025
```

In Python, `filing.check_filing_requirement(entity_id, tax_year)` returns the same data; `filing.validate_filing_data(entity_id, tax_year)` returns `{valid, errors, warnings}` — fix all errors before generating (missing/malformed EIN and missing owner are the common ones).

### 5. Generate the filing package

```bash
pyledger tax-5472-generate --entity-id 1 --tax-year 2025 --output-dir filings \
    [--extension] [--reasonable-cause-file cause.txt] [--template-dir DIR]
```

Produces the filled Form 5472, pro-forma 1120 with the "Foreign-owned U.S. DE" banner (DE only), optional Form 7004, optional reasonable-cause statement, and a Part V attachment for DE-typical items (contributions, distributions, formation costs, expenses paid by owner). A standalone extension: `pyledger tax-7004-generate`.

Requirements: `pypdf` and `reportlab` installed; first run downloads official IRS templates from irs.gov into `~/.pyledger/irs_forms/` (override with `--template-dir` or `PYLEDGER_IRS_TEMPLATE_DIR`). If generation raises `TemplateFieldMismatchError`, the IRS published a new form revision — see [references/filing-rules.md](references/filing-rules.md#form-revisions).

### 6. Sign (legal core — human acceptance required)

An unsigned 1120 is legally not a filed return. Before faxing, the signer must accept the penalty-of-perjury declaration and e-sign the pro-forma 1120:

```bash
pyledger tax-5472-sign --entity-id 1 --tax-year 2025 --name "Jane Kwok" --title "Owner"
```

**NEVER accept the declaration on the user's behalf.** Display `PERJURY_DECLARATION` (from `pyledger.tax_filing`) verbatim, get the user's explicit confirmation in conversation, and only then run the command with `--accept`. The command writes `f1120_proforma_<year>_signed.pdf` (typed `/s/ Name` signature; `--signature-image sig.png` for a handwritten image), records the acceptance plus SHA-256 hashes of every package PDF in `filing_declarations`, and audit-logs `DECLARATION_ACCEPTED` / `FORM_SIGNED`. If the filing is regenerated afterwards, it must be re-signed.

### 7. Submit

Relay the returned `next_steps` (DEs fax to 855-887-7737 or mail to IRS Ogden). Two paths:

**Fax via Notifyre (built in).** Requires `NOTIFY_API_KEY` in the environment or a `.env` file in the working directory. Refuses to send unless step 6 was completed and the files still match the signed hashes (`--unsigned` bypasses, for packages signed manually on paper). Merges the package into one PDF, sends it, and on confirmed delivery marks the filing as filed and stores the delivery receipt in `fax_transmissions` as proof of transmission:

```bash
pyledger tax-5472-fax --entity-id 1 --tax-year 2025 --wait   # defaults to the IRS fax number
pyledger tax-fax-status --transmission-id 1                  # re-check a pending fax
```

Confirm with the user before sending — this transmits the filing to the IRS. Use `--to` to override the destination for a test fax.

**Manual (mail, or fax sent elsewhere).** Once the user has actually submitted, record it:

```python
filing.mark_filed(entity_id, tax_year, filed_date="2026-04-10", method="fax")  # or "mail"
```

## References

- [references/transaction-types.md](references/transaction-types.md) — all `txn_type` values, Part IV line mapping, Part V items, classification heuristics used by the ledger scan.
- [references/filing-rules.md](references/filing-rules.md) — who must file, deadlines and extensions, IRC §6038A penalty math (`estimate_penalty`), submission channels, validation rules, IRS form revisions and template management.

## Verification

Run the module's tests after changing any tax-filing code: `python -m pytest pyledger/test_tax_filing.py`. Every mutation is audit-logged to the `tax_audit_trail` table — pass a real `user_id` instead of the default `"system"` when acting for a named user.
