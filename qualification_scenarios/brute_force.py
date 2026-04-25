"""
Brute force qualification scenario enumerator for IPL.

Enumerates all 2^m outcomes of the remaining matches, computes final standings
for each, and reports qualification statistics.

NRR is not modeled. Two modes bracket the NRR-dependent answer:
- reject_pt_ties=False (default): assume target wins all point-table ties.
  Answers "Can target qualify assuming a favorable NRR?"
- reject_pt_ties=True: assume target loses all point-table ties.
  Answers "Can target qualify regardless of NRR?"

Practical limit: ~22 remaining matches (2^22 ≈ 4M scenarios).
"""

from itertools import product
from collections import defaultdict
import tournament_data as tournament


def enumerate_scenarios(
    target_team,
    pt_filepath,
    schedule_filepath,
    top_n=4,
    reject_pt_ties=False,
    verbose=True,
):
    _, points_table_data, _, schedule_data = tournament.import_from_csv(
        pt_filepath, schedule_filepath
    )

    if target_team not in points_table_data:
        if verbose:
            print(f"ERROR: {target_team} not in points table.")
        return None

    curr_points = {team: int(data["Points"]) for team, data in points_table_data.items()}
    all_teams = list(curr_points.keys())

    unplayed = []
    for game in schedule_data:
        if not int(game["Completed"]):
            match_num = int(game["Match Number"])
            t1, t2 = sorted(game["Teams"].split(","))
            unplayed.append((match_num, t1, t2))

    m = len(unplayed)
    total_scenarios = 2 ** m

    if m > 22:
        if verbose:
            print(f"ERROR: {m} matches remaining → {total_scenarios:,} scenarios. Too many.")
        return None

    if verbose:
        print(f"Enumerating {total_scenarios:,} scenarios over {m} matches...")

    qualifying_count = 0
    per_match_t1_wins = defaultdict(int)
    sample_qualifying = None

    for outcomes in product((0, 1), repeat=m):
        points = dict(curr_points)
        for (_, t1, t2), result in zip(unplayed, outcomes):
            winner = t1 if result else t2
            points[winner] += 2

        target_pts = points[target_team]
        if reject_pt_ties:
            # Pessimistic: tied teams count as above target
            above = sum(1 for t in all_teams
                        if t != target_team and points[t] >= target_pts)
        else:
            # Optimistic: target wins ties
            above = sum(1 for t in all_teams
                        if t != target_team and points[t] > target_pts)

        if above <= top_n - 1:
            qualifying_count += 1
            if sample_qualifying is None:
                sample_qualifying = outcomes
            for (match_num, _, _), result in zip(unplayed, outcomes):
                if result:
                    per_match_t1_wins[match_num] += 1

    result = {
        "target_team": target_team,
        "top_n": top_n,
        "reject_pt_ties": reject_pt_ties,
        "total_scenarios": total_scenarios,
        "qualifying_count": qualifying_count,
        "unplayed_matches": unplayed,
        "per_match_t1_wins": dict(per_match_t1_wins),
        "sample_qualifying": sample_qualifying,
    }

    if verbose:
        _print_report(result)

    return result


def _print_report(result):
    target_team = result["target_team"]
    top_n = result["top_n"]
    total_scenarios = result["total_scenarios"]
    qualifying_count = result["qualifying_count"]
    unplayed = result["unplayed_matches"]
    per_match_t1_wins = result["per_match_t1_wins"]
    sample_qualifying = result["sample_qualifying"]

    tie_mode = "regardless of NRR" if result["reject_pt_ties"] else "assuming favorable NRR"
    print(f"\n{'='*60}")
    print(f"Target: {target_team}  |  Top {top_n}  |  {tie_mode}")
    print(f"{'='*60}")
    print(f"Total scenarios:      {total_scenarios:>12,}")
    print(f"Qualifying scenarios: {qualifying_count:>12,} "
          f"({100 * qualifying_count / total_scenarios:.2f}%)")

    if qualifying_count == 0:
        print(f"\n→ {target_team} is ELIMINATED.")
        return
    if qualifying_count == total_scenarios:
        print(f"\n→ {target_team} has CLINCHED qualification.")
        return

    print(f"\n--- Per-match requirements (across qualifying scenarios) ---")
    for match_num, t1, t2 in unplayed:
        t1_wins = per_match_t1_wins[match_num]
        t2_wins = qualifying_count - t1_wins
        if t1_wins == qualifying_count:
            print(f"  Match {match_num:>3}: {t1} MUST beat {t2}")
        elif t2_wins == qualifying_count:
            print(f"  Match {match_num:>3}: {t2} MUST beat {t1}")
        else:
            pct = 100 * t1_wins / qualifying_count
            print(f"  Match {match_num:>3}: flexible  "
                  f"({t1} wins in {pct:.0f}%, {t2} wins in {100-pct:.0f}%)")

    print(f"\n--- Sample qualifying scenario ---")
    for (match_num, t1, t2), outcome in zip(unplayed, sample_qualifying):
        winner, loser = (t1, t2) if outcome else (t2, t1)
        print(f"  Match {match_num:>3}: {winner} beats {loser}")


def main():
    enumerate_scenarios(
        target_team="Royal Challengers Bengaluru",
        pt_filepath="data/ipl_2025_points_table_removed.csv",
        schedule_filepath="data/ipl_2025_schedule_removed.csv",
        top_n=4,
        reject_pt_ties=False,
    )


if __name__ == "__main__":
    main()
