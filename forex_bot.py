#!/usr/bin/env python3
"""
Forex Trading Bot for Raspberry Pi
Designed to trade forex pairs using OANDA's API
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Create logs directory if it doesn't exist
import os
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/forex_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ForexTradingBot:
    """Main trading bot class for forex trading via OANDA"""
    
    def __init__(self, account_id: str, access_token: str, practice: bool = True):
        """
        Initialize the trading bot
        
        Args:
            account_id: Your OANDA account ID
            access_token: Your OANDA API access token
            practice: Whether to use practice (demo) or live account
        """
        self.account_id = account_id
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # API endpoints
        if practice:
            self.base_url = "https://api-fxpractice.oanda.com"
            self.stream_url = "https://stream-fxpractice.oanda.com"
        else:
            self.base_url = "https://api-fxtrade.oanda.com"
            self.stream_url = "https://stream-fxtrade.oanda.com"
            
        # Trading parameters
        self.instruments = ["EUR_USD", "GBP_USD"]  # Forex pairs to trade
        self.position_size = 1000  # Units to trade (micro lots)
        self.max_positions = 2  # Maximum concurrent positions
        self.stop_loss_pips = 20  # Stop loss in pips
        self.take_profit_pips = 40  # Take profit in pips
        
        # Strategy parameters
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_fast = 20
        self.ma_slow = 50
        
        # State tracking
        self.running = True
        self.positions = {}
        self.price_data = {instrument: [] for instrument in self.instruments}
        
    def get_account_summary(self) -> Dict:
        """Get account summary including balance and margin"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get account summary: {response.text}")
            return None
            
    def get_current_price(self, instrument: str) -> Optional[float]:
        """Get current bid/ask prices for an instrument"""
        url = f"{self.base_url}/v3/instruments/{instrument}/candles"
        params = {
            'count': 1,
            'granularity': 'M1',
            'price': 'MBA'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['candles']:
                candle = data['candles'][0]
                bid = float(candle['bid']['c'])
                ask = float(candle['ask']['c'])
                return (bid + ask) / 2  # Mid price
        
        logger.error(f"Failed to get price for {instrument}")
        return None
        
    def get_historical_prices(self, instrument: str, count: int = 100) -> pd.DataFrame:
        """Get historical price data for analysis"""
        url = f"{self.base_url}/v3/instruments/{instrument}/candles"
        params = {
            'count': count,
            'granularity': 'M5',  # 5-minute candles
            'price': 'MBA'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            candles = []
            
            for candle in data['candles']:
                candles.append({
                    'time': candle['time'],
                    'open': float(candle['mid']['o']),
                    'high': float(candle['mid']['h']),
                    'low': float(candle['mid']['l']),
                    'close': float(candle['mid']['c']),
                    'volume': candle['volume']
                })
                
            return pd.DataFrame(candles)
        
        logger.error(f"Failed to get historical data for {instrument}")
        return pd.DataFrame()
        
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI if not enough data
            
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
        
    def calculate_moving_averages(self, prices: pd.Series) -> Tuple[float, float]:
        """Calculate fast and slow moving averages"""
        if len(prices) < self.ma_slow:
            return 0.0, 0.0
            
        ma_fast = prices.rolling(window=self.ma_fast).mean().iloc[-1]
        ma_slow = prices.rolling(window=self.ma_slow).mean().iloc[-1]
        
        return ma_fast, ma_slow
        
    def generate_signal(self, instrument: str) -> str:
        """Generate trading signal based on strategy"""
        df = self.get_historical_prices(instrument)
        
        if df.empty or len(df) < self.ma_slow:
            return "HOLD"
            
        # Calculate indicators
        rsi = self.calculate_rsi(df['close'])
        ma_fast, ma_slow = self.calculate_moving_averages(df['close'])
        current_price = df['close'].iloc[-1]
        
        # Trading logic
        signal = "HOLD"
        
        # RSI-based signals
        if rsi < self.rsi_oversold and ma_fast > ma_slow:
            signal = "BUY"
        elif rsi > self.rsi_overbought and ma_fast < ma_slow:
            signal = "SELL"
            
        # Log the analysis
        logger.info(f"{instrument} - Price: {current_price:.5f}, RSI: {rsi:.2f}, "
                   f"MA Fast: {ma_fast:.5f}, MA Slow: {ma_slow:.5f}, Signal: {signal}")
        
        return signal
        
    def calculate_position_size(self) -> int:
        """Calculate position size based on account balance and risk"""
        account = self.get_account_summary()
        
        if account:
            balance = float(account['account']['balance'])
            # Risk 1% of account per trade
            risk_amount = balance * 0.01
            # Simple position sizing - can be improved
            return self.position_size
        
        return self.position_size
        
    def place_order(self, instrument: str, units: int, stop_loss: float = None, 
                   take_profit: float = None) -> bool:
        """Place a market order"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        
        order_data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        
        # Add stop loss if provided
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": f"{stop_loss:.5f}"
            }
            
        # Add take profit if provided
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": f"{take_profit:.5f}"
            }
            
        response = requests.post(url, headers=self.headers, json=order_data)
        
        if response.status_code == 201:
            logger.info(f"Order placed successfully for {instrument}: {units} units")
            return True
        else:
            logger.error(f"Failed to place order: {response.text}")
            return False
            
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/positions"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()['positions']
        
        return []
        
    def close_position(self, instrument: str) -> bool:
        """Close all positions for an instrument"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/positions/{instrument}/close"
        
        response = requests.put(url, headers=self.headers)
        
        if response.status_code == 200:
            logger.info(f"Closed position for {instrument}")
            return True
        else:
            logger.error(f"Failed to close position: {response.text}")
            return False
            
    def manage_positions(self):
        """Check and manage existing positions"""
        positions = self.get_open_positions()
        
        for position in positions:
            instrument = position['instrument']
            unrealized_pl = float(position['unrealizedPL'])
            
            # Simple position management - close if profit > 50 or loss > 30
            if unrealized_pl > 50:
                logger.info(f"Taking profit on {instrument}: ${unrealized_pl:.2f}")
                self.close_position(instrument)
            elif unrealized_pl < -30:
                logger.info(f"Stopping loss on {instrument}: ${unrealized_pl:.2f}")
                self.close_position(instrument)
                
    def execute_trading_cycle(self):
        """Execute one complete trading cycle"""
        try:
            # Check account status
            account = self.get_account_summary()
            if account:
                balance = float(account['account']['balance'])
                logger.info(f"Account balance: ${balance:.2f}")
                
            # Manage existing positions
            self.manage_positions()
            
            # Check for new trading opportunities
            positions = self.get_open_positions()
            if len(positions) < self.max_positions:
                for instrument in self.instruments:
                    # Skip if we already have a position in this instrument
                    if any(p['instrument'] == instrument for p in positions):
                        continue
                        
                    signal = self.generate_signal(instrument)
                    
                    if signal in ["BUY", "SELL"]:
                        current_price = self.get_current_price(instrument)
                        
                        if current_price:
                            # Calculate stop loss and take profit
                            pip_value = 0.0001 if "_JPY" not in instrument else 0.01
                            
                            if signal == "BUY":
                                units = self.calculate_position_size()
                                stop_loss = current_price - (self.stop_loss_pips * pip_value)
                                take_profit = current_price + (self.take_profit_pips * pip_value)
                            else:  # SELL
                                units = -self.calculate_position_size()
                                stop_loss = current_price + (self.stop_loss_pips * pip_value)
                                take_profit = current_price - (self.take_profit_pips * pip_value)
                                
                            # Place the order
                            success = self.place_order(instrument, units, stop_loss, take_profit)
                            
                            if success:
                                logger.info(f"Opened {signal} position for {instrument} at {current_price:.5f}")
                                # Only open one position per cycle
                                break
                                
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            
    def run(self):
        """Main bot loop"""
        logger.info("Starting Forex Trading Bot...")
        
        # Wait for market to open (Forex is closed on weekends)
        while self.running:
            now = datetime.utcnow()
            
            # Check if market is open (Sunday 5PM ET to Friday 5PM ET)
            if now.weekday() == 5 or (now.weekday() == 6 and now.hour < 22):
                logger.info("Market is closed. Waiting...")
                time.sleep(3600)  # Check every hour
                continue
                
            # Execute trading cycle
            self.execute_trading_cycle()
            
            # Wait before next cycle (5 minutes)
            time.sleep(300)
            
    def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        self.running = False
        
        # Close all positions before stopping
        positions = self.get_open_positions()
        for position in positions:
            self.close_position(position['instrument'])
            

def load_config(config_path: str = "config.json") -> Dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Please create a config.json file based on config_template.json")
        exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in configuration file: {config_path}")
        exit(1)


def main():
    """Main entry point"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Forex Trading Bot')
    parser.add_argument('--config', type=str, default='config.json',
                       help='Path to configuration file')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Create and run the bot
    bot = ForexTradingBot(
        account_id=config['account_id'],
        access_token=config['access_token'],
        practice=config.get('practice', True)
    )
    
    # Apply configuration if provided
    if 'trading' in config:
        bot.instruments = config['trading'].get('instruments', bot.instruments)
        bot.position_size = config['trading'].get('position_size', bot.position_size)
        bot.max_positions = config['trading'].get('max_positions', bot.max_positions)
        bot.stop_loss_pips = config['trading'].get('stop_loss_pips', bot.stop_loss_pips)
        bot.take_profit_pips = config['trading'].get('take_profit_pips', bot.take_profit_pips)
    
    if 'strategy' in config:
        bot.rsi_period = config['strategy'].get('rsi_period', bot.rsi_period)
        bot.rsi_oversold = config['strategy'].get('rsi_oversold', bot.rsi_oversold)
        bot.rsi_overbought = config['strategy'].get('rsi_overbought', bot.rsi_overbought)
        bot.ma_fast = config['strategy'].get('ma_fast', bot.ma_fast)
        bot.ma_slow = config['strategy'].get('ma_slow', bot.ma_slow)
    
    try:
        logger.info("Starting Forex Trading Bot with configuration from: " + args.config)
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
        logger.info("Bot stopped by user")
        

if __name__ == "__main__":
    main()
