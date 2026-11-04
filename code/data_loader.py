"""Module 1: Data Loader for Buy or Wait Financial Affordability Agent.

Provides robust, validated, and type-hinted data loading capabilities for all
datasets required by the HackerRank Orchestrate 'Buy or Wait?' challenge.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Expected schema column mappings for validation
EXPECTED_COLUMNS: Dict[str, List[str]] = {
    "requests": [
        "request_id",
        "user_id",
        "request_date",
        "request_type",
        "requested_amount",
        "desired_completion_date",
        "allows_partial_payment",
        "request_text",
    ],
    "sample_requests": [
        "request_id",
        "user_id",
        "request_date",
        "request_type",
        "requested_amount",
        "desired_completion_date",
        "allows_partial_payment",
        "request_text",
        "amount_safe_to_pay",
        "affordability_status",
        "recommended_payment_method",
        "payment_plan",
        "earliest_date_for_full_payment",
        "spending_changes_needed",
        "decision_explanation",
    ],
    "financial_profiles": [
        "user_id",
        "home_currency",
        "current_available_balance",
        "minimum_balance_to_keep",
        "financial_priorities",
        "expense_categories_to_protect",
        "expense_categories_user_is_willing_to_reduce",
        "expense_categories_user_is_willing_to_stop",
        "payment_methods_user_will_consider",
        "max_installment_months",
    ],
    "financial_events": [
        "event_id",
        "user_id",
        "event_type",
        "description",
        "category",
        "direction",
        "amount",
        "currency",
        "event_date",
        "settlement_date",
        "status",
        "linked_event_id",
        "flexibility",
        "minimum_allowed_amount",
    ],
    "exchange_rates": [
        "rate_date",
        "from_currency",
        "to_currency",
        "rate",
    ],
    "request_payment_options": [
        "payment_option_id",
        "request_id",
        "payment_method",
        "payment_amount",
        "number_of_payments",
        "first_payment_date",
        "payment_frequency_days",
        "financing_fee",
        "total_payable_amount",
    ],
    "messages": [
        "message_id",
        "user_id",
        "request_id",
        "related_event_id",
        "sent_at",
        "source_type",
        "message_text",
    ],
    "images": [
        "image_id",
        "user_id",
        "request_id",
        "related_event_id",
    ],
}

FILE_MAP: Dict[str, str] = {
    "requests": "requests.csv",
    "sample_requests": "sample_requests.csv",
    "financial_profiles": "financial_profiles.csv",
    "financial_events": "financial_events.csv",
    "exchange_rates": "exchange_rates.csv",
    "request_payment_options": "request_payment_options.csv",
    "messages": "messages.csv",
    "images": "images.csv",
}


@dataclass
class Datasets:
    """Strongly typed container providing convenient attribute and dictionary access

    to all loaded pandas DataFrames.
    """

    requests: pd.DataFrame
    sample_requests: pd.DataFrame
    financial_profiles: pd.DataFrame
    financial_events: pd.DataFrame
    exchange_rates: pd.DataFrame
    request_payment_options: pd.DataFrame
    messages: pd.DataFrame
    images: pd.DataFrame

    def __getitem__(self, key: str) -> pd.DataFrame:
        """Allow dict-like access e.g., datasets['requests']."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Dataset '{key}' not found. Available keys: {list(FILE_MAP.keys())}")

    def __contains__(self, key: str) -> bool:
        """Support 'key in datasets' checks."""
        return hasattr(self, key)

    def __iter__(self) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Iterate over (name, DataFrame) pairs."""
        for name in FILE_MAP:
            yield name, getattr(self, name)

    def summary(self) -> List[Dict[str, Any]]:
        """Return a structured summary of row counts, column counts, and column names."""
        result = []
        for name in FILE_MAP:
            df = getattr(self, name)
            result.append({
                "name": name,
                "file": FILE_MAP[name],
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
            })
        return result


class DataLoader:
    """Reusable, validated data loader for all 'Buy or Wait' challenge datasets."""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        """Initialize DataLoader with a path to the dataset folder.

        If data_dir is not provided, resolves relative to this file's repository root.
        """
        if data_dir is not None:
            self.data_dir = Path(data_dir).resolve()
        else:
            # Default resolution: <repo_root>/dataset
            repo_root = Path(__file__).resolve().parent.parent
            self.data_dir = (repo_root / "dataset").resolve()

    def get_file_path(self, dataset_name: str) -> Path:
        """Get the full resolved path to a given dataset file."""
        if dataset_name not in FILE_MAP:
            raise ValueError(
                f"Unknown dataset name '{dataset_name}'. Allowed: {list(FILE_MAP.keys())}"
            )
        return self.data_dir / FILE_MAP[dataset_name]

    def validate_file_exists(self, dataset_name: str) -> Path:
        """Check whether the required dataset file exists on disk."""
        path = self.get_file_path(dataset_name)
        if not path.is_file():
            raise FileNotFoundError(
                f"Dataset file missing for '{dataset_name}'. Expected at: {path}"
            )
        return path

    def load_dataset(self, dataset_name: str, validate_schema: bool = True) -> pd.DataFrame:
        """Load a single dataset by name without modifying the underlying data."""
        file_path = self.validate_file_exists(dataset_name)

        try:
            # Read CSV using pandas without modifying raw values
            df = pd.read_csv(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV at {file_path}: {e}") from e

        if validate_schema:
            self._validate_dataframe(dataset_name, df)

        return df

    def _validate_dataframe(self, dataset_name: str, df: pd.DataFrame) -> None:
        """Perform basic integrity and schema checks on a loaded DataFrame."""
        if df.empty:
            raise ValueError(
                f"Dataset '{dataset_name}' ({FILE_MAP[dataset_name]}) loaded with 0 rows."
            )

        expected = EXPECTED_COLUMNS.get(dataset_name)
        if expected is not None:
            missing_cols = [c for c in expected if c not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"Dataset '{dataset_name}' missing expected column(s): {missing_cols}. "
                    f"Actual columns: {list(df.columns)}"
                )

    def load_all(self, validate_schema: bool = True) -> Datasets:
        """Load and validate all 8 datasets into a Datasets container.

        Raises:
            FileNotFoundError: If any of the 8 dataset files are missing.
            ValueError: If any dataset fails validation checks.
            RuntimeError: If pandas fails to parse any CSV.
        """
        if not self.data_dir.is_dir():
            raise FileNotFoundError(
                f"Dataset directory not found at: {self.data_dir}. "
                "Ensure dataset/ is present in the repository root or provide data_dir."
            )

        loaded: Dict[str, pd.DataFrame] = {}
        for name in FILE_MAP:
            loaded[name] = self.load_dataset(name, validate_schema=validate_schema)

        return Datasets(
            requests=loaded["requests"],
            sample_requests=loaded["sample_requests"],
            financial_profiles=loaded["financial_profiles"],
            financial_events=loaded["financial_events"],
            exchange_rates=loaded["exchange_rates"],
            request_payment_options=loaded["request_payment_options"],
            messages=loaded["messages"],
            images=loaded["images"],
        )


def load_all_datasets(data_dir: Optional[Union[str, Path]] = None) -> Datasets:
    """Convenience functional interface to load all datasets.

    Args:
        data_dir: Optional custom directory path to the dataset folder.

    Returns:
        Datasets dataclass with all 8 loaded DataFrames.
    """
    loader = DataLoader(data_dir=data_dir)
    return loader.load_all()

