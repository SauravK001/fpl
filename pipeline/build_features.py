"""
pipeline/build_features.py

Transforms RAW data already sitting on disk (from fetch_fpl_data.py and
fetch_underlying_stats.py) into clean, model-ready feature tables saved
to data/processed/.

IMPORTANT: this file never calls the network itself. It only reads what's
already been fetched. If data/raw/ or data/historical/ don't have data yet,
run fetch_fpl_data.py and fetch_underlying_stats.py first (or just run
update_all.py, which handles the ordering).
"""

import json
import os
from pathlib import Path

import pandas as pd

# Resolve relative to PROJECT ROOT (one level up from pipeline/), not the
# terminal's working directory -- same reasoning as fetch_fpl_data.py.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
HISTORICAL_DATA_DIR = PROJECT_ROOT / "data" / "historical"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

# Must match the SEASONS list used in fetch_underlying_stats.py
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]


def ensure_processed_dir_exists():
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)


def load_bootstrap_static() -> dict:
    """Load the raw bootstrap-static JSON fetched by fetch_fpl_data.py."""
    path = os.path.join(RAW_DATA_DIR, "bootstrap_static.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run fetch_fpl_data.py first."
        )
    with open(path, "r") as f:
        return json.load(f)


def build_team_id_map(bootstrap: dict) -> dict:
    """
    Builds an {team_id: team_name} lookup from bootstrap-static's 'teams' list.
    ONLY valid for CURRENT-season data (e.g. current fixtures.json), since
    this reflects this season's ID assignments.
    """
    teams = bootstrap.get("teams", [])
    return {team["id"]: team["name"] for team in teams}


def build_season_team_id_map(season: str) -> dict:
    """
    Builds an {team_id: team_name} lookup from a SPECIFIC historical season's
    own teams.csv (data/historical/<season>/teams.csv).

    This matters because team IDs are NOT stable across seasons -- promotion
    and relegation reshuffle which numeric ID maps to which club each year.
    Using the current season's ID map against an older season's fixtures.csv
    silently produces WRONG team names (no crash, no NaN -- just wrong data).
    Always use each season's own teams.csv for that season's fixtures.
    """
    teams_path = os.path.join(HISTORICAL_DATA_DIR, season, "teams.csv")
    if not os.path.exists(teams_path):
        raise FileNotFoundError(
            f"{teams_path} not found. Re-run fetch_underlying_stats.py "
            f"(it now fetches teams.csv per season -- if you ran it before "
            f"this fix, you need to run it again)."
        )
    teams = pd.read_csv(teams_path)
    # vaastav's teams.csv uses 'id' and 'name' columns, consistent with the
    # live API's shape -- verified against 2024-25/teams.csv structure.
    return dict(zip(teams["id"], teams["name"]))


def build_match_data() -> pd.DataFrame:
    """
    Builds the six-column Dixon-Coles training table:
        date, season, home_team, away_team, home_goals, away_goals

    Pulls from each season's fixtures.csv in data/historical/<season>/,
    keeping only matches that have actually been played (i.e. have a
    final score), since unplayed fixtures have no goals to fit against.
    """
    all_matches = []

    for season in SEASONS:
        fixtures_path = os.path.join(HISTORICAL_DATA_DIR, season, "fixtures.csv")
        if not os.path.exists(fixtures_path):
            print(f"WARNING: {fixtures_path} not found, skipping {season}. "
                  f"Run fetch_underlying_stats.py first.")
            continue

        # Use THIS season's own team ID map -- not the current season's.
        team_id_map = build_season_team_id_map(season)

        fixtures = pd.read_csv(fixtures_path)

        # NOTE: verify these column names against what you actually printed
        # from fixtures.csv earlier -- adjust here if they differ.
        # Expected FPL-style columns: kickoff_time, team_h, team_a,
        # team_h_score, team_a_score, finished
        played = fixtures[fixtures["finished"] == True].copy()

        played["season"] = season
        played["date"] = pd.to_datetime(played["kickoff_time"]).dt.date
        played["home_team"] = played["team_h"].map(team_id_map)
        played["away_team"] = played["team_a"].map(team_id_map)
        played["home_goals"] = played["team_h_score"]
        played["away_goals"] = played["team_a_score"]

        season_matches = played[
            ["date", "season", "home_team", "away_team", "home_goals", "away_goals"]
        ]

        missing_team_names = season_matches["home_team"].isna().sum() + season_matches["away_team"].isna().sum()
        if missing_team_names > 0:
            print(f"WARNING: {missing_team_names} unmapped team IDs in {season} "
                  f"-- team_id_map may be incomplete for older seasons (team IDs "
                  f"can shift between seasons in some sources, worth checking).")

        all_matches.append(season_matches)
        print(f"{season}: {len(season_matches)} played matches added")

    match_data = pd.concat(all_matches, ignore_index=True)
    match_data = match_data.sort_values("date").reset_index(drop=True)
    return match_data


def build_current_season_player_table() -> pd.DataFrame:
    """
    Builds a basic current-season player reference table from bootstrap-static:
    id, name, team, position, price. This is a minimal starting point --
    NOT yet the full feature table player_involvement_model.py or
    minutes_model.py will eventually need (those require historical
    per-gameweek features that haven't been designed yet).
    """
    bootstrap = load_bootstrap_static()
    team_id_map = build_team_id_map(bootstrap)  # correct here: current-season data, current-season map

    element_type_map = {et["id"]: et["singular_name_short"] for et in bootstrap.get("element_types", [])}

    players = pd.DataFrame(bootstrap["elements"])
    players["team_name"] = players["team"].map(team_id_map)
    players["position"] = players["element_type"].map(element_type_map)
    players["price"] = players["now_cost"] / 10  # now_cost is stored *10

    cols = ["id", "first_name", "second_name", "team_name", "position", "price", "total_points"]
    return players[cols]


def main():
    ensure_processed_dir_exists()

    print("Building match-level data (Dixon-Coles input)...")
    match_data = build_match_data()
    match_data.to_csv(os.path.join(PROCESSED_DATA_DIR, "matches.csv"), index=False)
    print(f"Saved {len(match_data)} rows -> data/processed/matches.csv\n")

    print("Building current-season player reference table...")
    players = build_current_season_player_table()
    players.to_csv(os.path.join(PROCESSED_DATA_DIR, "players_current.csv"), index=False)
    print(f"Saved {len(players)} rows -> data/processed/players_current.csv")

    # TODO: player-level historical feature table for player_involvement_model.py
    # TODO: minutes/starts feature table for minutes_model.py
    # TODO: clean sheet feature table for clean_sheet_model.py
    # These need their schemas designed first -- see mentoring notes, don't
    # guess at these shapes ahead of that.


if __name__ == "__main__":
    main()