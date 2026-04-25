# ipl-fantasy

Tools for answering qualification-scenario questions about the Indian Premier League:
*"Can CSK still make the top 4?"*, *"Has GT clinched a top-2 spot?"*, *"What does RCB
need to win to qualify?"*.

The repo contains two complementary solvers and an archive of earlier approaches.

## Repo layout

```
ipl-fantasy/
├── qualification_scenarios/      # the active project
│   ├── solver.py                 # CP-SAT model construction (v3)
│   ├── queries.py                # can_qualify, has_qualified, must_win_analysis,
│   │                             # minimum_points_needed, elimination_certificate
│   ├── driver.py                 # CLI entry point
│   ├── script_driver.py          # Python entry point (for constraints)
│   ├── brute_force.py            # v0 enumerator (late-season ground truth)
│   ├── constraint_classes.py     # MatchConstraint, TeamConstraint, MatchOutcome
│   ├── tournament_data.py        # CSV I/O + Cricbuzz scraping
│   ├── remove_matches.py         # rewind utility
│   ├── tests/test_consistency.py # asserts v3 ≡ v0 on small datasets
│   ├── data/                     # historical points tables and schedules
│   └── legacy/                   # archived v1/v2 max-flow implementations
├── fantasy_analysis/             # separate side project (player analytics)
├── requirements.txt
└── .venv/                        # gitignored
```

## Setup

One-time:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Each new terminal: `source .venv/bin/activate` from the repo root.

## Usage

All commands below assume you've activated the venv and `cd`'d into
`qualification_scenarios/`.

### CLI driver — quick queries with no constraints

```bash
python driver.py \
  --target "Royal Challengers Bengaluru" \
  --year 2025 \
  --top-n 4 \
  --mode eliminated
```

Available `--mode` values:
- `eliminated` — is target eliminated from top N? (yes/no)
- `qualified` — has target clinched a top N spot? (yes/no)
- `must-win` — for each unplayed match, report if its outcome is forced for target's qualification
- `min-points` — fewest additional points target needs to have a chance at top N
- `why-eliminated` — when target is eliminated, show the most-favorable-for-target
  scenario (target's max points, teams beating them, gap to qualifying spot)

Optional flags:
- `--removed-games N` — rewind the tournament by N completed matches
- `--allow-match-ties` — permit tied matches in the model (default: off)
- `--reject-pt-ties` — pessimistic NRR mode ("regardless of NRR"); default is
  optimistic ("assuming favorable NRR")

### Script driver — queries with constraints

For "what-if" scenarios involving forced match outcomes or per-team bounds, edit
the configuration block at the top of `script_driver.py` and run:

```bash
python script_driver.py
```

Available `QUERY` values: `"eliminated"`, `"qualified"`, `"must_win"`,
`"min_points"`, `"why_eliminated"` — same questions as the CLI's `--mode` flag.

Example constraints (uncomment and modify in the file):

```python
MATCH_CONSTRAINTS = [
    MatchConstraint(match_number=62, outcome=MatchOutcome.WIN, winner="Chennai Super Kings"),
]
TEAM_CONSTRAINTS = [
    TeamConstraint("Mumbai Indians", lower_bound=2),               # ≥ 2 more wins
    TeamConstraint("Delhi Capitals", upper_bound=4, unit="points"),# ≤ 4 more points
]
```

### Brute force — full enumeration (late-season only)

For end-of-season questions where you want every qualifying scenario counted:

```bash
python brute_force.py
```

Edit `main()` to choose the target team and dataset. Capped at 22 unplayed matches
(2²² ≈ 4M scenarios). Output includes a per-match must-win analysis and a sample
qualifying scenario.

### Updating the data

`tournament_data.py` scrapes Cricbuzz for the current points table and schedule:

```bash
python tournament_data.py
```

Writes to `data/ipl_<year>_points_table.csv` and `data/ipl_<year>_schedule.csv`.

### Tests

A consistency check that asserts v3 (CP-SAT) and v0 (brute force) agree on
yes/no questions, `minimum_points_needed`, and `elimination_certificate`:

```bash
python tests/test_consistency.py
```

Runs ~5 cases; takes a few seconds. Brute force is the ground-truth oracle.

## How the solvers work, briefly

**v3 (CP-SAT)** models each unplayed match as three booleans (team A wins, team B
wins, tied) with an exactly-one constraint, builds final-points expressions per
team, and adds reified rank-indicator booleans. Qualification questions become a
single sum constraint (`at most N-1 teams above target`). Solved by Google's
OR-Tools CP-SAT engine in milliseconds.

**v0 (brute force)** enumerates all 2ᵐ outcomes of m unplayed matches, classifies
each, and aggregates statistics. Tractable for m ≤ 22.

**NRR** is not modeled directly. Two flags bracket the NRR-dependent answer:
- `--reject-pt-ties` off (default): assume target wins point-table ties → answers
  "can target qualify *assuming favorable NRR*?"
- `--reject-pt-ties` on: assume target loses ties → answers "can target qualify
  *regardless of NRR*?"

## Legacy (`qualification_scenarios/legacy/`)

The original max-flow / network-simplex implementations from before v3. Modeled
after the classical baseball-elimination problem (Schwartz 1966; Sedgewick &
Wayne). Polynomial worst-case for the simplified problem but couldn't express
NRR-aware constraints, multi-target queries, or "what does target need" analysis
— which is why v3 exists.

To run a legacy solver from the project root:

```bash
cd qualification_scenarios
PYTHONPATH=. python legacy/calculate_elimination_v2.py
```

## Roadmap

Done:
- **v3.0**: CP-SAT model + `can_qualify` / `has_qualified` + CLI + speculation CSVs
- **v3.1**: `must_win_analysis` — per-match required-outcome report from O(m) solves
- **v3.2**: `minimum_points_needed` (objective minimization) and
  `elimination_certificate` (lexicographic 2-solve: min teams above target, then max
  target points)

Open:
- **v3.3**: multi-target queries ("CSK qualifies AND PBKS doesn't")
- CLI constraint support (constraints from a JSON file or stdin)
- Web UI
- Probability / Monte Carlo overlay
- Dynamic NRR modeling (margin-of-victory variables)
