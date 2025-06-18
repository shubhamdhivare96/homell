from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import os
from gtts import gTTS
import speech_recognition as sr
from dotenv import load_dotenv
import requests
import tempfile
import base64
import streamlit as st
from PIL import Image
# Import Groq SDK
try:
    from groq import Groq
except ImportError:
    Groq = None
import difflib

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize text-to-speech engine
engine = gTTS.init()

def speak_text(text):
    engine = gTTS.init()
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_filename = temp_file.name
    engine.save_to_file(text, temp_filename)
    engine.runAndWait()
    with open(temp_filename, 'rb') as audio_file:
        audio_data = audio_file.read()
    os.unlink(temp_filename)
    return audio_data

def get_rag_context(query, rag_path="static/ragcontext.txt", n=1):
    # Retrieve the most relevant chunk(s) from the RAG file for the query
    try:
        with open(rag_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip()]
    except Exception as e:
        print(f"Failed to load RAG context: {e}")
        return ""
    # Use difflib to find the most similar lines
    best = difflib.get_close_matches(query, lines, n=n, cutoff=0.1)
    # If nothing matches, just return the whole file (fallback)
    if not best:
        return '\n'.join(lines)
    return '\n'.join(best)

def get_chatgpt_response(question):
    openai_api_key = os.getenv('OPENAI_API_KEY')
    groq_api_key = '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'
    groq_api_key_1 = os.getenv('GROQ_API_KEY_1')
    rag_context = get_rag_context(question)
    system_prompt = (
        f"You are Shubham Dhivare, an AI engineer. Always answer as yourself, in the first person, as if you are Shubham Dhivare. "
        f"Use the following reference information about your life and experiences to answer as specifically and personally as possible:\n{rag_context}\n" 
        f"Provide a friendly, natural response of no more than 200 words. Avoid sounding robotic or like an AI. Do not mention being an AI, assistant, or bot. Do not include meta statements."
    )
    initial_response = None
    # First, get the initial response from OpenAI or Groq (llama-4-scout)
    if openai_api_key and openai_api_key.startswith('sk-'):
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ]
            )
            initial_response = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI failed: {e}")
    if not initial_response and groq_api_key and Groq is not None:
        try:
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
            initial_response = completion.choices[0].message.content
        except Exception as e:
            print(f"Groq failed: {e}")
            return "Sorry, both OpenAI and Groq APIs failed to respond."
    if not initial_response:
        return "No valid API key found for OpenAI or Groq, or Groq SDK not installed."
    # Now, refine the response using llama3-8b-8192 with GROQ_API_KEY_1, also using the RAG context
    refined_response = None
    if groq_api_key_1 and Groq is not None:
        try:
            refine_prompt = (
                f"You are Shubham Dhivare, an AI engineer. Refine the following response to be even more clear, concise, and personal, keeping it under 200 words. "
                f"Always answer as yourself, in the first person, as if you are Shubham Dhivare. "
                f"Use the following reference information about your life and experiences to answer as specifically and personally as possible:\n{rag_context}\n"
                f"Do not mention being an AI, assistant, or bot. Do not include meta statements."
            )
            client_llama3 = Groq(api_key=groq_api_key_1)
            completion_llama3 = client_llama3.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": refine_prompt},
                    {"role": "user", "content": initial_response}
                ],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
            )
            refined_response = completion_llama3.choices[0].message.content
        except Exception as e:
            print(f"Llama3 refinement failed: {e}")
    def clean_response(text):
        import re
        patterns = [
            r"^Here'?s a refined version of the response:?\s*",
            r"^Refined response:?\s*",
            r"^Here is the refined response:?\s*",
            r"^Refined version:?\s*",
        ]
        for pat in patterns:
            text = re.sub(pat, '', text, flags=re.IGNORECASE)
        return text.strip()
    return clean_response(refined_response or initial_response)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    response = get_chatgpt_response(question)
    return jsonify({'response': response})

@app.route('/api/speak', methods=['POST'])
def speak():
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # Save the audio to the temporary file
        engine.save_to_file(text, temp_filename)
        engine.runAndWait()
        
        # Read the audio file and convert to base64
        with open(temp_filename, 'rb') as audio_file:
            audio_data = audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Clean up the temporary file
        os.unlink(temp_filename)
        
        return jsonify({
            'status': 'success',
            'audio': audio_base64
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# This is needed for Vercel
app = app

# --- Streamlit UI ---
st.set_page_config(page_title="Shubham Dhivare | Voice Bot Portfolio", layout="centered")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("# Shubham Dhivare")
    st.markdown("**AI Engineer**")
    st.write("""
    Hi there! I'm Shubham, an AI engineer passionate about building intelligent, user-friendly solutions. With experience in Python, AI/ML, and full-stack web development, I thrive on solving real-world problems and creating seamless digital experiences. Let's connect and innovate together!
    """)
    st.markdown("""
    [![LinkedIn](https://img.shields.io/badge/LinkedIn-Profile-blue?logo=linkedin)](https://www.linkedin.com/in/your-linkedin)
    [![Resume](https://img.shields.io/badge/Download-Resume-green?logo=adobeacrobatreader)](static/ShubhamDhivare__Resume__.pdf)
    """)
with col2:
    img = Image.open("static/th (1).jpg")
    st.image(img, width=192, caption="Shubham Dhivare", output_format="auto")

st.markdown("---")

st.markdown("## Voice Bot")

preset_questions = [
    "What should we know about your life story in a few sentences?",
    "What's your #1 superpower?",
    "What are the top 3 areas you'd like to grow in?",
    "What misconception do your coworkers have about you?",
    "How do you push your boundaries and limits?"
]

preset = st.selectbox("Choose a preset question or type your own:", ["(Type your own)"] + preset_questions)
if preset != "(Type your own)":
    question = preset
else:
    question = st.text_area("Type your question here:")

if st.button("Submit"):
    if question.strip():
        with st.spinner("Thinking..."):
            response = get_chatgpt_response(question)
        st.session_state['response'] = response
    else:
        st.warning("Please enter a question.")

if 'response' in st.session_state:
    st.markdown("### Response:")
    st.markdown(f"<div style='max-height:250px;overflow-y:auto;background:#f9fafb;padding:1em;border-radius:8px;'>{st.session_state['response']}</div>", unsafe_allow_html=True)
    if st.button("🔊 Speak/Stop", key="speak_btn"):
        if 'audio_playing' not in st.session_state or not st.session_state['audio_playing']:
            audio_data = speak_text(st.session_state['response'])
            st.audio(audio_data, format='audio/wav')
            st.session_state['audio_playing'] = True
        else:
            st.session_state['audio_playing'] = False
            st.experimental_rerun()
