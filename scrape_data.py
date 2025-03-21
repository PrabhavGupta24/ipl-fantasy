import requests
from bs4 import BeautifulSoup
import csv


DOMAIN = 'https://www.cricbuzz.com'


def get_tournament_match_links(tournament_link):
    response = requests.get(tournament_link)
    bs_response = BeautifulSoup(response.content, 'html.parser')

    series_div = bs_response.find('div', id='series-matches')
    match_entries = list(series_div.findAll('div', class_='cb-series-matches'))

    match_links = []
    for match in match_entries:
        link = match.find('a')['href']
        link = DOMAIN + link.replace('cricket-scores', 'live-cricket-scorecard')
        match_links.append(link)
    
    return match_links

def get_squad_names(sqauds_link):
    team1_squad_names = {}
    team2_squad_names = {}
    squad_data = requests.get(sqauds_link)
    squad_data = BeautifulSoup(squad_data.content, 'html.parser')
    
    team1_data = squad_data.findAll('div', class_='cb-play11-lft-col')[:2]
    team2_data = squad_data.findAll('div', class_='cb-play11-rt-col')[:2]

    get_squad_names_helper(team1_squad_names, team1_data, 'left')
    # print(*team1_squad_names.values(), sep='\n')
    get_squad_names_helper(team2_squad_names, team2_data, 'right')
    # print(*team2_squad_names.values(), sep='\n')
    return team1_squad_names, team2_squad_names

def get_squad_names_helper(squad_names, team_data, side):
    for section in team_data:
        players = section.findAll('div', class_='cb-col-100')
        for player in players:
            link_section = player.find('a')
            if not link_section:
                break
            player_num = get_player_num(link_section)
            
            
            player_info = player.find('div', class_='cb-player-name-' + side)
            name = player_info.find('div').find(string=True, recursive=False).strip()
            name = name.replace('(C)', '').replace('(WK)', '').strip()

            role = player_info.find('span').text.strip()
            role = 'Allrounder' if 'Allrounder' in role else role

            squad_names[player_num] = (name, role)

def get_player_num(player_link_section):
    player_num = player_link_section['href'].strip('/').split('/')[1]
    player_num = int(player_num)
    return player_num


def clean_name_and_initialize(unfiltered_link_section, squad, player_entries, match_number):
    unfiltered_name = unfiltered_link_section.text
    is_captain = 1 if '(c)' in unfiltered_name.lower() else 0
    is_keeper = 1 if '(wk)' in unfiltered_name.lower() else 0

    player_num = get_player_num(unfiltered_link_section)
    name, role = squad[player_num]

    if name not in player_entries:
        player_entries[name] = {'Match Number': match_number,
                                'Name': name,
                                'Role': role,
                                'Captain': is_captain,
                                'Wicketkeeper': is_keeper,
                                'Out String': 'Did Not Bat',
                                'Batting Runs': 0,
                                'Balls': 0,
                                '4s': 0,
                                '6s': 0,
                                'Strike Rate': 0.00,
                                'Overs': 0.0,
                                'Maidens': 0,
                                'Bowling Runs': 0,
                                'Wickets': 0,
                                'No Balls': 0,
                                'Wides': 0,
                                'Economy': 0.00,
                                'Catches': 0,
                                'Run Outs': 0.0,
                                'Stumpings': 0}
    
    return name


def get_card_data(raw_card, match_number, player_entries, sqauds, batting=True):
    
    for entry in raw_card.findAll('div', class_='cb-scrd-itms'):
        if entry.find('div', class_='cb-col-60'): #Got to Extras
            break
        entry_contents = entry.findAll('div')
        unfiltered_name = entry_contents[0].find('a')
        name = clean_name_and_initialize(unfiltered_name, sqauds, player_entries, match_number)
        
        player_entry = player_entries[name]
        
        
        if batting:
            out_string = entry_contents[1].find('span').text
            print(out_string)
            player_entry['Out String'] = out_string

            player_entry['Batting Runs'] = entry_contents[2].text
            player_entry['Balls'] = entry_contents[3].text
            player_entry['4s'] = entry_contents[4].text
            player_entry['6s'] = entry_contents[5].text
            player_entry['Strike Rate'] = entry_contents[6].text

        else:
            player_entry['Overs'] = entry_contents[1].text
            player_entry['Maidens'] = entry_contents[2].text
            player_entry['Bowling Runs'] = entry_contents[3].text
            player_entry['Wickets'] = entry_contents[4].text
            player_entry['No Balls'] = entry_contents[5].text
            player_entry['Wides'] = entry_contents[6].text
            player_entry['Economy'] = entry_contents[7].text
    
    if batting:
        unfiltered_names = list(raw_card.findAll('div', class_='cb-scrd-itms'))[-1].findAll('a')
        for unfiltered_name in unfiltered_names:
            clean_name_and_initialize(unfiltered_name, sqauds, player_entries, match_number)
        

def initialize_output_file(filename, fieldnames):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    print("Output File Created")

def export_data(filename, fieldnames, player_entries):
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        for name in player_entries:
            writer.writerow(player_entries[name])
    
    print("Data Exported to:", filename)



match_links = get_tournament_match_links('https://www.cricbuzz.com/cricket-series/7607/indian-premier-league-2024/matches')

filename = 'ipl_2024_scorecards.csv'
fieldnames = ['Match Number', 'Name', 'Role', 'Captain', 'Wicketkeeper',
              'Out String', 'Batting Runs', 'Balls', '4s', '6s', 'Strike Rate',
              'Overs', 'Maidens', 'Bowling Runs', 'Wickets', 'No Balls', 'Wides', 'Economy', 'Catches', 'Run Outs', 'Stumpings']

initialize_output_file(filename, fieldnames)

for match_number, link in enumerate(match_links):
    team1_squad_names, team2_squad_names = get_squad_names(link.replace('live-cricket-scorecard', 'cricket-match-squads'))
    
    match_data = requests.get(link)
    match_data = BeautifulSoup(match_data.content, 'html.parser')
    player_entries = {}

    innings1 = match_data.find('div', id='innings_1')
    innings2 = match_data.find('div', id='innings_2')

    innings1_parts = innings1.contents
    innings2_parts = innings2.contents
    # 0, 2, 5, 7, 9 -> empty
    # 1 -> batting card
    # 3 -> Fall of Wickets header
    # 4 -> Fall of Wickets card
    # 6 -> bowling card
    # 8 -> Powerplay card

    batting_card_1 = innings1_parts[1]
    bowling_card_1 = innings1_parts[6]
    batting_card_2 = innings2_parts[1]
    bowling_card_2 = innings2_parts[6]

    #for now, merging the squads
    squads = team1_squad_names | team2_squad_names
    get_card_data(batting_card_1, match_number, player_entries, squads, batting=True)
    get_card_data(bowling_card_1, match_number, player_entries, squads, batting=False)
    get_card_data(batting_card_2, match_number, player_entries, squads, batting=True)
    get_card_data(bowling_card_2, match_number, player_entries, squads, batting=False)
    print(player_entries.keys())
    print(len(player_entries))

    export_data(filename, fieldnames, player_entries)


    

    break

    