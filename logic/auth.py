import json
import os
import hashlib
import streamlit as st
import secrets
import time
from datetime import datetime, timedelta

# Path to the users database file
USERS_DB_PATH = "data/users.json"
# Path to the password reset tokens file
RESET_TOKENS_PATH = "data/reset_tokens.json"
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
                "role": "admin",
                "email": "admin@example.com"  # Add email for password reset
            }
        }
        with open(USERS_DB_PATH, 'w') as f:
            json.dump(default_users, f)

def init_reset_tokens():
    """Initialize the reset tokens file if it doesn't exist."""
    if not os.path.exists(RESET_TOKENS_PATH):
        with open(RESET_TOKENS_PATH, 'w') as f:
            json.dump({}, f)

def init_login_attempts():
    """Initialize the login attempts file if it doesn't exist."""
    if not os.path.exists(os.path.dirname(LOGIN_ATTEMPTS_PATH)):
        os.makedirs(os.path.dirname(LOGIN_ATTEMPTS_PATH))
    
    if not os.path.exists(LOGIN_ATTEMPTS_PATH):
        with open(LOGIN_ATTEMPTS_PATH, 'w') as f:
            json.dump({}, f)

def load_users():
    """Load users from the database."""
    if not os.path.exists(USERS_DB_PATH):
        init_users_db()
    
    with open(USERS_DB_PATH, 'r') as f:
        return json.load(f)

def save_users(users):
    """Save users to the database."""
    with open(USERS_DB_PATH, 'w') as f:
        json.dump(users, f)

def load_reset_tokens():
    """Load reset tokens from the database."""
    if not os.path.exists(RESET_TOKENS_PATH):
        init_reset_tokens()
    
    with open(RESET_TOKENS_PATH, 'r') as f:
        return json.load(f)

def save_reset_tokens(tokens):
    """Save reset tokens to the database."""
    with open(RESET_TOKENS_PATH, 'w') as f:
        json.dump(tokens, f)

def generate_reset_token(email):
    """Generate a password reset token for a user."""
    tokens = load_reset_tokens()
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=1)  # Token expires in 1 hour
    
    tokens[token] = {
        "email": email,
        "expiry": expiry.isoformat()
    }
    save_reset_tokens(tokens)
    return token

def validate_reset_token(token):
    """Validate a password reset token."""
    tokens = load_reset_tokens()
    if token in tokens:
        token_data = tokens[token]
        expiry = datetime.fromisoformat(token_data["expiry"])
        if datetime.now() < expiry:
            return True, token_data["email"]
    return False, None

def clear_reset_token(token):
    """Clear a used reset token."""
    tokens = load_reset_tokens()
    if token in tokens:
        del tokens[token]
        save_reset_tokens(tokens)

def reset_password(token, new_password):
    """Reset a user's password using a valid token."""
    valid, email = validate_reset_token(token)
    if not valid:
        return False, "Invalid or expired reset token"
    
    users = load_users()
    if email in users:
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        users[email]["password"] = hashed_password
        save_users(users)
        clear_reset_token(token)
        return True, "Password reset successful"
    return False, "User not found"

def load_login_attempts():
    """Load login attempts from the database."""
    if not os.path.exists(LOGIN_ATTEMPTS_PATH):
        init_login_attempts()
    
    with open(LOGIN_ATTEMPTS_PATH, 'r') as f:
        return json.load(f)

def save_login_attempts(attempts):
    """Save login attempts to the database."""
    with open(LOGIN_ATTEMPTS_PATH, 'w') as f:
        json.dump(attempts, f)

def check_login_attempts(email):
    """Check if user has exceeded login attempts."""
    attempts = load_login_attempts()
    if email in attempts:
        attempt_data = attempts[email]
        if attempt_data["count"] >= MAX_LOGIN_ATTEMPTS:
            lockout_time = datetime.fromisoformat(attempt_data["last_attempt"])
            if datetime.now() < lockout_time + timedelta(minutes=LOCKOUT_DURATION):
                remaining_time = (lockout_time + timedelta(minutes=LOCKOUT_DURATION) - datetime.now()).seconds // 60
                return False, f"Account locked. Please try again in {remaining_time} minutes."
            else:
                # Reset attempts after lockout period
                attempts[email] = {"count": 0, "last_attempt": datetime.now().isoformat()}
                save_login_attempts(attempts)
    return True, None

def record_login_attempt(email, success):
    """Record a login attempt."""
    attempts = load_login_attempts()
    if email not in attempts:
        attempts[email] = {"count": 0, "last_attempt": datetime.now().isoformat()}
    
    if not success:
        attempts[email]["count"] += 1
        attempts[email]["last_attempt"] = datetime.now().isoformat()
    else:
        # Reset attempts on successful login
        attempts[email]["count"] = 0
    
    save_login_attempts(attempts)

def authenticate_user(email, password, remember_me=False):
    """Authenticate a user."""
    # Check login attempts first
    allowed, message = check_login_attempts(email)
    if not allowed:
        return False, None, message
    
    users = load_users()
    if email in users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if users[email]["password"] == hashed_password:
            if remember_me:
                # Set a cookie that expires in 30 days
                st.session_state["remember_me"] = True
                st.session_state["remember_me_expiry"] = time.time() + REMEMBER_ME_DURATION
            record_login_attempt(email, True)
            return True, users[email]["role"], None
    
    record_login_attempt(email, False)
    return False, None, "Invalid email or password"

def create_user(email, password, role="user"):
    """Create a new user."""
    users = load_users()
    if email in users:
        return False, "Email already registered"
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    users[email] = {
        "password": hashed_password,
        "role": role
    }
    save_users(users)
    return True, "User created successfully"

def login_page():
    """Display the login page and handle authentication."""
    st.title("Login")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    remember_me = st.checkbox("Remember me")
    
    if st.button("Login"):
        authenticated, role, message = authenticate_user(email, password, remember_me)
        if authenticated:
            st.session_state["authenticated"] = True
            st.session_state["username"] = email
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