# src/components/ui_styles.py
import streamlit as st

def apply_custom_styles():
    """Applies glassmorphic effects and background animations to the Streamlit app with a purple theme."""
    glassmorphism_css = """
    <style>
    /* Global Styles for Glassmorphism Background with Purple Theme */
    .stApp {
        background-color: #0e0d12; /* Very dark nearly black background for deep contrast */
        overflow: hidden; /* Hide overflow for background animations */
        font-family: 'Inter', sans-serif; /* Modern font */
        color: rgba(255, 255, 255, 0.9); /* Default text color */
    }

    /* Apply glassmorphism to Streamlit containers and elements */
    /* !!! IMPORTANT: These class names are Streamlit's generated classes.
       They are HIGHLY UNSTABLE and might change with Streamlit updates.
       If the UI looks off, right-click -> Inspect Element in your browser
       to find the current class names and update them here.
       (Tested with Streamlit 1.34.0+) */
    
    /* General containers & main content area */
    .st-emotion-cache-l9bo8e,    /* stColumn (individual column div) */
    .st-emotion-cache-z5fcl4,    /* stContainer (general container for widgets) */
    .st-emotion-cache-1w0rcx2,   /* stExpandable (expander widget) */
    .st-emotion-cache-1cyp78v,   /* stBlockContainer (main content area, also appears for forms/columns) */
    .st-emotion-cache-16txt3u,   /* stSidebar (the main sidebar div) */
    .st-emotion-cache-17av0q5,   /* stSidebarV (inner sidebar content blocks) */
    .st-emotion-cache-0,         /* Common generic div that wraps various content */
    .st-emotion-cache-10o5j50,   /* Another common generic div */
    .st-emotion-cache-1y4q8c2,   /* stTextInput / st.number_input / st.date_input base container */
    .st-emotion-cache-1c0xf9c,   /* stTextArea base container */
    .st-emotion-cache-1g8l07b,   /* stFileUploader base container */
    .st-emotion-cache-j7qwjs,    /* stRadio/stCheckbox container */
    .st-emotion-cache-vdve29,    /* stMarkdown base container (for st.write, st.markdown) */
    .st-emotion-cache-k3g09m,    /* stCode block container */
    .st-emotion-cache-1er4z1h,   /* stSelectbox / st.multiselect container */
    .st-emotion-cache-1x4mptd,   /* stMetric container */
    
    /* Elements that specifically hold content like alerts or progress */
    .stAlert,                    /* The main alert box */
    .stProgress > div > div      /* The progress bar fill */
    {
        background: rgba(138, 43, 226, 0.08); /* Frosted purple glass effect */
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2); /* Stronger shadow for depth */
        backdrop-filter: blur(10px); /* Slightly stronger blur effect */
        -webkit-backdrop-filter: blur(10px); /* Safari support */
        border: 1px solid rgba(138, 43, 226, 0.2); /* Purple tinted border */
        padding: 18px; /* Slightly more padding */
        margin-bottom: 18px; /* Space between elements */
        transition: all 0.3s ease-in-out; /* Smooth transitions for hover/focus */
    }
    
    /* Specific adjustments for input fields - target inner input elements */
    .st-emotion-cache-1y4q8c2 input[type="text"],
    .st-emotion-cache-1y4q8c2 input[type="password"],
    .st-emotion-cache-1c0xf9c textarea,
    .st-emotion-cache-1er4z1h div[data-baseweb="select"] { /* stSelectbox styling */
        background-color: rgba(75, 0, 130, 0.3); /* Darker purple input background */
        color: white;
        border: 1px solid rgba(138, 43, 226, 0.4);
        border-radius: 10px; /* Slightly more rounded inputs */
        padding: 10px 15px;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    /* Placeholder text color for inputs */
    .st-emotion-cache-1y4q8c2 input::placeholder,
    .st-emotion-cache-1c0xf9c textarea::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    .st-emotion-cache-1y4q8c2 input[type="text"]:focus,
    .st-emotion-cache-1y4q8c2 input[type="password"]:focus,
    .st-emotion-cache-1c0xf9c textarea:focus,
    .st-emotion-cache-1er4z1h div[data-baseweb="select"]:focus-within { /* Selectbox focus */
        border-color: #B19CD9; /* Lighter purple highlight on focus */
        box-shadow: 0 0 0 3px rgba(177, 156, 217, 0.4); /* Glow effect */
    }

    /* Button Styling (universal selector for robustness) */
    div[data-testid="stButton"] > button {
        background: linear-gradient(145deg, rgba(138, 43, 226, 0.3), rgba(75, 0, 130, 0.3)); /* Purple gradient glass button */
        color: white;
        border: 1px solid rgba(138, 43, 226, 0.5);
        border-radius: 10px;
        transition: all 0.3s ease;
        padding: 12px 25px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stButton"] > button:hover {
        background: linear-gradient(145deg, rgba(138, 43, 226, 0.5), rgba(75, 0, 130, 0.5));
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
        transform: translateY(-2px);
    }
    div[data-testid="stButton"] > button:active {
        transform: translateY(0);
        box-shadow: none;
    }

    /* Text color adjustments for readability on dark glass */
    h1, h2, h3, h4, h5, h6, label, p, .stMarkdown, .st-emotion-cache-j7qwjs label, .st-emotion-cache-1x4mptd div {
        color: rgba(255, 255, 255, 0.95); /* Very light text for strong contrast */
    }

    /* Streamlit alerts/info/success messages - ensure text is white */
    .stAlert {
        background: rgba(138, 43, 226, 0.15); /* Lighter purple for alerts */
        backdrop-filter: blur(8px);
        border-radius: 12px;
        border: 1px solid rgba(138, 43, 226, 0.3);
        color: white; /* Ensure text inside is white */
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }
    .stAlert > div > span, .stAlert > div > div > p { /* Alert message text */
        color: white !important;
    }

    /* Streamlit sidebar navigation links */
    /* Target the list items in the sidebar navigation using data-testid for robustness */
    [data-testid="stSidebarNav"] li {
        background: rgba(138, 43, 226, 0.05); /* Very subtle purple tint for nav items */
        border-radius: 12px;
        margin-bottom: 8px;
        transition: all 0.2s ease-in-out;
        padding: 10px 15px; /* Adjust padding for better look */
    }
    [data-testid="stSidebarNav"] li:hover {
        background: rgba(138, 43, 226, 0.15); /* More visible on hover */
        transform: translateX(5px); /* Slight slide effect */
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    }
    [data-testid="stSidebarNav"] li > a { /* The actual link text */
        color: rgba(255, 255, 255, 0.85); /* Slightly muted white */
        text-decoration: none;
        font-weight: bold;
    }
    [data-testid="stSidebarNav"] li > a:hover {
        color: white; /* Bright white on hover */
    }

    /* Streamlit sidebar header title */
    .st-emotion-cache-vk3ypz, /* Class for the sidebar title (often stable) */
    .st-emotion-cache-17av0q5 h1 { /* Fallback/alternative for the title element inside sidebar */
        color: #B19CD9 !important; /* Lighter purple for sidebar title */
        text-shadow: 0 0 5px rgba(177, 156, 217, 0.5); /* Subtle glow */
    }

    /* Hide "Press Enter to submit form" hint */
    /* This targets the specific paragraph element within a div that has data-testid="InputInstructions" */
    div[data-testid="InputInstructions"] p {
        display: none !important;
    }

    /* Hide the password toggle button when hint is hidden, if it causes visual issues */
    /* This rule targets the eye icon for toggling password visibility */
    .st-emotion-cache-1y4q8c2 button[data-testid="stTextInputPasswordToggle"] {
        /* Optionally hide if it floats awkwardly after removing the hint */
        /* display: none !important; */
    }


    /* Feature Card Styling */
    .feature-card {
        background: rgba(138, 43, 226, 0.15); /* Slightly more opaque glass for cards */
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3); /* Stronger shadow for depth */
        backdrop-filter: blur(12px); /* Stronger blur for cards */
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(138, 43, 226, 0.3);
        padding: 25px;
        margin-bottom: 25px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: default; /* Not clickable by default */
        height: 100%; /* Ensure cards in a row have consistent height */
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .feature-card:hover {
        background: rgba(138, 43, 226, 0.25); /* More visible on hover */
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transform: translateY(-5px); /* Lift effect on hover */
        border-color: rgba(138, 43, 226, 0.5);
    }
    .card-icon {
        font-size: 3em; /* Larger icons */
        margin-bottom: 15px;
        color: #B19CD9; /* Lighter purple for icons */
        text-shadow: 0 0 8px rgba(177, 156, 217, 0.6); /* Glow effect */
    }
    .card-title {
        font-size: 1.5em;
        font-weight: bold;
        margin-bottom: 10px;
        color: rgba(255, 255, 255, 0.98);
    }
    .card-description {
        font-size: 0.9em;
        color: rgba(255, 255, 255, 0.8);
        line-height: 1.5;
    }

    /* Background Animation (subtle glowing purple shapes) */
    .stApp::before, .stApp::after,
    .stApp .block-container::before, .stApp .block-container::after {
        content: '';
        position: absolute;
        opacity: 0.1; /* Subtle effect */
        background: linear-gradient(135deg, rgba(138, 43, 226, 0.1), rgba(75, 0, 130, 0.1)); /* Purple gradient shapes */
        z-index: -1; /* Behind content */
        animation: floatEffect 20s ease-in-out infinite alternate;
        filter: blur(20px); /* Extra blur for ethereal glow */
    }
    .stApp::before {
        width: 250px;
        height: 250px;
        border-radius: 40%;
        top: 10%;
        left: 5%;
        animation-duration: 25s;
        animation-delay: 0s;
        transform: rotate(0deg) scale(1);
    }
    .stApp::after {
        width: 180px;
        height: 180px;
        border-radius: 50%;
        bottom: 15%;
        right: 10%;
        animation-duration: 22s;
        animation-delay: -5s;
        transform: rotate(0deg) scale(1);
    }
    .stApp .block-container::before {
        width: 300px;
        height: 300px;
        border-radius: 30%;
        top: 40%;
        left: 25%;
        animation-duration: 28s;
        animation-delay: -10s;
        transform: rotate(0deg) scale(1);
    }
    .stApp .block-container::after {
        width: 200px;
        height: 200px;
        border-radius: 60%;
        bottom: 25%;
        right: 20%;
        animation-duration: 30s;
        animation-delay: -15s;
        transform: rotate(0deg) scale(1);
    }
    @keyframes floatEffect {
        0% { transform: translate(0, 0) rotate(0deg) scale(1); opacity: 0.1; }
        25% { transform: translate(30px, 40px) rotate(15deg) scale(1.03); opacity: 0.15; }
        50% { transform: translate(-20px, 60px) rotate(-10deg) scale(0.98); opacity: 0.1; }
        75% { transform: translate(40px, -30px) rotate(25deg) scale(1.06); opacity: 0.17; }
        100% { transform: translate(0, 0) rotate(0deg) scale(1); opacity: 0.1; }
    }
    </style>
    """
    st.markdown(glassmorphism_css, unsafe_allow_html=True)