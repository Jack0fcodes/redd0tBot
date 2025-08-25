import os
import requests

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
def fetch_posts(subreddit, limit=5):
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
            "hiring",
            "looking for",
            "[HIRING]",
            "[Hiring]",
            "[hiring]",
            "[looking for artist]",
            "[Looking for artist ]",
            "[Looking for Artist ]",
            "[Looking For Artist ]",
            "[LOOKING FOR ARTIST]",
            "[LOOKING FOR]",
            "[looking for]"
        ]
        limit = 5  # Number of new posts to fetch per subreddit

        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                content = (data.get("title", "") + " " + data.get("selftext", "")).lower()
                if any(keyword.lower() in content for keyword in keywords):
                    title = data.get("title", "")
                    link = "https://reddit.com" + data.get("permalink", "")
                    message = f"📌 [{subreddit}] {title}\n{link}"
                    send_to_telegram(message)
        print("✅ Sent filtered posts to Telegram")
    except Exception as e:
        print(f"❌ Error: {e}")
