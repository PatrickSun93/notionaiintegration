// Enhanced settings functionality for configuration management

let currentConfig = {};

document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    const testAllButton = document.getElementById('test-all');
    const validateButton = document.getElementById('validate-config');
    
    // Load current settings
    loadCurrentSettings();
    
    // Load database options
    loadDatabaseOptions();
    
    // Handle form submission
    settingsForm.addEventListener('submit', handleSettingsSave);
    
    // Handle test all connections
    testAllButton.addEventListener('click', testAllConnections);
    
    // Handle validation
    validateButton.addEventListener('click', validateConfiguration);
    
    // Handle provider selection change
    const providerSelect = document.getElementById('default-provider');
    providerSelect.addEventListener('change', updateProviderHighlight);
    
    // Add input validation listeners
    addInputValidationListeners();
});

async function loadCurrentSettings() {
    try {
        updateSettingsStatus('Loading configuration...');
        const response = await apiCall('/api/config');
        const form = document.getElementById('settings-form');
        
        if (response.success && response.config) {
            currentConfig = response.config;
            
            // Populate form fields with current config
            Object.keys(response.config).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    if (field.type === 'checkbox') {
                        field.checked = response.config[key] === true || response.config[key] === 'true';
                    } else if (response.config[key]) {
                        field.value = response.config[key];
                    }
                }
            });
            
            // Update provider highlighting
            updateProviderHighlight();
            
            // Update connection status indicators
            updateConnectionStatuses();
            
            updateSettingsStatus('Configuration loaded');
        } else {
            updateSettingsStatus('No configuration found - first time setup');
        }
    } catch (error) {
        console.error('Failed to load current settings:', error);
        updateSettingsStatus('Failed to load configuration');
        // Don't show error to user as this might be first-time setup
    }
}

