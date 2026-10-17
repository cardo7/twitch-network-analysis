"""
Step 2 - Node enrichment: broadcaster type and view count.

For every node collected by 01_crawl_teams.py, queries the Twitch
`/helix/users` endpoint in batches of 100 IDs per request and adds:
    Total_Views        (later dropped: Twitch no longer updates view_count)
    Broadcaster_Type   partner / affiliate / normal

Input:  data/twitch_nodes_raw.csv
Output: data/twitch_nodes_enriched.csv
"""

import os
import time
from pathlib import Path

import pandas as pd
import requests

try:  # optional: load credentials from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

DATA_DIR = Path(__file__).resolve().parent / "data"

# --- STEP 1: OAUTH2 AUTHENTICATION ---
auth_url = "https://id.twitch.tv/oauth2/token"
auth_params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
auth_response = requests.post(auth_url, data=auth_params)
ACCESS_TOKEN = auth_response.json()["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- STEP 2: LOAD CRAWLED NODES ---
df_nodes = pd.read_csv(DATA_DIR / "twitch_nodes_raw.csv")
print(f"Loaded {len(df_nodes)} nodes.")

node_ids = df_nodes["ID"].tolist()
real_views = {}
broadcaster_types = {}

# --- STEP 3: BATCH REQUESTS (100 IDs per call) ---
batch_size = 100
for i in range(0, len(node_ids), batch_size):
    batch = node_ids[i:i + batch_size]

    # id=123&id=456&id=789...
    id_params = "&".join([f"id={node_id}" for node_id in batch])
    url = f"https://api.twitch.tv/helix/users?{id_params}"

    res = requests.get(url, headers=headers)

    if res.status_code == 429:
        wait_time = int(res.headers.get("Retry-After", 5))
        print(f"Rate limit reached. Sleeping {wait_time} s...")
        time.sleep(wait_time)
        res = requests.get(url, headers=headers)

    if res.status_code == 200:
        data = res.json().get("data", [])
        for user in data:
            u_id = int(user["id"])
            real_views[u_id] = int(user["view_count"])
            b_type = user["broadcaster_type"]
            broadcaster_types[u_id] = b_type if b_type != "" else "normal"
    else:
        print(f"Error in batch starting at index {i}: {res.status_code}")

    if (i // batch_size) % 10 == 0 and i > 0:
        print(f"Updated {i}/{len(node_ids)} nodes...")

# --- STEP 4: MAP AND SAVE ---
df_nodes["Total_Views"] = df_nodes["ID"].map(real_views).fillna(0).astype(int)
df_nodes["Broadcaster_Type"] = df_nodes["ID"].map(broadcaster_types).fillna("unknown")

output_path = DATA_DIR / "twitch_nodes_enriched.csv"
df_nodes.to_csv(output_path, index=False)
print(f"Saved: {output_path}")
