# AGENTS.md - NT Construction & Tender Management

**For: AI coding agents working on the nt_construction module**

## Big Picture Architecture

This is an **Odoo 19 construction & tender management system** structured as a complete workflow:

```
Tender (as-bid) 
  → tender.tender (state: draft → submitted → won/lost)
  → boq.line (hierarchical Chapter→Item structure, tender_id)
       ↓ (if won)
  → Creates project.project with is_construction_project=True
  → Copies BOQ to project (boq.line with project_id, not tender_id)
       ↓ (execution phase)
  → boq.variation.order (changes to scope, needs 2-level approval)
  → boq.payment.certificate (progress billing with retention %)
```

**Key architectural decision**: BOQ lines belong to **either** a tender **or** a project, never both. This allows as-bid vs as-contracted tracking.

---

## Core Models & Data Flows

### 1. **Tender (`tender.tender`)**
- **States**: draft → submitted → under_evaluation → won/lost/cancelled
- **Purpose**: Bid management before award
- **Linked BOQ**: `boq_line_ids` (tender_id filled, project_id empty)
- **Conversion to Project**: `action_set_won()` → triggers project creation in inherited `project.project.create_execution_project()`
- **Key fields**: name (seq), client_id, estimated_value, awarded_value, state (tracked)

### 2. **Project Inheritance (`project.project`)**
- **New Boolean**: `is_construction_project` – gate for BOQ/Variation/Certificate features
- **BOQ after conversion**: `boq_line_ids` (project_id filled, different from as-bid)
- **Retention & advance**: `retention_percentage` (default 5%), `advance_payment_percentage` (affects certificates)
- **Contract tracking**: `contract_value` (starts from awarded_value, updated by Variation Orders)
- **Key methods**: `create_execution_project()` – copies tender→project + BOQ, clears as-bid BOQ

### 3. **BOQ Line Hierarchy (`boq.line`)**
- **Structure**: `parent_id` + `child_ids` → Chapter→Item→Sub-item
- **Ownership**: Either `tender_id` (bid phase) OR `project_id` (execution phase), never both
- **Computed fields** (recursive, store=True):
  - `level` – depth in hierarchy (0=root, 1=child, etc)
  - `is_group` – True if has children
  - `total_contracted` = qty × unit_price (for leaves), sum of children for groups
  - `quantity_executed_cumulative`, `amount_executed_cumulative` (from `boq.line.progress`)
  - `percentage_complete` = executed / contracted
- **Leaf lines only**: qty, unit_price; group lines compute from children
- **No direct editing in UI**: Changes via `boq.variation.order` (approval-gated)

### 4. **BOQ Progress (`boq.line.progress`)**
- **Purpose**: Track execution (quantities, dates, notes) per period
- **Created by**: Payment Certificates on final approval (`_on_final_approval()`)
- **Feeds**: Cumulative execution metrics in `boq.line` via aggregation

### 5. **Variation Order (`boq.variation.order`)**
- **Inherits**: `construction.approval.mixin` + mail.thread/activity.mixin
- **State flow**: draft → submitted → approved_l1 → approved → rejected/cancelled
- **Lines**: Can modify existing BOQ lines (qty/price) OR add new lines under a chapter
- **Final approval hook**: `_on_final_approval()` → applies all line changes, updates `project.contract_value`
- **Applied flag**: Once approved, marked `applied=True` (idempotent)

### 6. **Payment Certificate (`boq.payment.certificate`)**
- **Inherits**: `construction.approval.mixin` + mail.thread/activity.mixin
- **Lines**: Selected BOQ lines + qty/amount this period
- **Auto-computed**:
  - `gross_amount` = sum of line amounts
  - `retention_amount` = gross × project.retention_percentage / 100
  - `net_payable` = gross - retention - advance_recovery
- **Final approval hook**: Creates `boq.line.progress` records (feeds cumulative execution)
- **Invoice creation**: `action_create_customer_invoice()` → Creates `account.move` linked to project's customer

### 7. **Purchase Order (`purchase.order` inherited)**
- **Extended fields**: `project_id`, `boq_line_id` on lines
- **Constraint**: PO line's BOQ must match PO's project
- **Purpose**: Link subcontractor/material costs to BOQ lines for cost tracking

