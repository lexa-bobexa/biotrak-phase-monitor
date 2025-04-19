import json
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import hashlib

# Path to the usage logs file
USAGE_LOGS_PATH = "data/usage_logs.json"
# Path to the users database file
USERS_DB_PATH = "data/users.json"

def init_usage_logs():
    """Initialize the usage logs file if it doesn't exist."""
    if not os.path.exists(os.path.dirname(USAGE_LOGS_PATH)):
        os.makedirs(os.path.dirname(USAGE_LOGS_PATH))
    
    if not os.path.exists(USAGE_LOGS_PATH):
        with open(USAGE_LOGS_PATH, 'w') as f:
            json.dump([], f)

def log_usage(user_email, action, details=None):
    """Log a user action."""
    if not os.path.exists(USAGE_LOGS_PATH):
        init_usage_logs()
    
    with open(USAGE_LOGS_PATH, 'r') as f:
        logs = json.load(f)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_email,
        "action": action,
        "details": details or {}
    }
    
    logs.append(log_entry)
    
    with open(USAGE_LOGS_PATH, 'w') as f:
        json.dump(logs, f)

def get_usage_data(timeframe='year'):
    """Get usage data for the specified timeframe."""
    if not os.path.exists(USAGE_LOGS_PATH):
        return pd.DataFrame()
    
    with open(USAGE_LOGS_PATH, 'r') as f:
        logs = json.load(f)
    
    if not logs:
        return pd.DataFrame()
    
    # Convert logs to DataFrame
    df = pd.DataFrame(logs)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter by timeframe
    now = datetime.now()
    if timeframe == 'year':
        start_date = now - timedelta(days=365)
    elif timeframe == 'month':
        start_date = now - timedelta(days=30)
    elif timeframe == 'week':
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=365)  # Default to year
    
    return df[df['timestamp'] >= start_date]

def show_admin_dashboard():
    """Display the admin dashboard with usage statistics and user management."""
    st.title("Admin Dashboard")
    
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["Usage Statistics", "User Management"])
    
    with tab1:
        # Timeframe selector
        timeframe = st.selectbox(
            "Select Timeframe",
            options=['year', 'month', 'week'],
            format_func=lambda x: x.capitalize(),
            key="timeframe_selector"
        )
        
        # Get usage data
        df = get_usage_data(timeframe)
        
        if df.empty:
            st.info("No usage data available yet.")
        else:
            # Calculate statistics
            total_uses = len(df)
            unique_users = df['user'].nunique()
            most_common_action = df['action'].mode().iloc[0]
            
            # Calculate average processing time for completed processes
            processing_times = []
            for log in df[df['action'] == 'processing_complete'].to_dict('records'):
                if 'details' in log and 'processing_time' in log['details']:
                    processing_times.append(log['details']['processing_time'])
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            # Display key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Uses", total_uses)
            with col2:
                st.metric("Unique Users", unique_users)
            with col3:
                st.metric("Most Common Action", most_common_action)
            with col4:
                st.metric("Avg Processing Time", f"{avg_processing_time:.2f} seconds")
            
            # Usage over time
            st.subheader("Usage Over Time")
            daily_usage = df.groupby(df['timestamp'].dt.date).size()
            st.line_chart(daily_usage)
            
            # Processing time over time
            st.subheader("Processing Time Trend")
            processing_data = df[df['action'] == 'processing_complete'].copy()
            if not processing_data.empty:
                processing_data['date'] = pd.to_datetime(processing_data['timestamp']).dt.date
                processing_data['processing_time'] = processing_data['details'].apply(lambda x: x.get('processing_time', 0))
                time_trend = processing_data.groupby('date')['processing_time'].mean()
                st.line_chart(time_trend)
            
            # User activity
            st.subheader("User Activity")
            user_activity = df.groupby('user').size().sort_values(ascending=False)
            st.bar_chart(user_activity)
            
            # Action breakdown
            st.subheader("Action Breakdown")
            action_counts = df['action'].value_counts()
            st.bar_chart(action_counts)
            
            # Raw data view
            st.subheader("Recent Activity")
            st.dataframe(df.sort_values('timestamp', ascending=False).head(100))
    
    with tab2:
        st.subheader("User Management")
        
        # Load users
        if not os.path.exists(USERS_DB_PATH):
            st.error("Users database not found!")
            return
        
        with open(USERS_DB_PATH, 'r') as f:
            users = json.load(f)
        
        # Create new user section
        st.subheader("Create New User")
        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Role", ["user", "admin"])
            
            if st.form_submit_button("Create User"):
                if new_username in users:
                    st.error("Username already exists!")
                else:
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    users[new_username] = {
                        "password": hashed_password,
                        "role": new_role
                    }
                    with open(USERS_DB_PATH, 'w') as f:
                        json.dump(users, f)
                    st.success(f"User {new_username} created successfully!")
                    st.rerun()
        
        # Display existing users
        st.subheader("Existing Users")
        for username, user_data in users.items():
            col1, col2, col3, col4 = st.columns([0.3, 0.2, 0.25, 0.25])
            with col1:
                st.write(f"**{username}**")
            with col2:
                st.write(f"Role: {user_data['role']}")
            with col3:
                # Add a button to change password
                if st.button(f"Change Password", key=f"change_pw_{username}"):
                    st.session_state[f"changing_pw_{username}"] = True
                    st.rerun()
            with col4:
                if username != "admin":  # Don't allow deleting the admin user
                    if st.button(f"Delete", key=f"delete_{username}"):
                        del users[username]
                        with open(USERS_DB_PATH, 'w') as f:
                            json.dump(users, f)
                        st.success(f"User {username} deleted successfully!")
                        st.rerun()
            
            # Show password change form if button was clicked
            if st.session_state.get(f"changing_pw_{username}", False):
                with st.form(f"change_pw_form_{username}"):
                    new_password = st.text_input("New Password", type="password", key=f"new_pw_{username}")
                    confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_{username}")
                    
                    if st.form_submit_button("Update Password"):
                        if new_password != confirm_password:
                            st.error("Passwords do not match!")
                        else:
                            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                            users[username]["password"] = hashed_password
                            with open(USERS_DB_PATH, 'w') as f:
                                json.dump(users, f)
                            st.success(f"Password for {username} updated successfully!")
                            st.session_state[f"changing_pw_{username}"] = False
                            st.rerun()
                    
                    if st.form_submit_button("Cancel"):
                        st.session_state[f"changing_pw_{username}"] = False
                        st.rerun() 