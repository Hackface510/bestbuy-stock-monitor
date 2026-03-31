import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger("bestbuy_monitor")


class DiscordNotifier:
      def __init__(self, webhook_url: str, max_retries: int = 3):
                self.webhook_url = webhook_url
                self.max_retries = max_retries
                self.session: Optional[aiohttp.ClientSession] = None

      async def __aenter__(self):
                self.session = aiohttp.ClientSession(
                              timeout=aiohttp.ClientTimeout(total=10)
                )
                return self

      async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.session:
                              await self.session.close()
                              self.session = None

            async def _send(self, payload: dict, is_essential: bool = False) -> bool:
                      if not self.session:
                                    raise RuntimeError(
                                                      "DiscordNotifier not initialized. Use 'async with DiscordNotifier(...)'."
                                    )
                                for attempt in range(self.max_retries):
                                              try:
                                                                async with self.session.post(self.webhook_url, json=payload) as resp:
                                                                                      if resp.status in (200, 204):
                                                                                                                return True
                                                                                                            if resp.status == 429:
                                                                                                                                      retry_after = resp.headers.get("Retry-After", "5")
                                                                                                                                      try:
                                                                                                                                                                    wait_time = float(retry_after)
                                                                                                              except ValueError:
                                                                                              wait_time = 5.0
                                                                                                                                        logger.warning(f"Rate limited, waiting {wait_time}s")
                                                                                                                                        await asyncio.sleep(wait_time)
                                                                                                                                        continue
                                                                                                                                    text = await resp.text()
                    log_fn = logger.error if is_essential else logger.warning
                    log_fn(f"Discord HTTP {resp.status}: {text[:200]}")
except aiohttp.ClientError as e:
                log_fn = logger.error if is_essential else logger.warning
                log_fn(f"Discord connection error (attempt {attempt + 1}): {e}")
except asyncio.TimeoutError:
                log_fn = logger.error if is_essential else logger.warning
                log_fn(f"Discord timeout (attempt {attempt + 1})")
            if attempt < self.max_retries - 1:
                              wait = 2 ** attempt
                logger.info(f"Retrying Discord in {wait}s...")
                await asyncio.sleep(wait)
        return False

    async def send_alert(self, item: dict, check_num: int) -> bool:
              color = 0x00FF00 if item.get("pickup") else 0x0099FF
        fields = [
                      {"name": "Store", "value": f"#{item['store_id']} ({item['store_name']})", "inline": True},
                      {"name": "Price", "value": item.get("price", "Check site"), "inline": True},
                      {"name": "SKU", "value": item["sku"], "inline": True},
        ]
        if item.get("pickup"):
                      fields.append({"name": "Pickup", "value": "Available for store pickup", "inline": False})
        if item.get("shipping"):
                      fields.append({"name": "Shipping", "value": "Available for delivery", "inline": False})
        payload = {
                      "content": "@everyone" if item.get("pickup") else None,
                      "allowed_mentions": {"parse": ["everyone"]} if item.get("pickup") else {"parse": []},
                      "embeds": [{
                                        "title": "In Stock!",
                                        "description": f"**{item['sku']}** available at Best Buy #{item['store_id']}!",
                                        "url": item["url"],
                                        "color": color,
                                        "timestamp": datetime.utcnow().isoformat(),
                                        "fields": fields,
                                        "footer": {"text": f"BestBuy Monitor - Check #{check_num}"},
                      }],
                      "username": "Stock Alert Bot",
                      "avatar_url": "https://www.bestbuy.com/favicon.ico",
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        success = await self._send(payload)
        if success:
                      logger.info(f"Alert sent for {item['sku']} at store {item['store_id']}")
        return success

    async def send_startup(self, skus: list, stores: list, interval: int) -> bool:
              store_names = {"138": "Pinole", "135": "Pleasant Hill", "324": "Emeryville", "482": "San Francisco"}
        sku_display = ", ".join(skus[:5]) + (f" (+{len(skus)-5} more)" if len(skus) > 5 else "")
        payload = {
                      "content": "BestBuy Monitor started",
                      "embeds": [{
                                        "title": "Monitor Initialized",
                                        "description": f"Watching {len(skus)} SKU(s) at {len(stores)} store(s)",
                                        "color": 0x00FF00,
                                        "fields": [
                                                              {"name": "SKUs", "value": sku_display, "inline": False},
                                                              {"name": "Stores", "value": ", ".join([f"{s} ({store_names.get(s, s)})" for s in stores]), "inline": False},
                                                              {"name": "Interval", "value": f"{interval}s", "inline": True},
                                        ],
                                        "timestamp": datetime.utcnow().isoformat(),
                      }],
        }
        return await self._send(payload, is_essential=True)

    async def send_shutdown(self, uptime: str, total_checks: int, total_alerts: int) -> bool:
              payload = {
                            "embeds": [{
                                              "title": "Monitor Stopped",
                                              "color": 0xFF0000,
                                              "fields": [
                                                                    {"name": "Uptime", "value": uptime, "inline": True},
                                                                    {"name": "Total Checks", "value": str(total_checks), "inline": True},
                                                                    {"name": "Total Alerts", "value": str(total_alerts), "inline": True},
                                              ],
                                              "timestamp": datetime.utcnow().isoformat(),
                            }],
              }
        return await self._send(payload, is_essential=True)

    async def send_heartbeat(self, uptime: str, checks: int, alerts: int) -> bool:
              payload = {
                            "embeds": [{
                                              "title": "Health Check",
                                              "description": "Monitor is healthy",
                                              "color": 0xFFFF00,
                                              "fields": [
                                                                    {"name": "Uptime", "value": uptime, "inline": True},
                                                                    {"name": "Checks", "value": str(checks), "inline": True},
                                                                    {"name": "Alerts", "value": str(alerts), "inline": True},
                                              ],
                                              "timestamp": datetime.utcnow().isoformat(),
                            }],
              }
        return await self._send(payload)
