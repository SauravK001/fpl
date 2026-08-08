"""
pipeline/fetch_underlying_stats.py

Pulls historical player-gameweek data (including underlying stats like
ICT index, and xG/xA where present) from vaastav's community-maintained
Fantasy-Premier-League GitHub repo, for a configurable set of past seasons.

This is your training data source for the regression/component models --
NOT for current-season live data (use fetch_fpl_data.py for that).

Repo: https://github.com/vaastav/Fantasy-Premier-League

Run this file directly:
    python fetch_underlying_stats.py
"""

import os
from pathlib import Path

import pandas as pd
import requests

RAW_BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

# Decision from our earlier discussion: 3 past seasons is the working window.
# Adjust this list as needed -- format must match the repo's folder naming.
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]

# Resolve relative to PROJECT ROOT (one level up from pipeline/), not the
# terminal's working directory -- same reasoning as fetch_fpl_data.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORICAL_DATA_DIR = PROJECT_ROOT / "data" / "historical"


def ensure_dirs_exist(seasons: list[str]):
    """Create data/historical/<season>/ folders if they don't exist yet."""
    for season in seasons:
        os.makedirs(os.path.join(HISTORICAL_DATA_DIR, season), exist_ok=True)


def fetch_csv(url: str) -> pd.DataFrame:
    """
    Fetch a CSV file from a raw GitHub URL into a pandas DataFrame.
    Raises an informative error if the file doesn't exist (e.g. season
    folder not present, or filename differs for that season).
    """
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    from io import StringIO
    return pd.read_csv(StringIO(response.text))


def fetch_season(season: str) -> dict:
    """
    Fetches the three core files for one season:
      - merged_gw.csv   : gameweek-by-gameweek stats for every player
      - players_raw.csv : season-level player metadata (price, position, team, etc.)
      - fixtures.csv     : all fixtures for the season with results

    Returns a dict of DataFrames, and saves each to data/historical/<season>/.
    """
    season_dir = os.path.join(HISTORICAL_DATA_DIR, season)
    files = {
        "merged_gw": f"{RAW_BASE_URL}/{season}/gws/merged_gw.csv",
        "players_raw": f"{RAW_BASE_URL}/{season}/players_raw.csv",
        "fixtures": f"{RAW_BASE_URL}/{season}/fixtures.csv",
        # Each season has its OWN team ID -> name mapping. Team IDs are NOT
        # stable across seasons (promotion/relegation reshuffles them), so
        # this must be fetched per-season rather than reused from the
        # current season's bootstrap-static.
        "teams": f"{RAW_BASE_URL}/{season}/teams.csv",
    }

    season_data = {}
    for name, url in files.items():
        print(f"  Fetching {season}/{name}...")
        try:
            df = fetch_csv(url)
        except requests.exceptions.HTTPError as e:
            print(f"    WARNING: could not fetch {name} for {season} ({e}). Skipping this file.")
            continue

        out_path = os.path.join(season_dir, f"{name}.csv")
        df.to_csv(out_path, index=False)
        print(f"    Saved {len(df)} rows -> {out_path}")
        season_data[name] = df

    return season_data


def check_for_underlying_stats(merged_gw: pd.DataFrame, season: str):
    """
    Sanity check: not every season/row in this repo has xG/xA populated --
    coverage depends on Understat merge availability for that season.
    Warn if the columns are missing or entirely empty, so it's obvious
    early rather than silently breaking a downstream model.
    """
    xg_cols = [c for c in merged_gw.columns if c.lower() in ("xg", "xa", "expected_goals", "expected_assists")]
    if not xg_cols:
        print(f"    NOTE: no xG/xA-style columns found in {season} merged_gw.csv. "
              f"You may need a separate Understat pull for this season.")
    else:
        non_null_counts = {c: merged_gw[c].notna().sum() for c in xg_cols}
        print(f"    xG/xA-related columns found: {non_null_counts}")


def main():
    ensure_dirs_exist(SEASONS)

    all_seasons_data = {}
    for season in SEASONS:
        print(f"\n=== Season {season} ===")
        season_data = fetch_season(season)
        all_seasons_data[season] = season_data

        if "merged_gw" in season_data:
            check_for_underlying_stats(season_data["merged_gw"], season)

    print("\n--- Summary ---")
    for season, files in all_seasons_data.items():
        row_count = len(files.get("merged_gw", []))
        print(f"{season}: {row_count} player-gameweek rows fetched")

    print("\nDone.")


if __name__ == "__main__":
    main()