import os
import re
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    discord_webhook: str
    skus: List[str]
      stores: List[str]
      interval: int = 60
      cooldown_minutes: int = 30
      health_check_interval: int = 1800
      log_level: str = "INFO"
      state_file: str = "state.json"

      @classmethod
      def from_env(cls) -> "Config":
          skus_raw = os.getenv("BESTBUY_SKUS", "")
          stores_raw = os.getenv("BESTBUY_STORES", "")
          return cls(
              discord_webhook=os.getenv("DISCORD_WEBHOOK", ""),
              skus=[s.strip() for s in skus_raw.split(",") if s.strip()],
              stores=[s.strip() for s in stores_raw.split(",") if s.strip()],
              interval=int(os.getenv("CHECK_INTERVAL", "60")),
              cooldown_minutes=int(os.getenv("COOLDOWN_MINUTES", "30")),
              health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "1800")),
              log_level=os.getenv("LOG_LEVEL", "INFO"),
              state_file=os.getenv("STATE_FILE", "state.json"),
          )

      def validate(self) -> List[str]:
        errors = []
          if not self.discord_webhook or "YOUR/WEBHOOK" in self.discord_webhook:
            errors.append("DISCORD_WEBHOOK not configured")
          elif not re.match(r"^https://discord\.com/api/webhooks/\d+/", self.discord_webhook):
            errors.append("Invalid DISCORD_WEBHOOK format")
          if not self.skus:
            errors.append("BESTBUY_SKUS not configured")
          for sku in self.skus:
            if not sku.isdigit() or len(sku) < 6:
                errors.append(f"Invalid SKU format: {sku} (expected 6+ digits)")
        if not self.stores:
            errors.append("BESTBUY_STORES not configured")
          if self.interval < 30:
              errors.append(f"CHECK_INTERVAL {self.interval}s too low (min 30s)")
          if self.interval > 3600:
              errors.append(f"CHECK_INTERVAL {self.interval}s too high (max 3600s)")
        if self.cooldown_minutes < 0:
              errors.append("COOLDOWN_MINUTES cannot be negative")
          if self.cooldown_minutes > 1440:
            errors.append("COOLDOWN_MINUTES > 24hrs is excessive")
          return errors
