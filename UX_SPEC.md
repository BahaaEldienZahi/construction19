# UX_SPEC — nt_construction (menus, form standard, dashboards, approvals)

Status: **Reviewed by owner 2026-11-02 — Q1–Q7 answered (§10, DECISIONS.md S5). No code written yet.**
Schedule (owner): menu + form standard after step 3, before the golden-cycle demo; dashboards,
Overview and My Approvals in step 4. Estimates in §9, open questions in §10.

Wireframes are ASCII and drawn left-to-right; in Arabic the whole screen mirrors (§7).
`[Button]` = secondary button, `[[Button]]` = `btn-primary` (highlighted), `(◉ 3)` = smart button.

---

## 0. Principles and what exists today

**Principles**
1. Native Odoo 19 views and widgets first (`list`, `form`, `kanban`, `pivot`, `graph`, `progress_bar`,
   `dashboard_graph`, `statusbar`, `badge`, `<chatter/>`). OWL only for the Overview page (§4).
2. No overriding of core styles. One small SCSS file using Bootstrap/Odoo variables (§8).
3. Every number on a dashboard is defined once in Python, tested, and drillable: clicking it opens
   the list of records it was computed from.
4. A screen is only "done" when it is checked in Arabic RTL and at tablet width (§7).

**Audit of the current views (facts, from `views/*.xml`)**
| Finding | Effect |
|---|---|
| One flat menu "Tenders & Construction" with 9 entries in no business order | Users don't see the cycle |
| **All search views are commented out** (8 files) | No filters, group-by, "Waiting for me", or kanban grouping |
| Header buttons use 5 different emphasis classes (`btn-primary`, `oe_highlight`, `btn-success`, `btn-info`, none) for the same role. Two coloured buttons show at once in: tender `submitted` (Move to Evaluation + Mark as Won), handover `provisional` (Release Stage 1 + Final Handover), handover `final` (Release Stage 2 + Close) | The next step isn't obvious, and it looks different on each document |
| No tender kanban; no kanban on any document | No pipeline view |
| Smart buttons exist only on tender, project and certificate | Hard to navigate between linked documents |
| "Reporting" = 2 pivot/graph views on BOQ lines | No dashboard |

---

## 1. Menu restructure (business order)

App root: **Construction** (`menu_construction_root`, renamed from "Tenders & Construction").
Group visibility uses the step-2 roles. Role names below are provisional until step 2 fixes them.

```
Construction
├── Overview                         → OWL client action (§4)                [Mgmt, PM, Finance]
│   ├── Company Overview
│   └── My Approvals                 → §5                                     [Approver L1/L2]
├── Tenders
│   ├── Tenders                      → kanban by state (default), list, form  [Tender, Mgmt]
│   └── Tender BOQ (as-bid)          → list grouped by tender                 [Tender, QS]
├── Projects
│   ├── Construction Projects        → dashboard kanban (default, §3), list, form
│   └── Project BOQ                  → list grouped by project/chapter        [QS, PM]
├── Execution
│   ├── Daily Reports                → list, form, calendar                   [Site Eng, PM]
│   └── Measurements (حصر)            → list, form                             [Site Eng, QS, PM]
├── Contracts
│   ├── Subcontracts                 → list, form                             [PM, Procurement]
│   ├── Variation Orders             → list, form                             [PM, QS, Approvers]
│   └── Purchase Orders              → purchase.order filtered to construction projects
├── Billing
│   ├── Client Certificates          → list, form                             [QS, Finance, Approvers]
│   └── Subcontractor Certificates   → list, form (step 3 model)              [QS, Finance, Approvers]
├── Handover
│   ├── Handovers                    → list, form                             [PM]
│   └── Open Punch Items             → list of punch lines, status = open     [PM, Site Eng]
├── Reporting                                                                 [Mgmt, PM, Finance, QS]
│   ├── Budget vs Committed vs Actual   (pivot/graph, step 3 data)
│   ├── Executed / Certified / Invoiced / Collected  (pivot, per project and month)
│   ├── Retention                       (pivot: held / released / due by date)
│   ├── Tender Analysis                 (pivot/graph: win rate by client/type)
│   ├── Cost Analysis                   (existing, kept)
│   └── Billing Trend                   (existing, kept)
└── Configuration                                                             [Construction Admin]
    ├── Settings                     → res.config.settings section (accounts, approval, thresholds)
    ├── Escalation Indices           (step 3, P1)
    ├── Labour / Equipment Rates     (scope addition, P3)
    └── Sequences                    → filtered ir.sequence (admin only)
```

