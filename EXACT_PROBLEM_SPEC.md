# EXAKT PROBLEMANALYS - MOMENTUM RUNNER V2.0

**Datum:** 2026-01-24 15:30
**Status:** PRODUKTION FUNGERAR INTE
**Kostnad:** ~200 SEK, 10+ timmar slösade
**Root Cause:** ÄNDRINGAR INTE I PRODUKTION + TOKEN DISCOVERY FAILAR

---

## PRODUKTIONSLOGGAR - VAD SOM HÄNDER NU

### Scan-resultat:
```
2026-01-24 14:22:22,838 - src.main - INFO - ✅ Scan complete: 0 entries from 18 tokens
```

**Translation:** Boten scannar BARA 18 hardcoded tokens, inget nytt.

### Momentum scoring:
```
- Bonk (MOMENTUM) - Score 0/100 (need 80+)
- BOME (MOMENTUM) - Score 0/100 (need 80+)
- $WIF (MOMENTUM) - Score 15/100 (need 80+)
- JUP (MOMENTUM) - Score 30/100 (need 80+)
- MEW (MOMENTUM) - Score 0/100 (need 80+)
```

**Translation:** Alla tokens får 0-30/100, threshold är 80+ → INGEN KAN PASSA

### Safety rejections:
```
- 5z3EqYQo... (SAFETY) - LP=True, Mint=False
- HeLp6NuQ... (SAFETY) - LP=True, Mint=False
- mSoLzYCx... (SAFETY) - LP=True, Mint=False
... (7 tokens rejecterade pga mint authority exists)
```

### Jupiter API failures:
```
Jupiter request failed (attempt 1/3): Status 401
Jupiter request failed (attempt 2/3): Status 401
Jupiter request failed (attempt 3/3): Status 401
```

---

## KRITISKA PROBLEM (Varför inget fungerar)

### Problem 1: BARA 18 TOKENS - INGEN NY DISCOVERY ⚠️⚠️⚠️

**Symptom:** "Scan complete: 0 entries from 18 tokens"

**Förväntad:** 50-100 nya tokens varje scan

**Orsak:**
1. DexScreener.get_trending_tokens() returnerar förmodligen tom lista
2. Birdeye failar (ingen data i logg, ingen warning heller)
3. Fallback till hardcoded 18 tokens

**Varför DexScreener kanske failar:**
- API endpoint fel konfigurerad
- Returnerar data men extraherar inga tokens
- Tyst exception (ingen logging)

**Impact:** 🔴 KRITISK - Boten kan ALDRIG hitta nya möjligheter

---

### Problem 2: THRESHOLD 80+ ÄR OMÖJLIG UTAN MACD ⚠️⚠️⚠️

**Symptom:** "Score 0/100 (need 80+)"

**Vad som händer:**
- GAMLA MomentumEntry körs (kräver 80+)
- Försöker beräkna MACD (behöver 35 candles)
- Inga candles → MACD score = 0
- Volume score max ~20
- RSI score = 0 (inga candles)
- Pullback score = 0 (inga candles)
- **Total: Max 20/100, oftast 0/100**

**Förväntad:** SimpleMomentumEntry (threshold 60+, inga candles)

**Impact:** 🔴 KRITISK - ALLA tokens rejecteras även om momentum finns

---

### Problem 3: ÄNDRINGAR INTE I PRODUKTION ⚠️⚠️⚠️

**Produktion körs från:**
```
/root/momentum-runner-v2/new-bot-v2/
```

**Ändringar gjordes i:**
```
/home/user/solbottrad/new-bot-v2/
```

**→ OLIKA PLATSER! Produktionen har GAMMAL kod!**

**Impact:** 🔴 KRITISK - Allt jobb värdelöst om inte deployed

---

### Problem 4: LOGGING BUG I main.py

**I /home/user/solbottrad/new-bot-v2/src/main.py:379:**
```python
token_data["rejection_reason"] = f"Score {momentum_result['score']}/100 (need 80+)"
```

**Problem:** Hardcoded "need 80+" även fast SimpleMomentumEntry kräver 60+

**Impact:** 🟡 MEDIUM - Misleading logs, svårt att debugga

---

## EXAKT SPECIFIKATION AV VAS SOM MÅSTE FIXAS

### Fix 1: TOKEN DISCOVERY - GÖR DEXSCREENER ROBUST

**Fil:** `src/strategies/token_discovery.py`

**Nuvarande (line 74):**
```python
dex_tokens = self.dexscreener.get_trending_tokens(limit * 2)

if dex_tokens:
    all_tokens.update(dex_tokens)
    logger.info(f"✅ DexScreener (latest pairs): {len(dex_tokens)} tokens")
else:
    logger.warning("⚠️ DexScreener: No tokens")
```

**Problem:** Om get_trending_tokens() returnerar tom lista, ingen info varför.

