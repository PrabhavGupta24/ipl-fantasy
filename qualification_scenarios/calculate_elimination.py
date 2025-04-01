import networkx as nx
from itertools import combinations
import csv
import time
from collections import defaultdict, OrderedDict
import math

def get_schedule_data(filepath):
    matches = defaultdict(int)
    total_matches = 0
    with open(filepath, mode='r', newline='') as file:
        reader = csv.DictReader(file)
        for match in reader:
            if not int(match['Completed']):
                matches[match['Teams']] += 1
                total_matches += 1

    return matches, total_matches

def get_points_table_data(filepath):
    teams = OrderedDict()
    with open(filepath, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for team in reader:
            teams[team['Name']] = int(team['Points'])

    return teams

def create_graph(teams, matches, using_points):
    G = nx.DiGraph()
    source, sink = "source", "sink"
    for match, capacity in matches.items():
        team1, team2 = match.split(",")
        # Edges from source to match nodes
        G.add_edge(source, (team1, team2), capacity=((int(using_points)) + 1) * capacity)

        # Edges from match to team nodes
        G.add_edge((team1, team2), team1, capacity=((int(using_points)) + 1) * capacity)
        G.add_edge((team1, team2), team2, capacity=((int(using_points)) + 1) * capacity)

    for team, capacity in teams.items():
        # Edges from team nodes to sink
        G.add_edge(team, sink, capacity=capacity)

    return G, source, sink

def get_possibility(target_team, pt_filepath, schedule_filepath, allow_ties, top_n=1):

    # Get teams and their points, remove target team
    teams_data = get_points_table_data(pt_filepath)
    all_teams = teams_data.keys()
    target_team_points = teams_data[target_team]

    # Get remaining matches
    matches, total_matches = get_schedule_data(schedule_filepath)
    target_team_games_left = sum(matches[match] for match in matches if target_team in match)

    # Get max points for target team
    target_team_max = (
        target_team_points + 2 * target_team_games_left 
        if allow_ties 
        else math.floor(target_team_points / 2) + target_team_games_left
    )

    # Set number of wins that each team can still get
    for team in teams_data:
        teams_data[team] = (
            target_team_max - teams_data[team]
            if allow_ties
            else target_team_max - math.ceil(teams_data[team] / 2)
        )
    teams_data[target_team] = 100

    # Make the graph
    G, source, sink = create_graph(teams_data, matches, allow_ties)

    # Get parameters for calculating max flow, and calculate
    target_max_flow = ((int(allow_ties)) + 1) * total_matches

    success, max_flow_val, max_flow_path = get_max_flow(G, source, sink, all_teams, teams_data, target_max_flow, top_n)

    return (
        success,
        (
            math.floor(max_flow_val / 2)
            if allow_ties
            else max_flow_val
        ),
        total_matches,
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

                # Check if valid flow
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


def main():
    target_team = "Punjab Kings"
    top_n = 4
    allow_ties = False
    success, scheduled_count, total_matches, max_flow_path = (
        get_possibility(
            target_team,
            "data/ipl_2024_points_table_edit.csv",
            "data/ipl_2024_schedule_edit.csv",
            allow_ties=allow_ties,
            top_n=top_n,
        )
    )
    # success, scheduled_count, total_matches, max_flow_path = (
    #     get_possibility(
    #         target_team,
    #         "data/ipl_2025_points_table.csv",
    #         "data/ipl_2025_schedule.csv",
    #         allow_ties=allow_ties,
    #         top_n=top_n,
    #     )
    # )

    print(f'{target_team} can end in the top {top_n}: {success}')
    print(f'Scheduled {scheduled_count} out of {total_matches} matches.')

    # for edge_flow in max_flow_path:
    #     print(edge_flow, max_flow_path[edge_flow])
    # print(max_flow_path)

if __name__ == '__main__':
    main()
