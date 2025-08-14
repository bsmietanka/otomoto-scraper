"""Command line interface for the otomoto offer manager."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .database import OfferDatabase
from .offer_manager import OfferManager
from .pricing_model import CarPricingModel

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
def cleanup(
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be removed without actually removing"
    ),
) -> None:
    """Remove duplicate offers from the database."""
    try:
        database = OfferDatabase(database_path)

        if dry_run:
            # For dry run, just show what would be removed
            offers = database.load_offers()
            if offers.empty:
                console.print("[yellow]Database is empty, nothing to clean up[/yellow]")
                return

            duplicated_urls = offers[offers["url"].duplicated(keep=False)]
            if duplicated_urls.empty:
                console.print("[green]No duplicates found to remove[/green]")
            else:
                duplicate_count = len(duplicated_urls) - len(
                    duplicated_urls["url"].unique()
                )
                console.print(
                    f"[yellow]Dry run: Would remove {duplicate_count} duplicate entries[/yellow]"
                )
        else:
            # Actually remove duplicates
            removed_count = database.remove_duplicates()
            if removed_count > 0:
                console.print(
                    f"[green]✓ Removed {removed_count} duplicate entries[/green]"
                )
            else:
                console.print("[green]✓ No duplicates found to remove[/green]")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


@app.command()
def verify(
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
) -> None:
    """Verify database integrity by checking for duplicate URLs."""
    try:
        database = OfferDatabase(database_path)
        offers = database.load_offers()

        if offers.empty:
            console.print("[yellow]Database is empty, nothing to verify[/yellow]")
            return

        # Check for duplicate URLs
        duplicated_urls = offers[offers["url"].duplicated(keep=False)]

        if duplicated_urls.empty:
            console.print("[green]✓ No duplicate URLs found in database[/green]")
            console.print(f"Verified {len(offers)} unique offers")
        else:
            # Group duplicates by URL
            duplicate_groups = duplicated_urls.groupby("url")

            console.print(
                f"[red]✗ Found {len(duplicate_groups)} URLs with duplicates[/red]"
            )

            # Create table showing duplicates
            table = Table(title="Duplicate URLs Found")
            table.add_column("URL", style="cyan", no_wrap=False)
            table.add_column("Count", style="red", justify="right")
            table.add_column("First Seen", style="yellow")
            table.add_column("Last Seen", style="yellow")

            for url, group in duplicate_groups:
                count = len(group)
                first_seen = (
                    group["first_seen"].min()
                    if "first_seen" in group.columns
                    else "N/A"
                )
                last_seen = (
                    group["last_seen"].max() if "last_seen" in group.columns else "N/A"
                )

                # Truncate long URLs for display
                url_str = str(url)
                display_url = url_str[:80] + "..." if len(url_str) > 80 else url_str
                table.add_row(display_url, str(count), str(first_seen), str(last_seen))

            console.print(table)

            # Show summary
            total_duplicates = len(duplicated_urls)
            console.print("\n[yellow]Summary:[/yellow]")
            console.print(f"Total offers: {len(offers)}")
            console.print(f"Duplicate entries: {total_duplicates}")
            console.print(
                f"Unique URLs: {len(offers) - total_duplicates + len(duplicate_groups)}"
            )

            console.print(
                "\n[blue]Tip:[/blue] You may want to clean up these duplicates manually"
            )

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


@app.command()
def pricing(
    database_path: str = typer.Option(
        "offers.xlsx", "--db", "-d", help="Path to the database file"
    ),
    output_path: str = typer.Option(
        "rated_offers.xlsx", "--output", "-o", help="Output file for rated offers"
    ),
    top_deals: int = typer.Option(
        15, "--top", "-t", help="Number of top deals to display"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
) -> None:
    """Build pricing model and rate car offers based on relative value within segments."""
    setup_logging(verbose)

    try:
        console.print(
            "[bold blue]Building relative pricing model and rating offers[/bold blue]"
        )
        console.print(f"Database: {database_path}")

        # Load data
        database = OfferDatabase(database_path)
        offers = database.get_active_offers()

        if offers.empty:
            console.print("[yellow]No active offers found in database[/yellow]")
            return

        console.print(f"Found {len(offers)} active offers")

        # Initialize and train model
        pricing_model = CarPricingModel()

        console.print("[blue]Training relative pricing model...[/blue]")
        results = pricing_model.train_model(offers)

        # Display model performance
        table = Table(title="Model Performance")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Samples Used", str(results["n_samples"]))
        table.add_row("Features", str(results["n_features"]))
        table.add_row("Brand/Model Segments", str(results["n_brand_models"]))
        table.add_row("R² Score", f"{results['r2']:.3f}")
        table.add_row("RMSE (ratio)", f"{results['rmse']:.3f}")
        table.add_row("MAE (ratio)", f"{results['mae']:.3f}")

        console.print(table)

        # Get model summary
        summary = pricing_model.get_model_summary()
        console.print("\n[blue]Data Summary:[/blue]")
        console.print(f"• Price range: {summary['price_range']}")
        console.print(f"• Year range: {summary['year_range']}")
        console.print(f"• Brands: {summary['brands']}")
        console.print(f"• Average price: {summary['avg_price']}")

        # Rate offers
        console.print("[blue]Rating offers based on relative value...[/blue]")
        rated_offers = pricing_model.rate_offers()

        # Display top deals
        console.print(f"\n[bold green]Top {top_deals} Value Deals:[/bold green]")

        deals_table = Table()
        deals_table.add_column("Rank", style="cyan", justify="right")
        deals_table.add_column("Brand/Model", style="white", no_wrap=False)
        deals_table.add_column("Year", style="yellow", justify="center")
        deals_table.add_column("Price", style="green", justify="right")
        deals_table.add_column("Expected", style="blue", justify="right")
        deals_table.add_column("Value Score", style="magenta", justify="right")
        deals_table.add_column("Category", style="cyan")

        top_offers = rated_offers.head(top_deals)

        for i, (_, offer) in enumerate(top_offers.iterrows(), 1):
            brand_model = f"{offer.get('Marka pojazdu', 'N/A')} {offer.get('Model pojazdu', 'N/A')}"
            if len(brand_model) > 20:
                brand_model = brand_model[:17] + "..."

            price_str = f"{offer['price']:,.0f}"
            expected_str = (
                f"{offer['predicted_price']:,.0f}"  # Use model prediction as "Expected"
            )
            value_score = f"{offer['value_score']:+.1f}%"

            deals_table.add_row(
                str(i),
                brand_model,
                str(int(offer["year"])),
                price_str,
                expected_str,
                value_score,
                offer["deal_category"],
            )

        console.print(deals_table)

        # Save rated offers
        console.print(f"\n[blue]Saving rated offers to {output_path}...[/blue]")

        # Select columns for export (ordered for better readability)
        export_columns = [
            # Deal assessment columns (most important first)
            "value_score",
            "deal_category",
            "price",
            "predicted_price",
            # Car identification
            "Marka pojazdu",
            "Model pojazdu",
            "year",
            "age",
            # Car specifications
            "mileage",
            "engine_capacity",
            "power",
            "Rodzaj paliwa",
            "Skrzynia biegów",
            "Typ nadwozia",
            # Additional metrics
            "expected_price",
            "mileage_per_year",
            "price_ratio",
            "predicted_ratio",
            # Reference data
            "url",
            "Cena",
            "Waluta",
            "Rok produkcji",
            "Przebieg",
            "Pojemność skokowa",
            "Moc",
        ]

        # Create export dataframe with available columns
        export_data = rated_offers[
            [col for col in export_columns if col in rated_offers.columns]
        ].copy()

        # Add useful derived columns
        if "predicted_price" in export_data.columns and "price" in export_data.columns:
            export_data["savings_pln"] = (
                export_data["predicted_price"] - export_data["price"]
            )

        # Round numeric columns for readability
        numeric_cols = [
            "price",
            "expected_price",
            "predicted_price",
            "savings_pln",
            "value_score",
            "mileage",
            "engine_capacity",
            "power",
            "mileage_per_year",
            "price_ratio",
            "predicted_ratio",
        ]
        for col in numeric_cols:
            if col in export_data.columns:
                if col == "value_score":
                    export_data[col] = export_data[col].round(1)
                elif col in ["price_ratio", "predicted_ratio"]:
                    export_data[col] = export_data[col].round(3)
                else:
                    export_data[col] = export_data[col].round(0)

        export_data.to_excel(output_path, index=False, engine="openpyxl")

        console.print(
            f"[green]✓ Saved {len(rated_offers)} rated offers to {output_path}[/green]"
        )

        # Summary statistics
        console.print("\n[bold blue]Deal Distribution:[/bold blue]")
        deal_counts = rated_offers["deal_category"].value_counts()

        summary_table = Table()
        summary_table.add_column("Category", style="cyan")
        summary_table.add_column("Count", style="magenta", justify="right")
        summary_table.add_column("Percentage", style="yellow", justify="right")

        for category, count in deal_counts.items():
            percentage = (count / len(rated_offers)) * 100
            summary_table.add_row(category, str(count), f"{percentage:.1f}%")

        console.print(summary_table)

        # Best deal highlight
        best_deal = rated_offers.iloc[0]
        console.print("\n[bold green]🏆 Best Value Deal:[/bold green]")
        console.print(
            f"   {best_deal.get('Marka pojazdu', 'N/A')} {best_deal.get('Model pojazdu', 'N/A')} ({int(best_deal['year'])})"
        )
        console.print(f"   Price: {best_deal['price']:,.0f} PLN")
        console.print(
            f"   Expected by model: {best_deal['predicted_price']:,.0f} PLN"
        )  # Use model prediction
        console.print(
            f"   Value score: {best_deal['value_score']:+.1f}% ({best_deal['deal_category']})"
        )

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
