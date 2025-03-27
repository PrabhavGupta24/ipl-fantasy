import csv
import requests
from bs4 import BeautifulSoup


def get_points_table_data(points_table_link):
    points_table_data = {}
    response = requests.get(points_table_link)
    bs_response = BeautifulSoup(response.content, "html.parser")
    table = bs_response.find_all("table")[0].tbody
    table_entries = table.find_all("tr", recursive=False)[::2]
    keys = ['Name', 'Matches', 'Won', 'Lost', 'Tied/NR', 'Points', 'NRR']

    for entry in table_entries:
        contents = entry.contents
        name = contents[0].text.split('(')[0].strip()
        points_table_data[name] = {
            keys[0]: name,
            keys[1]: contents[1].text,
            keys[2]: contents[2].text,
            keys[3]: contents[3].text,
            keys[4]: int(contents[4].text) + int(contents[5].text),
            keys[5]: contents[6].text,
            keys[6]: contents[7].text,
        }

    return points_table_data, keys


def get_schedule_data(schedule_link):

    schedule_data = {}
    response = requests.get(schedule_link)
    bs_response = BeautifulSoup(response.content, 'html.parser')
    series_div = bs_response.find('div', id='series-matches')
    match_entries = list(series_div.findAll('div', class_='cb-series-matches'))
    keys = ['Match Number', 'Teams', 'Completed', 'Tied/NR', 'Result String', 'Winner', 'Loser', 'Margin Runs', 'Margin Wickets']
    match_number = 1

    for match in match_entries[:70]:
        internal_links = match.find_all('a')

        schedule_data[match_number] = {
            keys[0]: match_number,
            keys[1]: sorted(internal_links[0].text.split(',')[0].split(' vs ')),
            keys[2]: 1 if 'complete' in internal_links[1]['class'][0] else 0
        }

        #TODO: Actually account for Tied/No Results
        #TODO: Account for Super Overs
        if schedule_data[match_number][keys[2]]:
            schedule_data[match_number][keys[3]] = 0
            schedule_data[match_number][keys[4]] = internal_links[1].text
            result_parts = internal_links[1].text.split(' won by ')
            schedule_data[match_number][keys[5]] = result_parts[0]
            schedule_data[match_number][keys[6]] = (
                set(schedule_data[match_number][keys[1]]) - {result_parts[0]}
            ).pop()

            if 'run' in result_parts[1]:
                schedule_data[match_number][keys[7]] = result_parts[1].split('run')[0].strip()
            elif "wkt" in result_parts[1]:
                schedule_data[match_number][keys[8]] = result_parts[1].split('wkt')[0].strip()
            else:
                print(match_number, "ERROR:", result_parts[1])

        match_number += 1

    return schedule_data, keys


def export_data(filename, fieldnames, player_entries):

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for name in player_entries:
            writer.writerow(player_entries[name])

    print("Data Exported to:", filename)


def get_curr_tournament_data():
    # main function
    # get points table data -> gets list of teams -> export
    # get match results -> export
    # schedule_link = 'https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/matches'
    # points_table_link = 'https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/points-table'
    schedule_link = 'https://www.cricbuzz.com/cricket-series/7607/indian-premier-league-2024/matches'
    points_table_link = 'https://www.cricbuzz.com/cricket-series/7607/indian-premier-league-2024/points-table'

    points_table_data, points_table_keys = get_points_table_data(points_table_link)
    export_data('ipl_2024_points_table.csv', points_table_keys, points_table_data)

    schedule_data, schedule_keys = get_schedule_data(schedule_link)
    export_data("ipl_2024_schedule.csv", schedule_keys, schedule_data)


if __name__ == '__main__':
    get_curr_tournament_data()
