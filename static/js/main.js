// Main JavaScript functionality for Notion AI Integration

// Toast notification system
let toastContainer = null;

function initializeToastContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
}

function showToast(message, type = 'info', title = null, duration = 5000) {
    initializeToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-content">
            ${title ? `<div class="toast-title">${title}</div>` : ''}
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this)">×</button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => closeToast(toast.querySelector('.toast-close')), duration);
    }
    
    return toast;
}

function closeToast(button) {
    const toast = button.closest('.toast');
    toast.classList.remove('show');
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

function showError(message, title = 'Error') {
    console.error(message);
    showToast(message, 'error', title, 7000);
}

function showSuccess(message, title = 'Success') {
    console.log(message);
    showToast(message, 'success', title, 4000);
}

function showWarning(message, title = 'Warning') {
    console.warn(message);
    showToast(message, 'warning', title, 6000);
}

function showInfo(message, title = null) {
    console.info(message);
    showToast(message, 'info', title, 4000);
}

// API helper function
// Get CSRF token from meta tag or form
function getCSRFToken() {
    // Try to get from meta tag first
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }
    
    // Try to get from form
    const formToken = document.querySelector('input[name="csrf_token"]');
    if (formToken) {
        return formToken.value;
    }
    
    return null;
}

async function apiCall(url, options = {}) {
    try {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        // Add CSRF token for POST requests
        if (options.method === 'POST' || (!options.method && options.body)) {
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }
        }
        
        const response = await fetch(url, {
            headers,
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            // Handle specific error codes
            if (response.status === 429) {
                throw new Error('Rate limit exceeded. Please try again later.');
            } else if (response.status === 403) {
                throw new Error('Access denied. Please refresh the page and try again.');
            } else if (response.status === 413) {
                throw new Error('Request too large. Please reduce the content size.');
            }
            
            throw new Error(data.error || `API call failed (${response.status})`);
        }
        
        return data;
    } catch (error) {
        console.error('API call error:', error);
        
        // Log structured error information for debugging
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            console.error('Network error - check your internet connection');
        }
        
        throw error;
    }
}

// Dashboard functionality
async function loadDashboardContent() {
    try {
        // Load pages
        const pagesResponse = await apiCall('/api/pages');
        const pagesContainer = document.getElementById('pages-list');
        if (pagesContainer && pagesResponse.pages) {
            pagesContainer.innerHTML = pagesResponse.pages.map(page => `
                <div class="content-item">
                    <h4>${page.title}</h4>
                    <p>Last edited: ${new Date(page.last_edited_time).toLocaleDateString()}</p>
                </div>
            `).join('');
        }
        
        // Load databases
        const databasesResponse = await apiCall('/api/databases');
        const databasesContainer = document.getElementById('databases-list');
        if (databasesContainer && databasesResponse.databases) {
            databasesContainer.innerHTML = databasesResponse.databases.map(db => `
                <div class="content-item">
                    <h4>${db.title}</h4>
                    <p>Entries: ${db.entry_count || 0}</p>
                </div>
            `).join('');
        }
    } catch (error) {
        showError('Failed to load dashboard content: ' + error.message);
    }
}

// Enhanced form validation helpers
function validateRequired(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    const errors = [];
    
    requiredFields.forEach(field => {
        const value = field.value.trim();
        const fieldName = field.getAttribute('name') || field.getAttribute('id') || 'Field';
        
        if (!value) {
            field.classList.add('invalid');
            isValid = false;
            errors.push(`${fieldName} is required`);
        } else {
            field.classList.remove('invalid');
        }
    });
    
    return { isValid, errors };
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validateUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

function validateApiKey(key, provider) {
    const patterns = {
        openai: /^sk-[a-zA-Z0-9]{48,}$/,
        claude: /^sk-ant-[a-zA-Z0-9-]{95,}$/,
        notion: /^secret_[a-zA-Z0-9]{43}$/
    };
    
    return patterns[provider] ? patterns[provider].test(key) : key.length > 0;
}

function addRealTimeValidation(form) {
    const inputs = form.querySelectorAll('input, textarea, select');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            // Clear error state on input
            this.classList.remove('invalid');
            
            // Real-time validation for specific field types
            if (this.type === 'email') {
                const isValid = !this.value || validateEmail(this.value);
                this.classList.toggle('invalid', !isValid);
            } else if (this.type === 'url') {
                const isValid = !this.value || validateUrl(this.value);
                this.classList.toggle('invalid', !isValid);
            }
        });
    });
}

