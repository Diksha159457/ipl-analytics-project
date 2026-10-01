# IPL 2022 Analysis Summary

## Executive Takeaways

- Gujarat was the most successful side, with 12 wins in 16 matches (75.0% win rate).
- Teams that won the toss won 48.6% (95% CI 37.6–59.8%, n=74, p=0.91), statistically indistinguishable from a coin flip.
- Chasing sides won 50.0% (95% CI 38.9–61.1%, n=74, p=1.00), statistically indistinguishable from a coin flip. Captains still chose to field 79.7% of the time, a preference the results don't justify.
- **Par score ≈ 172.** A logistic model on first-innings score alone puts the batting-first side's win probability at 50% around 172 runs. Every ~7 extra runs lifts it by 10 points. Leave-one-out accuracy is 76% (Brier 0.184 vs 0.25 for a no-skill baseline, 0.066 better).
- Kuldeep Yadav had the most repeated impact, with 4 player-of-the-match awards.
- Brabourne Stadium, Mumbai was the highest-scoring venue among grounds with at least 5 matches: 341.4 runs per match on average over 16 games.

## Notable Match Extremes

- Biggest win by runs: Chennai by 91 runs.
- Biggest win by wickets: Delhi by 9 wickets.

## Method notes

- Rates use Wilson 95% confidence intervals and an exact two-sided binomial test against 50% (α = 0.05).
- One season is 74 matches, so effects smaller than roughly ±11 points can't be detected. "No significant edge" means "no evidence of an edge", not "proof there is none".
- Venues with fewer than 5 matches are excluded from venue leaderboards to avoid small-sample extremes.
