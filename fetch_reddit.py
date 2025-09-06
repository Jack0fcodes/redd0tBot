import os
import requests
import csv

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CSV_FILE = "posts_reddit.csv"

# Get Reddit OAuth token
def get_reddit_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": USER_AGENT}
    res = requests.post("https://www.reddit.com/api/v1/access_token",
                        auth=auth, data=data, headers=headers)
    res.raise_for_status()
    return res.json()["access_token"]

# Fetch newest subreddit posts
def fetch_posts(subreddit, limit=3):
    token = get_reddit_token()
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={limit}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"]["children"]

# Send to Telegram
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    res = requests.post(url, json=payload)
    res.raise_for_status()

# Load existing post IDs from CSV
def load_existing_ids():
    if not os.path.isfile(CSV_FILE):
        return set()
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        return {row[0] for row in csv.reader(f) if row and row[0] != "PostID"}

# Save new posts to CSV
def save_to_csv(posts):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["PostID", "Subreddit", "Title", "Author", "URL"])  # header
        for subreddit, post in posts:
            pid = post["data"]["id"]
            title = post["data"]["title"]
            author = post["data"].get("author", "unknown")
            link = "https://reddit.com" + post["data"]["permalink"]
            writer.writerow([pid, subreddit, title, author, link])

if __name__ == "__main__":
    try:
        subreddits = [
    "HungryArtists",
    "commissions",
    "DesignJobs",
    "artcommission",
    "artcommissions",
    "artisthirecommission",
    "announcements",
    "Artcommission",
    "Artistsforhire",
    "artstore",
    "ComicBookCollabs",
    "commissionart",
    "Commissions_",
    "Commissions_rh",
    "dndcommissions",
    "FurryCommissions",
    "FursCommissions",
    "hireanartist",
    "HungryArtistsFed",
    "starvingartist",
    "DrawForMe",
    "CatsWithDogs",
    "starvingartists"
]
        keywords = ["hiring", "looking for"]
        limit = 5

        # Load archive of IDs
        existing_ids = load_existing_ids()

        new_posts = []
        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                pid = data["id"]
                title = data.get("title", "")
                body = data.get("selftext", "")
                link = "https://reddit.com" + data["permalink"]
                content = (title + " " + body).lower()

                # Only process new + keyword-matching posts
                if any(keyword in content for keyword in keywords) and pid not in existing_ids:
                    new_posts.append((subreddit, post))

        if new_posts:
            # Send to Telegram
            for subreddit, post in new_posts:
                title = post["data"]["title"]
                author = post["data"].get("author", "unknown")
                link = "https://reddit.com" + post["data"]["permalink"]
                message = f"📌 Subreddit: {subreddit}\nTitle: {title}\nAuthor: {author}\nURL: {link}"
                send_to_telegram(message)

            # Save to CSV archive
            save_to_csv(new_posts)

            print(f"✅ {len(new_posts)} new posts sent & saved")
        else:
            print("⚠️ No new posts found")
    except Exception as e:
        print(f"❌ Error: {e}")
