import csv
from tournament_data import export_to_csv, import_from_csv
from collections import OrderedDict


def remove_matches(
    num_to_remove, pt_data, schedule_data
):
    num_to_remove = min(num_to_remove, len(schedule_data))
    s_fieldname_keep = ["Match Number", "Teams", "Completed"]

    for i in range(len(schedule_data) - 1, len(schedule_data) - 1 - num_to_remove, -1):
        match = schedule_data[i]

        if int(match['Completed']):
            team1, team2 = match['Teams'].split(',')
            pt_data[team1]['Matches'] = int(pt_data[team1]['Matches']) - 1
            pt_data[team2]["Matches"] = int(pt_data[team2]["Matches"]) - 1

            if int(match['Tied/NR']):
                pt_data[team1]["Tied/NR"] = int(pt_data[team1]["Tied/NR"]) - 1
                pt_data[team2]["Tied/NR"] = int(pt_data[team2]["Tied/NR"]) - 1

                pt_data[team1]["Points"] = int(pt_data[team1]["Points"]) - 1
                pt_data[team2]["Points"] = int(pt_data[team2]["Points"]) - 1
            else:
                winner = match["Winner"]
                loser = match['Loser']
                pt_data[winner]["Won"] = int(pt_data[winner]["Won"]) - 1
                pt_data[loser]["Lost"] = int(pt_data[loser]["Lost"]) - 1

                pt_data[winner]["Points"] = int(pt_data[winner]["Points"]) - 2

        match['Completed'] = 0
        schedule_data[i] = {k: v for k, v in match.items() if k in s_fieldname_keep}

    pt_data = OrderedDict(sorted(pt_data.items(), key=lambda entry: int(entry[1]['Points']), reverse=True))

    return pt_data, schedule_data

def remove_matches_driver(num_to_remove, pt_filepath, sched_filepath, pt_outpath, sched_outpath):
    pt_fieldnames, pt_data, schedule_fieldnames, schedule_data = import_from_csv(
        pt_filepath, sched_filepath
    )
    pt_data, schedule_data = remove_matches(num_to_remove, pt_data, schedule_data)
    export_to_csv(pt_outpath, pt_fieldnames, pt_data)

    schedule_data = {entry["Match Number"]: entry for entry in schedule_data}
    export_to_csv(sched_outpath, schedule_fieldnames, schedule_data)


def main():
    pt_filepath = "data/ipl_2025_points_table.csv"
    pt_filepath_removed = "data/ipl_2025_points_table_removed.csv"
    schedule_filepath = "data/ipl_2025_schedule.csv"
    schedule_filepath_removed = "data/ipl_2025_schedule_removed.csv"

    remove_matches_driver(
        20,
        pt_filepath,
        schedule_filepath,
        pt_filepath_removed,
        schedule_filepath_removed,
    )
    # # new_pt_filepath = "data/ipl_2024_points_table_edit.csv"
    # # new_schedule_filepath = "data/ipl_2024_schedule_edit.csv"
    # pt_data, schedule_data = remove_matches(20, pt_data, schedule_data)
    # # export_to_csv(new_pt_filepath, pt_fieldnames, pt_data)
    # export_to_csv(pt_filepath_removed, pt_fieldnames, pt_data)

    # schedule_data = {entry['Match Number']: entry for entry in schedule_data}
    # # export_to_csv(new_schedule_filepath, schedule_fieldnames, schedule_data)
    # export_to_csv(schedule_filepath_removed, schedule_fieldnames, schedule_data)


if __name__ == '__main__':
    main()
