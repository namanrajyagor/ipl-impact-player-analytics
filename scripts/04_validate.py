"""Step 2.4 - Validate the clean data against well-known IPL records."""
import pandas as pd

pd.set_option("display.width", 200)
d = pd.read_csv("data/clean/deliveries.csv")
m = pd.read_csv("data/clean/matches.csv")

# 1. Top run-scorer of each season (Orange Cap)
bat = d.groupby(["season", "batter"]).agg(runs=("runs_batter", "sum"), balls=("is_ball_faced", "sum")).reset_index()
orange = bat.sort_values("runs", ascending=False).groupby("season").head(1).sort_values("season")
print("=== TOP RUN-SCORER PER SEASON ===")
print(orange.to_string(index=False))

# 2. Top wicket-taker of each season (Purple Cap)
bowl = d.groupby(["season", "bowler"]).agg(wkts=("is_bowler_wicket", "sum"), balls=("is_legal", "sum"),
                                           runs=("bowler_runs", "sum")).reset_index()
purple = bowl.sort_values(["wkts", "runs"], ascending=[False, True]).groupby("season").head(1).sort_values("season")
print("\n=== TOP WICKET-TAKER PER SEASON ===")
print(purple.to_string(index=False))

# 3. Highest individual innings
inns = (d.groupby(["match_id", "innings", "batter"])
          .agg(runs=("runs_batter", "sum"), balls=("is_ball_faced", "sum")).reset_index()
          .merge(m[["match_id", "season"]], on="match_id"))
print("\n=== HIGHEST INDIVIDUAL SCORES ===")
print(inns.nlargest(5, "runs").to_string(index=False))

# 4. Highest team totals
team = (d.groupby(["match_id", "innings", "batting_team"])
          .agg(runs=("runs_total", "sum"), wkts=("is_team_wicket", "sum")).reset_index()
          .merge(m[["match_id", "season", "venue"]], on="match_id"))
print("\n=== HIGHEST TEAM TOTALS ===")
print(team.nlargest(5, "runs").to_string(index=False))

# 5. Best bowling figures in a match
fig = (d.groupby(["match_id", "bowler"]).agg(wkts=("is_bowler_wicket", "sum"), runs=("bowler_runs", "sum"))
         .reset_index().merge(m[["match_id", "season"]], on="match_id"))
print("\n=== BEST BOWLING FIGURES ===")
print(fig.sort_values(["wkts", "runs"], ascending=[False, True]).head(5).to_string(index=False))

# 6. Most runs and wickets, all time
print("\n=== MOST RUNS (ALL TIME) ===")
print(d.groupby("batter")["runs_batter"].sum().nlargest(5).to_string())
print("\n=== MOST WICKETS (ALL TIME) ===")
print(d.groupby("bowler")["is_bowler_wicket"].sum().nlargest(5).to_string())