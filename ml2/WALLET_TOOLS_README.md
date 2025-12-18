# Wallet Management Tools

Complete toolkit for managing your trading bot wallet.

## 📋 Available Tools

### 1. **show_wallet_address.py** - View Your Wallet Address
Shows your public wallet address for funding and checking balance.

```bash
python show_wallet_address.py
```

**Output:**
- Public wallet address
- Solscan links (mainnet & devnet)
- Instructions for funding

**Use when:**
- You need your address to send SOL to the bot
- You want to check balance on Solscan

---

### 2. **check_wallet_balance.py** - Check Balance
Check SOL balance on both mainnet and devnet with USD values.

```bash
python check_wallet_balance.py
```

**Output:**
- Current SOL price
- Mainnet balance (real money)
- Devnet balance (test SOL)
- USD equivalent values

**Use when:**
- Checking if wallet is funded
- Monitoring balance before/after trading
- Verifying deposits

---

### 3. **decrypt_for_phantom.py** - Import to Phantom
⚠️ **SECURITY WARNING:** Reveals your private key!

```bash
python decrypt_for_phantom.py
```

**Output:**
- Decrypted private key (KEEP SECRET!)
- Step-by-step Phantom import instructions

**Use when:**
- You want to manage wallet in Phantom
- You need to send SOL manually
- You want visual wallet interface

**Security:**
- Private key is shown ONLY after typing "SHOW"
- Never share the private key with anyone
- Clear your screen/clipboard after use

---

### 4. **withdraw_sol.py** - Withdraw SOL
Safely send SOL from bot wallet to another address.

```bash
python withdraw_sol.py
```

**Interactive prompts:**
1. Shows current balance
2. Enter destination address
3. Enter amount (or 'max' for all)
4. Confirm transaction
5. Sends SOL on-chain

**Use when:**
- Withdrawing trading profits
- Moving SOL to cold storage
- Sending to exchange

**Safety features:**
- Balance check before withdrawal
- Confirmation required
- Leaves small amount for fees
- Clear transaction preview

---

## 🚀 Quick Start: Funding Your Wallet

### Step 1: Get Your Wallet Address
```bash
python show_wallet_address.py
```
Copy the public address shown.

### Step 2: Send SOL
**Option A - From Phantom:**
1. Open Phantom wallet
2. Click "Send"
3. Paste your bot's address
4. Enter amount (start with 0.5 SOL for testing)
5. Confirm and send

**Option B - From Exchange:**
1. Go to your exchange (Coinbase, Binance, etc.)
2. Navigate to SOL withdrawal
3. Paste your bot's address
4. **Important:** Select "Solana" network (NOT SPL or other)
5. Enter amount and confirm

### Step 3: Verify Received
```bash
python check_wallet_balance.py
```
Wait 1-2 minutes for confirmation, then run this to see balance.

### Step 4: Update Bot to Mainnet
Edit `.env`:
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```

Then restart bot - it's ready to trade!

---

## 💡 Common Tasks

### Check if Wallet is Funded
```bash
python check_wallet_balance.py
```

### Get Address to Fund Wallet
```bash
python show_wallet_address.py
```

### Withdraw All Profits
```bash
python withdraw_sol.py
# Enter destination address
# Type 'max' for amount
# Type 'CONFIRM'
```

### Import to Phantom for Manual Control
```bash
python decrypt_for_phantom.py
# Type 'SHOW'
# Copy private key
# Import in Phantom
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` file secure
- Use strong `WALLET_ENCRYPTION_KEY`
- Regular balance checks
- Withdraw profits regularly
- Test with small amounts first

### ❌ DON'T:
- Share private key (decrypted)
- Post wallet info in public chats
- Leave private key visible on screen
- Use the same wallet for other purposes
- Store large amounts without cold storage backup

---

## 🆘 Troubleshooting

### "Wallet credentials not found"
- Make sure `.env` file exists in project root
- Check `WALLET_ENCRYPTION_KEY` and `SOLANA_PRIVATE_KEY_ENCRYPTED` are set

### "Failed to load wallet"
- Encryption key might be wrong
- Encrypted private key might be corrupted
- Try decrypting with `decrypt_for_phantom.py` to verify

### "Balance is zero"
- Wait 1-2 minutes after sending (blockchain confirmation)
- Check you sent to correct address with `show_wallet_address.py`
- Verify on Solscan that transaction succeeded
- Make sure you sent to mainnet (not devnet)

### "Transaction failed" during withdrawal
- Check you have enough balance (leave ~0.001 for fees)
- Verify destination address is correct
- Make sure network connection is stable
- Try again after a minute

---

## 📞 Need Help?

1. **Check balance:** `python check_wallet_balance.py`
2. **View on Solscan:** `python show_wallet_address.py` (get links)
3. **Verify .env:** Make sure wallet credentials are present
4. **Test withdrawal:** Try small amount first (0.01 SOL)

---

**Created:** $(date)
**Bot Version:** Solana Trading Bot v1.0
