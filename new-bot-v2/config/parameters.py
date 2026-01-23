"""
Fearless Momentum Runner v2.0 - Trading Parameters

All parameters for the momentum trading bot.
Parameters marked with "# ADJUSTABLE" can be optimized by AI/backtesting.
"""

# ============================================================================
# ENTRY LOGIC PARAMETERS
# ============================================================================

# Momentum Pattern Scoring (need 80/100 to enter)
MOMENTUM_SCORE_THRESHOLD = 80  # ADJUSTABLE - minimum score to enter trade

# A) MACD Parameters (40 points max - MOST IMPORTANT!)
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
MACD_HISTOGRAM_POSITIVE_POINTS = 20  # Points if histogram > 0
MACD_HISTOGRAM_GROWING_POINTS = 20   # Points if growing for 3 candles
MACD_GROWING_STREAK_MIN = 3          # ADJUSTABLE - candles needed for "growing"

# B) Volume Spike Parameters (30 points max)
VOLUME_VELOCITY_THRESHOLD = 4.0      # ADJUSTABLE - 400% spike = 30 points
VOLUME_SPIKE_POINTS = 30             # Points for volume spike

# C) RSI Parameters (20 points max)
RSI_PERIOD = 14
RSI_MIN_SWEET_SPOT = 40             # ADJUSTABLE - lower bound of sweet spot
RSI_MAX_SWEET_SPOT = 70             # ADJUSTABLE - upper bound of sweet spot
RSI_SWEET_SPOT_POINTS = 10          # Points if RSI in sweet spot
RSI_RISING_POINTS = 10              # Points if RSI is rising

# D) Pullback Parameters (10 points max)
PULLBACK_RED_CANDLES_MIN = 1        # Minimum red candles before green
PULLBACK_RED_CANDLES_MAX = 2        # Maximum red candles for valid pullback
PULLBACK_POINTS = 10                # Points for pullback confirmation

# ============================================================================
# SAFETY CHECKS (Binary - must pass both)
# ============================================================================

LP_BURNED_REQUIRED = True            # LP must be burned
MINT_REVOKED_REQUIRED = True         # Mint authority must be revoked

# ============================================================================
# TREND CONFIRMATION PARAMETERS
# ============================================================================

TREND_MIN_GREEN_CANDLES = 2          # ADJUSTABLE - min green candles in recent history
TREND_HIGHER_HIGHS_REQUIRED = True   # Must be making higher highs
TREND_HIGHER_LOWS_REQUIRED = True    # Must be making higher lows
TREND_VOLUME_INCREASING = True       # Volume should increase with price

# ============================================================================
# ANTI-FOMO PARAMETERS
# ============================================================================

FOMO_RSI_OVERBOUGHT = 80            # ADJUSTABLE - block if RSI > this
FOMO_MAX_CONSECUTIVE_GREEN = 4      # ADJUSTABLE - block if 4+ green candles
FOMO_MAX_PUMP_PERCENT = 15          # ADJUSTABLE - block if 15%+ pump in 1 min without pullback

# ============================================================================
# POSITION MANAGEMENT
# ============================================================================

# Entry
POSITION_SIZE_PERCENT = 40           # ADJUSTABLE - 40% of available capital (fearless!)
ENTRY_AMOUNT_SOL = 0.1              # ADJUSTABLE - SOL per trade
HARD_STOP_LOSS_PERCENT = -25        # -25% hard stop (broad - give room!)

# Breakeven (at +50% profit)
BREAKEVEN_TRIGGER_PERCENT = 50       # ADJUSTABLE - when to hit breakeven
BREAKEVEN_SELL_PERCENT = 40          # ADJUSTABLE - sell 40% at breakeven
BREAKEVEN_STOP_OFFSET = 2            # Move stop to entry + 2%

# Pyramiding
PYRAMID_1_TRIGGER = 150              # ADJUSTABLE - at +150% profit
PYRAMID_1_SIZE = 30                  # ADJUSTABLE - add 30% more capital
PYRAMID_2_TRIGGER = 300              # ADJUSTABLE - at +300% profit
PYRAMID_2_SIZE = 20                  # ADJUSTABLE - add 20% more capital

# Partial Profits
PARTIAL_PROFIT_1_TRIGGER = 500       # ADJUSTABLE - at +500%
PARTIAL_PROFIT_1_SELL = 30           # ADJUSTABLE - sell 30%
PARTIAL_PROFIT_2_TRIGGER = 1000      # ADJUSTABLE - at +1000%
PARTIAL_PROFIT_2_SELL = 30           # ADJUSTABLE - sell 30%
MOON_BAG_PERCENT = 40                # 40% rides to 1700%+

