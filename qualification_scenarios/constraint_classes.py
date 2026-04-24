"""
Constraint vocabulary shared by v3 solver and queries.

Semantics differ from legacy/constraint_classes.py:
- MatchConstraint now uses a MatchOutcome enum instead of a bool flag.
- TeamConstraint has an explicit `unit` field ("wins" or "points").
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional


class MatchOutcome(Enum):
    WIN = "win"
    TIE = "tie"


@dataclass
class MatchConstraint:
    """Force an unplayed match to a specific outcome.

    If outcome == WIN, `winner` must be set to the winning team name.
    If outcome == TIE, `winner` is ignored.
    """
    match_number: int
    outcome: MatchOutcome
    winner: Optional[str] = None

    def __post_init__(self):
        if self.outcome == MatchOutcome.WIN and self.winner is None:
            raise ValueError("winner is required when outcome == MatchOutcome.WIN")


@dataclass
class TeamConstraint:
    """Bound how many more wins (or points) a team earns in remaining matches.

    `lower_bound` / `upper_bound` are inclusive. Either or both may be set.
    `unit` decides whether the bounds apply to wins or to points (default wins).
    """
    team_name: str
    lower_bound: Optional[int] = None
    upper_bound: Optional[int] = None
    unit: Literal["wins", "points"] = "wins"
