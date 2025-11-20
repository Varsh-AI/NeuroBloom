import os
import io
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from gtts import gTTS

# Load API Keys

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")


# Groq Llama 3.1

def call_groq(prompt, max_tokens=300):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        data = res.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return "Error generating text."
    except Exception as e:
        print("Groq error:", e)
        return "Groq API error."


# Stability Image Core (WORKING)

def generate_image(prompt):
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    files = {"none": ""}  # Dummy file required by API
    data = {
        "prompt": prompt,
        "output_format": "png",  # or "webp"
    }

    try:
        res = requests.post(url, headers=headers, files=files, data=data, timeout=60)
        if res.status_code == 200:
            return Image.open(io.BytesIO(res.content))
        else:
            print("Error:", res.status_code, res.text)
            return None
    except Exception as e:
        print("Exception during image generation:", e)
        return None



# Text-to-Speech

def text_to_speech_bytes(text):
    tts = gTTS(text=text, lang="en")
    bio = io.BytesIO()
    tts.write_to_fp(bio)
    bio.seek(0)
    return bio.read()


# Quiz: request structured JSON from model

def generate_quiz_json_from_story(story_text, n_questions=3):
    """
    Ask Groq to return exactly n_questions in JSON format:
    [
      {
        "question": "...",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "answer": "A"
      },
      ...
    ]
    """
    prompt = f"""
Generate exactly {n_questions} multiple-choice questions based on this story.
Return them ONLY in valid JSON (no extra text). The JSON must be an array of objects, each object:
- question: string
- options: array of 4 strings, each starting with "A) ", "B) ", "C) ", "D) "
- answer: single letter string "A" or "B" or "C" or "D"

Story:
{story_text}
"""
    raw = call_groq(prompt, max_tokens=800)

    # Try to parse as JSON directly
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and len(parsed) >= 1:
            # Basic validation
            for obj in parsed:
                if not ("question" in obj and "options" in obj and "answer" in obj):
                    raise ValueError("Missing keys in quiz object")
            # Trim to requested number
            return parsed[:n_questions], None
    except Exception:
        # Try to extract JSON substring if model added commentary
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end+1])
                if isinstance(parsed, list):
                    # basic validation
                    for obj in parsed:
                        if not ("question" in obj and "options" in obj and "answer" in obj):
                            raise ValueError("Missing keys in quiz object")
                    return parsed[:n_questions], None
            except Exception as e:
                return None, f"Failed to parse quiz JSON: {e}\nModel output:\n{raw}"
    return None, f"Model did not return valid JSON quiz. Raw output:\n{raw}"


# Streamlit UI Setup

st.set_page_config(page_title="NeuroBloom Kids AI", page_icon="🌈", layout="centered")

st.markdown("""
<style>

body {
    background-color: #D9EEFF;   /* Light sky blue */
}

/* DARK TEXT for all readability */
h1, h2, h3, h4, h5, h6,
p, label, span, div, input, textarea {
    color: #87CEEB !important; /* sky blue text */
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #26B878, #139DF2);
    color: Black !important;
    padding: 10px 18px;
    font-size: 17px;
    border-radius: 12px;
    border: none;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #139DF2, #26B878);
}

</style>
""", unsafe_allow_html=True)

st.title("🌈 NeuroBloom – Kids AI Friend")
st.caption("Chat • Stories • Images • Read-Aloud • Quizzes")


# Session Storage

if "chat" not in st.session_state:
    st.session_state.chat = []
if "story" not in st.session_state:
    st.session_state.story = ""
# quiz-related
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_answered" not in st.session_state:
    st.session_state.quiz_answered = {}  # keys: q0, q1, q2 -> True/False
if "quiz_submitted_choice" not in st.session_state:
    st.session_state.quiz_submitted_choice = {}  # store selected option text per question


# CHATBOT

st.markdown('<div class="block">', unsafe_allow_html=True)
st.header("💬 Chat with NeuroBloom")

chat_input = st.text_input("Say something…")

if st.button("Send"):
    if chat_input.strip():
        st.session_state.chat.append(("You", chat_input))
        bot = call_groq(chat_input, max_tokens=200)
        st.session_state.chat.append(("NeuroBloom", bot))

for speaker, text in st.session_state.chat:
    st.markdown(f"**{speaker}:** {text}")

st.markdown("</div>", unsafe_allow_html=True)


# STORY GENERATOR

st.markdown('<div class="block">', unsafe_allow_html=True)
st.header("📖 Create a Magical Story")

