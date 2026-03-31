import asyncio
import logging
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

from .config import Config
from .notifier import DiscordNotifier
from .state import StateManager

logger = logging.getLogger("bestbuy_monitor")

STORE_NAMES = {
      "138": "Pinole",
      "135": "Pleasant Hill",
      "324": "Emeryville",
      "482": "San Francisco",
}


class BestBuyMonitor:
      def __init__(self, config: Config):
                self.config = config
                self.state = StateManager(config.state_file)
                self.notifier: Optional[DiscordNotifier] = None
                self.browser: Optional[Browser] = None
                self.context: Optional[BrowserContext] = None
                self.page: Optional[Page] = None
                self.playwright = None
                self.playwright_cm = None
                self.start_time = datetime.now()
                self.consecutive_failures = 0
                self.last_health_check = 0.0
                self.check_num = 0

      @property
      def uptime(self) -> str:
                delta = datetime.now() - self.start_time
                h, rem = divmod(int(delta.total_seconds()), 3600)
                m, s = divmod(rem, 60)
                return f"{h}h {m}m {s}s"

      def setup_logging(self):
                Path("logs").mkdir(exist_ok=True)
                log_file = f"logs/monitor_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
                root = logging.getLogger("bestbuy_monitor")
                if root.handlers:
                              return
                          logging.basicConfig(
                    level=getattr(logging, self.config.log_level.upper(), logging.INFO),
                    format="%(asctime)s | %(levelname)-8s | %(message)s",
                    datefmt="%H:%M:%S",
                    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
                    force=True,
                )

      async def cleanup_browser(self):
                for attr in ("context", "browser"):
                              obj = getattr(self, attr, None)
                              if obj:
                                                try:
                                                                      await obj.close()
except Exception:
                    pass
        if self.playwright_cm:
                      try:
                                        await self.playwright_cm.__aexit__(None, None, None)
except Exception:
                pass
        self.page = self.context = self.browser = self.playwright = self.playwright_cm = None

    async def init_browser(self) -> bool:
              for attempt in range(3):
                            try:
                                              await self.cleanup_browser()
                                              stealth = Stealth()
                                              self.playwright_cm = stealth.use_async(async_playwright())
                                              self.playwright = await self.playwright_cm.__aenter__()
                                              self.browser = await self.playwright.chromium.launch(
                                                  headless=True, args=["--disable-blink-features=AutomationControlled"]
                                              )
                                              self.context = await self.browser.new_context(
                                                  viewport={"width": 1920, "height": 1080},
                                                  user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                                  locale="en-US",
                                                  timezone_id="America/Los_Angeles",
                                              )
                                              self.page = await self.context.new_page()
                                              await self.page.goto("https://www.bestbuy.com", wait_until="domcontentloaded", timeout=30000)
                                              await asyncio.sleep(2)
                                              for sel in ['button:has-text("Skip")', 'button:has-text("No, thanks")', ".c-close-icon"]:
                                                                    try:
                                                                                              await self.page.click(sel, timeout=2000)
                                                                                              break
                            except Exception:
                                                      continue
                                              logger.info(f"Browser initialized (attempt {attempt + 1})")
                                return True
except Exception as e:
                logger.error(f"Browser init failed (attempt {attempt + 1}): {e}")
                await self.cleanup_browser()
                await asyncio.sleep(2 ** attempt)
        return False

    async def check_store(self, store_id: str) -> list:
              if not self.page:
                            return []
                        skus = ",".join(self.config.skus)
        ts = int(time.time())
        url = f"https://www.bestbuy.com/api/tcl/products/v1/availability?skus={skus}&storeId={store_id}&t={ts}"
        try:
                      result = await self.page.evaluate(
                                        """async (url) => {
                                                            const ctrl = new AbortController();
                                                                                const t = setTimeout(() => ctrl.abort(), 15000);
                                                                                                    try {
                                                                                                                            const r = await fetch(url, {
                                                                                                                                                        credentials: 'include',
                                                                                                                                                                                    signal: ctrl.signal,
                                                                                                                                                                                                                headers: { 'Accept': 'application/json', 'Referer': 'https://www.bestbuy.com/' }
                                                                                                                                                                                                                                        });
                                                                                                                                                                                                                                                                clearTimeout(t);
                                                                                                                                                                                                                                                                                        if (!r.ok) return { error: `HTTP ${r.status}` };
                                                                                                                                                                                                                                                                                                                return await r.json();
                                                                                                                                                                                                                                                                                                                                    } catch(e) {
                                                                                                                                                                                                                                                                                                                                                            clearTimeout(t);
                                                                                                                                                                                                                                                                                                                                                                                    return { error: e.message, type: e.name };
                                                                                                                                                                                                                                                                                                                                                                                                        }
                                                                                                                                                                                                                                                                                                                                                                                                                        }""",
                                        url,
                      )
                      if result.get("error"):
                                        logger.warning(f"Store {store_id} API error: {result['error']}")
                                        self.consecutive_failures += 1
                                        return []
                                    self.consecutive_failures = 0
            return self.parse_items(result, store_id)
