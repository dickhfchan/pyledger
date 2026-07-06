# Filing Rules, Deadlines, Penalties, Templates

## Who must file

`check_filing_requirement(entity_id, tax_year)` implements these rules and returns `required`, `reasons`, `forms_needed`, `deadline`, `extended_deadline`, `can_efile`, and submission details.

- **`foreign_owned_de`** (foreign-owned single-member LLC): required if it has a foreign owner **and** any reportable transaction in the year. Files Form 5472 + pro-forma 1120. Required even with zero income — formation costs, capital contributions, and expenses paid by the owner all count as reportable transactions, so a "dormant" first-year LLC usually still must file. **Cannot e-file.**
- **`foreign_owned_corporation`**: required if any owner holds ≥ 25% **and** there are reportable transactions. Attaches Form 5472 to its regular 1120; can e-file through normal 1120 channels (pyledger only generates the 5472 in this case).

## Deadlines and extension

`get_deadline(tax_year, extended=False, tax_year_end="12-31")`: 15th day of the 4th month after year end — April 15 of the following year for calendar-year filers. Form 7004 extends by 6 months (October 15). The 7004 must itself be filed by the regular deadline; generate it with `--extension` on `tax-5472-generate` or `pyledger tax-7004-generate`.

## Penalties (IRC §6038A(d))

`estimate_penalty(tax_year, as_of=..., filed_date=..., irs_notice_date=..., num_forms=..., extended=...)`:

- Base: **$25,000 per Form 5472 per year** if filed after the deadline (flat statutory amount, not inflation-indexed).
- Continuation: another $25,000 per form per 30-day period (rounded up), starting 90 days after an IRS notice date, if still unfiled/filed later.
- Returns `{is_late, deadline, base_penalty, continuation_periods, continuation_penalty, total, explanation}`.

For late filings, pass `reasonable_cause_text` to `generate_filing` (or `--reasonable-cause-file` on the CLI) to render a reasonable-cause statement PDF supporting penalty abatement.

## Submission (DE filings)

- Fax: **855-887-7737**
- Mail: Internal Revenue Service, 1973 Rulon White Blvd, M/S 6112 Attn: PIN Unit, Ogden, UT 84201
- Sign the pro-forma 1120 (the 5472 itself is not signed for a DE filing). Keep copies and proof of transmission.
- Record submission with `mark_filed(entity_id, tax_year, filed_date, method)` — method must be `"mail"` or `"fax"`.

## Validation rules

`validate_filing_data(entity_id, tax_year)` gates generation. Errors (block): missing EIN or EIN not `NN-NNNNNNN`; missing entity address_line1/city; no foreign owner; no owner ≥ 25%; owner missing address_line1/city/country; non-positive transaction amounts. Warnings (don't block): owner without any TIN (form prints "FOREIGNUS" per IRS instructions); no reportable transactions for the year.

If the entity has no EIN, it must apply with Form SS-4 before filing — there is no workaround.

## Form revisions

Field maps in `pyledger/irs_form_maps.py` are pinned to specific IRS revisions: Form 5472 Rev. Dec 2023, Form 1120 (2025), Form 7004 Rev. Dec 2018. Templates are downloaded from `https://www.irs.gov/pub/irs-pdf/` on first use and cached in `~/.pyledger/irs_forms/` (override: `PYLEDGER_IRS_TEMPLATE_DIR` env var, `--template-dir` flag, or `template_dir=` argument).

- A SHA256 mismatch against `EXPECTED_SHA256` logs a **warning** only — the IRS republishes PDFs without structural changes.
- A `TemplateFieldMismatchError` means the AcroForm field names changed (a real new revision). Fix: dump the new field names with `pypdf.PdfReader(path).get_fields()`, add a new revision entry to the field-map dicts in `irs_form_maps.py`, update `FORM_*_REVISION` and `EXPECTED_SHA256`, and verify against the rendered PDF.
- The "Foreign-owned U.S. DE" banner on the pro-forma 1120 is not a form field; it is drawn as a reportlab overlay at coordinates in `FORM_1120_OVERLAY`.