# ============================================================================
# EXIT LOGIC PARAMETERS
# ============================================================================

# Weakness Score (exit if >= 70)
WEAKNESS_SCORE_THRESHOLD = 70        # ADJUSTABLE - exit threshold
WEAKNESS_MACD_SHRINKING_POINTS = 30  # Points if MACD histogram shrinking
WEAKNESS_MACD_SHRINKING_CANDLES = 2  # ADJUSTABLE - candles for "shrinking"
WEAKNESS_VOLUME_DECLINING_POINTS = 25  # Points if volume declining
WEAKNESS_VOLUME_DECLINE_PERCENT = 30   # ADJUSTABLE - 30%+ decline
WEAKNESS_VOLUME_DECLINE_CANDLES = 3    # ADJUSTABLE - over 3 candles
WEAKNESS_RSI_DIVERGENCE_POINTS = 25    # Points for bearish RSI divergence
WEAKNESS_SELL_PRESSURE_POINTS = 20     # Points if sells >> buys
WEAKNESS_SELL_MULTIPLIER = 3.0         # ADJUSTABLE - sells 3x buys

# Time-Based Exit
TIME_EXIT_ENABLED = True             # Enable time-based exits
TIME_EXIT_MIN_MINUTES = 3            # ADJUSTABLE - min time in position
TIME_EXIT_MIN_MOVEMENT = 5           # ADJUSTABLE - min 5% movement required

# Trailing Stop (for big winners)
TRAILING_STOP_ACTIVATION = 100       # ADJUSTABLE - activate at +100% profit
TRAILING_STOP_PERCENT = 30           # ADJUSTABLE - trail 30% from highest

# ============================================================================
# TECHNICAL INDICATOR SETTINGS
# ============================================================================

# Candle Timeframes
CANDLE_TIMEFRAME = "1m"              # Use 1-minute candles
CANDLE_LOOKBACK = 100                # Load last 100 candles for calculations

# Moving Averages
MA_SHORT_PERIOD = 7                  # ADJUSTABLE - for trend detection
MA_LONG_PERIOD = 25                  # ADJUSTABLE - for trend detection

# ============================================================================
# API RATE LIMITING
# ============================================================================

API_TIMEOUT_SECONDS = 10             # Timeout for API calls
API_MAX_RETRIES = 3                  # Maximum retry attempts
API_RETRY_DELAY = 2                  # Seconds between retries

# DexScreener Rate Limits
DEXSCREENER_REQUESTS_PER_MINUTE = 30  # Free tier limit
DEXSCREENER_BATCH_SIZE = 10           # Tokens per batch request

# ============================================================================
# LOGGING & DATA COLLECTION
# ============================================================================

# CSV File Paths
ML_TRADES_CSV = "data/ml_trades.csv"
REJECTED_TRADES_CSV = "data/rejected_trades.csv"
TRADE_HISTORY_CSV = "data/trade_history_all.csv"

# Log Levels
LOG_LEVEL_CONSOLE = "INFO"           # Console logging level
LOG_LEVEL_FILE = "DEBUG"             # File logging level

# ============================================================================
# RISK MANAGEMENT
# ============================================================================

MAX_CONCURRENT_POSITIONS = 5         # ADJUSTABLE - max open positions
MAX_DAILY_LOSS_PERCENT = 50         # ADJUSTABLE - stop trading if -50% for day
MAX_POSITION_SIZE_SOL = 1.0         # ADJUSTABLE - max size per position

# ============================================================================
# DISCOVERY & SCANNING
# ============================================================================

DISCOVERY_TOKEN_LIMIT = 50           # Scan top 50 trending tokens
SCAN_INTERVAL_SECONDS = 120          # ADJUSTABLE - scan every 2 minutes (long cycle to catch all tokens)
POSITION_UPDATE_INTERVAL = 15        # CRITICAL - update positions every 15 seconds (fast for momentum)
MIN_LIQUIDITY_USD = 50000            # Minimum liquidity to consider
MIN_VOLUME_24H_USD = 100000          # Minimum 24h volume to consider

# ============================================================================
# MAIN LOOP & HEALTH
# ============================================================================

