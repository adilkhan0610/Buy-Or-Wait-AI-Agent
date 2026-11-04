"""Test and verification script for Module 4: Message & Image Analyzers.

Validates:
- MessageAnalyzer: extracts structured findings across English and Indonesian messages.
- ImageAnalyzer: maps all 16 images to valid PNG files and extracts correct amounts.
- Referential Integrity: verifies extracted event IDs match financial_events.csv records.
- Type integrity: verifies Decimal amounts, currencies, and finding types.
"""

from decimal import Decimal
import sys
from pathlib import Path
import pandas as pd

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from code.data_loader import DataLoader
from code.message_analyzer import MessageAnalyzer, MessageFinding
from code.image_analyzer import ImageAnalyzer, ImageFinding


def run_context_analyzer_tests() -> bool:
    """Execute all verification tests on MessageAnalyzer and ImageAnalyzer."""
    print("=" * 80)
    print("MODULE 4: MESSAGE & IMAGE ANALYZER TEST")
    print("=" * 80)

    try:
        # Step 1: Load datasets via Module 1
        print("1. Loading datasets via Module 1 DataLoader...")
        loader = DataLoader()
        datasets = loader.load_all()
        print(f"[OK] Loaded datasets ({len(datasets.messages)} messages, {len(datasets.images)} images).\n")

        # Step 2: Test MessageAnalyzer
        print("2. Testing MessageAnalyzer on messages.csv...")
        msg_analyzer = MessageAnalyzer(datasets.messages)
        msg_findings = msg_analyzer.analyze_all()
        print(f"[OK] Total messages processed: {len(datasets.messages)}")
        print(f"[OK] Total message findings produced: {len(msg_findings)}")

        # Verify findings categories
        finding_types = {}
        confirmed_count = 0
        unconfirmed_count = 0
        for f in msg_findings:
            finding_types[f.finding_type] = finding_types.get(f.finding_type, 0) + 1
            if f.is_confirmed:
                confirmed_count += 1
            else:
                unconfirmed_count += 1

        print("\nMessage Findings Breakdown:")
        for ftype, count in sorted(finding_types.items()):
            print(f"  - {ftype:<30}: {count:3d}")
        print(f"  Confirmed findings: {confirmed_count}, Unconfirmed / Notice: {unconfirmed_count}")

        # Spot check specific messages (English & Indonesian)
        # message_01: Indonesian salary increase to 42,750,000 IDR
        f_01 = next(f for f in msg_findings if f.message_id == "message_01")
        assert f_01.finding_type == "salary_update", f"Unexpected type {f_01.finding_type}"
        assert f_01.extracted_value == Decimal("42750000"), f"Unexpected amount {f_01.extracted_value}"
        assert f_01.currency == "IDR", f"Unexpected currency {f_01.currency}"
        assert f_01.effective_date == "2025-08-15", f"Unexpected effective_date {f_01.effective_date}"
        assert f_01.is_confirmed is True
        print(f"\n[OK] message_01 (Indonesian salary increase): {f_01.currency} {f_01.extracted_value} effective {f_01.effective_date}")

        # message_04: English temporary pay reduction to 1037.52 EUR
        f_04 = next(f for f in msg_findings if f.message_id == "message_04")
        assert f_04.finding_type == "temporary_salary_adjustment"
        assert f_04.extracted_value == Decimal("1037.52")
        assert f_04.currency == "EUR"
        assert f_04.is_confirmed is True
        print(f"[OK] message_04 (English temporary pay): {f_04.currency} {f_04.extracted_value}")

        # message_07: Unconfirmed pending payout
        f_07 = next(f for f in msg_findings if f.message_id == "message_07")
        assert f_07.finding_type == "unconfirmed_pending_funds"
        assert f_07.is_confirmed is False
        print(f"[OK] message_07 (Unconfirmed pending payout): is_confirmed={f_07.is_confirmed}")

        # Step 3: Test ImageAnalyzer
        print("\n3. Testing ImageAnalyzer on images.csv and media/images...")
        img_analyzer = ImageAnalyzer(datasets.images)
        img_findings = img_analyzer.analyze_all()
        assert len(img_findings) == 16, f"Expected 16 image findings, got {len(img_findings)}"
        print(f"[OK] Successfully analyzed all {len(img_findings)} challenge images.\n")

        print("-" * 80)
        print(f"{'IMAGE ID':<10} | {'EVENT ID':<12} | {'USER':<8} | {'AMOUNT':<14} | {'CURR':<5} | {'DOCUMENT TYPE':<22}")
        print("-" * 80)
        for img in img_findings:
            print(
                f"{img.image_id:<10} | {img.related_event_id:<12} | {img.user_id:<8} | "
                f"{str(img.extracted_amount):<14} | {img.currency:<5} | {img.document_type:<22}"
            )
        print("-" * 80)

        # Step 4: Verify image physical paths and event linkage
        print("\n4. Verifying image physical paths and event linkages...")
        fe_df = datasets.financial_events
        for img in img_findings:
            # Check file exists on disk
            assert Path(img.image_path).is_file(), f"Image file not found: {img.image_path}"

            # Check linked financial_event
            matching_events = fe_df[fe_df["event_id"] == img.related_event_id]
            assert len(matching_events) == 1, f"Event {img.related_event_id} not found in financial_events"
            event_row = matching_events.iloc[0]

            # Verify user_id matches
            assert event_row["user_id"] == img.user_id, f"User mismatch for {img.image_id}: {event_row['user_id']} vs {img.user_id}"

            # Verify currency matches
            assert event_row["currency"] == img.currency, f"Currency mismatch for {img.image_id}: {event_row['currency']} vs {img.currency}"

            # Verify that the event in financial_events had null amount (as expected)
            assert pd.isna(event_row["amount"]), f"Expected null amount in financial_events for {img.related_event_id}"

        print("[OK] All 16 images confirmed: physical files exist, users match, currencies match, and all 16 correspond to null event amounts.")

        # Test lookup helper
        assert img_analyzer.get_extracted_amount_for_event("event_253") == Decimal("4365000.00")
        assert img_analyzer.get_extracted_amount_for_event("event_1442") == Decimal("100000.00")
        print("\n[OK] ImageAnalyzer.get_extracted_amount_for_event() verified.")

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED: Module 4 Context Analyzers are fully operational.")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[FAILURE] Context Analyzer test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_context_analyzer_tests()
    sys.exit(0 if success else 1)
