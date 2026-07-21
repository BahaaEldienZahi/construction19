# IMPLEMENTATION ROADMAP: Phase 1 (Critical Fixes)

**Goal**: Restore search views, enable subcontractor linkages, complete approval workflows  
**Estimated Time**: 2-3 hours  
**Difficulty**: Medium (XML + Python)

---

## PART 1: PAYMENT CERTIFICATE SEARCH VIEW (5 min)

**File**: `views/boq_payment_certificate_views.xml`  
**Action**: Uncomment search view (lines 91-108)

Replace:
```xml
<!--    <record id="view_boq_payment_certificate_search" model="ir.ui.view">-->
<!--        <field name="name">boq.payment.certificate.search</field>-->
...
<!--    </record>-->
```

With:
```xml
<record id="view_boq_payment_certificate_search" model="ir.ui.view">
    <field name="name">boq.payment.certificate.search</field>
    <field name="model">boq.payment.certificate</field>
    <field name="arch" type="xml">
        <search string="Search Payment Certificates">
            <field name="name"/>
            <field name="project_id"/>
            <field name="date"/>
            <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
            <filter string="Pending Approval" name="pending"
                    domain="[('state', 'in', ('submitted', 'approved_l1'))]"/>
            <filter string="Approved" name="approved" domain="[('state', '=', 'approved')]"/>
            <group expand="0" string="Group By">
                <filter string="Project" name="group_project" context="{'group_by': 'project_id'}"/>
                <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                <filter string="Date" name="group_date" context="{'group_by': 'date'}"/>
            </group>
        </search>
    </field>
</record>
```

---

## PART 2: CREATE MISSING SEARCH VIEWS

### 2A. Subcontract Agreement Search View

**File**: `views/subcontract_agreement_views.xml` (CREATE NEW)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_subcontract_agreement_form" model="ir.ui.view">
        <field name="name">subcontract.agreement.form</field>
        <field name="model">subcontract.agreement</field>
        <field name="arch" type="xml">
            <form string="Subcontract Agreement">
                <header>
                    <button name="action_submit_for_approval" string="Submit for Approval" type="object"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_approve_l1" string="Approve (L1)" type="object"
                            class="btn-primary" invisible="state != 'submitted'"/>
                    <button name="action_approve_l2" string="Final Approve (L2)" type="object"
                            class="btn-success" invisible="state != 'approved_l1'"/>
                    <button name="action_reject" string="Reject" type="object"
                            invisible="state not in ('submitted', 'approved_l1')"/>
                    <button name="action_reset_draft" string="Reset to Draft" type="object"
                            invisible="state != 'rejected'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,submitted,approved_l1,approved"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="project_id" readonly="state != 'draft'"/>
                            <field name="partner_id" readonly="state != 'draft'"/>
                            <field name="date" readonly="state != 'draft'"/>
                        </group>
                        <group>
                            <field name="contract_value"/>
                            <field name="retention_percentage"/>
                            <field name="total_value"/>
                        </group>
                    </group>
                    <group>
                        <group>
                            <field name="start_date"/>
                            <field name="completion_date"/>
                        </group>
                        <group>
                            <field name="state" widget="badge"/>
                        </group>
                    </group>
                    <group string="Scope of Work">
                        <field name="scope_of_work" nolabel="1"/>
                    </group>
                    <field name="line_ids" readonly="state != 'draft'">
                        <list editable="bottom">
                            <field name="boq_line_id"/>
                            <field name="code" readonly="1"/>
                            <field name="name" readonly="1"/>
                            <field name="uom_id" readonly="1"/>
                            <field name="quantity"/>
                            <field name="unit_price"/>
                            <field name="subtotal" sum="Total"/>
                        </list>
                    </field>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="view_subcontract_agreement_list" model="ir.ui.view">
        <field name="name">subcontract.agreement.list</field>
        <field name="model">subcontract.agreement</field>
        <field name="arch" type="xml">
            <list string="Subcontract Agreements" decoration-success="state == 'approved'"
                  decoration-danger="state == 'rejected'">
                <field name="name"/>
                <field name="project_id"/>
                <field name="partner_id"/>
                <field name="date"/>
                <field name="total_value" sum="Total"/>
                <field name="state" widget="badge"
                       decoration-success="state == 'approved'"
                       decoration-danger="state == 'rejected'"
                       decoration-info="state in ('submitted', 'approved_l1')"/>
            </list>
        </field>
    </record>

    <record id="view_subcontract_agreement_search" model="ir.ui.view">
        <field name="name">subcontract.agreement.search</field>
        <field name="model">subcontract.agreement</field>
        <field name="arch" type="xml">
            <search string="Search Subcontract Agreements">
                <field name="name"/>
                <field name="project_id"/>
                <field name="partner_id"/>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Pending Approval" name="pending"
                        domain="[('state', 'in', ('submitted', 'approved_l1'))]"/>
                <filter string="Approved" name="approved" domain="[('state', '=', 'approved')]"/>
                <separator/>
                <filter string="This Month" name="this_month"
                        domain="[('date', '&gt;=', context_today().replace(day=1)), ('date', '&lt;', (context_today() + relativedelta(months=1)).replace(day=1))]"/>
                <group expand="0" string="Group By">
                    <filter string="Project" name="group_project" context="{'group_by': 'project_id'}"/>
                    <filter string="Subcontractor" name="group_partner" context="{'group_by': 'partner_id'}"/>
                    <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                    <filter string="Date" name="group_date" context="{'group_by': 'date:month'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_subcontract_agreement" model="ir.actions.act_window">
        <field name="name">Subcontract Agreements</field>
        <field name="res_model">subcontract.agreement</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_subcontract_agreement" name="Subcontract Agreements"
              parent="nt_construction.menu_tender_root"
              action="action_subcontract_agreement" sequence="50"/>

