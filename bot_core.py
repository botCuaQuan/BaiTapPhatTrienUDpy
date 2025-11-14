import time
import threading
import random
import math
from collections import defaultdict
from binance_client import (
    get_max_leverage, get_step_size, set_leverage, get_balance, 
    place_order, cancel_all_orders, get_current_price, get_positions,
    get_all_usdc_pairs, binance_api_request, WebSocketManager
)

class CoinManager:
    def __init__(self):
        self.active_coins = set()
        self._lock = threading.Lock()
    
    def register_coin(self, symbol):
        if not symbol:
            return
        with self._lock:
            self.active_coins.add(symbol.upper())
    
    def unregister_coin(self, symbol):
        if not symbol:
            return
        with self._lock:
            self.active_coins.discard(symbol.upper())
    
    def is_coin_active(self, symbol):
        if not symbol:
            return False
        with self._lock:
            return symbol.upper() in self.active_coins
    
    def get_active_coins(self):
        with self._lock:
            return list(self.active_coins)

class SmartCoinFinder:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        
    def get_symbol_leverage(self, symbol):
        return get_max_leverage(symbol, self.api_key, self.api_secret)
    
    def get_volume_signal(self, symbol):
        try:
            data = binance_api_request(
                "https://fapi.binance.com/fapi/v1/klines",
                params={"symbol": symbol, "interval": "5m", "limit": 10}
            )
            if not data or len(data) < 10:
                return None
            
            current_candle = data[-2]
            prev_candle = data[-3]

            open_price = float(current_candle[1])
            close_price = float(current_candle[4])
            current_volume = float(current_candle[5])
            prev_volume = float(prev_candle[5])

            volumes = [float(k[5]) for k in data[:-1]]
            avg_volume = sum(volumes) / len(volumes)

            volume_increase = current_volume > prev_volume * 1.2
            volume_above_average = current_volume > avg_volume * 1.1

            if close_price > open_price:
                candle_direction = "GREEN"
            elif close_price < open_price:
                candle_direction = "RED"
            else:
                candle_direction = "DOJI"

            if volume_increase and volume_above_average:
                if candle_direction == "GREEN":
                    return "BUY"
                elif candle_direction == "RED":
                    return "SELL"
            return None

        except Exception as e:
            return None
    
    def has_existing_position(self, symbol):
        try:
            positions = get_positions(symbol, self.api_key, self.api_secret)
            if positions:
                for pos in positions:
                    position_amt = float(pos.get('positionAmt', 0))
                    if abs(position_amt) > 0:
                        return True
            return False
        except Exception:
            return False
    
    def find_best_coin(self, target_direction, excluded_coins=None, required_leverage=10):
        try:
            all_symbols = get_all_usdc_pairs(limit=100)
            if not all_symbols:
                return None
            
            valid_symbols = []
            
            for symbol in all_symbols:
                if excluded_coins and symbol in excluded_coins:
                    continue
                
                if self.has_existing_position(symbol):
                    continue
                
                max_lev = self.get_symbol_leverage(symbol)
                if max_lev < required_leverage:
                    continue
                
                volume_signal = self.get_volume_signal(symbol)
                if volume_signal == target_direction:
                    valid_symbols.append(symbol)
            
            if not valid_symbols:
                return None
            
            selected_symbol = random.choice(valid_symbols)
            return selected_symbol
            
        except Exception:
            return None

