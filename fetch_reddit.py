import requests

# Hardcoded for quick test
TG_TOKEN = "7512011024:AAF-Zpx5cerWpuz8wvwP08yOSKvjfI905tI"
TG_CHAT_ID = "6231406396"

# Example: top 5 posts from r/worldnews
url = "https://www.reddit.com/r/worldnews/top.json?limit=5&t=day"
headers = {"User-Agent": "github-actions-script/0.1"}
response = requests.get(url, headers=headers)
data = response.json()

posts = []
for post in data["data"]["children"]:
    title = post["data"]["title"]
    link = "https://reddit.com" + post["data"]["permalink"]
    posts.append(f"• {title}\n{link}")

message = "\n\n".join(posts)

# Send to Telegram
send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
payload = {"chat_id": TG_CHAT_ID, "text": message}
r = requests.post(send_url, data=payload)

print("✅ Sent to Telegram!", r.text)
