"""
CP-SAT model construction for the IPL qualification problem.

Exposes:
- build_model(...): construct the CP-SAT model, decision variables, and metadata
- add_in_top_n_constraint / add_outside_top_n_constraint: rank queries
- write_speculation_csv: dump a solved assignment as updated CSVs
"""

from typing import List
from collections import OrderedDict

from ortools.sat.python import cp_model

import tournament_data as tournament
from constraint_classes import MatchConstraint, TeamConstraint, MatchOutcome


def build_model(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    match_constraints: List[MatchConstraint] = None,
    team_constraints: List[TeamConstraint] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
):
    match_constraints = match_constraints or []
    team_constraints = team_constraints or []

    _, points_table_data, _, schedule_data = tournament.import_from_csv(
        pt_filepath, schedule_filepath
    )

    curr_points = {team: int(data["Points"]) for team, data in points_table_data.items()}
    all_teams = list(curr_points.keys())

    if target_team not in all_teams:
        raise ValueError(f"Unknown target team: {target_team}")

    # Unplayed matches: list of (match_num, team_a, team_b)
    unplayed_matches = []
    for game in schedule_data:
        if not int(game["Completed"]):
            match_num = int(game["Match Number"])
            teams = [t.strip() for t in game["Teams"].split(",")]
            unplayed_matches.append((match_num, teams[0], teams[1]))

    model = cp_model.CpModel()

    # One set of booleans per match: win_a, win_b, tied (exactly one true)
    win_a, win_b, tied = {}, {}, {}
    for match_num, _, _ in unplayed_matches:
        win_a[match_num] = model.NewBoolVar(f"win_a_{match_num}")
        win_b[match_num] = model.NewBoolVar(f"win_b_{match_num}")
        tied[match_num] = model.NewBoolVar(f"tied_{match_num}")
        model.Add(win_a[match_num] + win_b[match_num] + tied[match_num] == 1)
        if not allow_match_ties:
            model.Add(tied[match_num] == 0)

    # Lookup maps: team -> list of win/tie vars belonging to that team
    team_wins = {team: [] for team in all_teams}
    team_ties = {team: [] for team in all_teams}
    for match_num, a, b in unplayed_matches:
        team_wins[a].append(win_a[match_num])
        team_wins[b].append(win_b[match_num])
        team_ties[a].append(tied[match_num])
        team_ties[b].append(tied[match_num])

    def points_expr(t):
        # curr + 2 * wins + 1 * ties
        return curr_points[t] + 2 * sum(team_wins[t]) + sum(team_ties[t])

    def wins_expr(t):
        return sum(team_wins[t])

    # Match constraints
    match_lookup = {m: (a, b) for m, a, b in unplayed_matches}
    for mc in match_constraints:
        if mc.match_number not in match_lookup:
            print(f"Warning: match {mc.match_number} is not unplayed; skipping.")
            continue
        a, b = match_lookup[mc.match_number]
        if mc.outcome == MatchOutcome.WIN:
            if mc.winner == a:
                model.Add(win_a[mc.match_number] == 1)
            elif mc.winner == b:
                model.Add(win_b[mc.match_number] == 1)
            else:
                raise ValueError(
                    f"winner {mc.winner!r} not in match {mc.match_number} ({a} vs {b})"
                )
        else:  # TIE
            if not allow_match_ties:
                raise ValueError(
                    f"Cannot force match {mc.match_number} to tie when allow_match_ties=False"
                )
            model.Add(tied[mc.match_number] == 1)

    # Team constraints
    for tc in team_constraints:
        if tc.team_name not in all_teams:
            raise ValueError(f"Unknown team: {tc.team_name}")
        if tc.unit == "wins":
            bound_expr = wins_expr(tc.team_name)
        elif tc.unit == "points":
            bound_expr = 2 * wins_expr(tc.team_name) + sum(team_ties[tc.team_name])
        else:
            raise ValueError(f"Unknown unit {tc.unit!r}; expected 'wins' or 'points'")
        if tc.lower_bound is not None:
            model.Add(bound_expr >= tc.lower_bound)
        if tc.upper_bound is not None:
            model.Add(bound_expr <= tc.upper_bound)

    # Rank indicators: for each non-target team, is their final points strictly above target's?
    target_pts = points_expr(target_team)
    above_target = {}
    for t in all_teams:
        if t == target_team:
            continue
        b_above = model.NewBoolVar(f"above_{t}")
        if reject_pt_ties:
            # Pessimistic: ties go against target — tied teams are considered "above"
            model.Add(points_expr(t) >= target_pts).OnlyEnforceIf(b_above)
            model.Add(points_expr(t) < target_pts).OnlyEnforceIf(b_above.Not())
        else:
            # Optimistic: target wins ties — strictly more needed to be above
            model.Add(points_expr(t) > target_pts).OnlyEnforceIf(b_above)
            model.Add(points_expr(t) <= target_pts).OnlyEnforceIf(b_above.Not())
        above_target[t] = b_above

    vars_dict = {
        "win_a": win_a,
        "win_b": win_b,
        "tied": tied,
        "above_target": above_target,
    }
    metadata = {
        "target_team": target_team,
        "all_teams": all_teams,
        "unplayed_matches": unplayed_matches,
        "points_table_data": points_table_data,
        "schedule_data": schedule_data,
    }
    return model, vars_dict, metadata


