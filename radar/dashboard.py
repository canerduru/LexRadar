"""
Rich terminal dashboard for tracking Intelligence processing.
"""

from __future__ import annotations

import json
import os
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from datetime import datetime, timedelta, timezone

from config.settings import get_settings
from memory.vector_store import ChromaMemory


class ConsoleDashboard:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._console = Console()
        self._memory = ChromaMemory(self._settings)

    def _get_last_run(self) -> dict:
        log_file = "data/pipeline_runs.jsonl"
        if not os.path.exists(log_file):
            return {}
        try:
            with open(log_file, "r") as f:
                lines = [l.strip() for l in f if l.strip()]
                if not lines:
                    return {}
                return json.loads(lines[-1])
        except Exception:
            return {}

    def _get_alert_counts(self) -> tuple[int, int]:
        log_file = "data/alert_log.jsonl"
        if not os.path.exists(log_file):
            return 0, 0
            
        today = datetime.now(timezone.utc).date()
        week_ago = today - timedelta(days=7)
        
        today_count = 0
        week_count = 0
        
        try:
            with open(log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    if "timestamp" in record:
                        row_date = datetime.fromisoformat(record["timestamp"]).date()
                        if row_date == today:
                            today_count += 1
                        if row_date >= week_ago:
                            week_count += 1
        except Exception:
            pass
            
        return today_count, week_count

    def print_status(self) -> None:
        # Fetch DB metrics directly
        intel_count = self._memory._intel_collection.count()
        port_count = self._memory._portfolio_collection.count()
        
        last_run = self._get_last_run()
        alerts_today, alerts_week = self._get_alert_counts()
        
        # Build Stats Table
        stats_table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_header=False)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="bold white")
        
        # Format Run string
        run_time = last_run.get("started_at", "Never")
        if run_time != "Never":
            run_time = datetime.fromisoformat(run_time).strftime("%Y-%m-%d %H:%M:%S")
            duration = "N/A"
            if last_run.get("finished_at"):
                rt = datetime.fromisoformat(last_run["started_at"])
                ft = datetime.fromisoformat(last_run["finished_at"])
                duration = f"{(ft - rt).total_seconds():.1f}s"
            run_time = f"{run_time} ({duration})"
            
        stats_table.add_row("Last Pipeline Run", run_time)
        stats_table.add_row("Docs Processed", str(last_run.get("reports_generated", 0)))
        stats_table.add_row("ChromaDB Intel Entries", str(intel_count))
        stats_table.add_row("ChromaDB Portfolio Items", str(port_count))
        stats_table.add_row("Alerts Sent Today", str(alerts_today))
        stats_table.add_row("Alerts Sent This Week", str(alerts_week))

        panel = Panel(stats_table, title="[bold magenta]🏗️ LandIntel Radar Dashboard", border_style="cyan")
        self._console.print(panel)


def main() -> None:
    dash = ConsoleDashboard()
    dash.print_status()

if __name__ == "__main__":
    main()
