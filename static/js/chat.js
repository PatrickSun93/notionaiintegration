// Enhanced chat functionality for AI interaction

let chatHistory = [];
let isTyping = false;
let currentContextPage = null;
let chatSocket = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let messageQueue = [];
let isOnline = navigator.onLine;

// Initialize chat interface
document.addEventListener('DOMContentLoaded', function() {
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('message-input');
    const providerSelect = document.getElementById('ai-provider');
    const contextSelect = document.getElementById('context-page');
    
    // Initialize WebSocket connection for real-time updates
    initializeWebSocket();
    
    // Monitor online/offline status
    setupConnectionMonitoring();
    
    // Load available pages for context
    loadContextPages();
    
    // Load chat history from localStorage
    loadChatHistory();
    
    // Check URL parameters for pre-selected page
    const urlParams = new URLSearchParams(window.location.search);
    const pageId = urlParams.get('page_id');
    if (pageId) {
        contextSelect.value = pageId;
        updateContextInfo(pageId);
    }
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter (but not Shift+Enter)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea and update character count
    messageInput.addEventListener('input', function() {
        // Auto-resize
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        
        // Update character count
        const charCount = this.value.length;
        document.getElementById('char-count').textContent = charCount;
        
        // Enable/disable send button
        const sendButton = document.getElementById('send-button');
        sendButton.disabled = charCount === 0 || isTyping || !isOnline;
        
        // Show typing indicator to other users (if multi-user)
        if (charCount > 0) {
            sendTypingIndicator();
        }
    });
    
    // Provider change handler with validation
    providerSelect.addEventListener('change', async function() {
        const provider = this.value;
        updateChatStatus(`Switching to ${this.options[this.selectedIndex].text}...`);
        
        try {
            // Validate provider availability
            const response = await apiCall(`/api/validate_provider/${provider}`);
            if (response.success) {
                updateChatStatus(`Switched to ${this.options[this.selectedIndex].text}`);
                showInfo(`Now using ${this.options[this.selectedIndex].text} for AI responses`);
            } else {
                throw new Error(response.error || 'Provider validation failed');
            }
        } catch (error) {
            updateChatStatus('Provider switch failed');
            showWarning(`Failed to switch to ${this.options[this.selectedIndex].text}: ${error.message}`);
            // Revert to previous selection
            this.value = this.dataset.previousValue || 'openai';
        }
        
        this.dataset.previousValue = this.value;
    });
    
    // Context page change handler
    contextSelect.addEventListener('change', function() {
        if (this.value) {
            updateContextInfo(this.value);
        } else {
            currentContextPage = null;
            updateChatStatus('No context selected');
        }
    });
    
    // Auto-save chat periodically
    setInterval(saveChatHistory, 30000); // Save every 30 seconds
    
    // Setup drag and drop for file uploads
    setupDragAndDrop();
});

async function loadContextPages() {
    try {
        updateChatStatus('Loading pages...');
        const response = await apiCall('/api/pages');
        const contextSelect = document.getElementById('context-page');
        
        // Clear existing options except the first one
        while (contextSelect.children.length > 1) {
            contextSelect.removeChild(contextSelect.lastChild);
        }
        
        if (response.success && response.pages) {
            response.pages.forEach(page => {
                const option = document.createElement('option');
                option.value = page.id;
                option.textContent = page.title || 'Untitled';
                option.dataset.lastEdited = page.last_edited_time;
                contextSelect.appendChild(option);
            });
            updateChatStatus(`Loaded ${response.pages.length} pages`);
        } else {
            updateChatStatus('No pages found');
        }
    } catch (error) {
        console.error('Failed to load pages for context:', error);
        updateChatStatus('Failed to load pages');
        addMessageToChat('error', 'Failed to load pages for context. Please check your Notion connection.');
    }
}

