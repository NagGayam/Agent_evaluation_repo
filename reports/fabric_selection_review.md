# FABRIC selection review

Selected 120 records from 138 in-scope candidates; excluded 18. Reserved 15 guardrail records; 51 other records remain outside scope.

## Review boundary

This is a content selection for an educational RAG/evaluation demo, not approval of financial correctness or currency. No external primary-source fact check was performed. Original answers and references are preserved without correction. Selected records must not serve as verified financial ground truth.

The selection is explicit and deterministic by ID. No seed or random sampling is used. Difficulty counts are descriptive; no artificial difficulty quota was imposed.

The source dataset revision was not captured by the inspection report. The manifest records the source report SHA-256 for local provenance. Exports contain English fields only.

## Final allocation

| Category | Original target | Selected | Easy | Medium | Hard |
|---|---:|---:|---:|---:|---:|
| income_tax | 20 | 20 | 1 | 12 | 7 |
| banking_rbi | 18 | 18 | 5 | 11 | 2 |
| mutual_funds | 18 | 18 | 4 | 9 | 5 |
| stock_market | 16 | 17 | 2 | 5 | 10 |
| insurance | 14 | 14 | 4 | 6 | 4 |
| retirement | 14 | 14 | 3 | 6 | 5 |
| sebi_regulations | 12 | 12 | 1 | 7 | 4 |
| financial_literacy | 4 | 4 | 4 | 0 | 0 |
| employment_benefits | 4 | 3 | 0 | 2 | 1 |

Employment benefits drops from 4 to 3 because adv_015 is internally contradictory. Stock market rises from 16 to 17 to preserve the 120-record total.

## Excluded in-scope records

| ID | Category | Reason |
|---|---|---|
| bank_001 | banking_rbi | Question asks for current repo rate and EMI impact; a static dated rate snapshot and generic EMI estimate cannot reliably answer that moving target. |
| bank_012 | banking_rbi | Answer mixes Rs 7 lakh and Rs 10 lakh thresholds in the same explanation. LRS/TCS coverage remains in tax_023, whose claims still require verification. |
| adv_015 | employment_benefits | Internal contradiction: opening says the entire Rs 18 lakh is tax-free, but the calculation later says only about Rs 7.6 lakh is exempt. General gratuity coverage remains in ret_004. |
| tax_007 | income_tax | Filing and penalty answer is not tied to a clear assessment year and mixes multiple deadline thresholds; defer rather than use as a clean reference. |
| tax_012 | income_tax | Complex assertion about agricultural-income integration across tax regimes needs primary-source validation; defer from the small demo. |
| tax_016 | income_tax | Answer introduces a per-property interest cap without resolving aggregate limits or tax-regime conditions; defer this ambiguous reference. |
| tax_018 | income_tax | Cross-border treaty, residency and Form 67 timing conditions add specialist complexity; defer to a later verified subset. |
| tax_025 | income_tax | Internal arithmetic failure: listed slab components sum to Rs 12,30,000, not the stated Rs 16,30,000. Downstream surcharge and cess use the inconsistent total. |
| ins_015 | insurance | Health-claim answer invokes Section 45 and mixes several waiting-period timelines without clearly separating insurance types; defer pending specialist verification. |
| mf_005 | mutual_funds | Internally inconsistent indexation explanation: says grandfathered units retain indexation, then says indexation was removed, then offers an election. Defer pending correction and verification. |
| mf_007 | mutual_funds | Answer first states there is no TDS on resident equity SWP, then adds a conflicting TDS exception. Defer this internally inconsistent reference. |
| ret_015 | retirement | Direct-annuity section separates return of capital from income, then the later summary says India taxes annuity income unlike countries that separate capital. The unresolved distinction weakens the reference. |
| sebi_002 | sebi_regulations | Question requests a maximum blended TER, but answer provides only an approximation and incomplete slab workings; expense-ratio concepts remain covered in mf_011. |
| sebi_004 | sebi_regulations | Near-duplicate of market-wide circuit-breaker coverage in stock_002; retain one reference to reduce retrieval redundancy. |
| sebi_014 | sebi_regulations | SME IPO eligibility and market-making mechanics are relatively niche and multi-condition; prioritize everyday investor topics for the initial demo. |
| stock_006 | stock_market | F&O reform coverage overlaps sebi_006; also includes changing index lot-size snapshots. Keep the margin-focused record rather than both. |
| stock_008 | stock_market | Combines off-market gifts, fair-value rules and subsequent-sale STT eligibility into broad conclusions; too many unresolved conditions for this small reference set. |
| stock_010 | stock_market | Weekly-expiry coverage overlaps sebi_006 and includes changing weekday schedules and later algo requirements; omit the duplicate moving-target record. |

