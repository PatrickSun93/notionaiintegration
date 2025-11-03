// Settings functionality for configuration management

document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    const testButton = document.getElementById('test-connection');
    const testResults = document.getElementById('test-results');
    
    // Load current settings
    loadCurrentSettings();
    
    // Handle form submission
    settingsForm.addEventListener('submit', handleSettingsSave);
    
    // Handle test connection
    testButton.addEventListener('click', testConnections);
    
    // Handle provider selection change
    const providerSelect = document.getElementById('default-provider');
    providerSelect.addEventListener('change', updateProviderFields);
});

async function loadCurrentSettings() {
    try {
        const response = await apiCall('/api/config');
        const form = document.getElementById('settings-form');
        
        if (response.config) {
            // Populate form fields with current config
            Object.keys(response.config).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field && response.config[key]) {
                    field.value = response.config[key];
                }
            });
        }
    } catch (error) {
        console.error('Failed to load current settings:', error);
        // Don't show error to user as this might be first-time setup
    }
}

async function handleSettingsSave(e) {
    e.preventDefault();
    
    const saveButton = document.getElementById('save-settings');
    const formData = new FormData(e.target);
    
    const config = {};
    for (let [key, value] of formData.entries()) {
        if (value.trim()) {
            config[key] = value.trim();
        }
    }
    
    // Validate required fields
    if (!config.notion_api_key) {
        showError('Notion API Key is required');
        return;
    }
    
    if (!config.provider) {
        showError('Please select a default AI provider');
        return;
    }
    
    setLoading(saveButton, true);
    
    try {
        await apiCall('/api/save_config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        
        showSuccess('Settings saved successfully!');
        
    } catch (error) {
        showError('Failed to save settings: ' + error.message);
    } finally {
        setLoading(saveButton, false);
    }
}

async function testConnections() {
    const testButton = document.getElementById('test-connection');
    const testResults = document.getElementById('test-results');
    
    setLoading(testButton, true);
    testResults.style.display = 'block';
    testResults.innerHTML = '<p>Testing connections...</p>';
    
    try {
        const response = await apiCall('/api/test_config', {
            method: 'POST'
        });
        
        let resultsHtml = '<h4>Connection Test Results:</h4><ul>';
        
        if (response.results) {
            Object.keys(response.results).forEach(service => {
                const result = response.results[service];
                const status = result.success ? '✅' : '❌';
                const message = result.message || (result.success ? 'Connected' : 'Failed');
                resultsHtml += `<li>${status} ${service}: ${message}</li>`;
            });
        }
        
        resultsHtml += '</ul>';
        testResults.innerHTML = resultsHtml;
        
    } catch (error) {
        testResults.innerHTML = `<p style="color: red;">Test failed: ${error.message}</p>`;
    } finally {
        setLoading(testButton, false);
    }
}

function updateProviderFields() {
    const provider = document.getElementById('default-provider').value;
    const allProviderFields = document.querySelectorAll('[id$="-api-key"], #ollama-endpoint');
    
    // Reset all field styles
    allProviderFields.forEach(field => {
        field.parentElement.style.opacity = '0.6';
    });
    
    // Highlight the selected provider's field
    let activeField;
    switch (provider) {
        case 'openai':
            activeField = document.getElementById('openai-api-key');
            break;
        case 'claude':
            activeField = document.getElementById('claude-api-key');
            break;
        case 'deepseek':
            activeField = document.getElementById('deepseek-api-key');
            break;
        case 'ollama':
            activeField = document.getElementById('ollama-endpoint');
            break;
    }
    
    if (activeField) {
        activeField.parentElement.style.opacity = '1';
        activeField.focus();
    }
}