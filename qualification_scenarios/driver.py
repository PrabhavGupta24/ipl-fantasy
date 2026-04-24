"""
v3 CLI entry point.

For v3.0 the CLI only exposes the common case: one team, one year, one query mode.
Constraints (MatchConstraint, TeamConstraint) are available via the Python API
in queries.py — import and call from a script when needed.

Example:
    python driver.py --target "Royal Challengers Bengaluru" --year 2025 \
        --top-n 4 --mode eliminated --removed-games 20
"""

import argparse

import remove_matches
from queries import can_qualify, has_qualified


def parse_args():
    parser = argparse.ArgumentParser(
        description="CP-SAT qualification scenario solver for IPL."
    )
    parser.add_argument("--target", required=True,
                        help="Target team name (exact, as it appears in the points table).")
    parser.add_argument("--year", type=int, default=2025,
                        help="IPL year (requires data/ipl_<year>_* CSVs).")
    parser.add_argument("--removed-games", type=int, default=0,
                        help="Rewind the tournament by N completed matches before solving.")
    parser.add_argument("--top-n", type=int, default=4,
                        help="Qualification cutoff (top 4 for IPL playoffs).")
    parser.add_argument("--mode", choices=["eliminated", "qualified"], required=True,
                        help="'eliminated' asks whether target IS eliminated from top N; "
                             "'qualified' asks whether target HAS clinched top N.")
    parser.add_argument("--allow-match-ties", action="store_true",
                        help="Permit tied matches (default: no ties).")
    parser.add_argument("--reject-pt-ties", action="store_true",
                        help="Treat point-table ties as unfavorable to target "
                             "(pessimistic: 'regardless of NRR' question).")
    return parser.parse_args()


def main():
    args = parse_args()

    pt_filepath = f"data/ipl_{args.year}_points_table.csv"
    schedule_filepath = f"data/ipl_{args.year}_schedule.csv"

    if args.removed_games > 0:
        pt_filepath_rewound = pt_filepath.replace(".csv", f"_{args.removed_games}rem.csv")
        schedule_filepath_rewound = schedule_filepath.replace(".csv", f"_{args.removed_games}rem.csv")
        remove_matches.remove_matches_driver(
            args.removed_games,
            pt_filepath,
            schedule_filepath,
            pt_filepath_rewound,
            schedule_filepath_rewound,
        )
        pt_filepath = pt_filepath_rewound
        schedule_filepath = schedule_filepath_rewound

    pt_outpath = pt_filepath.replace(".csv", "_v3_spec.csv")
    schedule_outpath = schedule_filepath.replace(".csv", "_v3_spec.csv")

    if args.mode == "eliminated":
        can_still_qualify = can_qualify(
            target_team=args.target,
            pt_filepath=pt_filepath,
            schedule_filepath=schedule_filepath,
            top_n=args.top_n,
            allow_match_ties=args.allow_match_ties,
            reject_pt_ties=args.reject_pt_ties,
            pt_outpath=pt_outpath,
            schedule_outpath=schedule_outpath,
        )
        verdict = "is NOT eliminated from" if can_still_qualify else "IS eliminated from"
        print(f"{args.target} {verdict} the top {args.top_n}.")

    elif args.mode == "qualified":
        clinched = has_qualified(
            target_team=args.target,
            pt_filepath=pt_filepath,
            schedule_filepath=schedule_filepath,
            top_n=args.top_n,
            allow_match_ties=args.allow_match_ties,
            reject_pt_ties=args.reject_pt_ties,
            pt_outpath=pt_outpath,
            schedule_outpath=schedule_outpath,
        )
        verdict = "HAS qualified for" if clinched else "has NOT yet qualified for"
        print(f"{args.target} {verdict} the top {args.top_n}.")


if __name__ == "__main__":
    main()
