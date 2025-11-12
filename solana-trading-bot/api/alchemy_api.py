import websockets
import json
import asyncio
from config.settings import settings
from utils.logger import setup_logger

class AlchemyAPI:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.wss_url = settings.ALCHEMY_WSS
        self.websocket = None
        self.is_connected = False

    async def connect(self):
        """
        Establish WebSocket connection to Alchemy API
        """
        try:
            self.websocket = await websockets.connect(self.wss_url)
            self.is_connected = True
            self.logger.info("Connected to Alchemy WebSocket")
            return self.websocket
        except Exception as e:
            self.logger.error(f"Failed to connect to Alchemy WebSocket: {str(e)}")
            self.is_connected = False
            raise

    async def disconnect(self, websocket=None):
        """
        Disconnect from WebSocket
        """
        try:
            if websocket:
                await websocket.close()
            elif self.websocket:
                await self.websocket.close()
            
            self.is_connected = False
            self.logger.info("Disconnected from Alchemy WebSocket")
        except Exception as e:
            self.logger.error(f"Error disconnecting from Alchemy WebSocket: {e}")

    async def subscribe_to_address(self, websocket, address):
        """
        Subscribe to address updates using Solana methods
        """
        try:
            # For Solana, we use accountSubscribe instead of eth_subscribe
            subscription = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "accountSubscribe",
                "params": [
                    address,
                    {
                        "encoding": "base64",
                        "commitment": "finalized"
                    }
                ]
            }
            
            await websocket.send(json.dumps(subscription))
            self.logger.info(f"Subscribed to Solana address: {address}")
            
            # Wait for subscription confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if "result" in response_data:
                self.logger.info(f"Subscription confirmed for {address}: {response_data['result']}")
            else:
                self.logger.error(f"Subscription failed for {address}: {response_data}")
                
        except Exception as e:
            self.logger.error(f"Failed to subscribe to address {address}: {str(e)}")
            raise

    async def subscribe_to_logs(self, websocket, program_id=None):
        """
        Subscribe to program logs (useful for DEX monitoring)
        """
        try:
            subscription = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [program_id]} if program_id else "all",
                    {
                        "commitment": "finalized"
                    }
                ]
            }
            
            await websocket.send(json.dumps(subscription))
            self.logger.info(f"Subscribed to logs for program: {program_id or 'all'}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to logs: {str(e)}")
            raise

    async def handle_messages(self, websocket):
        """
        Handle incoming WebSocket messages
        """
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.logger.debug(f"Received message: {data}")
                    
                    # Handle different message types
                    if "method" in data:
                        if data["method"] == "accountNotification":
                            await self._handle_account_notification(data)
                        elif data["method"] == "logsNotification":
                            await self._handle_logs_notification(data)
                    
                    yield data
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON message: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"Error handling WebSocket messages: {str(e)}")
            raise

    async def _handle_account_notification(self, data):
        """
        Handle account change notifications
        """
        try:
            params = data.get("params", {})
            result = params.get("result", {})
            
            self.logger.info(f"Account notification: {result}")
            # Add your account change handling logic here
            
        except Exception as e:
            self.logger.error(f"Error handling account notification: {e}")

    async def _handle_logs_notification(self, data):
        """
        Handle program logs notifications
        """
        try:
            params = data.get("params", {})
            result = params.get("result", {})
            
            self.logger.info(f"Logs notification: {result}")
            # Add your logs handling logic here
            
        except Exception as e:
            self.logger.error(f"Error handling logs notification: {e}")

    async def get_account_info(self, address):
        """
        Get account information (non-WebSocket method)
        """
        try:
            # This would typically use HTTP requests to get account info
            # For now, just log the request
            self.logger.info(f"Getting account info for: {address}")
            return {"address": address, "status": "active"}
            
        except Exception as e:
            self.logger.error(f"Error getting account info for {address}: {e}")
            return None

    def is_websocket_connected(self):
        """
        Check if WebSocket is connected
        """
        return self.is_connected and self.websocket and not self.websocket.closed