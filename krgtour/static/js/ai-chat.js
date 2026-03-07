/**
 * AI Chat Assistant JavaScript
 * AJAX communication with Django/Ollama backend
 */

(function() {
    'use strict';

    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const quickBtns = document.querySelectorAll('[data-quick-message]');

    if (!chatMessages || !chatInput || !sendBtn) return;

    let history = []; // Conversation history for context
    let isLoading = false;

    const CSRF_TOKEN = document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';

    // Send message
    async function sendMessage(text) {
        if (isLoading || !text.trim()) return;

        appendMessage(text, 'user');
        chatInput.value = '';
        chatInput.style.height = 'auto';

        // Add to history
        history.push({ role: 'user', content: text });

        // Show typing indicator
        const typingId = showTyping();
        isLoading = true;
        sendBtn.disabled = true;

        try {
            const response = await fetch('/ai/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN,
                },
                body: JSON.stringify({
                    message: text,
                    history: history.slice(-10), // Last 10 messages
                }),
            });

            const data = await response.json();
            removeTyping(typingId);

            if (data.success) {
                appendMessage(data.response, 'ai');
                history.push({ role: 'assistant', content: data.response });
            } else {
                appendMessage(data.error || 'Произошла ошибка. Попробуйте снова.', 'ai', true);
            }
        } catch (err) {
            removeTyping(typingId);
            appendMessage('Не удалось подключиться к AI ассистенту. Проверьте соединение.', 'ai', true);
        } finally {
            isLoading = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    function appendMessage(text, role, isError = false) {
        const isUser = role === 'user';
        const avatar = isUser
            ? `<div class="chat-avatar user-av">👤</div>`
            : `<div class="chat-avatar ai">✨</div>`;

        const bubble = document.createElement('div');
        bubble.className = `chat-message ${isUser ? 'user' : 'ai'}`;

        // Parse markdown-like formatting in AI responses
        const formattedText = isUser ? escapeHtml(text) : formatAIResponse(text);

        bubble.innerHTML = `
            ${!isUser ? avatar : ''}
            <div class="chat-bubble ${isError ? 'chat-bubble-error' : ''}">
                ${formattedText}
            </div>
            ${isUser ? avatar : ''}
        `;

        chatMessages.appendChild(bubble);
        scrollToBottom();
    }

    function formatAIResponse(text) {
        // Convert markdown-like formatting
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            // Convert URLs to links
            .replace(/\/routes\/([a-z0-9-]+)\//g, '<a href="/routes/$1/" style="color: var(--primary); font-weight: 600;">🏔 Открыть маршрут</a>');
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function showTyping() {
        const id = 'typing_' + Date.now();
        const bubble = document.createElement('div');
        bubble.id = id;
        bubble.className = 'chat-message ai';
        bubble.innerHTML = `
            <div class="chat-avatar ai">✨</div>
            <div class="chat-bubble">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatMessages.appendChild(bubble);
        scrollToBottom();
        return id;
    }

    function removeTyping(id) {
        document.getElementById(id)?.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Send on Enter (not Shift+Enter)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(chatInput.value);
        }
    });

    sendBtn.addEventListener('click', () => sendMessage(chatInput.value));

    // Quick message buttons
    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            sendMessage(btn.dataset.quickMessage);
        });
    });

    // Welcome message
    setTimeout(() => {
        appendMessage(
            'Привет! Я — AI ассистент КарагандаТур. 🏔\n\n' +
            'Я помогу вам:\n' +
            '• Выбрать маршрут по вашим предпочтениям\n' +
            '• Составить план путешествия\n' +
            '• Рассказать об интересных местах\n' +
            '• Ответить на вопросы о регионе\n\n' +
            'Спрашивайте!',
            'ai'
        );
    }, 500);

})();