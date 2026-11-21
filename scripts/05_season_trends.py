"""Step 3.1 - How the IPL has changed season by season (business questions 1 and 2)."""
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 220)
OUT = Path("data/analysis")
OUT.mkdir(parents=True, exist_ok=True)

d = pd.read_csv("data/clean/deliveries.csv")
m = pd.read_csv("data/clean/matches.csv")

# ---------- full matches only: a result, no D/L, not shortened by rain (target over 20 overs)
t_overs = d[d["innings"] == 2].groupby("match_id")["target_overs"].first()
m["target_overs"] = m["match_id"].map(t_overs)
m["is_full"] = (m["result_type"] != "no result") & ~m["is_dl"] & m["target_overs"].fillna(20).eq(20)
full_ids = set(m.loc[m["is_full"], "match_id"])
print(f"Full matches used: {len(full_ids)} of {len(m)} "
      f"(dropped: {(m['result_type'] == 'no result').sum()} no result, {m['is_dl'].sum()} D/L, "
      f"{(~m['is_full']).sum() - (m['result_type'] == 'no result').sum() - m['is_dl'].sum()} other shortened)")
f = d[d["match_id"].isin(full_ids) & d["innings"].isin([1, 2])]

# ---------- innings-level totals
inn = (f.groupby(["match_id", "innings", "season", "batting_team"])
         .agg(runs=("runs_total", "sum"), wkts=("is_team_wicket", "sum"), legal=("is_legal", "sum"))
         .reset_index())
first = inn[inn["innings"] == 1]

# ---------- season table
season = pd.DataFrame({
    "matches": first.groupby("season")["match_id"].nunique(),
    "avg_1st_inn": first.groupby("season")["runs"].mean().round(1),
    "pct_200_plus": (first.groupby("season")["runs"].apply(lambda s: (s >= 200).mean()) * 100).round(1),
    "run_rate": (f.groupby("season")["runs_total"].sum() / f.groupby("season")["is_legal"].sum() * 6).round(2),
    "balls_per_wkt": (f.groupby("season")["is_legal"].sum() / f.groupby("season")["is_team_wicket"].sum()).round(1),
    "boundary_pct": ((f["is_four"] | f["is_six"]).groupby(f["season"]).sum()
                     / f.groupby("season")["is_ball_faced"].sum() * 100).round(1),
    "sixes_per_match": (f.groupby("season")["is_six"].sum() / first.groupby("season")["match_id"].nunique()).round(1),
})
phase_rr = (f.groupby(["season", "phase"])["runs_total"].sum() / f.groupby(["season", "phase"])["is_legal"].sum() * 6)
phase_rr = phase_rr.unstack()[["Powerplay", "Middle", "Death"]].round(2).add_prefix("rr_")
season = season.join(phase_rr)

# ---------- bat first vs chase, and the toss (full matches with a winner)
mm = m[m["is_full"]].copy()
bat_first = d[d["innings"] == 1].groupby("match_id")["batting_team"].first()
mm["bat_first_team"] = mm["match_id"].map(bat_first)
mm["chase_win"] = np.where(mm["result_type"] == "tie", 0.5,
                           (mm["match_winner"] != mm["bat_first_team"]).astype(float))
season["chase_win_pct"] = (mm.groupby("season")["chase_win"].mean() * 100).round(1)
season["toss_bowl_pct"] = (mm.groupby("season")["toss_decision"].apply(lambda s: (s == "field").mean()) * 100).round(1)
season["toss_winner_win_pct"] = (mm.groupby("season")["toss_winner_won"].mean() * 100).round(1)

print("\n=== SEASON BY SEASON (full matches) ===")
print(season.to_string())

print("\n=== OVERALL ===")
print(f"Chasing team won {mm['chase_win'].mean() * 100:.1f}% | toss winner won {mm['toss_winner_won'].mean() * 100:.1f}% "
      f"| toss winners chose to bowl {(mm['toss_decision'] == 'field').mean() * 100:.1f}%")
for dec, g in mm.groupby("toss_decision"):
    print(f"  Toss winner chose to {dec}: won {g['toss_winner_won'].mean() * 100:.1f}% of {len(g)} matches")

season.to_csv(OUT / "season_trends.csv")
inn.to_csv(OUT / "innings_totals.csv", index=False)
m[["match_id", "is_full", "target_overs"]].to_csv(OUT / "match_flags.csv", index=False)
print("\nSaved: data/analysis/season_trends.csv, innings_totals.csv, match_flags.csv")