async function updateContextInfo(pageId) {
    try {
        const response = await apiCall(`/api/page/${pageId}`);
        if (response.success && response.page) {
            currentContextPage = response.page;
            updateChatStatus(`Context: ${response.page.title}`);
            
            // Show context info message
            addMessageToChat('system', `📄 Context set to: "${response.page.title}". AI responses will now consider this page's content.`);
        }
    } catch (error) {
        console.error('Failed to load page context:', error);
        updateChatStatus('Failed to load context');
    }
}

async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const providerSelect = document.getElementById('ai-provider');
    const contextSelect = document.getElementById('context-page');
    
    const message = messageInput.value.trim();
    if (!message || isTyping || !isOnline) return;
    
    // Hide welcome message if it exists
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    // Add user message to chat
    const userMessageId = addMessageToChat('user', message);
    
    // Clear input and set loading state
    messageInput.value = '';
    messageInput.style.height = 'auto';
    document.getElementById('char-count').textContent = '0';
    setTypingState(true);
    
    // Create progress indicator
    const progressContainer = document.createElement('div');
    progressContainer.className = 'message-progress';
    const progress = createProgressBar(progressContainer);
    progress.setIndeterminate(true);
    
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.appendChild(progressContainer);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    try {
        const requestData = {
            message: message,
            provider: providerSelect.value,
            page_id: contextSelect.value || null,
            chat_history: chatHistory.slice(-10), // Send last 10 messages for context
            message_id: userMessageId,
            timestamp: new Date().toISOString()
        };
        
        updateChatStatus('AI is thinking...');
        
        // Add to message queue for offline handling
        if (!isOnline) {
            messageQueue.push(requestData);
            showWarning('Message queued - will send when connection is restored');
            return;
        }
        
        const response = await apiCall('/api/chat', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        // Remove progress indicator
        progress.remove();
        
        if (response.success) {
            // Add AI response to chat with streaming effect
            const aiMessageId = addMessageToChat('ai', '', response.provider);
            await streamMessage(aiMessageId, response.response);
            updateChatStatus('Ready');
            
            // Update message in history
            const historyMessage = chatHistory.find(msg => msg.id === aiMessageId);
            if (historyMessage) {
                historyMessage.content = response.response;
            }
        } else {
            throw new Error(response.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        // Remove progress indicator
        progress.remove();
        
        addMessageToChat('error', 'Failed to get AI response: ' + error.message);
        updateChatStatus('Error occurred');
        
        // Retry logic for network errors
        if (error.message.includes('fetch') || error.message.includes('network')) {
            showRetryOption(requestData);
        }
    } finally {
        setTypingState(false);
    }
}

// Stream message content for better UX
async function streamMessage(messageId, content) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"] .message-content`);
    if (!messageElement) return;
    
    const words = content.split(' ');
    let currentIndex = 0;
    
    return new Promise((resolve) => {
        const interval = setInterval(() => {
            if (currentIndex < words.length) {
                const currentText = words.slice(0, currentIndex + 1).join(' ');
                messageElement.innerHTML = formatMessageContent(currentText, 'ai');
                currentIndex++;
                
                // Auto-scroll
                const messagesContainer = document.getElementById('chat-messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } else {
                clearInterval(interval);
                resolve();
            }
        }, 50); // Adjust speed as needed
    });
}

// Show retry option for failed messages
function showRetryOption(requestData) {
    const retryContainer = document.createElement('div');
    retryContainer.className = 'message message-system';
    retryContainer.innerHTML = `
        <div class="message-header">
            <div class="message-sender">
                <span class="sender-icon">🔄</span>
                <span class="sender-name">System</span>
            </div>
        </div>
        <div class="message-content">
            <div class="system-content">
                Message failed to send. 
                <button class="btn-small btn-primary" onclick="retryMessage('${JSON.stringify(requestData).replace(/'/g, "\\'")}')">
                    Retry
                </button>
            </div>
        </div>
    `;
    
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.appendChild(retryContainer);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Retry failed message
async function retryMessage(requestDataStr) {
    try {
        const requestData = JSON.parse(requestDataStr);
        
        // Remove retry message
        event.target.closest('.message').remove();
        
        // Resend message
        setTypingState(true);
        updateChatStatus('Retrying...');
        
        const response = await apiCall('/api/chat', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (response.success) {
            const aiMessageId = addMessageToChat('ai', '', response.provider);
            await streamMessage(aiMessageId, response.response);
            updateChatStatus('Ready');
        } else {
            throw new Error(response.error || 'Retry failed');
        }
        
    } catch (error) {
        addMessageToChat('error', 'Retry failed: ' + error.message);
        updateChatStatus('Error occurred');
    } finally {
        setTypingState(false);
    }
}

function addMessageToChat(type, content, provider = null) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    messageDiv.className = `message message-${type}`;
    messageDiv.dataset.messageId = messageId;
    
    const timestamp = new Date().toLocaleTimeString();
    let senderName = type === 'user' ? 'You' : type === 'ai' ? (provider ? provider.toUpperCase() : 'AI') : 'System';
    
    // Format content for better display
    const formattedContent = formatMessageContent(content, type);
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <div class="message-sender">
                <span class="sender-icon">${getSenderIcon(type)}</span>
                <span class="sender-name">${senderName}</span>
            </div>
            <span class="message-time">${timestamp}</span>
        </div>
        <div class="message-content">${formattedContent}</div>
        ${type === 'ai' ? '<div class="message-actions"><button class="btn-small btn-outline" onclick="copyMessage(this)">Copy</button><button class="btn-small btn-outline" onclick="regenerateResponse(this)">Regenerate</button></div>' : ''}
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in chat history (exclude system messages from history)
    if (type !== 'system') {
        const historyEntry = {
            id: messageId,
            type: type,
            content: content,
            timestamp: new Date().toISOString(),
            provider: provider
        };
        
        chatHistory.push(historyEntry);
        
        // Save to localStorage
        saveChatHistory();
    }
    
    // Animate message appearance
    setTimeout(() => {
        messageDiv.classList.add('message-appear');
    }, 10);
    
    return messageId;
}

// WebSocket functionality for real-time updates
function initializeWebSocket() {
    // Only initialize if WebSocket is supported
    if (!window.WebSocket) {
        console.log('WebSocket not supported');
        return;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
    
    try {
        chatSocket = new WebSocket(wsUrl);
        
        chatSocket.onopen = function(e) {
            console.log('WebSocket connected');
            reconnectAttempts = 0;
            updateChatStatus('Connected');
        };
        
        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            handleWebSocketMessage(data);
        };
        
        chatSocket.onclose = function(e) {
            console.log('WebSocket disconnected');
            updateChatStatus('Disconnected');
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                setTimeout(() => {
                    reconnectAttempts++;
                    console.log(`Reconnection attempt ${reconnectAttempts}`);
                    initializeWebSocket();
                }, 1000 * Math.pow(2, reconnectAttempts)); // Exponential backoff
            }
        };
        
        chatSocket.onerror = function(e) {
            console.error('WebSocket error:', e);
        };
        
    } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
    }
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'typing':
            showTypingIndicator(data.user);
            break;
        case 'message':
            addMessageToChat(data.messageType, data.content, data.provider);
            break;
        case 'status':
            updateChatStatus(data.message);
            break;
        case 'error':
            showError(data.message);
            break;
    }
}

