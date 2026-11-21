"""Step 2.3 - Clean the parsed tables: seasons, team and venue names, cricket counting rules,
batting positions and player ids. Writes analysis-ready tables to data/clean/ and runs checks."""
from pathlib import Path

import numpy as np
import pandas as pd

INTERIM = Path("data/interim")
CLEAN = Path("data/clean")
CLEAN.mkdir(parents=True, exist_ok=True)

m = pd.read_csv(INTERIM / "matches.csv")
d = pd.read_csv(INTERIM / "deliveries.csv")
p = pd.read_csv(INTERIM / "players.csv")
r = pd.read_csv(INTERIM / "replacements.csv")

# ------------------------------------------------------------------ 1. teams
# Same franchise, renamed -> current name. Deccan Chargers and Sunrisers Hyderabad are
# different franchises (different owners), so they stay separate.
TEAM_MAP = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}
def team(s):
    return s.replace(TEAM_MAP)

for col in ["team1", "team2", "toss_winner", "winner", "super_over_winner"]:
    m[col] = team(m[col])
d["batting_team"] = team(d["batting_team"])
p["team"] = team(p["team"])
r["team"] = team(r["team"])

# ------------------------------------------------------------------ 2. venues
# Use the part before the first comma, then merge grounds that were renamed.
VENUE_MAP = {
    "Feroz Shah Kotla": "Arun Jaitley Stadium",
    "Punjab Cricket Association Stadium": "Punjab Cricket Association IS Bindra Stadium",
    "Subrata Roy Sahara Stadium": "Maharashtra Cricket Association Stadium",
    "Sardar Patel Stadium": "Narendra Modi Stadium",
    "M.Chinnaswamy Stadium": "M Chinnaswamy Stadium",
    "Zayed Cricket Stadium": "Sheikh Zayed Stadium",
    "Andhra Cricket Association-Visakhapatnam District Cricket Association Stadium": "ACA-VDCA Stadium",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": "ACA-VDCA Stadium",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium": "Ekana Cricket Stadium",
    "Dr DY Patil Sports Academy": "DY Patil Stadium",
}
CITY_MAP = {"Bangalore": "Bengaluru", "Chandigarh": "Mohali", "New Chandigarh": "Mullanpur",
            "Navi Mumbai": "Navi Mumbai"}
VENUE_CITY = {  # fixed city for grounds whose city is spelled several ways
    "Maharaja Yadavindra Singh International Cricket Stadium": "Mullanpur",
    "Punjab Cricket Association IS Bindra Stadium": "Mohali",
    "DY Patil Stadium": "Navi Mumbai",
    "M Chinnaswamy Stadium": "Bengaluru",
}
m["venue_raw"] = m["venue"]
m["venue"] = m["venue_raw"].str.split(",").str[0].str.strip().replace(VENUE_MAP)
m["city"] = m["city"].replace(CITY_MAP)
# fill a missing city with the most common city recorded for that ground (Dubai, Sharjah)
m["city"] = m["city"].fillna(m.groupby("venue")["city"].transform(
    lambda s: s.mode().iloc[0] if s.notna().any() else np.nan))