HEALTH_CHECK_INTERVAL_SEC = 300      # Health check every 5 minutes
MAX_SCAN_RETRIES = 3                 # Retry on scan failure
SCAN_RETRY_DELAY_SEC = 10            # Wait between retries
DEFAULT_POSITION_SIZE_SOL = 0.1      # Default trade size

# ============================================================================
# NOTIFICATIONS
# ============================================================================

TELEGRAM_ENABLED = True              # Enable Telegram notifications
NOTIFY_ON_ENTRY = True               # Notify on entry signals
NOTIFY_ON_EXIT = True                # Notify on exit signals
NOTIFY_ON_BREAKEVEN = True           # Notify on breakeven triggers
NOTIFY_ON_PYRAMID = True             # Notify on pyramid adds
NOTIFY_ON_PARTIAL = True             # Notify on partial profits
NOTIFY_ON_ERROR = True               # Notify on errors

# ============================================================================
# PARAMETER SUMMARY
# ============================================================================

def get_parameter_summary():
    """Get a summary of all key parameters."""
    return {
        "entry": {
            "momentum_score_threshold": MOMENTUM_SCORE_THRESHOLD,
            "macd_growing_streak": MACD_GROWING_STREAK_MIN,
            "volume_velocity_threshold": VOLUME_VELOCITY_THRESHOLD,
            "rsi_sweet_spot": f"{RSI_MIN_SWEET_SPOT}-{RSI_MAX_SWEET_SPOT}",
        },
        "position": {
            "entry_size": f"{POSITION_SIZE_PERCENT}%",
            "entry_amount_sol": ENTRY_AMOUNT_SOL,
            "hard_stop": f"{HARD_STOP_LOSS_PERCENT}%",
            "breakeven_trigger": f"+{BREAKEVEN_TRIGGER_PERCENT}%",
        },
        "exit": {
            "weakness_threshold": WEAKNESS_SCORE_THRESHOLD,
            "time_exit_minutes": TIME_EXIT_MIN_MINUTES,
            "trailing_stop": f"{TRAILING_STOP_PERCENT}%",
        },
        "risk": {
            "max_positions": MAX_CONCURRENT_POSITIONS,
            "max_daily_loss": f"{MAX_DAILY_LOSS_PERCENT}%",
        }
    }


# ============================================================================
# ADJUSTABLE PARAMETERS LIST (for AI optimization)
# ============================================================================

ADJUSTABLE_PARAMETERS = [
    "MOMENTUM_SCORE_THRESHOLD",
    "MACD_GROWING_STREAK_MIN",
    "VOLUME_VELOCITY_THRESHOLD",
    "RSI_MIN_SWEET_SPOT",
    "RSI_MAX_SWEET_SPOT",
    "TREND_MIN_GREEN_CANDLES",
    "FOMO_RSI_OVERBOUGHT",
    "FOMO_MAX_CONSECUTIVE_GREEN",
    "FOMO_MAX_PUMP_PERCENT",
    "POSITION_SIZE_PERCENT",
    "ENTRY_AMOUNT_SOL",
    "BREAKEVEN_TRIGGER_PERCENT",
    "BREAKEVEN_SELL_PERCENT",
    "PYRAMID_1_TRIGGER",
    "PYRAMID_1_SIZE",
    "PYRAMID_2_TRIGGER",
    "PYRAMID_2_SIZE",
    "PARTIAL_PROFIT_1_TRIGGER",
    "PARTIAL_PROFIT_1_SELL",
    "PARTIAL_PROFIT_2_TRIGGER",
    "PARTIAL_PROFIT_2_SELL",
    "WEAKNESS_SCORE_THRESHOLD",
    "WEAKNESS_MACD_SHRINKING_CANDLES",
    "WEAKNESS_VOLUME_DECLINE_PERCENT",
    "WEAKNESS_VOLUME_DECLINE_CANDLES",
    "WEAKNESS_SELL_MULTIPLIER",
    "TIME_EXIT_MIN_MINUTES",
    "TIME_EXIT_MIN_MOVEMENT",
    "TRAILING_STOP_ACTIVATION",
    "TRAILING_STOP_PERCENT",
    "MA_SHORT_PERIOD",
    "MA_LONG_PERIOD",
    "MAX_CONCURRENT_POSITIONS",
    "MAX_DAILY_LOSS_PERCENT",
    "MAX_POSITION_SIZE_SOL",
    "SCAN_INTERVAL_SECONDS",
    "POSITION_UPDATE_INTERVAL",
]
