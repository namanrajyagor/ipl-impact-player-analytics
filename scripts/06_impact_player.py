"""Step 3.2 - Did the Impact Player rule (from 2023) change the game? Business questions 4-7.
Before = 2018-2022, After = 2023-2026, full matches only. Three checks: trend, venue, mechanism."""
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
OUT = Path("data/analysis")

d = pd.read_csv("data/clean/deliveries.csv")
m = pd.read_csv("data/clean/matches.csv").merge(pd.read_csv(OUT / "match_flags.csv"), on="match_id")
r = pd.read_csv("data/clean/replacements.csv")
inn = pd.read_csv(OUT / "innings_totals.csv")          # full matches only (from step 3.1)
season = pd.read_csv(OUT / "season_trends.csv", index_col="season")

def period(y):
    return np.select([y.between(2018, 2022), y >= 2023], ["Before (2018-22)", "After (2023-26)"], "Earlier")

full_ids = set(m.loc[m["is_full"], "match_id"])
f = d[d["match_id"].isin(full_ids) & d["innings"].isin([1, 2])].copy()
f["period"] = period(f["season"])
inn["period"] = period(inn["season"])
first = inn[inn["innings"] == 1]
ba = ["Before (2018-22)", "After (2023-26)"]

# ================================================================ A. before vs after
print("=== A. BEFORE vs AFTER (full matches) ===")
g = f[f["period"].isin(ba)].groupby("period")
summary = pd.DataFrame({
    "matches": first[first["period"].isin(ba)].groupby("period")["match_id"].nunique(),
    "avg_1st_inn": first.groupby("period")["runs"].mean().round(1),
    "pct_200_plus": (first.groupby("period")["runs"].apply(lambda s: (s >= 200).mean()) * 100).round(1),
    "run_rate": (g["runs_total"].sum() / g["is_legal"].sum() * 6).round(2),
    "balls_per_wkt": (g["is_legal"].sum() / g["is_team_wicket"].sum()).round(1),
    "dot_pct": (g["is_dot"].sum() / g["is_ball_faced"].sum() * 100).round(1),
    "boundary_pct": ((f["is_four"] | f["is_six"]).groupby(f["period"]).sum() / g["is_ball_faced"].sum() * 100).round(1),
}).loc[ba]
ph = (f[f["period"].isin(ba)].groupby(["period", "phase"])
        .apply(lambda x: x["runs_total"].sum() / x["is_legal"].sum() * 6, include_groups=False)
        .unstack()[["Powerplay", "Middle", "Death"]].round(2).add_prefix("rr_"))
summary = summary.join(ph)
summary.loc["Change"] = summary.loc[ba[1]] - summary.loc[ba[0]]
print(summary.T.to_string())

# chasing big targets
chase = inn[inn["innings"] == 2].merge(first[["match_id", "runs"]].rename(columns={"runs": "first_runs"}), on="match_id")
chase = chase.merge(m[["match_id", "match_winner", "result_type"]], on="match_id")
chase["won"] = np.where(chase["result_type"] == "tie", 0.5, (chase["match_winner"] == chase["batting_team"]).astype(float))
chase["target"] = chase["first_runs"] + 1
print("\nChasing 190+ targets:")
for p_ in ba:
    c = chase[(chase["period"] == p_) & (chase["target"] >= 190)]
    print(f"  {p_}: {len(c)} chases, won {c['won'].mean() * 100:.1f}%")
print("Chasing overall: " + " | ".join(f"{p_}: {chase[chase['period'] == p_]['won'].mean() * 100:.1f}%" for p_ in ba))

# ================================================================ B. trend check
print("\n=== B. TREND CHECK: was scoring already rising? ===")
trend_rows = []
for start in [2008, 2018]:
    base = season.loc[start:2022, "avg_1st_inn"]
    slope, intercept = np.polyfit(base.index, base.values, 1)
    for y in range(2023, 2027):
        pred = slope * y + intercept
        trend_rows.append({"baseline": f"{start}-2022", "season": y, "actual": season.loc[y, "avg_1st_inn"],
                           "trend_prediction": round(pred, 1),
                           "above_trend": round(season.loc[y, "avg_1st_inn"] - pred, 1)})
    print(f"Trend {start}-2022: {slope:+.2f} runs per season")
trend = pd.DataFrame(trend_rows)
print(trend.to_string(index=False))
for b_, t in trend.groupby("baseline"):
    print(f"  Baseline {b_}: actual is on average {t['above_trend'].mean():+.1f} runs above the trend line in 2023-26")

