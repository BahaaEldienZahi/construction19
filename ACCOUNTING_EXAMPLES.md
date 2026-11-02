# Accounting examples — nt_construction 19.0.2.1.0

One project, real numbers. Each journal entry below is asserted **account by account (debit and
credit)** by a test in `nt_construction/tests/test_accounting_examples.py`
(class `TestAccountingExamples`). If code changes any number here, that test fails.

Run it:

```bash
./odoo-bin --addons-path=odoo/addons,addons,custom_addons -d agent_examples -i nt_construction \
  --test-tags /nt_construction:TestAccountingExamples --stop-after-init --http-port=8079
```

## 1. The project

| Term | Value | Where it is set |
|---|---|---|
| Company currency / contract currency | EGP / EGP | Company / project |
| Contract value | **10,000,000.00 EGP** | Project › Contract |
| BOQ item A — Concrete | 5,000 m³ × 1,200 = 6,000,000 | BOQ |
| BOQ item B — Reinforcement steel | 100 t × 40,000 = 4,000,000 | BOQ |
| Retention | 5 % of each certificate's gross (work **+ escalation**, P5) | Project |
| Advance payment | 10 % of the contract = 1,000,000, recovered **pro-rata**: 10 % of each certificate's work value | Project (Advance % and Advance Recovery %) |
| VAT | 14 % on the gross work value and on escalation (S12, P2); also on the advance and, negatively, on its recovery (S14) | Construction Settings |
| Withholding tax (client side) | 1 % of gross, booked on the invoice (S13) — *assumption: Egyptian contracting rate; the brief did not give one* | Construction Settings / project |
| Escalation (فروق أسعار) | factor = 0.15 + 0.50 × Steel/100 + 0.35 × Cement/200 − 1, threshold 5 % (not deducted) | Project › Escalation |
| Subcontractor | Steel, 100 t × 30,000, retention 5 %, VAT 14 % input, withholding 1 % | Subcontract agreement / Settings |

**Chart of accounts used by the test** (codes are configurable; these are created by the test):

| Code | Account | Type |
|---|---|---|
| 1121 | Clients | Receivable |
| 1125 | Retention Receivable | Current asset |
| 1126 | Withholding Tax Receivable | Current asset |
| 1127 | VAT Input | Current asset |
| 2111 | Subcontractors | Payable |
| 2121 | Customer Advances | Current liability |
| 2125 | Retention Payable | Current liability |
| 2131 | VAT Output | Current liability |
| 2132 | Withholding Tax Payable | Current liability |
| 4101 | Construction Revenue | Income |
| 5101 | Subcontract Cost | Expense |

**Order of events** (as in real life): a → b → c/d → g (certificate 2 is cancelled) → h (final
certificate) → f (retention release). e (subcontractor) is independent.

---

## a. Advance payment invoice

Project › **Create Advance Invoice** → customer invoice, 10 % × 10,000,000.

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 1,140,000.00 | |
| 2121 Customer Advances | | 1,000,000.00 |
| 2131 VAT Output (14 %) | | 140,000.00 |
| **Total** | **1,140,000.00** | **1,140,000.00** |

Advance to recover: 1,000,000.00.
Test: `test_a_advance_invoice`.

## b. Certificate 1 (current period)

Quantities to date: A 1,500 m³ (1,800,000), B 30 t (1,200,000) → **work 3,000,000.00**.
Indices at base (Steel 100, Cement 200) → escalation factor 0 → no escalation.

| Calculation | EGP |
|---|---:|
| Work this period | 3,000,000.00 |
| Retention 5 % | 150,000.00 |
| Advance recovery 10 % × 3,000,000 | 300,000.00 |
| VAT 14 % on work | 420,000.00 |
| VAT on recovery (−14 % × 300,000) | −42,000.00 |
| Withholding 1 % | 30,000.00 |
| **Net payable** = 3,000,000 + 420,000 − 42,000 − 30,000 − 150,000 − 300,000 | **2,898,000.00** |

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 2,898,000.00 | |
| 1125 Retention Receivable | 150,000.00 | |
| 1126 Withholding Tax Receivable | 30,000.00 | |
| 2121 Customer Advances (recovery) | 300,000.00 | |
| 2131 VAT Output (420,000 − 42,000) | | 378,000.00 |
| 4101 Construction Revenue | | 3,000,000.00 |
| **Total** | **3,378,000.00** | **3,378,000.00** |

