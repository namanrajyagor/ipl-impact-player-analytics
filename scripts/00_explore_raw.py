"""First look at the raw Cricsheet IPL files: seasons, matches, outcomes, structure."""
import json
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/ipl_json")
files = sorted(RAW.glob("*.json"))
print(f"Match files: {len(files)}")

seasons, outcomes, methods, dates = Counter(), Counter(), Counter(), []
for f in files:
    info = json.loads(f.read_text(encoding="utf-8"))["info"]
    seasons[str(info["season"])] += 1
    dates.append(info["dates"][0])
    out = info["outcome"]
    if "winner" in out:
        outcomes["result"] += 1
    else:
        outcomes[out.get("result", "unknown")] += 1      # no result / tie
    if "method" in out:
        methods[out["method"]] += 1                       # e.g. D/L (rain)

print(f"Date range: {min(dates)} to {max(dates)}")
print("\nMatches per season:")
for s, n in sorted(seasons.items()):
    print(f"  {s}: {n}")
print("\nOutcomes:", dict(outcomes))
print("Rain-rule results:", dict(methods))

sample = json.loads(files[-1].read_text(encoding="utf-8"))
print("\nTop-level keys:", list(sample.keys()))
print("Info keys:", list(sample["info"].keys()))
first_ball = sample["innings"][0]["overs"][0]["deliveries"][0]
print("One delivery looks like:", first_ball)