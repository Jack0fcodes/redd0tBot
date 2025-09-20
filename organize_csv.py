import csv

input_file = "posts_reddit.csv"
output_file = "posts_reddit.csv"
header = ["PostID", "Subreddit", "Title", "Author", "URL"]

rows = []

with open(input_file, newline='', encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        # skip empty rows
        if not row or all(not x.strip() for x in row):
            continue
        # fill missing columns
        if len(row) == 3:
            # Assume: Subreddit, Title, URL
            rows.append(["", row[0], row[1], "", row[2]])
        elif len(row) == 5:
            rows.append(row)
        else:
            # skip malformed
            continue

# remove duplicates based on PostID + Title + Subreddit (optional)
seen = set()
cleaned_rows = []
for row in rows:
    key = tuple(row)
    if key not in seen:
        cleaned_rows.append(row)
        seen.add(key)

with open(output_file, "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(cleaned_rows)

print(f"Organized CSV written to {output_file}")
