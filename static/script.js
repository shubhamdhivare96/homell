document.addEventListener('DOMContentLoaded', () => {
    // Modal elements
    const openVoiceBot = document.getElementById('openVoiceBot');
    const voiceBotModal = document.getElementById('voiceBotModal');
    const closeVoiceBot = document.getElementById('closeVoiceBot');
    const startButton = document.getElementById('startRecording');
    const stopButton = document.getElementById('stopRecording');
    const sendButton = document.getElementById('sendQuestion');
    const questionInput = document.getElementById('questionInput');
    const responseDiv = document.getElementById('response');

    // Preset questions
    const presetQuestions = [
        "What should we know about your life story in a few sentences?",
        "What's your #1 superpower?",
        "What are the top 3 areas you'd like to grow in?",
        "What misconception do your coworkers have about you?",
        "How do you push your boundaries and limits?"
    ];

    // Add preset questions to modal
    const presetContainer = document.createElement('div');
    presetContainer.className = 'mb-4 flex flex-wrap gap-2';
    presetQuestions.forEach(q => {
        const btn = document.createElement('button');
        btn.textContent = q;
        btn.className = 'bg-gray-200 text-gray-800 px-2 py-1 rounded hover:bg-gray-300 text-sm';
        btn.onclick = () => {
            questionInput.value = q;
        };
        presetContainer.appendChild(btn);
    });
    questionInput.parentNode.insertBefore(presetContainer, questionInput);

    // Modal open/close logic
    openVoiceBot.addEventListener('click', () => {
        voiceBotModal.classList.remove('hidden');
    });
    closeVoiceBot.addEventListener('click', () => {
        voiceBotModal.classList.add('hidden');
        responseDiv.textContent = '';
        questionInput.value = '';
    });

    // Speech recognition
    let isRecording = false;
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
            .map(result => result[0].transcript)
            .join('');
        questionInput.value = transcript;
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        stopRecording();
    };

    // Start recording
    startButton.addEventListener('click', () => {
        try {
            recognition.start();
            isRecording = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            startButton.classList.add('recording');
        } catch (error) {
            console.error('Error starting recording:', error);
        }
    });

    // Stop recording
    stopButton.addEventListener('click', () => {
        stopRecording();
    });

    function stopRecording() {
        recognition.stop();
        isRecording = false;
        startButton.disabled = false;
        stopButton.disabled = true;
        startButton.classList.remove('recording');
    }

    // Send question
    sendButton.addEventListener('click', async () => {
        const question = questionInput.value.trim();
        if (!question) return;

        responseDiv.textContent = 'Thinking...';
        // Hide main speaker button while loading
        mainSpeakBtn.style.display = 'none';
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question }),
            });

            const data = await response.json();
            
            if (data.error) {
                responseDiv.textContent = `Error: ${data.error}`;
                return;
            }

            responseDiv.textContent = data.response;
            // Show main speaker button
            mainSpeakBtn.style.display = 'inline-flex';
            mainSpeakBtn.onclick = async () => {
                if (isPlaying && currentAudio) {
                    currentAudio.pause();
                    currentAudio.currentTime = 0;
                    isPlaying = false;
                    mainSpeakBtn.innerHTML = '<i class="fas fa-volume-up mr-2"></i> Speak';
                    return;
                }
                try {
                    const text = responseDiv.textContent;
                    const speakResponse = await fetch('/api/speak', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ text }),
                    });
                    const speakData = await speakResponse.json();
                    if (speakData.error) {
                        console.error('Error:', speakData.error);
                        return;
                    }
                    if (currentAudio) {
                        currentAudio.pause();
                        currentAudio.currentTime = 0;
                    }
                    currentAudio = new Audio(`data:audio/wav;base64,${speakData.audio}`);
                    currentAudio.onended = () => {
                        isPlaying = false;
                        mainSpeakBtn.innerHTML = '<i class="fas fa-volume-up mr-2"></i> Speak';
                    };
                    currentAudio.play();
                    isPlaying = true;
                    mainSpeakBtn.innerHTML = '<i class="fas fa-stop mr-2"></i> Stop';
                } catch (error) {
                    console.error('Error playing audio:', error);
                }
            };
        } catch (error) {
            console.error('Error:', error);
            responseDiv.textContent = 'Error: Could not get response';
        }
    });

    // Add this after DOMContentLoaded
    const mainSpeakBtn = document.getElementById('mainSpeakBtn');
    mainSpeakBtn.style.display = 'none';
    let currentAudio = null;
    let isPlaying = false;
}); 