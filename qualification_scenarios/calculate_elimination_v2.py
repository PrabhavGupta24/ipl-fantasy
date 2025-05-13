import networkx as nx
from itertools import combinations
from collections import defaultdict, OrderedDict
import tournament_data as tournament
from typing import cast
from constraint_classes import MatchConstraint, TeamConstraint


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
    match_constraints=[],
    team_constraints=[],
    allow_match_ties=False,
    reject_pt_ties=False,
    top_n=4,
):

    pt_keys, points_table_data, sched_keys, schedule_data = tournament.import_from_csv(pt_filepath, schedule_filepath)
    
    # Apply match constraints (using update_tournament_data())
    for game in match_constraints:
        game = cast(MatchConstraint, game)
        update_tournament_data(
            game.winner,
            game.loser,
            schedule_data[int(game.match_number) - 1],
            points_table_data,
            game.match_tied,
        )

    incomplete_games, unplayed_match_counts, total_unplayed_matches = (
        get_incomplete_games(schedule_data)
    )
    points_per_team = clean_points_table_data(points_table_data)

    all_teams = points_per_team.keys()
    target_team_points = points_per_team[target_team]

    # Get remaining matches for target team
    target_team_games_left = sum(
        unplayed_match_counts[game]
        for game in unplayed_match_counts
        if target_team in game
    )

    # Get max points for target team
    target_team_max_points = target_team_points + 2 * target_team_games_left

    target_team_upper_bound = float('inf')
    for constraint in team_constraints:
        if constraint.team_name == target_team and constraint.upper_bound is not None:
            target_team_upper_bound = min(target_team_upper_bound, constraint.upper_bound)

    if not allow_match_ties:
        target_team_upper_bound *= 2

    target_team_upper_bound += target_team_points
    target_team_max_points = min(target_team_max_points, target_team_upper_bound)

    # Set number of points/wins that each team can still get
    # If reject_pt_ties -> decrease number of points that can be earned by 1
    capacity_per_team = {}
    for team in all_teams - {target_team}:
        capacity_per_team[team] = (
            target_team_max_points - points_per_team[team] - int(reject_pt_ties)
        )

    capacity_per_team[target_team] = target_team_max_points - target_team_points

    # If allow_match_ties -> pts that can be earned (no change), Else -> games that can be won (int div by 2)
    if not allow_match_ties:
        for team in all_teams:
            capacity_per_team[team] //= 2

    target_max_flow = ((int(allow_match_ties)) + 1) * total_unplayed_matches
    target_team_demand = capacity_per_team[target_team]

    # Make the graph
    # allow_match_ties -> using_points -> capacity of 2 along game edges instead of 1
    G, source, sink = create_graph(
        capacity_per_team, unplayed_match_counts, using_points=allow_match_ties
    )

    # Insert Demand
    G.nodes[source]['demand'] = -1 * target_max_flow
    G.nodes[sink]['demand'] = target_max_flow 

    # Apply Team Constraints
    for team_const in team_constraints:
        apply_team_constraint(G, sink, team_const)

    # Ensure that the target team's lower bound = upper bound
    apply_team_constraint(G, sink, TeamConstraint(target_team, lower_bound=G.nodes[target_team].get("upper_bound", target_team_demand)))

    log_graph(G, all_teams, sink)

    capacity_per_team = {team : G[team][sink]["capacity"] for team in all_teams}

    # Get parameters for calculating max flow, and calculate
    success, max_flow_path = get_max_flow(G, sink, all_teams, target_team, capacity_per_team, top_n)

    if success:
        generate_tournament_results_from_flow(
            max_flow_path,
            points_table_data,
            schedule_data,
            pt_speculation,
            schedule_speculation,
            allow_match_ties,
        )

    return (
        success,
        total_unplayed_matches,
        max_flow_path,
    )


def apply_team_constraint(G, sink, constraint:TeamConstraint):
    if constraint.lower_bound is not None:
        curr_lower_bound = G.nodes[constraint.team_name].get("demand", 0)
        if curr_lower_bound < constraint.lower_bound:
            G.nodes[constraint.team_name]["demand"] = constraint.lower_bound
            G[constraint.team_name][sink]["capacity"] -= (constraint.lower_bound - curr_lower_bound)
            G.nodes[sink]["demand"] -= (constraint.lower_bound - curr_lower_bound)

            if "upper_bound" in G.nodes[constraint.team_name]:
                G[constraint.team_name][sink]["upper_bound"] -= (
                    constraint.lower_bound - curr_lower_bound
                )

    if constraint.upper_bound is not None:
        new_capacity = constraint.upper_bound - G.nodes[constraint.team_name].get("demand", 0)
        G[constraint.team_name][sink]["capacity"] = min(
            G[constraint.team_name][sink]["capacity"], new_capacity
        )
        G.nodes[constraint.team_name]["upper_bound"] = min(
            G.nodes[constraint.team_name].get("upper_bound", float('inf')), new_capacity
        )


