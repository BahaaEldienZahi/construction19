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
| R7 | Never touch the owner's Odoo server (PID 2575728, `odoo-bin -c odoo.conf --dev xml`; restarted 2026-11-02 12:51 as **PID 3412413**) or its DBs. Old agent-created `nt_*` / `ph_*` DBs are dropped only when no server holds a connection to them. 2026-11-02: 6 dropped; `nt_step1`, `nt_step1_up`, `nt_s1_upgrade2`, `ph_baseline_ce` kept (held by PID 3412413). Those 4 dropped later the same day once that server had stopped; no agent-created DB remains. `nt_intrnal_17`, `nt_intrnal17_new` are not agent DBs — never touched. | 2026-11-02 |
| R8 | Lint tools (`ruff`, `pylint-odoo`) may be installed into `odoo_19/.venv`. | 2026-11-02 |
| R9 | During a step, new questions are written to DECISIONS.md (§7) and work continues with the agent's default. Stop and wait **only** if the question is destructive or changes money or permissions logic. | 2026-11-02 |

## 2. Scope & sequencing (from project owner)

| # | Decision | Date |
|---|---|---|
| S1 | ~~Pharmacy (step 5) on hold~~ → **`pharmacy_retail` removed by the owner** (2026-11-02, "i delete the pharma"). Deletion committed in this repo; recoverable from history (`git show 858b91e:pharmacy_retail/...`). Phase 2 / step 5 out of scope unless re-requested. | 2026-11-02 |
| S2 | After step 3, deliver the demo-able **golden cycle** (tender → project → measurement → certificate → invoice + Arabic PDF + minimal demo data) **before** the rest of step 4. | 2026-11-02 |
| S3 | Scope additions accepted for planning: unit rate analysis, stock integration, labor/equipment cost from daily reports, price escalation (فروق أسعار). | 2026-11-02 |
| S4 | **UX & dashboards: design now, build later.** `UX_SPEC.md` must be reviewed by the owner before any UX code. Native Odoo 19 views/widgets first; OWL only for the Overview page; minimal SCSS with Odoo/Bootstrap variables, no core style overrides; must work in Arabic RTL and at tablet width. Schedule: menu + form standard after step 3, **before** the golden-cycle demo; project dashboard, Overview and My Approvals in step 4. | 2026-11-02 |

| S8 | **Reorder: UX Phase A before step 3** — menu restructure, base SCSS, form standard on Tender (form + kanban), Daily Report, Subcontract, Handover; screenshots EN + AR of every changed screen in the report. Certificate, Variation Order, Project, Measurement forms and all dashboards stay after step 3. | 2026-11-02 |
| S5 | **UX_SPEC answers** (2026-11-02): Q1 divergence threshold = 10 percentage points as a **company setting**, not hardcoded. Q2 show three labelled figures everywhere — **Certified** (approved certificates), **Invoiced** (posted invoices), **Collected** (payments) — with the same definitions on every screen (UX_SPEC §3.0). Q3 no bulk approval. Q4 cash-flow forecast excludes uncertified work; "Executed not yet certified" shown as a separate line. Q5 Overview for Mgmt/Finance/PMs approved. Q6 online only for now, client confirmation pending (OPEN). Q7 no drag-and-drop on tenders. | 2026-11-02 |
| S7 | **Certified vs Invoiced are always compared on the same basis: both excluding VAT, both including escalation (فروق أسعار).** A step 3 test must assert it (same project, same period → Certified = Invoiced once every approved certificate is invoiced). | 2026-11-02 |
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
| U7 | **Approved by owner 2026-11-02 (+ rule S7).** Invoiced is compared like-for-like with Certified because step 3 books revenue at gross work value (retention → Retention Receivable, advance recovery → Customer Advances); Collected is shown as % of the invoices' receivable total, not of contract | Different bases would make the three figures look inconsistent |
| U8 | **Approved by owner 2026-11-02.** One shared Python helper computes Executed / Certified / Invoiced / Collected for card, Overview and pivots (+0.5 d on UX-6) | Guarantees "same definitions on every screen" (S5 Q2) |

## 6b. Agent decisions (step 2) — open to review

