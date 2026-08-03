"""
pipeline/fetch_fpl_data.py

Fetches core FPL data from the official public API and saves it locally
as raw JSON, so the rest of the pipeline doesn't need to re-hit the API
every time you want to reprocess data.

Run this file directly to refresh your local data:
    python fetch_fpl_data.py
"""

import json
import os
from datetime import datetime

import requests

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"

RAW_DATA_DIR = os.path.join("data", "raw")


def ensure_raw_dir_exists():
    """Create data/raw/ if it doesn't exist yet."""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)


def fetch_json(url: str, timeout: int = 10) -> dict | list:
    """
    Fetch JSON from a URL, raising an informative error if it fails.
    Returns the parsed JSON (dict or list depending on endpoint).
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()  # raises an exception on 4xx/5xx instead of failing silently
    return response.json()


def save_json(data, filename: str):
    """Save a Python object as pretty-printed JSON in data/raw/."""
    path = os.path.join(RAW_DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved {filename} ({os.path.getsize(path) / 1024:.1f} KB) -> {path}")


def fetch_bootstrap_static() -> dict:
    """
    Fetches the main bootstrap-static payload: players (elements),
    teams, gameweeks (events), chips, element_stats, element_types, etc.
    """
    print("Fetching bootstrap-static...")
    data = fetch_json(BOOTSTRAP_URL)
    save_json(data, "bootstrap_static.json")
    return data


def fetch_fixtures() -> list:
    """
    Fetches the full fixture list for the season: match dates, teams,
    difficulty ratings (FDR), and results once played.
    """
    print("Fetching fixtures...")
    data = fetch_json(FIXTURES_URL)
    save_json(data, "fixtures.json")
    return data


def summarize(bootstrap: dict, fixtures: list):
    """Print a quick sanity-check summary so you know the pull worked."""
    players = bootstrap.get("elements", [])
    teams = bootstrap.get("teams", [])
    events = bootstrap.get("events", [])

    print("\n--- Summary ---")
    print(f"Players fetched:   {len(players)}")
    print(f"Teams fetched:     {len(teams)}")
    print(f"Gameweeks fetched: {len(events)}")
    print(f"Fixtures fetched:  {len(fixtures)}")

    current_gw = next((e for e in events if e.get("is_current")), None)
    next_gw = next((e for e in events if e.get("is_next")), None)
    print(f"Current gameweek: {current_gw['name'] if current_gw else 'None (season not started)'}")
    print(f"Next gameweek:    {next_gw['name'] if next_gw else 'Unknown'}")

    if players:
        sample = players[67]
        print(f"\nSample player: {sample.get('first_name')} {sample.get('second_name')}")
        print(f"  now_cost (price):   {sample.get('now_cost')/10}")
        print(f"  element_type (pos): {sample.get('element_type')}")
        print(f"  total_points:       {sample.get('total_points')}")


def main():
    ensure_raw_dir_exists()
    bootstrap = fetch_bootstrap_static()
    fixtures = fetch_fixtures()
    summarize(bootstrap, fixtures)
    print(f"\nDone. Data pulled at {datetime.now().isoformat(timespec='seconds')}")


if __name__ == "__main__":
    main()