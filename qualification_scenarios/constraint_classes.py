from dataclasses import dataclass
from enum import Enum


@dataclass
class MatchConstraint:
    match_number: int
    winner: str
    loser: str
    match_tied: bool = False


@dataclass
class TeamConstraint:
    team_name: str
    lower_bound: int = None
    upper_bound: int = None


# @dataclass
# class TeamWinsConstraint:

#     class Comparator(Enum):
#         EXACT = "EXACT"
#         AT_LEAST = "AT_LEAST"
#         AT_MOST = "AT_MOST"

#     team_name: str
#     num_wins: int
#     comparator: Comparator
