# src/utils/auth.py
import streamlit as st
import re
from passlib.hash import pbkdf2_sha256
from core.neo4j_handler import Neo4jHandler

# Initialize Neo4j Handler for authentication operations
# Using st.cache_resource to ensure a single instance across Streamlit reruns
@st.cache_resource
def get_auth_neo4j_handler():
    return Neo4jHandler()

neo4j_handler = get_auth_neo4j_handler()

# --- Password Policy Validation ---
def validate_password_policy(password: str) -> list[str]:
    """
    Validates password against a policy:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one symbol
    Returns a list of error messages, or empty list if valid.
    """
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one symbol (!@#$%^&*...).")
    return errors

# --- User Management Functions (interacting with Neo4j) ---
def register_user(username, password) -> bool:
    """Registers a new user with hashed password in Neo4j (initially unapproved)."""
    if neo4j_handler.get_user(username):
        return False, "Username already exists."

    password_errors = validate_password_policy(password)
    if password_errors:
        return False, "Password does not meet requirements: " + ", ".join(password_errors)

    hashed_password = pbkdf2_sha256.hash(password)
    return neo4j_handler.create_user(username, hashed_password)

def authenticate_user_neo4j(username, password) -> bool:
    """Authenticates user against Neo4j, checking hashed password and approval status."""
    user_data = neo4j_handler.get_user(username)
    if user_data:
        hashed_password_from_db = user_data.get("hashed_password")
        is_approved = user_data.get("approved", False)
        
        # Verify password using passlib
        if hashed_password_from_db and pbkdf2_sha256.verify(password, hashed_password_from_db):
            if is_approved:
                return True, "Authenticated"
            else:
                return False, "Account pending approval by administrator."
        else:
            return False, "Invalid username or password."
    return False, "Invalid username or password."

def is_user_approved(username: str) -> bool:
    """Checks if a user is approved to log in."""
    user_data = neo4j_handler.get_user(username)
    return user_data.get("approved", False) if user_data else False

def is_admin_user(username: str) -> bool:
    """Checks if the given username has the 'admin' role."""
    return neo4j_handler.check_user_role(username, "admin")

def get_pending_users() -> list[dict]:
    """Retrieves a list of users awaiting approval."""
    return neo4j_handler.get_unapproved_users()

def approve_user(username: str) -> bool:
    """Approves a user account, allowing them to log in."""
    return neo4j_handler.update_user_approval(username, True)

def logout_user():
    """Clears authentication state from session."""
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
    if "username" in st.session_state:
        del st.session_state["username"]