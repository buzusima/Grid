"""
Smart Trading Enhancements - ฟังก์ชั่นเสริมแก้ไม้
smart_enhancements.py
เพิ่มความฉลาดให้ระบบเก่าโดยไม่แก้ core logic
Phase 1: Technical Analysis + Confidence Scoring + Rebate Optimization
"""

import math
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import MetaTrader5 as mt5

class ConfidenceLevel(Enum):
    VERY_LOW = 0      # 0-20%
    LOW = 1           # 21-40%
    MEDIUM = 2        # 41-60%
    HIGH = 3          # 61-80%
    VERY_HIGH = 4     # 81-100%

class OrderTier(Enum):
    QUALITY = "QUALITY"     # High confidence, larger lots
    VOLUME = "VOLUME"       # Low confidence, small lots for rebate
    SCALP = "SCALP"         # Quick profit + rebate
    HEDGE = "HEDGE"         # News events protection

@dataclass
class EnhancementResult:
    should_place: bool
    lot_size: float
    confidence: float
    tier: OrderTier
    reasoning: List[str]
    expected_profit: float
    rebate_value: float

@dataclass
class ProfitOpportunity:
    positions: List[int]
    expected_profit: float
    confidence: float
    tier: str
    reasoning: str
    rebate_bonus: float

