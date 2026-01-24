# 🤖 Claude Code Access Guide
*Ge Claude Code full åtkomst till din trading bot på Digital Ocean*

---

## 🎯 Översikt

Claude Code KAN INTE direkt SSH:a till externa servrar, men kan använda:
- ✅ **HTTP/HTTPS** via WebFetch tool
- ✅ **REST APIs** för data och kontroll
- ✅ **MCP (Model Context Protocol)** för avancerad integration

---

## 📡 METOD 1: HTTP API (Rekommenderat!)

### **Setup:**

1. **Installera Bot API:**
   ```bash
   cd /home/user/solbottrad
   chmod +x setup_bot_api.sh
   sudo ./setup_bot_api.sh
   ```

2. **Sätt säkert lösenord:**
   ```bash
   nano bot_api.py
   # Ändra: USERS = {"claude": "ditt_säkra_lösenord"}
   ```

3. **Starta API:**
   ```bash
   sudo systemctl restart bot-api
   sudo systemctl status bot-api
   ```

### **Claude Code Användning:**

Ge Claude Code denna URL:
```
http://claude:YOUR_PASSWORD@209.38.229.243:8765/api/status
```

Claude kan då använda:
```python
# I Claude Code session:
WebFetch("http://claude:PASSWORD@209.38.229.243:8765/api/status",
         "Analyze bot performance and suggest improvements")
```

### **Tillgängliga Endpoints:**

| Endpoint | Beskrivning | Auth |
|----------|-------------|------|
| `GET /health` | Health check | ❌ No |
| `GET /api/status` | Bot status, positions, stats | ✅ Yes |
| `GET /api/data/trades` | Get trades CSV (JSON or CSV) | ✅ Yes |
| `GET /api/data/rejected` | Get rejected trades | ✅ Yes |
| `GET /api/data/logs` | Get recent logs | ✅ Yes |
| `GET /api/analysis/session` | Session analysis | ✅ Yes |
| `GET /api/control/config` | Get bot config (redacted) | ✅ Yes |

**Query Parameters:**
- `?limit=50` - Limit results
- `?format=csv` - Return CSV instead of JSON
- `?lines=200` - Number of log lines
- `?level=error` - Filter logs by level

---

## 🔒 METOD 2: Nginx Reverse Proxy (Produktion)

För **säkrare** setup med SSL:

```bash
# 1. Setup nginx
sudo ./setup_nginx_csv.sh

# 2. Lägg till SSL (Let's Encrypt)
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d botapi.dindomain.com

# 3. Konfigurera reverse proxy till port 8765
# (nginx config kommer vara i /etc/nginx/sites-available/)
```

Då får du:
```
https://claude:PASSWORD@botapi.dindomain.com/api/status
```

---

## 🚀 METOD 3: MCP Server (Avancerat)

För **strukturerad data** och **real-time streaming**:

### **Fördelar med MCP:**
- ✅ Type-safe data queries
- ✅ Real-time WebSocket updates
- ✅ Function calls (start/stop bot, change config)
- ✅ Streaming logs
- ✅ Native Claude Code integration

### **Setup:**
```bash
# Installera MCP SDK
pip3 install mcp anthropic-mcp

# Skapa MCP server config
# (script kommer att genereras om du vill ha detta)
```

**MCP ger Claude Code "superpowers":**
- Query specifik data med typsäkerhet
- Real-time notifikationer vid nya trades
- Direkta function calls för bot-kontroll
- Streaming av logs

**Men kräver:**
- WebSocket server setup
- MCP protocol implementation
- Mer komplext än HTTP

---

## 💡 Rekommenderad Workflow

### **För Live Monitoring:**

1. **Starta Bot API** (Metod 1)
2. **Ge Claude Code URL:en** med credentials
3. **Claude kan nu:**
   - Hämta status varje timme
   - Analysera session results
   - Föreslå optimeringar baserat på data
   - Läsa logs för debugging

### **Exempel Claude Code Session:**