</odoo>
```

Add to `__manifest__.py` data list:
```python
'views/subcontract_agreement_views.xml',
```

---

### 2B. Project Handover Search View

**File**: `views/project_handover_views.xml` (CREATE NEW)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_project_handover_form" model="ir.ui.view">
        <field name="name">project.handover.form</field>
        <field name="model">project.handover</field>
        <field name="arch" type="xml">
            <form string="Project Handover">
                <header>
                    <button name="action_confirm_provisional_handover" string="Confirm Provisional Handover"
                            type="object" class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_release_retention_stage1" string="Release Stage 1 Retention"
                            type="object" invisible="state != 'provisional' or retention_release_stage1_done"/>
                    <button name="action_final_handover" string="Finalize Handover" type="object"
                            class="btn-success" invisible="state != 'provisional'"/>
                    <button name="action_release_retention_stage2" string="Release Stage 2 Retention"
                            type="object" invisible="state != 'final' or retention_release_stage2_done"/>
                    <button name="action_close" string="Close Handover" type="object"
                            class="btn-success" invisible="state != 'final'"/>
                    <button name="action_reset_draft" string="Reset to Draft" type="object"
                            invisible="state == 'draft'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,provisional,final,closed"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="project_id" readonly="state != 'draft'"/>
                            <field name="date" readonly="state != 'draft'"/>
                        </group>
                        <group>
                            <field name="state" widget="badge"/>
                            <field name="punch_list_open_count"/>
                            <field name="punch_list_total_count"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Provisional Handover">
                            <group>
                                <group>
                                    <field name="provisional_handover_date"/>
                                    <field name="defects_liability_months"/>
                                    <field name="defects_liability_end_date"/>
                                </group>
                                <group>
                                    <field name="retention_held_total"/>
                                    <field name="retention_release_stage1_percentage"/>
                                    <field name="retention_release_stage1_amount" readonly="1"/>
                                    <field name="retention_release_stage1_date" readonly="1"/>
                                </group>
                            </group>
                        </page>
                        <page string="Punch List">
                            <field name="punch_list_ids">
                                <list editable="bottom">
                                    <field name="description"/>
                                    <field name="location"/>
                                    <field name="responsible_party"/>
                                    <field name="date_reported" readonly="1"/>
                                    <field name="status" widget="badge"/>
                                    <field name="date_closed" readonly="1"/>
                                </list>
                            </field>
                        </page>
                        <page string="Final Handover">
                            <group>
                                <group>
                                    <field name="final_handover_date"/>
                                    <field name="retention_release_stage2_percentage"/>
                                    <field name="retention_release_stage2_amount" readonly="1"/>
                                    <field name="retention_release_stage2_date" readonly="1"/>
                                </group>
                                <group>
                                    <field name="final_acceptance_notes" nolabel="1"/>
                                </group>
                            </group>
                        </page>
                        <page string="Notes">
                            <field name="notes" nolabel="1"/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="view_project_handover_list" model="ir.ui.view">
        <field name="name">project.handover.list</field>
        <field name="model">project.handover</field>
        <field name="arch" type="xml">
            <list string="Project Handovers" decoration-success="state == 'closed'"
                  decoration-info="state in ('provisional', 'final')">
                <field name="name"/>
                <field name="project_id"/>
                <field name="provisional_handover_date"/>
                <field name="final_handover_date"/>
                <field name="retention_held_total" sum="Total Retained"/>
                <field name="state" widget="badge"/>
            </list>
        </field>
    </record>

    <record id="view_project_handover_search" model="ir.ui.view">
        <field name="name">project.handover.search</field>
        <field name="model">project.handover</field>
        <field name="arch" type="xml">
            <search string="Search Project Handovers">
                <field name="name"/>
                <field name="project_id"/>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Provisional" name="provisional" domain="[('state', '=', 'provisional')]"/>
                <filter string="Final" name="final" domain="[('state', '=', 'final')]"/>
                <filter string="Closed" name="closed" domain="[('state', '=', 'closed')]"/>
                <separator/>
                <filter string="Punch List Open" name="punch_open"
                        domain="[('punch_list_open_count', '&gt;', 0)]"/>
                <group expand="0" string="Group By">
                    <filter string="Project" name="group_project" context="{'group_by': 'project_id'}"/>
                    <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_project_handover" model="ir.actions.act_window">
        <field name="name">Project Handovers</field>
        <field name="res_model">project.handover</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_project_handover" name="Project Handovers"
              parent="nt_construction.menu_tender_root"
              action="action_project_handover" sequence="60"/>

</odoo>
```

