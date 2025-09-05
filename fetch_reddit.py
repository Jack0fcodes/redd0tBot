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

# Save posts to CSV
def save_to_csv(posts):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Subreddit", "Title", "Link"])  # write header once
        for subreddit, post in posts:
            title = post["data"]["title"]
            link = "https://reddit.com" + post["data"]["permalink"]
            writer.writerow([subreddit, title, link])

if __name__ == "__main__":
    try:
        subreddits = ["HungryArtists", "commissions", "artcommission"]
        keywords = ["hiring", "looking for"]
        limit = 5

        filtered_posts = []
        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                content = (data.get("title", "") + " " + data.get("selftext", "")).lower()
                if any(keyword in content for keyword in keywords):
                    filtered_posts.append((subreddit, post))

        if filtered_posts:
            # Send to Telegram
            for subreddit, post in filtered_posts:
                title = post["data"]["title"]
                link = "https://reddit.com" + post["data"]["permalink"]
                message = f"📌 [{subreddit}] {title}\n{link}"
                send_to_telegram(message)

            # Save to CSV
            save_to_csv(filtered_posts)

            print("✅ Sent filtered posts to Telegram & saved to CSV")
        else:
            print("⚠️ No posts found with specified keywords")
    except Exception as e:
        print(f"❌ Error: {e}")