def read_unplayed_matches(schedule_filepath):
    """Return list of (match_num, team_a, team_b) for matches not yet completed."""
    import csv
    unplayed = []
    with open(schedule_filepath) as f:
        for row in csv.DictReader(f):
            if not int(row["Completed"]):
                teams = [t.strip() for t in row["Teams"].split(",")]
                unplayed.append((int(row["Match Number"]), teams[0], teams[1]))
    return unplayed


def add_in_top_n_constraint(model, vars_dict, top_n: int):
    """Target is in the top N ⟺ at most top_n - 1 other teams are above."""
    model.Add(sum(vars_dict["above_target"].values()) <= top_n - 1)


def add_outside_top_n_constraint(model, vars_dict, top_n: int):
    """Target is outside the top N ⟺ at least top_n other teams are above."""
    model.Add(sum(vars_dict["above_target"].values()) >= top_n)


def write_speculation_csv(solver, vars_dict, metadata, pt_outpath, schedule_outpath):
    """Decode a solved model's match outcomes into updated points-table and schedule CSVs."""
    # Deep-enough copies: points table values are dicts, schedule rows are dicts
    points_table_data = {team: dict(row) for team, row in metadata["points_table_data"].items()}
    schedule_data = [dict(row) for row in metadata["schedule_data"]]
    unplayed = {m: (a, b) for m, a, b in metadata["unplayed_matches"]}

    for row in schedule_data:
        m = int(row["Match Number"])
        if m not in unplayed:
            continue
        a, b = unplayed[m]
        if solver.Value(vars_dict["win_a"][m]):
            _apply_win(points_table_data, row, winner=a, loser=b)
        elif solver.Value(vars_dict["win_b"][m]):
            _apply_win(points_table_data, row, winner=b, loser=a)
        else:
            _apply_tie(points_table_data, row, a, b)

    points_table_data = OrderedDict(
        sorted(points_table_data.items(),
               key=lambda kv: int(kv[1]["Points"]),
               reverse=True)
    )

    pt_fieldnames = list(next(iter(points_table_data.values())).keys())
    tournament.export_to_csv(pt_outpath, pt_fieldnames, points_table_data)

    schedule_dict = OrderedDict((row["Match Number"], row) for row in schedule_data)
    sched_fieldnames = list(next(iter(schedule_dict.values())).keys())
    tournament.export_to_csv(schedule_outpath, sched_fieldnames, schedule_dict)


def _apply_win(points_table_data, schedule_row, winner, loser):
    schedule_row["Completed"] = 1
    schedule_row["Tied/NR"] = 0
    schedule_row["Winner"] = winner
    schedule_row["Loser"] = loser
    points_table_data[winner]["Won"] = 1 + int(points_table_data[winner]["Won"])
    points_table_data[winner]["Matches"] = 1 + int(points_table_data[winner]["Matches"])
    points_table_data[winner]["Points"] = 2 + int(points_table_data[winner]["Points"])
    points_table_data[loser]["Lost"] = 1 + int(points_table_data[loser]["Lost"])
    points_table_data[loser]["Matches"] = 1 + int(points_table_data[loser]["Matches"])


def _apply_tie(points_table_data, schedule_row, a, b):
    schedule_row["Completed"] = 1
    schedule_row["Tied/NR"] = 1
    for t in (a, b):
        points_table_data[t]["Tied/NR"] = 1 + int(points_table_data[t]["Tied/NR"])
        points_table_data[t]["Matches"] = 1 + int(points_table_data[t]["Matches"])
        points_table_data[t]["Points"] = 1 + int(points_table_data[t]["Points"])
