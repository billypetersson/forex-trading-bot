# Forex Trading Bot for Raspberry Pi

A Python-based automated forex trading bot designed to run on Raspberry Pi, using OANDA's REST API for live and demo trading.

## Features

- **Automated Trading**: Executes trades based on technical indicators
- **Multiple Strategies**: RSI + Moving Average crossover strategy
- **Risk Management**: Configurable stop-loss and take-profit levels
- **Position Management**: Monitors and manages open positions
- **Multi-Pair Support**: Trade multiple currency pairs simultaneously
- **Logging**: Comprehensive logging for debugging and analysis
- **Demo & Live Support**: Switch between demo and live trading
- **Raspberry Pi Optimized**: Lightweight and efficient for Pi hardware

## Project Structure

```
C:\github\forex-trading-bot\
│   README.md              # This file
│   forex_bot.py          # Main trading bot script
│   requirements.txt      # Python dependencies
│   config_template.json  # Configuration template
│   .gitignore           # Git ignore file
│
├───logs\                 # Trading logs directory
│
└───backtest\            # Backtesting scripts (optional)
```

## Prerequisites

- Python 3.7 or higher
- OANDA demo or live account
- Stable internet connection
- Raspberry Pi (any model) or PC for testing

## Installation

### 1. Clone the Repository

```bash
cd C:\github
mkdir forex-trading-bot
cd forex-trading-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Get OANDA API Credentials

1. Visit [OANDA](https://www.oanda.com)
2. Sign up for a free demo account
3. Navigate to Manage API Access in your account settings
4. Generate an API token
5. Note your account ID

### 4. Configure the Bot

Create a `config.json` file based on the template:

```json
{
    "account_id": "YOUR_ACCOUNT_ID",
    "access_token": "YOUR_ACCESS_TOKEN",
    "practice": true,
    "instruments": ["EUR_USD", "GBP_USD"],
    "position_size": 1000,
    "max_positions": 2,
    "stop_loss_pips": 20,
    "take_profit_pips": 40
}
```

## Usage

### Running the Bot

```bash
# Basic run
python forex_bot.py

# Run with custom config
python forex_bot.py --config my_config.json

# Run in background (Linux/Mac)
nohup python forex_bot.py &

# Run in background (Windows)
start /B python forex_bot.py
```

### Running on Raspberry Pi

1. **Transfer files to Pi:**
```bash
scp -r C:\github\forex-trading-bot pi@raspberrypi:~/
```

2. **SSH into Pi and install:**
```bash
ssh pi@raspberrypi
cd ~/forex-trading-bot
pip3 install -r requirements.txt
```

3. **Run as a service (recommended):**

Create `/etc/systemd/system/forex-bot.service`:

```ini
[Unit]
Description=Forex Trading Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/forex-trading-bot
ExecStart=/usr/bin/python3 /home/pi/forex-trading-bot/forex_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable forex-bot.service
sudo systemctl start forex-bot.service
```

## Trading Strategy

The bot uses a combination of technical indicators:

### Entry Signals
- **BUY**: RSI < 30 (oversold) AND Fast MA > Slow MA
- **SELL**: RSI > 70 (overbought) AND Fast MA < Slow MA

### Risk Management
- **Position Size**: 1000 units (0.01 lots)
- **Stop Loss**: 20 pips
- **Take Profit**: 40 pips (2:1 risk-reward ratio)
- **Max Positions**: 2 concurrent trades
- **Risk per Trade**: 1% of account balance

### Indicators Used
- **RSI Period**: 14
- **Fast MA**: 20 periods
- **Slow MA**: 50 periods
- **Timeframe**: 5-minute candles for analysis

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `account_id` | Your OANDA account ID | Required |
| `access_token` | Your OANDA API token | Required |
| `practice` | Use demo account | `true` |
| `instruments` | Currency pairs to trade | `["EUR_USD", "GBP_USD"]` |
| `position_size` | Units per trade | `1000` |
| `max_positions` | Maximum concurrent trades | `2` |
| `stop_loss_pips` | Stop loss in pips | `20` |
| `take_profit_pips` | Take profit in pips | `40` |
| `rsi_period` | RSI calculation period | `14` |
| `rsi_oversold` | RSI oversold threshold | `30` |
| `rsi_overbought` | RSI overbought threshold | `70` |
| `ma_fast` | Fast MA period | `20` |
| `ma_slow` | Slow MA period | `50` |

## Monitoring

### Log Files
- Location: `logs/forex_bot.log`
- Rotation: Daily
- Level: INFO by default

### Check Status
```bash
# View recent logs
tail -f logs/forex_bot.log

# Check if running (Linux)
ps aux | grep forex_bot.py

# Check service status (if using systemd)
sudo systemctl status forex-bot
```

## Safety Features

1. **Demo Mode**: Always starts in demo mode by default
2. **Position Limits**: Maximum concurrent positions limit
3. **Stop Loss**: Mandatory stop loss on all trades
4. **Weekend Detection**: Automatically pauses during market closure
5. **Error Handling**: Comprehensive exception handling
6. **Connection Recovery**: Automatic reconnection on network issues

## Performance Optimization for Raspberry Pi

1. **Use Ethernet**: More stable than WiFi
2. **Quality Power Supply**: Use official Pi power adapter
3. **Heat Management**: Add heatsinks for 24/7 operation
4. **SD Card**: Use high-quality SD card (Class 10 or better)
5. **Swap Space**: Increase if running on Pi Zero
6. **Log Rotation**: Implement to prevent disk filling

## Troubleshooting

### Common Issues

1. **"Connection refused" error**
   - Check internet connection
   - Verify API credentials
   - Ensure not hitting rate limits

2. **"Insufficient balance" error**
   - Reduce position size
   - Check account balance
   - Verify margin requirements

3. **Bot stops during weekend**
   - This is normal - forex markets are closed
   - Bot will resume Sunday evening

4. **High CPU usage on Pi**
   - Increase sleep time between cycles
   - Reduce number of instruments
   - Check for memory leaks

## Backtesting

To backtest your strategy before going live:

```python
# Run backtest
python backtest/backtest_strategy.py --start 2024-01-01 --end 2024-12-31
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Disclaimer

**IMPORTANT**: Trading forex involves substantial risk of loss and is not suitable for all investors. 

- Always test thoroughly with a demo account first
- Never risk money you cannot afford to lose
- Past performance does not guarantee future results
- This bot is for educational purposes
- The authors are not responsible for any financial losses

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Issues**: Open an issue on GitHub
- **Documentation**: Check the Wiki
- **OANDA API**: [OANDA Developer Portal](http://developer.oanda.com)

## Roadmap

- [ ] Add more technical indicators (MACD, Bollinger Bands)
- [ ] Implement machine learning predictions
- [ ] Create web dashboard for monitoring
- [ ] Add backtesting framework
- [ ] Support for more brokers
- [ ] Mobile app for monitoring
- [ ] Advanced position sizing algorithms
- [ ] News sentiment analysis

## Acknowledgments

- OANDA for providing excellent API documentation
- The Python community for amazing libraries
- Raspberry Pi Foundation for affordable hardware

---

**Remember**: Start with a demo account and small position sizes. Only trade with money you can afford to lose.
