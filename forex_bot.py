#!/usr/bin/env python3
"""
Forex Trading Bot with Advanced Algorithms
Enhanced version with multiple trading strategies
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Import the trading algorithms
from trading_algorithms import (
    AlgorithmFactory, 
    RiskManager, 
    Signal,
    TradingSignal
)

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
    """Enhanced trading bot with advanced algorithms"""
    
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
        self.instruments = ["EUR_USD", "GBP_USD"]
        self.max_positions = 2
        
        # Algorithm configuration
        self.algorithm_name = "hybrid"  # Can be: momentum, trend, mean_reversion, hybrid
        self.algorithm_config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ema_fast': 20,
            'ema_slow': 50,
            'adx_period': 14,
            'adx_threshold': 25,
            'bb_period': 20,
            'bb_std': 2
        }
        
        # Risk management configuration
        self.risk_config = {
            'max_risk_per_trade': 0.01,  # 1% risk per trade
            'max_daily_loss': 0.05,      # 5% max daily loss
            'position_scaling': True,     # Scale positions by volatility
            'use_kelly_criterion': False  # Use Kelly for position sizing
        }
        
        # Initialize algorithm and risk manager
        self.algorithm = AlgorithmFactory.create_algorithm(
            self.algorithm_name, 
            self.algorithm_config
        )
        self.risk_manager = RiskManager(self.risk_config)
        
        # State tracking
        self.running = True
        self.daily_pnl = 0.0
        self.trades_today = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Performance tracking for Kelly Criterion
        self.trade_history = []
        
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
        
    def get_historical_prices(self, instrument: str, count: int = 200) -> pd.DataFrame:
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
        
    def generate_signal_advanced(self, instrument: str) -> Optional[Dict]:
        """Generate trading signal using advanced algorithms"""
        # Get account balance for position sizing
        account = self.get_account_summary()
        if not account:
            return None
            
        balance = float(account['account']['balance'])
        
        # Check daily loss limit
        if self.daily_pnl <= -balance * self.risk_config['max_daily_loss']:
            logger.warning("Daily loss limit reached. No new trades today.")
            return None
        
        # Get historical data
        df = self.get_historical_prices(instrument, count=200)
        if df.empty:
            return None
            
        current_price = self.get_current_price(instrument)
        if not current_price:
            return None
            
        # Get trading signal from algorithm
        signal = self.algorithm.analyze(df, current_price)
        
        # Skip if no signal or low confidence
        if signal.signal == Signal.HOLD or signal.confidence < 0.5:
            return None
            
        # Check correlation risk
        open_positions = self.get_open_positions()
        open_instruments = [pos['instrument'] for pos in open_positions]
        
        if not self.risk_manager.check_correlation_risk(instrument, open_instruments):
            logger.info(f"Skipping {instrument} due to correlation risk")
            return None
            
        # Calculate position size
        stop_distance = abs(current_price - signal.stop_loss)
        
        if self.risk_config['use_kelly_criterion'] and len(self.trade_history) > 20:
            # Calculate Kelly criterion from trade history
            wins = [t['pnl'] for t in self.trade_history if t['pnl'] > 0]
            losses = [abs(t['pnl']) for t in self.trade_history if t['pnl'] < 0]
            
            if wins and losses:
                win_rate = len(wins) / len(self.trade_history)
                avg_win = np.mean(wins)
                avg_loss = np.mean(losses)
                
                risk_percent = self.risk_manager.calculate_kelly_criterion(
                    win_rate, avg_win, avg_loss
                )
            else:
                risk_percent = self.risk_config['max_risk_per_trade']
        else:
            risk_percent = self.risk_config['max_risk_per_trade']
            
        position_size = self.risk_manager.calculate_position_size_fixed_risk(
            balance, stop_distance, risk_percent
        )
        
        # Adjust for volatility
        atr = signal.indicators.get('atr', 0)
        if atr > 0:
            # Calculate average ATR from historical data
            avg_atr = df['high'].rolling(20).max() - df['low'].rolling(20).min()
            avg_atr = avg_atr.mean()
            
            position_size = self.risk_manager.adjust_position_for_volatility(
                position_size, atr, avg_atr
            )
            
        # Round to valid lot size (OANDA uses units)
        position_size = int(position_size / 100) * 100  # Round to nearest 100
        
        # Ensure minimum position size
        min_position_size = 100
        if abs(position_size) < min_position_size:
            return None
            
        # Determine direction
        if signal.signal in [Signal.BUY, Signal.STRONG_BUY]:
            units = position_size
        else:
            units = -position_size
            
        return {
            'instrument': instrument,
            'units': units,
            'signal': signal.signal.name,
            'confidence': signal.confidence,
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'reason': signal.reason,
            'indicators': signal.indicators,
            'risk_percent': risk_percent
        }
        
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
            self.trades_today += 1
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
        """Advanced position management"""
        positions = self.get_open_positions()
        
        for position in positions:
            instrument = position['instrument']
            unrealized_pl = float(position['unrealizedPL'])
            units = int(position['long']['units']) if 'long' in position else int(position['short']['units'])
            
            # Get current market data
            df = self.get_historical_prices(instrument, count=50)
            if df.empty:
                continue
                
            current_price = self.get_current_price(instrument)
            if not current_price:
                continue
                
            # Get updated signal from algorithm
            signal = self.algorithm.analyze(df, current_price)
            
            # Check for signal reversal
            if units > 0 and signal.signal in [Signal.SELL, Signal.STRONG_SELL]:
                logger.info(f"Signal reversal detected for {instrument}. Closing long position.")
                self.close_position(instrument)
                self.update_trade_history(instrument, unrealized_pl)
                
            elif units < 0 and signal.signal in [Signal.BUY, Signal.STRONG_BUY]:
                logger.info(f"Signal reversal detected for {instrument}. Closing short position.")
                self.close_position(instrument)
                self.update_trade_history(instrument, unrealized_pl)
                
            # Trailing stop logic for profitable positions
            elif unrealized_pl > 0:
                # Calculate new trailing stop based on ATR
                atr = signal.indicators.get('atr', 0)
                if atr > 0:
                    if units > 0:  # Long position
                        new_stop = current_price - (2 * atr)
                        # Update stop loss if it's higher than current
                        # (This would require additional API calls to modify orders)
                    else:  # Short position
                        new_stop = current_price + (2 * atr)
                        
    def update_trade_history(self, instrument: str, pnl: float):
        """Update trade history for performance tracking"""
        self.trade_history.append({
            'timestamp': datetime.utcnow(),
            'instrument': instrument,
            'pnl': pnl
        })
        
        # Keep only last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
            
        # Update win/loss counters
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            
        # Update daily PnL
        self.daily_pnl += pnl
        
    def execute_trading_cycle(self):
        """Execute one complete trading cycle with advanced algorithms"""
        try:
            # Check account status
            account = self.get_account_summary()
            if account:
                balance = float(account['account']['balance'])
                margin_used = float(account['account']['marginUsed'])
                margin_available = float(account['account']['marginAvailable'])
                
                logger.info(f"Account - Balance: ${balance:.2f}, "
                          f"Margin Used: ${margin_used:.2f}, "
                          f"Margin Available: ${margin_available:.2f}")
                
                # Log performance metrics
                if self.trades_today > 0:
                    win_rate = self.winning_trades / (self.winning_trades + self.losing_trades) * 100
                    logger.info(f"Today - Trades: {self.trades_today}, "
                              f"Win Rate: {win_rate:.1f}%, "
                              f"Daily PnL: ${self.daily_pnl:.2f}")
                
            # Manage existing positions
            self.manage_positions()
            
            # Check for new trading opportunities
            positions = self.get_open_positions()
            if len(positions) < self.max_positions:
                for instrument in self.instruments:
                    # Skip if we already have a position
                    if any(p['instrument'] == instrument for p in positions):
                        continue
                        
                    # Generate advanced signal
                    trade_signal = self.generate_signal_advanced(instrument)
                    
                    if trade_signal:
                        # Log the signal details
                        logger.info(f"\n{'='*50}")
                        logger.info(f"TRADE SIGNAL for {instrument}:")
                        logger.info(f"Signal: {trade_signal['signal']}")
                        logger.info(f"Confidence: {trade_signal['confidence']:.2%}")
                        logger.info(f"Entry: {trade_signal['entry_price']:.5f}")
                        logger.info(f"Stop Loss: {trade_signal['stop_loss']:.5f}")
                        logger.info(f"Take Profit: {trade_signal['take_profit']:.5f}")
                        logger.info(f"Position Size: {abs(trade_signal['units'])} units")
                        logger.info(f"Risk: {trade_signal['risk_percent']:.2%} of balance")
                        logger.info(f"Reason: {trade_signal['reason']}")
                        logger.info(f"{'='*50}\n")
                        
                        # Place the order
                        success = self.place_order(
                            instrument=trade_signal['instrument'],
                            units=trade_signal['units'],
                            stop_loss=trade_signal['stop_loss'],
                            take_profit=trade_signal['take_profit']
                        )
                        
                        if success:
                            # Only open one position per cycle
                            break
                            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            
    def reset_daily_stats(self):
        """Reset daily statistics"""
        current_hour = datetime.utcnow().hour
        
        # Reset at midnight UTC
        if current_hour == 0 and self.trades_today > 0:
            logger.info(f"Daily stats reset - Trades: {self.trades_today}, PnL: ${self.daily_pnl:.2f}")
            self.daily_pnl = 0.0
            self.trades_today = 0
            
    def run(self):
        """Main bot loop with advanced algorithms"""
        logger.info(f"Starting Forex Trading Bot with {self.algorithm_name.upper()} algorithm...")
        logger.info(f"Trading instruments: {', '.join(self.instruments)}")
        logger.info(f"Risk per trade: {self.risk_config['max_risk_per_trade']:.1%}")
        logger.info(f"Max daily loss: {self.risk_config['max_daily_loss']:.1%}")
        
        # Wait for market to open
        while self.running:
            now = datetime.utcnow()
            
            # Check if market is open (Sunday 5PM ET to Friday 5PM ET)
            if now.weekday() == 5 or (now.weekday() == 6 and now.hour < 22):
                logger.info("Market is closed. Waiting...")
                time.sleep(3600)  # Check every hour
                continue
                
            # Reset daily statistics
            self.reset_daily_stats()
            
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
            
        # Log final statistics
        if self.winning_trades + self.losing_trades > 0:
            win_rate = self.winning_trades / (self.winning_trades + self.losing_trades) * 100
            logger.info(f"Final Statistics - Total Trades: {self.winning_trades + self.losing_trades}, "
                 
