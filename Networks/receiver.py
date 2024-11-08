# server.py
import streamlit as st
from flask import Flask, request, jsonify
import threading
from datetime import datetime
import pandas as pd
import altair as alt
import json
import logging
from waitress import serve
import traceback
from typing import Tuple, Dict, Optional, Any

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize session state for Streamlit
def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'emotion_data' not in st.session_state:
        st.session_state.emotion_data = []
    if 'server_running' not in st.session_state:
        st.session_state.server_running = False
    if 'model' not in st.session_state:
        st.session_state.model = None

@st.cache_resource
def load_model() -> Optional[Any]:
    """
    Load the emotion classification model with error handling.
    
    Returns:
        Optional[Any]: The loaded model pipeline or None if loading fails
    """
    try:
        from transformers import pipeline
        logger.info("Loading emotion classification model...")
        model = pipeline("text-classification", model="SamLowe/roberta-base-go_emotions")
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}\n{traceback.format_exc()}")
        st.error("Failed to load the model. Please check your environment setup.")
        return None

def analyze_emotions(text: str) -> Tuple[str, float]:
    """
    Analyze emotions in the text using the model.
    
    Args:
        text (str): Input text to analyze
        
    Returns:
        Tuple[str, float]: Tuple containing emotion label and confidence score
    """
    try:
        if st.session_state.model is None:
            st.session_state.model = load_model()
            
        if st.session_state.model is None:
            return "unknown", 0.0
            
        result = st.session_state.model(text)
        return result[0]['label'], result[0]['score']
    except Exception as e:
        logger.error(f"Error analyzing emotions: {str(e)}\n{traceback.format_exc()}")
        return "unknown", 0.0

def get_response(emotion: str, score: float) -> Dict[str, str]:
    """
    Generate appropriate response based on emotional analysis.
    
    Args:
        emotion (str): Detected emotion
        score (float): Confidence score
        
    Returns:
        Dict[str, str]: Response message and risk level
    """
    high_risk_emotions = ['sadness', 'fear', 'grief']
    
    if emotion in high_risk_emotions and score > 0.5:
        return {
            "message": (
                "I hear how much pain you're in, and I want you to know that your life has value. "
                "Please reach out to the crisis helpline immediately at 988 - they are available "
                "24/7 and want to support you. You don't have to go through this alone."
            ),
            "risk_level": "high"
        }
    else:
        return {
            "message": (
                "Thank you for reaching out. It takes courage to share these feelings. "
                "While I'm here to listen, it's important to connect with mental health "
                "professionals who can provide the support you need."
            ),
            "risk_level": "medium"
        }

@app.route('/api/support', methods=['POST'])
def receive_message() -> Tuple[Dict[str, Any], int]:
    """
    Handle incoming support requests.
    
    Returns:
        Tuple[Dict[str, Any], int]: Response data and HTTP status code
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        message = data.get('message', '')
        client_id = data.get('client_id', 'unknown')
        
        if not message:
            return jsonify({"error": "Empty message"}), 400
            
        logger.info(f"Received message from client {client_id}")
        
        # Analyze emotions
        emotion, score = analyze_emotions(message)
        
        # Generate response
        response = get_response(emotion, score)
        
        # Store in session state
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp,
            'client_id': client_id,
            'message': message,
            'emotion': emotion,
            'score': score,
            'response': response['message']
        }
        
        st.session_state.messages.append(entry)
        st.session_state.emotion_data.append({
            'timestamp': timestamp,
            'emotion': emotion,
            'score': score,
            'client_id': client_id
        })
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500

def run_server(host: str, port: int) -> None:
    """
    Run the Flask server using waitress.
    
    Args:
        host (str): Server host address
        port (int): Server port number
    """
    try:
        logger.info(f"Starting server on {host}:{port}")
        serve(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Server error: {str(e)}\n{traceback.format_exc()}")
        st.error("Server failed to start. Check logs for details.")

def create_emotion_chart(emotion_df: pd.DataFrame) -> alt.Chart:
    """
    Create an Altair chart for emotion visualization.
    
    Args:
        emotion_df (pd.DataFrame): DataFrame containing emotion data
        
    Returns:
        alt.Chart: Altair chart object
    """
    return alt.Chart(emotion_df).mark_line().encode(
        x=alt.X('timestamp:T', title='Time'),
        y=alt.Y('score:Q', title='Confidence Score'),
        color=alt.Color('emotion:N', title='Emotion'),
        strokeDash=alt.StrokeDash('client_id:N', title='Client ID')
    ).properties(
        title='Emotional Patterns Over Time',
        width='container',
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    )

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(
        page_title="Support System Server",
        page_icon="🏥",
        layout="wide"
    )
    
    # Initialize session state
    init_session_state()
    
    st.title("Support System Server 🏥")
    
    # Server controls
    col1, col2 = st.columns(2)
    
    with col1:
        server_host = st.text_input("Host", "localhost")
        server_port = st.number_input("Port", min_value=1024, max_value=65535, value=5000)
    
    with col2:
        if not st.session_state.server_running:
            if st.button("Start Server"):
                st.session_state.server_running = True
                server_thread = threading.Thread(
                    target=run_server,
                    args=(server_host, server_port)
                )
                server_thread.daemon = True
                server_thread.start()
        else:
            st.info("Server is running")
    
    # Display message history
    st.subheader("Message History")
    if st.session_state.messages:
        df = pd.DataFrame(st.session_state.messages)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    
    # Display emotion analysis
    st.subheader("Emotional Pattern Analysis")
    if st.session_state.emotion_data:
        emotion_df = pd.DataFrame(st.session_state.emotion_data)
        chart = create_emotion_chart(emotion_df)
        st.altair_chart(chart, use_container_width=True)
    
    # Server status in sidebar
    st.sidebar.header("Server Status")
    status = "🟢 Online" if st.session_state.server_running else "🔴 Offline"
    st.sidebar.write(f"Status: {status}")
    
    # Display server information
    if st.session_state.server_running:
        st.sidebar.info(
            f"Server is running at:\n"
            f"http://{server_host}:{server_port}/api/support"
        )

if __name__ == '__main__':
    main()