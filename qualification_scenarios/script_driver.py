"""
Python-script entry point for the v3 solver.

Use this when you want constraints. Edit the configuration block below,
then run from the qualification_scenarios/ directory:

    python script_driver.py

For simple queries with no constraints, driver.py (the CLI version) is
faster to invoke.
"""

import remove_matches
from queries import (
    can_qualify, has_qualified,
    must_win_analysis, print_must_win_report,
    minimum_points_needed, print_minimum_points_report,
    elimination_certificate, print_elimination_certificate,
)
from constraint_classes import MatchConstraint, TeamConstraint, MatchOutcome


# ============================================================
# Edit your scenario here
# ============================================================

TARGET_TEAM = "Royal Challengers Bengaluru"
YEAR = 2025
TOP_N = 4

# Number of completed matches to rewind (0 = use current state)
REMOVED_GAMES = 0

# Tiebreak / tie behavior
REJECT_PT_TIES = False     # True = "regardless of NRR", False = "assuming favorable NRR"
ALLOW_MATCH_TIES = False   # True = let matches end in a tie (rare in IPL)

# Optional match constraints — uncomment and edit to use
MATCH_CONSTRAINTS = [
    # MatchConstraint(match_number=62, outcome=MatchOutcome.WIN, winner="Chennai Super Kings"),
    # MatchConstraint(match_number=70, outcome=MatchOutcome.TIE),
]

# Optional team constraints — uncomment and edit to use
# Bounds apply to ADDITIONAL wins/points in the remaining matches, not the final total.
TEAM_CONSTRAINTS = [
    # TeamConstraint("Mumbai Indians", lower_bound=2),               # ≥ 2 more wins
    # TeamConstraint("Punjab Kings", upper_bound=1, unit="wins"),    # ≤ 1 more win
    # TeamConstraint("Delhi Capitals", upper_bound=4, unit="points"),# ≤ 4 more points
]

# "eliminated", "qualified", "must_win", "min_points", or "why_eliminated"
QUERY = "eliminated"

# ============================================================
# End of configuration
# ============================================================


def main():
    pt_filepath = f"data/ipl_{YEAR}_points_table.csv"
    schedule_filepath = f"data/ipl_{YEAR}_schedule.csv"

    if REMOVED_GAMES > 0:
        pt_rewound = pt_filepath.replace(".csv", f"_{REMOVED_GAMES}rem.csv")
        sched_rewound = schedule_filepath.replace(".csv", f"_{REMOVED_GAMES}rem.csv")
        remove_matches.remove_matches_driver(
            REMOVED_GAMES, pt_filepath, schedule_filepath, pt_rewound, sched_rewound
        )
        pt_filepath, schedule_filepath = pt_rewound, sched_rewound

    pt_outpath = pt_filepath.replace(".csv", "_v3_spec.csv")
    schedule_outpath = schedule_filepath.replace(".csv", "_v3_spec.csv")

    common_kwargs = dict(
        target_team=TARGET_TEAM,
        pt_filepath=pt_filepath,
        schedule_filepath=schedule_filepath,
        top_n=TOP_N,
        match_constraints=MATCH_CONSTRAINTS,
        team_constraints=TEAM_CONSTRAINTS,
        allow_match_ties=ALLOW_MATCH_TIES,
        reject_pt_ties=REJECT_PT_TIES,
        pt_outpath=pt_outpath,
        schedule_outpath=schedule_outpath,
    )

    if QUERY == "eliminated":
        can_still_qualify = can_qualify(**common_kwargs)
        verdict = "is NOT eliminated from" if can_still_qualify else "IS eliminated from"
        print(f"{TARGET_TEAM} {verdict} the top {TOP_N}.")
    elif QUERY == "qualified":
        clinched = has_qualified(**common_kwargs)
        verdict = "HAS qualified for" if clinched else "has NOT yet qualified for"
        print(f"{TARGET_TEAM} {verdict} the top {TOP_N}.")
    elif QUERY == "must_win":
        # must_win_analysis doesn't write speculation CSVs; drop those kwargs
        kwargs = {k: v for k, v in common_kwargs.items()
                  if k not in ("pt_outpath", "schedule_outpath")}
        report = must_win_analysis(**kwargs)
        print_must_win_report(report, TARGET_TEAM, TOP_N)
    elif QUERY == "min_points":
        kwargs = {k: v for k, v in common_kwargs.items()
                  if k not in ("pt_outpath", "schedule_outpath")}
        min_points = minimum_points_needed(**kwargs)
        print_minimum_points_report(min_points, TARGET_TEAM, TOP_N, schedule_filepath)
    elif QUERY == "why_eliminated":
        kwargs = {k: v for k, v in common_kwargs.items()
                  if k not in ("pt_outpath", "schedule_outpath")}
        cert = elimination_certificate(**kwargs)
        print_elimination_certificate(cert, TARGET_TEAM, TOP_N)
    else:
        raise ValueError(
            f"QUERY must be 'eliminated', 'qualified', 'must_win', 'min_points', or "
            f"'why_eliminated', got {QUERY!r}"
        )


if __name__ == "__main__":
    main()