Add to `__manifest__.py` data list:
```python
'views/project_handover_views.xml',
```

---

### 2C. Site Daily Report Search View

**File**: `views/site_daily_report_views.xml` (CREATE NEW)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_site_daily_report_form" model="ir.ui.view">
        <field name="name">site.daily.report.form</field>
        <field name="model">site.daily.report</field>
        <field name="arch" type="xml">
            <form string="Site Daily Report">
                <header>
                    <button name="action_confirm" string="Confirm Report" type="object"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_reset_draft" string="Reset to Draft" type="object"
                            invisible="state != 'confirmed'"/>
                    <field name="state" widget="statusbar" statusbar_visible="draft,confirmed"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="project_id" readonly="state != 'draft'"/>
                            <field name="date" readonly="state != 'draft'"/>
                            <field name="user_id" readonly="1"/>
                        </group>
                        <group>
                            <field name="weather"/>
                            <field name="state" widget="badge"/>
                            <field name="total_manpower_count" readonly="1"/>
                            <field name="total_equipment_hours" readonly="1"/>
                            <field name="total_amount_executed_today" readonly="1"/>
                        </group>
                    </group>
                    <notebook>
                        <page string="Manpower">
                            <field name="manpower_ids" readonly="state != 'draft'">
                                <list editable="bottom">
                                    <field name="trade"/>
                                    <field name="headcount"/>
                                    <field name="hours"/>
                                    <field name="is_subcontractor"/>
                                    <field name="note"/>
                                </list>
                            </field>
                        </page>
                        <page string="Equipment">
                            <field name="equipment_ids" readonly="state != 'draft'">
                                <list editable="bottom">
                                    <field name="equipment_name"/>
                                    <field name="equipment_type"/>
                                    <field name="count"/>
                                    <field name="hours_worked"/>
                                    <field name="hours_idle"/>
                                    <field name="idle_reason"/>
                                </list>
                            </field>
                        </page>
                        <page string="Quantities Executed">
                            <field name="progress_ids" readonly="state != 'draft'">
                                <list editable="bottom">
                                    <field name="boq_line_id"/>
                                    <field name="quantity_executed"/>
                                    <field name="period_name"/>
                                    <field name="note"/>
                                </list>
                            </field>
                        </page>
                        <page string="Notes">
                            <field name="site_notes" nolabel="1"/>
                        </page>
                    </notebook>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="view_site_daily_report_list" model="ir.ui.view">
        <field name="name">site.daily.report.list</field>
        <field name="model">site.daily.report</field>
        <field name="arch" type="xml">
            <list string="Site Daily Reports">
                <field name="name"/>
                <field name="project_id"/>
                <field name="date"/>
                <field name="weather"/>
                <field name="total_manpower_count"/>
                <field name="total_equipment_hours"/>
                <field name="total_amount_executed_today" sum="Total Executed"/>
                <field name="state" widget="badge"/>
            </list>
        </field>
    </record>

    <record id="view_site_daily_report_search" model="ir.ui.view">
        <field name="name">site.daily.report.search</field>
        <field name="model">site.daily.report</field>
        <field name="arch" type="xml">
            <search string="Search Daily Reports">
                <field name="name"/>
                <field name="project_id"/>
                <field name="user_id"/>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Confirmed" name="confirmed" domain="[('state', '=', 'confirmed')]"/>
                <separator/>
                <filter string="Today" name="today"
                        domain="[('date', '=', context_today())]"/>
                <filter string="This Week" name="this_week"
                        domain="[('date', '&gt;=', context_today() - relativedelta(days=7))]"/>
                <group expand="0" string="Group By">
                    <filter string="Project" name="group_project" context="{'group_by': 'project_id'}"/>
                    <filter string="Date" name="group_date" context="{'group_by': 'date'}"/>
                    <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                    <filter string="Engineer" name="group_engineer" context="{'group_by': 'user_id'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_site_daily_report" model="ir.actions.act_window">
        <field name="name">Site Daily Reports</field>
        <field name="res_model">site.daily.report</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_site_daily_report" name="Daily Reports (Sarky)"
              parent="nt_construction.menu_tender_root"
              action="action_site_daily_report" sequence="70"/>