## Selected record decisions

| ID | Category | Difficulty | Retained coverage |
|---|---|---|---|
| bank_002 | banking_rbi | medium | fd_rules |
| bank_003 | banking_rbi | easy | upi_limits |
| bank_004 | banking_rbi | medium | deposit_insurance |
| bank_005 | banking_rbi | medium | loan_prepayment |
| bank_006 | banking_rbi | medium | nbfc_vs_bank |
| bank_007 | banking_rbi | medium | gold_loan |
| bank_008 | banking_rbi | medium | digital_lending |
| bank_009 | banking_rbi | easy | rtgs_neft_imps |
| bank_010 | banking_rbi | hard | priority_sector |
| bank_011 | banking_rbi | medium | mclr_vs_eblr |
| bank_013 | banking_rbi | hard | sarfaesi_act |
| bank_014 | banking_rbi | medium | banking_ombudsman |
| bank_015 | banking_rbi | easy | dormant_account |
| bank_016 | banking_rbi | medium | education_loan |
| bank_017 | banking_rbi | easy | credit_score_cibil |
| bank_018 | banking_rbi | easy | recurring_deposit |
| bank_019 | banking_rbi | medium | cash_transaction_limits |
| bank_020 | banking_rbi | medium | card_tokenization |
| adv_013 | employment_benefits | hard | vrs_taxation |
| adv_014 | employment_benefits | medium | leave_encashment |
| adv_016 | employment_benefits | medium | relocation_allowance |
| adv_017 | financial_literacy | easy | leverage_investing |
| adv_018 | financial_literacy | easy | mis_selling |
| adv_019 | financial_literacy | easy | short_term_parking |
| adv_020 | financial_literacy | easy | debt_repayment |
| tax_001 | income_tax | easy | section_80c |
| tax_002 | income_tax | medium | old_vs_new_regime |
| tax_003 | income_tax | medium | ltcg |
| tax_004 | income_tax | medium | stcg |
| tax_005 | income_tax | hard | hra |
| tax_006 | income_tax | medium | section_80d |
| tax_008 | income_tax | hard | nri_taxation |
| tax_009 | income_tax | medium | new_regime_deductions |
| tax_010 | income_tax | medium | crypto_tax |
| tax_011 | income_tax | medium | gift_tax |
| tax_013 | income_tax | medium | advance_tax |
| tax_014 | income_tax | medium | section_80e |
| tax_015 | income_tax | hard | section_80g |
| tax_017 | income_tax | hard | capital_loss_setoff |
| tax_019 | income_tax | medium | presumptive_taxation |
| tax_020 | income_tax | medium | senior_citizen_benefits |
| tax_021 | income_tax | medium | income_other_sources |
| tax_022 | income_tax | hard | section_54 |
| tax_023 | income_tax | hard | tcs_lrs |
| tax_024 | income_tax | hard | esop_taxation |
| ins_001 | insurance | easy | term_vs_endowment |
| ins_002 | insurance | hard | tax_benefits_80c_10_10d |
| ins_003 | insurance | medium | health_insurance_portability |
| ins_004 | insurance | medium | pre_existing_disease_waiting |
| ins_005 | insurance | medium | claim_settlement_ratio |
| ins_006 | insurance | medium | irdai_standard_products |
| ins_007 | insurance | easy | group_vs_individual |
| ins_008 | insurance | easy | motor_insurance |
| ins_009 | insurance | hard | ulip_charges_lockin |
| ins_010 | insurance | hard | nomination_vs_will |
| ins_011 | insurance | easy | cashless_vs_reimbursement |
| ins_012 | insurance | medium | copay_sublimits |
| ins_013 | insurance | medium | critical_illness_rider_vs_standalone |
| ins_014 | insurance | hard | irdai_use_and_file |
| mf_001 | mutual_funds | medium | elss_lock_in_and_tax |
| mf_002 | mutual_funds | hard | sip_vs_lumpsum_taxation |
| mf_003 | mutual_funds | medium | exit_load_rules |
| mf_004 | mutual_funds | easy | direct_vs_regular_plan |
| mf_006 | mutual_funds | medium | switching_tax_implications |
| mf_008 | mutual_funds | medium | idcw_vs_growth |
| mf_009 | mutual_funds | medium | nomination_rules |
| mf_010 | mutual_funds | easy | nfo_investor_awareness |
| mf_011 | mutual_funds | medium | index_fund_vs_active_expense_ratio |
| mf_012 | mutual_funds | medium | gilt_funds_interest_rate_risk |
| mf_013 | mutual_funds | hard | international_fund_taxation_post_2023 |
| mf_014 | mutual_funds | hard | fund_of_funds_taxation |
| mf_015 | mutual_funds | hard | side_pocketing_sebi_rules |
| mf_016 | mutual_funds | medium | liquid_fund_vs_savings_account |
| mf_017 | mutual_funds | hard | target_maturity_funds |
| mf_018 | mutual_funds | medium | multicap_vs_flexicap_sebi_rules |
| mf_019 | mutual_funds | easy | overnight_fund_safety |
| mf_020 | mutual_funds | easy | kyc_ckyc_requirements |
| ret_001 | retirement | medium | epf_contribution |
| ret_002 | retirement | medium | ppf |
| ret_003 | retirement | hard | nps_tax_benefits |
| ret_004 | retirement | medium | gratuity |
| ret_005 | retirement | hard | eps_pension |
| ret_006 | retirement | medium | epf_withdrawal |
| ret_007 | retirement | hard | ppf_extension |
| ret_008 | retirement | hard | nps_annuity |
| ret_009 | retirement | medium | vpf |
| ret_010 | retirement | hard | superannuation |
| ret_011 | retirement | easy | epfo_online_claims |
| ret_012 | retirement | easy | atal_pension_yojana |
| ret_013 | retirement | easy | scss |
| ret_014 | retirement | medium | pmvvy |
| sebi_001 | sebi_regulations | medium | insider_trading |
| sebi_003 | sebi_regulations | medium | ipo_allotment |
| sebi_005 | sebi_regulations | medium | finfluencer_regulations |
| sebi_006 | sebi_regulations | hard | fo_margin_requirements |
| sebi_007 | sebi_regulations | hard | delisting_regulations |
| sebi_008 | sebi_regulations | easy | scores_platform |
| sebi_009 | sebi_regulations | hard | buyback_regulations |
| sebi_010 | sebi_regulations | medium | reit_invit_regulations |
| sebi_011 | sebi_regulations | medium | new_asset_class |
| sebi_012 | sebi_regulations | medium | investor_protection_fund |
| sebi_013 | sebi_regulations | hard | algo_trading_retail |
| sebi_015 | sebi_regulations | medium | dispute_resolution |
| stock_001 | stock_market | medium | settlement_cycle |
| stock_002 | stock_market | hard | circuit_breakers |
| stock_003 | stock_market | easy | demat_account |
| stock_004 | stock_market | hard | stt |
| stock_005 | stock_market | hard | intraday_vs_delivery_tax |
| stock_007 | stock_market | hard | corporate_actions_tax |
| stock_009 | stock_market | hard | pledge_unpledge_margin |
| stock_011 | stock_market | hard | rights_issue |
| stock_012 | stock_market | hard | dividend_taxation |
| stock_013 | stock_market | hard | share_buyback_taxation |
| stock_014 | stock_market | medium | individual_stock_circuit_limits |
| stock_015 | stock_market | medium | block_deal_bulk_deal |
| stock_016 | stock_market | medium | asba_ipo |
| stock_017 | stock_market | hard | stock_lending_borrowing |
| stock_018 | stock_market | hard | multi_asset_allocation |
| stock_019 | stock_market | medium | listing_gains_taxation |
| stock_020 | stock_market | easy | trading_holidays_market_timing |

## Follow-up before evaluation

Review overlapping retained topics for conflicting answers, especially tax thresholds, NPS exits, nomination, and insurance waiting periods. A nonblank source description does not establish validity.

Use separate paraphrased evaluation questions supported by the KB and label unsupported requests for abstention. Excluded records are not automatically unanswerable: their knowledge may overlap the selected KB. Guardrail references are not automatically correct evaluator instructions.

## Artifacts

- data/fabric_kb_120.jsonl: selected English Q&A and metadata; financial verification remains pending.
- data/fabric_selection.json: all 204 decisions, reasons, quotas and source report hash.
- data/fabric_guardrails_15.jsonl: separate original safety review pool.
- reports/fabric_candidates.md: original full inspection report, left unchanged.