class BaseBot:
    def __init__(self, symbol, lev, percent, tp, sl, roi_trigger, ws_manager, api_key, api_secret,
                 strategy_name, config_key=None, bot_id=None, coin_manager=None, symbol_locks=None):

        self.symbol = symbol.upper() if symbol else None
        self.lev = lev
        self.percent = percent
        self.tp = tp
        self.sl = sl
        self.roi_trigger = roi_trigger
        self.ws_manager = ws_manager
        self.api_key = api_key
        self.api_secret = api_secret
        self.strategy_name = strategy_name
        self.config_key = config_key
        self.bot_id = bot_id or f"{strategy_name}_{int(time.time())}_{random.randint(1000, 9999)}"

        self.status = "searching"
        self.side = ""
        self.qty = 0
        self.entry = 0
        self.prices = []
        self.current_price = 0
        self.position_open = False
        self._stop = False

        self.last_trade_time = 0
        self.last_close_time = 0
        self.last_position_check = 0
        self.last_error_log_time = 0

        self.cooldown_period = 3600
        self.position_check_interval = 30

        self._close_attempted = False
        self._last_close_attempt = 0

        self.should_be_removed = False

        self.coin_manager = coin_manager or CoinManager()
        self.symbol_locks = symbol_locks

        self.coin_finder = SmartCoinFinder(api_key, api_secret)

        self.last_side = None
        self.is_first_trade = True

        self.entry_base = 0
        self.average_down_count = 0
        self.last_average_down_time = 0
        self.average_down_cooldown = 60
        self.max_average_down_count = 7

        self.entry_green_count = 0
        self.entry_red_count = 0
        self.high_water_mark_roi = 0
        self.roi_check_activated = False

        self.global_long_count = 0
        self.global_short_count = 0
        self.global_long_pnl = 0
        self.global_short_pnl = 0
        self.last_global_position_check = 0
        self.global_position_check_interval = 10

        self.find_new_bot_after_close = True
        self.bot_creation_time = time.time()

        if symbol and self.coin_finder.has_existing_position(symbol):
            self.symbol = None
            self.status = "searching"
        else:
            self.check_position_status()
            if self.symbol:
                self.ws_manager.add_symbol(self.symbol, self._handle_price_update)

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def check_position_status(self):
        if not self.symbol:
            return
            
        try:
            positions = get_positions(self.symbol, self.api_key, self.api_secret)
            if not positions:
                self._reset_position()
                return
            
            position_found = False
            for pos in positions:
                if pos['symbol'] == self.symbol:
                    position_amt = float(pos.get('positionAmt', 0))
                    if abs(position_amt) > 0:
                        position_found = True
                        self.position_open = True
                        self.status = "open"
                        self.side = "BUY" if position_amt > 0 else "SELL"
                        self.qty = position_amt
                        self.entry = float(pos.get('entryPrice', 0))
                        self.last_side = self.side
                        self.is_first_trade = False
                        break
                    else:
                        position_found = True
                        self._reset_position()
                        break
            
            if not position_found:
                self._reset_position()
                
        except Exception:
            pass

    def check_global_positions(self):
        try:
            positions = get_positions(api_key=self.api_key, api_secret=self.api_secret)
            if not positions:
                self.global_long_count = 0
                self.global_short_count = 0
                self.global_long_pnl = 0
                self.global_short_pnl = 0
                self.global_long_value = 0
                self.global_short_value = 0
                return
            
            long_count = 0
            short_count = 0
            long_pnl_total = 0
            short_pnl_total = 0
            long_value_total = 0
            short_value_total = 0
            
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                entry_price = float(pos.get('entryPrice', 0))
                leverage = float(pos.get('leverage', 1))
                
                position_value = abs(position_amt) * entry_price / leverage
                
                if position_amt > 0:
                    long_count += 1
                    long_pnl_total += unrealized_pnl
                    long_value_total += position_value
                elif position_amt < 0:
                    short_count += 1
                    short_pnl_total += unrealized_pnl
                    short_value_total += position_value
            
            self.global_long_count = long_count
            self.global_short_count = short_count
            self.global_long_pnl = long_pnl_total
            self.global_short_pnl = short_pnl_total
            self.global_long_value = long_value_total
            self.global_short_value = short_value_total
            
        except Exception:
            pass
    
    def get_next_side_based_on_comprehensive_analysis(self):
        self.check_global_positions()
        
        long_pnl = self.global_long_pnl
        short_pnl = self.global_short_pnl
        
        if long_pnl > short_pnl:
            return "BUY"
        elif short_pnl > long_pnl:
            return "SELL"
        else:
            return random.choice(["BUY", "SELL"])

    def _reset_position(self):
        self.position_open = False
        self.status = "waiting"
        self.side = ""
        self.qty = 0
        self.entry = 0
        self._close_attempted = False
        self._last_close_attempt = 0
        self.entry_base = 0
        self.average_down_count = 0
        self.entry_green_count = 0
        self.entry_red_count = 0
        self.high_water_mark_roi = 0
        self.roi_check_activated = False

    def find_and_set_coin(self):
        try:
            active_coins = self.coin_manager.get_active_coins()
            target_direction = self.get_next_side_based_on_comprehensive_analysis()
            
            new_symbol = self.coin_finder.find_best_coin(
                target_direction=target_direction,
                excluded_coins=active_coins,
                required_leverage=self.lev
            )
            
            if new_symbol:
                self.coin_manager.register_coin(new_symbol)
                
                if self.symbol:
                    self.ws_manager.remove_symbol(self.symbol)
                    self.coin_manager.unregister_coin(self.symbol)
                
                self.symbol = new_symbol
                self.ws_manager.add_symbol(new_symbol, self._handle_price_update)
                self.status = "waiting"
                return True
            else:
                return False
            
        except Exception:
            return False

    def verify_leverage_and_switch(self):
        if not self.symbol:
            return True
        try:
            current_leverage = self.coin_finder.get_symbol_leverage(self.symbol)
            if current_leverage >= self.lev:
                return set_leverage(self.symbol, self.lev, self.api_key, self.api_secret)
            else:
                ok = set_leverage(self.symbol, current_leverage, self.api_key, self.api_secret)
                return ok
        except Exception:
            return False

    def _run(self):
        while not self._stop:
            try:
                current_time = time.time()
                
                if current_time - getattr(self, '_last_leverage_check', 0) > 60:
                    if not self.verify_leverage_and_switch():
                        if self.symbol:
                            self.ws_manager.remove_symbol(self.symbol)
                            self.coin_manager.unregister_coin(self.symbol)
                            self.symbol = None
                        time.sleep(1)
                        continue
                    self._last_leverage_check = current_time
                
                if current_time - self.last_global_position_check > self.global_position_check_interval:
                    self.check_global_positions()
                    self.last_global_position_check = current_time
                
                if current_time - self.last_position_check > self.position_check_interval:
                    self.check_position_status()
                    self.last_position_check = current_time
                
                if self.position_open:
                    self.check_averaging_down()
                              
                if not self.position_open:
                    if not self.symbol:
                        if self.find_and_set_coin():
                            pass
                        else:
                            time.sleep(5)
                        continue
                    
                    if current_time - self.last_trade_time > 60 and current_time - self.last_close_time > self.cooldown_period:
                        target_side = self.get_next_side_based_on_comprehensive_analysis()
                        current_volume_signal = self.coin_finder.get_volume_signal(self.symbol)
                        
                        if current_volume_signal == target_side:
                            if self.open_position(target_side):
                                self.last_trade_time = current_time
                            else:
                                time.sleep(1)
                        else:
                            self._cleanup_symbol()
                            time.sleep(1)
                    else:
                        time.sleep(1)
                
                if self.position_open and not self._close_attempted:
                    self.check_tp_sl()
                    
                time.sleep(1)
            
            except Exception:
                time.sleep(1)

    def _handle_price_update(self, price):
        self.current_price = price
        self.prices.append(price)
        
        if len(self.prices) > 100:
            self.prices.pop(0)

    def stop(self):
        self._stop = True
        if self.symbol:
            try:
                self.ws_manager.remove_symbol(self.symbol)
            except Exception:
                pass
            try:
                self.coin_manager.unregister_coin(self.symbol)
            except Exception:
                pass
            try:
                cancel_all_orders(self.symbol, self.api_key, self.api_secret)
            except Exception:
                pass

    def open_position(self, side):
        if side not in ["BUY", "SELL"]:
            return False

        if self.symbol:
            current_volume_signal = self.coin_finder.get_volume_signal(self.symbol)
            if current_volume_signal != side:
                return False

        if self.symbol_locks and self.symbol:
            lock = self.symbol_locks[self.symbol]
        else:
            lock = threading.Lock()

        with lock:
            try:
                self.check_position_status()
                if self.position_open:
                    return False

                if self.should_be_removed:
                    return False

                current_leverage = self.coin_finder.get_symbol_leverage(self.symbol)
                if current_leverage < self.lev:
                    self._cleanup_symbol()
                    return False

                if not set_leverage(self.symbol, self.lev, self.api_key, self.api_secret):
                    self._cleanup_symbol()
                    return False

                balance = get_balance(self.api_key, self.api_secret)
                if balance is None or balance <= 0:
                    return False

                current_price = get_current_price(self.symbol)
                if current_price <= 0:
                    self._cleanup_symbol()
                    return False

                step_size = get_step_size(self.symbol, self.api_key, self.api_secret)

                usd_amount = balance * (self.percent / 100)
                qty = (usd_amount * self.lev) / current_price
                if step_size > 0:
                    qty = math.floor(qty / step_size) * step_size
                    qty = round(qty, 8)

                if qty <= 0 or qty < step_size:
                    self._cleanup_symbol()
                    return False

                cancel_all_orders(self.symbol, self.api_key, self.api_secret)
                time.sleep(0.2)

                result = place_order(self.symbol, side, qty, self.api_key, self.api_secret)
                if result and 'orderId' in result:
                    executed_qty = float(result.get('executedQty', 0))
                    avg_price = float(result.get('avgPrice', current_price))

                    if executed_qty >= 0:
                        self.entry = avg_price
                        self.entry_base = avg_price
                        self.average_down_count = 0
                        self.side = side
                        self.qty = executed_qty if side == "BUY" else -executed_qty
                        self.position_open = True
                        self.status = "open"

                        self.last_side = side
                        self.is_first_trade = False

                        self.high_water_mark_roi = 0
                        self.roi_check_activated = False
                        return True
                    else:
                        self._cleanup_symbol()
                        return False
                else:
                    self._cleanup_symbol()
                    return False

            except Exception:
                self._cleanup_symbol()
                return False
    
    def _cleanup_symbol(self):
        if self.symbol:
            try:
                self.ws_manager.remove_symbol(self.symbol)
                self.coin_manager.unregister_coin(self.symbol)
            except Exception:
                pass
            
            self.symbol = None
        
        self.status = "searching"
        self.position_open = False
        self.side = ""
        self.qty = 0
        self.entry = 0
        self.entry_base = 0
        self.average_down_count = 0
        self.high_water_mark_roi = 0
        self.roi_check_activated = False

    def close_position(self, reason=""):
        try:
            self.check_position_status()
            
            if not self.position_open or abs(self.qty) <= 0:
                return False

            current_time = time.time()
            if self._close_attempted and current_time - self._last_close_attempt < 30:
                return False
            
            self._close_attempted = True
            self._last_close_attempt = current_time

            close_side = "SELL" if self.side == "BUY" else "BUY"
            close_qty = abs(self.qty)
            
            cancel_all_orders(self.symbol, self.api_key, self.api_secret)
            time.sleep(0.5)
            
            result = place_order(self.symbol, close_side, close_qty, self.api_key, self.api_secret)
            if result and 'orderId' in result:
                current_price = get_current_price(self.symbol)
                pnl = 0
                if self.entry > 0:
                    if self.side == "BUY":
                        pnl = (current_price - self.entry) * abs(self.qty)
                    else:
                        pnl = (self.entry - current_price) * abs(self.qty)
                
                self.last_close_time = time.time()
                
                time.sleep(2)
                self.check_position_status()
                
                return True
            else:
                self._close_attempted = False
                return False
                
        except Exception:
            self._close_attempted = False
            return False

    def check_tp_sl(self):
        if not self.symbol or not self.position_open or self.entry <= 0 or self._close_attempted:
            return

        current_price = get_current_price(self.symbol)
        if current_price <= 0:
            return

        if self.side == "BUY":
            profit = (current_price - self.entry) * abs(self.qty)
        else:
            profit = (self.entry - current_price) * abs(self.qty)
            
        invested = self.entry * abs(self.qty) / self.lev
        if invested <= 0:
            return
            
        roi = (profit / invested) * 100

        if roi > self.high_water_mark_roi:
            self.high_water_mark_roi = roi

        if self.roi_trigger is not None and self.high_water_mark_roi >= self.roi_trigger and not self.roi_check_activated:
            self.roi_check_activated = True

        if self.tp is not None and roi >= self.tp:
            self.close_position(f"✅ Đạt TP {self.tp}% (ROI: {roi:.2f}%)")
        elif self.sl is not None and self.sl > 0 and roi <= -self.sl:
            self.close_position(f"❌ Đạt SL {self.sl}% (ROI: {roi:.2f}%)")

    def check_averaging_down(self):
        if not self.position_open or not self.entry_base or self.average_down_count >= self.max_average_down_count:
            return
            
        try:
            current_time = time.time()
            if current_time - self.last_average_down_time < self.average_down_cooldown:
                return
                
            current_price = get_current_price(self.symbol)
            if current_price < 0:
                return
                
            if self.side == "BUY":
                profit = (current_price - self.entry_base) * abs(self.qty)
            else:
                profit = (self.entry_base - current_price) * abs(self.qty)
                
            invested = self.entry_base * abs(self.qty) / self.lev
            if invested < 0:
                return
                
            current_roi = (profit / invested) * 100
            
            if current_roi >= 0:
                return
                
            roi_negative = abs(current_roi)
            
            fib_levels = [200, 300, 500, 800, 1300, 2100, 3400]
            
            if self.average_down_count < len(fib_levels):
                current_fib_level = fib_levels[self.average_down_count]
                
                if roi_negative >= current_fib_level:
                    if self.execute_average_down_order():
                        self.last_average_down_time = current_time
                        self.average_down_count += 1
                        
        except Exception:
            pass

    def execute_average_down_order(self):
        try:
            balance = get_balance(self.api_key, self.api_secret)
            if balance is None or balance <= 0:
                return False
                
            current_price = get_current_price(self.symbol)
            if current_price < 0:
                return False
                
            additional_percent = self.percent * (self.average_down_count + 1)
            usd_amount = balance * (additional_percent / 100)
            qty = (usd_amount * self.lev) / current_price
            
            step_size = get_step_size(self.symbol, self.api_key, self.api_secret)
            if step_size > 0:
                qty = math.floor(qty / step_size) * step_size
                qty = round(qty, 8)
            
            if qty < step_size:
                return False
                
            result = place_order(self.symbol, self.side, qty, self.api_key, self.api_secret)
            
            if result and 'orderId' in result:
                executed_qty = float(result.get('executedQty', 0))
                avg_price = float(result.get('avgPrice', current_price))
                
                if executed_qty >= 0:
                    total_qty = abs(self.qty) + executed_qty
                    self.entry = (abs(self.qty) * self.entry + executed_qty * avg_price) / total_qty
                    self.qty = total_qty if self.side == "BUY" else -total_qty
                    
                    return True
                    
            return False
            
        except Exception:
            return False

    def get_bot_info(self):
        return {
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'status': self.status,
            'side': self.side,
            'lev': self.lev,
            'percent': self.percent,
            'tp': self.tp,
            'sl': self.sl,
            'roi_trigger': self.roi_trigger,
            'qty': self.qty,
            'entry': self.entry,
            'current_price': self.current_price,
            'position_open': self.position_open,
            'strategy_name': self.strategy_name,
            'last_side': self.last_side,
            'is_first_trade': self.is_first_trade,
            'average_down_count': self.average_down_count,
            'global_long_count': self.global_long_count,
            'global_short_count': self.global_short_count,
            'global_long_pnl': self.global_long_pnl,
            'global_short_pnl': self.global_short_pnl
        }