class TechnicalAnalyzer:
    """🔬 Technical Analysis สำหรับ Enhancement"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.cache = {}
        self.cache_timeout = 30
        
    def get_price_data(self, timeframe=mt5.TIMEFRAME_M5, count=50) -> List[Dict]:
        """ดึงข้อมูลราคา with fallback"""
        try:
            cache_key = f"price_data_{timeframe}"
            now = datetime.now()
            
            # Check cache
            if cache_key in self.cache:
                cached_time, cached_data = self.cache[cache_key]
                if (now - cached_time).total_seconds() < self.cache_timeout:
                    return cached_data
            
            # Get real data from MT5
            rates = mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)
            
            if rates is not None and len(rates) > 10:
                price_data = []
                for rate in rates:
                    price_data.append({
                        'time': datetime.fromtimestamp(rate['time']),
                        'high': float(rate['high']),
                        'low': float(rate['low']),
                        'close': float(rate['close']),
                        'volume': int(rate['tick_volume'])
                    })
                
                self.cache[cache_key] = (now, price_data)
                return price_data
            
            # Fallback: create synthetic data
            return self.create_fallback_data()
            
        except Exception as e:
            print(f"⚠️ Price data fallback: {e}")
            return self.create_fallback_data()
    
    def create_fallback_data(self) -> List[Dict]:
        """สร้างข้อมูลสำรองเมื่อ MT5 ล้มเหลว"""
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                current_price = (tick.ask + tick.bid) / 2
                data = []
                for i in range(30):
                    # สร้างข้อมูลแบบ random walk
                    variation = (i - 15) * 0.3  
                    price = current_price + variation
                    data.append({
                        'time': datetime.now() - timedelta(minutes=i),
                        'high': price + 0.5,
                        'low': price - 0.5,
                        'close': price,
                        'volume': 100 + (i * 5)
                    })
                return list(reversed(data))
        except:
            pass
        
        # Ultimate fallback
        base_price = 2650.0
        return [{
            'time': datetime.now() - timedelta(minutes=i),
            'high': base_price + 0.5,
            'low': base_price - 0.5,
            'close': base_price,
            'volume': 100
        } for i in range(20)]

    def calculate_rsi(self, period: int = 14) -> Dict:
        """คำนวณ RSI"""
        try:
            price_data = self.get_price_data(count=period + 10)
            if len(price_data) < period:
                return {'value': 50, 'signal': 'NEUTRAL', 'confidence': 0.3}
            
            closes = [data['close'] for data in price_data[-period-1:]]
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [max(0, delta) for delta in deltas]
            losses = [max(0, -delta) for delta in deltas]
            
            avg_gain = sum(gains) / len(gains) if gains else 0.01
            avg_loss = sum(losses) / len(losses) if losses else 0.01
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Signal interpretation
            if rsi <= 25:
                return {'value': rsi, 'signal': 'STRONG_BUY', 'confidence': 0.9}
            elif rsi <= 30:
                return {'value': rsi, 'signal': 'BUY', 'confidence': 0.7}
            elif rsi >= 75:
                return {'value': rsi, 'signal': 'STRONG_SELL', 'confidence': 0.9}
            elif rsi >= 70:
                return {'value': rsi, 'signal': 'SELL', 'confidence': 0.7}
            else:
                return {'value': rsi, 'signal': 'NEUTRAL', 'confidence': 0.4}
                
        except Exception as e:
            print(f"⚠️ RSI calculation fallback: {e}")
            return {'value': 50, 'signal': 'NEUTRAL', 'confidence': 0.2}

    def calculate_bollinger_bands(self, period: int = 20) -> Dict:
        """คำนวณ Bollinger Bands"""
        try:
            price_data = self.get_price_data(count=period + 5)
            if len(price_data) < period:
                current_price = self.get_current_price()
                return {
                    'upper': current_price + 8,
                    'middle': current_price,
                    'lower': current_price - 8,
                    'signal': 'NEUTRAL',
                    'confidence': 0.3
                }
            
            closes = [data['close'] for data in price_data[-period:]]
            middle = sum(closes) / len(closes)
            
            # Calculate standard deviation
            variance = sum((close - middle) ** 2 for close in closes) / len(closes)
            std_dev = math.sqrt(variance)
            
            upper = middle + (std_dev * 2)
            lower = middle - (std_dev * 2)
            current_price = closes[-1]
            
            # Signal interpretation
            if current_price <= lower:
                signal, confidence = 'STRONG_BUY', 0.8
            elif current_price <= lower + std_dev * 0.5:
                signal, confidence = 'BUY', 0.6
            elif current_price >= upper:
                signal, confidence = 'STRONG_SELL', 0.8
            elif current_price >= upper - std_dev * 0.5:
                signal, confidence = 'SELL', 0.6
            else:
                signal, confidence = 'NEUTRAL', 0.4
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'signal': signal,
                'confidence': confidence,
                'current_position': 'LOWER' if current_price <= lower else 'UPPER' if current_price >= upper else 'MIDDLE'
            }
            
        except Exception as e:
            print(f"⚠️ Bollinger calculation fallback: {e}")
            current_price = self.get_current_price()
            return {
                'upper': current_price + 8,
                'middle': current_price,
                'lower': current_price - 8,
                'signal': 'NEUTRAL',
                'confidence': 0.2
            }

    def find_support_resistance(self) -> Dict:
        """หา Support/Resistance levels"""
        try:
            price_data = self.get_price_data(count=50)
            if len(price_data) < 10:
                current_price = self.get_current_price()
                return {
                    'support': current_price - 10,
                    'resistance': current_price + 10,
                    'confidence': 0.3
                }
            
            highs = [data['high'] for data in price_data]
            lows = [data['low'] for data in price_data]
            
            # Find recent significant levels
            support_level = min(lows[-20:])  # Lowest in last 20 periods
            resistance_level = max(highs[-20:])  # Highest in last 20 periods
            
            # Dynamic support/resistance based on recent price action
            recent_closes = [data['close'] for data in price_data[-10:]]
            recent_avg = sum(recent_closes) / len(recent_closes)
            
            # Adjust levels based on recent price action
            if recent_avg > (support_level + resistance_level) / 2:
                # Price in upper half - find closer support
                support_candidates = [low for low in lows[-20:] if recent_avg - 15 <= low <= recent_avg - 3]
                if support_candidates:
                    support_level = max(support_candidates)
            else:
                # Price in lower half - find closer resistance  
                resistance_candidates = [high for high in highs[-20:] if recent_avg + 3 <= high <= recent_avg + 15]
                if resistance_candidates:
                    resistance_level = min(resistance_candidates)
            
            confidence = 0.7 if len(price_data) >= 30 else 0.5
            
            return {
                'support': round(support_level, 2),
                'resistance': round(resistance_level, 2),
                'confidence': confidence
            }
            
        except Exception as e:
            print(f"⚠️ S/R calculation fallback: {e}")
            current_price = self.get_current_price()
            return {
                'support': current_price - 10,
                'resistance': current_price + 10,
                'confidence': 0.3
            }

    def analyze_trend(self) -> Dict:
        """วิเคราะห์เทรนด์"""
        try:
            price_data = self.get_price_data(count=30)
            if len(price_data) < 20:
                return {'direction': 'SIDEWAYS', 'strength': 0.3, 'confidence': 0.3}
            
            closes = [data['close'] for data in price_data]
            
            # Calculate moving averages
            ma_fast = sum(closes[-10:]) / 10  # 10-period MA
            ma_slow = sum(closes[-20:]) / 20  # 20-period MA
            
            # Calculate trend strength
            recent_price = closes[-1]
            oldest_price = closes[-20]
            price_change = recent_price - oldest_price
            
            # Determine trend direction
            if ma_fast > ma_slow and price_change > 2:
                direction = 'UPTREND'
                strength = min(0.9, abs(price_change) / 20)
            elif ma_fast < ma_slow and price_change < -2:
                direction = 'DOWNTREND'
                strength = min(0.9, abs(price_change) / 20)
            else:
                direction = 'SIDEWAYS'
                strength = 0.4
            
            confidence = 0.8 if abs(ma_fast - ma_slow) > 1 else 0.5
            
            return {
                'direction': direction,
                'strength': round(strength, 2),
                'confidence': round(confidence, 2),
                'ma_fast': round(ma_fast, 2),
                'ma_slow': round(ma_slow, 2)
            }
            
        except Exception as e:
            print(f"⚠️ Trend analysis fallback: {e}")
            return {'direction': 'SIDEWAYS', 'strength': 0.4, 'confidence': 0.3}

    def get_current_price(self) -> float:
        """ได้ราคาปัจจุบัน"""
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                return (tick.ask + tick.bid) / 2
        except:
            pass
        return 2650.0  # Fallback gold price

class ConfidenceScorer:
    """🎯 ระบบให้คะแนนความมั่นใจ 0-100"""
    
    def __init__(self, technical_analyzer: TechnicalAnalyzer):
        self.technical = technical_analyzer
        
    def calculate_confidence_score(self, price: float, direction: str) -> Dict:
        """คำนวณคะแนนความมั่นใจสำหรับการวางไม้"""
        try:
            # Get technical indicators
            rsi_data = self.technical.calculate_rsi()
            bb_data = self.technical.calculate_bollinger_bands()
            sr_data = self.technical.find_support_resistance()
            trend_data = self.technical.analyze_trend()
            
            current_price = self.technical.get_current_price()
            
            # Calculate individual scores
            scores = {}
            reasoning = []
            
            # 1. RSI Score (25 points max)
            rsi_score = self.score_rsi(rsi_data, direction)
            scores['rsi'] = rsi_score
            if rsi_score > 15:
                reasoning.append(f"RSI {rsi_data['signal']} ({rsi_data['value']:.1f})")
            
            # 2. Bollinger Bands Score (25 points max)
            bb_score = self.score_bollinger_bands(bb_data, price, direction)
            scores['bollinger'] = bb_score
            if bb_score > 15:
                reasoning.append(f"BB {bb_data['signal']} ({bb_data['current_position']})")
            
            # 3. Support/Resistance Score (25 points max)
            sr_score = self.score_support_resistance(sr_data, price, direction)
            scores['support_resistance'] = sr_score
            if sr_score > 15:
                reasoning.append(f"S/R level match")
            
            # 4. Trend Alignment Score (25 points max)
            trend_score = self.score_trend_alignment(trend_data, direction)
            scores['trend'] = trend_score
            if trend_score > 15:
                reasoning.append(f"Trend {trend_data['direction']}")
            
            # Calculate total score
            total_score = sum(scores.values())
            
            # Determine confidence level
            if total_score >= 80:
                level = ConfidenceLevel.VERY_HIGH
            elif total_score >= 60:
                level = ConfidenceLevel.HIGH
            elif total_score >= 40:
                level = ConfidenceLevel.MEDIUM
            elif total_score >= 20:
                level = ConfidenceLevel.LOW
            else:
                level = ConfidenceLevel.VERY_LOW
            
            return {
                'total_score': round(total_score, 1),
                'level': level,
                'scores': scores,
                'reasoning': reasoning,
                'technical_data': {
                    'rsi': rsi_data,
                    'bollinger': bb_data,
                    'support_resistance': sr_data,
                    'trend': trend_data
                }
            }
            
        except Exception as e:
            print(f"⚠️ Confidence scoring fallback: {e}")
            return {
                'total_score': 30.0,
                'level': ConfidenceLevel.LOW,
                'scores': {'fallback': 30},
                'reasoning': ['Technical analysis unavailable'],
                'technical_data': {}
            }

    def score_rsi(self, rsi_data: Dict, direction: str) -> float:
        """คะแนน RSI (0-25 points)"""
        rsi_value = rsi_data['value']
        rsi_signal = rsi_data['signal']
        
        if direction == 'BUY':
            if rsi_signal == 'STRONG_BUY':
                return 25
            elif rsi_signal == 'BUY':
                return 20
            elif rsi_signal == 'NEUTRAL' and rsi_value < 50:
                return 10
            elif rsi_signal == 'SELL':
                return 5
            else:
                return 0
        else:  # SELL
            if rsi_signal == 'STRONG_SELL':
                return 25
            elif rsi_signal == 'SELL':
                return 20
            elif rsi_signal == 'NEUTRAL' and rsi_value > 50:
                return 10
            elif rsi_signal == 'BUY':
                return 5
            else:
                return 0

    def score_bollinger_bands(self, bb_data: Dict, price: float, direction: str) -> float:
        """คะแนน Bollinger Bands (0-25 points)"""
        bb_signal = bb_data['signal']
        position = bb_data['current_position']
        
        if direction == 'BUY':
            if bb_signal == 'STRONG_BUY' and position == 'LOWER':
                return 25
            elif bb_signal == 'BUY':
                return 20
            elif position == 'LOWER':
                return 15
            elif position == 'MIDDLE':
                return 8
            else:
                return 0
        else:  # SELL
            if bb_signal == 'STRONG_SELL' and position == 'UPPER':
                return 25
            elif bb_signal == 'SELL':
                return 20
            elif position == 'UPPER':
                return 15
            elif position == 'MIDDLE':
                return 8
            else:
                return 0

    def score_support_resistance(self, sr_data: Dict, price: float, direction: str) -> float:
        """คะแนน Support/Resistance (0-25 points)"""
        support = sr_data['support']
        resistance = sr_data['resistance']
        confidence = sr_data['confidence']
        
        base_score = 25 * confidence
        
        if direction == 'BUY':
            # ดีถ้าใกล้ support
            distance_to_support = abs(price - support)
            if distance_to_support <= 2:
                return base_score
            elif distance_to_support <= 5:
                return base_score * 0.7
            else:
                return base_score * 0.3
        else:  # SELL
            # ดีถ้าใกล้ resistance
            distance_to_resistance = abs(price - resistance)
            if distance_to_resistance <= 2:
                return base_score
            elif distance_to_resistance <= 5:
                return base_score * 0.7
            else:
                return base_score * 0.3

    def score_trend_alignment(self, trend_data: Dict, direction: str) -> float:
        """คะแนน Trend Alignment (0-25 points)"""
        trend_direction = trend_data['direction']
        trend_strength = trend_data['strength']
        confidence = trend_data['confidence']
        
        base_score = 25 * confidence * trend_strength
        
        if direction == 'BUY' and trend_direction == 'UPTREND':
            return base_score
        elif direction == 'SELL' and trend_direction == 'DOWNTREND':
            return base_score
        elif trend_direction == 'SIDEWAYS':
            return base_score * 0.6  # Sideways ดีสำหรับ grid
        else:
            return base_score * 0.2  # Against trend

class RebateOptimizer:
    """💰 เพิ่มประสิทธิภาพ Rebate"""
    
    def __init__(self, rebate_per_lot: float = 35.0, spread_cost: float = 4.0):
        self.rebate_per_lot = rebate_per_lot
        self.spread_cost = spread_cost
        self.daily_volume = 0
        self.daily_rebate = 0
        self.target_daily_rebate = 50.0
        
    def calculate_rebate_value(self, lot_size: float) -> float:
        """คำนวณมูลค่า rebate"""
        gross_rebate = lot_size * self.rebate_per_lot
        net_rebate = gross_rebate - (lot_size * self.spread_cost)
        return max(0, net_rebate)
    
    def is_rebate_worthy(self, lot_size: float, expected_profit: float) -> bool:
        """เช็คว่าควรทำเพื่อ rebate หรือไม่"""
        rebate_value = self.calculate_rebate_value(lot_size)
        total_expected = expected_profit + rebate_value
        return total_expected > 0 and rebate_value >= 0.1
    
    def suggest_volume_boost(self, current_volume: float, target_rebate: float) -> List[Dict]:
        """แนะนำการเพิ่ม volume เพื่อ rebate"""
        needed_volume = (target_rebate - self.daily_rebate) / (self.rebate_per_lot - self.spread_cost)
        
        if needed_volume <= 0:
            return []
        
        suggestions = []
        
        # Micro scalping orders
        micro_orders = min(10, int(needed_volume / 0.003))
        for i in range(micro_orders):
            suggestions.append({
                'type': 'MICRO_SCALP',
                'lot_size': 0.003,
                'profit_target': 1.0,
                'rebate_value': self.calculate_rebate_value(0.003),
                'reasoning': 'Volume boost for rebate'
            })
        
        return suggestions

class SmartEnhancements:
    """🧠 Main Enhancement Class - ฟังก์ชั่นเสริมหลัก"""
    
    def __init__(self, symbol: str = "XAUUSD.v", config: Dict = None):
        self.symbol = symbol
        self.config = config or {}
        
        # Initialize components
        self.technical = TechnicalAnalyzer(symbol)
        self.confidence_scorer = ConfidenceScorer(self.technical)
        self.rebate_optimizer = RebateOptimizer(
            rebate_per_lot=self.config.get('rebate_per_lot', 35.0),
            spread_cost=self.config.get('spread_cost', 4.0)
        )
        
        # Settings
        self.min_confidence_threshold = self.config.get('min_confidence', 30)
        self.quality_confidence_threshold = self.config.get('quality_confidence', 60)
        self.enabled = self.config.get('enabled', True)
        
        print("🧠 Smart Enhancements Initialized")
        print(f"   Symbol: {symbol}")
        print(f"   Min Confidence: {self.min_confidence_threshold}%")
        print(f"   Quality Threshold: {self.quality_confidence_threshold}%")
        print(f"   Rebate: ${self.rebate_optimizer.rebate_per_lot}/lot")

    def enhance_grid_order(self, original_params: Dict) -> EnhancementResult:
        """🎯 เสริมการวางไม้ด้วย Technical Analysis"""
        try:
            if not self.enabled:
                return EnhancementResult(
                    should_place=True,
                    lot_size=original_params['base_lot'],
                    confidence=50.0,
                    tier=OrderTier.VOLUME,
                    reasoning=['Enhancement disabled'],
                    expected_profit=0,
                    rebate_value=0
                )
            
            price = original_params['price']
            direction = original_params['direction']
            base_lot = original_params['base_lot']
            
            # Calculate confidence score
            confidence_data = self.confidence_scorer.calculate_confidence_score(price, direction)
            total_confidence = confidence_data['total_score']
            reasoning = confidence_data['reasoning']
            
            # Determine if should place order
            should_place = total_confidence >= self.min_confidence_threshold
            
            # Calculate enhanced lot size
            if total_confidence >= self.quality_confidence_threshold:
                # High confidence = Quality tier
                lot_multiplier = 1.0 + (total_confidence - self.quality_confidence_threshold) / 100
                enhanced_lot = base_lot * min(lot_multiplier, 2.0)  # Max 2x
                tier = OrderTier.QUALITY
            elif total_confidence >= self.min_confidence_threshold:
                # Medium confidence = Normal sizing
                enhanced_lot = base_lot
                tier = OrderTier.VOLUME
            else:
                # Low confidence = Small lot for rebate only
                enhanced_lot = max(base_lot * 0.3, 0.003)  # Min 0.003 for rebate
                tier = OrderTier.VOLUME
                
            # Calculate expected values
            expected_profit = self.estimate_expected_profit(confidence_data, enhanced_lot)
            rebate_value = self.rebate_optimizer.calculate_rebate_value(enhanced_lot)
            
            # Add reasoning
            enhanced_reasoning = reasoning.copy()
            enhanced_reasoning.append(f"Confidence: {total_confidence:.1f}%")
            enhanced_reasoning.append(f"Tier: {tier.value}")
            
            if not should_place:
                enhanced_reasoning.append(f"Below threshold ({self.min_confidence_threshold}%)")
            
            return EnhancementResult(
                should_place=should_place,
                lot_size=round(enhanced_lot, 3),
                confidence=total_confidence,
                tier=tier,
                reasoning=enhanced_reasoning,
                expected_profit=round(expected_profit, 2),
                rebate_value=round(rebate_value, 2)
            )
            
        except Exception as e:
            print(f"❌ Enhancement error: {e}")
            # Safe fallback
            return EnhancementResult(
                should_place=True,
                lot_size=original_params['base_lot'],
                confidence=30.0,
                tier=OrderTier.VOLUME,
                reasoning=['Enhancement error - using defaults'],
                expected_profit=0,
                rebate_value=0
            )

    def enhance_profit_taking(self, original_pairs: List[Dict]) -> List[ProfitOpportunity]:
        """💰 เสริมการปิดไม้ด้วย Technical + Rebate optimization"""
        try:
            if not self.enabled or not original_pairs:
                return [ProfitOpportunity(
                    positions=pair.get('positions', []),
                    expected_profit=pair.get('expected_profit', 0),
                    confidence=50.0,
                    tier='ORIGINAL',
                    reasoning='No enhancement',
                    rebate_bonus=0
                ) for pair in original_pairs]
            
            enhanced_opportunities = []
            
            # Get current technical state
            current_price = self.technical.get_current_price()
            rsi_data = self.technical.calculate_rsi()
            bb_data = self.technical.calculate_bollinger_bands()
            sr_data = self.technical.find_support_resistance()
            
            for pair in original_pairs:
                try:
                    positions = pair.get('positions', [])
                    original_profit = pair.get('expected_profit', 0)
                    
                    # Calculate technical exit signals
                    exit_confidence = self.calculate_exit_confidence(
                        rsi_data, bb_data, sr_data, current_price, original_profit
                    )
                    
                    # Calculate rebate bonus
                    estimated_lots = len(positions) * 0.01  # Estimate
                    rebate_bonus = self.rebate_optimizer.calculate_rebate_value(estimated_lots)
                    
                    # Determine tier based on confidence
                    if exit_confidence >= 80:
                        tier = 'STRONG_EXIT'
                        reasoning = f"Strong technical exit signals ({exit_confidence:.0f}%)"
                    elif exit_confidence >= 60:
                        tier = 'GOOD_EXIT'
                        reasoning = f"Good technical signals + profit (${original_profit:.2f})"
                    elif original_profit >= 5:
                        tier = 'PROFIT_SECURE'
                        reasoning = f"Secure profit (${original_profit:.2f}) + rebate"
                    else:
                        tier = 'REBATE_FOCUS'
                        reasoning = f"Small profit + rebate bonus (${rebate_bonus:.2f})"
                    
                    enhanced_opportunities.append(ProfitOpportunity(
                        positions=positions,
                        expected_profit=original_profit,
                        confidence=exit_confidence,
                        tier=tier,
                        reasoning=reasoning,
                        rebate_bonus=rebate_bonus
                    ))
                    
                except Exception as e:
                    print(f"⚠️ Pair enhancement error: {e}")
                    # Keep original pair
                    enhanced_opportunities.append(ProfitOpportunity(
                        positions=pair.get('positions', []),
                        expected_profit=pair.get('expected_profit', 0),
                        confidence=50.0,
                        tier='ORIGINAL',
                        reasoning='Enhancement error',
                        rebate_bonus=0
                    ))
            
            # Sort by combined value (profit + rebate + confidence)
            enhanced_opportunities.sort(
                key=lambda x: x.expected_profit + x.rebate_bonus + (x.confidence / 100 * 5),
                reverse=True
            )
            
            return enhanced_opportunities
            
        except Exception as e:
            print(f"❌ Profit enhancement error: {e}")
            return []

    def boost_rebate_volume(self, current_status: Dict) -> List[Dict]:
        """🚀 เพิ่ม Volume สำหรับ Rebate"""
        try:
            if not self.enabled:
                return []
            
            current_volume = current_status.get('current_volume', 0)
            target_rebate = current_status.get('target_rebate', self.rebate_optimizer.target_daily_rebate)
            market_condition = current_status.get('market_condition', 'UNKNOWN')
            
            volume_boosts = []
            
            # 1. Micro-scalping opportunities
            if market_condition in ['RANGING', 'LOW_VOLATILITY']:
                micro_scalps = self.generate_micro_scalp_opportunities()
                volume_boosts.extend(micro_scalps)
            
            # 2. News event hedging (if applicable)
            news_hedges = self.generate_news_hedge_opportunities()
            volume_boosts.extend(news_hedges)
            
            # 3. End-of-session volume push
            if self.should_push_volume():
                volume_push = self.generate_volume_push_orders()
                volume_boosts.extend(volume_push)
            
            return volume_boosts
            
        except Exception as e:
            print(f"❌ Volume boost error: {e}")
            return []

    def generate_micro_scalp_opportunities(self) -> List[Dict]:
        """สร้างโอกาส micro-scalping"""
        opportunities = []
        current_price = self.technical.get_current_price()
        
        # Create small scalp orders around current price
        for offset in [1, 2, 3]:
            buy_price = current_price - offset
            sell_price = current_price + offset
            
            opportunities.extend([
                {
                    'type': 'MICRO_SCALP',
                    'direction': 'BUY',
                    'price': buy_price,
                    'lot_size': 0.003,
                    'profit_target': offset + 1,
                    'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.003),
                    'reasoning': f'Micro scalp BUY @${buy_price:.2f}'
                },
                {
                    'type': 'MICRO_SCALP',
                    'direction': 'SELL',
                    'price': sell_price,
                    'lot_size': 0.003,
                    'profit_target': offset + 1,
                    'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.003),
                    'reasoning': f'Micro scalp SELL @${sell_price:.2f}'
                }
            ])
        
        return opportunities[:4]  # Limit to 4 opportunities

    def generate_news_hedge_opportunities(self) -> List[Dict]:
        """สร้างโอกาส hedge ช่วงข่าว"""
        # Simple news hedge logic
        current_price = self.technical.get_current_price()
        
        return [
            {
                'type': 'NEWS_HEDGE',
                'direction': 'BUY',
                'price': current_price - 5,
                'lot_size': 0.005,
                'profit_target': 3,
                'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.005),
                'reasoning': 'News hedge BUY protection'
            },
            {
                'type': 'NEWS_HEDGE',
                'direction': 'SELL',
                'price': current_price + 5,
                'lot_size': 0.005,
                'profit_target': 3,
                'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.005),
                'reasoning': 'News hedge SELL protection'
            }
        ]

    def generate_volume_push_orders(self) -> List[Dict]:
        """สร้าง orders สำหรับ volume push"""
        current_price = self.technical.get_current_price()
        
        return [
            {
                'type': 'VOLUME_PUSH',
                'direction': 'BUY',
                'price': current_price - 3,
                'lot_size': 0.004,
                'profit_target': 2,
                'rebate_value': self.rebate_optimizer.calculate_rebate_value(0.004),
                'reasoning': 'Volume push for daily rebate target'
            }
        ]

    def should_push_volume(self) -> bool:
        """เช็คว่าควร push volume หรือไม่"""
        # Simple logic: push if daily rebate below target
        return self.rebate_optimizer.daily_rebate < self.rebate_optimizer.target_daily_rebate * 0.8

    def calculate_exit_confidence(self, rsi_data: Dict, bb_data: Dict, sr_data: Dict, 
                                current_price: float, profit: float) -> float:
        """คำนวณความมั่นใจในการปิดไม้"""
        confidence = 0
        
        # Profit-based confidence
        if profit >= 10:
            confidence += 30
        elif profit >= 5:
            confidence += 20
        elif profit >= 2:
            confidence += 10
        
        # Technical-based confidence
        rsi_value = rsi_data.get('value', 50)
        if rsi_value >= 70 or rsi_value <= 30:
            confidence += 25
        elif rsi_value >= 60 or rsi_value <= 40:
            confidence += 15
        
        # Bollinger position
        bb_position = bb_data.get('current_position', 'MIDDLE')
        if bb_position in ['UPPER', 'LOWER']:
            confidence += 20
        elif bb_position == 'MIDDLE':
            confidence += 10
        
        # Support/Resistance proximity
        support = sr_data.get('support', current_price - 10)
        resistance = sr_data.get('resistance', current_price + 10)
        
        if abs(current_price - resistance) <= 2 or abs(current_price - support) <= 2:
            confidence += 15
        
        return min(confidence, 100)

    def estimate_expected_profit(self, confidence_data: Dict, lot_size: float) -> float:
        """ประเมินกำไรที่คาดหวัง"""
        confidence = confidence_data['total_score']
        
        # Base profit estimation based on confidence
        base_profit_points = 30 + (confidence / 100 * 50)  # 30-80 points
        
        # Convert to dollar value
        profit_per_point = lot_size * 1.0  # $1 per point for standard lot
        estimated_profit = base_profit_points * profit_per_point
        
        return estimated_profit

    def get_enhancement_status(self) -> Dict:
        """สถานะของ Enhancement System"""
        return {
            'enabled': self.enabled,
            'symbol': self.symbol,
            'min_confidence': self.min_confidence_threshold,
            'quality_threshold': self.quality_confidence_threshold,
            'daily_rebate': self.rebate_optimizer.daily_rebate,
            'daily_volume': self.rebate_optimizer.daily_volume,
            'rebate_target': self.rebate_optimizer.target_daily_rebate,
            'last_update': datetime.now().isoformat()
        }

    def update_daily_stats(self, volume: float, rebate: float):
        """อัพเดตสถิติรายวัน"""
        self.rebate_optimizer.daily_volume += volume
        self.rebate_optimizer.daily_rebate += rebate

# Test function
def test_smart_enhancements():
    """ทดสอบ Smart Enhancements"""
    print("🧪 Testing Smart Enhancements...")
    
    # Initialize
    enhancer = SmartEnhancements("XAUUSD.v", {
        'min_confidence': 30,
        'quality_confidence': 60,
        'rebate_per_lot': 35.0,
        'enabled': True
    })
    
    # Test 1: Grid Order Enhancement
    print("\n📊 Test 1: Grid Order Enhancement")
    test_params = {
        'price': 2650.0,
        'direction': 'BUY',
        'base_lot': 0.01
    }
    
    result = enhancer.enhance_grid_order(test_params)
    print(f"Should Place: {result.should_place}")
    print(f"Lot Size: {result.lot_size}")
    print(f"Confidence: {result.confidence}%")
    print(f"Tier: {result.tier.value}")
    print(f"Reasoning: {', '.join(result.reasoning)}")
    print(f"Expected Profit: ${result.expected_profit:.2f}")
    print(f"Rebate Value: ${result.rebate_value:.2f}")
    
    # Test 2: Profit Taking Enhancement
    print("\n💰 Test 2: Profit Taking Enhancement")
    test_pairs = [
        {'positions': [1, 2], 'expected_profit': 8.5},
        {'positions': [3], 'expected_profit': 3.2}
    ]
    
    enhanced_pairs = enhancer.enhance_profit_taking(test_pairs)
    for i, pair in enumerate(enhanced_pairs):
        print(f"Pair {i+1}: ${pair.expected_profit:.2f} profit, {pair.confidence:.0f}% confidence")
        print(f"  Tier: {pair.tier}, Rebate: ${pair.rebate_bonus:.2f}")
        print(f"  Reasoning: {pair.reasoning}")
    
    # Test 3: Volume Boost
    print("\n🚀 Test 3: Volume Boost")
    status = {
        'current_volume': 0.05,
        'target_rebate': 50.0,
        'market_condition': 'RANGING'
    }
    
    volume_boosts = enhancer.boost_rebate_volume(status)
    print(f"Generated {len(volume_boosts)} volume boost opportunities:")
    for boost in volume_boosts[:3]:
        print(f"  {boost['type']}: {boost['direction']} @${boost['price']:.2f}")
        print(f"    Lot: {boost['lot_size']}, Rebate: ${boost['rebate_value']:.2f}")
    
    print("\n✅ Smart Enhancements Test Completed!")

if __name__ == "__main__":
    test_smart_enhancements()