m["city"] = m["venue"].map(VENUE_CITY).fillna(m["city"])
# one city per ground
m["city"] = m.groupby("venue")["city"].transform(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
UAE = {"Dubai", "Sharjah", "Abu Dhabi"}
SA = {"Cape Town", "Port Elizabeth", "Durban", "Centurion", "Johannesburg", "Kimberley",
      "East London", "Bloemfontein"}
m["country"] = np.select([m["city"].isin(UAE), m["city"].isin(SA)], ["UAE", "South Africa"], "India")

# ------------------------------------------------------------------ 3. match fields
m["season"] = m["match_date"].str[:4].astype(int)            # fixes 2007/08, 2009/10, 2020/21
m["is_playoff"] = m["stage"].notna()
m["result_type"] = m["result"].fillna("normal")               # normal / tie / no result
m["is_dl"] = m["method"].eq("D/L")
m["match_winner"] = m["winner"].fillna(m["super_over_winner"])  # ties -> super-over winner
m["toss_winner_won"] = np.where(m["match_winner"].notna(), m["toss_winner"] == m["match_winner"], np.nan)

# ------------------------------------------------------------------ 4. deliveries
n_super = int(d["is_super_over"].sum())
d = d[~d["is_super_over"]].drop(columns="is_super_over").copy()   # super overs excluded everywhere
d = d.merge(m[["match_id", "season"]], on="match_id", how="left")

d["is_wide"] = d["wides"] > 0
d["is_noball"] = d["noballs"] > 0
d["is_legal"] = ~d["is_wide"] & ~d["is_noball"]
d["is_ball_faced"] = ~d["is_wide"]                          # no-balls count as faced
d["bowler_runs"] = d["runs_batter"] + d["wides"] + d["noballs"]   # byes / leg-byes not charged
d["is_four"] = d["runs_batter"].eq(4)
d["is_six"] = d["runs_batter"].eq(6)
d["is_dot"] = d["is_ball_faced"] & d["runs_batter"].eq(0)
d["phase"] = pd.cut(d["over"], [0, 6, 15, 20], labels=["Powerplay", "Middle", "Death"]).astype(str)

BOWLER_KINDS = {"caught", "bowled", "lbw", "caught and bowled", "stumped", "hit wicket"}
d["is_bowler_wicket"] = d["wicket_kind"].isin(BOWLER_KINDS)
d["is_team_wicket"] = d["wicket_kind"].notna() & d["wicket_kind"].ne("retired hurt")  # retired hurt can return

d = d.sort_values(["match_id", "innings", "over", "seq_in_over"]).reset_index(drop=True)
key = ["match_id", "innings", "over"]
d["legal_ball_in_over"] = d.groupby(key)["is_legal"].cumsum()
# ball number as scorers write it: wides/no-balls carry the number of the next legal ball
d["ball_label_no"] = d["legal_ball_in_over"] + (~d["is_legal"]).astype(int)
d["innings_legal_ball"] = d.groupby(["match_id", "innings"])["is_legal"].cumsum()
d["balls_left"] = 120 - d["innings_legal_ball"]
d["team_runs_so_far"] = d.groupby(["match_id", "innings"])["runs_total"].cumsum()
d["team_wkts_so_far"] = d.groupby(["match_id", "innings"])["is_team_wicket"].cumsum()

# batting position = order in which batters first appear in the innings
appear = pd.concat([
    d[["match_id", "innings", "batter"]].assign(o=d.index * 2).rename(columns={"batter": "name"}),
    d[["match_id", "innings", "non_striker"]].assign(o=d.index * 2 + 1).rename(columns={"non_striker": "name"}),
]).sort_values("o").drop_duplicates(["match_id", "innings", "name"])
appear["batting_position"] = appear.groupby(["match_id", "innings"]).cumcount() + 1
d = d.merge(appear[["match_id", "innings", "name", "batting_position"]]
            .rename(columns={"name": "batter"}), on=["match_id", "innings", "batter"], how="left")

# player ids (names are unique within a match)
ids = p[["match_id", "player", "player_id"]]
for col in ["batter", "bowler", "non_striker", "player_out"]:
    d = d.merge(ids.rename(columns={"player": col, "player_id": f"{col}_id"}),
                on=["match_id", col], how="left")

# ------------------------------------------------------------------ 5. players dimension
dim_player = (p.merge(m[["match_id", "match_date"]], on="match_id")
               .sort_values("match_date")
               .groupby("player_id")
               .agg(player=("player", "last"), last_team=("team", "last"),
                    first_season=("match_date", lambda s: int(s.min()[:4])),
                    last_season=("match_date", lambda s: int(s.max()[:4])),
                    matches=("match_id", "nunique"))
               .reset_index())

# ------------------------------------------------------------------ 6. checks
print("=== CHECKS ===")
inn = d.groupby(["match_id", "innings"]).agg(total=("runs_total", "sum"), target=("target_runs", "first"))
inn1 = inn.xs(1, level="innings")["total"]
inn2 = inn.xs(2, level="innings")
chk = inn2.join(inn1.rename("first_total"))
chk = chk.join(m.set_index("match_id")[["is_dl"]])
normal = chk[~chk["is_dl"] & chk["target"].notna()]
bad_target = normal[normal["target"] != normal["first_total"] + 1]
print(f"1. Target = 1st-innings total + 1 (non-D/L): {len(normal) - len(bad_target)} of {len(normal)} OK")
dup = d.duplicated(["match_id", "innings", "over", "seq_in_over"]).sum()
print(f"2. Duplicate balls: {dup}")
ad_ball = pd.to_numeric(d["actual_delivery"].astype(str).str.split(".").str[1], errors="coerce")
print(f"3. Our ball numbering = Cricsheet actual_delivery: {(ad_ball == d['ball_label_no']).sum():,} of {len(d):,}")
ov = d.groupby(key)["is_legal"].sum().rename("legal").reset_index()
last_over = ov.groupby(["match_id", "innings"])["over"].transform("max")
odd = ov[(ov["legal"] != 6) & (ov["over"] != last_over)]
print(f"4. Completed overs without exactly 6 legal balls: {len(odd)}  {odd['legal'].value_counts().to_dict()}")
print(f"5. Teams after renaming: {pd.concat([m['team1'], m['team2']]).nunique()} (expected 15)")
print(f"6. Grounds after merging: {m['venue'].nunique()} (raw names: {m['venue_raw'].nunique()})")
print(f"7. Matches with no city: {m['city'].isna().sum()}")
print(f"8. Balls with a missing batter/bowler id: {d['batter_id'].isna().sum()} / {d['bowler_id'].isna().sum()}")
print(f"9. Super-over balls removed: {n_super}; deliveries kept: {len(d):,}")
print(f"10. Matches by country: {m['country'].value_counts().to_dict()}")

# ------------------------------------------------------------------ 7. save
keep_m = ["match_id", "season", "match_date", "match_number", "stage", "is_playoff", "venue", "city", "country",
          "team1", "team2", "toss_winner", "toss_decision", "match_winner", "result_type", "super_over_winner",
          "win_by_runs", "win_by_wickets", "is_dl", "toss_winner_won", "player_of_match", "venue_raw"]
m[keep_m].to_csv(CLEAN / "matches.csv", index=False)
d.drop(columns=["actual_delivery"]).to_csv(CLEAN / "deliveries.csv", index=False)
dim_player.to_csv(CLEAN / "players.csv", index=False)
r.to_csv(CLEAN / "replacements.csv", index=False)
print("\nSaved: data/clean/matches.csv, deliveries.csv, players.csv, replacements.csv")
print("\nGrounds:")
print(m.groupby(["venue", "city", "country"]).size().rename("matches").to_string())