Rules:
- The root menu has no action of its own, so it opens the first menu the user can see.
  Management lands on Overview; a site engineer (no Overview access) lands on Execution › Daily Reports.
- Menu xml-ids are new. The old ones are deleted, which is safe because no real data exists (D1);
  menus aren't data, but deleting them is still listed for owner awareness.
- Purchase Orders reuses `purchase.purchase_rfq`'s views with a domain on construction projects.
  No new view.

---

## 2. Form standard (every document)

### 2.1 Layout contract
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [[Next step]]  [Secondary] [Secondary]          Draft › Submitted › ● Approved│  <header>
├──────────────────────────────────────────────────────────────────────────────┤
│                         (◉ Invoice) (◉ 3 Measurements) (◉ Project) (◉ Prev.)  │  oe_button_box
│  [ribbon: Rejected / Cancelled / Over budget]                                 │  web_ribbon
│  CERT/2026/0007                                                               │  oe_title h1
│  ┌ Who / where ──────────────────┐  ┌ When / value ─────────────────────────┐ │
│  │ Project      Tower A          │  │ Period        01/10 – 31/10/2026      │ │
│  │ Customer     Client X         │  │ Date          02/11/2026              │ │
│  │ Reference    Client ref #12   │  │ Currency      EGP                     │ │
│  └───────────────────────────────┘  └───────────────────────────────────────┘ │
│  ┌ Lines │ Deductions │ Accounting │ Other Info │ Notes ┐                      │  notebook
│  │ … editable list (≤ 6 visible columns, rest optional="hide") …              │ │
│  │                                        Subtotal / totals (oe_subtotal_footer)│
│  └───────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Chatter: Send message · Log note · Activities · tracked field changes        │  <chatter/>
└──────────────────────────────────────────────────────────────────────────────┘
```

| Element | Rule |
|---|---|
| Header buttons | For any state, **at most one** visible `btn-primary`: the next step in the cycle. Reject, Cancel and Reset are secondary. Destructive ones (Cancel, Reject) carry `confirm="..."`. Approval buttons also carry `groups=` for the approval level. |
| Statusbar | `widget="statusbar"` on the right with `statusbar_visible` = the happy path only. Rejected and cancelled are shown with a `web_ribbon` (red or grey), not as statusbar steps. |
| Smart buttons | In `oe_button_box`, one per related document type, with a count or a monetary value, and hidden (`invisible`) when zero. Order: upstream document first, then downstream (Tender ← Project → BOQ → Measurements → Certificates → Invoices). |
| Title | `name` as `h1` and read-only (it comes from the sequence). Draft shows "New". |
| Field groups | Left = **who/where** (project, partner, references); right = **when/value** (dates, currency, key amounts). `company_id` goes under "Other Info", with `groups="base.group_multi_company"`. |
| Notebook order | Lines → document-specific financial tab (Deductions / Accounting) → Other Info → Notes. |
| Lines | `editable="bottom"`, at most 6 visible columns on tablet (§7), totals in `oe_subtotal_footer`, monetary fields with `currency_field`, and sections via `display_type` where the BOQ needs chapters. |
| Read-only after approval | Fields are `readonly="state not in ('draft',)"` in the view **and** guarded in `write()` (step 2 closes the server-side bypass; the view alone isn't security). |
| Chatter | `<chatter/>` on every document; `state` and key amounts get `tracking=True`. |
| Search view | Restored for every model. Filters: My documents, Draft, **Waiting for me** (approval docs), This month; group by Project, State, Partner, Month. |

**Automated check (planned test):** a test reads each form view's header. For every value of `state`, it evaluates the `invisible` expressions and asserts that **at most one** `btn-primary` is visible. This guards the standard against future edits.

### 2.2 Next-step button per document and state
| Document | State → highlighted `[[button]]` | Smart buttons | Tabs |
|---|---|---|---|
| Tender | draft → **Submit**; submitted → **Move to Evaluation**; under_evaluation → **Mark as Won** (Lost is secondary); won without project → **Create Project**; lost/cancelled → none | Opportunity (needs `crm`, step 4), BOQ (count, value), Project | BOQ summary, Bonds & Deadlines, Description, Lost/Cancel reason |
| Daily Report | draft → **Confirm** | Project, Measurement | Manpower, Equipment, Quantities, Site Notes |
| Measurement | draft → **Confirm**; confirmed → **Create Certificate** (golden cycle) | Daily Reports (count), Certificate | Lines, Daily Reports, Notes |
| Variation Order | draft → **Submit**; submitted → **Approve (L1)** [L1]; approved_l1 → **Final Approve (L2)** [L2] | Project, BOQ lines affected | Lines, Justification, History (step 4) |
| Subcontract | same approval path as VO | POs, Subcontractor Certificates, Vendor Bills | Scope, BOQ Lines, Retention & Advance, Notes |
| Client Certificate | approval path, then approved without invoice → **Create Invoice** | Invoice, Measurement(s), Previous certificate | Lines (previous / current / total), Deductions (retention, advance recovery, WHT), Accounting, Notes |
| Subcontractor Cert. | approval path, then **Create Vendor Bill** | Vendor Bill, Subcontract | as client certificate |
| Handover | draft → **Confirm Provisional**; provisional → **Release Retention 1**; after DLP end → **Final Handover**; final → **Release Retention 2**; released → **Close** | Project, Punch items (open count), Journal entries | Provisional, Punch List, Final, Notes |

### 2.3 Tenders as a kanban pipeline
```
 Draft (3)          Submitted (5)       Evaluation (2)      Won (4)           ▸Lost ▸Cancelled
 ▓▓▓▓▓░░ 2.1M       ▓▓▓▓░░░ 8.4M        ▓▓░░░░ 3.0M         ▓▓▓▓▓▓ 12.7M      (folded)