Test: `test_b_certificate_1`.

## c. Certificate 2: previous / current / total

The QS enters the **total to date**; previous comes from approved certificates and is frozen at submission (S15, F2).

| Item | Previous qty | Current qty | Total qty | Previous EGP | Current EGP | Total EGP |
|---|---:|---:|---:|---:|---:|---:|
| A Concrete (1,200 / m³) | 1,500 | 1,500 | 3,000 | 1,800,000 | 1,800,000 | 3,600,000 |
| B Steel (40,000 / t) | 30 | 25 | 55 | 1,200,000 | 1,000,000 | 2,200,000 |
| **Work** | | | | **3,000,000** | **2,800,000** | **5,800,000** |

Only the **current** column is invoiced. Advance recovery 10 % × 2,800,000 = 280,000.
Advance left after certificate 2: 1,000,000 − 300,000 − 280,000 = 420,000.
Retention held: 150,000 + 148,470 = 298,470.
Test: `test_c_certificate_2_cumulative`.

## d. Escalation on certificate 2 (and its journal entry)

Indices this period: Steel 110, Cement 206.
factor = 0.15 + 0.50 × 110/100 + 0.35 × 206/200 − 1 = 0.15 + 0.55 + 0.3605 − 1 = **0.0605** (6.05 % > 5 % threshold → paid in full).

| Calculation | EGP |
|---|---:|
| Work this period | 2,800,000.00 |
| Escalation 6.05 % × 2,800,000 | 169,400.00 |
| **Gross** (VAT, withholding and retention base) | 2,969,400.00 |
| Retention 5 % × 2,969,400 (P5) | 148,470.00 |
| Advance recovery 10 % × 2,800,000 (work only) | 280,000.00 |
| VAT 14 % on work + escalation (392,000 + 23,716) | 415,716.00 |
| VAT on recovery (−14 % × 280,000) | −39,200.00 |
| Withholding 1 % × 2,969,400 | 29,694.00 |
| **Net payable** | **2,887,752.00** |

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 2,887,752.00 | |
| 1125 Retention Receivable | 148,470.00 | |
| 1126 Withholding Tax Receivable | 29,694.00 | |
| 2121 Customer Advances (recovery) | 280,000.00 | |
| 2131 VAT Output (415,716 − 39,200) | | 376,516.00 |
| 4101 Construction Revenue — work | | 2,800,000.00 |
| 4101 Construction Revenue — escalation | | 169,400.00 |
| **Total** | **3,345,916.00** | **3,345,916.00** |

Rule S7 holds: Certified = Invoiced = 5,969,400 (3,000,000 + 2,969,400), both without VAT and both including escalation.
Test: `test_d_certificate_2_escalation` (the two 4101 lines are asserted as their net, 2,969,400).

## e. Subcontractor certificate → vendor bill with retention

Steel subcontractor, certificate 1: 30 t × 30,000 = **900,000.00**.

| Calculation | EGP |
|---|---:|
| Work this period | 900,000.00 |
| VAT input 14 % | 126,000.00 |
| Withholding 1 % (we withhold, pay to the tax authority) | 9,000.00 |
| Retention 5 % (we hold it) | 45,000.00 |
| **Payable to subcontractor** = 900,000 + 126,000 − 9,000 − 45,000 | **972,000.00** |

| Account | Debit | Credit |
|---|---:|---:|
| 5101 Subcontract Cost (project analytic account) | 900,000.00 | |
| 1127 VAT Input | 126,000.00 | |
| 2132 Withholding Tax Payable | | 9,000.00 |
| 2125 Retention Payable | | 45,000.00 |
| 2111 Subcontractors | | 972,000.00 |
| **Total** | **1,026,000.00** | **1,026,000.00** |

Test: `test_e_subcontractor_bill`.

## g. Cancelling certificate 2 after its invoice is posted

Certificate › **Cancel & Reverse Invoice** (accountant). Odoo creates and posts a **credit note**
that mirrors the invoice and reconciles it with the invoice (invoice status: *Reversed*).

| Account | Debit | Credit |
|---|---:|---:|
| 4101 Construction Revenue | 2,969,400.00 | |
| 2131 VAT Output | 376,516.00 | |
| 1121 Clients | | 2,887,752.00 |
| 1125 Retention Receivable | | 148,470.00 |
| 1126 Withholding Tax Receivable | | 29,694.00 |
| 2121 Customer Advances | | 280,000.00 |
| **Total** | **3,345,916.00** | **3,345,916.00** |