class GlobalMarketBot(BaseBot):
    def __init__(self, symbol, lev, percent, tp, sl, roi_trigger, ws_manager,
                 api_key, api_secret, bot_id=None, **kwargs):
        super().__init__(symbol, lev, percent, tp, sl, roi_trigger, ws_manager,
                         api_key, api_secret, "Global-Market-PnL-Khối-Lượng", 
                         bot_id=bot_id, **kwargs)

class BotManager:
    def __init__(self, api_key=None, api_secret=None):
        self.ws_manager = WebSocketManager()
        self.bots = {}
        self.running = True
        self.start_time = time.time()

        self.api_key = api_key
        self.api_secret = api_secret

        self.coin_manager = CoinManager()
        self.symbol_locks = defaultdict(threading.Lock)

        if api_key and api_secret:
            self._verify_api_connection()

    def _verify_api_connection(self):
        try:
            balance = get_balance(self.api_key, self.api_secret)
            if balance is None:
                return False
            else:
                return True
        except Exception:
            return False

    def add_bot(self, symbol, lev, percent, tp, sl, roi_trigger, strategy_type, bot_count=1, **kwargs):
        if sl == 0:
            sl = None
            
        if not self.api_key or not self.api_secret:
            return False
        
        if not self._verify_api_connection():
            return False
        
        bot_mode = kwargs.get('bot_mode', 'static')
        created_count = 0
        
        for i in range(bot_count):
            try:
                if bot_mode == 'static' and symbol:
                    bot_id = f"{symbol}_{strategy_type}_{i}_{int(time.time())}"
                    
                    if bot_id in self.bots:
                        continue
                    
                    bot_class = GlobalMarketBot
                    
                    bot = bot_class(
                        symbol, lev, percent, tp, sl, roi_trigger, self.ws_manager,
                        self.api_key, self.api_secret,
                        coin_manager=self.coin_manager,
                        symbol_locks=self.symbol_locks,
                        bot_id=bot_id
                    )
                    
                else:
                    bot_id = f"DYNAMIC_{strategy_type}_{i}_{int(time.time())}"
                    
                    if bot_id in self.bots:
                        continue
                    
                    bot_class = GlobalMarketBot
                    
                    bot = bot_class(
                        None, lev, percent, tp, sl, roi_trigger, self.ws_manager,
                        self.api_key, self.api_secret,
                        coin_manager=self.coin_manager,
                        symbol_locks=self.symbol_locks,
                        bot_id=bot_id
                    )
                
                self.bots[bot_id] = bot
                created_count += 1
                
            except Exception:
                continue
        
        return created_count > 0

    def stop_bot(self, bot_id):
        bot = self.bots.get(bot_id)
        if bot:
            bot.stop()
            del self.bots[bot_id]
            return True
        return False

    def stop_all(self):
        for bot_id in list(self.bots.keys()):
            self.stop_bot(bot_id)

    def get_bots_info(self):
        bots_info = []
        for bot_id, bot in self.bots.items():
            bots_info.append(bot.get_bot_info())
        return bots_info

    def get_system_info(self):
        try:
            balance = get_balance(self.api_key, self.api_secret)
            positions = get_positions(api_key=self.api_key, api_secret=self.api_secret)
            
            total_long_count = 0
            total_short_count = 0
            total_long_pnl = 0
            total_short_pnl = 0
            total_unrealized_pnl = 0
            
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:
                    unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                    total_unrealized_pnl += unrealized_pnl
                    
                    if position_amt > 0:
                        total_long_count += 1
                        total_long_pnl += unrealized_pnl
                    else:
                        total_short_count += 1
                        total_short_pnl += unrealized_pnl
            
            searching_bots = sum(1 for bot in self.bots.values() if bot.status == "searching")
            waiting_bots = sum(1 for bot in self.bots.values() if bot.status == "waiting")
            trading_bots = sum(1 for bot in self.bots.values() if bot.status == "open")
            
            return {
                'balance': balance,
                'total_bots': len(self.bots),
                'searching_bots': searching_bots,
                'waiting_bots': waiting_bots,
                'trading_bots': trading_bots,
                'total_long_count': total_long_count,
                'total_short_count': total_short_count,
                'total_long_pnl': total_long_pnl,
                'total_short_pnl': total_short_pnl,
                'total_unrealized_pnl': total_unrealized_pnl
            }
        except Exception:
            return {}