┌──────────────┐   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│TND/2026/0012 │   │TND/2026/0009 │    │TND/2026/0005 │    │TND/2026/0003 │
│Ring Road Br. │   │School Phase 2│    │Hospital MEP  │    │Tower A       │
│Client X      │   │Ministry Y    │    │Client Z      │    │Client X      │
│EGP 1,250,000 │   │EGP 4,800,000 │    │EGP 3,000,000 │    │EGP 6,100,000 │
│⏰ 5 days left │   │⏰ 2 days ⚠    │    │Bond expires  │    │(◉ Project)   │
│         (MB) │   │         (AH) │    │ in 10 days ⚠ │    │         (MB) │
└──────────────┘   └──────────────┘    └──────────────┘    └──────────────┘
```
- `default_group_by="state"`, with Lost and Cancelled folded (`fold` via `group_expand`). The column header has a `progressbar` coloured by deadline: green >7 days, orange ≤7, red past.
- Each card shows: reference, name, client, value (`monetary`), days to the deadline, bid-bond expiry warning (step 4 field), and the responsible user's avatar (`many2one_avatar_user`). `activity_ids` uses the `kanban_activity` widget.
- Drag-and-drop between columns is **disabled** (`records_draggable="0"`), because state changes must go through the buttons (validation, chatter). Quick create is off; "New" opens the form.

---

## 3. Project dashboard (journal-dashboard style kanban)

### 3.0 Shared financial definitions (owner Q2: same labels and formulas on every screen)
Computed by **one** Python helper used by the project card, the Overview and the Reporting pivots,
so the same project and date always give the same numbers. All amounts exclude VAT unless stated.

| Label (EN / AR) | Definition |
|---|---|
| **Executed / المنفذ** | Σ confirmed measurement quantity × contract unit price, cumulative to the date |
| **Certified / المعتمد** | Σ cumulative gross work value of **approved** client certificates (before retention, advance recovery and WHT) |
| **Invoiced / المفوتر** | Σ untaxed amount of **posted** customer invoices created from client certificates, minus posted credit notes. Step 3 books revenue at gross work value, so Invoiced compares like-for-like with Certified; a step 3 test asserts this |
| **Collected / المحصل** | Σ payments reconciled to those invoices (cash received, incl. VAT, after retention / advance / WHT deductions). Shown as an amount and as % of the invoices' receivable total, not as % of contract, because the bases differ |
| **Executed not yet certified / منفذ غير معتمد** | max(0, Executed − Certified). Shown as its own line; never added to Certified, Invoiced or the cash-flow forecast (Q4) |

Default view of *Projects › Construction Projects* (domain `is_construction_project = True`).
It's a `kanban` view on `project.project` with `class="o_kanban_dashboard"` (the same class the
Invoicing journal dashboard uses), so it gets core styling without custom CSS.

```
┌─────────────────────────────────────────────┐ ┌─────────────────────────────────────────────┐
│▌Tower A                        PRJ-0003  ⋮ │ │▌Ring Road Bridge               PRJ-0007  ⋮ │
│▌Client X                                    │ │▌Ministry Y                                  │
│                                             │ │                                             │
│ Contract value         EGP 6,450,000        │ │ Contract value         EGP 9,800,000        │
│ Executed  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░  58 %        │ │ Executed  ▓▓▓▓▓▓░░░░░░░░░░░░░░  31 %        │
│ Certified ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  49 %        │ │ Certified ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░  55 %  ⚠     │
│ Invoiced  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  41 %        │ │ Invoiced  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░  55 %        │
│ Collected              EGP 2,210,000 (83 %) │ │ Collected              EGP 4,020,000 (71 %) │
│ Executed not certified EGP   580,000        │ │ Executed not certified EGP         0        │
│ Retention held         EGP   315,000        │ │ Retention held         EGP   539,000        │
│ Pending approvals      (2) →                │ │ Pending approvals      (0)                  │
│                                             │ │ ⚠ Certified ahead of executed by 24 pts     │
│  ▁▃▅▂▇▆   certified, last 6 months          │ │  ▂▂▇▅▃▁   certified, last 6 months          │
│                                             │ │                                             │
│ [+ Daily Report] [+ Measurement] [+ Cert.]  │ │ [+ Daily Report] [+ Measurement] [+ Cert.]  │
└─────────────────────────────────────────────┘ └─────────────────────────────────────────────┘
  ▌= left (in RTL: right) border colour: none = OK, orange = under-certified, red = over-certified
