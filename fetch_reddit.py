import requests
import os
import time

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    response = requests.post(url, data=data)
    response.raise_for_status()

def fetch_reddit_posts(subreddit="HungryArtists", limit=5, retries=3):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"

    user_agents = [
        "Mozilla/5.0 (compatible; MyRedditBot/1.0; +https://github.com/yourusername)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    ]

    for attempt in range(retries):
        headers = {"User-Agent": user_agents[attempt % len(user_agents)]}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                time.sleep(2)  # wait before retry
                continue  # try again with next user-agent
            else:
                raise e
    raise Exception("Failed to fetch subreddit after multiple retries (403 Blocked).")

def main():
    subreddit = "HungryArtists"
    try:
        data = fetch_reddit_posts(subreddit)
        posts = data["data"]["children"]
        if not posts:
            send_message(f"No posts found in r/{subreddit}")
            return

        for post in posts:
            title = post["data"]["title"]
            url = "https://reddit.com" + post["data"]["permalink"]
            message = f"📌 {title}\n{url}"
            send_message(message)

    except Exception as e:
        send_message(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
