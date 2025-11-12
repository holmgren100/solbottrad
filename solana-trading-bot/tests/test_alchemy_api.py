import asyncio
from api.alchemy_api import AlchemyAPI

async def test_alchemy():
    alchemy = AlchemyAPI()

    # Test WebSocket connection
    websocket = await alchemy.connect()
    print("Connected to Alchemy WebSocket")

    # Test subscribing to a wallet (replace with a valid wallet address)
    wallet_address = "3jbU2sKhQAY34pT7o8ZwtfNnRCcke2L63ZFQJhC83EDm"
    await alchemy.subscribe_to_address(websocket, wallet_address)
    print(f"Subscribed to wallet: {wallet_address}")

    # Test handling messages (this will block until a message is received)
    print("Waiting for messages...")
    message = await alchemy.handle_messages(websocket)
    print(f"Received message: {message}")

    # Disconnect WebSocket
    await alchemy.disconnect(websocket)
    print("Disconnected from Alchemy WebSocket")

if __name__ == "__main__":
    asyncio.run(test_alchemy())