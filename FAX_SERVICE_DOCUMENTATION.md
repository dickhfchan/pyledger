# IRS Filing Fax Service Documentation (Notifyre)

## Overview

PyLedger can fax the generated Form 5472 / pro-forma 1120 filing package directly to the IRS through the [Notifyre](https://notifyre.com) fax API. Foreign-owned US disregarded entities cannot e-file this filing — the IRS accepts it only by fax (855-887-7737) or mail — so the fax service closes the last step of the workflow: it merges the package into a single PDF, transmits it, tracks delivery, stores the provider's delivery receipt as **proof of transmission**, and marks the filing as filed once delivery is confirmed.

The implementation lives in `pyledger/fax_service.py`.

## 🎯 Key Features

- **One-command submission**: `pyledger tax-5472-fax` sends the whole generated package to the IRS fax line
- **Correct package assembly**: PDFs are merged in IRS order — pro-forma 1120 on top, then Form 5472, then the Part V and reasonable-cause statements. Form 7004 is never included (an extension request is its own separate transmission)
- **Proof of transmission**: every send is recorded in the `fax_transmissions` table; on delivery, Notifyre's receipt JSON is stored in the `confirmation` column
- **Automatic filing state**: confirmed delivery calls `mark_filed(..., method="fax")`; a failed fax never marks the filing as filed
- **Audit trail**: `FAX_QUEUED` and `FAX_CONFIRMED` entries are written to `tax_audit_trail`
- **Swappable provider**: Notifyre sits behind a small `FaxProvider` adapter, so changing vendors means implementing two methods

## 🚀 Setup

1. Create a Notifyre account at [notifyre.com](https://notifyre.com) (pay-as-you-go; top up from $10, roughly 3¢/page to US numbers).
2. Create an API token in the Notifyre dashboard under **Settings > API Tokens**.
3. Provide the token to PyLedger, either as an environment variable or in a `.env` file in the working directory:

```bash
# .env  (keep this file out of version control)
NOTIFY_API_KEY=your-notifyre-api-token
```

4. Ensure the `requests` package is installed (it is a standard PyLedger dependency; core PyLedger still imports fine without it).

## ✍️ Electronic Signature Gate

The fax service will not transmit an unsigned package. An unsigned 1120 is legally not a filed return, so the flow enforces the signature step:

```bash
pyledger tax-5472-sign --entity-id 1 --tax-year 2025 --name "Jane Kwok" --title "Owner"
```

This displays the Form 1120 penalty-of-perjury declaration and requires the signer to type `AGREE` (the acceptance is the taxpayer's personal legal act — software never accepts it for them). It then:

1. Writes `f1120_proforma_<year>_signed.pdf` with the signature drawn on the officer line — typed `/s/ Name` by default, or a handwritten image via `--signature-image sig.png` — plus the date and title.
2. Records the declaration text, signer, timestamp, and **SHA-256 hashes of every package PDF** in the `filing_declarations` table, and writes `DECLARATION_ACCEPTED` / `FORM_SIGNED` audit entries.
3. At fax time, the hashes are re-verified: if any document changed since signing, the send is refused until re-signed. This proves the declaration was accepted over exactly the pages the IRS received.

`--unsigned` on `tax-5472-fax` bypasses the gate for packages that were printed and signed by hand. Whether an e-signature is acceptable for your situation is a question for your tax professional.

## 💻 CLI Usage

```bash
# Generate the filing first
pyledger tax-5472-generate --entity-id 1 --tax-year 2025

# Accept the declaration and e-sign the pro-forma 1120
pyledger tax-5472-sign --entity-id 1 --tax-year 2025 --name "Jane Kwok" --title "Owner"

# Fax it to the IRS (855-887-7737 by default) and wait for confirmation
pyledger tax-5472-fax --entity-id 1 --tax-year 2025 --wait

# Queue without waiting, then check later
pyledger tax-5472-fax --entity-id 1 --tax-year 2025
pyledger tax-fax-status --transmission-id 1

# Dry-run against your own fax machine before the real submission
pyledger tax-5472-fax --entity-id 1 --tax-year 2025 --to 555-123-4567
```

Options for `tax-5472-fax`:

| Option | Description |
|---|---|
| `--entity-id`, `--tax-year` | Which generated filing to send |
| `--to` | Override the destination number (default: IRS 855-887-7737) |
| `--wait` | Poll until the fax reaches a terminal status |
| `--timeout` | Max seconds to wait with `--wait` (default 600) |

## 🐍 Python API

```python
import sqlite3
from pyledger.db import init_db
from pyledger.tax_filing import Form5472Filing
from pyledger.fax_service import FilingFaxService, NotifyreProvider

conn = sqlite3.connect("pyledger.db")
init_db(conn)
filing = Form5472Filing(conn)

service = FilingFaxService(filing, NotifyreProvider())
record = service.send_filing(entity_id=1, tax_year=2025)   # queues with Notifyre
record = service.wait_for_completion(record["id"])          # poll to terminal status

if record["status"] == "completed":
    print("Delivered:", record["num_pages"], "pages")
    print("Receipt:", record["confirmation"])               # proof of transmission
else:
    print("Failed:", record["failed_message"])
```

Key classes:

- **`NotifyreProvider`** — Notifyre REST adapter. Auth via the `x-api-token` header; the key comes from the constructor, `NOTIFY_API_KEY`, or `.env`. Sending follows Notifyre's three-step flow: upload the PDF base64 to `/fax/send/conversion`, poll the conversion until ready, then POST `/fax/send`. `high_quality` defaults to `True` because IRS form text is small.
- **`FilingFaxService`** — orchestrates a transmission for an entity + tax year: validates the generated filing exists, merges the package (`fax_package_{entity}_{year}.pdf`), sends, persists status, and updates filing state on confirmation.
- **`FaxProvider`** — the adapter interface (`send(to_number, file_path, reference)` and `get_status(fax_id)`). Implement it to swap vendors without touching the service, schema, or CLI.

## 📊 Transmission Statuses

Notifyre statuses are normalized to provider-neutral values:

| Notifyre | PyLedger | Terminal? | Effect |
|---|---|---|---|
| `accepted`, `queued` | `queued` | no | — |
| `in_progress` | `in_progress` | no | — |
| `successful` | `completed` | yes | Filing marked filed; receipt stored |
| `failed` | `failure` | yes | `failed_message` recorded; filing unchanged |

## 🗄️ Database Schema

```sql
CREATE TABLE fax_transmissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES filing_entities(id),
    tax_year INTEGER NOT NULL,
    provider TEXT NOT NULL,           -- 'notifyre'
    provider_fax_id TEXT,             -- Notifyre fax id
    to_number TEXT NOT NULL,          -- E.164, e.g. +18558877737
    files TEXT NOT NULL,              -- JSON list of source PDFs
    package_path TEXT,                -- merged PDF actually transmitted
    status TEXT NOT NULL DEFAULT 'queued',
    num_pages INTEGER,
    failed_message TEXT,
    completed_at TEXT,
    confirmation TEXT,                -- provider receipt JSON (proof of transmission)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Retain `confirmation` and the merged `package_path` permanently — together with the `tax_audit_trail` entries they are your evidence that the filing was transmitted on time.

## 🔧 Troubleshooting

- **"Notifyre API key missing"** — set `NOTIFY_API_KEY` in the environment or `.env` in the directory you run PyLedger from.
- **"No generated filing"** — run `pyledger tax-5472-generate` first; the fax service only sends packages recorded in `form_filings`.
- **"Filing PDFs missing on disk"** — the PDFs were moved or deleted since generation; regenerate the filing.
- **Status `failure`** — check `failed_message` (busy line, invalid number, unanswered). Re-run `tax-5472-fax`; each attempt is a new transmission row. Persistent failures: fall back to mailing the package (IRS Ogden, UT — see the README) and record it with `mark_filed(..., method="mail")`.
- **"Fax ... not found in Notifyre sent faxes"** — status lookup searches the last 90 days of sent faxes; older transmissions must be checked in the Notifyre dashboard.

## 🧪 Testing

`pyledger/test_fax_service.py` covers the service and the Notifyre adapter with no network access (fake provider + stubbed HTTP session):

```bash
python -m pytest pyledger/test_fax_service.py
```

To verify your live setup end-to-end without contacting the IRS, send to a fax number you control with `--to`.

> **Disclaimer**: PyLedger assists with form preparation and transmission and is not tax advice. Review all generated filings with a qualified tax professional before submitting.
