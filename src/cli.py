"""Command line interface for the otomoto offer manager."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .database import OfferDatabase
from .offer_manager import OfferManager

app = typer.Typer(help="Otomoto car offer management system")
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@app.command()
def update(
    search_url: str = typer.Argument(..., help="Otomoto search URL to process"),
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
    workers: int = typer.Option(
        4, "--workers", "-w", help="Number of concurrent workers for scraping"
    ),
    pause: float = typer.Option(
        2.0, "--pause", "-p", help="Pause between requests in seconds"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Update offers for a given search URL."""
    setup_logging(verbose)

    console.print("[bold blue]Starting offer update[/bold blue]")
    console.print(f"Search URL: {search_url}")
    console.print(f"Database: {database_path}")
    console.print(f"Workers: {workers}, Pause: {pause}s")

    try:
        # Initialize components
        database = OfferDatabase(database_path)
        manager = OfferManager(database, workers, pause)

        # Show current stats
        current_stats = manager.get_database_stats()
        console.print("\n[bold]Current database stats:[/bold]")
        console.print(f"Total offers: {current_stats['total_offers']}")
        console.print(f"Active offers: {current_stats['active_offers']}")
        console.print(f"Inactive offers: {current_stats['inactive_offers']}")
        console.print(f"Search URLs tracked: {current_stats['search_urls']}")

        # Update offers
        with console.status("[bold green]Updating offers..."):
            stats = manager.update_offers(search_url)

        # Display results
        display_update_results(stats)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def stats(
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
) -> None:
    """Show database statistics."""
    try:
        database = OfferDatabase(database_path)
        manager = OfferManager(database)
        stats = manager.get_database_stats()

        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Total Offers", str(stats["total_offers"]))
        table.add_row("Active Offers", str(stats["active_offers"]))
        table.add_row("Inactive Offers", str(stats["inactive_offers"]))
        table.add_row("Search URLs", str(stats["search_urls"]))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def export(
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
    output_path: str = typer.Option(
        "exported_offers.xlsx", "--output", "-o", help="Output file path"
    ),
    include_inactive: bool = typer.Option(
        False, "--include-inactive", help="Include inactive offers in export"
    ),
) -> None:
    """Export offers to a new file."""
    try:
        database = OfferDatabase(database_path)

        if include_inactive:
            offers = database.load_offers()
            console.print(f"Exporting {len(offers)} total offers...")
        else:
            offers = database.get_active_offers()
            console.print(f"Exporting {len(offers)} active offers...")

        if offers.empty:
            console.print("[yellow]No offers to export[/yellow]")
            return

        # Save to new file
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        offers.to_excel(output_path, index=False, engine="openpyxl")

        console.print(f"[green]Exported to {output_path}[/green]")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


def display_update_results(stats: dict) -> None:
    """Display the results of an update operation."""
    table = Table(title="Update Results")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Total offers found", str(stats["total_found"]))
    table.add_row("New offers added", str(stats["new_offers"]))
    table.add_row("Existing offers updated", str(stats["updated_offers"]))
    table.add_row("Offers marked inactive", str(stats["inactive_offers"]))
    table.add_row("Failed scrapes", str(stats["failed_scrapes"]))
    table.add_row("Duration (seconds)", f"{stats['duration_seconds']:.1f}")

    console.print(table)

    # Show summary message
    if stats["new_offers"] > 0:
        console.print(f"[green]✓ Added {stats['new_offers']} new offers[/green]")
    if stats["updated_offers"] > 0:
        console.print(
            f"[blue]✓ Updated {stats['updated_offers']} existing offers[/blue]"
        )
    if stats["inactive_offers"] > 0:
        console.print(
            f"[yellow]⚠ Marked {stats['inactive_offers']} offers as inactive[/yellow]"
        )
    if stats["failed_scrapes"] > 0:
        console.print(f"[red]✗ {stats['failed_scrapes']} offers failed to scrape[/red]")


if __name__ == "__main__":
    app()
