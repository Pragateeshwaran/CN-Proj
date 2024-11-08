# client.py
import streamlit as st
import requests
import uuid
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Support System Client",
    page_icon="💚",
    layout="wide"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'client_id' not in st.session_state:
    st.session_state.client_id = str(uuid.uuid4())
if 'server_url' not in st.session_state:
    st.session_state.server_url = None

# Emergency contacts
EMERGENCY_CONTACTS = {
    "National Suicide Prevention Lifeline": "988",
    "Crisis Text Line": "Text HOME to 741741",
    "Emergency Services": "911"
}

def send_message(message):
    """Send message to the server and receive response."""
    if not st.session_state.server_url:
        st.error("Server URL not configured")
        return
        
    try:
        # Prepare request data
        data = {
            "message": message,
            "client_id": st.session_state.client_id
        }
        
        # Send request to server
        response = requests.post(
            f"{st.session_state.server_url}/api/support",
            json=data
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Store message and response
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.messages.append({
                "timestamp": timestamp,
                "role": "user",
                "content": message
            })
            st.session_state.messages.append({
                "timestamp": timestamp,
                "role": "assistant",
                "content": response_data["message"],
                "risk_level": response_data["risk_level"]
            })
            
            return True
        else:
            st.error(f"Error: Server returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

# Sidebar with connection settings and emergency information
with st.sidebar:
    st.header("Connection Settings")
    server_host = st.text_input("Server Host", "localhost")
    server_port = st.number_input("Server Port", min_value=1024, max_value=65535, value=5000)
    
    if st.button("Connect"):
        st.session_state.server_url = f"http://{server_host}:{server_port}"
        
    st.markdown("---")
    
    st.header("Emergency Contacts 🆘")
    for service, number in EMERGENCY_CONTACTS.items():
        st.info(f"{service}: {number}")

# Main chat interface
st.title("Mental Health Support System 💚")

# Connection status
status = "🟢 Connected" if st.session_state.server_url else "🔴 Not Connected"
st.write(f"Status: {status}")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("risk_level") == "high":
            st.warning("Please consider reaching out to emergency services or a crisis helpline.")

# Chat input
if st.session_state.server_url:
    if prompt := st.chat_input("Share your thoughts..."):
        send_message(prompt)
else:
    st.info("Please configure the server connection to start chatting.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Remember: You're not alone. Help is always available.</p>
        <p>This is a supportive space, but not a substitute for professional help.</p>
    </div>
    """,
    unsafe_allow_html=True
)