# GAP LIST

Honest list of what is **not** done, provisional decisions awaiting confirmation, and blockers.
Estimates are working days for one developer. Updated: 2026-11-02 (after step 1).

## A. Provisional decisions — pending client confirmation (OPEN)

| # | Item | Provisional default | Who confirms | Implementation rule |
|---|---|---|---|---|
| A1 | **Price escalation basis (فروق أسعار)** | Public-procurement formula (Law 182/2018) for government clients; same engine with contract-specific coefficients for private / FIDIC contracts | Client legal / contracts | Fully configurable per project: indices, coefficients, fixed portion, base date, threshold. **No hardcoded coefficients or formula constants.** |
| A2 | **VAT on escalation** | Escalation amount is part of the VAT base | Client tax advisor | Tax taken from a configurable setting / product tax; **no hardcoded tax logic**. |
| A3 | Labor cost source for daily reports | Flat hourly rate per trade (alt: payroll actual cost, +3 d, needs `hr`) | Client | Configurable rate table |
| A4 | Site storage | One warehouse per project (alt: sub-location under central warehouse, −1 d) | Client | Option on project |
| A5 | Executed vs certified quantities | Measurement (حصر) = executed; certificate = certified/billed; tracked separately | — (NT design, step 3) | — |

## B. Known defects still open (from BASELINE.md)

| Item | Planned step | Est. |
|---|---|---|
| Double counting: daily-report progress + certificate approval both create `boq.line.progress` (3 executed shows 6) | Step 3 (certificate rewrite, A5) | in step 3 |
| Certificate invoice books net only to revenue; retention not recognized; no VAT; no advance account | Step 3 | in step 3 |
| Retention release creates no journal entries | Step 3 | in step 3 |
| Multi-currency: `boq.line.currency_id` = company currency while certificates/VOs use project contract currency; committed amounts summed without conversion | Step 3 | in step 3 |
| Record rules file not loaded; references non-existent model `subcontract.payment.certificate` | Step 2 | in step 2 |
| Any internal user can `write({'state': 'approved'})` on certificates (approval bypass) | Step 2 | in step 2 |
| Role model (8 roles) missing; daily report / handover / subcontract / measurement manager-only | Step 2 | 3 d |
| Work measurement has no action to generate a certificate | Step 4 / golden cycle | in step 4 |
| VO overwrites BOQ line in place (no history of previous qty/price) | Step 4 | in step 4 |
| Project analytic account not auto-created | Step 4 | in step 4 |
| Lint not clean (2026-11-02, step 1 code): ruff 37 findings (35 auto-fixable: import order, EOF newline, coding header, `l` var name); pylint-odoo 150 style warnings, 0 errors (85 `prefer-env-translation`, 62 `attribute-string-redundant`, 3 manifest keys), score 8.28/10 | Proposed: first commit of step 2 | 0.5 d |
| No `i18n/ar.po`; strings that used to be hardcoded Arabic now show English until it exists | Step 6 (partial earlier for the demo PDF) | in step 6 |

## C. Not started (scope)

Steps 2–6 of the plan, plus scope additions (rate analysis, stock integration, labor/equipment
cost, price escalation), QWeb PDFs, dashboards, demo data, Arabic deliverables
(DEMO_SCRIPT_AR, UAT_CHECKLIST_AR, USER_GUIDE_AR, INSTALL_AND_DEPLOY).
Estimate: ~10–13 weeks total (see plan); step 1 consumed ~1 day of the 2–3 d budget.

## D. Blockers / environment

| Item | Impact |
|---|---|
| **Enterprise 19 source not available** (only Enterprise 18 on this machine); Enterprise vs Community for the client **still unknown** (2026-11-02) | `pharmacy_retail` cannot be installed or tested. Step 5 on hold (DECISIONS S1). |
| `odoo.conf` addons_path points to missing `construction19/` and omits `custom_addons/` | Tests use `--addons-path` explicitly. `odoo.conf` belongs to the core repo; not changed. |
