import logging
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from tqdm import tqdm

ScrapFunType = Callable[[str], Any]


class Scraper:
    def __init__(self, scrap_fn, num_workers: int = 1, pause: float = 0.2):
        self.scrap_fn = scrap_fn
        self.num_workers = num_workers
        self.pause = pause

    def _internal_scrap(self, url: str) -> Any:
        """Internal method to handle scraping with a pause."""
        res = self.scrap_fn(url)
        time.sleep(self.pause)
        return res

    def scrape(self, urls: list[str], progress: bool = True) -> list[Any]:
        results = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [executor.submit(self._internal_scrap, url) for url in urls]
            if progress:
                futures = tqdm(futures, total=len(urls), desc="Scraping URLs")
            for i, future in enumerate(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    results.append(None)
                    logging.exception(f"Error scraping url: {urls[i]}")
        return results
