import os
import requests
import re

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
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
            "hireanartist",  "starvingartist", "DrawForMe",
            "CatsWithDogs", "starvingartists"
        ]
        # Split into two types: bracketed tags and word matchers
        bracket_keywords = [
            r"\[HIRING\]", r"\[Hiring\]", r"\[hiring\]",
            r"\[looking for artist\]", r"\[Looking for artist \]", r"\[Looking for Artist \]",
            r"\[Looking For Artist \]", r"\[LOOKING FOR ARTIST\]", r"\[LOOKING FOR\]", r"\[looking for\]"
        ]
        # Use word boundaries for plain keywords
        word_keywords = [
            r"\bhiring\b",
            r"\blooking for\b"
        ]
        limit = 5

        # Compile regex patterns (case-insensitive)
        patterns = [re.compile(bk, re.IGNORECASE) for bk in bracket_keywords] + \
                   [re.compile(wk, re.IGNORECASE) for wk in word_keywords]

        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                content = (data.get("title", "") + " " + data.get("selftext", ""))
                if any(pattern.search(content) for pattern in patterns):
                    title = data.get("title", "")
                    link = "https://reddit.com" + data.get("permalink", "")
                    message = f"📌 [{subreddit}] {title}\n{link}"
                    send_to_telegram(message)
        print("✅ Sent filtered posts to Telegram")
    except Exception as e:
        print(f"❌ Error: {e}")
