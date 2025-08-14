"""Main offer management system."""

import logging
from datetime import datetime
from itertools import chain

import pandas as pd

from .database import OfferDatabase
from .scrapers import Scraper, get_offer, get_offer_links_on_page, get_offer_pages


class OfferManager:
    """Manages the complete offer scraping and database update process."""

    def __init__(
        self,
        database: OfferDatabase,
        num_workers: int = 4,
        pause_between_requests: float = 2.0,
    ):
        """Initialize the offer manager.

        Args:
            database: Database instance to manage offers
            num_workers: Number of concurrent workers for scraping
            pause_between_requests: Pause between requests in seconds
        """
        self.database = database
        self.num_workers = num_workers
        self.pause = pause_between_requests

    def update_offers(self, search_url: str) -> dict:
        """Update offers for a given search URL.

        Args:
            search_url: The otomoto search URL to process

        Returns:
            Dictionary with update statistics
        """
        logging.info(f"Starting offer update for: {search_url}")
        start_time = datetime.now()

        # Step 1: Get all offer links from search results
        offer_links = self._get_all_offer_links(search_url)
        logging.info(f"Found {len(offer_links)} total offers in search results")

        # Step 2: Filter out existing offers to minimize scraping
        existing_urls = self.database.get_all_urls()  # Get ALL URLs, not just for this search URL
        new_offer_links = [url for url in offer_links if url not in existing_urls]

        logging.info(
            f"Found {len(new_offer_links)} new offers "
            f"({len(offer_links) - len(new_offer_links)} already in database)"
        )

        # Step 3: Scrape only new offers
        scraped_offers = []
        if new_offer_links:
            scraped_offers = self._scrape_offers(new_offer_links)

        # Step 4: Update database
        stats = self._update_database(search_url, offer_links, scraped_offers, new_offer_links)

        # Calculate timing
        duration = datetime.now() - start_time
        stats["duration_seconds"] = duration.total_seconds()
        stats["search_url"] = search_url

        logging.info(f"Update completed in {duration.total_seconds():.1f} seconds")
        return stats

    def _get_all_offer_links(self, search_url: str) -> list[str]:
        """Get all offer links from a search URL.

        Args:
            search_url: The search URL to process

        Returns:
            List of offer URLs found in search results
        """
        # Get number of pages
        pages_scraper = Scraper(get_offer_pages, 1)
        num_pages_list = pages_scraper.scrape([search_url], progress=False)
        num_pages = num_pages_list[0] if num_pages_list else 1

        logging.info(f"Search has {num_pages} pages")

        # Generate page URLs
        page_links = self._generate_page_urls(search_url, num_pages)

        # Get offer links from all pages
        links_scraper = Scraper(get_offer_links_on_page, self.num_workers, self.pause)
        offer_links_nested = links_scraper.scrape(page_links)

        # Flatten the list
        offer_links = list(chain.from_iterable(offer_links_nested))
        return offer_links

    def _generate_page_urls(self, search_url: str, num_pages: int) -> list[str]:
        """Generate URLs for all pages of search results.

        Args:
            search_url: Base search URL
            num_pages: Number of pages to generate

        Returns:
            List of page URLs
        """
        if "page=" in search_url:
            # Remove existing page parameter
            base_url = search_url.split("&page=")[0].split("?page=")[0]
        else:
            base_url = search_url

        page_urls = []
        for page in range(1, num_pages + 1):
            if "?" in base_url:
                page_url = f"{base_url}&page={page}"
            else:
                page_url = f"{base_url}?page={page}"
            page_urls.append(page_url)

        return page_urls

    def _scrape_offers(self, offer_links: list[str]) -> list[dict]:
        """Scrape offer details from a list of URLs.

        Args:
            offer_links: List of offer URLs to scrape

        Returns:
            List of scraped offer dictionaries
        """
        if not offer_links:
            return []

        logging.info(f"Scraping {len(offer_links)} new offers...")
        offers_scraper = Scraper(get_offer, self.num_workers, self.pause)
        scraped_offers = offers_scraper.scrape(offer_links)

        # Filter out failed scrapes and add URLs
        valid_offers = []
        for offer, url in zip(scraped_offers, offer_links, strict=True):
            if offer:  # Skip empty/failed offers
                offer["url"] = url
                valid_offers.append(offer)
            else:
                logging.warning(f"Failed to scrape offer: {url}")

        logging.info(f"Successfully scraped {len(valid_offers)} offers")
        return valid_offers

    def _update_database(
        self,
        search_url: str,
        all_offer_links: list[str],
        scraped_offers: list[dict],
        new_offer_links: list[str],
    ) -> dict:
        """Update the database with scraped offers and mark inactive offers.

        Args:
            search_url: The search URL being processed
            all_offer_links: All offer links found in search (new + existing)
            scraped_offers: Newly scraped offer data
            new_offer_links: URLs of new offers that were scraped

        Returns:
            Dictionary with update statistics
        """
        stats = {
            "total_found": len(all_offer_links),
            "new_offers": 0,
            "updated_offers": 0,
            "inactive_offers": 0,
            "failed_scrapes": len(new_offer_links) - len(scraped_offers),
        }

        # Add new offers to database
        if scraped_offers:
            new_offers_df = pd.DataFrame(scraped_offers)
            stats["new_offers"] = self.database.add_new_offers(new_offers_df, search_url)

        # Update existing offers (mark as seen again)
        all_existing_urls = set(self.database.get_all_urls())
        current_existing_urls = [url for url in all_offer_links if url in all_existing_urls]

        if current_existing_urls:
            # Create a simple dataframe with just URLs for existing offers
            existing_df = pd.DataFrame({"url": current_existing_urls})
            stats["updated_offers"] = self.database.update_existing_offers(existing_df)

        # Mark offers not found in current search as inactive
        stats["inactive_offers"] = self.database.mark_inactive(all_offer_links, search_url)

        return stats

    def get_database_stats(self) -> dict:
        """Get current database statistics.

        Returns:
            Dictionary with database statistics
        """
        return self.database.get_stats()
