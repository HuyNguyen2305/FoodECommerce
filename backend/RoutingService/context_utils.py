"""
Context Detection for Route Learning
====================================
Detects time-based and environmental contexts for route optimization
"""
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ContextDetector:
    """
    Detects context for route optimization (time of day, day of week, etc.)
    """
    
    def __init__(self):
        """Initialize context detector"""
        # Rush hour definitions for Ho Chi Minh City
        self.morning_rush = (7, 9)   # 7 AM - 9 AM
        self.lunch_rush = (11, 14)   # 11 AM - 2 PM
        self.evening_rush = (17, 20)  # 5 PM - 8 PM
        
        logger.info("Context detector initialized")
    
    def get_time_context(self, timestamp: datetime = None) -> str:
        """
        Get time-based context string
        
        Args:
            timestamp: Datetime to analyze (default: now)
            
        Returns:
            Context string like "weekday_morning", "weekend_evening"
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Determine day type
        day_type = self.get_day_type(timestamp)
        
        # Determine time period
        hour = timestamp.hour
        
        if 5 <= hour < 11:
            time_period = 'morning'
        elif 11 <= hour < 14:
            time_period = 'lunch'
        elif 14 <= hour < 17:
            time_period = 'afternoon'
        elif 17 <= hour < 22:
            time_period = 'evening'
        else:
            time_period = 'night'
        
        return f"{day_type}_{time_period}"
    
    def get_day_type(self, timestamp: datetime = None) -> str:
        """
        Get day type (weekday, weekend, holiday)
        
        Args:
            timestamp: Datetime to analyze (default: now)
            
        Returns:
            "weekday", "weekend", or "holiday"
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        weekday = timestamp.weekday()  # 0 = Monday, 6 = Sunday
        
        # Check if holiday (expandable)
        if self._is_holiday(timestamp):
            return 'holiday'
        
        # Weekend
        if weekday >= 5:  # Saturday or Sunday
            return 'weekend'
        
        return 'weekday'
    
    def get_rush_hour_multiplier(self, timestamp: datetime = None) -> float:
        """
        Get traffic multiplier based on rush hour
        
        Args:
            timestamp: Datetime to analyze (default: now)
            
        Returns:
            Multiplier (1.0 = normal, >1.0 = slower traffic)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        # Weekend traffic is generally lighter
        if weekday >= 5:
            base_multiplier = 0.85
        else:
            base_multiplier = 1.0
        
        # Check rush hours (only on weekdays)
        if weekday < 5:
            if self.morning_rush[0] <= hour < self.morning_rush[1]:
                return 1.4  # 40% slower during morning rush
            elif self.lunch_rush[0] <= hour < self.lunch_rush[1]:
                return 1.3  # 30% slower during lunch
            elif self.evening_rush[0] <= hour < self.evening_rush[1]:
                return 1.5  # 50% slower during evening rush (worst)
        
        # Late night is faster
        if 22 <= hour or hour < 5:
            return 0.75  # 25% faster late night
        
        return base_multiplier
    
    def _is_holiday(self, timestamp: datetime) -> bool:
        """
        Check if date is a Vietnamese holiday
        
        Args:
            timestamp: Date to check
            
        Returns:
            True if holiday
        """
        # Major Vietnamese holidays (expandable)
        # Format: (month, day)
        fixed_holidays = [
            (1, 1),   # New Year's Day
            (4, 30),  # Reunification Day
            (5, 1),   # Labor Day
            (9, 2),   # National Day
        ]
        
        month_day = (timestamp.month, timestamp.day)
        return month_day in fixed_holidays
    
    def get_weather_context(self, is_raining: bool = False) -> str:
        """
        Get weather context (expandable for weather API integration)
        
        Args:
            is_raining: Whether it's currently raining
            
        Returns:
            Weather context string
        """
        return 'rainy' if is_raining else 'clear'
    
    def get_weather_multiplier(self, is_raining: bool = False) -> float:
        """
        Get traffic multiplier based on weather
        
        Args:
            is_raining: Whether it's currently raining
            
        Returns:
            Multiplier (1.0 = normal, >1.0 = slower)
        """
        if is_raining:
            return 1.3  # 30% slower in rain
        return 1.0
    
    def get_combined_context(self, timestamp: datetime = None, 
                            is_raining: bool = False) -> Dict:
        """
        Get comprehensive context information
        
        Args:
            timestamp: Datetime to analyze (default: now)
            is_raining: Weather condition
            
        Returns:
            Dictionary with all context info
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        return {
            'time_context': self.get_time_context(timestamp),
            'day_type': self.get_day_type(timestamp),
            'hour': timestamp.hour,
            'weekday': timestamp.weekday(),
            'is_weekend': timestamp.weekday() >= 5,
            'rush_hour_multiplier': self.get_rush_hour_multiplier(timestamp),
            'weather_context': self.get_weather_context(is_raining),
            'weather_multiplier': self.get_weather_multiplier(is_raining),
            'combined_multiplier': self.get_rush_hour_multiplier(timestamp) * 
                                  self.get_weather_multiplier(is_raining),
            'timestamp': timestamp.isoformat()
        }
    
    def should_use_cached_route(self, times_used: int, context_samples: int = 0) -> bool:
        """
        Determine if cached route should be used based on confidence
        
        Args:
            times_used: Total times this route has been used
            context_samples: Samples in specific context
            
        Returns:
            True if cached route should be used
        """
        # Use context samples if available, otherwise total uses
        samples = context_samples if context_samples > 0 else times_used
        
        # Require at least 3 samples before trusting cache
        return samples >= 3


# Singleton instance
_context_detector = None

def get_context_detector() -> ContextDetector:
    """Get singleton context detector instance"""
    global _context_detector
    if _context_detector is None:
        _context_detector = ContextDetector()
    return _context_detector
