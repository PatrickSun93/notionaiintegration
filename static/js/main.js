// Main JavaScript functionality for Notion AI Integration

// Utility functions
function showError(message) {
    console.error(message);
    // You can enhance this to show toast notifications
    alert('Error: ' + message);
}

function showSuccess(message) {
    console.log(message);
    // You can enhance this to show toast notifications
    alert('Success: ' + message);
}

// API helper function
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'API call failed');
        }
        
        return data;
    } catch (error) {
        console.error('API call error:', error);
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

// Form validation helpers
function validateRequired(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

// Loading state management
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.textContent = 'Loading...';
    } else {
        element.disabled = false;
        element.textContent = element.dataset.originalText || element.textContent;
    }
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    // Store original button text for loading states
    document.querySelectorAll('button').forEach(btn => {
        btn.dataset.originalText = btn.textContent;
    });
    
    // Add form validation to all forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateRequired(form)) {
                e.preventDefault();
                showError('Please fill in all required fields');
            }
        });
    });
});