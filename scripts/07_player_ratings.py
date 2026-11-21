"""Step 3.3 - Era-adjusted player ratings (business questions 8 and 9).
Batters: runs above average (RAA) = actual runs - what an average batter scores on the same number of
balls in the same season and phase. Bowlers: runs saved = expected runs conceded - actual."""
from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
OUT = Path("data/analysis")

d = pd.read_csv("data/clean/deliveries.csv")
names = pd.read_csv("data/clean/players.csv").set_index("player_id")["player"]

# ================================================================ batting
bf = d[d["is_ball_faced"]].copy()
avg_bat = bf.groupby(["season", "phase"])["runs_batter"].mean().rename("exp_run_per_ball")
bf = bf.join(avg_bat, on=["season", "phase"])
bf["is_out"] = bf["player_out_id"].eq(bf["batter_id"]) & bf["is_team_wicket"]

fact_batting = (bf.groupby(["batter_id", "season", "phase", "batting_team"])
                  .agg(balls=("is_ball_faced", "sum"), runs=("runs_batter", "sum"),
                       exp_runs=("exp_run_per_ball", "sum"), fours=("is_four", "sum"),
                       sixes=("is_six", "sum"), dots=("is_dot", "sum"), outs=("is_out", "sum"))
                  .reset_index())
fact_batting["exp_runs"] = fact_batting["exp_runs"].round(2)

def batting_table(df, keys):
    t = df.groupby(keys).agg(balls=("balls", "sum"), runs=("runs", "sum"), exp_runs=("exp_runs", "sum"),
                             outs=("outs", "sum")).reset_index()
    t["player"] = t["batter_id"].map(names)
    t["strike_rate"] = (t["runs"] / t["balls"] * 100).round(1)
    t["avg_sr_same_context"] = (t["exp_runs"] / t["balls"] * 100).round(1)
    t["raa"] = (t["runs"] - t["exp_runs"]).round(1)
    t["raa_per_100"] = (t["raa"] / t["balls"] * 100).round(1)
    return t

bat_all = batting_table(fact_batting, ["batter_id"])
bat_season = batting_table(fact_batting, ["batter_id", "season"])
cols = ["player", "balls", "runs", "strike_rate", "avg_sr_same_context", "raa", "raa_per_100"]

print("=== BATTERS: MOST RUNS ABOVE AVERAGE (all time) ===")
print(bat_all.nlargest(10, "raa")[cols].to_string(index=False))
print("\n=== BATTERS: BEST RAA PER 100 BALLS (min 500 balls) ===")
print(bat_all[bat_all["balls"] >= 500].nlargest(10, "raa_per_100")[cols].to_string(index=False))
print("\n=== BATTERS: TOP 10 RUN-SCORERS - HOW MUCH VALUE DID THEY ADD? ===")
print(bat_all.nlargest(10, "runs")[cols].to_string(index=False))
print("\n=== BATTERS: BEST SINGLE SEASONS BY RAA (min 150 balls) ===")
print(bat_season[bat_season["balls"] >= 150].nlargest(10, "raa")[["season"] + cols].to_string(index=False))
recent = batting_table(fact_batting[fact_batting["season"] >= 2023], ["batter_id"])
print("\n=== BATTERS: IMPACT PLAYER ERA 2023-26 (min 500 balls) ===")
print(recent[recent["balls"] >= 500].nlargest(10, "raa")[cols].to_string(index=False))

# ================================================================ bowling
bw = d.copy()
lg = bw.groupby(["season", "phase"]).agg(r=("bowler_runs", "sum"), b=("is_legal", "sum"), w=("is_bowler_wicket", "sum"))
lg["exp_run_per_legal"] = lg["r"] / lg["b"]
lg["exp_wkt_per_legal"] = lg["w"] / lg["b"]
bw = bw.join(lg[["exp_run_per_legal", "exp_wkt_per_legal"]], on=["season", "phase"])
bw["exp_runs"] = bw["exp_run_per_legal"] * bw["is_legal"]
bw["exp_wkts"] = bw["exp_wkt_per_legal"] * bw["is_legal"]
fact_bowling = (bw.groupby(["bowler_id", "season", "phase"])
                  .agg(legal_balls=("is_legal", "sum"), runs_conceded=("bowler_runs", "sum"),
                       exp_runs=("exp_runs", "sum"), wickets=("is_bowler_wicket", "sum"),
                       exp_wkts=("exp_wkts", "sum"), dots=("is_dot", "sum"))
                  .reset_index())
fact_bowling[["exp_runs", "exp_wkts"]] = fact_bowling[["exp_runs", "exp_wkts"]].round(3)

def bowling_table(df, keys):
    t = df.groupby(keys).agg(balls=("legal_balls", "sum"), runs=("runs_conceded", "sum"),
                             exp_runs=("exp_runs", "sum"), wkts=("wickets", "sum"), exp_wkts=("exp_wkts", "sum")).reset_index()
    t["player"] = t["bowler_id"].map(names)
    t["economy"] = (t["runs"] / t["balls"] * 6).round(2)
    t["avg_econ_same_context"] = (t["exp_runs"] / t["balls"] * 6).round(2)
    t["runs_saved"] = (t["exp_runs"] - t["runs"]).round(1)
    t["runs_saved_per_24"] = (t["runs_saved"] / t["balls"] * 24).round(2)      # per 4 overs
    t["wkts_above_avg"] = (t["wkts"] - t["exp_wkts"]).round(1)
    return t

bowl_all = bowling_table(fact_bowling, ["bowler_id"])
bowl_season = bowling_table(fact_bowling, ["bowler_id", "season"])
bcols = ["player", "balls", "wkts", "economy", "avg_econ_same_context", "runs_saved", "runs_saved_per_24", "wkts_above_avg"]

print("\n=== BOWLERS: MOST RUNS SAVED (all time) ===")
print(bowl_all.nlargest(10, "runs_saved")[bcols].to_string(index=False))
print("\n=== BOWLERS: BEST RUNS SAVED PER 4 OVERS (min 500 balls) ===")
print(bowl_all[bowl_all["balls"] >= 500].nlargest(10, "runs_saved_per_24")[bcols].to_string(index=False))
print("\n=== BOWLERS: BEST SINGLE SEASONS BY RUNS SAVED (min 150 balls) ===")
print(bowl_season[bowl_season["balls"] >= 150].nlargest(10, "runs_saved")[["season"] + bcols].to_string(index=False))
recent_b = bowling_table(fact_bowling[fact_bowling["season"] >= 2023], ["bowler_id"])
print("\n=== BOWLERS: IMPACT PLAYER ERA 2023-26 (min 500 balls) ===")
print(recent_b[recent_b["balls"] >= 500].nlargest(10, "runs_saved")[bcols].to_string(index=False))

# ================================================================ sanity check + save
print(f"\nCheck - league total RAA = {(fact_batting['runs'] - fact_batting['exp_runs']).sum():.1f} "
      f"and runs saved = {(fact_bowling['exp_runs'] - fact_bowling['runs_conceded']).sum():.1f} (both should be ~0)")
fact_batting.to_csv(OUT / "fact_batting.csv", index=False)
fact_bowling.to_csv(OUT / "fact_bowling.csv", index=False)
bat_all.to_csv(OUT / "batter_ratings_alltime.csv", index=False)
bowl_all.to_csv(OUT / "bowler_ratings_alltime.csv", index=False)
print("Saved: fact_batting, fact_bowling, batter_ratings_alltime, bowler_ratings_alltime (.csv)")