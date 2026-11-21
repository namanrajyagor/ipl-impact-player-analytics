"""Step 2.2 - Look for naming and data quirks before cleaning."""
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 80)

m = pd.read_csv("data/interim/matches.csv")
d = pd.read_csv("data/interim/deliveries.csv")
m["year"] = m["match_date"].str[:4]

# 1. Team names and the years each one appears
teams = pd.concat([m[["team1", "year"]].rename(columns={"team1": "team"}),
                   m[["team2", "year"]].rename(columns={"team2": "team"})])
print("=== TEAMS ===")
print(teams.groupby("team")["year"].agg(["min", "max", "count"]).sort_values("min").to_string())

# 2. Venue names (spelling variants show up as separate rows)
print("\n=== VENUES ===")
print(m.groupby(["venue", "city"], dropna=False)["year"].agg(["min", "max", "count"]).sort_index().to_string())

# 3. Wicket types
print("\n=== WICKET KINDS ===")
print(d["wicket_kind"].value_counts().to_string())

# 4. What does actual_delivery mean? Compare it with the over number and the order inside the over
print("\n=== actual_delivery vs over / seq ===")
print(d[["over", "seq_in_over", "wides", "noballs", "actual_delivery"]].head(12).to_string())
wd = d[d["wides"] > 0][["match_id", "over", "seq_in_over", "wides", "actual_delivery"]].head(5)
print("\nAround a wide:\n", wd.to_string())

# 5. Other checks
print("\n=== OTHER ===")
print("Scheduled overs:", m["scheduled_overs"].value_counts().to_dict())
print("Stages:", m["stage"].value_counts(dropna=False).to_dict())
print("Max over number:", d["over"].max())
print("Matches with a city missing:", m["city"].isna().sum())