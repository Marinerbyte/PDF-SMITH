import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserStateManager:
    """Manage user states and data for multi-step operations"""
    
    def __init__(self):
        self.user_states: Dict[int, str] = {}
        self.user_data: Dict[int, Dict[str, Any]] = {}
    
    def set_state(self, user_id: int, state: str):
        """Set user state"""
        self.user_states[user_id] = state
        logger.debug(f"User {user_id} state set to: {state}")
    
    def get_state(self, user_id: int) -> Optional[str]:
        """Get user state"""
        return self.user_states.get(user_id)
    
    def clear_state(self, user_id: int):
        """Clear user state"""
        if user_id in self.user_states:
            del self.user_states[user_id]
            logger.debug(f"User {user_id} state cleared")
    
    def set_user_data(self, user_id: int, key: str, value: Any):
        """Set user data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id][key] = value
        logger.debug(f"User {user_id} data set: {key}")
    
    def get_user_data(self, user_id: int, key: str) -> Any:
        """Get user data"""
        return self.user_data.get(user_id, {}).get(key)
    
    def clear_user_data(self, user_id: int, key: str):
        """Clear specific user data"""
        if user_id in self.user_data and key in self.user_data[user_id]:
            del self.user_data[user_id][key]
            logger.debug(f"User {user_id} data cleared: {key}")
    
    def clear_user_state(self, user_id: int):
        """Clear all user state and data"""
        self.clear_state(user_id)
        if user_id in self.user_data:
            del self.user_data[user_id]
            logger.debug(f"User {user_id} all data cleared")
    
    def get_all_user_data(self, user_id: int) -> Dict[str, Any]:
        """Get all user data"""
        return self.user_data.get(user_id, {})
    
    def has_state(self, user_id: int) -> bool:
        """Check if user has an active state"""
        return user_id in self.user_states
    
    def get_active_users(self) -> list:
        """Get list of users with active states"""
        return list(self.user_states.keys())
    
    def cleanup_inactive_users(self, active_threshold_hours: int = 24):
        """Clean up data for inactive users (placeholder for future enhancement)"""
        # This could be enhanced to track timestamps and clean up old data
        # For now, data persists until manually cleared
        pass
