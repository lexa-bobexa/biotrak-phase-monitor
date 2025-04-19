import streamlit as st
import time
from typing import Dict, Any, Optional, Literal
from logic.logging_config import logger

class SessionManager:
    """Manages Streamlit session state initialization and access."""
    
    # Define default values for session state variables
    DEFAULT_STATE: Dict[str, Any] = {
        "authenticated": False,
        "role": Optional[Literal["admin", "user"]],
        "username": Optional[str],
        "show_admin": False,
        "processing": False,
        "remember_me": False,
        "remember_me_expiry": Optional[float]
    }

    @classmethod
    def initialize_session_state(cls) -> None:
        """Initialize all session state variables with default values if they don't exist."""
        for key, default_value in cls.DEFAULT_STATE.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
                logger.debug(f"Initialized session state: {key} = {default_value}")

    @classmethod
    def set_auth_state(cls, username: str, role: str, remember_me: bool = False) -> None:
        """Set authentication state for a user.
        
        Args:
            username: The username of the authenticated user
            role: The role of the authenticated user
            remember_me: Whether to remember the user's session
        """
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["role"] = role
        
        if remember_me:
            # Set remember me cookie to expire in 30 days
            st.session_state["remember_me"] = True
            st.session_state["remember_me_expiry"] = time.time() + (30 * 24 * 60 * 60)
            logger.info(f"Set remember me cookie for user: {username}")
        else:
            st.session_state["remember_me"] = False
            st.session_state["remember_me_expiry"] = None

    @classmethod
    def clear_session(cls) -> None:
        """Clear all session state variables."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        logger.info("Cleared all session state variables")

    @classmethod
    def get_state(cls, key: str) -> Any:
        """Get a session state value.
        
        Args:
            key: The session state key to retrieve
            
        Returns:
            The value of the session state key, or None if it doesn't exist
        """
        return st.session_state.get(key)

    @classmethod
    def set_state(cls, key: str, value: Any) -> None:
        """Set a session state value.
        
        Args:
            key: The session state key to set
            value: The value to set
        """
        st.session_state[key] = value
        logger.debug(f"Set session state: {key} = {value}")

    @classmethod
    def check_remember_me(cls) -> bool:
        """Check if the user has a valid remember me cookie.
        
        Returns:
            bool: True if the remember me cookie is valid, False otherwise
        """
        if cls.get_state("remember_me") and cls.get_state("remember_me_expiry"):
            if time.time() < cls.get_state("remember_me_expiry"):
                return True
        return False 