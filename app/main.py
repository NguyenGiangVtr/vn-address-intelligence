from __future__ import annotations
import click
import sys
import os
import asyncio
from tabulate import tabulate

# Đảm bảo Python tìm thấy package app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.database import create_all_tables, SessionLocal
from sqlalchemy import text as sql_text
from app.services.seeders import seed_master_data, seed_cleansing_queue, check_database_stats
from app.services.osm_fetcher import OSMFetcher
from app.services.synthetic_mixer import SyntheticMixerPro
from app.services.exporter import export_training_data
from app.services.seeders_v2 import seed_admin_v2, seed_ward_mapping, check_v2_stats
from app.services.seeders_v3 import run_seed_v3, check_v3_stats
from app.services.enrichment import enrich_provinces, enrich_wards, check_enrichment_stats
from app.services.admin_mapping import run_admin_mapping
from app.core.logging_config import setup_logging

@click.group()
def cli():
    """Smart Address Intelligence Management System (VN Address Intelligence) CLI"""
    setup_logging()

# =============================================================================
# GROUP: ADMIN (ĐƠN VỊ HÀNH CHÍNH)
# =============================================================================

@cli.command('admin:init')
def admin_init():
    """[1] Initialize Schemas and tables in Database."""
    click.echo("--- Initializing Database ---")
    create_all_tables()
    click.echo("OK: Database initialized.")

@cli.command('admin:seed')
@click.option('--file', default='data/seed/AdministrativeUnitConversion.xlsx', help='Path to conversion file (.xlsx or .csv)')
def admin_seed(file):
    """[2] Seed administrative data from Excel/CSV (Admin Version 2)."""
    click.echo(f"--- Starting Admin Seeder from {file} ---")
    run_seed_v3(file)
    click.echo("OK: Seeding completed.")

@cli.command('admin:map')
def admin_map():
    """[3] Map OLD IDs to NEW IDs (Synchronize old_id columns)."""
    click.echo("--- Starting Admin ID Mapping ---")
    run_admin_mapping()
    click.echo("OK: Mapping completed.")

@cli.command('admin:stats')
def admin_stats():
    """[4] Show detailed administrative unit statistics."""
    click.echo("\n" + "="*60)
    click.echo("[STATS] VN ADDRESS INTELLIGENCE - ADMIN MONITORING")
    click.echo("="*60)
    
    # Check V3 specific stats
    stats_v3 = check_v3_stats()
    table_data = [[k, f"{v:,}" if isinstance(v, int) else v] for k, v in stats_v3.items()]
    
    # Add mapped ratios
    new_db = SessionLocal()
    try:
        p_mapped = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.province WHERE old_id IS NOT NULL')).scalar()
        p_total = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.province')).scalar()
        d_mapped = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.district WHERE old_id IS NOT NULL')).scalar()
        d_total = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.district')).scalar()
        w_mapped = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.ward WHERE old_id IS NOT NULL')).scalar()
        w_total = new_db.execute(sql_text('SELECT COUNT(*) FROM mat.ward')).scalar()
        
        table_data.append(["---", "---"])
        table_data.append(["Province Mapped", f"{p_mapped}/{p_total} ({p_mapped/p_total*100:.1f}%)"])
        table_data.append(["District Mapped", f"{d_mapped}/{d_total} ({d_mapped/d_total*100:.1f}%)"])
        table_data.append(["Ward Mapped", f"{w_mapped}/{w_total} ({w_mapped/w_total*100:.1f}%)"])
    finally:
        new_db.close()

    click.echo(tabulate(table_data, headers=["Category", "Value"], tablefmt="grid"))
    click.echo("="*60 + "\n")

# =============================================================================
# GROUP: DATA & OSM (DỮ LIỆU & OSM)
# =============================================================================

@cli.command('osm:fetch')
@click.option('--limit', default=63, help='Number of provinces.')
@click.option('--target', default=5000000, help='Target entities count.')
def osm_fetch(limit, target):
    """Fetch Streets, Buildings, POIs from OpenStreetMap."""
    click.echo(f"--- Fetching OSM data ---")
    fetcher = OSMFetcher()
    fetcher.fetch_all_provinces(limit_provinces=limit, target_total=target)

@cli.command('data:generate')
@click.option('--count', default=1000, help='Sample count.')
def data_generate(count):
    """Generate synthetic address-line with BIO tags."""
    click.echo(f"--- Generating {count} synthetic samples ---")
    mixer = SyntheticMixerPro()
    mixer.generate_batch(count)

@cli.command('data:export')
@click.option('--output', default='data/training_data.jsonl', help='Output file path.')
def data_export(output):
    """Export training data to JSONL format."""
    click.echo(f"--- Exporting to {output} ---")
    export_training_data(output)

# =============================================================================
# ALIASES (TƯƠNG THÍCH NGƯỢC)
# =============================================================================
@cli.command('seed_v3', hidden=True)
@click.pass_context
def alias_seed_v3(ctx, **kwargs):
    ctx.invoke(admin_seed, **kwargs)

@cli.command('check_db', hidden=True)
@click.pass_context
def alias_check_db(ctx):
    ctx.invoke(admin_stats)

if __name__ == "__main__":
    cli()
