import streamlit as st
import os
from dotenv import load_dotenv
from utils.auth import authenticate_user_neo4j, logout_user, register_user, is_admin_user, get_pending_users, approve_user, validate_password_policy
from components.ui_styles import apply_custom_styles
from streamlit_cookies_controller import CookieController

# Load environment variables from .env file
# IMPORTANT: Use an absolute path to .env relative to this script.
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=dotenv_path)

# Initialize CookieManager
cookies = CookieController()

# --- Page Configuration ---
st.set_page_config(
    page_title="Vulcanus AI",
    page_icon="✨", # Overall app icon
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom glassmorphic and animation styles (MUST be called on every page)
apply_custom_styles()

# --- Feature Card Rendering Function ---
def render_feature_cards():
    st.markdown("---")
    st.subheader("Key Features")
    st.markdown("""
        <style>
            .feature-cards-container {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* Responsive grid */
                gap: 20px;
                margin-top: 30px;
                margin-bottom: 50px;
            }
            /* Adjustments for card content when in columns (less internal padding) */
            .feature-card .card-icon { font-size: 2.5em; margin-bottom: 10px; }
            .feature-card .card-title { font-size: 1.2em; margin-bottom: 8px; }
            .feature-card .card-description { font-size: 0.85em; }
        </style>
        <div class="feature-cards-container">
    """, unsafe_allow_html=True)
    features = [
        {"icon": "💻", "title": "AI Code Generation", "description": "Generate, convert, refactor, and optimize code across languages."},
        {"icon": "📊", "title": "Data Analysis & Charting", "description": "Upload data, query AI for insights, and visualize with interactive charts."},
        {"icon": "📄", "title": "Document Processing", "description": "Upload documents to extract text and query their content with AI."},
        {"icon": "🗺️", "title": "Project Flow Mapping", "description": "Visualize project, data, or process flows using AI-generated diagrams."},
        {"icon": "☁️", "title": "Cloud Code Conversion", "description": "Seamlessly convert and update cloud-specific code between platforms/services."},
        {"icon": "🖼️", "title": "AI Wireframe UI Generator", "description": "Generate UI wireframes from natural language descriptions using custom markup."},
    ]
    for feature in features:
        st.markdown(f"""
            <div class="feature-card">
                <div class="card-icon">{feature['icon']}</div>
                <h3 class="card-title">{feature['title']}</h3>
                <p class="card-description">{feature['description']}</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True) # Close the feature-cards-container

# --- Authentication Logic ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = cookies.get("authenticated") == "true"
    st.session_state.username = cookies.get("username") if st.session_state.authenticated else ""
    st.session_state.show_register_form = False # New state to control registration form visibility
    st.session_state.show_admin_panel = False # Ensure this is initialized

if not st.session_state.authenticated:
    st.sidebar.title("🔮 Login / Register") # Overall title for the sidebar section
    st.sidebar.markdown("---")
    # Display feature cards before login
    st.title("✨ Vulcanus AI")
    st.markdown("---")
    st.markdown(
        """
        Welcome to the Vulcanus AI!
        A robust application designed to assist developers and data professionals.
        Explore its capabilities below or login to get started.
        """
    )
    render_feature_cards() # Show cards here before login form
    st.markdown("---") # Separator before login/register forms

    if st.session_state.show_register_form:
        # --- Registration Form ---
        with st.sidebar.form(key="register_form"):
            st.subheader("Register New User") # This subheader is inside the form
            
            # Safely initialize input values from session_state or empty string
            # These are inside the form.
            new_username = st.text_input(
                "New Username", 
                value=st.session_state.get("register_username_input_form", ""), # Use .get with default
                key="register_username_input_form"
            )
            new_password = st.text_input(
                "New Password", 
                type="password", 
                value=st.session_state.get("register_password_input_form", ""), # Use .get with default
                key="register_password_input_form"
            )
            confirm_password = st.text_input(
                "Confirm Password", 
                type="password", 
                value=st.session_state.get("confirm_password_input_form", ""), # Use .get with default
                key="confirm_password_input_form"
            )
            register_submit_button = st.form_submit_button("Register")
            
            # Password policy feedback (displayed live as user types, outside the button block but inside the form)
            if new_password:
                errors = validate_password_policy(new_password)
                if errors:
                    for error in errors:
                        st.error(error) # Uses st.error, which can be inside form
                else:
                    st.success("Password meets policy requirements!") # Uses st.success

            if register_submit_button:
                if new_password != confirm_password:
                    st.error("Passwords do not match.") # Display within the form context
                elif not new_username.strip() or not new_password.strip():
                    st.error("Username and password cannot be empty.") # Display within the form context
                else:
                    success, message = register_user(new_username, new_password)
                    if success:
                        st.success(message) # Display within the form context
                        st.session_state.show_register_form = False # Hide form after successful registration
                        # Clear session state keys *after* successful registration and before rerun
                        if "register_username_input_form" in st.session_state:
                            del st.session_state["register_username_input_form"]
                        if "register_password_input_form" in st.session_state:
                            del st.session_state["register_password_input_form"]
                        if "confirm_password_input_form" in st.session_state:
                            del st.session_state["confirm_password_input_form"]
                        st.rerun() # Rerun to show login form
                    else:
                        st.error(message) # Display within the form context
        
        # This button is outside the form, but still in the sidebar.
        st.sidebar.button("Back to Login", key="back_to_login_button", on_click=lambda: st.session_state.update(show_register_form=False))
    else: # Show login form
        # --- Login Form ---
        with st.sidebar.form(key="login_form"):
            st.subheader("Login to Your Account") # This subheader is inside the form
            
            # Safely initialize login input values
            # These are inside the form.
            username = st.text_input(
                "Username", 
                value=st.session_state.get("login_username_input_form", ""), # Use .get with default
                key="login_username_input_form"
            )
            password = st.text_input(
                "Password", 
                type="password", 
                value=st.session_state.get("login_password_input_form", ""), # Use .get with default
                key="login_password_input_form"
            )
            
            login_submit_button = st.form_submit_button("Login")
            if login_submit_button:
                cookies.set("authenticated", "false") # Default to false before checking
                cookies.set("username", "")
                
                success, message = authenticate_user_neo4j(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    cookies.set("authenticated", "true")
                    cookies.set("username", username)
                    cookies.getAll() # Save cookies immediately
                    st.success("Logged in successfully!") # Display within the form context
                    st.rerun() # Rerun to hide login and show content
                else:
                    st.error(message) # Display within the form context
                    cookies.getAll() # Save cookies even on failure
        
        # This button is outside the form, but still in the sidebar.
        st.sidebar.button("Register New User", key="show_register_form_button", on_click=lambda: st.session_state.update(show_register_form=True))
    
    st.stop() # Stop execution if not authenticated (prevents content from loading)

# If authenticated, show logout button and welcome message
st.sidebar.success(f"Welcome, {st.session_state.username}!")

# --- Admin Panel (Only for Admin User) ---
if is_admin_user(st.session_state.username):
    st.sidebar.markdown("---")
    st.sidebar.subheader("👑 Admin Panel")
    if st.sidebar.button("Manage User Approvals", key="manage_user_approvals_button"):
        st.session_state.show_admin_panel = not st.session_state.show_admin_panel # Toggle visibility
        st.rerun() # Rerun to apply toggle immediately
    
    if st.session_state.get("show_admin_panel"):
        st.subheader("User Approval Management")
        pending_users = get_pending_users()
        if pending_users:
            st.info("The following users are pending approval:")
            for user in pending_users:
                col_user, col_approve = st.columns([0.7, 0.3])
                with col_user:
                    st.write(f"**Username:** {user['username']}")
                    st.write(f"Registered: {user['created_at'].strftime('%Y-%m-%d %H:%M')}")
                with col_approve:
                    # Use a unique key for each button to avoid Streamlit warnings
                    if st.button(f"Approve {user['username']}", key=f"approve_user_{user['username']}"):
                        if approve_user(user['username']):
                            st.success(f"User '{user['username']}' approved successfully!")
                            st.rerun() # Rerun to refresh list
                        else:
                            st.error(f"Failed to approve user '{user['username']}'.")
                st.markdown("---")
        else:
            st.info("No users currently pending approval.")
        
        # Removed explicit "Close Admin Panel" button here, relying on toggle for "Manage User Approvals"
    st.markdown("---") # Separator after admin panel

if st.sidebar.button("Logout", key="logout_button"):
    logout_user()
    st.session_state.authenticated = False
    st.session_state.username = ""
    cookies.set("authenticated", "false") 
    cookies.set("username", "")
    cookies.getAll() # Clear cookies
    st.rerun() # Rerun to show login page

# --- Main App Content (after authentication and admin panel, if shown) ---
# Custom CSS for main container padding (can also be in ui_styles.py)
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-right: 2rem;
        padding-left: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("✨ Vulcanus AI")
st.markdown("---")
st.markdown(
    """
    Welcome to the Vulcanus AI!
    Use the sidebar to navigate between features:
    - **Code Generator**: Generate, convert, and refactor code, with flow mapping.
    - **Data Analysis**: Upload CSV/XLSX and query AI to create charts.
    - **Document Processor**: Upload documents and query their content.
    - **Project Flow Mapper**: Generate conceptual project or process flow diagrams.
    - **Cloud Code Converter**: Convert and update cloud function/deployment code across versions/platforms.
    - **AI Wireframe UI Generator**: Generate UI wireframes from natural language descriptions.
    """
)

render_feature_cards() # Show cards here after login as well