def get_max_flow(G, sink, teams, target_team, teams_data, top_n=1):

    flow_path = None

    if top_n <= 1:
        # Check for negative edge weights
        if any(edge[2]['capacity'] < 0 for edge in G.edges(teams, data=True)):
            return False, float('-inf'), None

        _, flow_path = nx.network_simplex(G)
        try:
            _, flow_path = nx.network_simplex(G)
        except:
            pass

        return flow_path != None, flow_path

    else:

        # Loop through every combo of teams to ignore
        for team_combo in combinations(teams - {target_team}, top_n - 1):

            # Set ignored edge weights
            for team in team_combo:
                G[team][sink]['capacity'] = G.nodes[team].get("upper_bound", 100)

            try:
                # Check for negative edge weights
                if any(edge[2]['capacity'] < 0 for edge in G.edges(teams, data=True)):
                    continue

                _, flow_path = nx.network_simplex(G)

            except nx.NetworkXUnfeasible as e:
                pass
                
            else:
                log_graph(G, teams, sink, flow_path)
                return True, flow_path

            # Restore Edge Weights
            finally:
                for team in team_combo:    
                    G[team][sink]["capacity"] = teams_data[team]

        return False, None


def generate_tournament_results_from_flow(
    flow_path,
    points_table_data,
    schedule_data,
    pt_speculation,
    schedule_speculation,
    using_points=False,
):
    flow_dict = flow_path.copy()
    adj_for_points = int(using_points)
    for game in schedule_data:
        if not int(game["Completed"]):
            team1, team2 = tuple(sorted(game["Teams"].split(",")))
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


def log_graph(G, team_names, sink, flow_dict=None, filename="log.txt"):
    with open(filename, "w") as f:
        f.write("=== Node Data (Teams and Sink) ===\n")
        for node in team_names | {sink}:
            node_data = G.nodes[node]
            f.write(f"Node: {node}, Data: {node_data}\n")

        f.write("\n=== Edge Data (Team → Sink) ===\n")
        for team in team_names:
            if G.has_edge(team, sink):
                edge_data = G[team][sink]
                capacity = edge_data.get("capacity", "N/A")
                if flow_dict and team in flow_dict and sink in flow_dict[team]:
                    flow = flow_dict[team][sink]
                else:
                    flow = "N/A"
                f.write(
                    f"Edge: {team} → {sink}, Capacity: {capacity}, Flow: {flow}, Full Edge Data: {edge_data}\n"
                )
            else:
                f.write(f"Edge: {team} → {sink} does not exist.\n")

    print(f"✅ Log written to: {filename}")


def update_tournament_data(winner, loser, game, points_table_data, match_tied=False):
    if match_tied:
        game["Tied/NR"] = 1
        points_table_data[winner]["Tied/NR"] = 1 + int(
            points_table_data[winner]["Tied/NR"]
        )
        points_table_data[winner]["Points"] = 1 + int(
            points_table_data[winner]["Points"]
        )
        points_table_data[loser]["Tied/NR"] = 1 + int(
            points_table_data[loser]["Tied/NR"]
        )
        points_table_data[loser]["Points"] = 1 + int(
            points_table_data[loser]["Points"]
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
    target_team = "Royal Challengers Bengaluru"
    top_n = 4
    allow_match_ties = True
    reject_pt_ties = True

    match_constraints = []
    # match_constraints.append(MatchConstraint(65, winner="Gujarat Titans", loser="Lucknow Super Giants"))
    team_constraints = []
    team_constraints.append(
        TeamConstraint("Royal Challengers Bengaluru", upper_bound=0)
    )

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
    success, total_matches, max_flow_path = get_possibility(
        target_team,
        "data/ipl_2025_points_table_removed.csv",
        "data/ipl_2025_schedule_removed.csv",
        "data/ipl_2025_points_table_speculation.csv",
        "data/ipl_2025_schedule_speculation.csv",
        match_constraints=match_constraints,
        team_constraints=team_constraints,
        allow_match_ties=allow_match_ties,
        reject_pt_ties=reject_pt_ties,
        top_n=top_n,
    )

    print(f'{target_team} can end in the top {top_n}: {success}')


if __name__ == '__main__':
    main()
