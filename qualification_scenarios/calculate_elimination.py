import networkx as nx
from itertools import combinations
import csv
import time
from collections import defaultdict
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
    teams = {}
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

def get_possibility(target_team, pt_filepath, schedule_filepath, allow_ties):

    # Get teams and their points, remove target team
    teams_data = get_points_table_data(pt_filepath)
    all_teams = teams_data.keys()
    target_team_points = teams_data.pop(target_team)

    # Get remaining matches
    matches, total_matches = get_schedule_data(schedule_filepath)

    # Remove target team's matches
    matches_to_remove = [match for match in matches if target_team in match]
    target_team_games_left = sum(matches[match] for match in matches_to_remove)
    games_to_schedule = total_matches - target_team_games_left
    for match in matches_to_remove:
        del matches[match]

    # Get max points for target team and set team edge capacities
    target_team_max = (
        target_team_points + 2 * target_team_games_left 
        if allow_ties 
        else math.floor(target_team_points / 2) + target_team_games_left
    ) 
    for team in teams_data:
        teams_data[team] = (
            target_team_max - teams_data[team]
            if allow_ties
            else target_team_max - math.ceil(teams_data[team] / 2)
        )
        if teams_data[team] < 0:
            print(f"Simple Check Failed, {target_team} cannot as many points as {team}.")
            return (
                False, None, None, None,None
            )

    G, source, sink = create_graph(teams_data, matches, allow_ties)

    print(G)
    # for i in G.edges(data=True):
    #     print(i)

    max_flow_val, max_flow_path = nx.maximum_flow(G, source, sink)
    # print(max_flow_val)
    # print(max_flow_val + target_team_games_left)
    # print(max_flow_path)
    return (
        True,
        max_flow_val == ((int(allow_ties)) + 1) * games_to_schedule,
        (
            math.floor(max_flow_val / 2) + target_team_games_left
            if allow_ties
            else max_flow_val + target_team_games_left
        ),
        total_matches,
        max_flow_path,
    )

def main():
    target_team = "Delhi Capitals"
    # simple_check, success, scheduled_count, total_matches, max_flow_path = (
    #     get_possibility(
    #         target_team,
    #         "data/ipl_2024_points_table_edit.csv",
    #         "data/ipl_2024_schedule_edit.csv",
    #         allow_ties=True,
    #     )
    # )
    simple_check, success, scheduled_count, total_matches, max_flow_path = (
        get_possibility(
            target_team,
            "data/ipl_2025_points_table.csv",
            "data/ipl_2025_schedule.csv",
            allow_ties=True,
        )
    )
    if simple_check:
        print(f'{target_team} can end at the top: {success}')
        print(f'Scheduled {scheduled_count} out of {total_matches} matches.')


if __name__ == '__main__':
    main()
