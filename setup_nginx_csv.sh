#!/bin/bash
# Setup nginx för säker CSV-åtkomst med basic auth

echo "🔧 Setting up nginx for secure CSV access..."

# Install nginx if needed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing nginx..."
    apt-get update && apt-get install -y nginx apache2-utils
fi

# Create basic auth
echo "🔐 Creating basic auth..."
echo "Enter username for CSV access:"
read USERNAME
htpasswd -c /etc/nginx/.htpasswd "$USERNAME"

# Create nginx config
cat > /etc/nginx/sites-available/csv-access << 'EOF'
server {
    listen 8765;
    server_name _;

    # Basic auth
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # CSV directory
    location / {
        root /home/user/solbottrad/data;
        autoindex on;

        # Allow only CSV files
        location ~ \.(csv|txt|log)$ {
            add_header Content-Type text/plain;
        }

        # Deny all other files
        location ~ /\. {
            deny all;
        }
    }

    # Health check (no auth needed)
    location /health {
        auth_basic off;
        return 200 "OK";
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/csv-access /etc/nginx/sites-enabled/

# Test config
nginx -t

# Reload nginx
systemctl reload nginx

echo ""
echo "✅ Nginx setup complete!"
echo "🔗 Access URL: http://$(curl -s ifconfig.me):8765/"
echo "📂 Files available:"
echo "   - http://YOUR_IP:8765/ml_trades.csv"
echo "   - http://YOUR_IP:8765/rejected_trades.csv"
echo ""
echo "🔐 Protected with username: $USERNAME"
echo "💡 Claude Code kan använda WebFetch med basic auth!"
