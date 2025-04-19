import json
import os
import hashlib
import streamlit as st
import time
from datetime import datetime, timedelta

# Path to the users database file
USERS_DB_PATH = "data/users.json"
# Path to the login attempts file
LOGIN_ATTEMPTS_PATH = "data/login_attempts.json"
# Remember me cookie duration (30 days)
REMEMBER_ME_DURATION = 30 * 24 * 60 * 60  # 30 days in seconds
# Maximum login attempts before lockout
MAX_LOGIN_ATTEMPTS = 4
# Lockout duration in minutes
LOCKOUT_DURATION = 15

def init_users_db():
    """Initialize the users database if it doesn't exist."""
    if not os.path.exists(os.path.dirname(USERS_DB_PATH)):
        os.makedirs(os.path.dirname(USERS_DB_PATH))
    
    if not os.path.exists(USERS_DB_PATH):
        # Create default admin user
        default_users = {
            "admin": {  # Keep admin as special case
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin"
            }
        }
        with open(USERS_DB_PATH, 'w') as f:
            json.dump(default_users, f)

def load_users():
    """Load the users database."""
    if not os.path.exists(USERS_DB_PATH):
        init_users_db()
    
    with open(USERS_DB_PATH, 'r') as f:
        return json.load(f)

def save_users(users):
    """Save the users database."""
    with open(USERS_DB_PATH, 'w') as f:
        json.dump(users, f)

def init_login_attempts():
    """Initialize the login attempts file if it doesn't exist."""
    if not os.path.exists(os.path.dirname(LOGIN_ATTEMPTS_PATH)):
        os.makedirs(os.path.dirname(LOGIN_ATTEMPTS_PATH))
    
    if not os.path.exists(LOGIN_ATTEMPTS_PATH):
        with open(LOGIN_ATTEMPTS_PATH, 'w') as f:
            json.dump({}, f)

def load_login_attempts():
    """Load the login attempts data."""
    if not os.path.exists(LOGIN_ATTEMPTS_PATH):
        init_login_attempts()
    
    with open(LOGIN_ATTEMPTS_PATH, 'r') as f:
        return json.load(f)

def save_login_attempts(attempts):
    """Save the login attempts data."""
    with open(LOGIN_ATTEMPTS_PATH, 'w') as f:
        json.dump(attempts, f)

def check_login_attempts(username):
    """Check if user has exceeded login attempts."""
    attempts = load_login_attempts()
    if username in attempts:
        attempt_data = attempts[username]
        if attempt_data["count"] >= MAX_LOGIN_ATTEMPTS:
            lockout_time = datetime.fromisoformat(attempt_data["last_attempt"])
            if datetime.now() < lockout_time + timedelta(minutes=LOCKOUT_DURATION):
                remaining_time = (lockout_time + timedelta(minutes=LOCKOUT_DURATION) - datetime.now()).seconds // 60
                return False, f"Account locked. Please try again in {remaining_time} minutes."
            else:
                # Reset attempts after lockout period
                attempts[username] = {"count": 0, "last_attempt": datetime.now().isoformat()}
                save_login_attempts(attempts)
    return True, None

def record_login_attempt(username, success):
    """Record a login attempt."""
    attempts = load_login_attempts()
    if username not in attempts:
        attempts[username] = {"count": 0, "last_attempt": datetime.now().isoformat()}
    
    if not success:
        attempts[username]["count"] += 1
        attempts[username]["last_attempt"] = datetime.now().isoformat()
    else:
        # Reset attempts on successful login
        attempts[username]["count"] = 0
    
    save_login_attempts(attempts)

def authenticate_user(username, password, remember_me=False):
    """Authenticate a user."""
    # Check login attempts first
    allowed, message = check_login_attempts(username)
    if not allowed:
        return False, None, message
    
    users = load_users()
    if username in users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if users[username]["password"] == hashed_password:
            if remember_me:
                # Set a cookie that expires in 30 days
                st.session_state["remember_me"] = True
                st.session_state["remember_me_expiry"] = time.time() + REMEMBER_ME_DURATION
            record_login_attempt(username, True)
            return True, users[username]["role"], None
    
    record_login_attempt(username, False)
    return False, None, "Invalid username or password"

def login_page():
    """Display the login page and handle authentication."""
    st.title("BT Phase Monitor Login")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    remember_me = st.checkbox("Remember me")
    
    if st.button("Login"):
        authenticated, role, message = authenticate_user(username, password, remember_me)
        if authenticated:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.rerun()
        else:
            st.error(message)

def signup_page():
    """Display the signup page and handle user creation."""
    st.title("Create New Account")
    
    email = st.text_input("Email")
    confirm_email = st.text_input("Confirm Email")
    password = st.text_input("Choose Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if st.button("Create Account"):
        if email != confirm_email:
            st.error("Emails do not match")
        elif password != confirm_password:
            st.error("Passwords do not match")
        else:
            success, message = create_user(email, password)
            if success:
                st.success(message)
                st.session_state["show_signup"] = False
                st.rerun()
            else:
                st.error(message)
    
    if st.button("Back to Login"):
        st.session_state["show_signup"] = False
        st.rerun()

def reset_password_page():
    """Display the password reset page."""
    st.title("Reset Password")
    
    if "reset_token" not in st.session_state:
        # First step: Request reset
        email = st.text_input("Enter your email")
        if st.button("Send Reset Link"):
            users = load_users()
            if email in users:
                token = generate_reset_token(email)
                # In a real app, you would send an email here
                st.success(f"Reset link has been sent to {email}")
                st.info("For demo purposes, here's your reset token:")
                st.code(token)
            else:
                st.error("No account found with that email")
    else:
        # Second step: Set new password
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Reset Password"):
            if new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, message = reset_password(st.session_state["reset_token"], new_password)
                if success:
                    st.success(message)
                    st.session_state["show_reset"] = False
                    st.session_state.pop("reset_token", None)
                    st.rerun()
                else:
                    st.error(message)
    
    if st.button("Back to Login"):
        st.session_state["show_reset"] = False
        st.session_state.pop("reset_token", None)
        st.rerun() 