```
User: "Analyze bot performance from droplet"

Claude: *Uses WebFetch to get /api/analysis/session*
        "I can see your bot has:
         - 45% win rate (up from 42.4%!)
         - Total P/L: +$127
         - Nuclear stops: 5 trades, avg -23%
         - Best trade: DOGE +847%

         Issues I notice:
         1. Nuclear stops still hitting -23% (target -20%)
         2. Missing moonshots in mature tokens

         Let me check rejected trades..."

        *Uses WebFetch to get /api/data/rejected?limit=50*

        "I found the problem! You're rejecting tokens with
         'bluechip_age' that are actually good breakout candidates.

         Recommendation: Remove bluechip age filter for tokens
         with LP burned + high volume spike."
```

---

## 🔐 Säkerhet

### **VIKTIGT:**

1. **Ändra default lösenord** i bot_api.py
2. **Använd stark auth** (minst 20 tecken)
3. **Begränsa IP-access** (ufw firewall):
   ```bash
   sudo ufw allow from YOUR_IP to any port 8765
   ```
4. **Använd SSL** i produktion (certbot)
5. **Logga API calls** för audit trail

### **För Max Säkerhet:**

```bash
# Allow endast localhost (använd SSH tunnel)
# I bot_api.py: app.run(host='127.0.0.1', ...)

# SSH tunnel från din maskin:
ssh -L 8765:localhost:8765 root@209.38.229.243

# Claude Code når då via localhost
```

---

## 📊 AI-Styrning & Bevakning (Din Fråga)

### **Möjliga Scenarios:**

#### **1. Auto-Optimization:**
```python
# Claude Code kan:
# 1. Hämta session data varje timme
# 2. Analysera win rate, P/L patterns
# 3. Föreslå parameter-ändringar
# 4. Du godkänner → Claude uppdaterar config
# 5. Bot startar om med nya settings
```

#### **2. Real-Time Alerts:**
```python
# MCP streaming:
# - Bot hittar moonshot kandidat
# - Skickar real-time till Claude Code
# - Claude analyserar mot historisk data
# - Bekräftar eller avvisar entry
# - Bot agerar på signal
```

#### **3. Continuous Learning:**
```python
# Efter varje session:
# 1. Claude läser alla trades
# 2. Identifierar patterns (vad funkade/missade)
# 3. Uppdaterar "lessons learned" dokument
# 4. Föreslår konkreta code changes
# 5. Du godkänner → implementeras nästa session
```

### **Exempel: Gemini + Claude Feedback Loop**

```
18:00 - Session ends
18:01 - Claude fetches /api/analysis/session
18:02 - Claude analyzes: "Win rate down to 38%, nuclear stops up"
18:03 - Claude checks /api/data/rejected: "Missed PEPE 1,200%"
18:05 - Claude: "Problem found: Entry filters too strict"
18:06 - Claude generates fix (code patch)
18:07 - You review and approve
18:08 - Git commit + push
18:09 - Bot pulls changes
18:10 - Bot restarts with fix
18:15 - Next session starts with optimized filters
```

---

## 🎯 Nästa Steg

**Välj din metod:**

1. **Quick Start** (5 min):
   ```bash
   sudo ./setup_bot_api.sh
   # Ger Claude Code basic access
   ```

2. **Production Ready** (30 min):
   ```bash
   sudo ./setup_nginx_csv.sh
   # SSL + reverse proxy
   ```

3. **Advanced** (2h):
   ```bash
   # MCP server implementation
   # Real-time streaming + function calls
   ```

**Rekommendation:** Börja med **Quick Start** (Metod 1), testa workflow, uppgradera till produktion senare.

---

## 🆘 Troubleshooting

### **API startar inte:**
```bash
sudo journalctl -u bot-api -f
# Check errors
```

### **Connection refused:**
```bash
# Check firewall
sudo ufw status
sudo ufw allow 8765/tcp
```

### **Claude Code kan inte nå API:**
```bash
# Test från annan maskin
curl http://209.38.229.243:8765/health
# Ska returnera: {"status":"ok","timestamp":"..."}
```

### **Authentication fails:**
```bash
# Check credentials i bot_api.py
grep "USERS = " /home/user/solbottrad/bot_api.py
```

---

## 📚 Resources

- Flask API Docs: https://flask.palletsprojects.com/
- MCP Protocol: https://modelcontextprotocol.io/
- Claude Code WebFetch: https://docs.anthropic.com/claude/docs/

---

**Frågor? Problem? Säg bara till!** 🚀