function sendTypingIndicator() {
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            type: 'typing',
            user: 'current_user'
        }));
    }
}

// Connection monitoring
function setupConnectionMonitoring() {
    window.addEventListener('online', function() {
        isOnline = true;
        updateChatStatus('Back online');
        showSuccess('Connection restored');
        
        // Process queued messages
        processMessageQueue();
        
        // Reconnect WebSocket if needed
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
            initializeWebSocket();
        }
    });
    
    window.addEventListener('offline', function() {
        isOnline = false;
        updateChatStatus('Offline');
        showWarning('Connection lost - messages will be queued');
    });
    
    // Periodic connection check
    setInterval(checkConnection, 30000); // Check every 30 seconds
}

async function checkConnection() {
    try {
        const response = await fetch('/api/health', { 
            method: 'HEAD',
            cache: 'no-cache'
        });
        
        if (!response.ok) {
            throw new Error('Health check failed');
        }
        
        if (!isOnline) {
            isOnline = true;
            updateChatStatus('Connection restored');
            processMessageQueue();
        }
    } catch (error) {
        if (isOnline) {
            isOnline = false;
            updateChatStatus('Connection issues detected');
        }
    }
}

function processMessageQueue() {
    if (messageQueue.length === 0) return;
    
    showInfo(`Sending ${messageQueue.length} queued messages...`);
    
    messageQueue.forEach(async (requestData, index) => {
        try {
            const response = await apiCall('/api/chat', {
                method: 'POST',
                body: JSON.stringify(requestData)
            });
            
            if (response.success) {
                const aiMessageId = addMessageToChat('ai', '', response.provider);
                await streamMessage(aiMessageId, response.response);
            }
        } catch (error) {
            addMessageToChat('error', `Queued message failed: ${error.message}`);
        }
    });
    
    messageQueue = [];
    showSuccess('All queued messages sent');
}

