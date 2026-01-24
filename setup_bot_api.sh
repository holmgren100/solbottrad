#!/bin/bash
# Setup Bot Control API för Claude Code access

echo "🔧 Setting up Bot Control API..."

# Install dependencies
echo "📦 Installing Flask and dependencies..."
/usr/bin/python3 -m pip install flask flask-httpauth pandas psutil

echo "✅ Dependencies installed"
echo "📋 Verifying imports..."
/usr/bin/python3 -c "import flask; import flask_httpauth; import pandas; import psutil; print('✅ All imports OK')"

# Fix file permissions
chmod 644 /home/user/solbottrad/bot_api.py

# Create systemd service
cat > /etc/systemd/system/bot-api.service << 'EOF'
[Unit]
Description=Trading Bot Control API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/user/solbottrad
Environment="API_PORT=8765"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 /home/user/solbottrad/bot_api.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set secure password
echo ""
echo "🔐 IMPORTANT: Edit bot_api.py and change the password!"
echo "   nano /home/user/solbottrad/bot_api.py"
echo "   Find line 21: USERS = {'claude': 'your_secure_password_here'}"
echo "   Change 'your_secure_password_here' to a strong password"
echo ""
read -p "Press ENTER after you've set a secure password..."

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable bot-api.service
systemctl start bot-api.service

# Check status
sleep 2
systemctl status bot-api.service --no-pager

echo ""
echo "✅ Bot API Setup Complete!"
echo ""
echo "📡 API URL: http://209.38.229.243:8765"
echo ""
echo "🔗 Test endpoints:"
echo "   curl http://209.38.229.243:8765/health"
echo "   curl -u claude:PASSWORD http://209.38.229.243:8765/api/status"
echo ""
echo "🚀 Claude Code kan nu använda WebFetch för att:"
echo "   - Läsa bot status och positions"
echo "   - Hämta trades och rejected data"
echo "   - Analysera session performance"
echo "   - Läsa logs i realtid"
echo ""
echo "⚠️  SECURITY: Överväg nginx reverse proxy med SSL för produktion!"
echo ""
echo "📝 Service commands:"
echo "   systemctl status bot-api"
echo "   systemctl restart bot-api"
echo "   journalctl -u bot-api -f"
echo ""
echo "🔍 Debug commands if service fails:"
echo "   journalctl -u bot-api -n 50 --no-pager"
echo "   /usr/bin/python3 /home/user/solbottrad/bot_api.py  # Test manually"
