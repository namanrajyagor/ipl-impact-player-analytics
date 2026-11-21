"""Step 2.1 - Parse the raw Cricsheet JSON files into flat tables (no cleaning yet)."""
import json
from collections import Counter
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/ipl_json")
OUT = Path("data/interim")
OUT.mkdir(parents=True, exist_ok=True)

matches, deliveries, players, replacements = [], [], [], []

for f in sorted(RAW.glob("*.json")):
    match_id = int(f.stem)                      # file name = Cricsheet match id
    d = json.loads(f.read_text(encoding="utf-8"))
    info = d["info"]
    out = info.get("outcome", {})
    by = out.get("by", {})
    event = info.get("event", {})
    team1, team2 = info["teams"]

    # ---------- one row per match ----------
    matches.append({
        "match_id": match_id,
        "match_date": info["dates"][0],
        "season_label": str(info["season"]),
        "match_number": event.get("match_number"),
        "stage": event.get("stage"),               # e.g. Final, Qualifier 1 (None = league)
        "city": info.get("city"),
        "venue": info.get("venue"),
        "team1": team1,
        "team2": team2,
        "toss_winner": info["toss"]["winner"],
        "toss_decision": info["toss"]["decision"],
        "winner": out.get("winner"),
        "result": out.get("result"),               # 'tie' / 'no result' / None (normal result)
        "super_over_winner": out.get("eliminator"),
        "win_by_runs": by.get("runs"),
        "win_by_wickets": by.get("wickets"),
        "method": out.get("method"),               # 'D/L' for rain-affected results
        "scheduled_overs": info.get("overs"),
        "player_of_match": ", ".join(info.get("player_of_match", [])),
    })

    # ---------- one row per player per match ----------
    registry = info.get("registry", {}).get("people", {})
    for team, names in info.get("players", {}).items():
        for name in names:
            players.append({"match_id": match_id, "team": team, "player": name,
                            "player_id": registry.get(name)})

    # ---------- one row per delivery ----------
    for inn_no, inn in enumerate(d.get("innings", []), start=1):
        target = inn.get("target", {})
        for ov in inn.get("overs", []):
            for seq, b in enumerate(ov["deliveries"], start=1):
                ex = b.get("extras", {})
                wk = b.get("wickets", [])
                deliveries.append({
                    "match_id": match_id,
                    "innings": inn_no,
                    "batting_team": inn["team"],
                    "is_super_over": bool(inn.get("super_over", False)),
                    "target_runs": target.get("runs"),
                    "target_overs": target.get("overs"),
                    "over": ov["over"] + 1,                # Cricsheet counts overs from 0
                    "seq_in_over": seq,                    # order within the over, incl. wides/no-balls
                    "actual_delivery": b.get("actual_delivery"),
                    "batter": b["batter"],
                    "bowler": b["bowler"],
                    "non_striker": b["non_striker"],
                    "runs_batter": b["runs"]["batter"],
                    "runs_extras": b["runs"]["extras"],
                    "runs_total": b["runs"]["total"],
                    "wides": ex.get("wides", 0),
                    "noballs": ex.get("noballs", 0),
                    "byes": ex.get("byes", 0),
                    "legbyes": ex.get("legbyes", 0),
                    "penalty": ex.get("penalty", 0),
                    "wicket_count": len(wk),
                    "player_out": wk[0]["player_out"] if wk else None,
                    "wicket_kind": wk[0]["kind"] if wk else None,
                    "fielders": ", ".join(x.get("name", "") for x in wk[0].get("fielders", [])) if wk else None,
                    "player_out_2": wk[1]["player_out"] if len(wk) > 1 else None,
                    "wicket_kind_2": wk[1]["kind"] if len(wk) > 1 else None,
                })
                # substitutions recorded on this ball (Impact Player, concussion, ...)
                for r in b.get("replacements", {}).get("match", []):
                    replacements.append({"match_id": match_id, "innings": inn_no, "over": ov["over"] + 1,
                                         "team": r.get("team"), "player_in": r.get("in"),
                                         "player_out": r.get("out"), "reason": r.get("reason")})

tables = {
    "matches": pd.DataFrame(matches),
    "deliveries": pd.DataFrame(deliveries),
    "players": pd.DataFrame(players),
    "replacements": pd.DataFrame(replacements),
}
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:13s} {len(df):>8,} rows  -> data/interim/{name}.csv")

dl = tables["deliveries"]
print(f"\nSuper-over deliveries: {dl['is_super_over'].sum():,}")
print(f"Balls with 2 wickets:  {(dl['wicket_count'] > 1).sum()}")
print(f"actual_delivery filled: {dl['actual_delivery'].notna().sum():,} of {len(dl):,}")
print(f"Players without an id: {tables['players']['player_id'].isna().sum()}")
if len(replacements):
    rep = tables["replacements"]
    print("\nSubstitution reasons:", dict(Counter(rep["reason"])))
    rep_season = rep.merge(tables["matches"][["match_id", "match_date"]], on="match_id")
    print("Substitutions per year:", rep_season["match_date"].str[:4].value_counts().sort_index().to_dict())