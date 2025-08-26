import os
import requests
import re
import time

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("USER_AGENT", "RedditBot/0.1")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_reddit_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": USER_AGENT}
    res = requests.post("https://www.reddit.com/api/v1/access_token",
                        auth=auth, data=data, headers=headers)
    res.raise_for_status()
    return res.json()["access_token"]

def fetch_posts(subreddit, limit=5):
    token = get_reddit_token()
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={limit}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"]["children"]

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    res = requests.post(url, json=payload)
    res.raise_for_status()

if __name__ == "__main__":
    try:
        subreddits = [
            "HungryArtists", "commissions", "artcommission", "artcommissions",
            "artisthirecommission", "announcements", "Artcommission", "Artistsforhire",
            "artstore", "ComicBookCollabs", "commissionart", "Commissions_", "Commissions_rh",
            "DesignJobs", "dndcommissions", "FurryCommissions", "FursCommissions",
            "hireanartist", "HungryArtistsFed", "starvingartist", "DrawForMe",
            "CatsWithDogs", "starvingartists"
        ]
        keywords = [
            r"\[HIRING\]", r"\[Hiring\]", r"\[hiring\]",
            r"\[looking for artist\]", r"\[Looking for artist \]", r"\[Looking for Artist \]",
            r"\[Looking For Artist \]", r"\[LOOKING FOR ARTIST\]", r"\[LOOKING FOR\]", r"\[looking for\]",
            r"\bhiring\b", r"\blooking for artist\b", r"\blooking for\b"
        ]
        patterns = [re.compile(k, re.IGNORECASE) for k in keywords]
        limit = 5
        hours_limit = 6  # only fetch posts newer than this many hours

        current_time = int(time.time())

        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                post_time = int(data.get("created_utc", 0))
                hours_ago = (current_time - post_time) / 3600
                if hours_ago > hours_limit:
                    continue  # Skip posts older than hours_limit
                content = (data.get("title", "") + " " + data.get("selftext", ""))
                if any(pattern.search(content) for pattern in patterns):
                    title = data.get("title", "")
                    author = data.get("author", "")
                    link = "https://reddit.com" + data.get("permalink", "")
                    time_ago = (
                        f"{int(hours_ago)}h ago" if hours_ago >= 1
                        else f"{int((current_time - post_time) / 60)}m ago"
                        if (current_time - post_time) >= 60
                        else f"{current_time - post_time}s ago"
                    )
                    message = (
                        f"📌 [{subreddit}] {title}\n"
                        f"Author: {author}\n"
                        f"Posted: {time_ago}\n"
                        f"{link}"
                    )
                    send_to_telegram(message)
        print("✅ Sent filtered posts to Telegram")
    except Exception as e:
        print(f"❌ Error: {e}")
