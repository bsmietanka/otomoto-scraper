"""Database management for car offers."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas import DataFrame


class OfferDatabase:
    """Manages the offer database stored in XLSX format."""

    def __init__(self, db_path: str | Path):
        """Initialize the database manager.

        Args:
            db_path: Path to the XLSX database file
        """
        self.db_path = Path(db_path)

    def load_offers(self) -> DataFrame:
        """Load existing offers from the database.

        Returns:
            DataFrame with existing offers, empty if file doesn't exist
        """
        if not self.db_path.exists():
            logging.info(f"Database file {self.db_path} doesn't exist, starting fresh")
            return self._create_empty_dataframe()

        try:
            df = pd.read_excel(self.db_path, engine="openpyxl")
            logging.info(f"Loaded {len(df)} offers from {self.db_path}")

            # Ensure required columns exist
            required_columns = [
                "url",
                "first_seen",
                "last_seen",
                "is_active",
                "search_url",
            ]
            for col in required_columns:
                if col not in df.columns:
                    if col == "is_active":
                        df[col] = True  # Default to active
                    elif col in ["first_seen", "last_seen"]:
                        df[col] = datetime.now()
                    elif col == "search_url":
                        df[col] = None  # Will be filled during updates
                    else:
                        df[col] = None

            return df

        except Exception as e:
            logging.error(f"Error loading database: {e}")
            # Return empty dataframe if loading fails
            return self._create_empty_dataframe()

    def save_offers(self, offers: DataFrame) -> None:
        """Save offers to the database.

        Args:
            offers: DataFrame containing offers to save
        """
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Sort by last_seen descending (most recent first)
            offers_sorted = offers.sort_values("last_seen", ascending=False)

            offers_sorted.to_excel(self.db_path, index=False, engine="openpyxl")
            logging.info(f"Saved {len(offers_sorted)} offers to {self.db_path}")

        except Exception as e:
            logging.error(f"Error saving database: {e}")
            raise

    def get_active_offers(self) -> DataFrame:
        """Get only active offers from the database.

        Returns:
            DataFrame with active offers only
        """
        all_offers = self.load_offers()
        return all_offers[all_offers["is_active"]].copy()

    def get_urls_for_search_url(self, search_url: str) -> set[str]:
        """Get all URLs that were found for a specific search URL.

        Args:
            search_url: The search URL to filter by

        Returns:
            Set of offer URLs found for this search URL
        """
        offers = self.load_offers()
        matching_offers = offers[offers["search_url"] == search_url]
        return set(matching_offers["url"].dropna().tolist())

    def get_all_urls(self) -> set[str]:
        """Get all URLs in the database regardless of search URL.

        Returns:
            Set of all offer URLs in the database
        """
        offers = self.load_offers()
        return set(offers["url"].dropna().tolist())

    def mark_inactive(self, offer_urls: list[str], search_url: str) -> int:
        """Mark offers as inactive if they're not in current search results.

        Args:
            offer_urls: List of URLs found in current search
            search_url: The search URL these offers came from

        Returns:
            Number of offers marked as inactive
        """
        offers = self.load_offers()

        # Find offers that were previously found for this search URL
        # but are not in the current results
        previous_urls = self.get_urls_for_search_url(search_url)
        current_urls = set(offer_urls)
        missing_urls = previous_urls - current_urls

        if missing_urls:
            # Mark missing offers as inactive
            mask = offers["url"].isin(missing_urls)
            offers.loc[mask, "is_active"] = False
            offers.loc[mask, "last_seen"] = datetime.now()

            self.save_offers(offers)
            logging.info(f"Marked {len(missing_urls)} offers as inactive")
            return len(missing_urls)

        return 0

    def add_new_offers(self, new_offers: DataFrame, search_url: str) -> int:
        """Add new offers to the database.

        Args:
            new_offers: DataFrame with new offers to add
            search_url: The search URL these offers came from

        Returns:
            Number of new offers added
        """
        if new_offers.empty:
            return 0

        # Load existing offers first
        existing_offers = self.load_offers()
        existing_urls = set(existing_offers["url"].dropna().tolist())

        # Filter out offers that already exist in database (by URL)
        new_urls = set(new_offers["url"].dropna().tolist())
        truly_new_urls = new_urls - existing_urls

        if not truly_new_urls:
            logging.info("No truly new offers to add (all URLs already exist)")
            return 0

        # Keep only offers with truly new URLs
        filtered_new_offers = new_offers[new_offers["url"].isin(truly_new_urls)].copy()

        # Add metadata
        now = datetime.now()
        filtered_new_offers["first_seen"] = now
        filtered_new_offers["last_seen"] = now
        filtered_new_offers["is_active"] = True
        filtered_new_offers["search_url"] = search_url

        # Append to existing offers
        combined_offers = pd.concat([existing_offers, filtered_new_offers], ignore_index=True)

        self.save_offers(combined_offers)
        logging.info(f"Added {len(filtered_new_offers)} new offers")
        return len(filtered_new_offers)

    def update_existing_offers(self, updated_offers: DataFrame) -> int:
        """Update last_seen timestamp for existing offers.

        Args:
            updated_offers: DataFrame with offers that were found again

        Returns:
            Number of offers updated
        """
        if updated_offers.empty:
            return 0

        existing_offers = self.load_offers()
        updated_urls = set(updated_offers["url"].tolist())

        # Update last_seen for existing offers
        mask = existing_offers["url"].isin(updated_urls)
        existing_offers.loc[mask, "last_seen"] = datetime.now()
        existing_offers.loc[mask, "is_active"] = True  # Reactivate if was inactive

        self.save_offers(existing_offers)
        updated_count = mask.sum()
        logging.info(f"Updated {updated_count} existing offers")
        return updated_count

    def _create_empty_dataframe(self) -> DataFrame:
        """Create an empty DataFrame with the required structure.

        Returns:
            Empty DataFrame with required columns
        """
        return pd.DataFrame(
            columns=[
                "url",
                "first_seen",
                "last_seen",
                "is_active",
                "search_url",
                # Common offer fields (will be populated during scraping)
                "Tytuł",
                "Cena",
                "Waluta",
                "Marka pojazdu",
                "Model pojazdu",
                "Rok produkcji",
                "Przebieg",
                "Pojemność skokowa",
                "Moc",
                "Rodzaj paliwa",
                "Skrzynia biegów",
                "Typ nadwozia",
                "Lokalizacja",
                "Opis",
                "Szczegóły ceny",
            ]
        )

    def get_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        offers = self.load_offers()

        if offers.empty:
            return {
                "total_offers": 0,
                "active_offers": 0,
                "inactive_offers": 0,
                "search_urls": 0,
            }

        active_count = offers["is_active"].sum()
        inactive_count = (~offers["is_active"]).sum()
        search_urls = offers["search_url"].nunique()

        return {
            "total_offers": len(offers),
            "active_offers": active_count,
            "inactive_offers": inactive_count,
            "search_urls": search_urls,
        }

    def remove_duplicates(self) -> int:
        """Remove duplicate offers keeping the best one for each URL.

        Priority order:
        1. Active entries over inactive ones
        2. Most recent last_seen date among entries with same activity status

        Returns:
            Number of duplicate entries removed
        """
        offers = self.load_offers()

        if offers.empty:
            return 0

        original_count = len(offers)

        # Sort by URL, then by is_active descending (True first), then by last_seen descending
        # This ensures that for each URL, active entries come first, and among those, most recent first
        offers_sorted = offers.sort_values(
            ["url", "is_active", "last_seen"], ascending=[True, False, False]
        )

        # Keep first entry for each URL (which will be active and most recent due to sorting)
        offers_deduplicated = offers_sorted.drop_duplicates(subset=["url"], keep="first")

        # Sort back by last_seen descending for consistent output
        offers_final = offers_deduplicated.sort_values("last_seen", ascending=False)

        duplicates_removed = original_count - len(offers_final)

        if duplicates_removed > 0:
            self.save_offers(offers_final)
            logging.info(
                f"Removed {duplicates_removed} duplicate entries, prioritizing active entries"
            )
        else:
            logging.info("No duplicates found to remove")

        return duplicates_removed
