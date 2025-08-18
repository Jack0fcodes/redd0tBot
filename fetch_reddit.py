import requests
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    response = requests.post(url, data=data)
    response.raise_for_status()

def fetch_reddit_posts(subreddit="HungryArtists", limit=5):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "GitHubActionBot/0.1"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

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
