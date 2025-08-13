"""Quick test to verify the system works."""

import tempfile
from pathlib import Path

from src.database import OfferDatabase


def test_database_basic():
    """Test basic database operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.xlsx"
        db = OfferDatabase(db_path)

        # Test loading empty database
        offers = db.load_offers()
        assert offers.empty
        print("✓ Empty database load works")

        # Test stats on empty database
        stats = db.get_stats()
        assert stats["total_offers"] == 0
        print("✓ Empty database stats work")

        # Test adding offers
        import pandas as pd

        test_offers = pd.DataFrame(
            [
                {"url": "http://test1.com", "Tytuł": "Test Car 1", "Cena": "20000"},
                {"url": "http://test2.com", "Tytuł": "Test Car 2", "Cena": "30000"},
            ]
        )

        count = db.add_new_offers(test_offers, "http://search.com")
        assert count == 2
        print("✓ Adding offers works")

        # Test loading with data
        offers = db.load_offers()
        assert len(offers) == 2
        assert all(offers["is_active"])
        print("✓ Loading saved offers works")

        # Test marking inactive
        inactive_count = db.mark_inactive(["http://test1.com"], "http://search.com")
        assert inactive_count == 1
        print("✓ Marking inactive works")

        # Test getting active only
        active = db.get_active_offers()
        assert len(active) == 1
        assert active.iloc[0]["url"] == "http://test1.com"
        print("✓ Getting active offers works")

        print("🎉 All database tests passed!")


if __name__ == "__main__":
    test_database_basic()
