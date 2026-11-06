# Buy or Wait? — AI-Powered Financial Affordability Decision Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/visualizations-Plotly-3F4F75.svg)](https://plotly.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![HackerRank Orchestrate](https://img.shields.io/badge/HackerRank-Orchestrate%202026-00EA64.svg)](https://www.hackerrank.com/)

An intelligent, deterministic financial decision-support engine and interactive Streamlit analytics platform developed for the **HackerRank Orchestrate (September 2026)** hackathon challenge: *Buy or Wait?*.

The system evaluates discretionary purchase and payment requests by simulating 90-day cash flow trajectories, reconciling multimodal evidence (text messages and invoice images), optimizing provider installment options and flexible expense adjustments, and enforcing conservative liquidity guardrails.

---

## Table of Contents

- [Problem Overview](#problem-overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Directory Structure](#project-directory-structure)
- [Core Modules Breakdown](#core-modules-breakdown)
- [Streamlit Dashboard Pages](#streamlit-dashboard-pages)
- [Dataset Inventory](#dataset-inventory)
- [Decision Logic & Golden Invariants](#decision-logic--golden-invariants)
- [Output Specification & Summary Results](#output-specification--summary-results)
- [Installation & Setup (Windows PowerShell)](#installation--setup-windows-powershell)
- [Execution Commands](#execution-commands)
- [Testing & Validation](#testing--validation)
- [Performance & Computational Telemetry](#performance--computational-telemetry)
- [Limitations & Future Roadmap](#limitations--future-roadmap)
- [Hackathon Context & Disclaimer](#hackathon-context--disclaimer)

---

## Problem Overview

When a user asks: **"Can I afford this laptop?"**, a simple current bank balance check is dangerously insufficient. Answering accurately requires answering a deeper set of questions:

1. **What recurring commitments exist?** Rent, utilities, loan repayments, and insurance must be serviced on time.
2. **What pending transactions are outstanding?** Pending debits reduce available liquidity immediately, whereas unconfirmed income, refunds, and investment gains must not be counted prematurely.
3. **What is the user's safety margin?** The user's account balance must never fall below their configured `minimum_balance_to_keep`.
4. **What payment structures exist?** Can the expense be converted into low-cost seller installments without violating the user's installment horizon limits?
5. **Can discretionary spending be paused?** If the purchase is unaffordable today, can non-essential subscriptions or dining expenses be temporarily reduced?

The **Buy or Wait?** engine reconstructs the user's complete financial state, models daily cash flows across 90 days, and recommends one of five concrete payment actions alongside a personalized, fully costed repayment plan.

---

## Key Features

- **90-Day Deterministic Cash Flow Simulation:** Projects daily closing balances factoring in fixed dated exchange rates, verified salary cycles, scheduled recurring debits, and essential variable spending.
- **Multimodal Evidence Reconciler:** Extracts missing transaction amounts from invoice/receipt images and parses contextual natural-language communications (salary delays, cancellations, refunds) to eliminate data gaps.
- **Provider Payment Plan Optimizer:** Evaluates seller installment terms (tenures, interest rates, down payments, fees) against user preferences and limits.
- **Discretionary Spending Reduction Optimizer:** Explores combinations of up to three non-protected flexible expense cuts (`stop` or `reduce_to`) to render borderline purchases feasible.
- **Zero-Hallucination Decision Generator:** Emits concise, audit-grounded explanations justifying every decision with real dates, balances, and expense items.
- **Interactive Fintech Analytics Dashboard:** A 7-page Streamlit suite featuring Plotly cash flow trajectories, repayment waterfalls, searchable prediction catalogs, and full telemetry.

---

## System Architecture

```text
                                  +---------------------------------------+
                                  |            Dataset Inputs             |
                                  |  - requests.csv (250)                 |
                                  |  - financial_profiles.csv (275)       |
                                  |  - financial_events.csv (25,342)      |
                                  |  - exchange_rates.csv (134)           |
                                  |  - request_payment_options.csv (790)  |
                                  |  - messages.csv & images.csv (231)    |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  | Module 1: Data Loader & Validator     |
                                  | (Schema check, currency normalization)|
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  | Module 2: Financial State Reconstruct |
                                  | (Reserve debits, reconcile evidence)  |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  | Module 3: 90-Day Cash Flow Engine     |
                                  | (Daily balance simulation, min-guard) |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  | Module 4: Affordability Engine        |
                                  | (Binary-search safe amount, earliest) |
                                  +---------+-------------------+---------+
                                            |                   |
                     Affordable Now?        |                   | Needs Plan / Later?
                           +----------------+                   +----------------+
                           v                                                     v
          +---------------------------------+                  +---------------------------------+
          | Safe to Pay == Requested Amount |                  | Module 5: Payment Plan Optimizer|
          | Status: affordable_now          |                  | (Seller installments, partials) |
          | Method: full_payment            |                  +----------------+----------------+
          +---------------------------------+                                   |
                                                                                v
                                                               +---------------------------------+
                                                               | Module 6: Spending Optimizer    |
                                                               | (Combinatorial flexible cuts)   |
                                                               +----------------+----------------+
                                                                                |
                                            +-----------------------------------+
                                            v
                            +---------------------------------------+
                            | Module 7: Decision Pipeline           |
                            | (Synthesize optimal plan & status)    |
                            +-------------------+-------------------+
                                                |
                                                v
                            +---------------------------------------+
                            | Module 8: Explanation Generator       |
                            | (Audit-grounded factual justification)|
                            +-------------------+-------------------+
                                                |
                                                v
                            +---------------------------------------+
                            | Module 9: Output Validation Engine    |
                            | (Verify bounds, enums, 8-col schema)  |
                            +-------------------+-------------------+
                                                |
                                                v
                            +---------------------------------------+
                            | output.csv (250 validated rows)       |
                            | Streamlit Dashboard (7 pages)         |
                            +---------------------------------------+
```

---

## Project Directory Structure

```text
hackerrank-orchestrate-september26-1/
├── .gitignore                          # Standard Python, virtualenv, and IDE exclusions
├── AGENTS.md                           # Hackathon operational specification and agent rules
├── CLAUDE.md                           # Compatibility pointer to AGENTS.md
├── code.zip                            # Official packaged submission archive
├── log.txt                             # Audit log of agent sessions and turn summaries
├── main.py                             # Root convenience wrapper executing code/main.py
├── output.csv                          # Generated predictions (250 rows, 8 required columns)
├── problem_statement.md                # Official challenge problem statement
├── README.md                           # Project documentation
├── requirements.txt                    # Python package dependencies
│
├── code/                               # Core Financial Decision Engine (10 Modules)
│   ├── __init__.py
│   ├── main.py                         # Standalone CLI entry point for the pipeline
│   ├── data_loader.py                  # Module 1: Ingestion, schema validation, currency mapping
│   ├── financial_state.py              # Module 2: State reconstruction, recurring detection, evidence
│   ├── cash_flow_engine.py             # Module 3: 90-day conservative cash flow simulation
│   ├── affordability_engine.py         # Module 4: Safe amount calculation, status determination
│   ├── payment_plan_optimizer.py       # Module 5: Provider installment and partial-payment evaluation
│   ├── spending_changes_optimizer.py   # Module 6: Flexible discretionary expense reduction optimizer
│   ├── decision_pipeline.py            # Module 7: Orchestration pipeline for all 250 requests
│   ├── explanation_generator.py        # Module 8: Deterministic factual rationale generator
│   ├── validation_engine.py            # Module 9: Schema, invariant, and constraint enforcement
│   └── test_decision_pipeline.py       # Module 10: 16-suite unit and integration test framework
│
├── dashboard/                          # Streamlit Analytics & Demonstration Platform
│   ├── __init__.py
│   ├── app.py                          # Main dashboard launcher and navigation config
│   ├── components/                     # Reusable UI widgets and charting components
│   │   ├── __init__.py
│   │   ├── cards.py                    # KPI cards, badges, and status chips
│   │   ├── charts.py                   # Plotly cash flow curves, breakdowns, waterfall charts
│   │   └── sidebar.py                  # Navigation sidebar and active request selector
│   ├── pages/                          # Multi-page dashboard views
│   │   ├── 1_overview.py               # Executive KPIs and currency distribution table
│   │   ├── 2_decision_explorer.py      # Detailed transaction and profile inspector
│   │   ├── 3_cash_flow_forecast.py     # 90-day balance forecast with transaction markers
│   │   ├── 4_payment_plan_optimizer.py # Provider options comparison & fee breakdown
│   │   ├── 5_spending_optimization.py  # Discretionary spending reduction simulator
│   │   ├── 6_all_predictions.py        # 250-row searchable catalog and CSV export
│   │   └── 7_system_info.py            # Architecture documentation and telemetry report
│   └── utils/
│       ├── __init__.py
│       └── data_loader.py              # Streamlit cached data loading and merging utilities
│
├── dataset/                            # Hackathon Data Warehouse
│   ├── requests.csv                    # 250 evaluation requests to predict
│   ├── sample_requests.csv             # 25 solved sample requests with reference output
│   ├── financial_profiles.csv          # 275 user financial profiles, limits, preferences
│   ├── financial_events.csv            # 25,342 historical, pending, and scheduled transactions
│   ├── request_payment_options.csv     # 790 provider installment and payment options
│   ├── exchange_rates.csv              # 134 fixed dated foreign currency conversion rates
│   ├── messages.csv                    # 215 user communication records (bilingual EN/ID)
│   ├── images.csv                      # 16 invoice and receipt image metadata mappings
│   ├── media/images/                   # 16 PNG invoice and document images
│   └── output.csv                      # Blank official prediction template
│
└── evaluation/                         # Evaluation & Telemetry Artifacts
    └── usage_report.md                 # Token, model call, and computational cost summary
```

---

## Core Modules Breakdown

| Module | File | Primary Responsibility |
|---|---|---|
| **Module 1** | `code/data_loader.py` | Validates column schemas, parses dates, maps foreign currencies to fixed rates in `exchange_rates.csv`, and merges user profile constraints. |
| **Module 2** | `code/financial_state.py` | Reconstructs liquidity positions: identifies recurring expenses, reserves pending debit holds, counts confirmed salary on settlement dates, and extracts OCR invoice totals. |
| **Module 3** | `code/cash_flow_engine.py` | Runs conservative 90-day forward simulations with daily resolution. Tracks running balances against `minimum_balance_to_keep`. |
| **Module 4** | `code/affordability_engine.py` | Computes `amount_safe_to_pay` on `request_date` via discrete simulation. Identifies `earliest_date_for_full_payment` and assigns baseline affordability statuses. |
| **Module 5** | `code/payment_plan_optimizer.py` | Evaluates options in `request_payment_options.csv`. Checks installment tenures against `max_installment_months` and constructs two-payment partial schedules. |
| **Module 6** | `code/spending_changes_optimizer.py` | Explores combinations of up to 3 discretionary expense reductions (`stop:<id>` or `reduce_to:<id>:<amount>`), strictly respecting protected categories. |
| **Module 7** | `code/decision_pipeline.py` | Master orchestrator coordinating data ingestion, per-request evaluation, spending optimization, and final output writing. |
| **Module 8** | `code/explanation_generator.py` | Formulates clear, deterministic justifications citing specific balances, dates, expense categories, and provider terms. |
| **Module 9** | `code/validation_engine.py` | Enforces all 12 hard output constraints (boundary bounds, date formats, non-null values, valid enums, plan cost conservation). |
| **Module 10** | `code/test_decision_pipeline.py` | Comprehensive test suite containing 16 unit and end-to-end integration tests verifying algorithmic correctness. |

---

## Streamlit Dashboard Pages

The dashboard provides an intuitive, fintech-styled demonstration interface built with Streamlit and Plotly:

1. **Executive Overview (`1_overview.py`)**: Top-level portfolio metrics, affordability status breakdown cards, recommended payment method distributions, and a multi-currency transaction breakdown table (INR, EUR, IDR, ZAR, USD).
2. **Purchase Decision Explorer (`2_decision_explorer.py`)**: Individual request inspector displaying user financial profiles, liquid balances, reserved pending transactions, and step-by-step decision rationales.
3. **90-Day Cash Flow Forecast (`3_cash_flow_forecast.py`)**: High-resolution daily balance trajectories with interactive Plotly curves, minimum balance threshold lines, and discrete debit/credit transaction markers.
4. **Payment Plan Optimizer (`4_payment_plan_optimizer.py`)**: Provider installment plan evaluator comparing tenures, down payments, total financing costs, and repayment schedules.
5. **Spending Optimization (`5_spending_optimization.py`)**: Interactive simulation tool showing before-and-after cash flow trajectories when flexible expenses are paused or reduced.
6. **All Predictions Catalog (`6_all_predictions.py`)**: 250-row interactive evaluation table featuring multi-dimensional filtering (status, payment method, amount ranges), search by request ID or explanation, and official CSV exports.
7. **System Information (`7_system_info.py`)**: In-depth technical documentation across 6 tabs detailing pipeline architecture, dataset statistics, golden invariants, test suite results, and execution telemetry.

---

## Dataset Inventory

| File | Rows | Description |
|---|---|---|
| `dataset/requests.csv` | 250 | Evaluation requests specifying user ID, requested amount, category, request date, and deadline. |
| `dataset/sample_requests.csv` | 25 | Ground-truth reference examples illustrating expected decision formats and reasoning style. |
| `dataset/financial_profiles.csv` | 275 | User profiles defining home currency, liquid balance, minimum balance, priorities, and installment limits. |
| `dataset/financial_events.csv` | 25,342 | Historical, pending, scheduled, and settled financial events across 5 currencies. |
| `dataset/request_payment_options.csv` | 790 | Seller payment and financing options (2 to 4 options per request). |
| `dataset/exchange_rates.csv` | 134 | Fixed, dated foreign currency conversion rates (USD, EUR, INR, ZAR, IDR). |
| `dataset/messages.csv` | 215 | Bilingual communication logs containing salary confirmations, cancellations, and merchant updates. |
| `dataset/images.csv` | 16 | Metadata linking missing transaction amounts in `financial_events.csv` to invoice images. |
| `dataset/media/images/` | 16 PNGs | Invoice and receipt images containing resolved transaction values. |
| `dataset/output.csv` | 250 | Blank prediction template defining the 8 required output columns. |

---

## Decision Logic & Golden Invariants

The pipeline enforces four foundational financial invariants across every prediction:

1. **Liquidity Preservation Invariant:** The projected closing cash balance must **never** drop below `minimum_balance_to_keep` on any day across the 90-day simulation window.
2. **Conservative Cash Flow Invariant:** Pending debits are reserved immediately; unconfirmed income, bonus promises, commissions, lottery proceeds, and unrealized investment gains are strictly excluded until settled.
3. **Plan Feasibility Invariant:** Installment recommendations must match an available provider option from `request_payment_options.csv` and comply with the user's `max_installment_months`. Partial payment schedules must complete on or before `desired_completion_date`.
4. **Protected Category Invariant:** Discretionary spending modifications (`stop` or `reduce_to`) may only target flexible, recurring events in categories the user has explicitly designated as adjustable.

---

## Output Specification & Summary Results

### Required Output Schema

The submission produces `output.csv` with exactly 250 rows and the following 8 columns:

```text
request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation
```

- `amount_safe_to_pay`: Maximum safe payment on `request_date` before spending changes ($0 \le \text{safe} \le \text{requested}$).
- `affordability_status`: `affordable_now` | `affordable_with_plan` | `affordable_later` | `not_affordable`.
- `recommended_payment_method`: `full_payment` | `partial_payment` | `installments` | `wait` | `not_recommended`.
- `payment_plan`: Chronological `YYYY-MM-DD:amount` entries separated by `|`, or `none`.
- `earliest_date_for_full_payment`: First projected date safe for a single full payment; blank if unfeasible within 90 days.
- `spending_changes_needed`: Up to three `stop:<event_id>` or `reduce_to:<event_id>:<amount>` actions, or `none`.
- `decision_explanation`: Grounded, factual explanation citing relevant numbers, dates, and constraints.

### 250-Request Prediction Distribution

```text
================================================================================
PREDICTION SUMMARY BREAKDOWN (250 EVALUATION REQUESTS)
================================================================================

Affordability Status:
  - affordable_now           :   82 (32.8%)
  - affordable_with_plan      :   74 (29.6%)
  - affordable_later          :   57 (22.8%)
  - not_affordable            :   37 (14.8%)

Recommended Payment Method:
  - full_payment              :   82 (32.8%)
  - installments              :   67 (26.8%)
  - wait                      :   57 (22.8%)
  - not_recommended           :   37 (14.8%)
  - partial_payment           :    7 ( 2.8%)

Spending Changes Required     :   20 ( 8.0%)
Constraint Violations / Nulls :    0 ( 0.0%)
```

---

## Installation & Setup (Windows PowerShell)

### Prerequisites

- **Python:** Version 3.10, 3.11, or 3.12 (Python 3.11 recommended).
- **Git:** Installed and available on system `PATH`.
- **PowerShell:** Standard Windows PowerShell terminal.

### Step 1: Clone the Repository

```powershell
git clone https://github.com/interviewstreet/hackerrank-orchestrate-september26.git
cd hackerrank-orchestrate-september26-1
```

### Step 2: Create and Activate Virtual Environment

```powershell
# Create virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

*(If script execution is restricted on your system, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies

```powershell
pip install -r requirements.txt
```

---

## Execution Commands

### 1. Run the Decision Pipeline (Generate Predictions)

Execute the end-to-end pipeline to process all 250 requests and write `output.csv`:

```powershell
# Using the module entry point (recommended)
python code/main.py

# Or using the root convenience wrapper
python main.py
```

### 2. Launch the Streamlit Analytics Dashboard

Start the interactive dashboard locally:

```powershell
python -m streamlit run dashboard/app.py
```

Open your browser at `http://localhost:8501` to explore the dashboard.

### 3. Run Automated Tests

Execute the 16-suite unit and integration test framework:

```powershell
python code/test_decision_pipeline.py
```

---

## Testing & Validation

The solution includes an extensive verification suite in `code/test_decision_pipeline.py`:

```powershell
.\.venv\Scripts\python.exe code/test_decision_pipeline.py
```

**Test Coverage Summary:**
- `test_data_loader`: Validates dataset completeness, column names, and date parsing.
- `test_exchange_rates`: Confirms fixed conversion rates for USD, EUR, INR, ZAR, and IDR.
- `test_financial_state_reconstruction`: Verifies balance reconciliation, debit holds, and OCR image amount extraction.
- `test_recurring_expenses`: Confirms monthly/biweekly cadence detection from historical transactions.
- `test_cash_flow_engine`: Tests 90-day cash flow simulation against known deposits and debits.
- `test_minimum_balance_guard`: Verifies that plans violating minimum balances are rejected.
- `test_affordability_binary_search`: Tests convergence of `amount_safe_to_pay`.
- `test_payment_plan_optimizer`: Evaluates installment matching and tenure limits.
- `test_spending_optimizer`: Verifies combinatorial flexible expense reductions.
- `test_end_to_end_pipeline`: Runs complete prediction generation on test batches.
- `test_output_schema`: Asserts exact 8-column layout and non-null constraints.
- `test_affordability_invariants`: Tests math boundaries: $0 \le \text{safe} \le \text{requested}$.

**Result: 16 / 16 Tests Passed (100% Pass Rate).**

---

## Performance & Computational Telemetry

Per hackathon guidelines, all execution metrics are formally audited in `evaluation/usage_report.md`:

- **Execution Model:** 100% deterministic, offline, algorithmic simulation engine.
- **External Model Calls:** 0
- **Total LLM Tokens:** 0
- **Total Inference Cost:** $0.00
- **Pipeline Runtime (250 Requests):** ~14.08 seconds (56.3 ms / request).
- **Memory Footprint:** < 150 MB RAM.

Because the system operates deterministically without relying on third-party API availability, rate limits, or network latency, predictions are instantaneous, repeatable, and completely private.

---

## Limitations & Future Roadmap

While the deterministic simulation engine is robust and compliant with all challenge criteria, future extensions could incorporate:

1. **Probabilistic Income Modeling:** Upgrading from conservative settlement dates to Monte Carlo cash flow forecasting for freelance/gig economy workers with variable income.
2. **Local Multi-Modal Vision Model (VLM):** Integrating an on-device OCR model (e.g., Donut or Florence-2) to dynamically parse arbitrary user invoices and salary slips beyond the curated metadata set.
3. **Tax & Currency Inflation Forecasts:** Incorporating macroeconomic inflation trends and tax withholding projections for longer forecast horizons (> 180 days).
4. **Automated Bank Sync (Open Banking / Plaid):** Connecting live account feeds via PSD2 / Open Banking APIs for continuous, real-time liquidity tracking.

---

## Hackathon Context & Disclaimer

This project was built for **HackerRank Orchestrate (September 2026)** under the *Buy or Wait?* challenge track.

**Disclaimer:** This software is an algorithmic proof-of-concept for educational and competition purposes. It does not constitute certified financial advice. Users should consult a qualified financial planner before making significant purchasing or financing decisions.
