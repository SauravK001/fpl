fpl-optimizer/
│
├── README.md                      # project overview, setup instructions
├── requirements.txt                # dependencies (ortools, pandas, requests, etc.)
├── config.py                       # constants: budget=100.0, squad rules, API URLs, current season/GW
│
├── data/
│   ├── raw/                        # untouched pulls (bootstrap_static.json, fixtures.json, etc.)
│   ├── processed/                  # cleaned CSVs ready for modeling (players.csv, form.csv)
│   └── historical/                 # past-season dumps (from vaastav repo) for backtesting
│
├── pipeline/
│   ├── fetch_fpl_data.py           # pulls bootstrap-static + fixtures from FPL API
│   ├── fetch_underlying_stats.py   # pulls/scrapes xG, xA, ICT from external source
│   ├── build_features.py           # joins everything into one feature table per player/GW
│   └── update_all.py               # orchestrates the weekly refresh (calls the above in order)
│
├── prediction/
│   ├── team_strength_model.py      # Dixon-Coles / Bayesian hierarchical Poisson — team attack/defense ratings, per-fixture expected goals │both sides
│   ├── player_involvement_model.py # goal involvement share per player given team xG (multinomial/Poisson conditioned on team model output)
│   ├── minutes_model.py            # start probability + expected minutes classifier
│   ├── clean_sheet_model.py        # derived from team_strength_model's P(opponent scores 0)
│   ├── bonus_points_model.py       # separate BPS estimator from underlying stats (tackles, key passes, etc.)
│   ├── points_combiner.py          # combines all of the above through actual FPL scoring rules -> final xPts
│   ├── ensemble_model.py           # independent LightGBM model on same features, blended with points_combiner output
│   └── backtest.py                 # walk-forward validation across past GWs, per-component and combined error
│
├── optimizer/
│   ├── squad_selector.py           # CP-SAT model: pick 15 + XI + captain (Phase 3)
│   ├── transfer_optimizer.py       # rolling transfer decisions given current squad (Phase 4)
│   ├── chip_strategy.py            # heuristics/logic for wildcard, bench boost, etc.
│   └── constraints.py              # shared constraint definitions (budget, club limits, formation rules)
│
├── tracking/
│   ├── my_squad.json               # your current actual squad + budget state
│   ├── performance_log.csv         # weekly actual vs predicted points, rank history
│   └── evaluate.py                 # compares model predictions to real outcomes over time
│
├── notebooks/                      # exploratory analysis, model tuning, sanity checks
│   └── exploration.ipynb
│
└── main.py                         # entry point: "give me this week's recommended squad/transfers"