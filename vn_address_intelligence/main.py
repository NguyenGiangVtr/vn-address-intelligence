import click
import sys
import os
import asyncio

# Đảm bảo Python tìm thấy thư mục src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.database import create_all_tables
from src.seeders import seed_master_data, seed_cleansing_queue, check_database_stats
from src.osm_fetcher import OSMFetcher
from src.synthetic_mixer import SyntheticMixerPro
from src.exporter import export_training_data
# from src.gso_playwright_crawler import GSOPlywrightCrawler  <-- Move this
from src.seeders_v2 import seed_admin_v2, seed_ward_mapping, check_v2_stats
from src.enrichment_v2 import enrich_provinces, enrich_wards, check_enrichment_stats

@click.group()
def cli():
    """Hệ thống Quản lý Dữ liệu Địa chỉ Thông minh (VN Address Intelligence)"""
    pass

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
@click.option('--file', default='vn_address_intelligence/data/seed/address_cleansing_queue.csv', help='Path to queue CSV file.')
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
@click.option('--output', default='vn_address_intelligence/data/training_data.jsonl', help='Output file path.')
def export_train_data(output):
    """Export training data to JSONL format."""
    click.echo(f"--- Exporting data to {output} ---")
    export_training_data(output)

@cli.command()
def check_db():
    """Check database statistics (row counts)."""
    click.echo("--- Database Statistics ---")
    stats = check_database_stats()
    for table, count in stats.items():
        click.echo(f"Table {table:30} : {count:10} rows")

@cli.command()
@click.option('--start', default=1, help='Start page.')
@click.option('--end', default=5, help='End page.')
def crawl_gso(start, end):
    """Crawl Population and Area from GSO website using Playwright."""
    from src.gso_playwright_crawler import GSOPlywrightCrawler
    click.echo(f"--- Starting GSO Crawler (Page {start} to {end}) ---")
    crawler = GSOPlywrightCrawler()
    asyncio.run(crawler.run(start_page=start, end_page=end))
@cli.command()
def seed_v2():
    """Seed Admin Version 2 and Ward Mapping from CSV files."""
    base_path = "vn_address_intelligence/data/seed"
    
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
    base_path = "vn_address_intelligence/data/seed"
    
    click.echo("--- Enriching Data from GSO Gov ---")
    enrich_provinces(f"{base_path}/nso-gov-province_25_04_2026.csv")
    enrich_wards(f"{base_path}/nso-gov-ward_25_04_2026.csv")
    
    click.echo("\n--- Enrichment Results ---")
    stats = check_enrichment_stats()
    for name, count in stats.items():
        click.echo(f"{name:25} : {count:10} rows")

if __name__ == "__main__":
    cli()
