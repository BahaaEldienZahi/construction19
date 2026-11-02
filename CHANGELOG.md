# Changelog

Each entry lists what changed and the evidence (commands + results). Older status reports
(PHASE_1_*, DEPLOYMENT_READY, ERROR_FIX_COMPLETE, …) were removed in step 1: they claimed
"complete / 100% pass" for a module that had no tests and several crashing paths
(see `BASELINE.md`).

## nt_construction 19.0.1.3.1 — Arabic digits, deployment notes (2026-11-02)
- Language *Arabic (Egypt)* `ar_EG` (inactive data record): Arabic text, RTL, Western digits (DECISIONS S9, provisional).
- `tests/test_arabic_digits.py` (2 tests): server-side dates, datetimes and amounts in `ar_EG` use 0-9.
- `INSTALL_AND_DEPLOY.md` started: rtlcss (required), addons path, upgrade note, Arabic language, roles.
- Screenshots moved to `docs/screenshots/` (latest set only), Arabic re-captured with `ar_EG`.
```
-i nt_construction, new DB agent_q10 → 0 failed, 0 error(s) of 39 tests; 0 WARNING/ERROR lines
screenshot server (agent_uxa_shots, ar_EG, 34 captures) → 0 WARNING/ERROR lines
```

## nt_construction 19.0.1.3.0 — UX Phase A (2026-11-02)

Report with screenshots (EN/AR, desktop/tablet): `docs/UX_PHASE_A.md`.
- Menu in business order (Tenders, Projects, Execution, Contracts, Billing, Handover, Reporting), role-based;
  app "Construction" with icon; new actions for construction projects, tender/project BOQ, POs, open punch items.
- Form standard on Tender, Daily Report, Subcontract Agreement, Handover; tender kanban pipeline; search views
  restored; daily report calendar; `static/src/scss/construction.scss`.
- `tests/test_ux_form_standard.py` (3 tests): ≤ 1 btn-primary per state, every role loads menus and views,
  menu order.
```
ruff / pylint-odoo                                      → All checks passed! / 10.00/10
-i nt_construction, new DB agent_uxa_fresh              → 0 failed, 0 error(s) of 37 tests; 0 WARNING/ERROR lines
-i nt_construction --with-demo, agent_uxa_demo          → 0 failed, 0 error(s) of 37 tests; 0 WARNING/ERROR lines
baseline 858b91e → -u nt_construction, agent_uxa_upgrade → 0 failed, 0 error(s) of 37 tests; 0 WARNING/ERROR lines (19.0.1.3.0)
screenshot server (agent_uxa_shots, 34 captures)        → 1 ERROR line: core mail_presence "could not serialize access
                                                          due to concurrent update" (bus poll vs scripted logout; retried by Odoo)
```

## nt_construction 19.0.1.2.0 — Step 2: security & roles (2026-11-02)

### Lint cleanup (first commit of step 2)
- ruff (core `ruff.toml`): 37 findings → **0**. pylint-odoo (`custom_addons/.pylintrc`): 150 warnings → **0**, 10.00/10.
- `_()` → `self.env._()`; redundant `string=` removed (labels unchanged); manifest `description`/`installable` removed.
- Regression caught by the install run, not by lint: `ruff --fix` re-sorted `models/__init__.py` and broke
  registry loading (mixin imported after its users). Order restored, file excluded from import sorting (DECISIONS L2).
```
-i nt_construction, new DB agent_s2_lint                  → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
-i nt_construction --with-demo, new DB agent_s2_lint_demo → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
```

### Approval bypass closed + multi-company (second commit of step 2)
- New `construction.workflow.guard`: workflow fields writable only from the buttons (DECISIONS L5).
- Approval documents and their lines frozen after submit; approved ones cannot be reset or deleted (L6, L7).
- Reject requires an approver (DECISIONS §7 Q5, pending confirmation).
- Record rules file fixed and loaded: 15 multi-company rules; `_check_company_auto` / `check_company` (L8).
- `tests/test_step2_security.py`: 11 tests (direct write/create refused, forged client context refused,
  frozen approved documents, reset/approve/reject rights, other-company user sees nothing).
```
-i nt_construction, new DB agent_s2_sec → 0 failed, 0 error(s) of 21 tests; 0 WARNING/ERROR lines
mutation check: guard forced open → 10 failed, 5 error(s) of 21 tests (tests detect the bypass); file restored
```

