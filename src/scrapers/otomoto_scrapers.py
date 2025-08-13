import logging
import re

import httpx
from bs4 import BeautifulSoup

from .header_utils import get_headers, shuffle_headers


def get_offer_pages(url: str) -> int:
    logging.info("Determine number of pages for search result url: %s", url)
    try:
        headers = get_headers()
        res = httpx.get(url, headers=headers, follow_redirects=True)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, features="lxml")
        next_page_button = soup.find("li", attrs={"title": "Go to next Page"})
        last_page_num = int(next_page_button.find_previous_sibling("li").text)
    except Exception as e:
        logging.exception("Error occurred while getting offer pages: %s", e)
        last_page_num = 1

    logging.info("Search result url has: %s subpages", last_page_num)
    return last_page_num


def get_offer_links_on_page(url: str) -> list[str]:
    logging.info("Scrapping page: %s", url)
    page_content = None
    for headers in shuffle_headers():
        try:
            res = httpx.get(url, headers=headers, follow_redirects=True)
            res.raise_for_status()
            page_content = res.text
            break
        except httpx.HTTPStatusError as e:
            logging.error("HTTP error: %s", e)
            continue
        except httpx.RequestError as e:
            logging.error("Request error: %s", e)
            continue

    if page_content is None:
        logging.error("Failed to fetch page content after retries.")
        return []

    soup = BeautifulSoup(page_content, features="lxml")
    car_links_section = []
    try:
        car_links_section = soup.find("div", attrs={"data-testid": "search-results"})
        car_banners = car_links_section.find_all("article")
        # remove featured dealers
        car_banners = [
            banner
            for banner in car_banners
            if "featured-dealer" not in banner.get("data-testid", "")
        ]
    except Exception:
        logging.exception("Failed to find car links section on page %s", url)
        return []

    links = []
    for banner in car_banners:
        try:
            section = banner.find("section")
            link = section.find("a", href=True)["href"]
            links.append(link)
        except Exception as e:
            logging.warning("Error extracting link: %s", e)

    logging.info("Found %s links", len(links))
    return links


def get_offer(link: str) -> dict:
    logging.info(f"Fetching {link}")
    header = get_headers()
    res = httpx.get(link, headers=header, follow_redirects=True)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, features="lxml")
    for style_tag in soup.find_all("style"):
        style_tag.decompose()

    fetchers = [
        _get_offer_title,
        _get_price,
        _get_currency,
        _get_price_details,
        _get_main_features,
        _get_description,
        _get_extended_features,
        __get_location,
    ]
    features = {}
    for fetcher in fetchers:
        try:
            features.update(fetcher(soup))
        except Exception:
            logging.exception(f"Error fetching features with {fetcher.__name__}")

    return features


def _get_main_features(soup) -> dict[str, str]:
    features = {}
    main_params = soup.find("div", attrs={"data-testid": "main-details-section"})
    for param in main_params.find_all("div", attrs={"data-testid": "detail"}):
        el = [p_tag.text for p_tag in param.find_all("p")]
        features[el[0]] = el[1]
    return features


def _get_description(soup) -> dict[str, str]:
    features = {}
    desc_div = soup.find("div", attrs={"data-testid": "textWrapper"})
    paragraphs = []
    for x in desc_div.find_all("p"):
        paragraphs.append(x.text.strip())
    features["Opis"] = "\n".join(paragraphs)
    return features


def _get_extended_features(soup) -> dict[str, str]:
    features = {}
    basic_params_section = soup.find("div", attrs={"data-testid": "basic_information"})
    basic_params = basic_params_section.find_all("div", attrs={"data-testid": True})
    for param in basic_params:
        text_tags = param.find_all("p")
        if len(text_tags) == 2:
            features[text_tags[0].text.strip()] = text_tags[1].text.strip()
    return features


def _get_price(soup) -> dict[str, str]:
    features = {}
    price_tag = soup.find("span", class_=re.compile("^offer-price__number"))
    features["Cena"] = price_tag.text.strip()
    return features


def _get_currency(soup) -> dict[str, str]:
    features = {}
    currency_tag = soup.find("span", class_=re.compile("^offer-price__currency"))
    features["Waluta"] = currency_tag.text.strip()
    return features


def _get_offer_title(soup) -> dict[str, str]:
    features = {}
    title_tag = soup.find("h1", class_=re.compile("^offer-title"))
    features["Tytuł"] = title_tag.text.strip()
    return features


def _get_price_details(soup) -> dict[str, str]:
    features = {}
    price_details_tag = soup.find(
        "div", attrs={"data-testid": "small-price-evaluation-indicator"}
    )
    features["Szczegóły ceny"] = price_details_tag.text.strip()
    return features


def __get_location(soup) -> dict[str, str]:
    features = {}
    location_tag = soup.find(href=re.compile("^https://www.google.com/maps/search/*"))
    features["Lokalizacja"] = location_tag.text.strip() if location_tag else "Nieznana"
    return features