---

## Two-Level Approval Workflow (Mixin-Based)

**Model**: `construction.approval.mixin` (abstract, inherited by Variation Order & Payment Certificate)

### How It Works
```python
# State machine:
draft → (submit) → submitted → (approve_l1) → approved_l1 → (approve_l2) → approved
                    ↓ (reject)    ↑ (reject)
                    rejected ←────┘
```

### Key Methods
- `action_submit_for_approval()` – moves to "submitted"
- `action_approve_l1()` – checks group `group_construction_approver_l1`, moves to "approved_l1"
- `action_approve_l2()` – checks group `group_construction_approver_l2`, moves to "approved", calls `_on_final_approval()`
- `action_reject()` – resets to "rejected"
- `action_reset_draft()` – clears all approval fields, back to draft

### Customization
- **Override `_approval_group_l1_xmlid`** to use different groups (default: `nt_construction.group_construction_approver_l1`)
- **Override `_on_final_approval()`** to add post-approval side effects (e.g., Variation Order applies BOQ changes)
- **Enforcement**: Python-level (no UI button hiding) — raises `UserError` if unauthorized

### Studio Integration (Optional, Enterprise Only)
You can layer Odoo Studio's "Approval Rules" on top for audit trail & notifications without breaking the core mixin. Not required for functionality.

---

## Critical Patterns & Developer Conventions

### 1. **Ownership vs Inheritance**
- BOQ lines have **mutually exclusive** ownership: `tender_id` XOR `project_id`
- Never query both at once; always filter by one or the other
- Example: `self.env['boq.line'].search([('project_id', '=', proj_id), ('parent_id', '=', False)])`

### 2. **Computed vs Stored Fields**
- Hierarchical computations (`total_contracted`, `percentage_complete`) use `store=True, recursive=True`
- Recursive triggers work on tree changes; manually trigger `_compute_field()` after bulk BOQ edits
- **Rule**: If a field name ends in `_cumulative`, it's aggregated from child records via `.progress` entries

### 3. **Sequence Generation**
- Document names (`tender`, `boq.variation.order`, `boq.payment.certificate`) auto-generate on create
- Check `data/tender_sequence.xml` and `data/construction_sequences.xml` for sequence codes
- Example: `self.env['ir.sequence'].next_by_code('boq.variation.order')`

### 4. **Translatable Strings**
- Module uses Arabic + English: Mix of `_("string")` and explicit Arabic comments
- Example: `help='القيمة التعاقدية...'` (help in Arabic, label in English via XML)
- Always wrap computed defaults with `_()` for translations

