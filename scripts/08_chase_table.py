"""Step 3.4 - Chase win probability (business question 10).
For every ball of every completed 20-over chase we record the situation (runs needed, balls left,
wickets in hand) and whether the chasing team went on to win. Situations are grouped into buckets;
win % = share of chases that won from that bucket. Each chase counts once per bucket."""
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
OUT = Path("data/analysis")
MIN_CHASES = 30

d = pd.read_csv("data/clean/deliveries.csv")
m = pd.read_csv("data/clean/matches.csv").merge(pd.read_csv(OUT / "match_flags.csv"), on="match_id")

full = m[m["is_full"]].copy()
c = d[(d["innings"] == 2) & d["match_id"].isin(full["match_id"]) & d["is_legal"]].copy()
c = c.merge(full[["match_id", "match_winner", "result_type"]], on="match_id")
c["won"] = np.where(c["result_type"] == "tie", 0.5, (c["match_winner"] == c["batting_team"]).astype(float))

# situation AFTER each legal ball, plus the starting situation of each chase
c["runs_needed"] = c["target_runs"] - c["team_runs_so_far"]
c["wkts_in_hand"] = 10 - c["team_wkts_so_far"]
start = (c.groupby("match_id").first().reset_index()
           .assign(runs_needed=lambda x: x["target_runs"], balls_left=120, wkts_in_hand=10))
states = pd.concat([start, c])[["match_id", "season", "runs_needed", "balls_left", "wkts_in_hand", "won", "target_runs"]]
states = states[(states["runs_needed"] > 0) & (states["balls_left"] > 0) & (states["wkts_in_hand"] > 0)]
states["period"] = np.where(states["season"] >= 2023, "2023-26", "2008-22")

# buckets
RUN_BINS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 1000]
BALL_BINS = [0, 6, 12, 18, 24, 30, 36, 48, 60, 72, 90, 120]
WKT_BINS = [0, 2, 4, 6, 8, 10]
def label(bins):
    out = [f"{a + 1}-{b}" for a, b in zip(bins[:-1], bins[1:])]
    if bins[-1] == 1000:
        out[-1] = f"{bins[-2] + 1}+"
    return out
states["runs_bucket"] = pd.cut(states["runs_needed"], RUN_BINS, labels=label(RUN_BINS)).astype(str)
states["balls_bucket"] = pd.cut(states["balls_left"], BALL_BINS, labels=label(BALL_BINS)).astype(str)
states["wkts_bucket"] = pd.cut(states["wkts_in_hand"], WKT_BINS, labels=label(WKT_BINS)).astype(str)
states["runs_lo"] = pd.cut(states["runs_needed"], RUN_BINS, labels=[a + 1 for a in RUN_BINS[:-1]]).astype(int)
states["balls_lo"] = pd.cut(states["balls_left"], BALL_BINS, labels=[a + 1 for a in BALL_BINS[:-1]]).astype(int)
states["wkts_lo"] = pd.cut(states["wkts_in_hand"], WKT_BINS, labels=[a + 1 for a in WKT_BINS[:-1]]).astype(int)

keys = ["runs_bucket", "balls_bucket", "wkts_bucket", "runs_lo", "balls_lo", "wkts_lo"]
once = states.drop_duplicates(keys + ["match_id"])          # each chase counts once per bucket

def table(df):
    t = df.groupby(keys).agg(chases=("match_id", "nunique"), win_pct=("won", "mean")).reset_index()
    t["win_pct"] = (t["win_pct"] * 100).round(1)
    t["enough_data"] = t["chases"] >= MIN_CHASES
    return t

overall = table(once).assign(period="All")
by_period = pd.concat([table(g).assign(period=p) for p, g in once.groupby("period")])
chase_table = pd.concat([overall, by_period], ignore_index=True)
chase_table.to_csv(OUT / "chase_win_table.csv", index=False)
print(f"Chases used: {states['match_id'].nunique()} | situations recorded: {len(states):,} | "
      f"buckets: {len(overall)} (with {MIN_CHASES}+ chases: {overall['enough_data'].sum()})")

def lookup(runs, balls, wkts, period="All"):
    lo = lambda v, bins: max(b + 1 for b in bins[:-1] if b < v)     # bucket a value falls into
    r = chase_table[(chase_table["period"] == period) & (chase_table["runs_lo"] == lo(runs, RUN_BINS))
                    & (chase_table["balls_lo"] == lo(balls, BALL_BINS)) & (chase_table["wkts_lo"] == lo(wkts, WKT_BINS))]
    if r.empty or not r["enough_data"].iloc[0]:
        return "too few"
    return f"{r['win_pct'].iloc[0]:.0f}% ({r['chases'].iloc[0]})"

print("\n=== EXAMPLE SITUATIONS: win % (number of chases) ===")
scenarios = [(12, 6, 3), (20, 12, 5), (30, 18, 5), (30, 18, 2), (50, 30, 7), (50, 30, 3),
             (70, 36, 6), (90, 60, 8), (100, 60, 5), (120, 72, 8), (150, 90, 9)]
rows = [{"runs_needed": r_, "balls_left": b_, "wkts_in_hand": w_, "req_rate": round(r_ / b_ * 6, 1),
         "all": lookup(r_, b_, w_), "2008-22": lookup(r_, b_, w_, "2008-22"), "2023-26": lookup(r_, b_, w_, "2023-26")}
        for r_, b_, w_ in scenarios]
print(pd.DataFrame(rows).to_string(index=False))

print("\n=== WIN % BY TARGET SIZE (start of the chase) ===")
st = states[states["balls_left"] == 120].copy()
st["target_band"] = pd.cut(st["target_runs"], [0, 140, 160, 180, 200, 220, 400],
                           labels=["<=140", "141-160", "161-180", "181-200", "201-220", "221+"])
tb = st.pivot_table(index="target_band", columns="period", values="won", aggfunc=["mean", "count"], observed=False)
tb.columns = [f"{a}_{b}" for a, b in tb.columns]
tb = tb.reindex(["<=140", "141-160", "161-180", "181-200", "201-220", "221+"])
for p_ in ["2008-22", "2023-26"]:
    tb[f"mean_{p_}"] = (tb[f"mean_{p_}"] * 100).round(1)
print(tb.rename(columns=lambda x: x.replace("mean_", "win%_").replace("count_", "chases_")).to_string())

print("\n=== HAS THE SAME SITUATION BECOME MORE WINNABLE SINCE 2023? ===")
cmp = by_period.pivot_table(index=keys, columns="period", values=["win_pct", "chases"])
cmp.columns = [f"{a}_{b}" for a, b in cmp.columns]
cmp = cmp[(cmp["chases_2008-22"] >= 20) & (cmp["chases_2023-26"] >= 20)].copy()
cmp["diff"] = cmp["win_pct_2023-26"] - cmp["win_pct_2008-22"]
w = cmp[["chases_2008-22", "chases_2023-26"]].min(axis=1)
if cmp.empty:
    raise SystemExit("Not enough chases to compare periods")
print(f"Buckets with 20+ chases in both periods: {len(cmp)} | more winnable now: {(cmp['diff'] > 0).sum()} | "
      f"weighted average change: {np.average(cmp['diff'], weights=w):+.1f} percentage points")
late = cmp.reset_index()
late = late[late["balls_lo"] <= 36]
print(f"  Last 6 overs only: {len(late)} buckets, weighted change "
      f"{np.average(late['diff'], weights=late[['chases_2008-22', 'chases_2023-26']].min(axis=1)):+.1f} points")

print("\nSaved: data/analysis/chase_win_table.csv")