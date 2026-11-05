# Token Usage and Model Call Report

HackerRank Orchestrate — Buy or Wait?
Final Evaluation Run Summary

## 1. Executive Summary

| Metric | Value |
|---|---|
| Execution Timestamp | 2026-11-05T18:06:39.517697Z |
| Total Requests Evaluated | 250 |
| Total Execution Time | 14.08 seconds |
| Average Execution Time / Request | 56.32 ms |
| Decision Engine Architecture | Deterministic Algorithmic Simulation Pipeline |
| Model Calls | 0 |
| Total Input Tokens | 0 |
| Total Output Tokens | 0 |
| Total Tokens | 0 |
| Average Tokens / Request | 0.0 |
| Estimated Total Cost | $0.00 |
| Estimated Cost / Request | $0.00 |

## 2. Model Calls Breakdown

| Provider | Model Name | Calls | Input Tokens | Output Tokens | Total Tokens | Est. Cost (USD) |
|---|---|---|---|---|---|---|
| None (Local Deterministic) | Rules & Cash-Flow Engine | 0 | 0 | 0 | 0 | $0.00 |
| **Total** | | **0** | **0** | **0** | **0** | **$0.00** |

## 3. Computational Methodology

The Buy or Wait? financial decision agent executes fully offline and deterministically without external LLM API inference calls during prediction time:

1. **Reconstruction & Disambiguation**: Deterministic date-indexed currency conversion, verified regex-anchored multilingual transaction parsing, and OCR receipt linkage.
2. **Cash Flow Simulation**: 90-day day-by-day cash flow ledger with strict debit-first intraday ordering and minimum required balance preservation.
3. **Multi-Plan Evaluation**: Combinatorial ranking over supplied vendor options, request-level partial plans, and up to 3 optional flexible spending changes.
4. **Reproducibility**: 100% deterministic, 0 API dependencies, 0 latency overhead, zero token expenditure.
