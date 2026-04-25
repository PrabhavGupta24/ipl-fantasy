"""
High-level queries over the CP-SAT model.

v3.0 exposes two questions, mirroring v2:
- can_qualify: is there any completion where target finishes in the top N?
- has_qualified: is target guaranteed to finish in the top N?

Both return a boolean. When output paths are provided:
- can_qualify writes a qualifying scenario (if one exists).
- has_qualified writes a counter-example scenario (if target is not yet clinched).
"""

from typing import List, Optional

from ortools.sat.python import cp_model

from constraint_classes import MatchConstraint, TeamConstraint, MatchOutcome
from solver import (
    build_model,
    add_in_top_n_constraint,
    add_outside_top_n_constraint,
    read_unplayed_matches,
    write_speculation_csv,
)


def can_qualify(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    top_n: int = 4,
    match_constraints: Optional[List[MatchConstraint]] = None,
    team_constraints: Optional[List[TeamConstraint]] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
    pt_outpath: Optional[str] = None,
    schedule_outpath: Optional[str] = None,
) -> bool:
    """Return True iff target can still finish in the top N."""
    model, vars_dict, metadata = build_model(
        target_team, pt_filepath, schedule_filepath,
        match_constraints=match_constraints,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
    )
    add_in_top_n_constraint(model, vars_dict, top_n)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    feasible = status in (cp_model.FEASIBLE, cp_model.OPTIMAL)

    if feasible and pt_outpath and schedule_outpath:
        write_speculation_csv(solver, vars_dict, metadata, pt_outpath, schedule_outpath)

    return feasible


def has_qualified(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    top_n: int = 4,
    match_constraints: Optional[List[MatchConstraint]] = None,
    team_constraints: Optional[List[TeamConstraint]] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
    pt_outpath: Optional[str] = None,
    schedule_outpath: Optional[str] = None,
) -> bool:
    """Return True iff target is guaranteed to finish in the top N.

    Implemented as the inverse: if a scenario exists where target ends *outside*
    the top N, then target is not yet guaranteed.
    """
    model, vars_dict, metadata = build_model(
        target_team, pt_filepath, schedule_filepath,
        match_constraints=match_constraints,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
    )
    add_outside_top_n_constraint(model, vars_dict, top_n)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    counter_example_exists = status in (cp_model.FEASIBLE, cp_model.OPTIMAL)

    if counter_example_exists and pt_outpath and schedule_outpath:
        write_speculation_csv(solver, vars_dict, metadata, pt_outpath, schedule_outpath)

    return not counter_example_exists


def must_win_analysis(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    top_n: int = 4,
    match_constraints: Optional[List[MatchConstraint]] = None,
    team_constraints: Optional[List[TeamConstraint]] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
) -> dict:
    """Per-match: is each unplayed match's outcome forced for target's qualification?

    Returns a dict:
        {
          "is_eliminated": bool,
          "matches": [
            {
              "match_number": int, "team_a": str, "team_b": str,
              "team_a_can_win": bool, "team_b_can_win": bool, "can_tie": bool,
              "verdict": "team_a_must_win" | "team_b_must_win" | "must_tie" | "flexible",
            }, ...
          ]
        }

    Cost: ~2 ILP solves per unplayed match (3 if allow_match_ties).
    """
    match_constraints = list(match_constraints or [])
    team_constraints = list(team_constraints or [])

    common_kwargs = dict(
        target_team=target_team,
        pt_filepath=pt_filepath,
        schedule_filepath=schedule_filepath,
        top_n=top_n,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
    )

    # Baseline: is qualification feasible at all under the user's constraints?
    if not can_qualify(match_constraints=match_constraints, **common_kwargs):
        return {"is_eliminated": True, "matches": []}

    matches_report = []
    for match_num, team_a, team_b in read_unplayed_matches(schedule_filepath):
        a_can_win = can_qualify(
            match_constraints=match_constraints + [
                MatchConstraint(match_num, MatchOutcome.WIN, winner=team_a)
            ],
            **common_kwargs,
        )
        b_can_win = can_qualify(
            match_constraints=match_constraints + [
                MatchConstraint(match_num, MatchOutcome.WIN, winner=team_b)
            ],
            **common_kwargs,
        )
        if allow_match_ties:
            can_tie = can_qualify(
                match_constraints=match_constraints + [
                    MatchConstraint(match_num, MatchOutcome.TIE)
                ],
                **common_kwargs,
            )
        else:
            can_tie = False

        feasible = sum((a_can_win, b_can_win, can_tie))
        if feasible == 1:
            verdict = ("team_a_must_win" if a_can_win
                       else "team_b_must_win" if b_can_win
                       else "must_tie")
        elif feasible > 1:
            verdict = "flexible"
        else:
            # Should be unreachable when baseline is feasible
            verdict = "infeasible"

        matches_report.append({
            "match_number": match_num,
            "team_a": team_a,
            "team_b": team_b,
            "team_a_can_win": a_can_win,
            "team_b_can_win": b_can_win,
            "can_tie": can_tie,
            "verdict": verdict,
        })

    return {"is_eliminated": False, "matches": matches_report}


