import os
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_reddit_post():
    url = "https://www.reddit.com/r/Python/hot.json?limit=1"
    headers = {"User-Agent": "GitHubActionBot/0.1"}
    response = requests.get(url, headers=headers)
    data = response.json()
    if "data" in data:
        post = data["data"]["children"][0]["data"]
        title = post["title"]
        link = "https://reddit.com" + post["permalink"]
        return f"{title}\n{link}"
    return "No post found."

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=payload)
    return response.json()

if __name__ == "__main__":
    msg = get_reddit_post()
    result = send_to_telegram(msg)
    print(result)
