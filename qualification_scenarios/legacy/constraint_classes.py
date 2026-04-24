from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class MatchConstraint:
    match_number: int
    winner: str
    loser: str
    match_tied: bool = False


@dataclass
class TeamConstraint:
    team_name: str
    lower_bound: Optional[int] = None
    upper_bound: Optional[int] = None


# @dataclass
# class QualificationConstraint:
#     team_name: str
#     qualifies: bool


# @dataclass
# class TeamWinsConstraint:

#     class Comparator(Enum):
#         EXACT = "EXACT"
#         AT_LEAST = "AT_LEAST"
#         AT_MOST = "AT_MOST"

#     team_name: str
#     num_wins: int
#     comparator: Comparator
