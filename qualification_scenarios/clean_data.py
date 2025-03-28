import csv
from scrape_curr_data import export_data

def extract_data(pt_filepath, schedule_filepath):
    pt_fieldnames = []
    pt_data = {}
    schedule_fieldnames = []
    schedule_data = {}

    with open(pt_filepath, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        pt_data = {row["Name"]: row for row in reader}
        pt_fieldnames = reader.fieldnames

    with open(schedule_filepath, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        schedule_data = list(reader)
        schedule_fieldnames = reader.fieldnames

    return pt_fieldnames, pt_data, schedule_fieldnames, schedule_data


def remove_matches(
    num_to_remove, pt_data, schedule_data
):
    num_to_remove = min(num_to_remove, len(schedule_data))
    s_fieldname_keep = ["Match Number", "Teams", "Completed"]

    for i in range(len(schedule_data) - 1, len(schedule_data) - 1 - num_to_remove, -1):
        match = schedule_data[i]

        if match['Completed']:
            team1, team2 = match['Teams'].split(',')
            pt_data[team1]['Matches'] = int(pt_data[team1]['Matches']) - 1
            pt_data[team2]["Matches"] = int(pt_data[team2]["Matches"]) - 1

            if match['Tied/NR']:
                pt_data[team1]["Tied/NR"] = int(pt_data[team1]["Tied/NR"]) - 1
                pt_data[team2]["Tied/NR"] = int(pt_data[team2]["Tied/NR"]) - 1

                pt_data[team1]["Points"] = int(pt_data[team1]["Points"]) - 1
                pt_data[team2]["Points"] = int(pt_data[team2]["Points"]) - 1
            else:
                winner = match["Winner"]
                loser = match['Loser']
                pt_data[winner]["Won"] = int(pt_data[winner]["Won"]) - 1
                pt_data[loser]["Lost"] = int(pt_data[loser]["Lost"]) - 1

                pt_data[winner]["Points"] = int(pt_data[team1]["Points"]) - 2

        schedule_data[i] = {k: v for k, v in match.items() if k in s_fieldname_keep}


    return pt_data, schedule_data


def main():
    pt_filepath = "data/ipl_2024_points_table.csv"
    schedule_filepath = "data/ipl_2024_schedule.csv"
    pt_fieldnames, pt_data, schedule_fieldnames, schedule_data = extract_data(
        pt_filepath, schedule_filepath
    )

    new_pt_filepath = "data/ipl_2024_points_table_edit.csv"
    new_schedule_filepath = "data/ipl_2024_schedule_edit.csv"
    pt_data, schedule_data = remove_matches(20, pt_data, schedule_data)
    export_data(new_pt_filepath, pt_fieldnames, pt_data)

    schedule_data = {entry['Match Number']: entry for entry in schedule_data}
    export_data(new_schedule_filepath, schedule_fieldnames, schedule_data)


if __name__ == '__main__':
    main()
