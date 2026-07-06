# Reportable Transaction Types

Valid `txn_type` values (enum `ReportableTransactionType` in `pyledger/tax_filing.py`) and where each lands on Form 5472 (Rev. Dec 2023). Part IV is the monetary grid on page 2; types with no Part IV line are described in a Part V attachment statement, which `generate_filing` renders automatically for DE entities.

## Part IV types (monetary lines)

Received block totals on line 22; paid block totals on line 36. `fill_form_5472` computes both totals from the per-line amounts.

| `txn_type` | Form 5472 line | Meaning |
|---|---|---|
| `sales_to_related` | 9 | Sales of stock in trade to the related party |
| `rents_royalties_received` | 13a | Rents received |
| `service_fees_received` | 15 | Consideration received for services |
| `loan_from_owner` | 17b | Amounts borrowed — ending balance |
| `interest_received` | 18 | Interest received |
| `purchases_from_related` | 23 | Purchases of stock in trade |
| `rents_royalties_paid` | 27a | Rents paid |
| `service_fees_paid` | 29 | Consideration paid for services |
| `loan_to_owner` | 31b | Amounts loaned — ending balance |
| `interest_paid` | 32 | Interest paid |

## Part V types (attachment statement, DE only)

These are the transactions a typical foreign-owned single-member LLC actually has:

- `capital_contribution` — owner funding the entity
- `distribution` — owner draws, dividends
- `expenses_paid_by_owner` — entity expenses paid personally by the owner
- `formation_dissolution_costs` — state filing fees, registered agent, incorporation/dissolution costs
- `other` — anything else with the owner/related party

## Classification heuristics (ledger scan)

`suggest_reportable_transactions(entity_id, tax_year)` walks every journal line for the year and suggests a type:

1. **Mapped accounts win.** If the line's account is in `tax_account_mappings` (via `map_account`), the mapping's type is suggested with `high` confidence, overriding keyword matches from other lines of the same entry.
2. **Otherwise keyword rules** (`_CLASSIFICATION_RULES`, first match wins) run against the entry description + account name. High-confidence phrases include "capital contribution", "owner draw", "loan from owner", "formation", "paid by owner"; a bare "owner"/"member" only yields a `low`-confidence `other`.
3. Entries already confirmed for that entity/year (linked via `journal_entry_id`) are skipped, so re-running the scan is safe.

Confirm a suggestion with `confirm_suggested_transaction(...)` — it copies the entry's date/description and records `source="ledger_confirmed"`. Manual additions via `add_reportable_transaction` record `source="manual"`.

When classifying on behalf of a user, auto-confirm only `high`-confidence suggestions from mapped accounts; show everything else to the user first — keyword matches can misfire (e.g. "distribution" in a product name).
