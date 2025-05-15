from dataclasses import dataclass, field
import calculate_elimination_v2
import calculate_qualification
import remove_matches
from constraint_classes import MatchConstraint, TeamConstraint
from typing import List
import argparse
import json


@dataclass
class Arguments:
    team_name: str
    ipl_year: int = 2025
    removed_games: int = 0
    top_n: int = 4
    qualified: bool = False
    eliminated: bool = False
    allow_match_ties: bool = False
    reject_pt_ties: bool = False
    match_constraints: List[MatchConstraint] = field(default_factory=list)
    team_constraints: List[TeamConstraint] = field(default_factory=list)


def parse_arguments() -> Arguments:
    parser = argparse.ArgumentParser(description="Process command-line arguments.")

    parser.add_argument(
        "-n", "--team_name", type=str, required=True, help="Name of the team."
    )
    parser.add_argument(
        "--ipl_year", type=int, default=2025, help="Year of IPL to speculate on."
    )
    parser.add_argument(
        "--removed_games", type=int, default=0, help="Number of games to remove, if any."
    )
    parser.add_argument(
        "--top_n", type=int, default=4, help="Top N ranking to consider."
    )
    parser.add_argument(
        "-q", "--qualified", action="store_true", help="Determine if guaranteed qualification."
    )
    parser.add_argument(
        "-e", "--eliminated", action="store_true", help="Determine if guaranteed elimination."
    )
    parser.add_argument(
        "--allow_match_ties", action="store_true", help="Allow match ties."
    )
    parser.add_argument(
        "--reject_pt_ties", action="store_true", help="Reject point ties."
    )

    parser.add_argument(
        "--match_constraints",
        type=str,
        default="[]",
        help="JSON string of match constraints.",
    )
    parser.add_argument(
        "--team_constraints",
        type=str,
        default="[]",
        help="JSON string of team constraints.",
    )

    args = parser.parse_args()

    # Convert JSON strings into lists of dataclass instances
    match_constraints_data = json.loads(args.match_constraints)
    team_constraints_data = json.loads(args.team_constraints)

    print(match_constraints_data)

    match_constraints = [MatchConstraint(**mc) for mc in match_constraints_data]
    team_constraints = [TeamConstraint(**tc) for tc in team_constraints_data]

    return Arguments(
        team_name=args.team_name,
        ipl_year=args.ipl_year,
        removed_games=args.removed_games,
        top_n=args.top_n,
        qualified=args.qualified,
        eliminated=args.eliminated,
        allow_match_ties=args.allow_match_ties,
        reject_pt_ties=args.reject_pt_ties,
        match_constraints=match_constraints,
        team_constraints=team_constraints,
    )

def main():
    args = parse_arguments()
    print(args)

    supported_ipl_years = [2024, 2025]
    if args.ipl_year not in supported_ipl_years:
        print("IPL Year not Supported.")
        return

    source_pt = "data/ipl_" + str(args.ipl_year) + "_points_table.csv"
    source_sched = "data/ipl_" + str(args.ipl_year) + "_schedule.csv"

    if args.removed_games > 0:
        dest_pt = f"_{args.removed_games}rem.".join(source_pt.rsplit(".", 1))
        dest_sched = f"_{args.removed_games}rem.".join(source_sched.rsplit(".", 1))
        remove_matches.remove_matches_driver(args.removed_games, source_pt, source_sched, dest_pt, dest_sched)
        source_pt, source_sched = dest_pt, dest_sched

    if args.eliminated:
        success, total_matches, max_flow_path = (
            calculate_elimination_v2.get_possibility(
                args.team_name,
                source_pt,
                source_sched,
                "_e_spec.".join(source_pt.rsplit(".", 1)),
                "_e_spec.".join(source_sched.rsplit(".", 1)),
                args.match_constraints,
                args.team_constraints,
                args.allow_match_ties,
                args.reject_pt_ties,
                args.top_n,
            )
        )
        print(f'{args.team_name} can end in the top {args.top_n}: {success}')

    elif args.qualified:
        success, total_matches, max_flow_path = calculate_qualification.get_possibility(
            args.team_name,
            source_pt,
            source_sched,
            "_q_spec.".join(source_pt.rsplit(".", 1)),
            "_q_spec.".join(source_sched.rsplit(".", 1)),
            args.match_constraints,
            args.team_constraints,
            args.allow_match_ties,
            args.reject_pt_ties,
            args.top_n,
        )
        print(f'{args.team_name} can end in the top {args.top_n}: {success}')

    else:
        print("Must select qualified or eliminated.")

if __name__ == "__main__":
    main()