def print_must_win_report(report: dict, target_team: str, top_n: int) -> None:
    """Format a must_win_analysis result as human-readable stdout."""
    if report["is_eliminated"]:
        print(f"{target_team} is ELIMINATED — no must-win analysis applicable.")
        return

    print(f"\nMust-win analysis for {target_team} (top {top_n}):")
    for m in report["matches"]:
        v = m["verdict"]
        if v == "team_a_must_win":
            line = f"{m['team_a']} MUST beat {m['team_b']}"
        elif v == "team_b_must_win":
            line = f"{m['team_b']} MUST beat {m['team_a']}"
        elif v == "must_tie":
            line = f"{m['team_a']} vs {m['team_b']} MUST tie"
        else:
            line = f"{m['team_a']} vs {m['team_b']} — flexible"
        print(f"  Match {m['match_number']:>3}: {line}")


def minimum_points_needed(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    top_n: int = 4,
    match_constraints: Optional[List[MatchConstraint]] = None,
    team_constraints: Optional[List[TeamConstraint]] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
) -> Optional[int]:
    """Minimum additional points target needs to (possibly) qualify for top N.

    Returns the minimum, or None if target is eliminated regardless.

    Points (not wins) is the right unit because qualifying depends on points: with
    ties allowed, the solver could swap wins for ties, making "min wins" misleading.
    With ties off (default), the answer is exactly 2 × the equivalent min-wins value.
    """
    model, vars_dict, _ = build_model(
        target_team, pt_filepath, schedule_filepath,
        match_constraints=match_constraints,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
    )
    add_in_top_n_constraint(model, vars_dict, top_n)
    # Incremental points: 2 per win + 1 per tie (current points are constant, ignored)
    incremental_points = (
        2 * sum(vars_dict["team_wins"][target_team])
        + sum(vars_dict["team_ties"][target_team])
    )
    model.Minimize(incremental_points)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status == cp_model.OPTIMAL:
        return int(solver.ObjectiveValue())
    return None


def print_minimum_points_report(min_points: Optional[int], target_team: str, top_n: int,
                                 schedule_filepath: str) -> None:
    """Format a minimum_points_needed result as human-readable stdout."""
    if min_points is None:
        print(f"{target_team} is ELIMINATED from top {top_n} — cannot qualify regardless of outcomes.")
        return

    remaining = sum(1 for _, a, b in read_unplayed_matches(schedule_filepath)
                    if target_team in (a, b))
    max_possible = 2 * remaining
    print(f"{target_team} needs at least {min_points} more point(s) "
          f"({remaining} match(es) remaining, max {max_possible}) "
          f"to have a chance at top {top_n}.")


