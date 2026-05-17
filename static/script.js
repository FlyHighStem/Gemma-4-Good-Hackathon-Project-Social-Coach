// Global variables to track the state
let chatHistory = [];
const urlParams = new URLSearchParams(window.location.search);
const selectedScenario = urlParams.get('scenario');
const selectedDifficulty = urlParams.get('diff');

// --- 🎨 ADAPTIVE THEMING LOGIC ---
const themes = {
    'job_interview': {
        color: '#b7e8e1', // mint
        bg: 'radial-gradient(circle at top right, #fff3b0, #f3e6a7, #e2efe3, #d0f3e0)',
        aiName: 'HR Manager'
    },
    'social_practice': {
        color: '#be9fe4', // Friendly Amber
        bg: 'radial-gradient(circle at top right, #e6b6ae, #f8f0ec, #f7d9fa, #d5c1ed)',
        aiName: 'Friend'
    }
};

function applyTheme() {
    const theme = themes[selectedScenario] || themes['job_interview'];
    const root = document.documentElement;

    // Apply color and background
    root.style.setProperty('--primary', theme.color);
    document.body.style.background = theme.bg;

    // Adapt for Difficulty
    if (selectedDifficulty === 'hard') {
        root.style.setProperty('--primary', '#ef4444'); // High-pressure Red
        document.querySelector('.live-indicator').innerText = '● INTENSE COACH';
    }
}
applyTheme();

// --- End Session Logic ---

async function handleEndSession() {
    try {
        // 1. Tell the server to wipe the recordings
        const response = await fetch("/end_session", { method: "POST" });

        if (response.ok) {
            // 2. Once cleanup is confirmed, redirect
            window.location.href = "/";
        }
    } catch (error) {
        console.error("Cleanup failed, redirecting anyway...", error);
        window.location.href = "/";
    }
}

// --- 🎙️ AUDIO RECORDING SETUP ---
let mediaRecorder;
let audioChunks = [];
const micBtn = document.getElementById('micBtn');
const micIcon = document.getElementById('micIcon');
const userInput = document.getElementById('userInput');
const typingIndicator = document.getElementById('typingIndicator');

micBtn.addEventListener('click', async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        micIcon.innerText = "🎤";
        micBtn.classList.remove('pulse');
    } else {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);

            mediaRecorder.onstop = async () => {
                    // 1. Add 'codecs=opus' to ensure Google's API recognizes the format immediately
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm;codecs=opus' });

                    // 2. CRITICAL: Clear the chunks array immediately to prevent file corruption
                    // on the next recording attempt
                    audioChunks = [];

                    // 3. Threshold Check: If it's under 5KB, it's too short to have a valid header
                    if (audioBlob.size < 5000) {
                        typingIndicator.style.display = "none";
                        displayMessage("ai", "I didn't quite catch that. Please speak for at least 3 seconds!");
                        micIcon.innerText = "🎤";
                        micBtn.classList.remove('pulse');
                        return;
                    }

                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audioHTML = `<audio controls src="${audioUrl}"></audio>`;
                    sendAudioToServer(audioBlob, audioHTML);

                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                    }
                    micIcon.innerText = "🎤";
                    micBtn.classList.remove('pulse');
                };

            mediaRecorder.start();
            micIcon.innerText = "🛑";
            micBtn.classList.add('pulse');
        } catch (err) {
            alert("Microphone access denied.");
        }
    }
});

/**
 * Handles Audio Upload and UI update
 */
async function sendAudioToServer(blob, audioHTML) {
    const formData = new FormData();
    formData.append('audio', blob, 'user_speech.webm');

    // Ensure these variables match your global constants at the top of the file
    formData.append('scenario', selectedScenario);
    formData.append('difficulty', selectedDifficulty);
    formData.append('history', JSON.stringify(chatHistory));

    displayMessage("user", audioHTML);
    typingIndicator.style.display = "block";

    try {
        const response = await fetch("/process_audio", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        console.log("Server Response:", data); // Debugging: See what the server actually sent

        typingIndicator.style.display = "none";

        // --- 🛡️ SAFETY CHECK ---
        if (data.error) {
            // If the server sent an error message, display that instead of 'undefined'
            displayMessage("ai", "System Error: " + data.error);
            return;
        }

        if (data.response) {
            displayMessage("ai", data.response);
            chatHistory.push({ user: "[Audio Message]", assistant: data.response });
            updateCoachFeedback(data.feedback);
        } else {
            displayMessage("ai", "Error: Received empty response from Gemma.");
        }

    } catch (error) {
        console.error("Fetch Error:", error);
        typingIndicator.style.display = "none";
        displayMessage("ai", "Connection Error: Could not reach the server.");
    }
}

/**
 * Manual Text Send
 */
async function sendMessage() {
    const userMessage = userInput.value.trim();
    if (!userMessage) return;

    displayMessage("user", userMessage);
    userInput.value = "";
    typingIndicator.style.display = "block";

    try {
        const response = await fetch("/get_response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userMessage,
                scenario: selectedScenario,
                difficulty: selectedDifficulty,
                history: chatHistory
            })
        });
        const data = await response.json();

        typingIndicator.style.display = "none";
        displayMessage("ai", data.response);
        chatHistory.push({ user: userMessage, assistant: data.response });

        const feedbackRes = await fetch("/get_feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userMessage })
        });
        const feedbackData = await feedbackRes.json();
        updateCoachFeedback(feedbackData.feedback);
    } catch (error) {
        typingIndicator.style.display = "none";
        displayMessage("ai", "Connection Error.");
    }
}

function displayMessage(role, content) {
    const chatBox = document.getElementById("chatBox");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${role === 'user' ? 'user-msg' : 'ai-msg'}`;
    const avatar = role === 'user' ? '👤' : '🤖';

    messageDiv.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="msg-content">${content}</div>
    `;

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * Updates Coach Feedback with scrolling
 */
function updateCoachFeedback(feedbackText) {
    const feedbackEl = document.getElementById("feedback-content");

    // Instead of replacing, we append for a scrollable history
    const logEntry = document.createElement("p");
    logEntry.style.marginBottom = "15px";
    logEntry.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
    logEntry.style.paddingBottom = "5px";
    logEntry.innerHTML = `<strong>➤</strong> ${feedbackText}`;

    feedbackEl.appendChild(logEntry);

    // Smooth scroll the feedback panel to bottom
    feedbackEl.scrollTop = feedbackEl.scrollHeight;
}

userInput.addEventListener("keypress", (e) => { if (e.key === "Enter") sendMessage(); });