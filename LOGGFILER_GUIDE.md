# 📝 Loggfiler Guide - Solana Trading Bot

## ✅ RÄTT LOGGFIL ATT ANVÄNDA

**ALLTID använd denna fil:**
```bash
/root/solbottrad/trading_bot.log
```

## 🔧 Snabbkommandon

### Live Logs (realtid)
```bash
tail -f /root/solbottrad/trading_bot.log
```

### Senaste 100 raderna
```bash
tail -100 /root/solbottrad/trading_bot.log
```

### Sök efter Jupiter scanning
```bash
grep -i "jupiter\|multi-source\|enriching" /root/solbottrad/trading_bot.log | tail -20
```

### Se trading statistik
```bash
grep "Win Rate\|Total PnL" /root/solbottrad/trading_bot.log | tail -5
```

### Se positions (ENTERED/EXITED)
```bash
grep -E "ENTERED|EXITED|Position opened|Position closed" /root/solbottrad/trading_bot.log | tail -20
```

### Kolla rug detection
```bash
grep "DEAD TOKEN\|Rug detected" /root/solbottrad/trading_bot.log | tail -10
```

## 🗑️ GAMLA/FELAKTIGA LOGGFILER (kan ignoreras/raderas)

- `bot.log` - Gammal loggfil från tidigare version (KAN RADERAS)
- `bot_output.log` - Användes av gamla systemd-konfigurationen (KAN RADERAS)

## 🧹 Städa upp gamla loggar

```bash
cd /root/solbottrad

# Ta backup först (säkert!)
mkdir -p old_logs
mv bot.log old_logs/ 2>/dev/null
mv bot_output.log old_logs/ 2>/dev/null

# Eller radera direkt (om du är säker)
# rm -f bot.log bot_output.log
```

## 📊 Systemd Service Info

Service använder:
```
StandardOutput=append:/root/solbottrad/trading_bot.log
StandardError=append:/root/solbottrad/trading_bot.log
```

Kolla service status:
```bash
sudo systemctl status solana-trading-bot
```

Kolla systemd logs (om trading_bot.log saknas):
```bash
sudo journalctl -u solana-trading-bot -n 100 --no-pager
```

## 🎯 Snabbt Alias (valfritt)

Lägg till i `~/.bashrc` för enklare kommando:
```bash
alias botlog='tail -f /root/solbottrad/trading_bot.log'
alias botstats='grep "Win Rate\|Total PnL" /root/solbottrad/trading_bot.log | tail -5'
alias bottrades='grep -E "ENTERED|EXITED" /root/solbottrad/trading_bot.log | tail -20'
```

Sedan kan du bara skriva:
```bash
botlog        # Live logs
botstats      # Stats
bottrades     # Recent trades
```

## ✅ Sammanfattning

**EN LOGGFIL ATT KOMMA IHÅG:**
```
/root/solbottrad/trading_bot.log
```

**ETT KOMMANDO FÖR LIVE LOGS:**
```bash
tail -f /root/solbottrad/trading_bot.log
```

**Klart!** 🎉
