import networkx as nx
from itertools import combinations
from collections import defaultdict, OrderedDict
import tournament_data as tournament


def get_incomplete_games(schedule_data):
    incomplete_games = {}
    unplayed_match_counts = defaultdict(int)
    total = 0
    for game in schedule_data:
        if not int(game["Completed"]):
            incomplete_games[int(game["Match Number"])] = game["Teams"]
            teams_playing = ",".join(sorted(str(game["Teams"]).split(","))) # sort team names so we can group same matches together
            unplayed_match_counts[teams_playing] += 1
            total += 1

    return incomplete_games, unplayed_match_counts, total

def clean_points_table_data(points_table_data):
    points_per_team = {}
    for team, data in points_table_data.items():
        points_per_team[team] = int(data["Points"])
    return points_per_team


def create_graph(capacity_per_team, unplayed_match_counts, using_points):
    G = nx.DiGraph()
    source, sink = "source", "sink"
    for match, capacity in unplayed_match_counts.items():
        team1, team2 = match.split(",")
        # Edges from source to match nodes
        G.add_edge(source, (team1, team2), capacity=((int(using_points)) + 1) * capacity)

        # Edges from match to team nodes
        G.add_edge((team1, team2), team1, capacity=((int(using_points)) + 1) * capacity)
        G.add_edge((team1, team2), team2, capacity=((int(using_points)) + 1) * capacity)

    for team, capacity in capacity_per_team.items():
        # Edges from team nodes to sink
        G.add_edge(team, sink, capacity=capacity)

    return G, source, sink


