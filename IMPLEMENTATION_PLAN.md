# 🔧 IMPLEMENTATION PLAN - Återställ Fungerande Bot

**Date:** 2026-01-08
**Based on:** Git history research + User requirements
**Status:** AWAITING APPROVAL

---

## 📊 RESEARCH FINDINGS

### 1. Liquidity $0 Fix - VI HAR DET REDAN!

**Hittade i:** Commit 624692b (Jan 4, 2026)
**Nuvarande implementation:**

```python
# main.py line ~931+
# TIER 1: VERY new launches (<30 min)
if liq == $0 and age < 0.5h and vol_1h >= $5k and txns_1h >= 100:
    ACCEPT  # API lag för ny launch

# TIER 2: New launches (<24h)
if liq == $0 and age < 24h and vol_1h >= $20k and txns_1h >= 100 and buy >= 50%:
    ACCEPT  # API lag för ny launch med stark activity
```

**SLUTSATS:** Vi HAR redan en $0 liq fix!

---

### 2. Partial Profit Settings - Current Fungerar!

```python
milestone_100: 25%  # +100% → ta 25%
milestone_200: 15%  # +200% → ta 15%
milestone_300-700: 10%  # Ta 10% per milestone

Trailing stop: 8% below peak (aktiveras vid +15%)
```

**Session 21:01 bevis:**
- FREN +395% (trailing)
- JUTICE +118% (trailing)
- ALL top winners använde trailing stops!

**FÖRSLAG: ÄNDRA INGET!**

---

### 3. Stop Loss - Historik

```
Dec 29: SL = 20%
Jan 7: SL = -12%
Current: SL = -12%
User vill: -10%

4th AI data: -10% SL = +640% PnL (3X better)
```

---

### 4. Buy Ratio - Fråga!

```
Dec 29: 45% (striktare)
Jan 3: 39% (golden era, +$633, 40% win!)
Current: 39%
User vill: 45%?
```

**FRÅGA:** Varför tillbaka till 45%?
- Jan 3 golden era VAR 39%
- 45% = färre trades

---

### 5. Jito = MEV Protection (för swaps, INTE rug detection)

**Kan läggas till senare för live trading**

---

## ✅ IMPLEMENTATION TASKS

### PHASE 1: API Integration (GRATIS!)

**Task 1: Restore RugCheck**
```bash
git show 9b3913f~1:src/blockchain/rugcheck_client.py > trading_bot/rugcheck_client.py
# Integrera i main.py
# Testa FREE tier
```

**Task 2: Fix Birdeye**
```bash
# Kolla docs: https://docs.birdeye.so
# Uppdatera API format
# Enable: ENABLE_BIRDEYE=true
```

**Task 3: Check Solscan**
```bash
grep SOLSCAN .env
# Aktivera om key finns
```

**Timeline:** 4-6 timmar
**Cost:** $0

---

### PHASE 2: Config Changes

**Task 4: SL → -10%**
```python
base_stop_percent = 10.0  # -10% (4th AI optimal)
```

**Task 5: Buy Ratio → 45%**
```python
MIN_BUY_RATIO = 0.45  # OM user confirmar!
```

**Task 6: Partial Profits**
```
FÖRSLAG: ÄNDRA INGET (fungerar bra!)

Om user vill:
- milestone_50: 15%?
- milestone_75: 20%?
```

**Timeline:** 15 minuter

---

### PHASE 3: Testing (3-5 sessions)

```
☐ Kör sessions
☐ Logga rug blocks
☐ Beräkna ROI
☐ Beslut om paid tiers
```

---

## ❓ FRÅGOR TILL USER

1. **Buy Ratio:** Säker på 45%? Jan 3 golden var 39%!

2. **Partial Profits:** Vill du ändra? (current fungerar!)

3. **Liquidity:** Vi har $0 fix redan! Blockerade den GOLDXRP?

4. **Jito:** För live trading senare?

---

## 💰 KOSTNAD

**Testing:** $0 (FREE tiers)
**Senare om behövs:** $49-149/mo

---

## 🚀 NÄSTA STEG

**Säg "kör" → Jag börjar!**
**Säg "vänta" → Frågor först!**

Väntar på godkännande! 💪
