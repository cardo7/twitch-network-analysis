# Twitch Network Analysis

Final project for the **Social Network Analysis** course (University of Pisa, A.Y. 2025/2026).

**Authors:** Riccardo Ranieri · Giambattista Bernardo · Pietro Gagliardi

We crawled a network of **10,356 Italian Twitch streamers** from the official Twitch API, where two streamers are linked when they belong to the same **Twitch Team**. The project studies how Teams shape the structure of the platform and whether they help small creators grow.

📄 **Full report:** [`report/Twitch_network_analysis_report.pdf`](report/Twitch_network_analysis_report.pdf)

---

## Repository structure

```
.
├── data_collection/                  # Part 1 – Data collection
│   ├── README.md                     # crawling strategy and choices
│   ├── 01_crawl_teams.py             # BFS crawler over Twitch Teams
│   ├── 02_enrich_nodes.py            # broadcaster type (batched API calls)
│   ├── 03_fetch_followers.py         # follower count (one call per node)
│   └── data/
│       ├── twitch_nodes.csv          # node list with attributes
│       ├── twitch_edgelist.csv       # edge list
│       └── twitch_network.zip        # compressed final data (CSV + GEXF)
├── network_analysis/                 # Part 2 – Network characterization
│   ├── 00_directed_exploration.ipynb # first look at the directed graph
│   └── 01_network_analysis.ipynb     # undirected analysis + ER / BA comparison
├── tasks/                            # Part 3 – Analytical tasks
│   ├── community_detection.ipynb     # Cluster 1 – Leiden, Infomap, ANGEL (CDlib)
│   ├── link_prediction.ipynb         # Cluster 1 – unsupervised link prediction
│   └── spreading_raids.ipynb         # Cluster 2 – custom NDlib model of Twitch raids
├── figures/                          # plots used in the report
│   └── interactive/                  # interactive graph (pyvis, open locally)
├── report/                           # final report (PDF)
├── requirements.txt
└── .env.example                      # template for Twitch API credentials
```

## The network

| | |
|---|---|
| **Source** | Twitch Helix API (OAuth2 client credentials) |
| **Nodes** | streamers (single node type) |
| **Edges** | Team co-membership |
| **Crawling** | BFS from 6 popular Italian streamers (`tumblurr`, `pow3r`, `grenbaud`, `homyatol`, `zanesecondo`, `ilrossopiace`) |
| **Node attributes** | `Label` (display name), `Broadcaster_Type` (partner / affiliate / normal), `Total_Followers` |
| **Size** | 10,356 nodes · 17,433 directed edges · 14,192 undirected edges |

Details on the crawling strategy, API limits and file formats are in [`data_collection/README.md`](data_collection/README.md).

## Main results

**Network characterization** – compared with Erdős–Rényi and Barabási–Albert graphs with the same number of nodes and average degree:

| | Real network | ER | BA |
|---|---:|---:|---:|
| Nodes | 10,356 | 10,356 | 10,356 |
| Edges | 14,192 | 14,285 | 14,098 |
| Avg. degree | 2.74 | 2.76 | 2.72 |
| Max degree | 6,680 | 12 | 237 |
| Density | 2.65 × 10⁻⁴ | 2.66 × 10⁻⁴ | 2.63 × 10⁻⁴ |
| Avg. clustering | 0.0244 | 0.0005 | 0.0018 |
| Giant component | 99.99% | 92.26% | 100% |
| Avg. path length | 3.11 | 9.03 | 5.96 |
| Power-law α | 1.52 | 2.25 | 2.70 |
| Degree assortativity | −0.42 | 0.00 | −0.05 |

The network is extremely sparse but almost fully connected, with a heavy-tailed degree distribution: most streamers have a single link, while a few hubs reach thousands of connections. The strongly negative assortativity shows that hubs mostly connect to low-degree streamers (star-like structure) rather than to each other.

**Community detection** (CDlib) – Leiden reaches the highest modularity (0.699); Infomap on the undirected graph agrees with it (0.694). Communities are validated against `Broadcaster_Type`: partner-dominated communities are also the ones with the highest average follower count.

**Link prediction** – 80/20 edge split with balanced negative sampling. Classical heuristics stay close to random, consistent with a star-like structure around hubs:

| Common Neighbors | Jaccard | Adamic-Adar | Preferential Attachment |
|---:|---:|---:|---:|
| 0.5349 | 0.4536 | 0.5353 | 0.4238 |

**Spreading (Twitch raids)** – a custom NDlib compartmental model (Susceptible → Infected, `EdgeStochastic` rule, p = 0.15) seeded with the top 1% and top 3% streamers by followers, averaged over 100 Monte Carlo runs of 20 hops. Raids reach many small creators at the first hop and then stall; a second wave appears only around hop 11, through rare bridging ties. A sensitivity analysis on p (0.05 / 0.15 / 0.30) shows that lower probabilities reach more small creators in the long run.

**Open question** – *Do Twitch Teams help smaller streamers grow, or do they reinforce already established channels?* Combining the results above, Teams act as "proximity multipliers": they strengthen existing clusters but do not open a path to visibility for the long tail of small creators. See section 6 of the report.

## How to reproduce

```bash
git clone https://github.com/cardo7/twitch_network_analysis.git
cd twitch_network_analysis
pip install -r requirements.txt
jupyter notebook
```

The notebooks read the CSV files in `data_collection/data/`. Run them from their own folder (the default in Jupyter).

**Re-crawling the data (optional).** Create an application on the [Twitch developer console](https://dev.twitch.tv/console), copy `.env.example` to `.env`, fill in your credentials, then run from the repository root:

```bash
python data_collection/01_crawl_teams.py
python data_collection/02_enrich_nodes.py
python data_collection/03_fetch_followers.py
```

A full crawl takes a while because of Twitch rate limits (about 800 requests per minute). The resulting network may differ from ours, since Teams change over time.
