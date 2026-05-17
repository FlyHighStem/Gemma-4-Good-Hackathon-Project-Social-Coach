import os
import json
import base64
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# --- 🔑 GEMMA 4 CONFIGURATION --- 
# IMPORTANT: Delete the hardcoded key before pushing to GitHub!
GEMINI_API_KEY = 'YOUR_GEMINI_API_KEY_HERE'
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemma-4-26b-a4b-it"

# --- 🧠 ENHANCED SCENARIO SYSTEM ---
SCENARIOS = {
    "job_interview": {
        "name": "Job Interview",
        "instruction": """
            ROLE: You are an experienced Senior Hiring Manager. 
            VARIABILITY: You can choose the company brand and field.
            CONTEXT: The candidate has entered your office. 
            DIFFICULTY: {diff}.

            INSTRUCTIONS: Start the interview immediately. Be realistic. 
            If difficulty is 'hard', be blunt and challenging. 
            Ask one question at a time.
        """
    },
    "social_practice": {
        "name": "Social Practice",
        "instruction": """
            ROLE: You are a good friend of the user. You are at a local cafe. 
            VARIABILITY: You can choose your gender and name.
            CONTEXT: You just ran into the user.
            DIFFICULTY: {diff}.

            INSTRUCTIONS: Start the conversation. Be warm/friendly if 'easy', 
            and slightly distracted/shy, difficult to read if 'hard'. 
            Ask one question at a time.
        """
    }
}


# --- 🤖 GEMMA CORE LOGIC ---

def call_gemma_ai(user_input, system_instr, history_data, is_audio=False):
    """Generates character response with conversation memory."""
    formatted_history = []
    for turn in history_data:
        formatted_history.append(types.Content(role="user", parts=[types.Part.from_text(text=turn['user'])]))
        formatted_history.append(types.Content(role="model", parts=[types.Part.from_text(text=turn['assistant'])]))

    if is_audio:
        # user_input is the file_uri from Google File API
        current_parts = [
            types.Part.from_uri(file_uri=user_input, mime_type="audio/webm"),
            types.Part.from_text(text="Please respond to this spoken message.")
        ]
    else:
        current_parts = [types.Part.from_text(text=user_input)]

    response = client.models.generate_content(
        model=MODEL_ID,
        config=types.GenerateContentConfig(
            system_instruction=system_instr,
            temperature=0.7,
        ),
        contents=formatted_history + [types.Content(role="user", parts=current_parts)]
    )
    return response.text


def get_coach_feedback(user_text, scenario_id, difficulty):
    """Analyzes tone/empathy using Gemma's Thinking Mode."""

    # Define detailed coaching personalities based on scenario
    scenario_configs = {
        "job_interview": {
            "focus": "Professionalism, confidence, and the STAR method.",
            "persona": "an Executive Career Coach"
        },
        "social_practice": {
            "focus": "Emotional intelligence, warmth, and casual conversational flow.",
            "persona": "a Social Skills Mentor"
        }
    }

    config = scenario_configs.get(scenario_id, {
        "focus": "General communication clarity and empathy.",
        "persona": "a Communication Expert"
    })

    coach_instruction = (
        f"You are {config['persona']}. The user is practicing a {scenario_id.replace('_', ' ')} "
        f"on {difficulty} difficulty. Focus your analysis on: {config['focus']}. "
        "Based on the user's latest input, provide exactly one specific strength "
        "and one actionable 'Pro-Tip' for improvement. Keep it encouraging and under 60 words."
    )

    response = client.models.generate_content(
        model=MODEL_ID,
        config=types.GenerateContentConfig(
            system_instruction=coach_instruction,
            thinking_config=types.ThinkingConfig(include_thoughts=True),
            temperature=0.4
        ),
        contents=f"Analyze this interaction: '{user_text}'"
    )
    return response.text


# --- 🌐 ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat")
def chat_page():
    scenario = request.args.get('scenario')
    difficulty = request.args.get('diff')
    return render_template("chat.html", scenario=scenario, difficulty=difficulty)

@app.route("/process_audio", methods=["POST"])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio"}), 400

    audio_file = request.files['audio']
    scenario_id = request.form.get("scenario")
    difficulty = request.form.get("difficulty")
    history = json.loads(request.form.get("history", "[]"))

    if not scenario_id or not difficulty:
        return jsonify({"error": "Session variables missing"}), 400

    try:
        # 1. Read raw audio bytes directly from the memory buffer (No local saving needed!)
        audio_bytes = audio_file.read()

        # 2. Convert to Base64 string for the API payload
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # 3. Match Scenario Context
        scenario_data = SCENARIOS.get(scenario_id, SCENARIOS['job_interview'])
        system_instr = scenario_data['instruction'].format(diff=difficulty)

        # 4. Construct the inline content payload
        # This bypasses the Files API entirely and sends data "inline"
        contents = [
            {
                "inline_data": {
                    "mime_type": "audio/webm",
                    "data": audio_b64
                }
            },
            "The user said the phrase above. Respond to them in character."
        ]

        # 5. Call the model directly
        # Note: If your call_gemma_ai function expects a URI, you can replace that call
        # with this direct client implementation:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Use your active model string here
            contents=contents,
            config={"system_instruction": system_instr}
        )
        ai_response = response.text

        # 6. Integrated Coaching
        feedback_context = (
            f"Scenario: {scenario_id} ({difficulty}). "
            f"User spoke via audio. AI responded: {ai_response[:100]}"
        )
        feedback = get_coach_feedback(feedback_context, scenario_id, difficulty)

        return jsonify({"response": ai_response, "feedback": feedback})

    except Exception as e:
        print(f"DIRECT API ERROR: {str(e)}")
        return jsonify({"error": "Failed to communicate with AI directly."}), 500
@app.route("/process_audio", methods=["POST"])
def analyze_voice_tone(audio_path):
    # Upload the file to Gemini/Gemma 4
    audio_file = client.files.upload(path=audio_path)

    # Ask the model to analyze the VIBE, not just the words
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            audio_file,
            "Listen to the user's voice. Do they sound confident, nervous, or aggressive? Give a 1-sentence tip."
        ]
    )
    return response.text

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json()
    scenario_id = data.get('scenario', 'job_interview')
    difficulty = data.get('difficulty', 'medium')
    user_message = data.get('message', '')
    history = data.get('history', [])

    scenario_data = SCENARIOS.get(scenario_id, SCENARIOS['job_interview'])
    system_instr = scenario_data['instruction'].format(diff=difficulty)

    ai_response = call_gemma_ai(user_message, system_instr, history)
    return jsonify({"response": ai_response})


@app.route("/get_feedback", methods=["POST"])
def get_feedback():
    data = request.get_json()
    user_msg = data.get("message", "")
    scenario = data.get("scenario", "job_interview")  # FIX: Pull from request
    difficulty = data.get("difficulty", "medium")  # FIX: Pull from request

    # Pass all 3 required arguments
    feedback = get_coach_feedback(user_msg, scenario, difficulty)
    return jsonify({"feedback": feedback})


import shutil


@app.route("/end_session", methods=["POST"])
def end_session():
    folder = 'recordings'
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Delete file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Delete subfolders if any
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

    return jsonify({"status": "cleaned"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=1000, debug=True)