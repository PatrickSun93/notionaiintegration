// Chat functionality for AI interaction

let chatHistory = [];

// Initialize chat interface
document.addEventListener('DOMContentLoaded', function() {
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('message-input');
    const providerSelect = document.getElementById('ai-provider');
    const contextSelect = document.getElementById('context-page');
    
    // Load available pages for context
    loadContextPages();
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter (but not Shift+Enter)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
});

async function loadContextPages() {
    try {
        const response = await apiCall('/api/pages');
        const contextSelect = document.getElementById('context-page');
        
        if (response.pages) {
            response.pages.forEach(page => {
                const option = document.createElement('option');
                option.value = page.id;
                option.textContent = page.title;
                contextSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load pages for context:', error);
    }
}

async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const providerSelect = document.getElementById('ai-provider');
    const contextSelect = document.getElementById('context-page');
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input and set loading state
    messageInput.value = '';
    setLoading(sendButton, true);
    
    try {
        const response = await apiCall('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: message,
                provider: providerSelect.value,
                page_id: contextSelect.value || null
            })
        });
        
        // Add AI response to chat
        addMessageToChat('ai', response.response);
        
    } catch (error) {
        addMessageToChat('error', 'Failed to get AI response: ' + error.message);
    } finally {
        setLoading(sendButton, false);
    }
}

function addMessageToChat(type, content) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    const timestamp = new Date().toLocaleTimeString();
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${type === 'user' ? 'You' : type === 'ai' ? 'AI' : 'System'}</span>
            <span class="message-time">${timestamp}</span>
        </div>
        <div class="message-content">${content}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in chat history
    chatHistory.push({
        type: type,
        content: content,
        timestamp: new Date().toISOString()
    });
}