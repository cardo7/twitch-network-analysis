"""
Step 3 - Node enrichment: total followers.

The follower count is only available per channel
(`/helix/channels/followers?broadcaster_id=...`), so this step needs one
request per node (~10k requests). Progress is checkpointed every 250 nodes,
so the script can be stopped and restarted without losing work.

Input:  data/twitch_nodes_enriched.csv
Output: data/twitch_nodes.csv   (ID, Label, Broadcaster_Type, Total_Followers)
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

# --- STEP 2: LOAD ENRICHED NODES ---
input_path = DATA_DIR / "twitch_nodes_enriched.csv"
df_nodes = pd.read_csv(input_path)
print(f"Loaded {len(df_nodes)} nodes. Fetching followers...")

followers_dict = {}

# Resume from a previous (interrupted) run if a partial column exists
if "Total_Followers" in df_nodes.columns:
    followers_dict = df_nodes.set_index("ID")["Total_Followers"].to_dict()

# --- STEP 3: ONE REQUEST PER NODE ---
start_time = time.time()

for idx, row in df_nodes.iterrows():
    node_id = int(row["ID"])

    # Skip nodes already fetched in a previous run
    if node_id in followers_dict and followers_dict[node_id] > 0:
        continue

    url = f"https://api.twitch.tv/helix/channels/followers?broadcaster_id={node_id}"

    while True:
        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            followers_dict[node_id] = res.json().get("total", 0)
            break
        elif res.status_code == 429:
            wait_time = int(res.headers.get("Retry-After", 2))
            print(f"Rate limit reached. Sleeping {wait_time} s... (nodes done: {idx})")
            time.sleep(wait_time)
        else:
            print(f"Could not fetch ID {node_id}. Status: {res.status_code}")
            followers_dict[node_id] = 0
            break

    # Progress + checkpoint every 250 nodes
    if idx % 250 == 0 and idx > 0:
        elapsed = time.time() - start_time
        print(f"Synced {idx}/{len(df_nodes)} nodes... elapsed: {elapsed / 60:.1f} min")
        df_nodes["Total_Followers"] = df_nodes["ID"].map(followers_dict).fillna(0).astype(int)
        df_nodes.to_csv(input_path, index=False)

# --- STEP 4: FINAL MAPPING AND CLEANUP ---
df_nodes["Total_Followers"] = df_nodes["ID"].map(followers_dict).fillna(0).astype(int)

# view_count is deprecated by Twitch -> drop it
if "Total_Views" in df_nodes.columns:
    df_nodes = df_nodes.drop(columns=["Total_Views"])

output_path = DATA_DIR / "twitch_nodes.csv"
df_nodes.to_csv(output_path, index=False)
print(f"Done. Final node list saved to: {output_path}")
