"""
Data loading and caching utilities for the Streamlit dashboard.
Safe read-only access to datasets and pipeline models.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_CSV_PATH = ROOT_DIR / "output.csv"
BACKUP_OUTPUT_CSV_PATH = ROOT_DIR / "dataset" / "output.csv"
REQUESTS_CSV_PATH = ROOT_DIR / "dataset" / "requests.csv"
PROFILES_CSV_PATH = ROOT_DIR / "dataset" / "financial_profiles.csv"
EVENTS_CSV_PATH = ROOT_DIR / "dataset" / "financial_events.csv"
PAYMENT_OPTIONS_CSV_PATH = ROOT_DIR / "dataset" / "request_payment_options.csv"


@st.cache_data(show_spinner="Loading predictions...")
def load_predictions_data() -> pd.DataFrame:
    """Load the predictions output.csv with validation."""
    target_path = OUTPUT_CSV_PATH if OUTPUT_CSV_PATH.exists() else BACKUP_OUTPUT_CSV_PATH
    if not target_path.exists():
        st.error(f"Predictions file not found at {OUTPUT_CSV_PATH}")
        return pd.DataFrame()
    df = pd.read_csv(target_path)
    # Ensure amount_safe_to_pay is numeric
    if "amount_safe_to_pay" in df.columns:
        df["amount_safe_to_pay"] = pd.to_numeric(df["amount_safe_to_pay"], errors="coerce").fillna(0.0)
    return df


@st.cache_data(show_spinner="Loading evaluation requests...")
def load_requests_data() -> pd.DataFrame:
    """Load dataset/requests.csv."""
    if not REQUESTS_CSV_PATH.exists():
        st.error(f"Requests file not found at {REQUESTS_CSV_PATH}")
        return pd.DataFrame()
    df = pd.read_csv(REQUESTS_CSV_PATH)
    if "requested_amount" in df.columns:
        df["requested_amount"] = pd.to_numeric(df["requested_amount"], errors="coerce").fillna(0.0)
    return df


@st.cache_data(show_spinner="Loading user profiles...")
def load_profiles_data() -> pd.DataFrame:
    """Load dataset/financial_profiles.csv."""
    if not PROFILES_CSV_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(PROFILES_CSV_PATH)


@st.cache_data(show_spinner="Merging decision datasets...")
def load_merged_data() -> pd.DataFrame:
    """Merge output.csv with requests.csv for rich analytics."""
    pred_df = load_predictions_data()
    req_df = load_requests_data()
    
    if pred_df.empty or req_df.empty:
        return pred_df
        
    merged = pd.merge(pred_df, req_df, on="request_id", how="left")
    
    # Calculate difference and affordability coverage
    if "requested_amount" in merged.columns and "amount_safe_to_pay" in merged.columns:
        merged["safe_to_pay_pct"] = (
            (merged["amount_safe_to_pay"] / merged["requested_amount"].replace(0, 1)) * 100
        ).clip(0, 100)
    return merged


@st.cache_resource(show_spinner="Initializing Financial Decision Engine...")
def get_decision_pipeline():
    """Lazily load the underlying DecisionPipeline for detailed cash flow lookups."""
    try:
        from code.decision_pipeline import DecisionPipeline
        pipeline = DecisionPipeline(data_dir=str(ROOT_DIR / "dataset"))
        return pipeline
    except Exception as e:
        st.warning(f"Engine simulation mode unavailable: {e}")
        return None