### Roles, own-project rules (third part of step 2; owner: "defaults OK")
- 7 roles as groups (one privilege each, combinable) + "Construction Approval" privilege (L1 < L2):
  Tender Engineer, Site Engineer, Quantity Surveyor, Project Manager, Accountant, Approver L1, Approver L2 / Management.
  Client Viewer (8th, portal) deferred to the golden cycle (DECISIONS Q8).
- ACL matrix rewritten: 84 rows, no more access for every internal user (DECISIONS Q2, L15).
- Own-project rules for Site Engineer / QS / PM (project manager or Construction Team member), company-wide
  for Tender Engineer, Accountant, Approvers; 47 rules in total (L10). Construction projects: "invited users",
  team auto-followed; company required (L9).
- Role checks on every workflow action, matching button `groups`; segregation of duties L1 ≠ L2 (Q4);
  handover reset blocked after a retention release, measurement reset blocked once linked (Q6);
  prices/amounts hidden from Site Engineers at field level (Q7, L13).
- `tests/test_step2_roles.py`: 13 tests. Step 1/2 tests use a second approver for L2.

### Evidence (step 2 final)
```
ruff check --config ruff.toml custom_addons/nt_construction            → All checks passed!
pylint --rcfile=custom_addons/.pylintrc custom_addons/nt_construction  → 10.00/10
-i nt_construction, new DB agent_s2_fresh                  → 0 failed, 0 error(s) of 34 tests; 0 WARNING/ERROR lines
-i nt_construction --with-demo, new DB agent_s2_demo       → 0 failed, 0 error(s) of 34 tests; 0 WARNING/ERROR lines
baseline 858b91e installed in agent_s2_upgrade             → 11 WARNING lines (= BASELINE W1-W4, expected)
-u nt_construction on agent_s2_upgrade (→ 19.0.1.2.0)      → 0 failed, 0 error(s) of 34 tests; 0 WARNING/ERROR lines
   after upgrade: 47 nt_construction rules, 84 ACL rows, 8 groups; old base.group_user ACLs: 0
```

## nt_construction 19.0.1.1.0 — Step 1: stabilization (2026-11-02)

### Fixed
- `project.project.subcontract_agreement_count` / `total_subcontracted_committed` and
  `boq.line.committed_amount`: compute methods were commented out → `AttributeError`. Restored;
  committed = confirmed PO lines + approved subcontract lines.
- Variation order `state` override dropped `rejected` → `action_reject` raised `ValueError`.
  The model now uses the approval-mixin selection.
- `_sql_constraints` (ignored by Odoo 19) → `models.Constraint` on tender, daily report (×2),
  work measurement, handover, subcontract agreement. Uniqueness is now enforced in the DB.
- Missing `ir.sequence` for subcontract agreement (`SUB/`), site daily report (`SDR/`),
  work measurement (`WM/`), handover (`HO/`): every record used to be named "New".
- Deprecated `_check_recursion` → `_has_cycle`; unknown field param `unaccent` removed;
  duplicate field label "Currency" on project → "Contract Currency".

### Added
- `company_id` (related to project, stored) on payment certificates and variation orders.
- Subcontracts smart button on the project form (project managers only until step 2 roles).
- `tests/test_step1_stabilization.py`: 10 regression tests.

### Changed
- All user-facing error/chatter strings wrapped in `_()` with named parameters; source
  language English (Arabic comes via `i18n/ar.po`, later step). Command API instead of tuples.

### Evidence (re-run 2026-11-02 under DECISIONS R6: `agent_` DBs, `--http-port 8079`)
```
-i nt_construction, new DB agent_s1_fresh            → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
-i nt_construction --with-demo, new DB agent_s1_demo → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
baseline 858b91e (19.0.1.0.0) installed in agent_s1_upgrade → 11 WARNING lines (= BASELINE W1-W4, expected)
-u nt_construction on agent_s1_upgrade (→ 19.0.1.1.0) → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
   after upgrade: 6 unique constraints present in pg_constraint; 4 new sequences (SUB/, SDR/, WM/, HO/) present
```
Lint (not yet fixed, see GAP_LIST §B): ruff 37 findings (35 auto-fixable); pylint-odoo 150 style
warnings, 0 errors, 8.28/10.

### Repo
- `custom_addons/` is now its own git repository; removed the 11 status `.md` files,
  `nt_construction.zip` (stale snapshot) and `__pycache__/`; added README, CHANGELOG, GAP_LIST.
