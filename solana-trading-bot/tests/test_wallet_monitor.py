from monitoring.wallet_monitor import WalletMonitor

def test_wallet_monitor():
    wallet_monitor = WalletMonitor()

    # Simulate a transaction
    transaction = {
        "wallet": "0x1234567890abcdef",
        "token": "SOL",
        "amount": 10.0,
        "price": 100.0,
        "timestamp": "2025-03-21T12:00:00Z"
    }

    try:
        if hasattr(wallet_monitor, "process_transaction"):
            wallet_monitor.process_transaction(transaction)
            print("Transaction processed successfully")
        else:
            print("Error: WalletMonitor has no method 'process_transaction'. Please implement it.")
    except Exception as e:
        print("Failed to process transaction.")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_wallet_monitor()