
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

if __name__ == "__main__":
    try:
        subreddits = ["HungryArtists", "commissions", "artcommission"]  # Add more here!
        keywords = ["hiring", "looking for"]
        limit = 5  # or any number you want

        filtered_posts = []
        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                content = (data.get("title", "") + " " + data.get("selftext", "")).lower()
                if any(keyword in content for keyword in keywords):
                    filtered_posts.append((subreddit, post))

        if filtered_posts:
            for subreddit, post in filtered_posts:
                title = post["data"]["title"]
                link = "https://reddit.com" + post["data"]["permalink"]
                message = f"📌 [{subreddit}] {title}\n{link}"
                send_to_telegram(message)
            print("✅ Sent filtered posts to Telegram")
        else:
            print("⚠️ No posts found with specified keywords")
    except Exception as e:
        print(f"❌ Error: {e}")
