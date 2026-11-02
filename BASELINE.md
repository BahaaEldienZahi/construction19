# BASELINE — Phase 0 (facts only)

Date: 2026-11-02 · Odoo source: `odoo_19/` (`odoo/release.py` → `version_info = (19, 0, 0, FINAL, 0, '')`), Python 3.12.16 (`.venv`), PostgreSQL local.
No code was changed to produce this report. Full logs are in the session scratchpad:
`/tmp/claude-1000/-home-bahaaabdelmaged-Desktop-National-Odoo-odoo-19-custom-addons/9d0aaa77-eaf7-4812-8f79-512c858e6b25/scratchpad/`
(`nt_install_nodemo.log`, `nt_install_demo.log`, `nt_upgrade.log`, `smoke_admin_output.txt`, `ph_install_ce.log`).

## 0. Environment facts

| Item | Fact | Evidence |
|---|---|---|
| Odoo 19 Community | present, 630 addons in `addons/` | `ls addons \| wc -l` |
| Odoo 19 **Enterprise** | **NOT present on this machine** | `find` for `web_studio`/`knowledge` → only `odoo18/enterprise18/enterprise/…` (Enterprise **18**) |
| `odoo.conf` addons_path | points to `construction19/` which no longer exists (warning on every start) and does **not** include `custom_addons/` | `odoo.conf`, log line `option addons_path, no such directory …/construction19` |
| Git | `custom_addons/` lives **inside the Odoo core repo** (branch `bahaa`). The index already holds unrelated staged changes (`I-Power` added, `construction19/` deleted, …) | `git status --short` |
| Lint tools | `ruff` and `pylint`/`pylint-odoo` not installed | `ruff: command not found`, `No module named pylint` |

## 1. nt_construction — install / upgrade

Commands (addons path = `odoo/addons,addons,custom_addons`):
```
odoo-bin -d nt_baseline_nodemo            -i nt_construction --test-tags /nt_construction --stop-after-init --log-level=test
odoo-bin -d nt_baseline_demo --with-demo  -i nt_construction --test-tags /nt_construction --stop-after-init --log-level=test
odoo-bin -d nt_baseline_demo              -u nt_construction --stop-after-init
```
Result: **installs and upgrades without ERROR**, but with these WARNINGs (both DBs, repeated on upgrade — 13 WARNING lines):

| # | Warning | Root cause |
|---|---|---|
| W1 | `Model attribute '_sql_constraints' is no longer supported` ×5 | `tender_tender.py:117`, `work_measurement.py:46`, `project_handover.py:84`, `subcontract_agreement.py:33`, `site_daily_report.py:54`. **Effect: none of these uniqueness constraints exist in the DB** (verified: a duplicate tender name `TND/2026/0002` was accepted). |
| W2 | `boq.variation.order.state … overrides existing selection` | VO redefines `state` without `rejected` (`boq_variation_order.py:26`) |
| W3 | `Field boq.line.parent_path: unknown parameter 'unaccent'` | `boq_line.py:43` |
| W4 | `Two fields (construction_currency_id, currency_id) of project.project have the same label` | `project_project.py:44` |
| W5 | `0 failed, 0 error(s) of 0 tests` | module has **no tests** |
| — | Runtime: `DeprecationWarning: Deprecated since 18.0, use _has_cycle()` | `boq_line.py:176` |

## 2. nt_construction — functional smoke test (real cycle, as `admin`, rolled back)

Script run through `odoo-bin shell -d nt_baseline_nodemo` (script: `smoke.py` / `smoke_admin.py`). Results:

| Step | Result |
|---|---|
| Tender → BOQ chapter+item → submit → won → create project | PASS (BOQ copied; as-bid BOQ kept on tender) |
| `project.subcontract_agreement_count` | **FAIL** `AttributeError: no attribute '_compute_subcontract_agreement_count'` (compute method commented out, `project_project.py:165`) |
| `project.total_subcontracted_committed` | **FAIL** same cause (`project_project.py:170`) |
| `boq.line.committed_amount` | compute method `_compute_committed_amount` is commented out (`boq_line.py:103-112`); field is used as a measure in `dashboard_views.xml:12,25` |
| Project analytic account auto-linked | **No** (`project.account_id` = False) |
| Daily report with 3 qty, then Certificate with the same 3 qty → L1 → L2 | executed cumulative = **6.0** for 3 actually executed → **double counting** (both daily report and certificate approval create `boq.line.progress`) |
| Certificate amounts (qty 3 × 100, retention 5%) | gross 300 / retention 15 / net 285 |
| Certificate → invoice → post | Journal: `400000 Cr 285`, `121000 Dr 285`. **Revenue understated by retention; retention not booked to any account; no VAT; no advance-recovery account.** |
| VO submit → reject | **FAIL** `ValueError: Wrong value for boq.variation.order.state: 'rejected'` |
| VO submit → L1 → L2 | PASS, contract_value 1000 → 1200; BOQ line overwritten in place (no history of previous qty/price) |
| Subcontract agreement submit → L1 → L2 | PASS (approval buttons **do exist** in `subcontract_agreement_views.xml:59-91` — known issue #3 is not accurate) |
| Work measurement confirm | PASS; **no method links it to a certificate** (only a readonly `payment_certificate_id`) |
| Handover provisional → stage-1 retention release | PASS, amount 7.5 recorded; **0 journal entries created** (informational only) |
| Duplicate tender reference | **accepted** (see W1) |

## 3. nt_construction — security

| Fact | Evidence |
|---|---|
| Only 2 groups: Approver L1, Approver L2 (no category, no role model); `base.user_admin` is auto-added to both | `security/construction_security.xml` |
| `security/construction_record_rules.xml` is **not in the manifest** → no record rules active | `__manifest__.py` `data` list |
| That file references `model_subcontract_payment_certificate`, a model that **does not exist** → adding it to the manifest as-is will break install | `grep -rn subcontract_payment_certificate` → only the rules file |
| `boq.payment.certificate` and `boq.variation.order` have **no `company_id`** | `grep -c company_id` → 0 |
| Plain internal user cannot read site daily reports / handovers / subcontracts / measurements (manager-only ACL) | smoke: `AccessError … site.daily.report` |
| Plain internal user **can write `state='approved'` directly** on a certificate, bypassing the approval workflow | smoke: `write({'state':'approved'})` → ALLOWED |

## 4. nt_construction — conventions / hygiene

- Views: 0 `<tree>`, 0 `attrs=`, 0 `states=` (good).
- 6+ user-facing `raise …Error('…')` strings not wrapped in `_()` (`boq_line.py`, `boq_line_progress.py`, `purchase_order.py`); no `i18n/` directory.
- No tests, no demo data, no QWeb reports, no settings for accounts.
- `__pycache__/` at module root and `models/`; `custom_addons/nt_construction.zip` (older snapshot, 13 .py files).
- 11 status reports in `custom_addons/*.md` claim e.g. "✅ COMPLETE", "Validation: 100% pass". **The module has 0 tests**, and the failures above contradict these reports.
- `AGENTS.md` names methods that do not exist (`create_execution_project`, `action_create_customer_invoice`).

## 5. pharmacy_retail

| Fact | Evidence |
|---|---|
| It **is** the Odoo **19.0 Enterprise** industry module | `i18n/pharmacy_retail.pot`: `Project-Id-Version: Odoo Server 19.0+e`; uses `is_storable` (18+ field) |
| Hard deps on Enterprise: `knowledge`, `web_studio` | `__manifest__.py` |
| **Cannot be installed here**: Community install → `module pharmacy_retail: some depends are not loaded (knowledge, web_studio), skipped` + `ERROR … inconsistent states` | `ph_install_ce.log` |
| Content is thin for a real pharmacy: 7 product templates, 19 demo lots, Studio fields mostly on partner/company (doctor, drug licence); on product only `x_manufacturer`. No generic name / active ingredient / strength / dosage form / Rx / controlled flags, no FEFO/expiry-blocking logic in POS | `data/ir_model_fields.xml`, `data/product_template.xml` |
| License OEEL-1 (Odoo S.A.) — modifying it in place is not ours to redistribute; extension should be a separate NT module | `__manifest__.py` |
