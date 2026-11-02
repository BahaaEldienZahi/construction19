# UX Phase A — report (nt_construction 19.0.1.3.0, 2026-11-02)

Scope (owner, DECISIONS S8): menu restructure, base SCSS, form standard on Tender (form + kanban),
Daily Report, Subcontract Agreement, Handover; screenshots EN + AR. Certificate, Variation Order,
Project and Measurement forms and all dashboards follow after step 3.

## Screenshots
Captured from a seeded `agent_uxa_shots` DB (headless Chrome, 1440×900 desktop and 768×1024 tablet),
admin user, English then Arabic (*Arabic (Egypt)* `ar_EG`, RTL, Western digits — DECISIONS S9).

| Screen | | | | |
|---|---|---|---|---|
| Menu (Contracts open) | [EN desktop](screenshots/01_menu_en_desktop.png) | [EN tablet](screenshots/01_menu_en_tablet.png) | [AR desktop](screenshots/01_menu_ar_desktop.png) | [AR tablet](screenshots/01_menu_ar_tablet.png) |
| Tender pipeline (kanban) | [EN desktop](screenshots/02_tender_kanban_en_desktop.png) | [EN tablet](screenshots/02_tender_kanban_en_tablet.png) | [AR desktop](screenshots/02_tender_kanban_ar_desktop.png) | [AR tablet](screenshots/02_tender_kanban_ar_tablet.png) |
| Tender list | [EN desktop](screenshots/03_tender_list_en_desktop.png) | [EN tablet](screenshots/03_tender_list_en_tablet.png) | [AR desktop](screenshots/03_tender_list_ar_desktop.png) | [AR tablet](screenshots/03_tender_list_ar_tablet.png) |
| Tender form (Under Evaluation) | [EN desktop](screenshots/04_tender_form_en_desktop.png) | [EN tablet](screenshots/04_tender_form_en_tablet.png) | [AR desktop](screenshots/04_tender_form_ar_desktop.png) | [AR tablet](screenshots/04_tender_form_ar_tablet.png) |
| Daily report list | [EN desktop](screenshots/05_daily_report_list_en_desktop.png) | [EN tablet](screenshots/05_daily_report_list_en_tablet.png) | [AR desktop](screenshots/05_daily_report_list_ar_desktop.png) | [AR tablet](screenshots/05_daily_report_list_ar_tablet.png) |
| Daily report form | [EN desktop](screenshots/06_daily_report_form_en_desktop.png) | [EN tablet](screenshots/06_daily_report_form_en_tablet.png) | [AR desktop](screenshots/06_daily_report_form_ar_desktop.png) | [AR tablet](screenshots/06_daily_report_form_ar_tablet.png) |
| Subcontract form (Submitted) | [EN desktop](screenshots/07_subcontract_form_en_desktop.png) | [EN tablet](screenshots/07_subcontract_form_en_tablet.png) | [AR desktop](screenshots/07_subcontract_form_ar_desktop.png) | [AR tablet](screenshots/07_subcontract_form_ar_tablet.png) |
| Handover form (Provisional) | [EN desktop](screenshots/08_handover_form_en_desktop.png) | [EN tablet](screenshots/08_handover_form_en_tablet.png) | [AR desktop](screenshots/08_handover_form_ar_desktop.png) | [AR tablet](screenshots/08_handover_form_ar_tablet.png) |
| Daily report as **Site Engineer** (no amounts, no Confirm) | [EN tablet](screenshots/09_daily_report_form_site_engineer_en_tablet.png) | [AR tablet](screenshots/09_daily_report_form_site_engineer_ar_tablet.png) | | |

Known in these screenshots:
- Our own labels (menus, states, field names) stay **English inside the Arabic UI** until
  `i18n/ar.po` exists (DECISIONS A3, step 6). Core Odoo strings are already Arabic. Layout,
  alignment and mirroring are what this pass verifies.
- Arabic RTL requires **`rtlcss` on the server** (Odoo builds the RTL CSS with it). Without it the
  Arabic UI is not mirrored. Installed locally for the capture only; server requirement in `INSTALL_AND_DEPLOY.md`.

## What changed
- **Menu** (business order, role-based): Construction › Tenders · Projects · Execution · Contracts ·
  Billing · Handover · Reporting. New actions: Construction Projects, Tender BOQ, Project BOQ,
  Purchase Orders (construction projects), Open Punch Items. App icon added.
- **Form standard** on the 4 documents: one `btn-primary` per state (tested), secondary buttons with
  confirmation where destructive, ribbons for lost / rejected / cancelled, smart buttons, who/where
  left · when/value right, company under Other Info, read-only after the editable state.
- **Tender pipeline**: kanban by state, no drag and drop, column totals, deadline badge + leading-edge
  accent for draft tenders, activity progress bar.
- **Search views** restored for tender, daily report, subcontract, handover, punch items, BOQ.
- Daily report: quantities tab first, calendar view, Measurements smart button.
- `static/src/scss/construction.scss` (39 lines, Bootstrap/Odoo variables, scoped classes, logical
  properties).