def get_possibility(
    target_team,
    pt_filepath,
    schedule_filepath,
    pt_speculation,
    schedule_speculation,
    allow_match_ties=False,
    reject_pt_ties=False,
    top_n=4,
):

    pt_keys, points_table_data, sched_keys, schedule_data = tournament.import_from_csv(pt_filepath, schedule_filepath)

    incomplete_games, unplayed_match_counts, total_unplayed_matches = get_incomplete_games(
        schedule_data
    )
    points_per_team = clean_points_table_data(points_table_data)

    # Get teams and their points, remove target team
    all_teams = points_per_team.keys()
    teams = all_teams - {target_team}
    target_team_points = points_per_team.pop(target_team)

    # Get remaining matches
    target_team_games_left = 0
    for match, number in list(unplayed_match_counts.items()):
        if target_team in match:
            target_team_games_left += number
            del unplayed_match_counts[match]

    games_to_schedule = total_unplayed_matches - target_team_games_left

    # Get max points for target team
    target_team_max_points = target_team_points + 2 * target_team_games_left

    # Set number of points/wins that each team can still get
    # If reject_pt_ties -> decrease number of points that can be earned by 1
    capacity_per_team = {}
    for team in teams:
        capacity_per_team[team] = (
            target_team_max_points - points_per_team[team] - int(reject_pt_ties)
        )

    # If allow_match_ties -> pts that can be earned (no change), Else -> games that can be won (int div by 2)
    if not allow_match_ties:
        for team in teams:
            capacity_per_team[team] //= 2

    # Make the graph
    # allow_match_ties -> using_points -> capacity of 2 along game edges instead of 1
    G, source, sink = create_graph(
        capacity_per_team, unplayed_match_counts, using_points=allow_match_ties
    )

    # Get parameters for calculating max flow, and calculate
    target_max_flow = ((int(allow_match_ties)) + 1) * games_to_schedule

    success, max_flow_val, max_flow_path = get_max_flow(G, source, sink, teams, capacity_per_team, target_max_flow, top_n)

    if success:
        generate_tournament_results_from_flow(
            max_flow_path,
            points_table_data,
            schedule_data,
            target_team,
            pt_speculation,
            schedule_speculation,
            allow_match_ties,
        )

    return (
        success,
        (max_flow_val // 2 if allow_match_ties and max_flow_val > 0 else max_flow_val) + target_team_games_left,
        total_unplayed_matches,
        max_flow_path,
    )


def get_max_flow(G, source, sink, teams, teams_data, target_max_flow, top_n=1):

    if top_n <= 1:
        # Check for negative edge weights
        if any(edge[2]["capacity"] < 0 for edge in G.edges(teams, data=True)):
            return False, float('-inf'), None

        max_flow_val, max_flow_path = nx.maximum_flow(G, source, sink)
        return max_flow_val == target_max_flow, max_flow_val, max_flow_path

    else:
        # Track best result
        max_max_flow, max_max_path = float('-inf'), None

        # Loop through every combo of teams to ignore
        for team_combo in combinations(teams, top_n - 1):

            # Set ignored edge weights
            for team in team_combo:
                G[team][sink]['capacity'] = 100

            try:
                # Check for negative edge weights
                if any(edge[2]['capacity'] < 0 for edge in G.edges(teams, data=True)):
                    continue

                max_flow_val, max_flow_path = nx.maximum_flow(G, source, sink)

                # Check if valid result
                if max_flow_val == target_max_flow:
                    return True, max_flow_val, max_flow_path

                # Track best result
                if max_flow_val > max_max_flow:
                    max_max_flow = max_flow_val
                    max_max_path = max_flow_path

            # Restore Edge Weights
            finally:
                for team in team_combo:    
                    G[team][sink]["capacity"] = teams_data[team]

        return False, max_max_flow, max_max_path


def generate_tournament_results_from_flow(
    flow_path,
    points_table_data,
    schedule_data,
    target_team,
    pt_speculation,
    schedule_speculation,
    using_points=False,
):
    flow_dict = flow_path.copy()
    adj_for_points = int(using_points)
    for game in schedule_data:
        if not int(game["Completed"]):
            team1, team2 = tuple(sorted(game["Teams"].split(",")))
            if team1 == target_team:
                update_tournament_data(team1, team2, game, points_table_data)
                continue
            elif team2 == target_team:
                update_tournament_data(team2, team1, game, points_table_data)
                continue

            relevant_flow = flow_dict[(team1, team2)]

            if relevant_flow[team1] > 0 + adj_for_points:
                update_tournament_data(team1, team2, game, points_table_data)
                relevant_flow[team1] -= (1 + adj_for_points)

            elif relevant_flow[team2] > 0 + adj_for_points:
                update_tournament_data(team2, team1, game, points_table_data)
                relevant_flow[team1] -= (1 + adj_for_points)

            elif using_points and relevant_flow[team1] == 1 and relevant_flow[team2] == 1:
                update_tournament_data(team1, team2, game, points_table_data, match_tied=True)
                relevant_flow[team1] -= 1
                relevant_flow[team2] -= 1

            else:
                print("NO WINNER FLOW ERROR:", game)
                return
    points_table_data = OrderedDict(
        sorted(
            points_table_data.items(),
            key=lambda entry: int(entry[1]["Points"]),
            reverse=True,
        )
    )
    tournament.export_to_csv(
        pt_speculation, list(points_table_data.values())[0].keys(), points_table_data
    )
    schedule_data = {row["Match Number"]: row for row in schedule_data}
    tournament.export_to_csv(
        schedule_speculation, list(schedule_data.values())[0].keys(), schedule_data
    )


def update_tournament_data(winner, loser, game, points_table_data, match_tied=False):
    if match_tied:
        game["Tied/NR"] = 1
        points_table_data[winner]["Tied/NR"] = 1 + int(
            points_table_data[winner]["Won"]
        )
        points_table_data[winner]["Points"] = 1 + int(
            points_table_data[winner]["Points"]
        )
        points_table_data[loser]["Tied/NR"] = 1 + int(
            points_table_data[loser]["Lost"]
        )
        points_table_data[winner]["Points"] = 1 + int(
            points_table_data[winner]["Points"]
        )
    else:
        game["Tied/NR"] = 0
        game["Winner"] = winner
        game["Loser"] = loser
        points_table_data[winner]["Won"] = 1 + int(
            points_table_data[winner]["Won"]
        )
        points_table_data[winner]["Points"] = 2 + int(
            points_table_data[winner]["Points"]
        )
        points_table_data[loser]["Lost"] = 1 + int(
            points_table_data[loser]["Lost"]
        )

    game["Completed"] = 1
    points_table_data[winner]["Matches"] = 1 + int(
        points_table_data[winner]["Matches"]
    )
    points_table_data[loser]["Matches"] = 1 + int(
        points_table_data[loser]["Matches"]
    )

def main():
    target_team = "Lucknow Super Giants"
    top_n = 4
    allow_match_ties = False
    reject_pt_ties = False

    # success, scheduled_count, total_matches, max_flow_path = (
    #     get_possibility(
    #         target_team,
    #         "data/ipl_2024_points_table_edit.csv",
    #         "data/ipl_2024_schedule_edit.csv",
    #         allow_match_ties=allow_match_ties,
    #         reject_pt_ties=reject_pt_ties,
    #         top_n=top_n,
    #     )
    # )
    success, scheduled_count, total_matches, max_flow_path = get_possibility(
        target_team,
        "data/ipl_2025_points_table_removed.csv",
        "data/ipl_2025_schedule_removed.csv",
        "data/ipl_2025_points_table_speculation.csv",
        "data/ipl_2025_schedule_speculation.csv",
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
        top_n=top_n,
    )

    print(f'{target_team} can end in the top {top_n}: {success}')
    print(f'Scheduled {scheduled_count} out of {total_matches} matches.')


if __name__ == '__main__':
    main()