def elimination_certificate(
    target_team: str,
    pt_filepath: str,
    schedule_filepath: str,
    top_n: int = 4,
    match_constraints: Optional[List[MatchConstraint]] = None,
    team_constraints: Optional[List[TeamConstraint]] = None,
    allow_match_ties: bool = False,
    reject_pt_ties: bool = False,
) -> Optional[dict]:
    """When target is eliminated, return the most favorable scenario for target.

    Returns None if target is not eliminated.
    Otherwise returns:
        {
          "min_count_above": int,                    # fewest teams above target across all completions
          "target_final_points": int,                # target's points in that scenario
          "teams_above": [(team_name, points), ...], # sorted desc by points
        }

    Computed via two ILP solves (lexicographic):
      1. Minimize count of teams above target.
      2. Among scenarios with that minimum count, maximize target's points.

    The returned scenario is the strongest case for target — and yet, by elimination,
    still has >= top_n teams beating them.
    """
    common_kwargs = dict(
        target_team=target_team,
        pt_filepath=pt_filepath,
        schedule_filepath=schedule_filepath,
        top_n=top_n,
        match_constraints=match_constraints,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
    )

    if can_qualify(**common_kwargs):
        return None  # not eliminated

    # build_model doesn't take top_n (rank constraint is added separately, not used here)
    build_kwargs = {k: v for k, v in common_kwargs.items() if k != "top_n"}

    # Solve 1: minimize teams above target
    model, vars_dict, _ = build_model(**build_kwargs)
    model.Minimize(sum(vars_dict["above_target"].values()))
    solver = cp_model.CpSolver()
    if solver.Solve(model) != cp_model.OPTIMAL:
        return None
    min_count = int(solver.ObjectiveValue())

    # Solve 2: lock the count, maximize target's incremental points
    model, vars_dict, metadata = build_model(**build_kwargs)
    model.Add(sum(vars_dict["above_target"].values()) == min_count)
    target_incremental_points = (
        2 * sum(vars_dict["team_wins"][target_team])
        + sum(vars_dict["team_ties"][target_team])
    )
    model.Maximize(target_incremental_points)
    solver = cp_model.CpSolver()
    if solver.Solve(model) != cp_model.OPTIMAL:
        return None

    # Decode the witness into final points per team
    curr_points = {team: int(data["Points"])
                   for team, data in metadata["points_table_data"].items()}

    def final_points(team):
        wins = sum(solver.Value(v) for v in vars_dict["team_wins"][team])
        ties = sum(solver.Value(v) for v in vars_dict["team_ties"][team])
        return curr_points[team] + 2 * wins + ties

    teams_above = []
    for t in metadata["all_teams"]:
        if t == target_team:
            continue
        if solver.Value(vars_dict["above_target"][t]):
            teams_above.append((t, final_points(t)))
    teams_above.sort(key=lambda tp: -tp[1])  # descending by points

    return {
        "min_count_above": min_count,
        "target_final_points": final_points(target_team),
        "teams_above": teams_above,
    }


def print_elimination_certificate(cert: Optional[dict], target_team: str, top_n: int) -> None:
    """Format an elimination_certificate result as human-readable stdout."""
    if cert is None:
        print(f"{target_team} is NOT eliminated from top {top_n}; no certificate to produce.")
        return

    print(f"\n{target_team} is ELIMINATED from top {top_n}.\n")
    print(f"Most favorable scenario for {target_team}:")
    print(f"  {target_team} finishes with {cert['target_final_points']} points, "
          f"but {cert['min_count_above']} team(s) still finish above:")
    for team, pts in cert["teams_above"]:
        print(f"    - {team}: {pts} pts")

    # Gap to the top_n-th finisher (0-indexed: position top_n - 1 in the sorted-above list)
    if len(cert["teams_above"]) >= top_n:
        top_n_th_pts = cert["teams_above"][top_n - 1][1]
        gap = top_n_th_pts - cert["target_final_points"]
        print(f"\n  Gap from {target_team} to {top_n}th place: {gap} point(s).")
