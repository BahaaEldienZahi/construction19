# National Technology — Odoo 19 custom addons

| Module | Purpose | Edition | Status |
|---|---|---|---|
| `nt_construction` | Tenders → BOQ → execution project → variation orders → payment certificates (مستخلصات) → handover | Community 19 (works on Enterprise) | Step 1 (stabilization) done; full cycle in progress, see `GAP_LIST.md` |

Status is only claimed with evidence: see `CHANGELOG.md` for what changed per step and the
commands/test results behind it, and `GAP_LIST.md` for what is not done.

## Requirements
- Odoo 19.0 (this repo is tested against the source in `../odoo`, `version_info = (19, 0, 0, FINAL)`).
- PostgreSQL, Python 3.12.
- `nt_construction` depends on: `project`, `purchase`, `account`, `analytic`.

## Run / test
Addons path must include this folder:
```bash
cd odoo_19
AP=$PWD/odoo/addons,$PWD/addons,$PWD/custom_addons

# fresh install + module tests
./odoo-bin -c odoo.conf --addons-path=$AP -d <new_db> -i nt_construction \
  --test-tags /nt_construction --stop-after-init --log-level=test

# upgrade an existing DB + module tests
./odoo-bin -c odoo.conf --addons-path=$AP -d <db> -u nt_construction \
  --test-tags /nt_construction --stop-after-init --log-level=test
```
`--test-tags /nt_construction` limits the run to this module's tests; a bare `--test-enable`
would also run every installed core module's tests.

## Repository layout
```
custom_addons/            ← its own git repo (separate from the Odoo core repo)
├── BASELINE.md           Phase 0 facts (as received)
├── CHANGELOG.md          per-step changes with evidence
├── DECISIONS.md          working rules + client/agent decisions (re-read every step)
├── GAP_LIST.md           open items, provisional decisions, blockers
├── UX_SPEC.md            menus, form standard, dashboards (draft for review)
└── nt_construction/      module (README.md in Arabic, AGENTS.md for developers)
```
