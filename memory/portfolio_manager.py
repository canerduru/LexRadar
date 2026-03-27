"""
Portfolio CRUD wrapper and CLI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any, Dict, List

import structlog

from config.settings import Settings, get_settings
from memory.schema import PortfolioItem
from memory.vector_store import ChromaMemory


class PortfolioManager:
    """
    Simple CRUD wrapper over ChromaMemory for portfolio items.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = structlog.get_logger()
        self._memory = ChromaMemory(settings)

    async def add_item(self, item_dict: Dict[str, Any]) -> PortfolioItem:
        if "id" not in item_dict:
            item_dict["id"] = uuid.uuid4()
        if "created_at" not in item_dict:
            from datetime import datetime, timezone
            item_dict["created_at"] = datetime.now(timezone.utc).isoformat()
            
        item = PortfolioItem.model_validate(item_dict)
        await self._memory.upsert_portfolio_item(item)
        self._logger.info("Portfolio item added", item_id=str(item.id), client=item.client_name)
        return item

    async def update_item(self, item_id: str, updates: Dict[str, Any]) -> PortfolioItem | None:
        items = await self.list_all()
        for item in items:
            if str(item.id) == item_id:
                item_dict = item.model_dump()
                item_dict.update(updates)
                updated_item = PortfolioItem.model_validate(item_dict)
                await self._memory.upsert_portfolio_item(updated_item)
                self._logger.info("Portfolio item updated", item_id=item_id)
                return updated_item
        self._logger.warning("Portfolio item not found for update", item_id=item_id)
        return None

    async def remove_item(self, item_id: str) -> None:
        await self._memory.delete_portfolio_item(item_id)
        self._logger.info("Portfolio item removed", item_id=item_id)

    async def list_all(self) -> List[PortfolioItem]:
        return await self._memory.get_all_portfolio()

    async def import_from_json(self, path: str) -> None:
        """Bulk import from a JSON file."""
        self._logger.info("Importing portfolio items from JSON", path=path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                self._logger.error("JSON should contain a list of portfolio items.")
                return
                
            imported = 0
            for item_dict in data:
                await self.add_item(item_dict)
                imported += 1
                
            self._logger.info("Portfolio import complete", total_imported=imported)
            
        except Exception as e:
            self._logger.error("Failed to import portfolio JSON", path=path, error=str(e))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio Manager CLI")
    parser.add_argument("--import", dest="import_path", type=str, help="Path to portfolio_seed.json to import")
    parser.add_argument("--list", action="store_true", help="List all portfolio items")
    args = parser.parse_args()

    # Configure logging
    import logging
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.ConsoleRenderer(),
        ],
    )

    manager = PortfolioManager(settings)
    
    if args.import_path:
        await manager.import_from_json(args.import_path)
    elif args.list:
        items = await manager.list_all()
        for item in items:
            print(f"- {item.id}: {item.client_name} - {item.asset_type} in {item.district}, {item.city}")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
