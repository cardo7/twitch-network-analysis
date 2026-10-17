# Data collection

## Data source

The network was built from scratch using the official **Twitch Helix API**, authenticated with OAuth2 *client credentials*. No pre-built network dataset was used.

## Nodes and edges

- **Node:** a Twitch streamer (single node type), identified by its Twitch user ID.
- **Edge:** two streamers are linked if they are members of the same **Twitch Team**. Teams are groups that streamers create to work under a common banner, so co-membership is a good sign of a social or professional relationship.

## Crawling strategy (`01_crawl_teams.py`)

We used a **Breadth-First Search** starting from 6 popular Italian streamers (`tumblurr`, `pow3r`, `grenbaud`, `homyatol`, `zanesecondo`, `ilrossopiace`):

1. pop a streamer from the queue and fetch its profile (`/helix/users`);
2. fetch the Teams it belongs to (`/helix/teams/channel`);
3. for each Team, fetch its members (`/helix/teams`) and add an edge *streamer → member*;
4. append unvisited members to the queue.

The crawl stops once **10,000 unique streamers** have been discovered. Duplicate edges and self-loops are removed, and only edges whose endpoints are both in the node list are kept. Members discovered in the last expansion step are included as well, so the final network has 10,356 nodes.

> **Note on edge direction.** The direction *source → target* only reflects the order in which the crawler discovered the two streamers, not an asymmetric relation. Team co-membership is symmetric, so the analysis is carried out on the undirected graph, as required by the project guidelines.

## Node attributes

| Script | Endpoint | Attribute | Notes |
|---|---|---|---|
| `01_crawl_teams.py` | `/helix/users` | `Label` | display name |
| `02_enrich_nodes.py` | `/helix/users` | `Broadcaster_Type` | partner / affiliate / normal; up to 100 IDs per request |
| `03_fetch_followers.py` | `/helix/channels/followers` | `Total_Followers` | one request per node, checkpoint every 250 nodes |

`Total_Views` was also collected in step 2 but then dropped, because Twitch no longer updates the view counter.

## Rate limiting

Twitch allows about **800 requests per minute**. Fetching followers alone takes over 10,000 requests, so every script checks for HTTP `429 Too Many Requests`, reads the `Retry-After` header and waits for the required time before retrying.

## Running the scripts

Credentials are read from environment variables. Copy `.env.example` (in the repository root) to `.env` and fill it in, or set the variables directly:

```powershell
# Windows PowerShell
$env:TWITCH_CLIENT_ID="..."; $env:TWITCH_CLIENT_SECRET="..."
```

```bash
# macOS / Linux
export TWITCH_CLIENT_ID=... TWITCH_CLIENT_SECRET=...
```

Then run the three scripts in order. Intermediate and final files are written to `data/`.

## Final data

The final node and edge lists are in `data/` as plain CSV files, which the notebooks read directly. As required by the guidelines, the final data are also provided compressed in [`data/twitch_network.zip`](data/twitch_network.zip), together with the GEXF versions of the graph:

| File | Content |
|---|---|
| `twitch_nodes.csv` | `ID, Label, Broadcaster_Type, Total_Followers` (10,356 rows) |
| `twitch_edgelist.csv` | `Source, Target, Type, Weight` (17,433 directed edges; 14,192 once made undirected) |
| `twitch_graph_directed.gexf` | directed graph with node attributes (for Gephi) |
| `twitch_graph_undirected.gexf` | undirected graph with node attributes (for Gephi) |
