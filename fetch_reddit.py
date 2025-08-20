import os
import time
import requests
import praw

# Load secrets
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Subreddits to scan
SUBREDDITS = [
    "HungryArtists", "commissions", "artcommission", "artcommissions",
    "artisthirecommission", "announcements", "Artcommission", "Artistsforhire",
    "artstore", "ComicBookCollabs", "commissionart", "Commissions_",
    "Commissions_rh", "DesignJobs", "dndcommissions", "FurryCommissions",
    "FursCommissions", "hireanartist", "HungryArtistsFed", "starvingartist",
    "DrawForMe", "CatsWithDogs", "starvingartists"
]

# Keywords to look for
KEYWORDS = [
    "[HIRING]", "[Hiring]", "[hiring]",
    "[looking for artist]", "[Looking for artist ]",
    "[Looking for Artist ]", "[Looking For Artist ]",
    "[LOOKING FOR ARTIST]", "[LOOKING FOR]",
    "[looking for]"
]

# File to track sent posts
SENT_FILE = "sent_posts.txt"

# Load already sent posts (if file exists)
if os.path.exists(SENT_FILE):
    with open(SENT_FILE, "r") as f:
        sent_posts = set(line.strip() for line in f if line.strip())
else:
    sent_posts = set()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    response = requests.post(url, data=payload)
    response.raise_for_status()

# Loop through subreddits
for sub in SUBREDDITS:
    try:
        subreddit = reddit.subreddit(sub)
        for submission in subreddit.new(limit=10):  # check last 10 posts
            if submission.id in sent_posts:
                continue

            title = submission.title
            if any(keyword in title for keyword in KEYWORDS):
                msg = (
                    f"📢 New Post Found!\n\n"
                    f"Subreddit: {sub}\n"
                    f"Title: {title}\n"
                    f"Author: {submission.author}\n"
                    f"Posted: {int(time.time() - submission.created_utc) // 60}m ago\n"
                    f"URL: https://www.reddit.com{submission.permalink}"
                )

                send_telegram_message(msg)

                # Save post ID
                with open(SENT_FILE, "a") as f:
                    f.write(submission.id + "\n")
                sent_posts.add(submission.id)

    except Exception as e:
        print(f"⚠️ Error fetching {sub}: {e}")
