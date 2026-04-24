import os
import re
import requests
import csv
import sys

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCOUT_API_URL = os.getenv("SCOUT_API_URL")
SCOUT_API_KEY = os.getenv("SCOUT_API_KEY")

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

# Extract a budget string like "$800-1,500" or "$400" from post text
def extract_budget(text):
    if not text:
        return "Unknown"
    range_match = re.search(r"\$\s?(\d[\d,]*)\s?[-–]\s?\$?(\d[\d,]*)", text)
    if range_match:
        return f"${range_match.group(1)}-{range_match.group(2)}"
    single_match = re.search(r"\$\s?(\d[\d,]*)", text)
    if single_match:
        return f"${single_match.group(1)}"
    return "Unknown"

# Rough lead-quality heuristic based on signals in the post text
def classify_quality(text, budget):
    content = (text or "").lower()
    strong_signals = ["hiring", "budget", "paid", "commission", "dm portfolio", "asap"]
    weak_signals = ["looking for", "need", "want"]
    has_budget = budget != "Unknown"
    strong_hits = sum(1 for s in strong_signals if s in content)
    weak_hits = sum(1 for s in weak_signals if s in content)
    if has_budget and strong_hits >= 1:
        return "High Quality"
    if strong_hits >= 1 or weak_hits >= 1:
        return "Medium"
    return "Low"

# Send lead to Scout app
def send_to_scout(subreddit, post):
    if not SCOUT_API_URL:
        return
    data = post["data"]
    title = data.get("title", "")
    body = data.get("selftext", "")
    full_text = f"{title}\n\n{body}".strip() if body else title
    budget = extract_budget(f"{title} {body}")
    quality = classify_quality(f"{title} {body}", budget)
    payload = {
        "platform": "Reddit",
        "source": f"r/{subreddit}",
        "author": f"u/{data.get('author', 'unknown')}",
        "title": title,
        "content": full_text,
        "url": "https://reddit.com" + data["permalink"],
        "post_id": data.get("id"),
        "quality": quality,
        "budget": budget,
    }
    headers = {"Content-Type": "application/json"}
    if SCOUT_API_KEY:
        headers["Authorization"] = f"Bearer {SCOUT_API_KEY}"
    res = requests.post(SCOUT_API_URL, json=payload, headers=headers, timeout=10)
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
            "Commissions_rh",
            "dndcommissions",
            "gameDevClassifieds",
            "FurryCommissions",
            "hireanartist",
            "HungryArtistsFed",
            "starvingartist",
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
            scout_sent = 0
            scout_failed = 0
            # Send to Telegram (and Scout)
            for subreddit, post in new_posts:
                title = post["data"]["title"]
                author = post["data"].get("author", "unknown")
                link = "https://reddit.com" + post["data"]["permalink"]
                message = f"Subreddit: {subreddit}\nTitle: {title}\nAuthor: {author}\nURL: {link}"
                send_to_telegram(message)

                if SCOUT_API_URL:
                    try:
                        send_to_scout(subreddit, post)
                        scout_sent += 1
                    except Exception as scout_err:
                        scout_failed += 1
                        print(f"⚠️ Scout send failed for {post['data'].get('id')}: {scout_err}")

            # Save to CSV archive
            save_to_csv(new_posts)

            scout_summary = ""
            if SCOUT_API_URL:
                scout_summary = f" | Scout: {scout_sent} sent, {scout_failed} failed"
            print(f"✅ {len(new_posts)} new posts sent & saved{scout_summary}")
        else:
            print("⚠️ No new posts found, skipping commit")
            sys.exit(0)  # Exit cleanly to prevent unnecessary commit
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