After the cancellation the project is back where it was after certificate 1:

- certified quantity of item A is 1,500
- advance left to recover is 700,000
- retention held is 150,000
- Certified = Invoiced = 3,000,000

Rules (DECISIONS F12):

- only the **latest** approved certificate can be cancelled
- the invoice must be **unpaid**; unreconcile any payment first
- no retention may have been released on the project
- a cancelled, invoiced certificate cannot be reset to draft: a new certificate is issued

Tests:

- `test_g_cancel_certificate_2`: the credit note entry and the project position
- `test_g_cancel_rules`: an earlier certificate is blocked, and so is a paid invoice

## h. Final certificate

Ticked **Final Certificate** (F13). Final quantities to date: A 4,950 m³ (5,940,000; 50 m³ under contract), B 100 t (4,000,000) → total 9,940,000.
Previous = certificate 1 only (certificate 2 was cancelled) = 3,000,000 → **current 6,940,000**.
Same indices as certificate 2 → factor 0.0605.

| Calculation | EGP |
|---|---:|
| Work this period | 6,940,000.00 |
| Escalation 6.05 % | 419,870.00 |
| **Gross** | 7,359,870.00 |
| Retention 5 % × 7,359,870 | 367,993.50 |
| Advance recovery: **all that is left** (pro-rata would give 694,000) | 700,000.00 |
| VAT 14 % on work + escalation (971,600 + 58,781.80) | 1,030,381.80 |
| VAT on recovery (−14 % × 700,000) | −98,000.00 |
| Withholding 1 % × 7,359,870 | 73,598.70 |
| **Net payable** | **7,150,659.60** |

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 7,150,659.60 | |
| 1125 Retention Receivable | 367,993.50 | |
| 1126 Withholding Tax Receivable | 73,598.70 | |
| 2121 Customer Advances (recovery) | 700,000.00 | |
| 2131 VAT Output (1,030,381.80 − 98,000) | | 932,381.80 |
| 4101 Construction Revenue — work | | 6,940,000.00 |
| 4101 Construction Revenue — escalation | | 419,870.00 |
| **Total** | **8,292,251.80** | **8,292,251.80** |

After it, the advance left is 0.00 and retention held is 517,993.50 (150,000 + 367,993.50). No
further certificate can be submitted. Test: `test_h_final_certificate`.

## f. Retention release, stage 1 and stage 2

Handover: 50 % at provisional handover, 50 % at final handover (configurable). The base is the
retention on approved certificates, 517,993.50. Each stage is a customer invoice **without VAT**,
because VAT was already charged on the gross work (S12).

**Stage 1** (provisional handover):

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 258,996.75 | |
| 1125 Retention Receivable | | 258,996.75 |
| **Total** | **258,996.75** | **258,996.75** |

**Stage 2** (final handover, after the defects liability period):

| Account | Debit | Credit |
|---|---:|---:|
| 1121 Clients | 258,996.75 | |
| 1125 Retention Receivable | | 258,996.75 |
| **Total** | **258,996.75** | **258,996.75** |

Retention held after stage 2: 0.00. Test: `test_f_retention_release`.

---

## 2. Account balances at the end (client side)

| Account | Movements | Balance |
|---|---|---:|
| 2121 Customer Advances | Cr 1,000,000 (a), Dr 300,000 (b), Dr 280,000 (d), Cr 280,000 (g), Dr 700,000 (h) | **0.00** |
| 1125 Retention Receivable | Dr 150,000 (b), Dr 148,470 (d), Cr 148,470 (g), Dr 367,993.50 (h), Cr 258,996.75 × 2 (f) | **0.00** |
| 4101 Construction Revenue | 3,000,000 + 2,969,400 − 2,969,400 + 7,359,870 | **Cr 10,359,870.00** (work 9,940,000 + escalation 419,870) |

## 3. What is configurable, and what is provisional

- **Configurable:** every account and tax is chosen in *Construction › Configuration › Settings*. Nothing is hardcoded and nothing is created automatically (F9).
- **Provisional, waiting on the client** (DECISIONS §4):
  - escalation formula (P1)
  - VAT on escalation (P2)
  - retention on escalation (P5)
- **Agent decisions to review:**
  - F12: cancellation rules
  - F13: final certificate recovers the remaining advance
  - the 1 % withholding rate used here is an example, not a rule