// Drag and drop functionality
function setupDragAndDrop() {
    const chatContainer = document.getElementById('chat-messages');
    
    chatContainer.addEventListener('dragover', function(e) {
        e.preventDefault();
        chatContainer.classList.add('drag-over');
    });
    
    chatContainer.addEventListener('dragleave', function(e) {
        e.preventDefault();
        chatContainer.classList.remove('drag-over');
    });
    
    chatContainer.addEventListener('drop', function(e) {
        e.preventDefault();
        chatContainer.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        handleFileUpload(files);
    });
}

async function handleFileUpload(files) {
    for (const file of files) {
        if (file.type.startsWith('text/') || file.name.endsWith('.md')) {
            try {
                const content = await readFileAsText(file);
                const messageInput = document.getElementById('message-input');
                const currentValue = messageInput.value;
                
                messageInput.value = currentValue + (currentValue ? '\n\n' : '') + 
                    `File: ${file.name}\n\`\`\`\n${content}\n\`\`\``;
                
                messageInput.dispatchEvent(new Event('input'));
                showSuccess(`File "${file.name}" added to message`);
            } catch (error) {
                showError(`Failed to read file "${file.name}": ${error.message}`);
            }
        } else {
            showWarning(`File type not supported: ${file.name}`);
        }
    }
}

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = e => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}

