import click
import sys
import os
import asyncio

# Đảm bảo Python tìm thấy package app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.database import create_all_tables
from app.services.seeders import seed_master_data, seed_cleansing_queue, check_database_stats
from app.services.osm_fetcher import OSMFetcher
from app.services.synthetic_mixer import SyntheticMixerPro
from app.services.exporter import export_training_data
# from app.services.gso_playwright_crawler import GSOPlywrightCrawler
from app.services.seeders_v2 import seed_admin_v2, seed_ward_mapping, check_v2_stats
from app.services.seeders_v3 import run_seed_v3, check_v3_stats
from app.services.enrichment import enrich_provinces, enrich_wards, check_enrichment_stats

from app.core.logging_config import setup_logging

@click.group()
def cli():
    """Smart Address Intelligence Management System (VN Address Intelligence)"""
    setup_logging()

@cli.command()
def init_db():
    """Initialize Schemas and tables in DB."""
    click.echo("--- Initializing Database ---")
    create_all_tables()
    click.echo("OK: Database initialized.")

@cli.command()
@click.option('--dir', default='data/seed', help='Directory containing master data CSV files.')
def seed_master(dir):
    """Import administrative master data (Province, District, Ward)."""
    click.echo(f"--- Importing Master Data from {dir} ---")
    seed_master_data(dir)

@cli.command()
@click.option('--file', default='data/seed/address_cleansing_queue.csv', help='Path to queue CSV file.')
def seed_queue(file):
    """Import raw addresses into cleansing queue."""
    click.echo(f"--- Importing Queue Data from {file} ---")
    seed_cleansing_queue(file)

@cli.command()
@click.option('--limit', default=63, help='Number of provinces to fetch.')
@click.option('--target', default=5000000, help='Target total raw entities count.')
def fetch_osm(limit, target):
    """Fetch Streets, Buildings, POIs from OpenStreetMap by province."""
    click.echo(f"--- Fetching OSM data (limit {limit} provinces, target {target} entities) ---")
    fetcher = OSMFetcher()
    fetcher.fetch_all_provinces(limit_provinces=limit, target_total=target)

@cli.command()
@click.option('--count', default=1000, help='Number of samples to generate.')
def generate_synthetic(count):
    """Generate high-quality synthetic address-line with BIO tags."""
    click.echo(f"--- Generating {count} high-quality synthetic samples ---")
    mixer = SyntheticMixerPro()
    mixer.generate_batch(count)

@cli.command()
@click.option('--output', default='data/training_data.jsonl', help='Output file path.')
def export_train_data(output):
    """Export training data to JSONL format."""
    click.echo(f"--- Exporting data to {output} ---")
    export_training_data(output)

@cli.command()
def check_db():
    """Check database statistics (row counts) with growth rate."""
    from tabulate import tabulate
    click.echo("\n" + "="*60)
    click.echo("[STATS] VN ADDRESS INTELLIGENCE - DATABASE MONITORING")
    click.echo("="*60)
    
    stats, growth, time_diff = check_database_stats()
    
    table_data = []
    for table, count in stats.items():
        g_val = growth.get(table, 0)
        g_str = f"+{g_val}" if g_val > 0 else "-"
        table_data.append([table, f"{count:,}", g_str])
    
    headers = ["Table Name", "Total Rows", "Growth (est. 3m)"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    if time_diff > 0:
        click.echo(f"\n[TIME] Last check was {int(time_diff)}s ago.")
    click.echo("="*60 + "\n")

@cli.command()
@click.option('--start', default=1, help='Start page.')
@click.option('--end', default=5, help='End page.')
def crawl_gso(start, end):
    """Crawl Population and Area from GSO website using Playwright."""
    from app.services.gso_playwright_crawler import GSOPlywrightCrawler
    click.echo(f"--- Starting GSO Crawler (Page {start} to {end}) ---")
    crawler = GSOPlywrightCrawler()
    asyncio.run(crawler.run(start_page=start, end_page=end))
@cli.command()
def seed_v2():
    """Seed Admin Version 2 and Ward Mapping from CSV files."""
    base_path = "data/seed"
    
    click.echo("--- Seeding Admin Version 2 Data ---")
    seed_admin_v2(f"{base_path}/province_admin_version_2.csv", "mat.province", "province_id")
    seed_admin_v2(f"{base_path}/district_admin_version_2.csv", "mat.district", "district_id")
    seed_admin_v2(f"{base_path}/ward_admin_version_2.csv", "mat.ward", "ward_id")
    
    click.echo("--- Seeding Ward Mapping ---")
    seed_ward_mapping(f"{base_path}/ward_mapping.csv")
    
    click.echo("\n--- Verification Results ---")
    stats = check_v2_stats()
    for name, count in stats.items():
        click.echo(f"{name:20} : {count:10} rows")
@cli.command()
def enrich_v2():
    """Enrich Administrative Data with GSO Gov details (Decisions, Notes)."""
    base_path = "data/seed"
    
    click.echo("--- Enriching Data from GSO Gov ---")
    enrich_provinces(f"{base_path}/nso-gov-province_25_04_2026.csv")
    enrich_wards(f"{base_path}/nso-gov-ward_25_04_2026.csv")
    
    click.echo("\n--- Enrichment Results ---")
    stats = check_enrichment_stats()
    for name, count in stats.items():
        click.echo(f"{name:25} : {count:10} rows")

@cli.command('seed_v3')
@click.option('--file', default='data/seed/AdministrativeUnitConversion.xlsx', help='Path to AdministrativeUnitConversion file (.xlsx or .csv)')
def seed_v3(file):
    """Import administrative v3 data from conversion file.
    
    Process:
      1. Mark is_deleted=True for all old data (4 tables in mat schema)
      2. Insert new Province/District/Ward (admin_version=2)
      3. Insert WardMapping v1 to v2
    """
    from tabulate import tabulate
    click.echo(f"--- Starting SeederV3 from {file} ---")
    run_seed_v3(file)
    
    click.echo("\n--- Final Stats ---")
    stats = check_v3_stats()
    table_data = [[k, f"{v:,}" if isinstance(v, int) else v] for k, v in stats.items()]
    click.echo(tabulate(table_data, headers=["Table / Status", "Count"], tablefmt="grid"))

if __name__ == "__main__":
    cli()
