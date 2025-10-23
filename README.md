# 🎾 Tennis Money Printer Go Brrrr 💰

## Status: **80% ACCURACY BABY!** 🚀

Yeah, you read that right. EIGHTY PERCENT. This thing actually works.

### What is this?

A completely over-engineered tennis prediction system that:
- Started as a weekend project
- Turned into a full-blown ML-inspired beast
- Actually predicts tennis matches at **80% accuracy**
- Makes bookies nervous (probably)
- Has more files than a tax return

### Does it work?

```python
accuracy = 0.80  # YES IT DOES
money_printer_status = "brrrrr" if accuracy > 0.75 else "broken"
print(f"Status: {money_printer_status}")  # Output: Status: brrrrr
```

### Setup (if future me forgets)

```bash
# Copy the secret sauce
cp api_secrets.example.py api_secrets.py

# Fill in your API keys (you know which ones)
# Hint: starts with 's' and ends with 'core' 
# And the betting one that rhymes with "sporty pet"

# Install stuff
pip install -r requirements.txt

# Make money... I mean, run predictions
python3.9 main.py
```

### Features That Actually Matter

- ✅ **Multi-year stats blending** (because one year is for amateurs)
- ✅ **Surface-specific analysis** (clay ≠ grass, who knew?)
- ✅ **UTR ratings** (because ATP rankings lie)
- ✅ **Recent form weighting** (hot streaks are real)
- ✅ **Opponent quality penalties** (no more inflated stats from weak opponents)
- ✅ **Coin flip detection** (skip the 50/50s like a boss)
- ✅ **Injury checking** (no betting on broken players)
- ✅ **Mental toughness metrics** (because tennis is 90% mental and 10% not getting psyched out)

### Features That Don't Matter But Took Forever

- 🎨 Next.js frontend (it looks cool though)
- 📊 Weight configuration manager with 47 different configs
- 🔍 5-tier skip logic system (overkill? maybe. effective? yes.)
- 📝 Loss analysis improvements (learned from every L)
- 🎯 Tournament classifier (Grand Slams hit different)

### The Journey

```
v1.0: 45% accuracy (yikes)
v2.0: 55% accuracy (getting there)
v3.0: 62% accuracy (ok now we're talking)
v4.0: 68% accuracy (hot streak!)
v5.0: 73% accuracy (THIS IS IT)
v6.0: 74% accuracy (PEAK!)
v7.0: 80% accuracy (WHAT THE F—)
```

### What Went Wrong (and then right)

1. **First version**: Trusted ATP rankings blindly → 45% accuracy 🤡
2. **Second version**: Added UTR ratings → 55% accuracy 📈
3. **Third version**: Surface filtering → 62% accuracy 🎾
4. **Fourth version**: Multi-year blending → 68% accuracy 🔥
5. **Fifth version**: Enhanced form weighting → 73% accuracy 💪
6. **Sixth version**: Loss analysis (Kypson/Engel taught me lessons) → 74% accuracy 🧠
7. **Current version**: Everything + opponent quality penalties → **80% ACCURACY** 🚀🚀🚀

### Configuration Files

I have like 12 different `all_*.csv` files with different weight configs:
- `all_HOT_STREAK_74PCT_BACKUP.csv` - The OG that hit 74%
- `all_LOSS_ANALYSIS_FIX_V1.csv` - After fixing the Kypson disaster
- `all_ULTRA_CONSERVATIVE_90PCT.csv` - For when I'm feeling scared
- `all_ML_OPTIMIZED_2024.csv` - When I pretended I knew ML
- etc.

Current winner: **2-year mode with loss analysis improvements** = 80% 👑

### The Secret Sauce

```python
# The magic formula (don't steal this, it took forever)
weighted_score = (
    set_performance * 0.28 +  # Historical dominance
    recent_form * 0.16 +       # Are they hot or not?
    utr_rating * 0.15 +        # Real skill level
    ranking_advantage * 0.22 + # Who's better on paper?
    # ... and like 10 more factors
)

# Plus a bunch of skip logic that prevents stupid bets
if coin_flip_detected:
    return "SKIP THIS GARBAGE"
```

### Files You'll Never Look At Again

- All the `debug_*.py` files (there are like 20)
- `.private_docs/` - 50+ markdown files documenting every mistake
- `.private_tests/` - Tests I wrote once and never ran
- `archive/` - The graveyard of bad ideas
- Everything in `scripts/` - "I'll need this later" (narrator: he didn't)

### Things I Learned

1. **More data ≠ better predictions** (quality > quantity)
2. **Hot streaks are real** (recent form is king)
3. **Set win rates lie** (if you only play weak opponents)
4. **UTR > ATP ranking** (for predictions at least)
5. **When in doubt, skip the match** (coin flips are -EV)
6. **Clay specialists exist** (Nadal has entered the chat)
7. **Injuries matter** (duh, but I had to code a checker)

### Tech Stack

- Python 3.9 (because 3.13 broke curl-cffi)
- FastAPI (for the API I never use)
- Next.js (for the frontend I look at once)
- Pandas (data frames go brr)
- curl-cffi (because requests got blocked)
- A LOT of hope and caffeine ☕

### TODO

- [ ] Stop tweaking weights (80% is good enough)
- [ ] Remember the frontend exists (it's pretty good actually)
- [ ] Go outside
- [ ] Touch grass
- [x] Hit 80% accuracy
- [x] Built a functional Next.js frontend
- [x] Commit to GitHub before I break something

### The Real MVP

```python
# The actual hero of this codebase
if prediction.should_skip:
    return None  # Saved me from so many bad bets
```

### Disclaimer

This is for research purposes only. Also, I'm not responsible if you:
- Lose money betting
- Get addicted to tweaking weights
- Spend 6 months on a "weekend project"
- Try to explain your code to non-technical friends
- Develop an unhealthy obsession with set win rates

### Final Thoughts

80% accuracy. On tennis predictions. With over-engineered Python code and too many CSV files.

**WE TAKE THOSE.** 🏆

---

*Last updated: When it hit 80% and I stopped touching it (October 2025)*

*"If it ain't broke, don't commit more changes"* - Ancient programmer wisdom