function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    
    // Required validation
    if (field.hasAttribute('required') && !value) {
        isValid = false;
    }
    
    // Type-specific validation
    if (value) {
        switch (field.type) {
            case 'email':
                isValid = validateEmail(value);
                break;
            case 'url':
                isValid = validateUrl(value);
                break;
        }
        
        // API key validation
        if (field.classList.contains('api-key')) {
            const provider = field.dataset.provider;
            isValid = validateApiKey(value, provider);
        }
    }
    
    field.classList.toggle('invalid', !isValid);
    return isValid;
}

// Enhanced loading state management
function setLoading(element, isLoading, loadingText = 'Loading...') {
    if (isLoading) {
        element.disabled = true;
        element.classList.add('loading');
        if (!element.dataset.originalText) {
            element.dataset.originalText = element.textContent;
        }
        element.textContent = loadingText;
    } else {
        element.disabled = false;
        element.classList.remove('loading');
        element.textContent = element.dataset.originalText || element.textContent;
    }
}

function showLoadingOverlay(message = 'Loading...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner-large"></div>
                <div class="loading-text">${message}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-text').textContent = message;
    }
    
    overlay.classList.add('active');
    return overlay;
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// Progress bar utilities
function createProgressBar(container, initialValue = 0) {
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.innerHTML = '<div class="progress-fill"></div>';
    
    if (container) {
        container.appendChild(progressBar);
    }
    
    return {
        element: progressBar,
        setProgress: (value) => {
            const fill = progressBar.querySelector('.progress-fill');
            fill.style.width = `${Math.max(0, Math.min(100, value))}%`;
        },
        setIndeterminate: (indeterminate = true) => {
            const fill = progressBar.querySelector('.progress-fill');
            fill.classList.toggle('indeterminate', indeterminate);
        },
        remove: () => {
            if (progressBar.parentNode) {
                progressBar.parentNode.removeChild(progressBar);
            }
        }
    };
}

// Intersection Observer for animations
function initializeAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);
    
    // Observe all fade-in elements
    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });
}

// Auto-refresh functionality
function setupAutoRefresh() {
    const refreshElements = document.querySelectorAll('[data-auto-refresh]');
    
    refreshElements.forEach(element => {
        const interval = parseInt(element.dataset.autoRefresh) * 1000;
        const refreshFunction = element.dataset.refreshFunction;
        
        if (interval > 0 && refreshFunction && window[refreshFunction]) {
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    window[refreshFunction]();
                }
            }, interval);
        }
    });
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit forms
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeForm = document.activeElement.closest('form');
            if (activeForm) {
                const submitButton = activeForm.querySelector('button[type="submit"], input[type="submit"]');
                if (submitButton && !submitButton.disabled) {
                    submitButton.click();
                }
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal[style*="flex"]');
            if (openModal) {
                const closeButton = openModal.querySelector('.modal-close');
                if (closeButton) {
                    closeButton.click();
                }
            }
        }
    });
}

