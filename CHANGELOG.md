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

### Evidence
```
-i nt_construction on new DB nt_s1_fresh2  → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
-u nt_construction on copy of Phase 0 DB (19.0.1.0.0 → 19.0.1.1.0) nt_s1_upgrade2
                                           → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
-i nt_construction --with-demo on new DB nt_s1_demo
                                           → 0 failed, 0 error(s) of 10 tests; 0 WARNING/ERROR lines
```

### Repo
- `custom_addons/` is now its own git repository; removed the 11 status `.md` files,
  `nt_construction.zip` (stale snapshot) and `__pycache__/`; added README, CHANGELOG, GAP_LIST.
