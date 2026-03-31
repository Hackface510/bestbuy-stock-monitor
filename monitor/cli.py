import argparse
import asyncio
import sys

from .config import Config
from .monitor import BestBuyMonitor
from .notifier import DiscordNotifier
from .state import StateManager


def main():
    parser = argparse.ArgumentParser(
                                             description="Best Buy Stock Monitor",
                                             formatter_class=argparse.RawDescriptionHelpFormatter,
                                             epilog="""
                                     Examples:
                                       python -m monitor               # Run continuously
                                       python -m monitor --once        # Single check and exit
                                       python -m monitor --status      # Show saved state
                                             """,
                                         )
    parser.add_argument(
                                "--once", action="store_true", help="Run one check and exit"
                            )
    parser.add_argument(
                                "--status", action="store_true", help="Show current saved state"
                            )
    args = parser.parse_args()

    config = Config.from_env()

    if args.status:
        state = StateManager(config.state_file)
        print(f"Total checks : {state.state.total_checks}")
        print(f"Total alerts : {state.state.total_alerts_sent}")
        print(f"Last alert   : {state.state.last_alert_time or 'Never'}")
        print(f"Cooldowns    : {len(state.state.seen_stock)} active")
        return

    monitor = BestBuyMonitor(config)

    if args.once:
        exit_code = asyncio.run(_run_once(monitor, config))
    else:
        exit_code = asyncio.run(monitor.run())

    sys.exit(exit_code or 0)


async def _run_once(monitor: BestBuyMonitor, config: Config) -> int:
    monitor.setup_logging()
    errors = config.validate()
    if errors:
        for err in errors:
            print(f"Config error: {err}", file=sys.stderr)
        return 1

    async with DiscordNotifier(config.discord_webhook) as notifier:
        monitor.notifier = notifier
        if not await monitor.init_browser():
            print("Failed to start browser", file=sys.stderr)
            return 1
        alerts_sent = await monitor.run_cycle()
        await monitor.cleanup_browser()
        print(f"\nSingle check complete. Alerts sent: {alerts_sent}")
    return 0


if __name__ == "__main__":
    main()
