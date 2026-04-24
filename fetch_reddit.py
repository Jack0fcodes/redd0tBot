import os
import re
import json
import requests
import csv
import sys
from datetime import datetime, timezone

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCOUT_API_URL = os.getenv("SCOUT_API_URL")
SCOUT_API_KEY = os.getenv("SCOUT_API_KEY")

CSV_FILE = "posts_reddit.csv"
LEADS_JSON_FILE = "leads.json"
LEADS_JSON_MAX = 200  # keep the file bounded for the iOS app to fetch

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

# Build the structured lead payload shared by Scout and leads.json
def build_lead(subreddit, post):
    data = post["data"]
    title = data.get("title", "")
    body = data.get("selftext", "")
    full_text = f"{title}\n\n{body}".strip() if body else title
    budget = extract_budget(f"{title} {body}")
    quality = classify_quality(f"{title} {body}", budget)
    created_utc = data.get("created_utc")
    created_at = (
        datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        if created_utc is not None
        else datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    )
    return {
        "post_id": data.get("id"),
        "platform": "Reddit",
        "source": f"r/{subreddit}",
        "author": f"u/{data.get('author', 'unknown')}",
        "title": title,
        "content": full_text,
        "url": "https://reddit.com" + data["permalink"],
        "quality": quality,
        "budget": budget,
        "created_at": created_at,
    }

# Send lead to Scout app
def send_to_scout(lead):
    if not SCOUT_API_URL:
        return
    headers = {"Content-Type": "application/json"}
    if SCOUT_API_KEY:
        headers["Authorization"] = f"Bearer {SCOUT_API_KEY}"
    res = requests.post(SCOUT_API_URL, json=lead, headers=headers, timeout=10)
    res.raise_for_status()

# Load existing leads.json if present; returns a list
def load_leads_json():
    if not os.path.isfile(LEADS_JSON_FILE):
        return []
    try:
        with open(LEADS_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []

# Prepend new leads, dedupe by post_id, cap, write back
def save_leads_json(new_leads):
    existing = load_leads_json()
    seen = set()
    merged = []
    for lead in new_leads + existing:
        pid = lead.get("post_id")
        if pid in seen:
            continue
        seen.add(pid)
        merged.append(lead)
    merged = merged[:LEADS_JSON_MAX]
    with open(LEADS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

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
        # Positive signals: a client is looking to hire an artist
        include_keywords = [
            "[hiring]",
            "hiring",
            "looking to hire",
            "want to hire",
            "need an artist",
            "need a artist",
            "need artist",
            "need an illustrator",
            "need illustrator",
            "need a designer",
            "need designer",
            "[paid]",
            "paying artist",
            "paying illustrator",
            "paying designer",
        ]
        # Negative signals: an artist is offering services (skip these)
        exclude_keywords = [
            "[for hire]",
            "[fh]",
            "for hire",
            "looking for work",
            "looking for a client",
            "looking for clients",
            "looking for commission",
            "looking for commissions",
            "open for commission",
            "open for commissions",
            "commissions open",
            "commission open",
            "taking commission",
            "taking commissions",
            "accepting commission",
            "accepting commissions",
            "portfolio in comment",
            "dm for portfolio",
            "dm for commission",
            "my portfolio",
            "my commission",
        ]
        limit = 5

        # Ensure leads.json exists on disk (so the iOS app and `git add` never miss it)
        if not os.path.isfile(LEADS_JSON_FILE):
            with open(LEADS_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

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

                has_include = any(k in content for k in include_keywords)
                has_exclude = any(k in content for k in exclude_keywords)

                # Client-hiring posts only: must have a positive signal,
                # must not contain an artist-offering signal, must be new
                if has_include and not has_exclude and pid not in existing_ids:
                    new_posts.append((subreddit, post))

        if new_posts:
            scout_sent = 0
            scout_failed = 0
            new_leads = []
            # Send to Telegram (and Scout), collect structured leads for leads.json
            for subreddit, post in new_posts:
                lead = build_lead(subreddit, post)
                new_leads.append(lead)

                message = (
                    f"Subreddit: {subreddit}\n"
                    f"Title: {lead['title']}\n"
                    f"Author: {lead['author']}\n"
                    f"URL: {lead['url']}"
                )
                send_to_telegram(message)

                if SCOUT_API_URL:
                    try:
                        send_to_scout(lead)
                        scout_sent += 1
                    except Exception as scout_err:
                        scout_failed += 1
                        print(f"⚠️ Scout send failed for {lead['post_id']}: {scout_err}")

            # Save archives
            save_to_csv(new_posts)
            save_leads_json(new_leads)

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
