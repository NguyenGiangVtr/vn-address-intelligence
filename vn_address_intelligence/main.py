import click
import sys
import os

# Đảm bảo Python tìm thấy thư mục src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.database import create_all_tables
from src.seeders import seed_master_data
from src.osm_fetcher import OSMFetcher
from src.synthetic_mixer import SyntheticMixerPro
from src.exporter import export_training_data

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
@click.option('--limit', default=5, help='Number of provinces to fetch.')
def fetch_osm(limit):
    """Fetch Streets, Buildings, POIs from OpenStreetMap by province."""
    click.echo(f"--- Fetching OSM data (limit {limit} provinces) ---")
    fetcher = OSMFetcher()
    fetcher.fetch_all_provinces(limit_provinces=limit)

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

if __name__ == "__main__":
    cli()