**FIX:**
```python
logger.debug("Calling DexScreener.get_trending_tokens()...")
dex_tokens = self.dexscreener.get_trending_tokens(limit * 2)

logger.debug(f"DexScreener returned: {type(dex_tokens)}, length: {len(dex_tokens) if dex_tokens else 0}")

if dex_tokens:
    all_tokens.update(dex_tokens)
    logger.info(f"✅ DexScreener (latest pairs): {len(dex_tokens)} tokens")
    
    # Log first 3 tokens for verification
    for token in list(dex_tokens)[:3]:
        logger.debug(f"   Sample token: {token}")
else:
    logger.warning("⚠️ DexScreener returned NO TOKENS - check API response")
```

**Förväntad effekt:** Se varför DexScreener failar (tom response, exception, etc)

---

### Fix 2: DEXSCREENER CLIENT - VERIFIERA API CALL

**Fil:** `src/api/dexscreener_client.py:405`

**Nuvarande:**
```python
def get_trending_tokens(self, limit: int = 50) -> List[str]:
    try:
        url = self.endpoints.get("latest_pairs")
        result = self._make_request(url)
        
        if not result or "pairs" not in result:
            logger.warning("No trending data from DexScreener")
            return []
        
        pairs = result["pairs"]
        ...
```

**FIX - Lägg till debug logging:**
```python
def get_trending_tokens(self, limit: int = 50) -> List[str]:
    try:
        url = self.endpoints.get("latest_pairs")
        logger.debug(f"DexScreener URL: {url}")
        
        result = self._make_request(url)
        logger.debug(f"DexScreener response type: {type(result)}")
        
        if not result:
            logger.error("❌ DexScreener: Empty response")
            return []
        
        if "pairs" not in result:
            logger.error(f"❌ DexScreener: No 'pairs' key. Keys: {result.keys()}")
            return []
        
        pairs = result["pairs"]
        logger.debug(f"DexScreener: {len(pairs)} pairs in response")
        
        if not pairs:
            logger.warning("DexScreener: 'pairs' is empty array")
            return []
        
        # Extract base token addresses
        tokens = []
        for pair in pairs[:limit]:
            base_token = pair.get("baseToken", {})
            address = base_token.get("address")
            
            if address:
                tokens.append(address)
                logger.debug(f"   Extracted: {base_token.get('symbol', 'UNKNOWN')} ({address[:8]}...)")
        
        logger.info(f"✅ DexScreener: Extracted {len(tokens)} tokens from {len(pairs)} pairs")
        return tokens
```

**Förväntad effekt:** Se exakt vad som returneras från API

---

### Fix 3: ANVÄND SIMPLEMOMETUMENTRY (60+ threshold)

**Fil:** `src/main.py`

**Line 21 (redan korrekt):**
```python
from src.strategies.momentum_entry_simple import SimpleMomentumEntry
```

**Line 379 (FIX denna):**
```python
# FÖRE:
token_data["rejection_reason"] = f"Score {momentum_result['score']}/100 (need 80+)"

# EFTER:
threshold = momentum_result.get("threshold", 60)
token_data["rejection_reason"] = f"Score {momentum_result['score']}/100 (need {threshold}+)"
```

**Förväntad effekt:** Korrekt threshold i logs (60+ istället för 80+)

---

### Fix 4: VERIFIERA SIMPLEMOMETUMENTRY ANVÄNDS

**Fil:** `src/main.py`

**Somewhere in __init__ (line ~100-150):**

**FÖRE (om det står):**
```python
self.momentum_entry = MomentumEntry()
```

**EFTER:**
```python
self.momentum_entry = SimpleMomentumEntry()
logger.info("✅ Using SimpleMomentumEntry (threshold: 60+, real data only)")
```

---

### Fix 5: DEPLOY TILL RÄTT KATALOG

**Production directory:**
```
/root/momentum-runner-v2/new-bot-v2/
```

**Changes directory:**
```
/home/user/solbottrad/new-bot-v2/
```

**ALTERNATIV A: Kopiera ändringar**
```bash
# Backup production
cp -r /root/momentum-runner-v2/new-bot-v2 /root/momentum-runner-v2/new-bot-v2.backup.$(date +%Y%m%d_%H%M%S)

# Copy changed files
cp /home/user/solbottrad/new-bot-v2/src/strategies/momentum_entry_simple.py \
   /root/momentum-runner-v2/new-bot-v2/src/strategies/

cp /home/user/solbottrad/new-bot-v2/src/main.py \
   /root/momentum-runner-v2/new-bot-v2/src/

cp /home/user/solbottrad/new-bot-v2/src/strategies/token_discovery.py \
   /root/momentum-runner-v2/new-bot-v2/src/strategies/

cp /home/user/solbottrad/new-bot-v2/src/utils/token_data_gatherer.py \
   /root/momentum-runner-v2/new-bot-v2/src/utils/

# Restart bot
pkill -f "python.*main.py"
cd /root/momentum-runner-v2/new-bot-v2
nohup python3 main.py > bot_error.log 2>&1 &
```

