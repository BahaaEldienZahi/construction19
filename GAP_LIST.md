# GAP LIST

Honest list of what is **not** done, provisional decisions awaiting confirmation, and blockers.
Estimates are working days for one developer. Updated: 2026-11-02 (after step 3).

## A. Provisional decisions — pending client confirmation (OPEN)

- A0 **Arabic number format**: Western digits via `ar_EG` (DECISIONS S9) — client to confirm. PDFs verified in step 3/golden cycle.

| # | Item | Provisional default | Who confirms | Implementation rule |
|---|---|---|---|---|
| A1 | **Price escalation basis (فروق أسعار)** | Public-procurement formula (Law 182/2018) for government clients; same engine with contract-specific coefficients for private / FIDIC contracts | Client legal / contracts | Fully configurable per project: indices, coefficients, fixed portion, base date, threshold. **No hardcoded coefficients or formula constants.** |
| A2 | **VAT on escalation** | Escalation amount is part of the VAT base | Client tax advisor | Tax taken from a configurable setting / product tax; **no hardcoded tax logic**. |
| A3 | Labor cost source for daily reports | Flat hourly rate per trade (alt: payroll actual cost, +3 d, needs `hr`) | Client | Configurable rate table |
| A4 | Site storage | One warehouse per project (alt: sub-location under central warehouse, −1 d) | Client | Option on project |
| A6 | Retention on escalation | Retention applies to escalation too (project option `retention_on_escalation`, default on) | Client contracts | Configurable per project |
| A7 | VAT on retention (P6) | Upfront on gross; release without VAT | Client accountant / tax advisor | Setting to add if "at release" is chosen |
| A8 | Withholding rate and booking (P7) | Configurable tax, booked on the invoice | Client accountant / tax advisor | Already a setting |
| A9 | ETA e-invoice: negative recovery line with negative VAT (P8) | Negative line | Client tax advisor | Verify with l10n_eg_edi before go-live |
| A10 | Escalation indices per period; advance-covered part (P9) | One index set per certificate; not excluded | Client legal | Configurable once confirmed |
| A5 | Executed vs certified quantities | Measurement (حصر) = executed; certificate = certified/billed; tracked separately | — (NT design, step 3) | — |

## B. Known defects still open (from BASELINE.md)

| Item | Planned step | Est. |
|---|---|---|
| Read-only Client Viewer (8th role, portal) — with the certificate PDF | Golden cycle (DECISIONS Q8) | in golden cycle |
| Per-role UI smoke: menus + standard views now load-tested for all 7 roles; remaining: click-through tour | Step 4 / UX-5 tour | 0.25 d |
| Subcontractor retention release and subcontractor advances (payable side) | Step 4 | 1 d |
| Budget vs committed vs actual with blocking when over budget | Step 4 | in step 4 |
| Client certificate PDF (Arabic, bilingual) | Golden cycle | in golden cycle |
| Work measurement has no action to generate a certificate | Step 4 / golden cycle | in step 4 |
| VO overwrites BOQ line in place (no history of previous qty/price) | Step 4 | in step 4 |
| Project analytic account not auto-created | Step 4 | in step 4 |
| No `i18n/ar.po`; strings that used to be hardcoded Arabic now show English until it exists | Step 6 (partial earlier for the demo PDF) | in step 6 |

### Step 3b (after the golden-cycle demo, DECISIONS S16) — each with an ACCOUNTING_EXAMPLES section + test

| # | Item | Est. |
|---|---|---|
| 3b.1 | Subcontractor advance + recovery, subcontractor retention release, subcontractor final certificate | 1.5 d |
| 3b.2 | VO and the advance: setting "advance / recovery base = original or revised contract value" (default original) | 0.5 d |
| 3b.3 | Customer payment registration; how "Collected" is computed (example + test) | 0.25 d |
| 3b.4 | Negative current quantity (total to date below previous) → credit note instead of a validation error | 1 d |
| 3b.5 | USD contract in an EGP company: certificate, payment at another rate, exchange difference entry | 0.5 d |
| 3b.6 | Demo data on the Egyptian chart (`l10n_eg`), accounts mapped in Construction Settings | 0.5 d |

## C. Not started (scope)

Steps 2–6 of the plan, plus scope additions (rate analysis, stock integration, labor/equipment
cost, price escalation), QWeb PDFs, dashboards, demo data, Arabic deliverables
(DEMO_SCRIPT_AR, UAT_CHECKLIST_AR, USER_GUIDE_AR, INSTALL_AND_DEPLOY).
Estimate: ~10–13 weeks total (see plan); step 1 consumed ~1 day of the 2–3 d budget.

**UX Phase A done** (19.0.1.3.0, `docs/UX_PHASE_A.md`). Remaining UX after step 3: Certificate, Variation Order, Project, Measurement forms (~1.5 d) and dashboards.

**UX & dashboards** (`UX_SPEC.md`, draft awaiting owner review, no code): menu restructure, form
standard, search views (all currently commented out), tender kanban — 5.5 d after step 3, before the
golden-cycle demo; project dashboard, My Approvals, Overview (OWL), RTL/tablet pass — 12 d in step 4.
Q1–Q7 answered by the owner (DECISIONS S5); **Q6 (offline on tablet) still open** pending client confirmation.

## D. Blockers / environment

| Item | Impact |
|---|---|
| **`rtlcss` not installed** on this machine; Odoo needs it (npm) to build the Arabic RTL CSS — without it the Arabic UI is not mirrored | In `INSTALL_AND_DEPLOY.md` §1 (S10); must be installed on every server |
| `odoo.conf` addons_path points to missing `construction19/` and omits `custom_addons/` | Tests use `--addons-path` explicitly. `odoo.conf` belongs to the core repo; not changed. |
