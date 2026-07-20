# NT Construction & Tender Management

مديول متكامل لإدارة المناقصات والمقاولات في أودو 19 (Community & Enterprise)، يغطي الدورة الكاملة من المناقصة حتى التسليم النهائي.

## 🏗️ Full Cycle — الدورة الكاملة

```
Tender → Won → Project → BOQ → Execution → Daily Reports (Sarky)
                                            → Work Measurement
                                            → Material Requisitions
                                            → Work Inspections (WIR/MIR)
                                            → Progress Photos
                                            → Correspondence
         → Variation Orders → Payment Certificates → Customer Invoice
         → Subcontract Agreements → Subcontractor Certificates → Vendor Bill
         → Bank Guarantees
         → Handover (Provisional → DLP → Final → Closed)
```

## المكونات

### 📋 المناقصات — Tenders
- **Tenders** (`tender.tender`): دورة المناقصة كاملة (draft → submitted → under_evaluation → won/lost) وتحويل المناقصة الفايزة لمشروع تنفيذي مع نسخ BOQ.
- **BOQ** (`boq.line`): جدول كميات هرمي (Chapter → Item → Sub-item) مع تتبع الإنجاز والتكاليف.

### 🏗️ التنفيذ — Project Execution
- **Daily Reports / Sarky** (`site.daily.report`): تقرير يومي بالعمالة والمعدات والكميات المنفذة.
- **Work Measurement** (`work.measurement`): تجميع التقارير اليومية لفترات محاسبية، مع تجميع تلقائي للكميات حسب بنود BOQ.
- **Material Requisitions** (`material.requisition`): طلبات صرف مواد من الموقع للمخازن.
- **Work Inspections WIR/MIR** (`work.inspection`): طلبات فحص الأعمال والمواد.
- **Progress Photos** (`site.progress.photo`): توثيق صور تقدم الأعمال حسب الموقع والتاريخ.
- **Correspondence** (`project.correspondence`): مراسلات وخطابات الموقع (وارد/صادر).

### 💰 الشؤون التجارية — Commercial
- **Variation Orders** (`boq.variation.order`): أوامر تغيير بموافقة مستويين، تطبق تلقائياً على BOQ وقيمة العقد.
- **Payment Certificates** (`boq.payment.certificate`): مستخلصات العميل بخصم ضمان واسترداد دفعة مقدمة، مع إنشاء فاتورة عميل وزر تحميل من قياس الأعمال.
- **Subcontract Agreements** (`subcontract.agreement`): اتفاقيات مقاولي الباطن مع تتبع التكاليف حسب بنود BOQ.
- **Subcontractor Certificates** (`subcontract.payment.certificate`): مستخلصات مقاولي الباطن مع إنشاء فاتورة مورد.
- **Bank Guarantees** (`bank.guarantee`): خطابات الضمان (ابتدائي/نهائي/دفعة مقدمة/خصم ضمان).

### 🏁 التسليم — Handover
- **Handovers** (`project.handover`): تسليم ابتدائي ونهائي مع فترة صيانة (DLP)، قائمة ملاحظات (Punch List)، وإفراج عن الضمان على مرحلتين.

### 📊 التقارير — Reporting
- **Cost Analysis**: Pivot/Graph (Contracted vs Committed vs Executed vs Actual Cost + Variance)
- **Billing Trend**: Pivot لحركة المستخلصات

## هيكل القائمة
```
Tenders & Construction
├── 📋 Tenders
│   ├── Tenders
│   ├── Bill of Quantities
├── 🏗️ Project Execution
│   ├── Construction Projects
│   ├── Daily Reports (Sarky)
│   ├── Work Measurements
│   ├── Material Requisitions
│   ├── Work Inspections (WIR/MIR)
│   ├── Progress Photos
│   ├── Correspondence
├── 💰 Commercial
│   ├── Variation Orders
│   ├── Payment Certificates
│   ├── Subcontract Agreements
│   ├── Subcontractor Certificates
│   ├── Bank Guarantees
├── 🏁 Handover & Delivery
│   ├── Handovers
├── 📊 Reporting
│   ├── Cost Analysis
│   ├── Billing Trend
```

## سير العمل — Workflow

### تدفق الكميات للفوترة
```
Daily Report → Work Measurement → Payment Certificate → Customer Invoice
     │                │
     │                └── Generate BOQ Summary → Load into Certificate
     └── BOQ Line Progress (quantity_executed)
```

### تدفق المقاولة من الباطن
```
Subcontract Agreement → Subcontractor Certificate → Vendor Bill
           │
           └── BOQ Line.committed_amount
```

### تدفق المواد
```
Material Requisition → Purchase Order → Vendor Bill → BOQ Line.actual_cost
```

## التنصيب
1. انسخ الفولدر `nt_construction` جوه الـ custom addons path.
2. Update Apps List من Settings.
3. نصّب المديول من Apps.
4. روح Settings → Users وحط المستخدمين المناسبين في جروبات:
   - **Approver - Level 1 (Site/PM)**
   - **Approver - Level 2 (Finance/Management)**

## طبقة الموافقة (Approval Workflow)
المحرك الأساسي للموافقات مكتوب بالكامل جوه المديول (`construction.approval.mixin`) — شغال 100% على أي نسخة أودو (CE أو Enterprise).

## قبل التسليم للعميل — Checklist
- [ ] نصّب على قاعدة تجريبية وراقب الـ log وقت التنصيب.
- [ ] اختبر دورة مناقصة كاملة.
- [ ] اختبر BOQ هرمي وتأكد من صحة الإجماليات.
- [ ] اختبر Variation Order كامل.
- [ ] اختبر Payment Certificate + Load from WM + Create Invoice.
- [ ] اختبر Subcontract Agreement → Certificate → Vendor Bill.
- [ ] اختبر Daily Report → Work Measurement → Gen Summary → Load into PC.
- [ ] اختبر Material Requisition + Work Inspection + Correspondence + Photos.
- [ ] اختبر Handover (Provisional → DLP → Punch List → Final → Close).
- [ ] اختبر Bank Guarantee flow.
- [ ] اختبر صلاحيات المستخدمين.
