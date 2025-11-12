# trading/gmgn_trader.py
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import csv
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError

from utils.logger import setup_logger
from config.settings import settings
from exceptions.custom_exceptions import TradingError
from api.dexscreener_api import DexScreenerAPI


class GMGNTrader:
    """
    Trading implementation using GMGN bot via Telegram (live) or Dry Run simulator.
    """

    def __init__(self):
        self.logger = setup_logger(__name__, log_file="logs/trading.gmgn_trader.log")

        # Settings
        self.position_size = settings.DEFAULT_POSITION_SIZE
        self.slippage = settings.DEFAULT_SLIPPAGE
        self.priority_fee = settings.DEFAULT_PRIORITY_FEE
        self.bot_username = settings.GMGN_BOT_USERNAME
        self.chat_id = settings.TELEGRAM_CHAT_ID

        # Live path: Telegram bot (initialized even if DRY_RUN just to be safe)
        try:
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        except Exception as e:
            raise TradingError(f"Failed to initialize Telegram bot: {e}")

        # Dry run state
        self.paper_sol = Decimal(str(settings.PAPER_SOL_BALANCE))
        self.positions: Dict[str, Dict[str, Decimal]] = {}  # token -> {"amount_sol": Decimal, "avg_price": Decimal}
        self.realized_pnl = Decimal("0")
        self.dex = DexScreenerAPI()
        self._journal_path = Path(settings.TRADE_JOURNAL_PATH)

        self.logger.info(
            f"GMGNTrader ready | DRY_RUN={settings.DRY_RUN} | "
            f"position_size=${self.position_size} slippage={self.slippage}% fee={self.priority_fee}"
        )

    async def execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unified entrypoint used by the strategy/main.
        signal should include: type ('buy'|'sell'), token (symbol or address), amount or amount_sol (float).
        """
        side = str(signal.get("type", "buy")).lower()
        token = signal.get("token")
        amount = signal.get("amount") or signal.get("amount_sol") or settings.DEFAULT_BUY_AMOUNT
        price = signal.get("price")  # optional

        if not token:
            raise TradingError("Trade signal missing 'token'")

        if settings.DRY_RUN:
            return await self._simulate_trade(side, token, float(amount), price)
        else:
            if side == "buy":
                return await self.buy_token(token, float(amount))
            else:
                return await self.sell_token(token, float(amount))

    async def buy_token(self, token_symbol: str, amount: float) -> Dict[str, Any]:
        """Live path: send buy to GMGN via Telegram."""
        try:
            if amount > self.position_size:
                self.logger.warning(f"Buy amount ${amount} exceeds default position size ${self.position_size}")

            command = f"/buy {token_symbol} {amount}"
            await self.bot.send_message(chat_id=self.chat_id, text=command)

            tx = {
                "type": "buy",
                "token": token_symbol,
                "amount": amount,
                "price": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "sent",
                "slippage": self.slippage,
                "priority_fee": self.priority_fee,
                "dry_run": False,
            }
            self.logger.info(f"Buy command sent: {token_symbol} amount={amount}")
            return tx

        except TelegramError as e:
            raise TradingError(f"Telegram error during buy: {e}")
        except Exception as e:
            raise TradingError(f"Buy failed for {token_symbol}: {e}")

    async def sell_token(self, token_symbol: str, amount: float) -> Dict[str, Any]:
        """Live path: send sell to GMGN via Telegram."""
        try:
            command = f"/sell {token_symbol} {amount}"
            await self.bot.send_message(chat_id=self.chat_id, text=command)

            tx = {
                "type": "sell",
                "token": token_symbol,
                "amount": amount,
                "price": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "sent",
                "slippage": self.slippage,
                "priority_fee": self.priority_fee,
                "dry_run": False,
            }
            self.logger.info(f"Sell command sent: {token_symbol} amount={amount}")
            return tx

        except TelegramError as e:
            raise TradingError(f"Telegram error during sell: {e}")
        except Exception as e:
            raise TradingError(f"Sell failed for {token_symbol}: {e}")

    async def get_balance(self, token_symbol: Optional[str] = None) -> Dict[str, Any]:
        try:
            command = "/balance"
            if token_symbol:
                command += f" {token_symbol}"
            await self.bot.send_message(chat_id=self.chat_id, text=command)
            return {
                "status": "query_sent",
                "token": token_symbol if token_symbol else "all",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except TelegramError as e:
            raise TradingError(f"Telegram error during balance query: {e}")
        except Exception as e:
            raise TradingError(f"Failed to get balance: {e}")

    # ------------- Dry Run helpers -------------

    async def _get_price(self, token: str) -> Decimal:
        try:
            data = await self.dex.get_market_data(token)
            price = data.get("price")
            if price is None:
                raise ValueError("No price in market data")
            return Decimal(str(price))
        except Exception as e:
            self.logger.warning(f"Price fetch failed for {token}: {e}")
            return Decimal("1")

    async def _simulate_trade(self, side: str, token: str, amount_sol: float, price: Any) -> Dict[str, Any]:
        amount_dec = Decimal(str(amount_sol))
        px = Decimal(str(price)) if price is not None else await self._get_price(token)
        slip = Decimal(str(settings.DEFAULT_SLIPPAGE)) / Decimal("100")
        exec_price = px * (Decimal("1") + slip) if side == "buy" else px * (Decimal("1") - slip)

        if side == "buy":
            if amount_dec > self.paper_sol:
                self.logger.warning(f"[DRY RUN] Insufficient SOL. Have {self.paper_sol}, need {amount_dec}. Skipping.")
                return {"type": "buy", "token": token, "skipped": True, "reason": "insufficient_balance", "dry_run": True}
            self.paper_sol -= amount_dec
            pos = self.positions.get(token, {"amount_sol": Decimal("0"), "avg_price": Decimal("0")})
            new_amount = pos["amount_sol"] + amount_dec
            new_avg = (pos["amount_sol"] * pos["avg_price"] + amount_dec * exec_price) / new_amount
            self.positions[token] = {"amount_sol": new_amount, "avg_price": new_avg}
        else:
            pos = self.positions.get(token)
            if not pos or pos["amount_sol"] <= 0:
                self.logger.warning(f"[DRY RUN] No position for {token} to sell. Skipping.")
                return {"type": "sell", "token": token, "skipped": True, "reason": "no_position", "dry_run": True}
            sell_size = min(pos["amount_sol"], amount_dec)
            pnl = sell_size * (exec_price - pos["avg_price"])
            self.realized_pnl += pnl
            pos["amount_sol"] -= sell_size
            self.paper_sol += sell_size
            if pos["amount_sol"] <= 0:
                del self.positions[token]
            else:
                self.positions[token] = pos

        result = {
            "type": side,
            "token": token,
            "amount": float(amount_dec),
            "price": float(exec_price),
            "dry_run": True,
            "paper_sol": float(self.paper_sol),
            "realized_pnl": float(self.realized_pnl),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.logger.info(f"[DRY RUN] {side.upper()} {token} at {exec_price} | SOL={self.paper_sol} PnL={self.realized_pnl}")
        await self._append_journal(result)
        return result

    async def _append_journal(self, trade: Dict[str, Any]) -> None:
        try:
            self._journal_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not self._journal_path.exists()
            loop = asyncio.get_running_loop()

            def write_csv():
                with open(self._journal_path, "a", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(
                        f,
                        fieldnames=["timestamp", "type", "token", "amount", "price", "dry_run", "paper_sol", "realized_pnl"],
                    )
                    if write_header:
                        w.writeheader()
                    w.writerow(trade)

            await loop.run_in_executor(None, write_csv)
        except Exception as e:
            self.logger.debug(f"Failed to write trade journal: {e}")

    async def cleanup(self) -> None:
        try:
            if hasattr(self.dex, "close") and callable(self.dex.close):
                await self.dex.close()
        except Exception:
            pass