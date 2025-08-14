# Otomoto Car Offer Management System

A simple-to-use solution for scraping car offers from otomoto.pl and managing them in a database with automatic tracking of new offers and identification of inactive ones.

## Responsible Scraping

This tool follows good scraping etiquette:

- **Smart Scraping**: Only scrapes offers that aren't already in the database
- **Rate Limiting**: Uses configurable delays between requests to minimize server load
- **Infrequent Updates**: Designed for periodic use (weekly/bi-weekly) rather than continuous monitoring
- **Respectful Traffic**: Minimizes website presence and follows reasonable request patterns

**Important**: Please respect otomoto.pl's terms of service and robots.txt when using this tool. This project is intended for educational and personal use only.

## Features

- 🚗 **Smart Scraping**: Only scrapes new offers to minimize website presence
- 📊 **Database Management**: Tracks offers in XLSX format with historical data
- 🔄 **Lifecycle Tracking**: Automatically detects new and inactive offers
- 🎯 **URL-based Identification**: Uses URLs as unique identifiers (reposted cars = new offers)
- ⚡ **Concurrent Processing**: Configurable number of workers for efficient scraping
- 📈 **Rich CLI Interface**: Beautiful command-line interface with progress indicators
- 🔍 **Data Integrity**: Built-in verification and cleanup tools

## Installation

This project uses `uv` for dependency management. Make sure you have Python 3.13+ installed.

```bash
# Install dependencies
uv sync

# Activate the environment (optional, commands will work without this)
uv shell
```

## Usage

### Getting Your Search URL

To get your search URL:

1. Go to otomoto.pl
2. Set up all your search criteria (brand, model, price range, year, etc.)
3. Copy the URL from your browser's address bar after the search is complete
4. Use this URL with the tool

### Command Line Interface

The system provides a simple CLI with multiple commands:

#### Update Offers

```bash
# Basic usage - update offers for a search URL
otomoto update "https://www.otomoto.pl/osobowe/...your-search-url..."

# With custom database file
otomoto update "your-search-url" --db my_offers.xlsx

# With custom scraping parameters
otomoto update "your-search-url" --workers 8 --pause 1.5

# With verbose logging
otomoto update "your-search-url" --verbose

# All options combined
otomoto update "your-search-url" --db my_offers.xlsx --workers 6 --pause 3.0 --verbose
```

#### Database Statistics

```bash
# Show current database statistics
otomoto stats

# For custom database file
otomoto stats --db my_offers.xlsx
```

#### Verify Database Integrity

```bash
# Check for duplicate URLs and data integrity
otomoto verify

# For custom database file
otomoto verify --db my_offers.xlsx
```

#### Clean Up Duplicates

```bash
# Remove duplicate entries (dry run first to see what would be removed)
otomoto cleanup --dry-run

# Actually remove duplicates
otomoto cleanup

# For custom database file
otomoto cleanup --db my_offers.xlsx --dry-run
```

#### Export Data

```bash
# Export active offers only (default)
otomoto export

# Export to custom file
otomoto export --output all_offers.xlsx

# Export all offers including inactive ones
otomoto export --include-inactive --output complete_export.xlsx

# Export from custom database
otomoto export --db my_offers.xlsx --output my_export.xlsx

# All options combined
otomoto export --db my_offers.xlsx --output complete_data.xlsx --include-inactive
```

### Python API

You can also use the system programmatically:

```python
import logging
from src.database import OfferDatabase
from src.offer_manager import OfferManager

# Setup logging
logging.basicConfig(level=logging.INFO)

# Initialize components
database = OfferDatabase("my_offers.xlsx")
manager = OfferManager(database, num_workers=4, pause_between_requests=2.0)

# Update offers
search_url = "https://www.otomoto.pl/osobowe/..."  # Your search URL here
stats = manager.update_offers(search_url)

print(f"Added {stats['new_offers']} new offers")
print(f"Updated {stats['updated_offers']} existing offers")
print(f"Marked {stats['inactive_offers']} as inactive")
```

## How It Works

### 1. Offer Lifecycle Management

- **New Offers**: URLs not in database are scraped and added
- **Existing Offers**: URLs already in database are marked as "seen again" (last_seen updated)
- **Inactive Offers**: URLs in database but not in current search results are marked inactive

### 2. Database Schema

The XLSX database contains these key columns:

| Column | Description |
|--------|-------------|
| `url` | Unique identifier for each offer |
| `first_seen` | When the offer was first discovered |
| `last_seen` | When the offer was last seen in search results |
| `is_active` | Whether the offer is currently active |
| `search_url` | Which search URL found this offer |
| `Tytuł`, `Cena`, etc. | Scraped offer details |

### 3. Configuration Options

- **Workers**: Number of concurrent scrapers (default: 4)
- **Pause**: Delay between requests in seconds (default: 2.0)
- **Database Path**: Custom location for the XLSX file (default: "offers.xlsx")

## Development

### Project Structure

```
src/
├── __init__.py
├── database.py          # XLSX database management
├── offer_manager.py     # Main orchestration logic
├── cli.py              # Command-line interface
└── scrapers/           # Web scraping utilities
    ├── __init__.py
    ├── otomoto_scrapers.py  # Site-specific scrapers
    ├── scraper.py           # Base scraper class
    └── header_utils.py      # User agent rotation
```

### Running Tests

```bash
# Test the CLI directly
otomoto stats
otomoto verify
```

## TODO

The system is designed to be extensible. Future enhancements could include:

- **Real Database Support**: Easy to replace XLSX with PostgreSQL, SQLite, etc.
- **Advanced Analysis**: Foundation for price analysis and deal detection
- **Web Interface**: CLI can be extended with a web dashboard

## Contributing

This is a personal project, but suggestions and improvements are welcome! The code is designed to be modular and extensible.

## License

This project is for educational and personal use. Please respect otomoto.pl's terms of service and robots.txt when using this tool.
