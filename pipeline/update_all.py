"""
pipeline/update_all.py

Orchestrates the data pipeline in the correct order.

Two modes:
  Weekly (default):  refresh current-season live data, then rebuild features.
                      This is what you'd run every week before setting your squad.
  Full (--full):     ALSO re-fetch historical seasons from vaastav's repo.
                      Historical seasons are finished/static data -- there's
                      no reason to re-download them weekly. Only run this
                      once, or when you want to add a newly-completed season
                      to your SEASONS list.

Usage:
    python update_all.py            # weekly: current data + rebuild features
    python update_all.py --full     # also re-fetch historical seasons
"""

import argparse
import sys
import time

import build_features
import fetch_fpl_data
import fetch_underlying_stats


def run_step(step_name: str, func):
    """Runs a pipeline step with basic timing and error handling, so one
    failed step gives a clear message instead of a silent/confusing crash."""
    print(f"\n{'=' * 50}")
    print(f"STEP: {step_name}")
    print("=" * 50)
    start = time.time()
    try:
        func()
    except Exception as e:
        print(f"\nFAILED at step '{step_name}': {e}")
        print("Stopping pipeline -- fix this before later steps run on bad/missing data.")
        sys.exit(1)
    elapsed = time.time() - start
    print(f"--- {step_name} done in {elapsed:.1f}s ---")


def main():
    parser = argparse.ArgumentParser(description="Refresh FPL data and rebuild features.")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Also re-fetch historical seasons (rarely needed -- static data).",
    )
    args = parser.parse_args()

    if args.full:
        run_step("Fetch historical seasons (vaastav repo)", fetch_underlying_stats.main)

    run_step("Fetch current-season live data (FPL API)", fetch_fpl_data.main)
    run_step("Build feature tables", build_features.main)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()