async function loadDatabaseOptions() {
    try {
        const response = await apiCall('/api/databases');
        const databaseSelect = document.getElementById('blog-database-id');
        
        // Clear existing options except the first one
        while (databaseSelect.children.length > 1) {
            databaseSelect.removeChild(databaseSelect.lastChild);
        }
        
        if (response.success && response.databases) {
            response.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db.id;
                option.textContent = db.title || 'Untitled Database';
                option.dataset.description = db.description || '';
                databaseSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load databases:', error);
        // Don't show error as Notion might not be configured yet
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
    
    // Handle checkboxes
    const checkboxes = e.target.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        config[checkbox.name] = checkbox.checked;
    });
    
    // Validate configuration
    const validation = validateConfigData(config);
    if (!validation.valid) {
        showError('Configuration validation failed: ' + validation.errors.join(', '));
        
        // Highlight invalid fields
        validation.errors.forEach(error => {
            const fieldName = error.split(' ')[0].toLowerCase().replace(' ', '_');
            const field = document.querySelector(`[name="${fieldName}"], [name="${fieldName.replace('_', '-')}"]`);
            if (field) {
                field.classList.add('invalid');
                field.focus();
            }
        });
        
        return;
    }
    
    setLoading(saveButton, true, 'Saving...');
    updateSettingsStatus('Saving configuration...');
    
    // Show progress bar
    const progressContainer = document.createElement('div');
    progressContainer.style.marginTop = '1rem';
    const progress = createProgressBar(progressContainer);
    saveButton.parentNode.appendChild(progressContainer);
    
    try {
        // Simulate progress steps
        progress.setProgress(25);
        await new Promise(resolve => setTimeout(resolve, 200));
        
        const response = await apiCall('/api/save_config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        
        progress.setProgress(75);
        await new Promise(resolve => setTimeout(resolve, 200));
        
        if (response.success) {
            progress.setProgress(100);
            currentConfig = config;
            showSuccess('Settings saved successfully!');
            updateSettingsStatus('Configuration saved');
            
            // Update connection status indicators
            updateConnectionStatuses();
            
            // Auto-test connections after save
            if (config.auto_test_on_save !== false) {
                setTimeout(testAllConnections, 1000);
            }
        } else {
            throw new Error(response.error || 'Failed to save configuration');
        }
        
    } catch (error) {
        showError('Failed to save settings: ' + error.message);
        updateSettingsStatus('Save failed');
        
        // Log detailed error for debugging
        console.error('Settings save error:', error);
    } finally {
        setLoading(saveButton, false);
        progress.remove();
    }
}

async function testAllConnections() {
    const testButton = document.getElementById('test-all');
    const testResults = document.getElementById('test-results');
    const testContent = document.getElementById('test-content');
    
    setLoading(testButton, true);
    updateSettingsStatus('Testing all connections...');
    
    testResults.style.display = 'block';
    testContent.innerHTML = '<div class="loading-spinner"></div><p>Testing connections...</p>';
    
    try {
        const response = await apiCall('/api/test_config', {
            method: 'POST'
        });
        
        if (response.success && response.results) {
            displayTestResults(response.results);
            updateConnectionStatuses(response.results);
            updateSettingsStatus('Connection tests completed');
        } else {
            throw new Error(response.error || 'Test failed');
        }
        
    } catch (error) {
        testContent.innerHTML = `<div class="error-content">❌ Test failed: ${error.message}</div>`;
        updateSettingsStatus('Connection tests failed');
    } finally {
        setLoading(testButton, false);
    }
}

async function testNotionConnection() {
    const notionKey = document.getElementById('notion-api-key').value;
    if (!notionKey) {
        showError('Please enter a Notion API key first');
        return;
    }
    
    updateConnectionStatus('notion', 'testing');
    
    try {
        const response = await apiCall('/api/test_notion', {
            method: 'POST',
            body: JSON.stringify({ api_key: notionKey })
        });
        
        if (response.success) {
            updateConnectionStatus('notion', 'connected');
            showSuccess('Notion connection successful!');
        } else {
            updateConnectionStatus('notion', 'error');
            showError('Notion connection failed: ' + (response.error || 'Unknown error'));
        }
    } catch (error) {
        updateConnectionStatus('notion', 'error');
        showError('Notion connection failed: ' + error.message);
    }
}

async function testProviderConnection(provider) {
    const keyField = document.getElementById(`${provider}-${provider === 'ollama' ? 'endpoint' : 'api-key'}`);
    const key = keyField.value;
    
    if (!key) {
        showError(`Please enter a ${provider} ${provider === 'ollama' ? 'endpoint' : 'API key'} first`);
        return;
    }
    
    updateConnectionStatus(`${provider}-provider`, 'testing');
    
    try {
        const response = await apiCall(`/api/test_${provider}`, {
            method: 'POST',
            body: JSON.stringify({ 
                [provider === 'ollama' ? 'endpoint' : 'api_key']: key 
            })
        });
        
        if (response.success) {
            updateConnectionStatus(`${provider}-provider`, 'connected');
            showSuccess(`${provider.charAt(0).toUpperCase() + provider.slice(1)} connection successful!`);
        } else {
            updateConnectionStatus(`${provider}-provider`, 'error');
            showError(`${provider} connection failed: ` + (response.error || 'Unknown error'));
        }
    } catch (error) {
        updateConnectionStatus(`${provider}-provider`, 'error');
        showError(`${provider} connection failed: ` + error.message);
    }
}

function validateConfiguration() {
    const form = document.getElementById('settings-form');
    const formData = new FormData(form);
    const config = {};
    
    for (let [key, value] of formData.entries()) {
        if (value.trim()) {
            config[key] = value.trim();
        }
    }
    
    const validation = validateConfigData(config);
    displayValidationResults(validation);
}

function validateConfigData(config) {
    const errors = [];
    const warnings = [];
    const suggestions = [];
    
    // Required field validation
    if (!config.notion_api_key) {
        errors.push('Notion API Key is required');
    } else if (!config.notion_api_key.startsWith('secret_')) {
        warnings.push('Notion API Key should start with "secret_"');
    }
    
    if (!config.provider) {
        errors.push('Default AI provider must be selected');
    } else {
        // Provider-specific validation
        switch (config.provider) {
            case 'openai':
                if (!config.openai_api_key) {
                    errors.push('OpenAI API Key is required for selected provider');
                } else if (!config.openai_api_key.startsWith('sk-')) {
                    warnings.push('OpenAI API Key should start with "sk-"');
                }
                break;
            case 'claude':
                if (!config.claude_api_key) {
                    errors.push('Claude API Key is required for selected provider');
                } else if (!config.claude_api_key.startsWith('sk-ant-')) {
                    warnings.push('Claude API Key should start with "sk-ant-"');
                }
                break;
            case 'deepseek':
                if (!config.deepseek_api_key) {
                    errors.push('Deepseek API Key is required for selected provider');
                }
                break;
            case 'ollama':
                if (!config.ollama_endpoint) {
                    errors.push('Ollama endpoint is required for selected provider');
                } else {
                    try {
                        new URL(config.ollama_endpoint);
                    } catch {
                        errors.push('Ollama endpoint must be a valid URL');
                    }
                }
                break;
        }
    }
    
    // Suggestions
    if (!config.blog_database_id) {
        suggestions.push('Consider setting a default blog database for easier content creation');
    }
    
    if (config.ai_timeout && (config.ai_timeout < 10 || config.ai_timeout > 120)) {
        warnings.push('AI timeout should be between 10 and 120 seconds');
    }
    
    return {
        valid: errors.length === 0,
        errors,
        warnings,
        suggestions
    };
}

function displayTestResults(results) {
    const testContent = document.getElementById('test-content');
    let html = '';
    
    Object.keys(results).forEach(service => {
        const result = results[service];
        const status = result.success ? '✅' : '❌';
        const statusClass = result.success ? 'test-success' : 'test-error';
        
        html += `
            <div class="test-result ${statusClass}">
                <div class="test-service">
                    ${status} <strong>${service}</strong>
                </div>
                <div class="test-message">${result.message || (result.success ? 'Connected successfully' : 'Connection failed')}</div>
                ${result.details ? `<div class="test-details">${result.details}</div>` : ''}
            </div>
        `;
    });
    
    testContent.innerHTML = html;
}

function displayValidationResults(validation) {
    const validationResults = document.getElementById('validation-results');
    const validationContent = document.getElementById('validation-content');
    
    let html = '';
    
    if (validation.valid) {
        html += '<div class="validation-success">✅ Configuration is valid and ready to use!</div>';
    }
    
    if (validation.errors.length > 0) {
        html += '<div class="validation-errors"><h4>Errors (must fix):</h4><ul>';
        validation.errors.forEach(error => {
            html += `<li class="validation-error">❌ ${error}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (validation.warnings.length > 0) {
        html += '<div class="validation-warnings"><h4>Warnings:</h4><ul>';
        validation.warnings.forEach(warning => {
            html += `<li class="validation-warning">⚠️ ${warning}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (validation.suggestions.length > 0) {
        html += '<div class="validation-suggestions"><h4>Suggestions:</h4><ul>';
        validation.suggestions.forEach(suggestion => {
            html += `<li class="validation-suggestion">💡 ${suggestion}</li>`;
        });
        html += '</ul></div>';
    }
    
    validationContent.innerHTML = html;
    validationResults.style.display = 'block';
    validationResults.scrollIntoView({ behavior: 'smooth' });
}

function updateProviderHighlight() {
    const provider = document.getElementById('default-provider').value;
    const allConfigs = document.querySelectorAll('.provider-config');
    
    // Reset all provider configs
    allConfigs.forEach(config => {
        config.classList.remove('active');
    });
    
    // Highlight the selected provider
    if (provider) {
        const activeConfig = document.getElementById(`${provider}-config`);
        if (activeConfig) {
            activeConfig.classList.add('active');
        }
    }
}

function updateConnectionStatuses(testResults = null) {
    // Update based on current config or test results
    if (currentConfig.notion_api_key) {
        updateConnectionStatus('notion', testResults?.notion?.success ? 'connected' : 'configured');
    }
    
    if (currentConfig.provider) {
        const providerKey = `${currentConfig.provider}_${currentConfig.provider === 'ollama' ? 'endpoint' : 'api_key'}`;
        if (currentConfig[providerKey]) {
            const status = testResults?.[currentConfig.provider]?.success ? 'connected' : 'configured';
            updateConnectionStatus(`${currentConfig.provider}-provider`, status);
            updateConnectionStatus('ai', status);
        }
    }
}

function updateConnectionStatus(elementId, status) {
    const indicator = document.querySelector(`#${elementId}-status .connection-indicator`);
    if (indicator) {
        indicator.dataset.status = status;
    }
}

function updateSettingsStatus(status) {
    const statusText = document.querySelector('#settings-status .status-text');
    const statusIndicator = document.querySelector('#settings-status .status-indicator');
    
    if (statusText) {
        statusText.textContent = status;
    }
    
    if (statusIndicator) {
        statusIndicator.className = 'status-indicator';
        if (status.includes('Error') || status.includes('Failed')) {
            statusIndicator.classList.add('status-error');
        } else if (status.includes('Loading') || status.includes('Testing') || status.includes('Saving')) {
            statusIndicator.classList.add('status-loading');
        } else {
            statusIndicator.classList.add('status-ready');
        }
    }
}

// Utility functions
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    const button = field.nextElementSibling;
    
    if (field.type === 'password') {
        field.type = 'text';
        button.textContent = '🙈';
    } else {
        field.type = 'password';
        button.textContent = '👁️';
    }
}

function addInputValidationListeners() {
    // Real-time validation for API keys
    const apiKeyFields = document.querySelectorAll('input[type="password"]');
    apiKeyFields.forEach(field => {
        // Debounced validation to avoid excessive API calls
        const debouncedValidation = debounce(() => {
            validateApiKeyFormat(field);
        }, 500);
        
        field.addEventListener('input', debouncedValidation);
        field.addEventListener('blur', () => validateApiKeyFormat(field));
        
        // Show/hide password functionality
        const toggleButton = field.nextElementSibling;
        if (toggleButton && toggleButton.classList.contains('input-action-btn')) {
            toggleButton.addEventListener('click', () => {
                togglePasswordVisibility(field.id);
            });
        }
    });
    
    // URL validation for Ollama endpoint
    const ollamaEndpoint = document.getElementById('ollama-endpoint');
    if (ollamaEndpoint) {
        const debouncedUrlValidation = debounce(() => {
            validateUrlFormat(ollamaEndpoint);
        }, 300);
        
        ollamaEndpoint.addEventListener('input', debouncedUrlValidation);
        ollamaEndpoint.addEventListener('blur', () => validateUrlFormat(ollamaEndpoint));
    }
    
    // Provider selection validation
    const providerSelect = document.getElementById('default-provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', function() {
            validateProviderConfiguration(this.value);
        });
    }
    
    // Auto-save functionality for non-sensitive fields
    const autoSaveFields = document.querySelectorAll('input[data-auto-save="true"]');
    autoSaveFields.forEach(field => {
        const debouncedSave = debounce(() => {
            autoSaveField(field);
        }, 2000);
        
        field.addEventListener('input', debouncedSave);
    });
}

async function validateProviderConfiguration(provider) {
    const providerConfigs = document.querySelectorAll('.provider-config');
    providerConfigs.forEach(config => config.classList.remove('active'));
    
    if (provider) {
        const activeConfig = document.getElementById(`${provider}-config`);
        if (activeConfig) {
            activeConfig.classList.add('active');
            
            // Check if required fields are filled
            const requiredField = activeConfig.querySelector('input[required]');
            if (requiredField && !requiredField.value) {
                showWarning(`Please configure ${provider.toUpperCase()} settings`);
                requiredField.focus();
            }
        }
    }
}

async function autoSaveField(field) {
    try {
        const config = { [field.name]: field.value };
        
        const response = await apiCall('/api/save_partial_config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
        
        if (response.success) {
            // Show subtle success indicator
            field.style.borderColor = '#10b981';
            setTimeout(() => {
                field.style.borderColor = '';
            }, 1000);
        }
    } catch (error) {
        console.error('Auto-save failed:', error);
        // Don't show error to user for auto-save failures
    }
}

function validateApiKeyFormat(field) {
    const value = field.value;
    let isValid = true;
    
    if (field.id === 'notion-api-key' && value && !value.startsWith('secret_')) {
        isValid = false;
    } else if (field.id === 'openai-api-key' && value && !value.startsWith('sk-')) {
        isValid = false;
    } else if (field.id === 'claude-api-key' && value && !value.startsWith('sk-ant-')) {
        isValid = false;
    }
    
    field.classList.toggle('invalid', !isValid);
}

function validateUrlFormat(field) {
    const value = field.value;
    let isValid = true;
    
    if (value) {
        try {
            new URL(value);
        } catch {
            isValid = false;
        }
    }
    
    field.classList.toggle('invalid', !isValid);
}

// Settings management functions
function exportSettings() {
    if (Object.keys(currentConfig).length === 0) {
        showError('No configuration to export');
        return;
    }
    
    // Remove sensitive data for export
    const exportConfig = { ...currentConfig };
    delete exportConfig.notion_api_key;
    delete exportConfig.openai_api_key;
    delete exportConfig.claude_api_key;
    delete exportConfig.deepseek_api_key;
    
    const blob = new Blob([JSON.stringify(exportConfig, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notion-ai-settings-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function importSettings() {
    document.getElementById('import-modal').style.display = 'flex';
}

function closeImportModal() {
    document.getElementById('import-modal').style.display = 'none';
}

function processImport() {
    const fileInput = document.getElementById('settings-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a settings file');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const importedConfig = JSON.parse(e.target.result);
            
            // Apply imported settings to form
            const form = document.getElementById('settings-form');
            Object.keys(importedConfig).forEach(key => {
                const field = form.querySelector(`[name="${key}"]`);
                if (field) {
                    if (field.type === 'checkbox') {
                        field.checked = importedConfig[key] === true || importedConfig[key] === 'true';
                    } else {
                        field.value = importedConfig[key];
                    }
                }
            });
            
            updateProviderHighlight();
            closeImportModal();
            showSuccess('Settings imported successfully! Remember to save and add your API keys.');
            
        } catch (error) {
            showError('Invalid settings file: ' + error.message);
        }
    };
    
    reader.readAsText(file);
}

function resetSettings() {
    if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        const form = document.getElementById('settings-form');
        form.reset();
        
        // Set default values
        document.getElementById('ollama-endpoint').value = 'http://localhost:11434';
        document.getElementById('ai-timeout').value = '30';
        document.getElementById('chat-history').checked = true;
        
        updateProviderHighlight();
        updateSettingsStatus('Settings reset to defaults');
        showSuccess('Settings reset to defaults. Remember to save your changes.');
    }
}

// Hide result panels
function hideTestResults() {
    document.getElementById('test-results').style.display = 'none';
}

function hideValidationResults() {
    document.getElementById('validation-results').style.display = 'none';
}