| # | Decision | Why |
|---|---|---|
| L1 | Lint = `ruff check --config ruff.toml` (core Odoo config) + `pylint --rcfile=custom_addons/.pylintrc` (pylint-odoo, `odoolint` only, `manifest-required-authors=National Technology`) | OCA author check doesn't apply to a private module; rcfile makes the command reproducible |
| L2 | `models/__init__.py` keeps a hand-written import order (mixin first) with `# ruff: file-ignore[unsorted-imports]` | `ruff --fix` sorted it alphabetically and the registry failed to load (`inherits from non-existing model 'construction.approval.mixin'`) |
| L3 | Manifest `description` removed; Apps falls back to `README.md` (Odoo `module.py` README lookup). `installable: True` removed (default) | pylint-odoo C8103/C8116 |
| L4 | `_()` → `self.env._()` everywhere (85 calls); redundant `string=` equal to the auto label removed (62 fields), so labels are unchanged | pylint-odoo prefer-env-translation / attribute-string-redundant |
| L5 | **Workflow guard** (`construction.workflow.guard`): `state`, approver stamps, `move_id` (certificate), `applied` (VO), `project_id`/`date_won` (tender), retention-release fields (handover), `payment_certificate_id` (measurement) can only change through the action methods. Unlock marker is a Python object in the context, so a JSON-RPC client cannot forge it (tested) | Closes BASELINE §4 bypass `write({'state': 'approved'})` |
| L6 | **Approval documents frozen once submitted** (certificate, VO, subcontract + their lines): no write/create/unlink of content until rejected → reset to draft. Approved documents cannot be deleted | Approving then editing amounts is the same bypass |
| L7 | Reset to draft on approval documents only from `rejected`/`cancelled` (the form button already showed it only on `rejected`); approved documents are never reset — corrections go through a new document (VO / credit note) | Server now enforces what the UI intended |
| L8 | `_check_company_auto = True` + `check_company=True` on cross-company links; global multi-company `ir.rule` on all 15 construction models (lines via their parent); old rules file rewritten (dropped non-existent `subcontract.payment.certificate`) and added to the manifest | Multi-company safety (brief) |
| L9 | A construction project must have a company (constraint). Odoo 19 projects may be company-less; such a project's documents had no company and vanished behind the company rules | Found by the role tests |
| L10 | Construction projects default to privacy "Invited internal users"; the project manager (`user_id`) and the Construction Team (`construction_member_ids`) are auto-subscribed as followers. Core `project_public_members_rule` is OR-ed with ours, so with "All internal users" every PM/SE would see every project | Implements S6/Q3 with core mechanisms, no core rule override |
| L11 | Side effects that need more rights than the actor's role run `sudo()` **after** the role check, uid unchanged: final-approval effects (VO → BOQ/contract value, certificate → progress) and tender → project conversion | Approvers / tender engineers must not get write access to BOQ or projects |
| L12 | `project.group_project_manager` (Project › Administrator) acts as Construction Admin: full ACL, passes role checks. It does **not** bypass approval groups or segregation of duties | Keeps step 1 admin flows; admin is not an approver by default except `base.user_admin` (existing data) |
| L13 | Prices/amounts hidden from Site Engineers with field-level `groups` (technical group "See Prices and Amounts" implied by every other role); Odoo removes these fields from the views | Q7; enforced on RPC too, not only in the UI |
| L14 | Approvers have write ACL on certificates / VOs / subcontracts (needed for the state change); they can therefore edit **draft** documents. Submitted+ documents are frozen (L6) | Alternative (approval via sudo) hides who changed what |
| L15 | Upgrade removes the old `base.group_user` ACLs: after upgrading a DB, internal users without a construction role lose access until a role is assigned | Expected with D1 (no real data); to note in INSTALL_AND_DEPLOY |

## 6c. Agent decisions (UX Phase A) — open to review

