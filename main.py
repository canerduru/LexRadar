"""
Main CLI entrypoint for Real Estate Intelligence Radar.
"""

import asyncio
import click

from config.settings import get_settings
from radar.orchestrator import PipelineOrchestrator
from radar.scheduler import PipelineScheduler
from radar.dashboard import ConsoleDashboard
from memory.portfolio_manager import PortfolioManager


@click.group()
def cli() -> None:
    """Real Estate Intelligence Radar CLI"""
    pass


@cli.command()
def start() -> None:
    """Start the APScheduler for 24/7 autonomous daily execution."""
    scheduler = PipelineScheduler()
    asyncio.run(scheduler.start())


@cli.command()
@click.option("--days-back", type=int, default=1, help="Number of days to scan backwards.")
def run_now(days_back: int) -> None:
    """Execute the full Hunter->Parser->Brain->Memory->Radar pipeline immediately."""
    settings = get_settings()
    orchestrator = PipelineOrchestrator(settings)
    asyncio.run(orchestrator.run_full_pipeline(days_back=days_back))


@cli.command()
def dashboard() -> None:
    """Show the rich terminal dashboard containing system status and recent alerts."""
    dash = ConsoleDashboard()
    dash.print_status()


@cli.command()
@click.option("--import-file", "-i", "import_path", required=True, type=str, help="Path to portfolio JSON file")
def add_portfolio(import_path: str) -> None:
    """Bulk import B2B portfolio records from JSON."""
    settings = get_settings()
    manager = PortfolioManager(settings)
    asyncio.run(manager.import_from_json(import_path))


if __name__ == "__main__":
    cli()
