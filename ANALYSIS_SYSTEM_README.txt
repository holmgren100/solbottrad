╔════════════════════════════════════════════════════════════════════╗
║                   ANALYSIS SYSTEM - USAGE GUIDE                    ║
║               För kontinuerlig optimering med Gemini               ║
╚════════════════════════════════════════════════════════════════════╝

📊 ÖVERSIKT
═══════════════════════════════════════════════════════════════════════
Detta system skapar en feedback loop mellan:
  Boten → CSV Data → Claude Code → Gemini AI → Implementering

Målet: "Info base kretslopp" för datadriven optimering utan copy/paste


🔧 TILLGÄNGLIGA SCRIPTS
═══════════════════════════════════════════════════════════════════════

1. check_bot_status.sh
   └─ Diagnostik av botens status
   └─ Kör: ./check_bot_status.sh
   └─ Visar:
      • Är boten aktiv eller stoppad?
      • Nätverksproblem?
      • Senaste trading aktivitet
      • CSV filer status
      • Analysis system status

2. create_snapshot.sh
   └─ Tar snapshot av loggfiler
   └─ Output: analysis/live/latest_snapshot.txt
   └─ Innehåller:
      • Errors/warnings
      • Senaste trades
      • Nuclear stops
      • Step-up tiers
      • Moonshot exceptions
      • Incubator triggers

3. create_summaries.sh
   └─ Skapar summaries från CSV data
   └─ Output: analysis/summaries/*.txt
   └─ Innehåller:
      • Latest 50 trades
      • Performance summary (win rate, avg profit, etc)
      • Rejected tokens
      • Moonshot exceptions
      • Incubator trades

4. analysis_pipeline.sh
   └─ MASTER SCRIPT - kör allt!
   └─ Kör: ./analysis_pipeline.sh
   └─ Steg:
      1. Creates snapshots
      2. Creates summaries
      3. Generates Python insights
   └─ Output: analysis/insights/latest_insights.txt

5. prepare_gemini_input.sh
   └─ Förbereder data för Gemini analys
   └─ Output: analysis/gemini_input.txt
   └─ Används för feedback loop med Gemini


📋 TYPISKA WORKFLOWS
═══════════════════════════════════════════════════════════════════════

WORKFLOW 1: Snabb Status Check
────────────────────────────────────────────────────────────────────
./check_bot_status.sh

  → Visar om boten trader eller har problem
  → Första steget när du undrar "fungerar det?"


WORKFLOW 2: Ge Claude Kontext (utan copy/paste!)
────────────────────────────────────────────────────────────────────
./analysis_pipeline.sh

  → Skapar alla summaries och insights
  → Claude kan sedan läsa:
     - analysis/live/latest_snapshot.txt
     - analysis/summaries/*.txt
     - analysis/insights/latest_insights.txt

  → Nu kan Claude se hela kontexten utan att du behöver copy/paste!


WORKFLOW 3: Gemini Feedback Loop
────────────────────────────────────────────────────────────────────
1. ./prepare_gemini_input.sh
2. cat analysis/gemini_input.txt
3. Copy output till Gemini
4. Fråga Gemini: "Analyze this trading data and suggest optimizations"
5. Copy Gemini's svar
6. Ge till Claude: "Implement these Gemini suggestions: [paste]"

  → Kontinuerlig optimering: Bot → Data → Gemini → Claude → Bot


WORKFLOW 4: Djup Analys av Feature
────────────────────────────────────────────────────────────────────
Exempel: "Fungerar Moonshot exceptions?"

1. ./analysis_pipeline.sh
2. Fråga Claude: "Read the analysis files and tell me about moonshot
   exceptions performance"
3. Claude läser:
   - analysis/summaries/moonshots.txt
   - analysis/insights/latest_insights.txt
   - Söker i CSV för pattern matching
4. Claude ger insights baserat på ACTUAL DATA istället för gissningar


🎯 NUVARANDE STATUS
═══════════════════════════════════════════════════════════════════════

Systemet är KLART men VÄNTAR på trading data.

Problem: Bot har nätverksproblem (DNS resolution failure)
         → Kan inte nå Jupiter/DexScreener/CoinGecko APIs
         → Ingen trading = ingen data att analysera

När nätverket fixas:
  ✅ Bot börjar trade
  ✅ CSV filer skapas (ml_trades.csv)
  ✅ Analysis scripts får data att jobba med
  ✅ Du kan köra alla workflows ovan!


💡 TIPS
═══════════════════════════════════════════════════════════════════════

• Kör check_bot_status.sh regelbundet för att se att allt funkar
• Efter många trades, kör analysis_pipeline.sh för full context
• Använd Gemini feedback loop för stora optimeringar
• Claude kan läsa analysis/ filerna direkt - ingen copy/paste behövs!


🚨 TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════

Problem: "No trades yet"
  → Kör check_bot_status.sh för att se varför
  → Troligen nätverksproblem eller bot stoppad

Problem: "CSV not found"
  → Normal om boten inte stängt några positioner än
  → CSV skapas första gången en position stängs

Problem: Analysis script errors
  → Kör: chmod +x *.sh
  → Kolla att analysis/ directories finns:
     mkdir -p analysis/live
     mkdir -p analysis/summaries
     mkdir -p analysis/insights


📁 DIRECTORY STRUKTUR
═══════════════════════════════════════════════════════════════════════

/home/user/solbottrad/
├── data/
│   ├── ml_trades.csv          ← Alla trades (skapas av bot)
│   └── rejected_trades.csv    ← Rejected tokens
├── analysis/
│   ├── live/
│   │   └── latest_snapshot.txt    ← Log snapshots
│   ├── summaries/
│   │   ├── latest_trades.txt      ← Senaste 50 trades
│   │   ├── performance.txt        ← Win rate, avg profit
│   │   ├── rejected.txt           ← Rejected tokens
│   │   ├── moonshots.txt          ← Moonshot exceptions
│   │   └── incubator.txt          ← Incubator trades
│   ├── insights/
│   │   └── latest_insights.txt    ← Python-genererade insights
│   └── gemini_input.txt           ← För Gemini analys
├── check_bot_status.sh        ← Diagnostik
├── create_snapshot.sh         ← Snapshot creator
├── create_summaries.sh        ← Summary creator
├── analysis_pipeline.sh       ← MASTER SCRIPT
└── prepare_gemini_input.sh    ← Gemini input prep


═══════════════════════════════════════════════════════════════════════
Systemet är redo! 🚀
Väntar bara på att boten ska börja trade.
═══════════════════════════════════════════════════════════════════════
