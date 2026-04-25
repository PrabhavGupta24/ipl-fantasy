"""
Consistency check: v3 (CP-SAT) must agree with v0 (brute force) on small datasets.

Brute force is the ground-truth oracle: it enumerates every possible completion.
v3 should agree with the boolean answers it produces:
- can_qualify(target) ⟺ brute force found at least one qualifying scenario
- has_qualified(target) ⟺ brute force found zero non-qualifying scenarios

Run from the qualification_scenarios/ directory:
    python tests/test_consistency.py
"""

import sys
from pathlib import Path

# Make qualification_scenarios/ importable regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brute_force import enumerate_scenarios
from queries import can_qualify, has_qualified


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PT_PATH = str(DATA_DIR / "ipl_2025_points_table.csv")
SCHED_PATH = str(DATA_DIR / "ipl_2025_schedule.csv")

# (target, top_n, reject_pt_ties)
CASES = [
    ("Royal Challengers Bengaluru", 4, False),
    ("Chennai Super Kings",         4, False),
    ("Gujarat Titans",              2, False),
    ("Chennai Super Kings",         4, True),
    ("Mumbai Indians",              4, False),
]


def run_case(target, top_n, reject_pt_ties):
    bf = enumerate_scenarios(
        target, PT_PATH, SCHED_PATH,
        top_n=top_n, reject_pt_ties=reject_pt_ties, verbose=False,
    )
    if bf is None:
        return False, "brute force failed"

    expected_can_qualify = bf["qualifying_count"] > 0
    expected_has_qualified = bf["qualifying_count"] == bf["total_scenarios"]

    actual_can_qualify = can_qualify(
        target, PT_PATH, SCHED_PATH,
        top_n=top_n, reject_pt_ties=reject_pt_ties,
    )
    actual_has_qualified = has_qualified(
        target, PT_PATH, SCHED_PATH,
        top_n=top_n, reject_pt_ties=reject_pt_ties,
    )

    issues = []
    if actual_can_qualify != expected_can_qualify:
        issues.append(f"can_qualify: v3={actual_can_qualify}, expected={expected_can_qualify}")
    if actual_has_qualified != expected_has_qualified:
        issues.append(f"has_qualified: v3={actual_has_qualified}, expected={expected_has_qualified}")

    summary = f"qualifying={bf['qualifying_count']}/{bf['total_scenarios']}"
    if issues:
        return False, summary + "  |  " + "; ".join(issues)
    return True, summary


def main():
    print(f"Running {len(CASES)} consistency tests on {Path(PT_PATH).name}...\n")

    passed = 0
    for target, top_n, reject_pt_ties in CASES:
        mode = "pessimistic" if reject_pt_ties else "optimistic"
        label = f"{target}  |  top {top_n}  |  {mode}"
        print(f"  {label}")
        ok, msg = run_case(target, top_n, reject_pt_ties)
        marker = "PASS" if ok else "FAIL"
        print(f"    {marker} ({msg})\n")
        if ok:
            passed += 1

    print(f"{passed}/{len(CASES)} tests passed.")
    sys.exit(0 if passed == len(CASES) else 1)


if __name__ == "__main__":
    main()
