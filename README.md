# Gemma Social Coach
Empowering Social Intelligence through Multimodal AI Simulation

### 1. 📖 Overview & Motivation
**Gemma Social Coach** is an interactive web application designed to help individuals practice high-stakes social interactions—specifically job interviews and social networking—in a safe, AI-driven environment. 

**The "Good" Factor:** Many individuals struggle with social anxiety or lack access to professional coaching. Often times, they might try to practice improving their social skills, however there aren't very many practical ways to do this without an actual audience. By leveraging **Gemma 3 Flash**, Gemma Social Coach provide a free, accessible, and empathetic "sparring partner" that offers real-time feedback on social intelligence ~~without~~ any of the added peer-pressure or scrutiny from other individuals to discourage them.

---

### 2. 🛠️ Key Features
*   **Multimodal Interaction:** Users talk to Gemma using real-time voice recording, simulating the pressure of a real conversation.
*   **Dynamic Scenarios:** Choose between "Job Interview" or "Social Practice" with adjustable difficulty levels.
*   **The AI Coach:** A secondary "Coach" persona analyzes the interaction and provides actionable feedback on strengths and areas for improvement, specifically for more professional scenarios. This feature is less accurate for casual interactions.
*   **Privacy-First Design:** A dedicated "End Session" feature wipes all temporary recordings and session data from the server.

---

### 3. 🚀 Technical Implementation

#### The Architecture
The project is built using a **Flask** backend and a **Vanilla JavaScript** frontend, communicating with the **Google GenAI SDK**.



#### Core Technologies:
*   **Model:** `gemini-3-flash` (via the `google-genai` library).
*   **Backend:** Python/Flask for handling audio file uploads and API orchestration.
*   **Frontend:** MediaRecorder API for capturing high-quality Opus-encoded audio.

---

### 4. 🧠 Challenges & Solutions

**Challenge: Handling Multimodal Latency**
Initially, sending audio directly resulted in errors because the AI tried to "read" the file while it was still being processed by the server.
*   **Solution:** Changed my strategy in `process_audio` from trying to process the audio directly, to utilizing the Gemma 3 API's in-built audio processing and `base_64`.

**Challenge: Audio File Corruption**
Browsers often append new audio chunks to old ones, creating malformed files.
*   **Solution:** Developed a strict **chunk-management system** in JavaScript that clears the buffer after every transmission and enforces a minimum file size (5KB) to ensure data integrity.

**Challenge: Session Privacy**
To maintain user privacy, I needed a way to ensure voice data didn't persist on the server.
*   **Solution:** Created a custom `/end_session` endpoint that uses `os.unlink` and `shutil` to recursively clear the `recordings/` directory upon exit.

---

### 5. 📊 Sample Prompt Logic
I utilized dynamic system instructions to pivot Gemma’s personality:
```python
# System Instruction Example
"You are a {diff} interviewer for a top tech company. 
Conduct a realistic interview. Keep responses concise 
to encourage the user to speak more."
```

---

### 6. 🌟 Impact & Future Work
This project demonstrates that lightweight models like Gemma 3 Flash are capable of complex multimodal tasks without the need for massive infrastructure. 

**Next Steps:**
*   **Coach Improvement:** Incorporating more sophisticated analysis and feedback for the user.
*   **Expanded Scenarios:** Adding conflict resolution, public speaking, and a variety of other modules.

---

### 7. 📚 Acknowledgments
*   **Google Kaggle Gemma 4 Good Hackathon** for the opportunity.
*   **Gemma 3 Flash** for the lightning-fast multimodal reasoning.
*   **Aanya Tiwari** — myself — for the awesome coding.
