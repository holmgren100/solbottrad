# New Solana Trading Bot - Strategy v2.0

## GOAL
Build trading bot with 60% win rate

## WHAT WE LEARNED (From 774 old trades)
✅ TIER 2 filters work: MIN_PRICE=0.10, MAX_TOKENS_PER_DOLLAR=10000
✅ Binary pass/fail is better than complex scoring
❌ Age-based logic conflicts with filters → REMOVE IT
❌ 100-point scoring system too complex → REMOVE IT

## FILTERS (Simple Binary: Pass or Fail)

### Safety Checks (TIER 1)
- Token price: 0.10 to 1.0 SOL
- Liquidity: minimum $50,000
- Security score: minimum 80/100
- Contract verified: YES

### Performance Checks (TIER 2)  
- Volume/Liquidity ratio: 0.3 to 0.8 (optimal range from data)
- Max tokens per dollar: 10,000
- Top holder concentration: max 20%

## DECISION LOGIC (SIMPLE!)
```python
if Safety_Checks_Pass AND Performance_Checks_Pass:
    TRADE
else:
    REJECT (log reason)
```

## POSITION MANAGEMENT
- Entry size: 0.1 SOL per trade
- Take profit: +15%
- Stop loss: -8%
- Max hold time: 4 hours

## IMPORTANT: REMOVE FROM OLD BOT
- All age-based strategies
- All scoring systems (0-100 points)
- All complex decision layers

## CODE STRUCTURE
```
src/
├── filters/
│   ├── tier1_safety.py    (safety checks)
│   └── tier2_performance.py (performance checks)
├── decision_engine.py     (simple pass/fail logic)
└── main.py                (run bot)

tests/
└── test_filters.py        (test each filter)
```

## REFERENCE
Base code structure on: https://github.com/holmgren100/solbottrad (main branch)
Working filters from: November 2024 version (71.4% win rate)
