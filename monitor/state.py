import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("bestbuy_monitor")


@dataclass
class PersistentState:
      total_checks: int = 0
      total_alerts_sent: int = 0
      last_alert_time: Optional[str] = None
      seen_stock: Dict[str, float] = field(default_factory=dict)


class StateManager:
      def __init__(self, path: str = "state.json"):
                self.path = Path(path)
                self.state = self._load()

      def _load(self) -> PersistentState:
                if self.path.exists():
                              try:
                                                data = json.loads(self.path.read_text())
                                                return PersistentState(
                                                    total_checks=data.get("total_checks", 0),
                                                    total_alerts_sent=data.get("total_alerts_sent", 0),
                                                    last_alert_time=data.get("last_alert_time"),
                                                    seen_stock=data.get("seen_stock", {}),
                                                )
except Exception as e:
                logger.warning(f"Could not load state from {self.path}: {e}")
        return PersistentState()

    def _save(self):
              try:
                            self.path.write_text(json.dumps({
                                              "total_checks": self.state.total_checks,
                                              "total_alerts_sent": self.state.total_alerts_sent,
                                              "last_alert_time": self.state.last_alert_time,
                                              "seen_stock": self.state.seen_stock,
                            }, indent=2))
except Exception as e:
            logger.warning(f"Could not save state to {self.path}: {e}")

    def increment_checks(self):
              self.state.total_checks += 1
              self._save()

    def is_cooldown(self, sku: str, store_id: str, cooldown_minutes: int) -> bool:
              key = f"{sku}:{store_id}"
              last_seen = self.state.seen_stock.get(key)
              if last_seen is None:
                            return False
                        elapsed = (time.time() - last_seen) / 60
        return elapsed < cooldown_minutes

    def mark_alerted(self, sku: str, store_id: str):
              key = f"{sku}:{store_id}"
        self.state.seen_stock[key] = time.time()
        self.state.total_alerts_sent += 1
        self.state.last_alert_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self._save()