function formatMessageContent(content, type) {
    if (type === 'error') {
        return `<div class="error-content">⚠️ ${escapeHtml(content)}</div>`;
    }
    
    if (type === 'system') {
        return `<div class="system-content">${escapeHtml(content)}</div>`;
    }
    
    // Convert markdown-like formatting
    let formatted = escapeHtml(content);
    
    // Bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Italic text
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code blocks
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    
    // Inline code
    formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function getSenderIcon(type) {
    switch (type) {
        case 'user': return '👤';
        case 'ai': return '🤖';
        case 'system': return 'ℹ️';
        case 'error': return '⚠️';
        default: return '💬';
    }
}

function setTypingState(typing) {
    isTyping = typing;
    const typingIndicator = document.getElementById('typing-indicator');
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('message-input');
    
    if (typing) {
        typingIndicator.style.display = 'flex';
        sendButton.disabled = true;
        messageInput.disabled = true;
    } else {
        typingIndicator.style.display = 'none';
        sendButton.disabled = messageInput.value.trim().length === 0;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

function updateChatStatus(status) {
    const statusText = document.querySelector('.status-text');
    const statusIndicator = document.querySelector('.status-indicator');
    
    if (statusText) {
        statusText.textContent = status;
    }
    
    if (statusIndicator) {
        statusIndicator.className = 'status-indicator';
        if (status.includes('Error') || status.includes('Failed')) {
            statusIndicator.classList.add('status-error');
        } else if (status.includes('thinking') || status.includes('Loading')) {
            statusIndicator.classList.add('status-loading');
        } else {
            statusIndicator.classList.add('status-ready');
        }
    }
}

// Quick action functions
function insertQuickPrompt(prompt) {
    const messageInput = document.getElementById('message-input');
    const currentValue = messageInput.value.trim();
    
    if (currentValue) {
        messageInput.value = currentValue + '\n\n' + prompt;
    } else {
        messageInput.value = prompt;
    }
    
    messageInput.focus();
    messageInput.dispatchEvent(new Event('input'));
}

// Chat management functions
function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        chatHistory = [];
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">🤖</div>
                <h3>Chat Cleared!</h3>
                <p>Start a new conversation with your AI assistant.</p>
            </div>
        `;
        saveChatHistory();
        updateChatStatus('Chat cleared');
    }
}

function exportChat() {
    if (chatHistory.length === 0) {
        alert('No chat history to export');
        return;
    }
    
    const chatData = {
        exported_at: new Date().toISOString(),
        messages: chatHistory
    };
    
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Message action functions
function copyMessage(button) {
    const messageContent = button.closest('.message').querySelector('.message-content');
    const text = messageContent.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        button.textContent = 'Copied!';
        setTimeout(() => {
            button.textContent = 'Copy';
        }, 2000);
    }).catch(() => {
        alert('Failed to copy message');
    });
}

function regenerateResponse(button) {
    // Find the user message that prompted this AI response
    const aiMessage = button.closest('.message');
    const messages = Array.from(document.querySelectorAll('.message'));
    const aiIndex = messages.indexOf(aiMessage);
    
    if (aiIndex > 0) {
        const userMessage = messages[aiIndex - 1];
        const userContent = userMessage.querySelector('.message-content').textContent;
        
        // Remove the AI message from display and history
        aiMessage.remove();
        chatHistory.pop();
        
        // Resend the user message
        document.getElementById('message-input').value = userContent;
        sendMessage();
    }
}

// Local storage functions
function saveChatHistory() {
    try {
        localStorage.setItem('notion-ai-chat-history', JSON.stringify(chatHistory));
    } catch (error) {
        console.error('Failed to save chat history:', error);
    }
}

function loadChatHistory() {
    try {
        const saved = localStorage.getItem('notion-ai-chat-history');
        if (saved) {
            chatHistory = JSON.parse(saved);
            
            // Restore messages to chat
            const messagesContainer = document.getElementById('chat-messages');
            if (chatHistory.length > 0) {
                // Hide welcome message
                const welcomeMessage = messagesContainer.querySelector('.welcome-message');
                if (welcomeMessage) {
                    welcomeMessage.style.display = 'none';
                }
                
                // Add messages
                chatHistory.forEach(msg => {
                    addMessageToChat(msg.type, msg.content, msg.provider);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
        chatHistory = [];
    }
}

// Context modal functions
function showContextPreview(pageId) {
    // Implementation for context preview modal
    const modal = document.getElementById('context-modal');
    modal.style.display = 'flex';
    
    // Load page content for preview
    loadPagePreview(pageId);
}

function closeContextModal() {
    document.getElementById('context-modal').style.display = 'none';
}

function useContextAndClose() {
    closeContextModal();
    // Context is already set, just close modal
}

async function loadPagePreview(pageId) {
    const preview = document.getElementById('context-preview');
    preview.innerHTML = '<div class="loading-spinner"></div><p>Loading page content...</p>';
    
    try {
        const response = await apiCall(`/api/page/${pageId}`);
        if (response.success && response.page) {
            preview.innerHTML = `
                <h4>${escapeHtml(response.page.title)}</h4>
                <div class="page-meta">
                    <p><strong>Last edited:</strong> ${new Date(response.page.last_edited_time).toLocaleString()}</p>
                </div>
                <div class="page-content">
                    ${escapeHtml(response.page.content).substring(0, 500)}${response.page.content.length > 500 ? '...' : ''}
                </div>
            `;
        }
    } catch (error) {
        preview.innerHTML = `<div class="error-content">Failed to load page preview: ${error.message}</div>`;
    }
}

// Utility function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}