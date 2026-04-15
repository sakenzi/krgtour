/**
 * AI Chat Assistant JavaScript
 * AJAX communication with Django/Ollama backend
 */

(function() {
    'use strict';

    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    if (!chatMessages || !chatInput || !sendBtn) return;

    let history = [];
    let isLoading = false;

    const CSRF_TOKEN = document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';

    async function sendMessage(text) {
        if (isLoading || !text.trim()) return;

        appendMessage(text, 'user');
        chatInput.value = '';
        chatInput.style.height = 'auto';

        history.push({ role: 'user', content: text });

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
                    history: history.slice(-10),
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

    // Expose globally for quick buttons
    window._sendAiMessage = sendMessage;

    function appendMessage(text, role, isError = false) {
        const isUser = role === 'user';
        const avatar = isUser
            ? `<div class="chat-avatar user-av">👤</div>`
            : `<div class="chat-avatar ai">✨</div>`;

        const bubble = document.createElement('div');
        bubble.className = `chat-message ${isUser ? 'user' : 'ai'}`;

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
        return escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
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

    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(chatInput.value);
        }
    });

    sendBtn.addEventListener('click', () => sendMessage(chatInput.value));

    // Welcome message using translation
    setTimeout(() => {
        const lang = (typeof detectLang === 'function') ? detectLang() : 'ru';
        const tr = (typeof T !== 'undefined' && T[lang]) ? T[lang] : {};
        const greeting = lang === 'en'
            ? 'Hello! I\'m the KaragandaTour AI Assistant. 🏔\n\nI can help you:\n• Choose a route based on your preferences\n• Plan your trip\n• Tell you about interesting places\n• Answer questions about the region\n\nFeel free to ask!'
            : lang === 'kk'
            ? 'Сәлем! Мен — КарагандаТур AI Көмекшісімін. 🏔\n\nМен сізге:\n• Қалауыңызға қарай маршрут таңдауға\n• Саяхат жоспарын жасауға\n• Қызықты орындар туралы айтуға\n• Өңір туралы сұрақтарға жауап беруге көмектесемін\n\nСұраңыз!'
            : 'Привет! Я — AI ассистент КарагандаТур. 🏔\n\nЯ помогу вам:\n• Выбрать маршрут по вашим предпочтениям\n• Составить план путешествия\n• Рассказать об интересных местах\n• Ответить на вопросы о регионе\n\nСпрашивайте!';
        appendMessage(greeting, 'ai');
    }, 500);

})();
