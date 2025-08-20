import os
import requests
import time

# --- Config ---
SUBREDDITS = [
    "HungryArtists", "commissions", "artcommission", "artcommissions",
    "artisthirecommission", "Artistsforhire", "artstore", "ComicBookCollabs",
    "commissionart", "Commissions_", "Commissions_rh", "DesignJobs",
    "dndcommissions", "FurryCommissions", "FursCommissions", "hireanartist",
    "HungryArtistsFed", "starvingartist", "DrawForMe", "CatsWithDogs",
    "starvingartists"
]

KEYWORDS = [
    "[HIRING]", "[Hiring]", "[hiring]",
    "[looking for artist]", "[Looking for artist ]", "[Looking for Artist ]",
    "[Looking For Artist ]", "[LOOKING FOR ARTIST]", "[LOOKING FOR]",
    "[looking for]"
]

LIMIT = 5
SENT_FILE = "sent_posts.txt"

CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Reddit OAuth ---
def get_reddit_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": USER_AGENT}
    res = requests.post("https://www.reddit.com/api/v1/access_token",
                        auth=auth, data=data, headers=headers)
    res.raise_for_status()
    return res.json()["access_token"]

# --- Fetch posts ---
def fetch_posts(subreddit, limit=LIMIT):
    token = get_reddit_token()
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={limit}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"]["children"]

# --- Telegram ---
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    res = requests.post(url, json=payload)
    res.raise_for_status()

# --- Main ---
if __name__ == "__main__":
    sent_posts = set()
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            sent_posts = set(line.strip() for line in f)

    new_sent = set()
    total_checked = 0
    total_matched = 0

    try:
        for subreddit in SUBREDDITS:
            posts = fetch_posts(subreddit)
            print(f"🔍 Checking r/{subreddit}, got {len(posts)} posts...")
            for post in posts:
                total_checked += 1
                post_id = post["data"]["id"]
                title = post["data"]["title"]
                author = post["data"]["author"]
                link = "https://reddit.com" + post["data"]["permalink"]
                created_utc = post["data"]["created_utc"]
                age_mins = int((time.time() - created_utc) / 60)

                if post_id in sent_posts:
                    continue

                if any(kw in title for kw in KEYWORDS):
                    total_matched += 1
                    message = (
                        f"📢 Subreddit: {subreddit}\n"
                        f"📝 Title: {title}\n"
                        f"👤 Author: {author}\n"
                        f"⏰ Posted: {age_mins}m ago\n"
                        f"🔗 {link}"
                    )
                    send_to_telegram(message)
                    new_sent.add(post_id)
                    time.sleep(1)

        # Save updated sent list
        with open(SENT_FILE, "a") as f:
            for post_id in new_sent:
                f.write(post_id + "\n")

        print(f"✅ Checked {total_checked} posts, matched {total_matched}, sent {len(new_sent)} new ones")

        if total_matched == 0:
            send_to_telegram("⚠️ No matching posts found this run.")

    except Exception as e:
        error_msg = f"❌ Error: {e}"
        print(error_msg)
        send_to_telegram(error_msg)
