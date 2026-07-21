# NT Construction Module: Codebase Audit & Rebuild Plan

**Date**: July 20, 2026  
**Status**: Comprehensive audit completed - identifying gaps and reconstruction priorities

---

## AUDIT FINDINGS

### ✅ What's WORKING
1. **Core Models Complete**
   - `tender.tender` – Full lifecycle (draft→submitted→under_evaluation→won/lost/cancelled)
   - `project.project` (inherited) – Construction project tracking
   - `boq.line` – Hierarchical BOQ with recursive computed totals
   - `boq.line.progress` – Execution tracking, constraints in place
   - `boq.variation.order` – 2-level approval mixin inherited, lines structure
   - `boq.payment.certificate` – Invoice creation logic, retention calculations
   - `subcontract.agreement` – Subcontractor pricing with BOQ line linkage
   - `project.handover` – Multi-stage delivery (provisional→final→closed), retention release stages
   - `site.daily.report` (Sarky) – Daily manpower/equipment/progress tracking
   - `work.measurement` – Period grouping for billing
   - `purchase.order` (inherited) – Project + BOQ line linkage

2. **Security Framework**
   - `construction_security.xml` – Approver groups defined (L1, L2, L2 implies L1)
   - `ir.model.access.csv` – Full access matrix (base.group_user vs project.group_project_manager)
   - All new models have access rows

3. **Views & UI**
   - Form views complete with workflow buttons
   - Tree/list views with status decorations
   - Search views present in: Variation Order, BOQ Lines
   - Action buttons and menuitems defined
   - Chatter integration on all approval models

---

### ⚠️ GAPS IDENTIFIED

#### **1. MISSING SEARCH VIEWS** (Search filtering broken)
- ❌ **Payment Certificate** – Search view COMMENTED OUT (lines 91-108 in boq_payment_certificate_views.xml)
- ❌ **Subcontract Agreement** – No search view file exists
- ❌ **Project Handover** – No search view file exists
- ❌ **Site Daily Report** – No search view file exists
- ❌ **Work Measurement** – No search view file exists
- ✅ Variation Order – Has search view
- ✅ Tender – Has search view (need to verify)
- ✅ BOQ Lines – Has search view (need to verify)

**Impact**: Users can't filter/group records by status, project, date ranges  
**Fix Priority**: HIGH

#### **2. MODEL STRUCTURE ISSUES**

**Incomplete Workflows**
- ❌ **Subcontract Agreement**: No state transitions or approval workflow
  - Should inherit `construction.approval.mixin` for 2-level approval
  - Currently inherits it but NO approval buttons defined
  - Missing: `action_approve_l1()`, `action_approve_l2()` button triggers in view
  
- ⚠️ **Work Measurement**: Incomplete linking to Payment Certificate
  - Fields `daily_report_ids`, `payment_certificate_id` exist but NO action to convert WM→PC
  - No method `action_create_payment_certificate()` 
  - No visibility logic for linking stage

- ❌ **Site Daily Report**: Bidirectional subcontractor linkage incomplete
  - Field `subcontract_agreement_id` COMMENTED OUT in manpower lines (line 105-107)
  - Field `subcontract_agreement_id` COMMENTED OUT in punch list (line 209-212)
  - Prevents daily labor tracking per subcontractor

#### **3. INTEGRATION GAPS**

**Subcontractor → BOQ Execution Flow Missing**
- ❌ No enforcement that subcontractor POs link to project+BOQ
  - `purchase_order.py` has project_id + boq_line_id but no "cost vs. contracted" tracking
  - Missing: Subcontractor cost commitment report
  
- ❌ No cost cascade: Subcontract Agr. Line → Purchase Order → Actual Cost
  - Subcontract agreement specifies contracted price per BOQ line
  - But no field to track actual PO lines linked to that agreement
  - No "committed cost vs. contracted price" variance analysis

**Daily Report → Payment Certificate → Invoice Flow Incomplete**
- ❌ `work.measurement` can aggregate daily reports but no auto-linking to PC
- ❌ Payment certificate lines NOT auto-populated from work measurement
- ❌ Quantity billing NOT enforced (PC lines must match WM aggregation)

**Handover → Retention Release NOT Integrated with Accounting**
- ⚠️ Retention release tracked in `project.handover` but NO GL entry creation
- Stage 1 & Stage 2 release amounts computed but no `account.move` (credit note) generated
- Finance must manually create credit notes (not ideal for audit trail)

#### **4. MISSING BUSINESS LOGIC**

