# ipl-fantasy


## How to Run


### Qualification Scenarios
Use the terminal to run the script with your desired arguments. Example (-e for "is team eliminated", -q for "has team qualified"):

```bash
python speculation_driver.py \
  --team_name "TeamX" \
  --ipl_year 2025 \
  --removed_games 0\
  --top_n 4 \
  -e \
  --allow_match_ties \
  --reject_pt_ties \
  --match_constraints '[{"match_number": 1, "winner": "TeamA", "loser": "TeamB", "match_tied": false}]' \
  --team_constraints '[{"team_name": "TeamC", "lower_bound": 2, "upper_bound": 5}]'
```

Todo:
- make this a website
- allow "target_team" to be multiple teams, with some qualifying and some not
