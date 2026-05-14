#!/usr/bin/env python3
"""
run_agent.py — CLI entry point for the Finance Credit Follow-Up Email Agent.

Usage:
    python run_agent.py                          # process all overdue invoices
    python run_agent.py --invoice INV-2024-001   # process specific invoice(s)
    python run_agent.py --dry-run                # force dry-run mode
    python run_agent.py --data custom.csv        # use a different data file
"""

import argparse
import logging
import sys
from pathlib import Path

# Make src importable when running from project root
sys.path.insert(0, str(Path(__file__).parent))

from src.agent import FinanceEmailAgent
from src.config import Config

# ─────────────────────────────────────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_run.log", mode="a", encoding="utf-8"),
    ],
)


def main():
    parser = argparse.ArgumentParser(
        description="Finance Credit Follow-Up Email Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agent.py
  python run_agent.py --dry-run
  python run_agent.py --invoice INV-2024-001 INV-2024-003
  python run_agent.py --data data/invoices.csv --dry-run
        """,
    )
    parser.add_argument(
        "--invoice",
        nargs="+",
        metavar="INV_NO",
        help="Process only these invoice numbers",
    )
    parser.add_argument(
        "--data",
        metavar="FILE",
        help="Path to CSV/Excel data file (overrides DATA_FILE in .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=None,
        help="Force dry-run mode (no real emails sent)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Force dry-run if flag passed on CLI
    if args.dry_run:
        import os
        os.environ["DRY_RUN"] = "true"

    print("\n" + "=" * 55)
    print("  Finance Credit Follow-Up Email Agent")
    print(f"  LLM: {Config.LLM_PROVIDER.upper()} / {Config.LLM_MODEL}")
    print(f"  Mode: {'🧪 DRY RUN' if Config.DRY_RUN else '🚀 LIVE'}")
    print("=" * 55 + "\n")

    try:
        agent = FinanceEmailAgent()
        result = agent.run(
            data_file=args.data,
            invoice_filter=args.invoice,
        )
        print(result.summary())
        sys.exit(0 if result.errors == 0 else 1)
    except Exception as e:
        logging.error(f"Agent failed: {e}", exc_info=True)
        print(f"\n❌ Agent failed: {e}")
        print("Check that your .env file is configured correctly.")
        sys.exit(1)


if __name__ == "__main__":
    main()
