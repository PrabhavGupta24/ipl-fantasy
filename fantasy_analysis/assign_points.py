import csv


infile_path = 'ipl_2024_scorecards.csv'
outfile_path = 'ipl_2024_scorecards_points.csv'

with open(infile_path, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)  # Read the file as a dictionary
    fieldnames = list(reader.fieldnames)
    fieldnames.insert(3, 'Points')  # Add 'Points' to the fieldnames
    
    # Read all rows into a list
    rows = list(reader)

for row in rows:
    points = 0
    runs = int(row['Batting Runs'])

    points += runs
    points += int(row['4s'])
    points += (2 * int(row['6s']))

    if runs >= 100:
        points += 16
    elif runs >= 50:
        points += 8
    elif runs >= 30:
        points += 4

    if runs == 0 and str(row['Role']) != 'Bowler' and str(row['Out String']) != 'did not bat' and str(row['Out String']) != 'not out':
        points -= 2
    
    wickets = int(row['Wickets'])
    points += (25 * wickets)

    points += 12 * int(row['Maidens'])
    points +=8 * int(row['LBW/Bowled'])
    if wickets >= 5:
        points += 16
    elif wickets == 4:
        points += 8
    elif wickets == 3:
        points += 4
    catches = int(row['Catches'])
    points += 8 * catches
    if catches >= 3:
        points += 4
    points += 12 * int(row['Stumpings'])
    points += 12 * float(row['Run Outs'])
    economy = float(row['Economy'])
    if (float(row['Overs']) >= 2):
        if economy <= 5:
            points += 6
        elif economy <= 5.99:
            points += 4
        elif economy <= 6.99:
            points += 2
        elif economy <= 9.99:
            points += 0
        elif economy <= 10.99:
            points -= 2
        elif economy <= 11.99:
            points -= 4
        elif economy >= 12:
            points -= 6
    
    strike_rate = float(row['Strike Rate'])
    if (str(row['Role']) != 'Bowler' and int(row['Balls']) >= 10) :
        if strike_rate < 50:
            points -= 6
        elif strike_rate < 60:
            points -= 4
        elif strike_rate < 70:
            points -= 2
        elif strike_rate < 130:
            points -= 0
        elif strike_rate < 150:
            points += 2
        elif strike_rate < 170:
            points += 4
        elif strike_rate >= 170:
            points += 6
    

    # Add points to the row
    row['Points'] = points

# Open the CSV file for writing (overwriting the original file)
with open(outfile_path, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()  # Write the header
    
    # Write the modified rows back to the file
    writer.writerows(rows)

print(f"Points have been calculated and stored in {outfile_path}.")