| # | Decision | Why |
|---|---|---|
| UX-A1 | Menu: Overview, My Approvals, Configuration and Subcontractor Certificates are **not** created yet (no content until step 3/4); Reporting visible only to roles that see amounts | No empty menus |
| UX-A2 | Menu xml-ids of existing entries kept (`menu_tender_root`, …) and re-parented; app renamed "Construction"; all menus in `views/construction_menus.xml` | No orphaned menus on upgrade |
| UX-A3 | Tender kanban progress bar = activities + column total (Odoo pipeline standard) instead of the deadline progress bar of UX_SPEC §2.3: Odoo progress bars need a stored, groupable field and "days to deadline" changes daily. Deadline shown as badge + accent on each card | Native widget, no stored daily-changing field |
| UX-A4 | Deadline status only for **draft** tenders (the submission deadline no longer matters once submitted) | Avoid red "deadline passed" on every submitted tender |
| UX-A5 | Lost / Cancelled kanban columns hidden by the default "Open" filter (shown when the filter is removed) | UX_SPEC "folded" columns; Odoo 19 cannot fold selection groups natively |
| UX-A6 | Kanban card accent via CSS `:has()` from an inner marker class | Odoo 19 kanban cards accept only a static class |
| UX-A7 | Handover state label "Provisional Handover (DLP Started)" → "Provisional (DLP)" | Long label collapsed the statusbar in Arabic |
| UX-A8 | Construction projects action uses the core project views until the dashboard (after step 3) | Scope S8 |
| UX-A9 | Screenshots via headless Chrome over `--remote-debugging-pipe` with the Python stdlib; `rtlcss@4.3.0` installed with npm **in the scratchpad only** for the capture (not system, not `.venv`) | R8 only covers lint tools in `.venv` |
| UX-A10 | Screenshots committed under `docs/screenshots/ux_phase_a/` (34 PNG, 2.5 MB) | Reviewable with the report |

## 7. Questions raised during steps (R9) — agent default applied unless marked STOP

| # | Step | Question | Default applied | Status |
|---|---|---|---|---|
| Q1 | 2 | 11 untracked folders appeared in `custom_addons/` on 2026-11-02 ~12:24 (`accounting_addons/`, `create_bill_from_po/`, `hr-community/`, `hr_payroll_community/`, `muk_web_*` ×7). Track them in this repo? | Left untouched: not committed, not ignored, not installed. Commits name files explicitly | open |
| Q2 | 2 | Role matrix for the 8 roles (UX/step 2 report §"Role matrix") | Proposal only; not wired | resolved: owner \"defaults OK\" 2026-11-02 |
| Q3 | 2 | Definition of "own project" for PM (S6) and Site Engineer | PM = `project.user_id`; Site Engineer / QS = new `construction_member_ids` on project | resolved: owner \"defaults OK\" 2026-11-02 |
| Q4 | 2 | Can the same user give L1 and L2 approval on one document? | Forbidden (segregation of duties) — not yet implemented | resolved: owner \"defaults OK\" 2026-11-02 |
| Q5 | 2 | Reject restricted to approvers (L1+). Previously any user could reject (button had no group) | Applied (reversible, no data) | resolved: owner \"defaults OK\" 2026-11-02 |
| Q6 | 2 | Handover reset to draft after a retention release, and measurement reset after it is linked to a certificate: allowed today (button visible in every non-draft state) | Unchanged for now; proposal: block once a release is recorded / once linked | resolved: owner \"defaults OK\" 2026-11-02 |
| Q7 | 2 | Site Engineer sees prices and amounts? | Hidden (quantities only) | resolved: owner \"defaults OK\" 2026-11-02 |
| Q8 | 2 | Read-only Client Viewer (portal) now or with the certificate PDF (golden cycle)? | With the golden cycle | resolved: owner "defaults OK" 2026-11-02 |

| Q9 | 2 | ~~`pharmacy_retail/` disappeared from disk ~12:25 on 2026-11-02 and its 116 files are **staged as deleted** in this repo's index — not done by the agent. Intended? | Not restored, not unstaged, not committed (agent commits use `git commit --only <paths>`). Recoverable from HEAD~~ | resolved: owner deleted it on purpose (S1) |
| Q10 | A | Deployment: production servers need `rtlcss` (npm) for Arabic RTL; also confirm Arabic number format (core `ar_001` shows Arabic-Indic digits in dates) | Listed in GAP_LIST §D; INSTALL_AND_DEPLOY | open |