// Enhanced AJAX functionality
function setupAjaxForms() {
    document.querySelectorAll('form[data-ajax="true"]').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const submitButton = this.querySelector('button[type="submit"]');
            const action = this.action || window.location.pathname;
            const method = this.method || 'POST';
            
            setLoading(submitButton, true);
            
            try {
                const response = await apiCall(action, {
                    method: method,
                    body: method === 'GET' ? null : JSON.stringify(Object.fromEntries(formData))
                });
                
                if (response.success) {
                    showSuccess(response.message || 'Operation completed successfully');
                    
                    // Handle redirect
                    if (response.redirect) {
                        setTimeout(() => {
                            window.location.href = response.redirect;
                        }, 1000);
                    }
                    
                    // Reset form if specified
                    if (this.dataset.resetOnSuccess === 'true') {
                        this.reset();
                    }
                    
                    // Trigger custom success event
                    this.dispatchEvent(new CustomEvent('ajaxSuccess', { detail: response }));
                } else {
                    throw new Error(response.error || 'Operation failed');
                }
            } catch (error) {
                showError(error.message);
                this.dispatchEvent(new CustomEvent('ajaxError', { detail: error }));
            } finally {
                setLoading(submitButton, false);
            }
        });
    });
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-save functionality
function setupAutoSave() {
    const autoSaveElements = document.querySelectorAll('[data-auto-save]');
    
    autoSaveElements.forEach(element => {
        const delay = parseInt(element.dataset.autoSave) || 30000; // Default 30 seconds
        const saveFunction = element.dataset.saveFunction || 'autoSave';
        
        const debouncedSave = debounce(() => {
            if (window[saveFunction]) {
                window[saveFunction](element);
            }
        }, delay);
        
        element.addEventListener('input', debouncedSave);
    });
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    // Store original button text for loading states
    document.querySelectorAll('button').forEach(btn => {
        if (!btn.dataset.originalText) {
            btn.dataset.originalText = btn.textContent;
        }
    });
    
    // Enhanced form validation
    document.querySelectorAll('form').forEach(form => {
        // Add real-time validation
        addRealTimeValidation(form);
        
        // Enhanced submit validation
        form.addEventListener('submit', function(e) {
            const validation = validateRequired(form);
            if (!validation.isValid) {
                e.preventDefault();
                showError('Please fix the following errors: ' + validation.errors.join(', '));
                
                // Focus first invalid field
                const firstInvalid = form.querySelector('.invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
    });
    
    // Initialize features
    initializeAnimations();
    setupAutoRefresh();
    setupKeyboardShortcuts();
    setupAjaxForms();
    setupAutoSave();
    
    // Add focus ring class to focusable elements
    document.querySelectorAll('input, textarea, select, button, a').forEach(el => {
        el.classList.add('focus-ring');
    });
    
    // Add hover effects to interactive elements
    document.querySelectorAll('.content-item, .stat-card, .template-card').forEach(el => {
        el.classList.add('hover-lift');
    });
    
    // Initialize tooltips (if needed)
    initializeTooltips();
});

// Tooltip functionality
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const text = e.target.dataset.tooltip;
    if (!text) return;
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    tooltip.style.position = 'absolute';
    tooltip.style.background = '#1f2937';
    tooltip.style.color = 'white';
    tooltip.style.padding = '0.5rem';
    tooltip.style.borderRadius = '0.375rem';
    tooltip.style.fontSize = '0.875rem';
    tooltip.style.zIndex = '10000';
    tooltip.style.pointerEvents = 'none';
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    e.target.tooltipElement = tooltip;
}

function hideTooltip(e) {
    if (e.target.tooltipElement) {
        document.body.removeChild(e.target.tooltipElement);
        delete e.target.tooltipElement;
    }
}

// Utility functions for common operations
function copyToClipboard(text) {
    return navigator.clipboard.writeText(text).then(() => {
        showSuccess('Copied to clipboard');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showSuccess('Copied to clipboard');
    });
}

function downloadFile(content, filename, contentType = 'text/plain') {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
}

// Performance monitoring
function measurePerformance(name, fn) {
    const start = performance.now();
    const result = fn();
    const end = performance.now();
    console.log(`${name} took ${end - start} milliseconds`);
    return result;
}

// Error boundary for JavaScript errors
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showError('An unexpected error occurred. Please refresh the page and try again.');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showError('An unexpected error occurred. Please refresh the page and try again.');
});