**ALTERNATIV B: Symlink (farligt)**
```bash
# Risk för att productiondriectory är ett separat repo
```

**ALTERNATIV C: Git push/pull**
```bash
# Från development
cd /home/user/solbottrad
git add -A
git commit -m "FIX: SimpleMomentumEntry + DexScreener primary + Debug logging"
git push origin claude/new-bot-v2-momentum-U7y6l

# På production
cd /root/momentum-runner-v2/new-bot-v2
git pull origin claude/new-bot-v2-momentum-U7y6l

# Restart
pkill -f "python.*main.py"
nohup python3 main.py > bot_error.log 2>&1 &
```

---

## DEPLOYMENT CHECKLISTA

### Pre-deployment:
- [ ] Verify SimpleMomentumEntry exists in changes
- [ ] Verify main.py imports SimpleMomentumEntry
- [ ] Verify token_discovery.py has DexScreener primary
- [ ] Verify all logging bugs fixed
- [ ] Run syntax check: `python3 -m py_compile src/**/*.py`
- [ ] Run import test: `python3 -c "from src.main import MomentumBot"`

### Deployment:
- [ ] Backup production directory
- [ ] Stop current bot process
- [ ] Copy/pull changes to production
- [ ] Verify files copied correctly (checksums/diff)
- [ ] Start bot with logging: `nohup python3 main.py > bot_error.log 2>&1 &`

### Post-deployment verification:
- [ ] Check bot_error.log for startup errors
- [ ] Wait 1 scan cycle (~5 min)
- [ ] Verify: "TOKEN DISCOVERY - Target: 50 tokens" in logs
- [ ] Verify: "DexScreener (latest pairs): XX tokens" in logs (XX > 18)
- [ ] Verify: "Score XX/100 (need 60+)" in logs (not 80+)
- [ ] Verify: At least some tokens score 30-60+ (not all 0-15)

### Success criteria:
- ✅ Discovery finds 30+ unique tokens (not just 18)
- ✅ At least 1 token passes screening per 100 scanned
- ✅ Threshold shown as 60+ in logs
- ✅ Scores vary (0-100 range, not stuck at 0-15)

### Rollback plan:
```bash
# If it fails:
pkill -f "python.*main.py"
mv /root/momentum-runner-v2/new-bot-v2.backup.TIMESTAMP /root/momentum-runner-v2/new-bot-v2
cd /root/momentum-runner-v2/new-bot-v2
nohup python3 main.py > bot_error.log 2>&1 &
```

---

## FÖRVÄNTADE RESULTAT EFTER FIX

### Token Discovery:
**FÖRE:**
```
Scan complete: 0 entries from 18 tokens
```

**EFTER:**
```
🔍 TOKEN DISCOVERY - Target: 50 tokens
✅ DexScreener (latest pairs): 87 tokens
✅ Birdeye (trending): 24 tokens (12 unique)
📊 DISCOVERY COMPLETE: 50 unique tokens

✅ Scan complete: 2 entries from 50 tokens
```

### Momentum Scoring:
**FÖRE:**
```
Bonk (MOMENTUM) - Score 0/100 (need 80+)
$WIF (MOMENTUM) - Score 15/100 (need 80+)
```

**EFTER:**
```
Bonk (MOMENTUM) - Score 35/100 (need 60+)
$WIF (MOMENTUM) - Score 65/100 (need 60+) ← PASS!
PUMP (MOMENTUM) - Score 85/100 (need 60+) ← PASS!
🚀 MOMENTUM MATCH! Score: 85/100
   Breakdown: {'price_momentum': 40, 'volume_spike': 30, 'buy_pressure': 15, 'trend': 0}
```

### Trade Execution:
**FÖRE:**
```
0 entries, 0 trades
```

**EFTER:**
```
2-5 entries per 50 tokens
1-3 trades per day (baserat på volume/liquidity)
```

---

## SAMMANFATTNING

### VAD ÄR FEL:
1. 🔴 Discovery: Bara 18 hardcoded tokens (DexScreener failar tyst)
2. 🔴 Scoring: Threshold 80+ omöjlig utan MACD (alla tokens rejecteras)
3. 🔴 Deployment: Ändringar finns inte där produktionen körs
4. 🟡 Logging: Misleading "need 80+" i logs

### VAD SOM MÅSTE GÖRAS:
1. ✅ Lägg till debug logging i DexScreener client
2. ✅ Fix threshold logging i main.py (80+ → 60+)
3. ✅ Deploy SimpleMomentumEntry till produktion
4. ✅ Verifiera discovery hittar 30+ tokens
5. ✅ Verifiera scoring ger variation (inte bara 0-15)

### KOSTNAD HITTILLS:
- ~200 SEK i API calls/server
- ~10 timmar arbete
- 0 trades genomförda

### NEXT STEPS:
1. Applicera alla fixes ovan
2. Deploy till produktion
3. Monitorera loggar i 1 scan cycle
4. Verifiera discovery + scoring fungerar
5. Om funkar: Låt köra 24h och följ upp