# ================================================================ C. venue check
print("\n=== C. VENUE CHECK: same grounds only (India) ===")
fv = first.merge(m[["match_id", "venue", "country"]], on="match_id")
fv = fv[fv["period"].isin(ba) & (fv["country"] == "India")]
vt = fv.pivot_table(index="venue", columns="period", values="runs", aggfunc=["mean", "count"])
vt.columns = [f"{a}_{b}" for a, b in vt.columns]
common = vt[(vt[f"count_{ba[0]}"] >= 5) & (vt[f"count_{ba[1]}"] >= 5)].copy()
common["change"] = common[f"mean_{ba[1]}"] - common[f"mean_{ba[0]}"]
common = common.round(1).sort_values("change", ascending=False)
print(common[[f"mean_{ba[0]}", f"mean_{ba[1]}", "change", f"count_{ba[0]}", f"count_{ba[1]}"]].to_string())
w = common[[f"count_{ba[0]}", f"count_{ba[1]}"]].min(axis=1)
print(f"Grounds compared: {len(common)} | grounds where scores rose: {(common['change'] > 0).sum()} | "
      f"weighted average change: {np.average(common['change'], weights=w):+.1f} runs")

# ================================================================ D. mechanism check
print("\n=== D. MECHANISM CHECK: is the extra batter being used? ===")
fb = f[f["period"].isin(ba)].copy()
fb["inn_key"] = fb["match_id"] * 10 + fb["innings"]
fb["tail_ball"] = fb["is_ball_faced"] & (fb["batting_position"] >= 8)   # balls FACED by No. 8+ (wides excluded, like the total)
per_inn = fb.groupby(["period", "match_id", "innings"]).agg(
    balls=("is_ball_faced", "sum"),
    tail_balls=("tail_ball", "sum"),
    max_pos=("batting_position", "max"))
mech = per_inn.groupby("period").agg(
    tail_share_pct=("tail_balls", lambda s: s.sum()),
    balls=("balls", "sum"),
    no8_batted_pct=("max_pos", lambda s: (s >= 8).mean() * 100))
mech["tail_share_pct"] = (mech["tail_share_pct"] / mech["balls"] * 100).round(2)
top = fb[fb["batting_position"] <= 3].groupby("period").agg(runs=("runs_batter", "sum"), balls=("is_ball_faced", "sum"))
pp = fb[fb["phase"] == "Powerplay"].groupby("period").agg(runs=("runs_batter", "sum"), balls=("is_ball_faced", "sum"),
                                                          wk=("is_team_wicket", "sum"), inns=("inn_key", "nunique"))
mech["top3_strike_rate"] = (top["runs"] / top["balls"] * 100).round(1)
mech["pp_strike_rate"] = (pp["runs"] / pp["balls"] * 100).round(1)
mech["pp_wkts_per_innings"] = (pp["wk"] / pp["inns"]).round(2)
mech["no8_batted_pct"] = mech["no8_batted_pct"].round(1)
print(mech.drop(columns="balls").loc[ba].T.to_string())

# who came in as the Impact Player: a batter or a bowler?
ip = r[r["reason"] == "impact_player"].copy()
bat_in = d.groupby(["match_id", "batter"])["is_ball_faced"].sum().rename("balls_faced").reset_index()
bowl_in = d.groupby(["match_id", "bowler"])["is_legal"].sum().rename("balls_bowled").reset_index()
ip = (ip.merge(bat_in.rename(columns={"batter": "player_in"}), on=["match_id", "player_in"], how="left")
        .merge(bowl_in.rename(columns={"bowler": "player_in"}), on=["match_id", "player_in"], how="left")
        .fillna({"balls_faced": 0, "balls_bowled": 0}))
ip["role_in_match"] = np.select(
    [(ip["balls_faced"] > 0) & (ip["balls_bowled"] > 0), ip["balls_faced"] > 0, ip["balls_bowled"] > 0],
    ["Batted and bowled", "Batted only", "Bowled only"], "Neither")
print("\nWhat the Impact Player did in the match:")
print((ip["role_in_match"].value_counts(normalize=True) * 100).round(1).to_string())

# ================================================================ save for Power BI
summary.to_csv(OUT / "impact_summary.csv")
trend.to_csv(OUT / "impact_trend_check.csv", index=False)
common.to_csv(OUT / "impact_venue_check.csv")
mech.to_csv(OUT / "impact_mechanism.csv")
ip.to_csv(OUT / "impact_players_used.csv", index=False)
print("\nSaved: impact_summary, impact_trend_check, impact_venue_check, impact_mechanism, impact_players_used (.csv)")