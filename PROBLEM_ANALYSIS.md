# KRITISK ANALYS - VARFÖR BOTEN INTE FUNGERAR

## PROBLEMET (Det Uppenbara)

Produktionsloggar visar:
```
Score 0/100 (need 80+)  ← GAMLA MomentumEntry (kräver 80+)
Scan complete: 0 entries from 18 tokens  ← BARA hardcoded tokens
```

**MITT SimpleMomentumEntry kräver 60+ poäng, INTE 80+**

Detta betyder: **MINA ÄNDRINGAR KÖRDES ALDRIG I PRODUKTION**

---

## ROOT CAUSE ANALYS

### Problem 1: OLIKA KATALOGER

**Produktion körs från:**
```
/root/momentum-runner-v2/new-bot-v2/
```

**Mina ändringar gjordes i:**
```
/home/user/solbottrad/new-bot-v2/
```

**→ DESSA ÄR OLIKA STÄLLEN! Ändringarna finns inte där boten körs!**

### Problem 2: VILKEN KOD KÖRS EGENTLIGEN?

Från loggen ser vi att produktionen FORTFARANDE använder:
- ❌ Gamla MomentumEntry (kräver 80+ poäng)
- ❌ Birdeye som primary source (failar)
- ❌ Gamla TokenDiscovery (hittar bara 18 tokens)
- ❌ MACD/RSI dependencies (därför 0 poäng)

---

## EXAKT VAD SOM HÄNDER I PRODUKTION

### Scanning-loop:

1. **TokenDiscovery** försöker hämta tokens:
   - Birdeye: FAILAR (ingen data i logg)
   - DexScreener: Används INTE som primary
   - Result: Fallback till 18 hardcoded tokens

2. **För varje token:**
   - Hämtar data OK (ser symbol, price, liquidity)
   - Några rejecteras: SAFETY (mint authority exists)
   - Resten går till momentum check

3. **Momentum scoring:**
   - GAMLA MomentumEntry körs
   - Försöker beräkna MACD (behöver 35 candles)
   - Inga candles → 0/100 score
   - Threshold är 80+ → REJECTED

4. **Result:** 0 trades, samma 18 tokens varje gång

---

## VARFÖR INGEN NY DISCOVERY

Från logg: "Scan complete: 0 entries from 18 tokens"

Detta betyder TokenDiscovery returnerar BARA 18 tokens, inte 50+.

**Troliga orsaker:**

1. **DexScreener inte primary:** get_trending_tokens() körs EFTER Birdeye
2. **Birdeye failar tyst:** Ingen data, ingen fallback till DexScreener  
3. **Gammal kod:** Mina ändringar (DexScreener primary) finns inte i prod

---

## VAD JAG GJORDE (Men som INTE är i produktion)

### Ändringar i /home/user/solbottrad/:

1. **momentum_entry_simple.py** - SKAPAD
   - Endast real DexScreener data
   - 60+ poäng threshold (ej 80+)
   - Inget MACD/RSI

2. **token_data_gatherer.py** - OMSKRIVEN
   - Ingen Birdeye client
   - Inga fake candles
   - Bara real data extraction

3. **main.py** - UPPDATERAD
   - from SimpleMomentumEntry (ej MomentumEntry)

4. **token_discovery.py** - UPPDATERAD (i annan repo?)
   - DexScreener PRIMARY
   - Birdeye SECONDARY

**DESSA ÄNDRINGAR FINNS INTE I /root/momentum-runner-v2/**

---

## SPECIFIKATION AV ÄNDRINGAR SOM BEHÖVS

### 1. TOKEN DISCOVERY (Kritiskt!)

**Problem:** Hittar bara 18 hardcoded tokens

**Lösning:**
```python
# token_discovery.py - get_tokens()

# FÖRE (nuvarande i prod):
birdeye_tokens = await birdeye.get_trending_tokens()  # FAILAR
dex_tokens = dexscreener.get_trending_tokens()  # Körs aldrig?
return fallback_tokens  # 18 tokens

# EFTER (vad som behövs):
dex_tokens = dexscreener.get_trending_tokens(limit=100)  # PRIMARY
all_tokens.update(dex_tokens)
try:
    birdeye_tokens = await birdeye.get_trending_tokens()  # BONUS
    all_tokens.update(birdeye_tokens)
except:
    pass  # OK if Birdeye fails
return list(all_tokens)[:50]
```

### 2. MOMENTUM SCORING (Kritiskt!)

**Problem:** MACD kräver 35 candles → 0/100 score för alla

**Lösning:**
```python
# Använd SimpleMomentumEntry:

def check_pattern(token_data):
    score = 0
    
    # Price momentum (40 pts)
    if token_data['price_change_5m'] >= 10:
        score += 20
    if token_data['price_change_1h'] >= 20:
        score += 20
    
    # Volume spike (30 pts)
    vol_ratio = token_data['volume_5m'] / (token_data['volume_1h'] / 12)
    if vol_ratio >= 6:
        score += 30
    
    # Buy pressure (20 pts)
    if token_data['buys_5m'] / token_data['sells_5m'] >= 3:
        score += 20
    
    # Trend (10 pts)
    if token_data['price_change_24h'] > 0:
        score += 10
    
    return score >= 60  # THRESHOLD 60, INTE 80
```

### 3. DATA GATHERING (Viktigt)

**Problem:** Försöker hämta candles från Birdeye (failar)

**Lösning:**
```python
# token_data_gatherer.py

# TA BORT:
- self.birdeye_client
- get_ohlcv_candles()
- get_price_history()

# BEHÅLL BARA:
- dexscreener_client.get_token_data()
- Extrahera real data (price, volume, buys, sells)
```

---

## NÄSTA STEG (VAD SOM MÅSTE GÖRAS)

### Steg 1: Identifiera rätt katalog

Produktionen körs från: `/root/momentum-runner-v2/new-bot-v2/`

Behöver verifiera:
- Är detta samma repo som holmgren100/solbottrad?
- Eller är det en separat klon?

### Steg 2: Applicera ändringar på RÄTT plats

Antingen:
A) Kopiera mina ändringar från /home/user/solbottrad/ till /root/momentum-runner-v2/
B) Eller ändra produktionen att köra från /home/user/solbottrad/

### Steg 3: Restart bot med nya ändringar

```bash
cd /root/momentum-runner-v2/new-bot-v2/
# Stoppa nuvarande bot
pkill -f "python.*main.py"
# Starta med nya ändringar
nohup python3 main.py > bot_error.log 2>&1 &
```

---

## SAMMANFATTNING

**Varför det inte fungerar:**
1. ❌ Produktion körs från annan katalog än där ändringar gjordes
2. ❌ TokenDiscovery använder inte DexScreener som primary
3. ❌ Momentum scoring kräver 80+ (omöjligt utan MACD)
4. ❌ MACD kräver candles som inte finns
5. ❌ Därför: 0/100 score för alla tokens
6. ❌ Därför: Inga trades, samma 18 tokens

**Vad som behövs:**
1. ✅ Identifiera rätt produktionskatalog
2. ✅ Applicera SimpleMomentumEntry där
3. ✅ Applicera DexScreener-primary TokenDiscovery
4. ✅ Ta bort Birdeye/MACD dependencies
5. ✅ Restart bot
6. ✅ Verifiera nya tokens hittas

**Förväntat resultat efter fix:**
- 50+ nya tokens varje scan (från DexScreener)
- Tokens får 0-100 score baserat på REAL data
- Tokens med 60+ score → TRADE
- Threshold uppnåbar (inte omöjlig 80+)

