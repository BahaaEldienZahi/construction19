# Changelog

Each entry lists what changed and the evidence (commands + results). Older status reports
(PHASE_1_*, DEPLOYMENT_READY, ERROR_FIX_COMPLETE, …) were removed in step 1: they claimed
"complete / 100% pass" for a module that had no tests and several crashing paths
(see `BASELINE.md`).

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
