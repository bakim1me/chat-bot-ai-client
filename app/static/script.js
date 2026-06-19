document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatContainer = document.getElementById('chatContainer');
    const sendBtn = document.getElementById('sendBtn');

    // Setting Panel Elements
    const useLlmToggle = document.getElementById('useLlmToggle');
    const topKSlider = document.getElementById('topKSlider');
    const topKValue = document.getElementById('topKValue');
    const scoreThresholdSlider = document.getElementById('scoreThresholdSlider');
    const scoreThresholdValue = document.getElementById('scoreThresholdValue');

    // Settings Binding
    topKSlider.addEventListener('input', (e) => {
        topKValue.textContent = e.target.value;
    });

    scoreThresholdSlider.addEventListener('input', (e) => {
        scoreThresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // DOM Helpers
    const scrollToBottom = () => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    const appendUserMessage = (text) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper user-wrapper';
        wrapper.innerHTML = `<div class="message user-message">${escapeHTML(text)}</div>`;
        chatContainer.appendChild(wrapper);
        scrollToBottom();
    };

    const appendTypingIndicator = (timeBadgeId) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper ai-wrapper';
        wrapper.id = 'typingIndicator';
        wrapper.innerHTML = `
            <div class="message ai-message">
                <div class="typing-indicator">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
            <span class="time-badge" id="${timeBadgeId}">0m 0s</span>
        `;
        chatContainer.appendChild(wrapper);
        scrollToBottom();
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    };

    const appendAIMessage = (text, isHtml = false, timeStr = "") => {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper ai-wrapper';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ai-message';
        if (isHtml) {
            messageDiv.innerHTML = text; // allow HTML for raw chunks
        } else {
            messageDiv.innerHTML = escapeHTML(text);
        }
        
        wrapper.appendChild(messageDiv);

        if (timeStr) {
            const timeBadge = document.createElement('span');
            timeBadge.className = 'time-badge';
            timeBadge.textContent = timeStr;
            wrapper.appendChild(timeBadge);
        }

        chatContainer.appendChild(wrapper);
        scrollToBottom();
    };

    const escapeHTML = (str) => {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag])
        );
    };

    // Chat form submission
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        // UI State update
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;
        
        appendUserMessage(text);
        
        // Start local timer
        const startTime = Date.now();
        const timeBadgeId = 'time-' + startTime;
        appendTypingIndicator(timeBadgeId);
        
        const timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const m = Math.floor(elapsed / 60);
            const s = elapsed % 60;
            const badge = document.getElementById(timeBadgeId);
            if(badge) badge.textContent = `${m}m ${s}s`;
        }, 1000);

        try {
            // Get current setting values
            const useLlm = useLlmToggle.checked;
            const topK = parseInt(topKSlider.value, 10);
            const scoreThreshold = parseFloat(scoreThresholdSlider.value);

            // Backend API Call with query parameter
            const response = await fetch(`/api/v1/chat/?use_llm=${useLlm}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    question: text,
                    top_k: topK,
                    score_threshold: scoreThreshold
                })
            });

            const data = await response.json();
            
            removeTypingIndicator();
            clearInterval(timerInterval);

            // Calculate final time string
            const finalElapsed = Math.floor((Date.now() - startTime) / 1000);
            const timeStr = `${Math.floor(finalElapsed / 60)}m ${finalElapsed % 60}s`;

            if (response.ok) {
                if (useLlm && data.answer) {
                    // LLM Answer mode
                    appendAIMessage(data.answer, false, timeStr);
                } else if (!useLlm && data.retrieved_chunks && data.retrieved_chunks.length > 0) {
                    // LLM OFF -> Display retrieved chunks
                    let chunkHtml = `<strong>[Gemini 비활성화 - 검색 결과만 표시]</strong><br><br>`;
                    data.retrieved_chunks.forEach((c, idx) => {
                        chunkHtml += `<span class="chunk-source">${idx + 1}. [${escapeHTML(c.source)}]</span> (Score: ${c.score.toFixed(3)})<br>`;
                        chunkHtml += `<div>${escapeHTML(c.text)}</div><br>`;
                    });
                    appendAIMessage(chunkHtml, true, timeStr);
                } else {
                    appendAIMessage("해당 조건으로 검색된 결과가 없습니다.", false, timeStr);
                }
            } else {
                appendAIMessage("죄송합니다. 오류가 발생했습니다: " + (data.detail || "서버 응답 실패"), false, timeStr);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            removeTypingIndicator();
            clearInterval(timerInterval);
            appendAIMessage("네트워크 오류가 발생했습니다. 서버가 켜져 있는지 확인해주세요.");
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    });
});
