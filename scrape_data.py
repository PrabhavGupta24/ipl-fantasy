import requests
from bs4 import BeautifulSoup

response = requests.get("https://www.cricbuzz.com/cricket-series/7607/indian-premier-league-2024/matches")

DOMAIN = 'https://www.cricbuzz.com'
print(response.status_code)
bs_response = BeautifulSoup(response.content, 'html.parser')
# print(bs_response.prettify())
series_div = bs_response.find('div', id='series-matches')
# print(series_div.prettify()[:1000])
match_entries = list(series_div.findAll('div', class_='cb-series-matches'))

# print(match_entries[0].prettify())

match_links = []
for match in match_entries:
    link = match.find('a')['href']
    link = DOMAIN + link.replace('cricket-scores', 'live-cricket-scorecard')
    match_links.append(link)

print(match_links)
print(len(match_links))

    