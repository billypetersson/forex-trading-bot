#!/bin/bash
# Raspberry Pi Forex Trading Bot Setup Script
# Run this after installing Raspberry Pi OS Lite

echo "=== Raspberry Pi Forex Trading Bot Setup ==="
echo "This script will configure your Pi for optimal trading performance"
echo ""

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "Installing essential packages..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    build-essential \
    libatlas-base-dev \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    htop \
    fail2ban \
    ufw \
    chrony

# Configure timezone for trading
echo "Setting timezone..."
sudo timedatectl set-timezone UTC
echo "Timezone set to UTC for forex trading"

# Optimize system for performance
echo "Optimizing system performance..."

# Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable hciuart.service
sudo systemctl disable avahi-daemon.service
sudo systemctl disable triggerhappy.service

# Configure swap for better performance
echo "Configuring swap..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/g' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Set CPU governor to performance
echo "Setting CPU to performance mode..."
echo "performance" | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

# Make it permanent
sudo apt install -y cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils

# Configure firewall
echo "Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw --force enable

# Install TA-Lib
echo "Installing TA-Lib..."
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd /
sudo rm -rf /tmp/ta-lib*

# Create trading bot directory
echo "Creating trading bot directory..."
mkdir -p ~/forex-trading-bot
cd ~/forex-trading-bot

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install wheel
pip install numpy pandas requests
pip install TA-Lib scipy
pip install python-dotenv schedule

# Create systemd service for auto-start
echo "Creating systemd service..."
sudo tee /etc/systemd/system/forex-bot.service > /dev/null <<EOF
[Unit]
Description=Forex Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/forex-trading-bot
Environment="PATH=/home/pi/forex-trading-bot/venv/bin"
ExecStart=/home/pi/forex-trading-bot/venv/bin/python /home/pi/forex-trading-bot/forex_bot.py
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/home/pi/forex-trading-bot/logs/service.log
StandardError=append:/home/pi/forex-trading-bot/logs/service-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation config
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/forex-bot > /dev/null <<EOF
/home/pi/forex-trading-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
EOF

# Create monitoring script
echo "Creating monitoring script..."
cat > ~/forex-trading-bot/monitor.sh <<'EOF'
#!/bin/bash
# Simple monitoring script for forex bot

echo "=== Forex Bot Monitor ==="
echo "Current time: $(date)"
echo ""

# Check if service is running
if systemctl is-active --quiet forex-bot; then
    echo "✓ Bot service is running"
else
    echo "✗ Bot service is NOT running"
fi

# Check system resources
echo ""
echo "System Resources:"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory: $(free -h | grep Mem | awk '{print $3 " / " $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $3 " / " $2 " (" $5 ")"}')"
echo "Temperature: $(vcgencmd measure_temp)"

# Show recent logs
echo ""
echo "Recent bot activity:"
tail -n 10 ~/forex-trading-bot/logs/forex_bot.log 2>/dev/null || echo "No logs found yet"

# Check network
echo ""
echo "Network status:"
ping -c 1 api-fxpractice.oanda.com > /dev/null 2>&1 && echo "✓ OANDA API reachable" || echo "✗ Cannot reach OANDA API"
EOF

chmod +x ~/forex-trading-bot/monitor.sh

# Create backup script
echo "Creating backup script..."
cat > ~/forex-trading-bot/backup.sh <<'EOF'
#!/bin/bash
# Backup script for forex bot

BACKUP_DIR="/home/pi/forex-bot-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/forex-bot-backup-$TIMESTAMP.tar.gz"

mkdir -p $BACKUP_DIR

# Create backup
tar -czf $BACKUP_FILE \
    --exclude='venv' \
    --exclude='logs' \
    --exclude='__pycache__' \
    /home/pi/forex-trading-bot/

echo "Backup created: $BACKUP_FILE"

# Keep only last 7 backups
ls -t $BACKUP_DIR/forex-bot-backup-*.tar.gz | tail -n +8 | xargs -r rm

echo "Old backups cleaned up"
EOF

chmod +x ~/forex-trading-bot/backup.sh

# Set up cron jobs
echo "Setting up automated tasks..."
(crontab -l 2>/dev/null; echo "0 0 * * * /home/pi/forex-trading-bot/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/30 * * * * /home/pi/forex-trading-bot/monitor.sh > /home/pi/forex-trading-bot/logs/monitor.log 2>&1") | crontab -

# Configure watchdog for auto-reboot on hang
echo "Installing watchdog..."
sudo apt install -y watchdog
sudo tee -a /etc/watchdog.conf > /dev/null <<EOF
max-load-1 = 24
watchdog-device = /dev/watchdog
watchdog-timeout = 15
EOF
sudo systemctl enable watchdog
sudo systemctl start watchdog

# Final configurations
echo "Applying final configurations..."

# Reduce GPU memory split (we don't need graphics)
echo "gpu_mem=16" | sudo tee -a /boot/config.txt

# Enable hardware watchdog
echo "dtparam=watchdog=on" | sudo tee -a /boot/config.txt

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Copy your forex bot files to ~/forex-trading-bot/"
echo "2. Create config.json with your OANDA credentials"
echo "3. Test the bot: cd ~/forex-trading-bot && source venv/bin/activate && python forex_bot.py"
echo "4. Enable auto-start: sudo systemctl enable forex-bot"
echo "5. Start service: sudo systemctl start forex-bot"
echo "6. Monitor status: sudo systemctl status forex-bot"
echo "7. View logs: tail -f ~/forex-trading-bot/logs/forex_bot.log"
echo "8. Run monitor: ~/forex-trading-bot/monitor.sh"
echo ""
echo "IMPORTANT: Reboot required for all optimizations to take effect!"
echo "Run: sudo reboot"
