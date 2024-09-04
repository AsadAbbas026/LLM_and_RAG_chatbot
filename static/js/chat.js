// Function to generate a new session ID
function generateSessionId() {
    return 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Initialize session ID
let sessionId = generateSessionId();

// Speech Recognition setup
if ('webkitSpeechRecognition' in window) {
    const recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        recognizing = true;
        microphoneButton.textContent = '🔴'; // Red dot to indicate recording
    };

    recognition.onend = () => {
        recognizing = false;
        microphoneButton.textContent = '🎤'; // Reset to microphone icon
    };

    recognition.onresult = (event) => {
        const speechText = event.results[0][0].transcript;
        messageInput.value = speechText;
    };

    const microphoneButton = document.getElementById('send-button');
    microphoneButton.addEventListener('click', () => {
        if (recognizing) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
} else {
    console.log('Speech recognition not supported');
}

// Function to add a message to the chat
function addMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(type === 'user' ? 'user-message' : 'bot-message');

    const messageText = document.createElement('p');
    messageText.textContent = text;
    messageDiv.appendChild(messageText);

    const chatMessages = document.getElementById('chat-messages');
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;  // Auto scroll to bottom
}

// Send button click event
const sendButton = document.getElementById('send-button');
sendButton.addEventListener('click', () => {
    sendMessage();
});

// Enter key press event
const messageInput = document.getElementById('chat-input-field');
messageInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevent default behavior (new line)
        sendMessage();
    }
});

// Function to send a message
async function sendMessage() {
    const text = messageInput.value.trim();
    if (text === '') return;

    addMessage(text, 'user');
    messageInput.value = '';

    try {
        const response = await fetch('http://127.0.0.1:5000/chat', {
            method: 'POST',
            headers: {  
              'Content-Type': 'application/json; charset=UTF-8',
            },
            body: JSON.stringify({ prompt: text, session_id: sessionId }),
        });

        if (response.ok) {
            const data = await response.json();
            const reply = data.response;
            addMessage(reply, 'bot');
        } else {
            addMessage('Error: Unable to get a response', 'bot');
        }
    } catch (error) {
        addMessage('Error: Unable to get a response', 'bot');
    }
}