except Exception as e:
            logger.error(f"Store {store_id} check exception: {e}")
            self.consecutive_failures += 1
            return []

    def parse_items(self, data: dict, store_id: str) -> list:
              found = []
        if not isinstance(data, dict):
                      return found
        for item in data.get("availabilities", []):
                      if not isinstance(item, dict):
                                        continue
                                    sku = item.get("sku")
            if not sku:
                              continue
                          pickup = item.get("pickup")
            shipping = item.get("shipping")
            sold_out = item.get("soldOut")
            pickup_avail = (isinstance(pickup, dict) and (pickup.get("purchasable") or pickup.get("status") == "IN_STOCK" or pickup.get("available"))) or pickup is True
            shipping_avail = (isinstance(shipping, dict) and (shipping.get("purchasable") or shipping.get("available") or shipping.get("inStock"))) or shipping is True
            if (pickup_avail or shipping_avail) and not sold_out:
                              price_data = item.get("price", {})
                              current_price = isinstance(price_data, dict) and (price_data.get("currentPrice") or price_data.get("salePrice"))
                              found.append({
                                  "sku": sku,
                                  "store_id": store_id,
                                  "store_name": STORE_NAMES.get(store_id, f"Store {store_id}"),
                                  "pickup": pickup_avail,
                                  "shipping": shipping_avail,
                                  "price": f"${current_price}" if current_price else "Check site",
                                  "url": f"https://www.bestbuy.com/site/searchpage.jsp?st={sku}",
                              })
                      return found

    async def run_cycle(self) -> int:
              self.check_num += 1
        self.state.increment_checks()
        logger.info(f"=== Check #{self.check_num} ===")
        now = time.time()
        if now - self.last_health_check > self.config.health_check_interval:
                      await self.notifier.send_heartbeat(self.uptime, self.state.state.total_checks, self.state.state.total_alerts_sent)
            self.last_health_check = now
            self.print_status()
        if self.consecutive_failures >= 3:
                      logger.warning(f"{self.consecutive_failures} consecutive failures, restarting browser...")
            if await self.init_browser():
                              logger.info("Browser restarted successfully")
                      all_items = []
        for store_id in self.config.stores:
                      logger.info(f"Checking store {store_id} ({STORE_NAMES.get(store_id, store_id)})...")
            items = await self.check_store(store_id)
            if items:
                              logger.info(f"  Found {len(items)} item(s)")
                              all_items.extend(items)
                          await asyncio.sleep(random.uniform(2, 5))
        alerts_sent = 0
        for item in all_items:
                      if self.state.is_cooldown(item["sku"], item["store_id"], self.config.cooldown_minutes):
                                        continue
                                    if await self.notifier.send_alert(item, self.check_num):
                                                      self.state.mark_alerted(item["sku"], item["store_id"])
                                                      alerts_sent += 1
                                              logger.info(f"Cycle complete. Alerts: {alerts_sent}")
        return alerts_sent

    def print_status(self):
              print(f"\n{'='*50}\nMONITOR STATUS\n{'='*50}")
        print(f"Uptime  : {self.uptime}")
        print(f"Checks  : {self.state.state.total_checks}")
        print(f"Alerts  : {self.state.state.total_alerts_sent}")
        print(f"Failures: {self.consecutive_failures}")
        print(f"{'='*50}\n")

    async def run(self) -> int:
              self.setup_logging()
        errors = self.config.validate()
        if errors:
                      for err in errors:
                                        logger.error(f"Config error: {err}")
                                    return 1
        logger.info("BEST BUY STOCK MONITOR")
        logger.info(f"SKUs: {self.config.skus} | Stores: {self.config.stores} | Interval: {self.config.interval}s")
        async with DiscordNotifier(self.config.discord_webhook) as self.notifier:
            await self.notifier.send_startup(self.config.skus, self.config.stores, self.config.interval)
            if not await self.init_browser():
                              logger.critical("Failed to initialize browser")
                              await self.notifier.send_shutdown("0s", 0, 0)
                              return 1
                          self.print_status()
            try:
                              while True:
                                                    await self.run_cycle()
                                                    await asyncio.sleep(self.config.interval)
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
except Exception as e:
                logger.exception("Fatal error in main loop")
                raise
finally:
                logger.info("Cleaning up...")
                try:
                                      await self.notifier.send_shutdown(self.uptime, self.state.state.total_checks, self.state.state.total_alerts_sent)
except Exception:
                    pass
                await self.cleanup_browser()
                self.print_status()
                logger.info("Monitor stopped")
        return 0