</odoo>
```

Add to `__manifest__.py` data list:
```python
'views/site_daily_report_views.xml',
```

---

### 2D. Work Measurement Search View

**File**: `views/work_measurement_views.xml` (CREATE NEW)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_work_measurement_form" model="ir.ui.view">
        <field name="name">work.measurement.form</field>
        <field name="model">work.measurement</field>
        <field name="arch" type="xml">
            <form string="Work Measurement">
                <header>
                    <button name="action_confirm" string="Confirm Measurement" type="object"
                            class="btn-primary" invisible="state != 'draft'"/>
                    <button name="action_create_payment_certificate" string="Create Payment Certificate" type="object"
                            class="btn-success" invisible="state != 'confirmed' or payment_certificate_id"/>
                    <button name="action_reset_draft" string="Reset to Draft" type="object"
                            invisible="state == 'draft'"/>
                    <field name="state" widget="statusbar"
                           statusbar_visible="draft,confirmed,linked"/>
                </header>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button name="action_view_payment_certificate" type="object"
                                class="oe_stat_button" icon="fa-file-text"
                                invisible="not payment_certificate_id">
                            <div class="o_stat_info">
                                <span class="o_stat_text">Payment Certificate</span>
                            </div>
                        </button>
                    </div>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group>
                            <field name="project_id" readonly="state != 'draft'"/>
                            <field name="date" readonly="state != 'draft'"/>
                        </group>
                        <group>
                            <field name="period_from" readonly="state != 'draft'"/>
                            <field name="period_to" readonly="state != 'draft'"/>
                            <field name="total_executed_value" readonly="1"/>
                        </group>
                    </group>
                    <field name="daily_report_ids" readonly="state != 'draft'">
                        <list editable="bottom">
                            <field name="name"/>
                            <field name="date"/>
                            <field name="user_id"/>
                            <field name="state" widget="badge"/>
                        </list>
                    </field>
                    <field name="progress_ids" readonly="1">
                        <list>
                            <field name="boq_line_id"/>
                            <field name="quantity_executed"/>
                            <field name="date"/>
                            <field name="period_name"/>
                        </list>
                    </field>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="view_work_measurement_list" model="ir.ui.view">
        <field name="name">work.measurement.list</field>
        <field name="model">work.measurement</field>
        <field name="arch" type="xml">
            <list string="Work Measurements">
                <field name="name"/>
                <field name="project_id"/>
                <field name="period_from"/>
                <field name="period_to"/>
                <field name="total_executed_value" sum="Total"/>
                <field name="payment_certificate_id"/>
                <field name="state" widget="badge"/>
            </list>
        </field>
    </record>

    <record id="view_work_measurement_search" model="ir.ui.view">
        <field name="name">work.measurement.search</field>
        <field name="model">work.measurement</field>
        <field name="arch" type="xml">
            <search string="Search Work Measurements">
                <field name="name"/>
                <field name="project_id"/>
                <filter string="Draft" name="draft" domain="[('state', '=', 'draft')]"/>
                <filter string="Confirmed" name="confirmed" domain="[('state', '=', 'confirmed')]"/>
                <filter string="Linked to PC" name="linked" domain="[('state', '=', 'linked')]"/>
                <separator/>
                <filter string="Not Yet Billed" name="not_billed"
                        domain="[('payment_certificate_id', '=', False), ('state', '=', 'confirmed')]"/>
                <group expand="0" string="Group By">
                    <filter string="Project" name="group_project" context="{'group_by': 'project_id'}"/>
                    <filter string="Status" name="group_state" context="{'group_by': 'state'}"/>
                    <filter string="Period" name="group_period" context="{'group_by': 'period_from'}"/>
                </group>
            </search>
        </field>
    </record>

    <record id="action_work_measurement" model="ir.actions.act_window">
        <field name="name">Work Measurements</field>
        <field name="res_model">work.measurement</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu_work_measurement" name="Work Measurements"
              parent="nt_construction.menu_tender_root"
              action="action_work_measurement" sequence="65"/>

</odoo>
```