title = st.text_input("Story Title")
age = st.selectbox("Age Group", ["4-6 yrs", "7-9 yrs", "10-12 yrs"])

if st.button("Generate Story"):
    if title.strip():
        prompt = f"Write a sweet children's story titled '{title}' for kids aged {age}. Make it fun, simple, and magical."
        st.session_state.story = call_groq(prompt, max_tokens=600)
        # reset quiz when new story generated
        st.session_state.quiz_data = None
        st.session_state.quiz_score = 0
        st.session_state.quiz_answered = {}
        st.session_state.quiz_submitted_choice = {}

if st.session_state.story:
    st.subheader("📚 Your Story")
    st.write(st.session_state.story)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Generate Image"):
            img_prompt = f"children's illustration: {st.session_state.story[:200]}"
            img = generate_image(img_prompt)
            if img:
                st.image(img)
            else:
                st.error("❌ Image generation failed.")

    with col2:
        if st.button("Read Aloud"):
            audio = text_to_speech_bytes(st.session_state.story)
            st.audio(audio)

    # -------------------QUIZ-------------------
    with col3:
        # When user clicks Create Quiz -> request structured JSON from model
        if st.button("Create Quiz"):
            if not st.session_state.story.strip():
                st.error("Generate a story first.")
            else:
                quiz_data, err = generate_quiz_json_from_story(st.session_state.story, n_questions=3)
                if err:
                    st.error(err)
                else:
                    # initialize quiz session states
                    st.session_state.quiz_data = quiz_data
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_answered = {}
                    st.session_state.quiz_submitted_choice = {}
                    st.success("Quiz generated! Answer the questions below.")

        # If quiz exists, show interactive questions
        if st.session_state.quiz_data:
            st.subheader("📝 Quiz (3 questions)")
            # iterate through questions
            for i, q in enumerate(st.session_state.quiz_data):
                q_key = f"q{i}"
                # question text
                question_text = q.get("question", f"Question {i+1}")
                options = q.get("options", [])  # Expecting ["A) ...", "B) ...", ...]
                answer_letter = q.get("answer", "").strip().upper()  # "A"/"B"/...

                st.markdown(f"**Q{i+1}: {question_text}**")

                # prepare default selected if previously submitted
                default_idx = None
                if q_key in st.session_state.quiz_submitted_choice:
                    # find index of the stored choice
                    prev = st.session_state.quiz_submitted_choice[q_key]
                    for idx_opt, opt_text in enumerate(options):
                        if opt_text == prev:
                            default_idx = idx_opt
                            break

                # show radio options
                choice = st.radio("", options, key=f"radio_{q_key}", index=default_idx if default_idx is not None else 0)

                # Submit button for this question
                if st.button("Submit Answer", key=f"submit_{q_key}"):
                    # If already answered before, do nothing (prevent double scoring)
                    if st.session_state.quiz_answered.get(q_key, False):
                        st.info("You already answered this question.")
                    else:
                        st.session_state.quiz_submitted_choice[q_key] = choice
                        # determine selected letter by first character (A/B/C/D)
                        selected_letter = choice.strip()[0].upper() if choice and len(choice) > 0 else ""
                        if selected_letter == answer_letter:
                            st.success("✅ Correct!")
                            st.session_state.quiz_score += 1
                        else:
                            # find full correct option text if possible
                            correct_full = next((opt for opt in options if opt.strip().upper().startswith(answer_letter)), "")
                            st.error(f"❌ Wrong! Correct: {answer_letter}. {correct_full}")
                        st.session_state.quiz_answered[q_key] = True

                # If user already submitted earlier in this session, show their result/status
                if st.session_state.quiz_answered.get(q_key, False):
                    prev_choice = st.session_state.quiz_submitted_choice.get(q_key, "")
                    selected_letter = prev_choice.strip()[0].upper() if prev_choice else ""
                    if selected_letter == answer_letter:
                        st.write(f"Your answer: **{prev_choice}** — ✅ Correct")
                    else:
                        correct_full = next((opt for opt in options if opt.strip().upper().startswith(answer_letter)), "")
                        st.write(f"Your answer: **{prev_choice}** — ❌ Wrong. Correct: **{correct_full}**")

                st.write("")  # spacing

            # final score display
            st.markdown(f"**Score: {st.session_state.quiz_score} / {len(st.session_state.quiz_data)}**")

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Made with ❤️ for kids – NeuroBloom")


