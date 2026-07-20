# NT Construction & Tender Management

مديول مخصص لإدارة المناقصات والمقاولات في أودو 19 (Community & Enterprise)، من مرحلة المناقصة لحد التنفيذ والمستخلصات.

## المكونات
- **Tenders** (`tender.tender`): دورة المناقصة كاملة (draft → submitted → won/lost) وتحويل المناقصة الفايزة لمشروع تنفيذي.
- **BOQ** (`boq.line` + `boq.line.progress`): جدول كميات هرمي (Chapter → Item) مع تتبع الإنجاز الدوري.
- **Variation Orders** (`boq.variation.order`): تعديل/إضافة بنود بعد الترسية، بموافقة مستويين.
- **Payment Certificates** (`boq.payment.certificate`): مستخلصات دورية بخصم ضمان + استرداد دفعة مقدمة، وإنشاء فاتورة فعلية.
- **Subcontractor cost tracking**: ربط `purchase.order` بالـ BOQ لحساب التكلفة الملتزم بيها.
- **Dashboards**: Cost Analysis (Contracted vs Committed vs Executed) وBilling Trend.

## التنصيب
1. انسخ الفولدر `nt_construction` جوه الـ custom addons path.
2. Update Apps List من Settings.
3. نصّب المديول من Apps.
4. روح Settings → Users وحط المستخدمين المناسبين في جروبات:
   - **Approver - Level 1 (Site/PM)**
   - **Approver - Level 2 (Finance/Management)**

من غير الخطوة دي محدش هيقدر يوافق على أي Variation Order أو Payment Certificate.

## طبقة الموافقة (Approval Workflow)
المحرك الأساسي للموافقات مكتوب بالكامل جوه المديول (`construction.approval.mixin`) — شغال 100% على أي نسخة أودو (CE أو Enterprise) بدون أي اعتماد خارجي، وفيه enforcement حقيقي جوه الـ Python (مش مجرد إخفاء زرار).

**لو عندك Studio (Enterprise)**، ممكن تضيف طبقة تدقيق إضافية (Studio Approval Rules) فوق نفس الأزرار للحصول على activity notifications وaudit trail جاهزين من أودو نفسه. الخطوات:
1. افتح أي فورم (Variation Order أو Payment Certificate) وادخل وضع Studio.
2. دوس على زرار "Approve (L1)" → أيقونة القفل → Add an Approval Rule → اختار جروب "Approver - Level 1".
3. كرر على "Final Approve (L2)" مع جروب "Approver - Level 2".
4. اختياري: نفس الشيء على زرار "Create Invoice" في المستخلص.

الطبقة دي **اختيارية وإضافية بس** — لو مش موجودة أو اتشالت، الـ workflow الأساسي فاضل شغال بالكامل.

## قبل التسليم للعميل — Checklist
- [ ] نصّب على قاعدة تجريبية (مش قاعدة عميل حقيقية) وراقب الـ log وقت التنصيب.
- [ ] اختبر دورة مناقصة كاملة لحد تحويلها لمشروع + نسخ الـ BOQ.
- [ ] اختبر BOQ هرمي (Chapter وبنود فرعية) وتأكد من صحة الإجماليات.
- [ ] اختبر Variation Order كامل: submit → L1 → L2 → تحديث الكمية والقيمة التعاقدية تلقائي.
- [ ] اختبر Payment Certificate كامل لحد إنشاء الفاتورة، وتأكد من صحة خصم الضمان.
- [ ] اختبر صلاحيات مستخدم عادي مقابل project manager.
- [ ] لو هتفعّل Studio Approval Rules، اختبرها بيوزرين مختلفين فعليًا.

## بنية الملفات
```
nt_construction/
├── models/          # كل الموديلات (tender, project inherit, boq, variation order, payment certificate, purchase inherit, approval mixin)
├── views/            # كل الفيوهات + المنيوهات
├── security/         # صلاحيات وجروبات
└── data/             # sequences
```