### 5. **Constraint Patterns**
- **SQL constraints**: For uniqueness (e.g., tender name per company)
- **@api.constrains**: For cross-field validation (e.g., PO line's BOQ matches project)
- **ValidationError**: User-facing, immediate failure during create/write
- **UserError**: Action-level (state transition), raised before write

### 6. **Mail Thread & Activity**
- All approval workflow models inherit `mail.thread, mail.activity.mixin`
- Tracking fields auto-create chatter messages: `tracking=True` in field definition
- Activities (follow-ups) managed by user actions; consider adding them in `_on_final_approval()`

### 7. **Monetary Fields**
- Always pair with `currency_field='...'` (e.g., `currency_field='currency_id'`)
- Related currency fields (`currency_id = fields.Many2one(related='project_id.construction_currency_id')`) are read-only

---

## Integration Points & External Dependencies

### Odoo Base Modules Required
- **project**: Project model (inherited, extended with is_construction_project, boq_ids, etc.)
- **purchase**: PurchaseOrder model (inherited, extended with project_id, boq_line_id)
- **account**: account.move creation (Payment Certificate → Customer Invoice)
- **analytic**: Analytic account linking (optional, for cost tracking)

### Key Inheritance Chain
```
nt_construction.tender.tender
  └─ mail.thread, mail.activity.mixin

nt_construction.project.project
  └─ project.project (inherits)

nt_construction.boq.variation.order
  └─ construction.approval.mixin (abstract)
  └─ mail.thread, mail.activity.mixin

nt_construction.boq.payment.certificate
  └─ construction.approval.mixin (abstract)
  └─ mail.thread, mail.activity.mixin
```

---

## Developer Workflows

### Testing a Tender → Project Workflow
```bash
# 1. Create a tender (draft) in UI
# 2. Add BOQ lines (hierarchical) — see boq_line_views.xml for tree view
# 3. Submit tender
# 4. Mark as Won (sets date_won, auto-generates sequence name)
# 5. Check project creation:
#    a. Navigate to Projects, find linked project
#    b. BOQ lines should be copied (project_id filled, no tender_id)
#    c. contract_value should = awarded_value
```

### Testing Variation Order Approval
```bash
# 1. Create Variation Order in project context
# 2. Add lines (modify qty or add new items)
# 3. Submit (state→submitted)
# 4. Log in as Level 1 approver → Approve (L1) button
#    (User must be in group_construction_approver_l1)
# 5. Log in as Level 2 approver → Final Approve (L2) button
#    (User must be in group_construction_approver_l2)
# 6. Check:
#    a. BOQ lines updated (qty, prices)
#    b. project.contract_value += total_delta_amount
#    c. Variation Order marked applied=True
```

### Debugging Approval Denials
- **Common issue**: User not in approver group
  - **Fix**: Settings → Users → Select user → Edit → Groups → Add "Approver - Level 1" or "Level 2"
  - **Level 2 implies Level 1**: If user in L2, they're also L1
- **Trace**: Enable logging in `construction_approval_mixin.action_approve_l1()` to see group check

### BOQ Recalculation After Bulk Edits
```python
# After creating/modifying many boq.line records:
for line in boq_lines:
    line._compute_total_contracted()
    line._compute_execution()
# Or trigger via ORM:
self.env['boq.line'].search([...]).invalidate_cache()
```

---

## File Organization

```
nt_construction/
├── models/
│   ├── __init__.py              # Imports all models
│   ├── tender_tender.py         # Bid lifecycle & project conversion
│   ├── project_project.py       # Construction project fields & BOQ inheritance
│   ├── boq_line.py              # Hierarchical BOQ (Chapter→Item)
│   ├── boq_line_progress.py     # Execution tracking per period
│   ├── boq_variation_order.py   # Scope change with 2-level approval
│   ├── boq_payment_certificate.py # Progress billing, retention, invoice
│   ├── purchase_order.py        # PO extensions (project linkage)
│   ├── construction_approval_mixin.py # Reusable 2-level approval (abstract)
│   └── [other_models].py        # Site daily report, handover, subcontract agreement, work measurement
├── views/
│   ├── tender_tender_views.xml  # Form, tree, kanban for tenders
│   ├── boq_line_views.xml       # Hierarchical tree view for BOQ
│   ├── boq_variation_order_views.xml # Form with approval buttons
│   ├── boq_payment_certificate_views.xml # Form with retention logic
│   ├── project_project_views.xml # Project form with construction fields
│   ├── purchase_order_views.xml # PO form extended fields
│   ├── dashboard_views.xml      # Cost analysis & billing trend (KPIs)
│   └── ...
├── security/
│   ├── construction_security.xml # Approver groups definition
│   └── ir.model.access.csv      # Row-level access (if needed)
├── data/
│   ├── tender_sequence.xml      # Sequence for tender.tender
│   └── construction_sequences.xml # Sequences for VO, PC, etc.
└── __manifest__.py
```

---

## Tips for Productivity

1. **Always check `is_construction_project=True`** when querying projects for BOQ/Variation/Certificate features
2. **Recursive computed fields**: Use `store=True` + `@api.depends()` for tree aggregations; manually call invalidate_cache() after bulk edits
3. **State transitions are immutable**: Use `copy=False` on state and approval fields to prevent accidental replication
4. **Approval workflow is not visible to non-approver groups**: Test with actual user in correct group, not just admin
5. **BOQ changes only via Variation Order**: Direct BOQ line edits should be prevented at UI level (see XML readonly attributes)
6. **Payment Certificate → Invoice**: Calls `action_create_customer_invoice()` to generate account.move; ensure project has customer linked

