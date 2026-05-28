"""Tests for the 1099-NEC packet generator."""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bookie.tax import generate_1099_packet, aggregate_vendor_payments, NEC_THRESHOLD_2026


def test_below_threshold_excluded():
    txs = [{"vendor_id": "V1", "amount": 1500, "payment_method": "ach"}]
    masters = {"V1": {"display_name": "Small Vendor", "tax_identifier": "12-3456789", "w9_on_file": True}}
    with tempfile.TemporaryDirectory() as d:
        r = generate_1099_packet(tax_year=2026, transactions=txs, vendor_master=masters,
                                 workspace=Path(d))
    assert len(r.entries) == 0


def test_above_threshold_included():
    txs = [{"vendor_id": "V1", "amount": 2500, "payment_method": "ach"}]
    masters = {"V1": {"display_name": "Real Contractor", "tax_identifier": "12-3456789",
                       "address": "100 Main St, Austin TX 78701", "w9_on_file": True}}
    with tempfile.TemporaryDirectory() as d:
        r = generate_1099_packet(tax_year=2026, transactions=txs, vendor_master=masters,
                                 workspace=Path(d))
    assert len(r.entries) == 1
    assert r.entries[0].vendor.display_name == "Real Contractor"
    assert r.entries[0].flags == []


def test_card_payments_excluded_from_threshold():
    """Card payments are NOT 1099-reportable (1099-K instead)."""
    txs = [{"vendor_id": "V1", "amount": 3000, "payment_method": "credit_card"}]
    masters = {"V1": {"display_name": "Card Vendor", "tax_identifier": "12-3456789", "w9_on_file": True}}
    with tempfile.TemporaryDirectory() as d:
        r = generate_1099_packet(tax_year=2026, transactions=txs, vendor_master=masters,
                                 workspace=Path(d))
    assert len(r.entries) == 0   # card payments don't count toward NEC threshold


def test_missing_w9_flagged():
    txs = [{"vendor_id": "V1", "amount": 2500, "payment_method": "ach"}]
    masters = {"V1": {"display_name": "No W9", "tax_identifier": "", "w9_on_file": False}}
    with tempfile.TemporaryDirectory() as d:
        r = generate_1099_packet(tax_year=2026, transactions=txs, vendor_master=masters,
                                 workspace=Path(d))
    assert len(r.flagged_no_w9) == 1
    assert "no_w9_on_file" in r.entries[0].flags


def test_artifact_written():
    txs = [{"vendor_id": "V1", "amount": 2500, "payment_method": "ach"}]
    masters = {"V1": {"display_name": "Test Vendor", "tax_identifier": "12-3456789",
                       "address": "1 Main St, NYC NY 10001", "w9_on_file": True}}
    with tempfile.TemporaryDirectory() as d:
        r = generate_1099_packet(tax_year=2026, transactions=txs, vendor_master=masters,
                                 workspace=Path(d))
        assert r.artifact_path.exists()
        content = r.artifact_path.read_text()
        assert "1099-NEC Packet" in content
        assert "Test Vendor" in content


def test_threshold_is_2000_for_2026():
    assert NEC_THRESHOLD_2026 == 2000.00
