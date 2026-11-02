# DECISIONS

Re-read at the start of every step. "Client" decisions come from the project owner;
"Agent" decisions were made during implementation and are open to review.

## 1. Working rules (from project owner)

| # | Decision | Date |
|---|---|---|
| R1 | Stop after each step and report: summary, files changed, commands run with output, test results, every decision taken alone. Wait for "go". | 2026-11-02 |
| R2 | Commit only in the separate repo (`custom_addons/`). Never touch the Odoo core repo's staging area. | 2026-11-02 |
| R3 | Replace the status `.md` files with one README + CHANGELOG. | 2026-11-02 |
| R4 | Never claim "done / production ready" without having run it; cite commands + output. | 2026-11-02 |
| R5 | Ask before any destructive migration. | 2026-11-02 |
| R6 | Test databases: only names prefixed `agent_`, only `--http-port 8079`. Drop own `agent_` DBs at the end of each step. | 2026-11-02 |
| R7 | Never touch the owner's Odoo server (PID 2575728, `odoo-bin -c odoo.conf --dev xml`) or its DBs. Old `nt_*` / `ph_*` DBs are dropped later, once the owner stops that server. | 2026-11-02 |
| R8 | Lint tools (`ruff`, `pylint-odoo`) may be installed into `odoo_19/.venv`. | 2026-11-02 |

## 2. Scope & sequencing (from project owner)

| # | Decision | Date |
|---|---|---|
| S1 | **Pharmacy (step 5) on hold** until Enterprise vs Community is confirmed. Still unknown as of 2026-11-02. `pharmacy_retail` stays unmodified. | 2026-11-02 |
| S2 | After step 3, deliver the demo-able **golden cycle** (tender → project → measurement → certificate → invoice + Arabic PDF + minimal demo data) **before** the rest of step 4. | 2026-11-02 |
| S3 | Scope additions accepted for planning: unit rate analysis, stock integration, labor/equipment cost from daily reports, price escalation (فروق أسعار). | 2026-11-02 |
| S4 | **UX & dashboards: design now, build later.** `UX_SPEC.md` must be reviewed by the owner before any UX code. Native Odoo 19 views/widgets first; OWL only for the Overview page; minimal SCSS with Odoo/Bootstrap variables, no core style overrides; must work in Arabic RTL and at tablet width. Schedule: menu + form standard after step 3, **before** the golden-cycle demo; project dashboard, Overview and My Approvals in step 4. | 2026-11-02 |

| S5 | **UX_SPEC answers** (2026-11-02): Q1 divergence threshold = 10 percentage points as a **company setting**, not hardcoded. Q2 show three labelled figures everywhere — **Certified** (approved certificates), **Invoiced** (posted invoices), **Collected** (payments) — with the same definitions on every screen (UX_SPEC §3.0). Q3 no bulk approval. Q4 cash-flow forecast excludes uncertified work; "Executed not yet certified" shown as a separate line. Q5 Overview for Mgmt/Finance/PMs approved. Q6 online only for now, client confirmation pending (OPEN). Q7 no drag-and-drop on tenders. | 2026-11-02 |
| S6 | **Step 2 requirement:** record rules restrict project managers to **their own projects** (and the documents of those projects). | 2026-11-02 |

## 3. Data & migration (from project owner)

| # | Decision | Date |
|---|---|---|
| D1 | No real database has `nt_construction` with data. `construction19` is not a client DB. Uniqueness constraints are enforced **without** a migration script. | 2026-11-02 |

## 4. Provisional business defaults — OPEN, pending client confirmation

Must stay configurable (no hardcoded coefficients or tax logic). Tracked in `GAP_LIST.md` §A.

| # | Item | Provisional default | Confirms |
|---|---|---|---|
| P1 | Price escalation basis | Law 182/2018 public-procurement formula for government clients; same engine with contract coefficients for private/FIDIC | Client legal |
| P2 | VAT on escalation | Escalation is in the VAT base | Client tax advisor |
| P3 | Labor cost source | Flat hourly rate per trade | Client |
| P4 | Site storage | One warehouse per project | Client |

## 5. Agent decisions (step 1) — open to review

| # | Decision | Why |
|---|---|---|
| A1 | Separate repo initialised **in** `custom_addons/`, branch `main`, local only (no remote); author = global git user | Owner preferred a separate repo; this needs no addons-path change |
| A2 | Baseline commit excludes `nt_construction.zip` and `__pycache__/` (`.gitignore`) | Zip is a stale snapshot, recoverable via `git -C .. show :custom_addons/nt_construction.zip` |
| A3 | Source strings are English inside `_()`; Arabic only via `i18n/ar.po`. Messages previously hardcoded in Arabic show in English until `ar.po` exists | Odoo convention; required for translation |
| A4 | Project "Total Subcontracted" = sum of approved agreements' **line totals** (`total_value`), not the manual header `contract_value` | Consistent with BOQ committed amount |
| A5 | Subcontracts smart button restricted to `project.group_project_manager` until step 2 roles | Plain users have no ACL on subcontracts → AccessError |
| A6 | BOQ hierarchy loop: Odoo's parent-store `UserError("Recursion Detected")` fires first; our `_has_cycle` constraint stays as fallback | Core behaviour |
| A7 | Deferred from step 1: executed-vs-certified double counting, accounting, multi-currency (→ step 3); record rules, approval bypass (→ step 2) | Each needs the redesign of its own step |
| A8 | Executed vs certified tracked separately: measurement (حصر) = executed, certificate = certified/billed (planned, step 3) | Removes double counting; gives over/under billing |
| A9 | Module tests run with `--test-tags /nt_construction` (not bare `--test-enable`) | Bare flag runs every core module's tests (hours) |
| A10 | Upgrade test = install the baseline commit (`858b91e`, v19.0.1.0.0) from a git worktree, then `-u` with current code | Self-contained; does not depend on old non-agent DBs |

## 6. Agent decisions (UX spec draft) — open to review

| # | Decision | Why |
|---|---|---|
| U1 | "My Approvals" is placed under the Overview menu (Overview › My Approvals), not as its own top-level entry | Keeps the owner's 9-menu business order |
| U2 | My Approvals = read-only SQL view (`UNION ALL`) over the approval documents + `mail.activity` on submit; no approve-from-list (confirmed by owner, S5 Q3) | One source for the list, the project card count and the Overview KPI; approver sees the lines first |
| U3 | Rejected / cancelled shown as a ribbon, not as statusbar steps | Statusbar shows the happy path only |
| U4 | Tender kanban: drag-and-drop disabled (confirmed by owner, S5 Q7) | State changes must run the button logic and chatter |
| U5 | Project card uses core `o_kanban_dashboard`, `progress_bar` and `dashboard_graph` widgets (all in Community `web`) | Native first, no custom JS for the card |
| U6 | ~~Divergence threshold provisional~~ → superseded by S5 Q1 (10 points, company setting) | — |
| U7 | Invoiced is compared like-for-like with Certified because step 3 books revenue at gross work value (retention → Retention Receivable, advance recovery → Customer Advances); Collected is shown as % of the invoices' receivable total, not of contract | Different bases would make the three figures look inconsistent |
| U8 | One shared Python helper computes Executed / Certified / Invoiced / Collected for card, Overview and pivots (+0.5 d on UX-6) | Guarantees "same definitions on every screen" (S5 Q2) |