```

**Fields** (new, on `project.project`, all computed in batch, non-stored unless noted):
| Field | Definition | Widget |
|---|---|---|
| `contract_value` | exists, original + approved VOs | `monetary` |
| `executed_percent` | Σ (executed qty × unit price) of BOQ items ÷ current contract value. **Executed = confirmed measurements** (A8, step 3) | `progress_bar` |
| `certified_percent`, `invoiced_percent` | Certified ÷ contract value, Invoiced ÷ contract value (§3.0) | `progress_bar` |
| `collected_amount`, `collected_percent` | Collected (§3.0); % of the invoices' receivable total | `monetary` + text |
| `executed_not_certified_amount` | §3.0 | `monetary` |
| `certification_divergence` | selection `ok` / `under` / `over`. `over` if certified % − executed % > T; `under` if executed % − certified % > T. T = **company setting** `res.company.construction_divergence_threshold` (Settings, default 10 points; owner Q1 — not hardcoded) | border colour + warning line |
| `retention_held_amount` | exists; step 3 redefines it as the balance of the Retention Receivable account for this project's analytic account | `monetary` |
| `pending_approval_count` | count of rows in the approval view (§5) for this project, at any level | button → My Approvals filtered by project |
| `construction_dashboard_graph` | JSON in the same shape as `account.journal.kanban_dashboard_graph`: Certified amount per month for the last 6 months (§3.0) | `dashboard_graph` (`graph_type="bar"`), core field widget, Chart.js already bundled |

**Quick-create buttons:** `type="object"` methods return the action for a new record with `default_project_id`. Each button is shown only to the roles allowed to create that document (`groups=`).

**Card menu `⋮`:** Open project, BOQ, Subcontracts, Variation Orders, Certificates, Handover, Settings (managers).

**Performance:** each metric is one `_read_group` over all displayed projects. That makes the whole card set about 7 queries, not 7 × N. A test asserts the query count with 50 projects (`assertQueryCount`), alongside the brief's performance gate of 2,000 BOQ lines and 50 certificates.

---

## 4. "Construction Overview" — OWL client action

`ir.actions.client`, tag `nt_construction.overview`. Data comes from **one** RPC,
`construction.overview.get_data(date_from, date_to, project_ids)` (`AbstractModel`). It runs with the
user's allowed companies, so record rules and multi-company apply. All amounts are in the **current
company's currency**, converted with `_convert` at the document date.

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ Construction Overview      Period [This year ▾] 01/01/2026 – 31/12/2026   Projects [All ▾] │
├───────────────┬───────────────┬───────────────┬───────────────┬──────────────┬────────────┤
│ Contracts     │ Certified     │ Invoiced      │ Collected     │ Retention held│ Executed not │
│ EGP 48.2M     │ EGP 23.4M     │ EGP 21.7M     │ EGP 17.9M     │ EGP 1.9M      │ certified    │
│ 12 projects   │ 49 % of contr.│ 45 % of contr.│ 83 % of recv. │ 0.6M due ≤90d │ EGP 2.6M     │
├───────────────┴──────┬────────┴───────────────┴───────────────┴──────┬────────┴──────────────┤
│ Tender win rate 38 % (5 / 13 by count, 41 % by value)                │ Pending approvals 7 (3 for me) │
├──────────────────────┴──────────────────────────────┬───────────────┴──────────────────────┤
│ Certified / Invoiced / Collected per month          │ Cash-flow forecast, next 6 months    │
│  ▆ ▇ ▅ ▆ ▇ █ ...                                    │  in ▇▇▆▅▅▄  out ▅▅▅▄▄▃  net ─────     │
│                                                     │  separate line, not in totals:       │
│                                                     │  Executed not yet certified 2.6M     │
├─────────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Executed vs Certified by project (horizontal bars)  │ Tender pipeline by state (value)     │
│  Tower A      ▓▓▓▓▓▓▓▓▓▓▓▓ 58 / ░░░░░░░░░░ 49        │  Draft ▓▓ Submitted ▓▓▓▓ Eval ▓▓     │
│  Ring Road ⚠  ▓▓▓▓▓▓ 31 / ░░░░░░░░░░░ 55             │                                      │
├─────────────────────────────────────────────────────┴──────────────────────────────────────┤
│ Projects needing attention: over-certified · budget overrun · DLP ending ≤ 30 d · bond expiry │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

**KPI definitions** (each with a drill-down action to the underlying records):
| KPI | Formula | Depends on |
|---|---|---|
| Contracts | Σ current contract value of active construction projects (not closed). Count shown below | step 1 ✓ |
| Certified | §3.0, approval date in period | step 3 |
| Invoiced | §3.0, invoice date in period | step 3 |
| Collected | §3.0, payment date in period | step 3 |
| Executed not yet certified | §3.0, at period end | step 3 |
| Retention held | balance of the Retention Receivable account (Settings) at period end; "due ≤ 90 d" = stage releases whose planned date (handover DLP end) falls in the next 90 days | step 3 |
| Tender win rate | won ÷ (won + lost), by decision date in period; by count and by value | needs a `decision_date` field on tender (step 4) |
| Pending approvals | all open approval rows (§5); "for me" = at my level | §5 |
| Cash-flow forecast | **in**: open receivables by due date, plus retention releases by planned date. **out**: open payables (vendor bills and subcontractor certificates) by due date. Monthly buckets for the next 6 months. Executed-not-yet-certified work is **excluded** from in/out/net and shown as a separate labelled line under the chart (owner Q4) | step 3 |

**OWL build**
- Components: `ConstructionOverview` → `OverviewFilters`, `KpiCard` (×8), `OverviewChart` (×4), `AttentionList`.
- Charts use Chart.js through `loadBundle("web.chartjs_lib")`, the same as core `dashboard_graph`, so no new library. Colours come from `getColor()` in `@web/core/colors/colors`, which makes them dark-mode aware like core.
- Filters:
  - Period presets: this month, quarter, year, or custom (date pickers from `@web/core/datetime`).
  - Projects use `MultiRecordSelector` (`@web/core/record_selectors`).
  - The filter state is kept in the action's context, so the breadcrumb back preserves it.
- A KPI click calls `action.doAction()` with the domain returned by `get_data` (the server builds the domain, so the number and the list always match).
- Tests:
  - Python: unit tests of `get_data` on the golden-cycle data (exact numbers).
  - JS: a Hoot test that the component renders with mocked RPC.
  - Tour: open Overview, click the "Invoiced" KPI, land on the invoice list.

---

## 5. "My Approvals"

**Recommended: a read-only SQL view model** `construction.approval.request` (`_auto = False`,
`init()` creates a `UNION ALL` view) over every approval document:
`boq.payment.certificate`, `boq.variation.order`, `subcontract.agreement`, and the subcontractor
certificate (step 3).

Columns: `res_model`, `res_id`, `name`, `document_type`, `project_id`, `partner_id`, `company_id`,
`amount`, `currency_id`, `state`, `required_level` (`l1` if submitted, `l2` if approved_l1),
`submitted_date`, `submitted_by`, `age_days`.

```
My Approvals                                    Filters: [Waiting for me ✓] [Overdue > 3 d]  Group by: Type ▾
┌───────────────┬────────────────┬──────────────┬────────────┬──────────────┬───────┬──────┬────────┐
│ Document      │ Type           │ Project      │ Partner    │ Amount       │ Level │ Age  │        │
├───────────────┼────────────────┼──────────────┼────────────┼──────────────┼───────┼──────┼────────┤
│ CERT/2026/0007│ Client Cert.   │ Tower A      │ Client X   │ EGP 812,000  │ L2    │ 1 d  │ [Open] │
│ VO/2026/0004  │ Variation Ord. │ Ring Road    │ Ministry Y │ EGP 140,500  │ L1    │ 5 d ⚠│ [Open] │
│ SUB/2026/0011 │ Subcontract    │ Tower A      │ Sub Co.    │ EGP 390,000  │ L1    │ 0 d  │ [Open] │
└───────────────┴────────────────┴──────────────┴────────────┴──────────────┴───────┴──────┴────────┘
```

- **"Waiting for me"** is the default filter. It shows `required_level = l1` if the user is in the L1 group and `l2` if in L2, via a search method on a non-stored `is_mine` field that reads the user's groups. It's computed in SQL, so it stays fast.
- **Open** opens the real document in a form, where the user approves with the normal header button. There's no approve-from-list and **no bulk approval** (owner Q3): the approver sees the lines first, and the document's checks run in one place.
- **Security:**
  - The view gets the same company rule and the step-2 project rules as the documents.
  - A row is only listed if the user can read the source document, checked by a test per role.
- **Notification:** on submit, a `mail.activity` ("To approve") is scheduled for the users of the required level's group, limited to the project's assigned approvers if step 2 defines them. That gives the native systray counter and email. The activity is marked done on approve or reject.
- The same model feeds `pending_approval_count` (§3) and the Overview KPI (§4), so all three numbers come from one source.

---

## 6. Search, list and kanban defaults per model (summary)
| Model | Default view | Other views | Default filter |
|---|---|---|---|
| Tender | kanban by state | list, form, pivot, graph, activity | Open (not lost/cancelled) |
| Construction project | dashboard kanban | list, form | Active |
| BOQ line | list (grouped by project/chapter) | pivot | My projects |
| Daily report | list | form, calendar (by date) | Last 7 days |
| Measurement | list | form | Draft + Confirmed |
| VO / Subcontract / Certificates | list | form, pivot | Not cancelled |
| Handover | list | form | Not closed |
| Approval request | list | — | Waiting for me |

Lists: state as a `badge` with `decoration-*`, monetary sums (`sum="Total"`), `optional="hide"` on
secondary columns, and `multi_edit` off on documents with approval.

---

## 7. Arabic RTL and tablet width

**RTL**
- Odoo builds the RTL asset bundle automatically (rtlcss) when the user language is RTL. Our SCSS still uses logical properties (`border-inline-start`, `margin-inline-end`, Bootstrap `ms-*`/`me-*`/`text-end`), so it's correct either way.
- No hardcoded `left`/`right` in templates and no `float`.
- Kanban card divergence border: `border-inline-start`, so it's on the right in Arabic.
- Chart.js: set `rtl: true` and `textDirection: 'rtl'` on legend and tooltip when `localization.direction === 'rtl'`. The time axis is **not** reversed, which matches core Odoo graph views.
- Numbers and dates use the user's language format (`formatMonetary`, `formatDate` from `@web`). There's no manual string concatenation, so "EGP 1,250,000" and "١٬٢٥٠٬٠٠٠ ج.م" both come from the language settings.
- Mixed text such as a reference in an Arabic label is wrapped in `<bdi>`/`dir="auto"`, so `CERT/2026/0007` doesn't flip.

**Tablet** (site engineers; target 768–1024 px, portrait and landscape)
- Forms: Odoo's 2-column `group` collapses to 1 column below 992 px natively. The rule is no `col="4"` layouts.
- Editable lines: at most 6 visible columns (others `optional="hide"`). Quantity fields use a numeric keyboard (`inputmode` comes from the float widget).
- Daily report and measurement are the tablet-first forms. Their line tabs come first, and they have no wide tables.
- Kanban cards: minimum width from `o_kanban_dashboard` is 1 per row in portrait and 2 in landscape. Quick-create buttons wrap (`d-flex flex-wrap gap-1`).
- Overview: Bootstrap grid. KPIs are `col-6 col-lg-4 col-xl-2` (8 cards: 6 + a 2-card row) and charts are `col-12 col-xl-6`.
- Touch targets are at least 44 px; core buttons already comply, so we add no small icon-only buttons.

**How it's verified** (per screen, before calling it done):
1. A tour (`HttpCase.start_tour`) runs the menu → document → next-step flow with the user language `ar_001`.
2. Screenshots at 768×1024 and 1024×768, in English and Arabic, attached to the step report.
3. The UAT checklist (Phase 5) gets one RTL/tablet line per screen.

---

## 8. Styling budget
- One file, `static/src/scss/construction.scss`, in `web.assets_backend`. Target under 80 lines.
- Only these rules:
  - The divergence border colours (`$warning`, `$danger` via `var(--bs-warning)` / `var(--bs-danger)`).
  - The Overview grid gaps.
  - The KPI card number size (`$h3-font-size`).
- No selectors on core classes except as a descendant of our own root class (`.o_nt_overview`, `.o_nt_project_dashboard`), so core screens are never affected.
- No colours as hex; Bootstrap and Odoo variables only, so dark mode works.

---

## 9. Schedule and estimate (working days, one developer)

| # | Part | When | Est. | Depends on |
|---|---|---|---|---|
| UX-1 | Menu restructure (§1), new xml-ids, groups per role | after step 3, before golden-cycle demo | 0.5 d | step 2 roles |
| UX-2 | Restore and standardise search views for all models (§2.1, §6) | same | 1 d | — |
| UX-3 | Form standard across 8 documents: header, one primary, ribbons, smart buttons, groups, tabs, chatter tracking (§2.1–2.2) | same | 3 d | step 3 (certificate tabs) |
| UX-4 | Tender kanban pipeline (§2.3), including deadline progressbar | same | 0.5 d | — |
| UX-5 | "One primary button" view test plus tour on the golden cycle (§2.1, §7) | same | 0.5 d | UX-3 |
| | **Subtotal before golden-cycle demo** | | **5.5 d** | |
| UX-6 | Shared financial helper (§3.0) + project dashboard kanban, batched computes, graph JSON, quick-create, divergence company setting, query-count test (§3) | step 4 | 3.5 d | step 3 (executed vs certified, invoices, retention account) |
| UX-7 | My Approvals: SQL view, "for me" search, activities on submit/approve, per-role tests (§5) | step 4 | 2 d | step 2 roles |
| UX-8 | Overview: `get_data` with exact-number tests (2 d) + OWL components and charts (2.5 d) + Hoot test and tour (0.5 d) | step 4 | 5 d | step 3, UX-7, tender `decision_date` |
| UX-9 | RTL and tablet pass on all screens, screenshots, fixes (§7) | end of step 4 | 1.5 d | all |
| | **Subtotal step 4** | | **12 d** | |
| | **Total** | | **17.5 d ≈ 3.5 weeks** | |

**Effect on the plan:** the original plan's step 4 had a reporting/dashboard line that covered pivot and graph views only. This spec replaces it and is largely additive. I'll restate the step 4 total with this included when step 4 starts. Before the golden-cycle demo, 5.5 d are added after step 3.

---

## 10. Owner answers (2026-11-02, recorded in DECISIONS.md S5)
| # | Question | Answer |
|---|---|---|
| Q1 | Divergence threshold | **10 percentage points, company setting** (`res.company`, editable in Settings), not hardcoded |
| Q2 | "Billed" basis | **Three labelled figures everywhere** (card and Overview): Certified (approved certificates), Invoiced (posted invoices), Collected (payments). Same definitions on every screen (§3.0). The word "Billed" is not used |
| Q3 | Bulk approval from My Approvals | **No.** Approved |
| Q4 | Uncertified work in cash-flow forecast | **Excluded**, but "Executed not yet certified" shown as a separate line |
| Q5 | Who sees the Overview | **Approved** (Mgmt, Finance, PMs). **Step 2 record rules must restrict project managers to their own projects** |
| Q6 | Offline on tablet | **Online only for now** — owner to confirm with the client (open) |
| Q7 | Tender drag-and-drop | **No.** Approved |
