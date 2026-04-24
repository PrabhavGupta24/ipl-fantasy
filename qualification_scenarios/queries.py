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

from constraint_classes import MatchConstraint, TeamConstraint
from solver import (
    build_model,
    add_in_top_n_constraint,
    add_outside_top_n_constraint,
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
