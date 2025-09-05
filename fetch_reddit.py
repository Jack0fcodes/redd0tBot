import os
import requests

# Load secrets
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
USER_AGENT = os.getenv("REDDIT_USER_AGENT")

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
def fetch_posts(subreddit, limit=5):
    token = get_reddit_token()
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    url = f"https://oauth.reddit.com/r/{subreddit}/new?limit={limit}"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()["data"]["children"]

# Load already saved IDs
def load_saved_ids(filename="post_ids.txt"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

# Save new IDs
def save_new_ids(new_ids, filename="post_ids.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        for pid in new_ids:
            f.write(pid + "\n")

if __name__ == "__main__":
    try:
        subreddits = ["HungryArtists", "commissions", "artcommission"]
        limit = 5  

        saved_ids = load_saved_ids()
        new_ids = set()
        new_posts = []

        for subreddit in subreddits:
            posts = fetch_posts(subreddit, limit=limit)
            for post in posts:
                data = post["data"]
                post_id = data["id"]

                # Skip if already saved
                if post_id in saved_ids:
                    continue

                title = data.get("title", "")
                link = "https://reddit.com" + data.get("permalink", "")
                message = f"📌 [{subreddit}] {title}\n{link}\n\n"

                new_posts.append(message)
                new_ids.add(post_id)

        if new_posts:
            with open("post_reddit.txt", "w", encoding="utf-8") as f:  # overwrite with fresh results
                f.writelines(new_posts)

            save_new_ids(new_ids)

            print(f"✅ Saved {len(new_posts)} new posts to post_reddit.txt")
        else:
            print("⚠️ No new posts found")
    except Exception as e:
        print(f"❌ Error: {e}")
