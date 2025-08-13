# Otomoto Car Offer Management System

A simple-to-use solution for scraping car offers from otomoto.pl and managing them in a database with automatic tracking of new offers and identification of inactive ones.

## Features

- 🚗 **Smart Scraping**: Only scrapes new offers to minimize website presence
- 📊 **Database Management**: Tracks offers in XLSX format with historical data
- 🔄 **Lifecycle Tracking**: Automatically detects new and inactive offers
- 🚀 **Multi-URL Support**: Can handle multiple search URLs (designed for future use)
- 🎯 **URL-based Identification**: Uses URLs as unique identifiers (reposted cars = new offers)
- ⚡ **Concurrent Processing**: Configurable number of workers for efficient scraping
- 📈 **Rich CLI Interface**: Beautiful command-line interface with progress indicators

## Installation

This project uses `uv` for dependency management. Make sure you have Python 3.13+ installed.

```bash
# Install dependencies
uv sync

# Activate the environment
uv shell
```

## Usage

### Command Line Interface

The system provides a simple CLI with multiple commands:

#### Update Offers

```bash
# Basic usage - update offers for a search URL
otomoto update "https://www.otomoto.pl/osobowe/...your-search-url..."

# With custom database file
otomoto update "https://www.otomoto.pl/..." --db my_offers.xlsx

# With custom scraping parameters
otomoto update "https://www.otomoto.pl/..." --workers 8 --pause 1.5

# With verbose logging
otomoto update "https://www.otomoto.pl/..." --verbose
```

#### Database Statistics

```bash
# Show current database statistics
otomoto stats

# For custom database file
otomoto stats --db my_offers.xlsx
```

#### Export Data

```bash
# Export all offers
otomoto export --output all_offers.xlsx

# Export only active offers
otomoto export --active-only --output active_offers.xlsx
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
search_url = "https://www.otomoto.pl/osobowe/..."
stats = manager.update_offers(search_url)

print(f"Added {stats['new_offers']} new offers")
print(f"Updated {stats['updated_offers']} existing offers")
print(f"Marked {stats['inactive_offers']} as inactive")
```

### Example Search URL

Here's an example of a typical otomoto search URL:

```
https://www.otomoto.pl/osobowe/dacia--ford--honda--mitsubishi--opel--skoda--subaru--toyota--volkswagen--volvo/seg-combi--seg-suv/od-2009?search%5Bfilter_enum_damaged%5D=0&search%5Bfilter_enum_fuel_type%5D%5B0%5D=petrol&search%5Bfilter_enum_fuel_type%5D%5B1%5D=petrol-lpg&search%5Bfilter_float_engine_capacity%3Afrom%5D=1750&search%5Bfilter_float_price%3Ato%5D=40000&search%5Border%5D=relevance_web
```

This searches for:
- Multiple car brands
- Combi and SUV body types
- From year 2009
- Petrol and petrol+LPG fuel
- Engine capacity from 1750cc
- Price up to 40,000 PLN

## How It Works

### 1. Smart Scraping Strategy

The system minimizes its presence on the website by:
- Only scraping offers that aren't already in the database
- Using configurable delays between requests
- Rotating user agents to appear more natural
- Handling rate limiting gracefully

### 2. Offer Lifecycle Management

- **New Offers**: URLs not in database are scraped and added
- **Existing Offers**: URLs already in database are marked as "seen again" (last_seen updated)
- **Inactive Offers**: URLs in database but not in current search results are marked inactive

### 3. Database Schema

The XLSX database contains these key columns:

| Column | Description |
|--------|-------------|
| `url` | Unique identifier for each offer |
| `first_seen` | When the offer was first discovered |
| `last_seen` | When the offer was last seen in search results |
| `is_active` | Whether the offer is currently active |
| `search_url` | Which search URL found this offer |
| `Tytuł`, `Cena`, etc. | Scraped offer details |

### 4. Configuration Options

- **Workers**: Number of concurrent scrapers (default: 4)
- **Pause**: Delay between requests in seconds (default: 2.0)
- **Database Path**: Custom location for the XLSX file (default: "offers.xlsx")

## Best Practices

### Weekly Updates
Since offers don't change that frequently, running the update once a week is typically sufficient:

```bash
# Add to your cron job or task scheduler
otomoto update "your-search-url" --db weekly_offers.xlsx
```

### Multiple Search URLs
While designed to support multiple search URLs, for now you can run separate commands:

```bash
otomoto update "search-url-1" --db cars_budget.xlsx
otomoto update "search-url-2" --db cars_premium.xlsx
```

### Error Handling
The system gracefully handles:
- Network timeouts and connection errors
- Individual offer scraping failures
- Malformed HTML responses
- Missing data fields

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
# Run the example script
python example_usage.py

# Or test the CLI directly
otomoto stats
```

### Future Enhancements

The system is designed to be extensible:

- **Real Database Support**: Easy to replace XLSX with PostgreSQL, SQLite, etc.
- **Multiple Sites**: Can be extended to other car websites
- **Advanced Analysis**: Foundation for price analysis and deal detection
- **Web Interface**: CLI can be extended with a web dashboard

## Troubleshooting

### Common Issues

1. **"No offers found"**: Check if the search URL is correct and publicly accessible
2. **"Failed to scrape"**: Website might be blocking requests - try increasing pause time
3. **"Database errors"**: Check file permissions and disk space

### Debugging

Enable verbose logging to see detailed operation logs:

```bash
otomoto update "your-url" --verbose
```

This will show:
- Number of pages found
- Individual offer scraping attempts
- Database operations
- Error details

## Contributing

This is a personal project, but suggestions and improvements are welcome! The code is designed to be modular and extensible.

## License

This project is for educational and personal use. Please respect otomoto.pl's terms of service and robots.txt when using this tool.