**BOQ Execution Tracking**
- ❌ No "% completion by period" trend analysis
- ❌ No progress curve (S-curve) forecasting
- ❌ No earned value calculations (BCWP, BCWS)
- Missing: Dashboard showing scheduled vs. actual progress

**Quantity-Based Billing Flow**
- ❌ Payment Certificate lines NOT auto-populated from site daily report quantities
- ❌ No validation that PC quantities come from daily reports (can be manually entered, breaking audit trail)
- Missing: "Show which daily reports contributed to this PC line"

**Subcontractor Billing & Retention**
- ❌ No separate retention calculation for subcontractors
- ❌ No "advance payment" tracking for subcontractor agreements
- Missing: Subcontractor payment certificate (separate from client billing)

**Punch List & Snag Management**
- ⚠️ Punch list status (open/closed) exists but no ENFORCEMENT
  - Final handover checks if punch list open but doesn't link responsible party to action
  - Missing: Task assignment, due dates, reminders for punch list items
  - Missing: Link punch items to project tasks or subcontract agreements

#### **5. COMMENTED-OUT / INCOMPLETE CODE**

**In Views**
- Payment certificate search view (9 lines commented, lines 91-108)
- Subcontract manpower → subcontract link (commented, line 105-107 in site_daily_report.py)
- Punch item → subcontract link (commented, line 209-212 in project_handover.py)

**In Models**
- None currently, but search-related functionality disabled by missing views

#### **6. DATA INTEGRITY ISSUES**

**Missing Constraints**
- ❌ Tender BOQ → Project BOQ copy: No enforcement that copy is complete
  - What if BOQ lines are deleted from tender after copy? Project BOQ orphaned?
  
- ❌ Variation Order apply: Can be called multiple times if `applied=True` check fails
  - Should be idempotent but could cause duplicate BOQ updates if approval called twice

- ⚠️ Payment Certificate lines: No constraint linking qty to daily report quantities
  - Can manually enter 100 units even if daily reports only show 50

**Missing Audit Trail**
- ⚠️ Retention release (handover stage 1/2) creates message_post but no GL entries
  - No audit trail of "who released how much on what date" in accounting records

---

## RECONSTRUCTION PRIORITIES

