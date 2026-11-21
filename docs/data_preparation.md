# Data Preparation

## Source
Cricsheet (cricsheet.org) IPL ball-by-ball JSON, downloaded 19 Nov 2026: 1,243 matches, 18 Apr 2008 – 31 May 2026.

## Pipeline
| Script | What it does | Output |
|---|---|---|
| `00_explore_raw.py` | First look: matches per season, outcomes, file structure | printed summary |
| `01_parse_raw.py` | Flattens nested JSON into tables, no cleaning | `data/interim/` matches 1,243 · deliveries 295,732 · players 27,909 · replacements 563 |
| `02_check_quirks.py` | Lists team names, venue variants, wicket kinds, ball numbering | printed summary |
| `03_clean.py` | Applies all fixes and cricket rules, runs checks | `data/clean/` |
| `04_validate.py` | Reproduces well-known IPL records | printed summary |

## Quirks found and fixed
| Quirk | Fix |
|---|---|
| Season labels "2007/08", "2009/10", "2020/21" | Season = year of the match date |
| 19 team names for 15 franchises (Delhi Daredevils, Kings XI Punjab, Royal Challengers Bangalore, Rising Pune Supergiants) | Mapped to current names; Deccan Chargers and Sunrisers Hyderabad kept separate (different franchises) |
| 41 venue names for 36 grounds (Feroz Shah Kotla, PCA Stadium, Subrata Roy Sahara, Sardar Patel/Motera, Bangalore/Bengaluru) | Name before first comma + rename map; one city per ground |
| 51 matches with no city (Dubai 33, Sharjah 18) | Filled from the ground |
| 175 super-over balls | Excluded from all ball-level stats; super-over winner kept as match winner |
| Wides and no-balls in the over sequence | Legal-ball counter; matches Cricsheet `actual_delivery` on all 295,557 balls |
| 8 overs with 5 or 7 legal balls | Real umpire miscounts; kept as recorded |

## Cricket rules applied
Ball faced = not a wide · Legal ball = not a wide or no-ball · Bowler runs = batter runs + wides + no-balls ·
Bowler wickets exclude run out, retired hurt/out, obstructing the field · Team wickets exclude retired hurt ·
Phases: Powerplay 1–6, Middle 7–15, Death 16–20.

## Added fields
Batting position (order of first appearance), running team score and wickets, balls left,
player ids for batter / bowler / non-striker / dismissed player, host country (India 1,075 · UAE 111 · South Africa 57).

## Checks
| Check | Result |
|---|---|
| Chase target = first-innings total + 1 (non-D/L) | 1,214 of 1,214 |
| Duplicate balls | 0 |
| Ball numbering vs Cricsheet | 295,557 of 295,557 |
| Teams / grounds after cleaning | 15 / 36 |
| Missing cities / player ids | 0 / 0 |
| Orange and Purple Cap 2008–2025 | All 36 reproduced exactly (e.g. Kohli 973 in 2016, Bravo and Harshal Patel 32) |
| Records | Gayle 175*, SRH 287/3, Alzarri Joseph 6/12 reproduced |

## Impact Player usage
557 Impact Player substitutions: 0 before 2023, then about 140 a season, roughly 95% of the maximum possible.