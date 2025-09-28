import streamlit as st

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

# Load user credentials from Streamlit secrets
USER_CREDENTIALS = {
    st.secrets["LUKE_LU_USERNAME"]: {
        "password": st.secrets["LUKE_LU_PASSWORD"],
        "role": st.secrets["LUKE_LU_ROLE"],
    },
    st.secrets["CARTER_DING_USERNAME"]: {
        "password": st.secrets["CARTER_DING_PASSWORD"],
        "role": st.secrets["CARTER_DING_ROLE"],
    },
    st.secrets["ZACH_LI_USERNAME"]: {
        "password": st.secrets["ZACH_LI_PASSWORD"],
        "role": st.secrets["ZACH_LI_ROLE"],
    },
}

# Login function
def login(username, password):
    user = USER_CREDENTIALS.get(username)  # Get user details
    if user and user["password"] == password:
        return True
    return False

# Login screen
if not st.session_state["logged_in"]:
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if login(username, password):
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username
            st.rerun()  # Automatically refresh the page after login
        else:
            st.sidebar.error("Invalid username or password.")
    # Show only the welcome page content before login
    st.title("Welcome to Lingbo PO Parser")
    st.write("Please log in to access the application.")
else:
    # Main content after login
    st.sidebar.title("Navigation")
    st.sidebar.success(f"Logged in as {st.session_state['current_user']}")

    # Add a "Log Out" button in the sidebar
    if st.sidebar.button("Log Out"):
        st.session_state["logged_in"] = False
        st.session_state["current_user"] = None
        st.rerun()  # Refresh the app to show the login screen
    # Top-left logo
    col1, col3, col2 = st.columns([2, 1, 2])
    with col3:
        st.image("logo.png", caption="", use_container_width=True)

    col11, col13, col12 = st.columns([1, 2, 1])
    with col13:
        st.title("Welcome Lingbo PO Parser")
    st.write("---")

    # Introduction section
    cola, colc, colb = st.columns([5, 1, 4])
    with cola:
        st.write("### About This Application")
        st.write("This application is designed to help you extract data from PDF files and convert it into CSV format.")
        st.write("With this tool, you can:")
        st.write("- Upload PDF files or ZIP archives containing PDFs.")
        st.write("- Extract purchase order information and item details.")
        st.write("- Download the extracted data as a CSV file.")
        st.write("Use the sidebar to navigate through the application and get started!")
    with colb:
        st.write("### How to Use")
        st.write("1. Log in using your credentials.")
        st.write("2. Navigate to the desired page using the sidebar.")
        st.write("3. Follow the instructions on each page to upload and process your files.")
