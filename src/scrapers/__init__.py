from .otomoto_scrapers import (
    get_offer,
    get_offer_links_on_page,
    get_offer_pages,
)
from .scraper import Scraper

__all__ = [
    "Scraper",
    "get_offer_pages",
    "get_offer_links_on_page",
    "get_offer",
]
