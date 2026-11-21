# Project 4 — IPL Analytics: What Actually Wins Matches

## 1. Objective
Help an IPL franchise's strategy team understand what wins matches in the modern IPL:
how the Impact Player rule changed the game, which players add the most value compared
with others in their era and phase, and how winnable a chase is from any situation.

## 2. Stakeholders
| Stakeholder | Needs | Decisions supported |
|---|---|---|
| Strategy & auction team | Fair, era-adjusted player value | Auction bids, retentions |
| Coaching staff | How scoring changed by phase since the rule | Batting order, bowling plans, bat/bowl first |
| Match-day analyst | Win chances in a live chase | When to attack or consolidate |

## 3. Scope
- **In:** men's IPL 2008–2026, 1,243 matches, ball-by-ball data from Cricsheet (cricsheet.org, downloaded 19 Nov 2026)
- **Out:** auction prices, ball-tracking / fielding positions, WPL, live feeds
- **Handling:** 9 no-results excluded from win/loss analysis (their balls kept in player stats);
  23 D/L matches excluded from Impact Player and chase analysis; super-over balls excluded from all
  player stats; ties count with the super-over winner as the match winner (and as 0.5 in chase win %).

## 4. Business questions
**A. How the game has changed**
1. How have scoring rates changed by season, overall and by phase?
2. Does batting first or chasing win more often, and does winning the toss help?
3. Which venues are high/low scoring and which favour chasing?

**B. USP 1 — the Impact Player rule (from 2023)**
4. Did first-innings totals and the share of 200+ totals rise, and by how much?
5. Which phase changed most, and did teams lose more wickets while scoring faster?
6. Did chasing 190+ targets become more successful?
7. Was it the rule, or a trend that already existed (2018–2022)?

**C. USP 2 — fair player ratings**
8. Which batters add the most runs above average for their season and phase?
9. Which bowlers save the most runs against the average economy for their season and phase?

**D. USP 3 — the chase**
10. What is the chance of winning a chase from a given runs needed, balls left and wickets in hand,
    and has it changed since the rule?

## 5. Metric definitions
| Metric | Definition |
|---|---|
| Season | Calendar year of the match date (fixes Cricsheet labels "2007/08", "2009/10", "2020/21") |
| Phase | Powerplay overs 1–6, Middle 7–15, Death 16–20 |
| Legal ball | Any delivery that is not a wide or a no-ball |
| Ball faced (batter) | Every delivery except wides (no-balls count as faced) |
| Runs conceded (bowler) | Batter runs + wides + no-balls (byes and leg-byes are not charged) |
| Bowler wicket | All dismissals except run out, retired hurt/out, obstructing the field |
| Strike rate | Batter runs ÷ balls faced × 100 |
| Economy | Runs conceded ÷ legal balls × 6 |
| Run rate | Team runs ÷ legal balls × 6 |
| Dot-ball % / Boundary % | Share of balls with 0 runs off the bat / with a 4 or 6 |
| Runs above average (RAA) | Σ (batter runs on the ball − average runs per ball faced in that season and phase) |
| Runs saved (bowler) | Σ (average runs conceded per ball in that season and phase − runs conceded on the ball) |
| RAA per 100 balls | RAA ÷ balls faced × 100 (rate version for comparing players) |
| Chase win % | Share of completed 20-over chases that won from a given state (ties = 0.5) |

Ranking thresholds: at least 500 balls (all-time) or 150 balls (single season) for batters;
at least 500 / 150 legal balls for bowlers. Chase states shown only with 30+ chases behind them.

## 6. Impact Player analysis design
- **Rule:** from IPL 2023 each team may substitute one player during the match (an extra batter or bowler).
- **Before:** 2018–2022 (5 seasons). **After:** 2023–2026 (4 seasons). 2022 is the first 10-team season,
  so 2022 vs 2023–26 is also shown as a like-for-like format comparison.
- **Exclusions:** D/L and no-result matches; reduced-overs innings; super-over balls.
- **Measures:** average first-innings total; % of innings scoring 200+; run rate by phase; balls per wicket;
  success rate chasing 190+; balls faced by batters at No. 8 and below (batting depth).
- **Checks before concluding:**
  1. Trend check — fit the 2018–22 trend in first-innings totals, project it to 2023–26, compare with actual.
  2. Venue check — repeat the comparison only on venues used in both periods
     (2020 was played in the UAE; 2021 partly; 2022 only in Mumbai and Pune).
  3. Mechanism check — deeper batting and more aggressive top orders should appear if the rule is the cause.
- **Caveats:** only 4 seasons after; other changes (e.g. two bouncers per over from 2024); observational data,
  so the result is evidence, not proof.

## 7. Tools and responsibilities
- **Python (pandas):** parse raw JSON, clean, standardise names, compute expected runs, ratings and chase states,
  validate against known records, export clean CSVs.
- **Power BI:** Power Query, star-schema model, DAX measures, interactive pages.

## 8. Data model (planned)
- **Facts:** `fact_deliveries` (one row per ball), `fact_chase_states` (one row per chase ball state)
- **Dimensions:** `dim_match`, `dim_player`, `dim_team`, `dim_venue`, `dim_season`, `dim_phase`

## 9. Dashboard pages (planned)
1. **Overview** — how the IPL has changed season by season
2. **Impact Player** — before vs after, with the trend, venue and mechanism checks
3. **Batter ratings** — era-adjusted leaderboards (all-time / by season)
4. **Bowler ratings** — runs saved leaderboards
5. **Player profile** — drill-through from any player
6. **Chase calculator** — what-if parameters for runs needed, balls left, wickets in hand
7. **Teams & venues** — bat first vs chase, toss, venue scoring
Plus tooltip pages, bookmarks and a field parameter to switch metrics.

## 10. Validation plan
- Match count per season matches the source (1,243 total)
- Known records reproduced exactly (e.g. top run-scorer of a season, highest individual score, highest team total)
- Every match's total runs from deliveries matches the innings total; no ball appears twice