Add to `__manifest__.py` data list:
```python
'views/work_measurement_views.xml',
```

---

## PART 3: RE-ENABLE SUBCONTRACTOR LINKAGES IN MODELS

### 3A. Site Daily Report Manpower

**File**: `models/site_daily_report.py`

Find the `SiteDailyReportManpower` class and uncomment the subcontract field (line 105-107):

Replace:
```python
    # subcontract_agreement_id = fields.Many2one(
    #     'subcontract.agreement', string='Subcontract',
    #     domain="[('project_id', '=', project_id)]",
    # )
```

With:
```python
    subcontract_agreement_id = fields.Many2one(
        'subcontract.agreement', string='Subcontract',
        domain="[('project_id', '=', project_id)]",
    )
```

### 3B. Project Handover Punch Item

**File**: `models/project_handover.py`

Find the `ProjectHandoverPunchItem` class and uncomment the subcontract field (line 209-212):

Replace:
```python
    # subcontract_agreement_id = fields.Many2one(
    #     'subcontract.agreement', string='Related Subcontract',
    #     domain="[('project_id', '=', project_id)]",
    # )
```

With:
```python
    subcontract_agreement_id = fields.Many2one(
        'subcontract.agreement', string='Related Subcontract',
        domain="[('project_id', '=', project_id)]",
    )
```

---

## PART 4: UPDATE MANIFEST

**File**: `__manifest__.py`

Update the `data` list to include new view files. Replace:

```python
'data': [
    'security/construction_security.xml',
    'security/ir.model.access.csv',
    'data/tender_sequence.xml',
    'data/construction_sequences.xml',
    'views/boq_line_views.xml',
    'views/tender_tender_views.xml',
    'views/project_project_views.xml',
    'views/purchase_order_views.xml',
    'views/boq_payment_certificate_views.xml',
    'views/dashboard_views.xml',
    'views/subcontract_agreement_views.xml',
    'views/work_measurement_views.xml',
],
```

With:

```python
'data': [
    'security/construction_security.xml',
    'security/ir.model.access.csv',
    'data/tender_sequence.xml',
    'data/construction_sequences.xml',
    'views/boq_line_views.xml',
    'views/tender_tender_views.xml',
    'views/project_project_views.xml',
    'views/purchase_order_views.xml',
    'views/boq_payment_certificate_views.xml',
    'views/boq_variation_order_views.xml',
    'views/subcontract_agreement_views.xml',
    'views/project_handover_views.xml',
    'views/site_daily_report_views.xml',
    'views/work_measurement_views.xml',
    'views/dashboard_views.xml',
],
```

---

## TESTING CHECKLIST (Phase 1)

- [ ] Module updates without errors
- [ ] Payment Certificate list has search filters (Draft, Pending, Approved)
- [ ] Subcontract Agreement list view displays all records
- [ ] Can create subcontract agreement with approval workflow buttons
- [ ] Project Handover list has search + status filters
- [ ] Site Daily Report list searches by project/date/engineer
- [ ] Work Measurement can be filtered by linked/not linked to PC
- [ ] Subcontractor field visible in daily report manpower lines
- [ ] Subcontractor field visible in punch list items

---

**Status**: Ready for implementation  
**Next**: Execute Part 1-4, then move to Phase 2 (Payment Certificate creation from Work Measurement)

