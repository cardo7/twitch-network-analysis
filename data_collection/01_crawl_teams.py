"""
Step 1 - BFS crawler over Twitch Teams.

Starting from a few popular Italian streamers (seeds), the crawler queries the
Twitch Helix API for the teams each streamer belongs to and links the streamer
to every other member of those teams. Newly discovered streamers are appended
to the BFS queue until TARGET_NODES unique streamers have been collected.

Twitch allows ~800 requests/minute: on HTTP 429 the script reads the
`Retry-After` header and waits before retrying.

Output (in data/):
    twitch_nodes_raw.csv     ID, Label, Total_Views
    twitch_edgelist.csv      Source, Target, Type, Weight

Credentials are read from the TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET
environment variables (or from a .env file, see .env.example).
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
DATA_DIR.mkdir(exist_ok=True)

# --- AUTHENTICATION (OAuth2 client credentials) ---
auth_url = "https://id.twitch.tv/oauth2/token"
auth_params = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
auth_response = requests.post(auth_url, data=auth_params)
ACCESS_TOKEN = auth_response.json()["access_token"]

headers = {
    "Client-Id": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# --- CRAWLER SETTINGS ---
TARGET_NODES = 10000  # target number of unique nodes
# Popular Italian streamers used as BFS seeds
queue = ["tumblurr", "pow3r", "grenbaud", "homyatol", "zanesecondo", "ilrossopiace"]
visited_logins = set()
discovered_nodes = {}  # ID -> {ID, Label, Total_Views}
edges_set = set()      # set of (Source, Target) tuples, no duplicates

print(f"Starting Twitch crawler. Target: {TARGET_NODES} nodes.")


def safe_request(url):
    """GET request that automatically handles Twitch rate limiting."""
    while True:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 429:
            wait_time = int(res.headers.get("Retry-After", 5))
            print(f"Rate limit reached. Sleeping {wait_time} s...")
            time.sleep(wait_time)
        else:
            return None


# --- BFS EXPLORATION ---
while queue and len(discovered_nodes) < TARGET_NODES:
    current_login = queue.pop(0)
    if current_login in visited_logins:
        continue
    visited_logins.add(current_login)

    # 1. Info about the current node
    user_data = safe_request(f"https://api.twitch.tv/helix/users?login={current_login}")
    if not user_data or not user_data.get("data"):
        continue

    user_info = user_data["data"][0]
    source_id = user_info["id"]
    source_label = user_info["display_name"]
    view_count = int(user_info["view_count"])

    if source_id not in discovered_nodes:
        discovered_nodes[source_id] = {"ID": source_id, "Label": source_label, "Total_Views": view_count}

    if len(discovered_nodes) % 100 == 0:
        print(f"Nodes: {len(discovered_nodes)}/{TARGET_NODES} | Edges: {len(edges_set)}")

    # 2. Expansion: neighbours are the members of the same Teams
    teams_data = safe_request(f"https://api.twitch.tv/helix/teams/channel?broadcaster_id={source_id}")
    if teams_data and "data" in teams_data:
        for team in teams_data["data"]:
            team_id = team["id"]

            team_details = safe_request(f"https://api.twitch.tv/helix/teams?id={team_id}")
            if team_details and "data" in team_details and len(team_details["data"]) > 0:
                users_in_team = team_details["data"][0]["users"]

                for member in users_in_team:
                    target_id = member["user_id"]
                    target_login = member["user_login"]
                    target_name = member["user_name"]

                    if target_login not in visited_logins and target_login not in queue:
                        queue.append(target_login)

                    # Edge source -> team member (no self-loops)
                    if target_id != source_id:
                        edges_set.add((source_id, target_id))
                        if target_id not in discovered_nodes:
                            discovered_nodes[target_id] = {"ID": target_id, "Label": target_name, "Total_Views": 0}

# --- SAVE ---
print("\nTarget reached or queue exhausted. Saving...")

df_nodes = pd.DataFrame(discovered_nodes.values())
df_edges = pd.DataFrame(list(edges_set), columns=["Source", "Target"])
df_edges["Type"] = "Directed"
df_edges["Weight"] = 1

# Keep only edges whose endpoints are both in the node list
df_edges = df_edges[df_edges["Source"].isin(df_nodes["ID"]) & df_edges["Target"].isin(df_nodes["ID"])]

df_nodes.to_csv(DATA_DIR / "twitch_nodes_raw.csv", index=False)
df_edges.to_csv(DATA_DIR / "twitch_edgelist.csv", index=False)

print(f"Nodes exported: {len(df_nodes)}")
print(f"Edges exported: {len(df_edges)}")