### **PHASE 1: CRITICAL (Complete Search & Approval Workflow)**
Priority: **DO FIRST** (users can't filter/search, approval buttons missing)

1. ✅ Uncomment & fix Payment Certificate search view
2. ✅ Create missing search views:
   - Subcontract Agreement (status, project, date, partner)
   - Project Handover (status, project, date)
   - Site Daily Report (project, date, state)
   - Work Measurement (project, date range, state)
3. ✅ Verify & enhance existing search views:
   - Tender (add filters for date_won, client, awarded value range)
   - BOQ Lines (add filters for project vs. tender, completed %, price range)
4. ✅ Add approval workflow to Subcontract Agreement view:
   - Add form buttons: Submit, Approve L1, Approve L2, Reject, Reset
   - State machine: draft→submitted→approved_l1→approved/rejected

### **PHASE 2: INTEGRATION (Daily Report → Work Measurement → Payment Certificate)**
Priority: **HIGH** (quantity billing flow essential for construction)

1. ✅ Create `action_create_from_daily_reports()` in work.measurement
   - Accepts list of confirmed daily reports
   - Aggregates quantities by BOQ line
   - Auto-creates payment.certificate with pre-populated lines
   
2. ✅ Add validation that PC lines = WM aggregation
   - Prevent manual edits if already linked to WM
   
3. ✅ Add "Source Daily Reports" back-link on PC
   - Show which daily reports this PC was derived from

### **PHASE 3: SUBCONTRACTOR INTEGRATION (Cost Tracking)**
Priority: **HIGH** (financial controls & subcontractor management)

1. ✅ Re-enable `subcontract_agreement_id` fields:
   - In `site.daily.report.manpower` (manpower per subcontractor)
   - In `project.handover.punch.item` (punch list by responsible party)
   
2. ✅ Create subcontractor cost tracking:
   - Add `boq.line` → aggregate committed PO line costs per subcontractor agreement
   - Show "Contracted vs. Committed vs. Executed" for each BOQ line + subcontractor
   
3. ✅ Create subcontractor payment certificate (separate model or view variant)
   - Similar to client PC but for internal subcontractor payments
   - Apply subcontractor retention % separately

### **PHASE 4: HANDOVER & RETENTION (GL Integration)**
Priority: **MEDIUM** (handover is final stage, can be done after Phase 2)

1. ✅ Auto-create credit note (account.move) on retention release
   - Stage 1 release: create 50% credit note (or configured %)
   - Stage 2 release: create final 50% credit note
   
2. ✅ Add GL account config to project:
   - Retention suspense account (where holdback is posted)
   - Retention release account (where credit notes post)

### **PHASE 5: REPORTING & DASHBOARDS (Nice-to-Have)**
Priority: **LOW** (core workflow works without dashboards)

1. ✅ BOQ execution progress curve (actual vs. planned)
2. ✅ Subcontractor cost variance (committed vs. contracted)
3. ✅ Retention status per project (held, released, final)

---

## FILE-BY-FILE REBUILD CHECKLIST

### Views to Create/Fix
- [ ] **boq_payment_certificate_views.xml** – Uncomment search view
- [ ] **subcontract_agreement_views.xml** – Add search + approval buttons to form
- [ ] **project_handover_views.xml** – Add search, improve punch list
- [ ] **site_daily_report_views.xml** – Add search, re-enable subcontract link field
- [ ] **work_measurement_views.xml** – Add search, add "Create PC" button
- [ ] **tender_tender_views.xml** – Verify search view (may need enhancement)
- [ ] **boq_line_views.xml** – Verify search view (check for project vs. tender filtering)

### Models to Update
- [ ] **subcontract_agreement.py** – No changes (inheritance already correct)
- [ ] **site_daily_report.py** – Uncomment subcontract_agreement_id fields
- [ ] **project_handover.py** – Uncomment subcontract link in punch items
- [ ] **work_measurement.py** – Add `action_create_payment_certificate()` method
- [ ] **boq_payment_certificate.py** – Add WM linkage, auto-populate from WM
- [ ] **purchase_order.py** – Add cost tracking/display fields (optional Phase 3)
- [ ] **project_project.py** – Add GL account fields for retention (optional Phase 4)

### Sequences to Verify/Add
- [ ] Check `data/construction_sequences.xml` has all needed codes:
  - tender.tender ✅
  - subcontract.agreement ✅
  - boq.variation.order ✅
  - boq.payment.certificate ✅
  - project.handover ✅
  - site.daily.report ✅
  - work.measurement ✅

---

## TESTING SCENARIOS (End-to-End)

### Scenario 1: Tender→Project→BOQ
- [ ] Create tender with hierarchical BOQ (chapter, items, sub-items)
- [ ] Submit & mark as won
- [ ] Create execution project
- [ ] Verify BOQ copied to project (no tender_id)

### Scenario 2: Subcontractor Daily Labor
- [ ] Create site daily report
- [ ] Add manpower with subcontractor agreement link
- [ ] Add BOQ progress (quantities)
- [ ] Confirm daily report
- [ ] Filter by subcontractor in tree view

### Scenario 3: Variation Order Approval
- [ ] Create variation order (modify existing BOQ line + add new item)
- [ ] Submit
- [ ] L1 approver logs in, approves
- [ ] L2 approver logs in, approves
- [ ] Verify BOQ line updated + contract_value changed

### Scenario 4: Payment Certificate from Daily Reports
- [ ] Create work measurement
- [ ] Link confirmed daily reports
- [ ] Create payment certificate from WM
- [ ] Verify PC lines auto-populated with aggregated quantities
- [ ] Approve L1 → L2
- [ ] Create invoice

### Scenario 5: Handover & Retention
- [ ] Create project handover
- [ ] Add punch list items
- [ ] Move to provisional handover
- [ ] Release stage 1 retention (50%)
- [ ] Move to final handover (punch list must be empty)
- [ ] Release stage 2 retention (50%)
- [ ] Close handover

---

## SUMMARY

**Total Gaps**: ~15 significant issues  
**Search Views Missing**: 5 (Payment Cert, SubAg, Handover, Daily Report, WM)  
**Approval Workflow Missing**: 1 (Subcontract Agreement view buttons)  
**Integration Incomplete**: 3 (Daily Report→PC, Subcontractor cost tracking, GL posting)  
**Commented-out Code**: 4 locations

**Estimate to Complete**: 
- Phase 1 (Search + Approval): 2-3 hours
- Phase 2 (Billing Integration): 3-4 hours
- Phase 3 (Subcontractor): 2-3 hours
- Phase 4 (GL): 2-3 hours
- Phase 5 (Dashboards): 4-5 hours
- **Total**: ~14-18 hours for complete production-ready module

---

**Next Step**: Begin Phase 1 – uncomment payment cert search view, create missing search views, add subcontract agreement approval buttons.

