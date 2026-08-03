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
│   ├── baseline_model.py           # rolling form + fixture difficulty predictor (Phase 2 step 5)
│   ├── minutes_model.py            # start probability / rotation risk estimator
│   ├── points_model.py             # main ML regression/GBM model (Phase 2 step 7)
│   └── backtest.py                 # runs model on past GWs, measures prediction error
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