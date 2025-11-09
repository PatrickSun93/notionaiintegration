// Enhanced editor functionality for page creation and editing

let currentAiSuggestion = '';
let isEditing = false;
let currentPageId = null;

// Templates
const templates = {
    'blog-post': {
        title: 'New Blog Post',
        content: `# Blog Post Title

## Introduction
Brief introduction to the topic...

## Main Content
### Key Point 1
Detailed explanation...

### Key Point 2
More details...

## Conclusion
Summary and final thoughts...

---
*Published on ${new Date().toLocaleDateString()}*`
    },
    'meeting-notes': {
        title: 'Meeting Notes - [Date]',
        content: `# Meeting Notes

**Date:** ${new Date().toLocaleDateString()}
**Time:** 
**Attendees:** 
**Location:** 

## Agenda
1. 
2. 
3. 

## Discussion Points
### Topic 1


### Topic 2


## Action Items
- [ ] Task 1 - Assigned to: [Name] - Due: [Date]
- [ ] Task 2 - Assigned to: [Name] - Due: [Date]

## Next Meeting
**Date:** 
**Topics:** `
    },
    'project-plan': {
        title: 'Project Plan - [Project Name]',
        content: `# Project Plan

## Project Overview
**Project Name:** 
**Start Date:** ${new Date().toLocaleDateString()}
**End Date:** 
**Project Manager:** 

## Objectives
1. 
2. 
3. 

## Scope
### In Scope
- 
- 

### Out of Scope
- 
- 

## Timeline
### Phase 1: Planning
- **Duration:** 
- **Deliverables:** 

### Phase 2: Development
- **Duration:** 
- **Deliverables:** 

### Phase 3: Testing
- **Duration:** 
- **Deliverables:** 

## Resources
### Team Members
- 
- 

### Budget
- 

## Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
|      |        |             |            |`
    },
    'task-list': {
        title: 'Task List - [Project/Area]',
        content: `# Task List

## High Priority
- [ ] 
- [ ] 
- [ ] 

## Medium Priority
- [ ] 
- [ ] 
- [ ] 

## Low Priority
- [ ] 
- [ ] 

## Completed ✅
- [x] 
- [x] 

## Notes
- 
- 

---
*Last updated: ${new Date().toLocaleDateString()}*`
    },
    'research-notes': {
        title: 'Research Notes - [Topic]',
        content: `# Research Notes

**Topic:** 
**Date:** ${new Date().toLocaleDateString()}
**Researcher:** 

## Research Question
What are we trying to find out?

## Sources
1. [Source Title](URL) - Brief description
2. [Source Title](URL) - Brief description
3. [Source Title](URL) - Brief description

## Key Findings
### Finding 1
- **Source:** 
- **Details:** 
- **Relevance:** 

### Finding 2
- **Source:** 
- **Details:** 
- **Relevance:** 

## Analysis
What do these findings mean?

## Conclusions
Summary of insights and next steps

## References
- 
- `
    }
};

// Initialize editor
document.addEventListener('DOMContentLoaded', function() {
    const pageForm = document.getElementById('page-form');
    const databaseSelect = document.getElementById('database-select');
    const previewButton = document.getElementById('preview-button');
    const validateButton = document.getElementById('validate-button');
    const titleInput = document.getElementById('page-title');
    const contentTextarea = document.getElementById('page-content');
    const templateSelect = document.getElementById('page-template');
    
    // Load available databases
    loadDatabases();
    
    // Check URL parameters for editing existing page
    const urlParams = new URLSearchParams(window.location.search);
    const pageId = urlParams.get('page_id');
    const databaseId = urlParams.get('database_id');
    
    if (pageId) {
        loadPageForEditing(pageId);
    } else if (databaseId) {
        databaseSelect.value = databaseId;
    }
    
    // Event listeners
    pageForm.addEventListener('submit', handlePageSave);
    previewButton.addEventListener('click', showPreview);
    validateButton.addEventListener('click', validateContent);
    
    // Character counters
    titleInput.addEventListener('input', updateTitleCount);
    contentTextarea.addEventListener('input', updateContentCount);
    
    // Template selection
    templateSelect.addEventListener('change', function() {
        if (this.value && templates[this.value]) {
            if (titleInput.value || contentTextarea.value) {
                if (confirm('This will replace your current content. Continue?')) {
                    applyTemplate(this.value);
                }
            } else {
                applyTemplate(this.value);
            }
        }
    });
    
    // Enhanced auto-save functionality
    let autoSaveTimer;
    let hasUnsavedChanges = false;
    
    function scheduleAutoSave() {
        clearTimeout(autoSaveTimer);
        hasUnsavedChanges = true;
        updateEditorStatus('Unsaved changes');
        
        autoSaveTimer = setTimeout(() => {
            if (hasUnsavedChanges) {
                autoSave();
            }
        }, 30000); // Auto-save every 30 seconds
    }
    
    function markAsSaved() {
        hasUnsavedChanges = false;
        updateEditorStatus('All changes saved');
    }
    
    titleInput.addEventListener('input', scheduleAutoSave);
    contentTextarea.addEventListener('input', scheduleAutoSave);
    
    // Warn before leaving with unsaved changes
    window.addEventListener('beforeunload', function(e) {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return e.returnValue;
        }
    });
    
    // Real-time word count and reading time
    contentTextarea.addEventListener('input', function() {
        updateContentStats();
    });
    
    function updateContentStats() {
        const content = contentTextarea.value;
        const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
        const readingTime = Math.ceil(wordCount / 200); // Average reading speed
        
        const statsElement = document.getElementById('content-stats');
        if (statsElement) {
            statsElement.innerHTML = `
                <span>${wordCount} words</span>
                <span>•</span>
                <span>${readingTime} min read</span>
            `;
        }
    }
});

async function loadDatabases() {
    try {
        updateEditorStatus('Loading databases...');
        const response = await apiCall('/api/databases');
        const databaseSelect = document.getElementById('database-select');
        
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
                option.dataset.entryCount = db.entry_count || 0;
                databaseSelect.appendChild(option);
            });
            updateEditorStatus(`Loaded ${response.databases.length} databases`);
        } else {
            updateEditorStatus('No databases found');
        }
    } catch (error) {
        console.error('Failed to load databases:', error);
        updateEditorStatus('Failed to load databases');
        showError('Failed to load databases: ' + error.message);
    }
}

async function loadPageForEditing(pageId) {
    try {
        isEditing = true;
        currentPageId = pageId;
        updateEditorStatus('Loading page for editing...');
        
        const response = await apiCall(`/api/page/${pageId}`);
        if (response.success && response.page) {
            document.getElementById('page-title').value = response.page.title || '';
            document.getElementById('page-content').value = response.page.content || '';
            
            updateTitleCount();
            updateContentCount();
            updateEditorStatus('Editing existing page');
            
            // Update save button text
            const saveButton = document.getElementById('save-button');
            saveButton.innerHTML = '<span class="btn-icon">💾</span> Update Page';
        }
    } catch (error) {
        console.error('Failed to load page:', error);
        updateEditorStatus('Failed to load page');
        showError('Failed to load page: ' + error.message);
    }
}

async function handlePageSave(e) {
    e.preventDefault();
    
    const saveButton = document.getElementById('save-button');
    const formData = new FormData(e.target);
    
    const pageData = {
        database_id: formData.get('database_id'),
        title: formData.get('title'),
        content: formData.get('content')
    };
    
    // Validation
    if (!pageData.title.trim()) {
        showError('Please enter a page title');
        document.getElementById('page-title').focus();
        return;
    }
    
    if (!pageData.content.trim()) {
        showError('Please enter some content');
        document.getElementById('page-content').focus();
        return;
    }
    
    if (!isEditing && !pageData.database_id) {
        showError('Please select a target database');
        document.getElementById('database-select').focus();
        return;
    }
    
    setLoading(saveButton, true);
    updateEditorStatus(isEditing ? 'Updating page...' : 'Creating page...');
    
    try {
        let response;
        if (isEditing && currentPageId) {
            response = await apiCall(`/api/update_page/${currentPageId}`, {
                method: 'POST',
                body: JSON.stringify({
                    title: pageData.title,
                    content: pageData.content
                })
            });
        } else {
            response = await apiCall('/api/create_page', {
                method: 'POST',
                body: JSON.stringify(pageData)
            });
        }
        
        if (response.success) {
            showSuccess(isEditing ? 'Page updated successfully!' : 'Page created successfully in Notion!');
            updateEditorStatus(isEditing ? 'Page updated' : 'Page created');
            
            // Optionally redirect to the created/updated page
            if (response.page_url) {
                const openPage = confirm(`Page ${isEditing ? 'updated' : 'created'}! Would you like to open it in Notion?`);
                if (openPage) {
                    window.open(response.page_url, '_blank');
                }
            }
            
            // Reset form if creating new page
            if (!isEditing) {
                e.target.reset();
                updateTitleCount();
                updateContentCount();
                hidePreview();
                hideValidation();
            }
        } else {
            throw new Error(response.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        showError(`Failed to ${isEditing ? 'update' : 'create'} page: ` + error.message);
        updateEditorStatus('Error occurred');
    } finally {
        setLoading(saveButton, false);
    }
}

function showPreview() {
    const title = document.getElementById('page-title').value;
    const content = document.getElementById('page-content').value;
    const previewContainer = document.getElementById('preview-container');
    const previewContent = document.getElementById('preview-content');
    
    if (!title && !content) {
        showError('Please enter some content to preview');
        return;
    }
    
    // Convert markdown to HTML
    const formattedContent = formatMarkdown(content);
    
    previewContent.innerHTML = `
        <h1>${escapeHtml(title) || 'Untitled'}</h1>
        ${formattedContent}
    `;
    
    previewContainer.style.display = 'block';
    previewContainer.scrollIntoView({ behavior: 'smooth' });
}

function hidePreview() {
    document.getElementById('preview-container').style.display = 'none';
}

function validateContent() {
    const title = document.getElementById('page-title').value;
    const content = document.getElementById('page-content').value;
    const validationContainer = document.getElementById('validation-results');
    const validationContent = document.getElementById('validation-content');
    
    const issues = [];
    const suggestions = [];
    
    // Title validation
    if (!title.trim()) {
        issues.push('Title is required');
    } else if (title.length < 3) {
        issues.push('Title is too short (minimum 3 characters)');
    } else if (title.length > 200) {
        issues.push('Title is too long (maximum 200 characters)');
    }
    
    // Content validation
    if (!content.trim()) {
        issues.push('Content is required');
    } else if (content.length < 10) {
        issues.push('Content is too short (minimum 10 characters)');
    }
    
    // Content suggestions
    if (content && !content.includes('#')) {
        suggestions.push('Consider adding headings to structure your content');
    }
    
    if (content && content.split('\n\n').length < 2) {
        suggestions.push('Consider breaking content into paragraphs for better readability');
    }
    
    if (title && content && !content.toLowerCase().includes(title.toLowerCase().split(' ')[0])) {
        suggestions.push('Consider mentioning the title topic in your content');
    }
    
    // Display results
    let html = '';
    
    if (issues.length === 0) {
        html += '<div class="validation-success">✅ Content validation passed!</div>';
    } else {
        html += '<div class="validation-issues"><h4>Issues to fix:</h4><ul>';
        issues.forEach(issue => {
            html += `<li class="validation-error">❌ ${issue}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (suggestions.length > 0) {
        html += '<div class="validation-suggestions"><h4>Suggestions:</h4><ul>';
        suggestions.forEach(suggestion => {
            html += `<li class="validation-suggestion">💡 ${suggestion}</li>`;
        });
        html += '</ul></div>';
    }
    
    validationContent.innerHTML = html;
    validationContainer.style.display = 'block';
    validationContainer.scrollIntoView({ behavior: 'smooth' });
}

function hideValidation() {
    document.getElementById('validation-results').style.display = 'none';
}

// Formatting functions
function formatText(type) {
    const textarea = document.getElementById('page-content');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    
    let formattedText = '';
    switch (type) {
        case 'bold':
            formattedText = `**${selectedText}**`;
            break;
        case 'italic':
            formattedText = `*${selectedText}*`;
            break;
        case 'code':
            formattedText = `\`${selectedText}\``;
            break;
    }
    
    textarea.value = textarea.value.substring(0, start) + formattedText + textarea.value.substring(end);
    textarea.focus();
    textarea.setSelectionRange(start + formattedText.length, start + formattedText.length);
    updateContentCount();
}

function insertText(text) {
    const textarea = document.getElementById('page-content');
    const start = textarea.selectionStart;
    
    textarea.value = textarea.value.substring(0, start) + text + textarea.value.substring(start);
    textarea.focus();
    textarea.setSelectionRange(start + text.length, start + text.length);
    updateContentCount();
}

// Character counting
function updateTitleCount() {
    const title = document.getElementById('page-title').value;
    document.getElementById('title-count').textContent = title.length;
}

function updateContentCount() {
    const content = document.getElementById('page-content').value;
    document.getElementById('content-count').textContent = content.length;
}

// Status updates
function updateEditorStatus(status) {
    const statusText = document.querySelector('#editor-status .status-text');
    const statusIndicator = document.querySelector('#editor-status .status-indicator');
    
    if (statusText) {
        statusText.textContent = status;
    }
    
    if (statusIndicator) {
        statusIndicator.className = 'status-indicator';
        if (status.includes('Error') || status.includes('Failed')) {
            statusIndicator.classList.add('status-error');
        } else if (status.includes('Loading') || status.includes('Creating') || status.includes('Updating')) {
            statusIndicator.classList.add('status-loading');
        } else {
            statusIndicator.classList.add('status-ready');
        }
    }
}

// Template functions
function loadTemplate() {
    document.getElementById('template-modal').style.display = 'flex';
}

function closeTemplateModal() {
    document.getElementById('template-modal').style.display = 'none';
}

function applyTemplate(templateKey) {
    const template = templates[templateKey];
    if (template) {
        document.getElementById('page-title').value = template.title;
        document.getElementById('page-content').value = template.content;
        updateTitleCount();
        updateContentCount();
        updateEditorStatus(`Applied ${templateKey} template`);
    }
    closeTemplateModal();
}

// AI assistance functions
function aiAssist() {
    document.getElementById('ai-modal').style.display = 'flex';
}

function closeAiModal() {
    document.getElementById('ai-modal').style.display = 'none';
    document.getElementById('ai-result').style.display = 'none';
}

async function aiAction(action) {
    const content = document.getElementById('page-content').value;
    const title = document.getElementById('page-title').value;
    let prompt = '';
    
    switch (action) {
        case 'improve':
            prompt = 'Improve the writing quality and clarity of this content';
            break;
        case 'expand':
            prompt = 'Expand this content with more details and examples';
            break;
        case 'summarize':
            prompt = 'Create a concise summary of this content';
            break;
        case 'outline':
            prompt = 'Create an outline structure for this content';
            break;
        case 'custom':
            prompt = document.getElementById('ai-prompt').value;
            break;
    }
    
    if (!prompt) {
        showError('Please enter a custom prompt');
        return;
    }
    
    if (!content && action !== 'outline') {
        showError('Please enter some content first');
        return;
    }
    
    try {
        updateEditorStatus('AI is working...');
        const response = await apiCall('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                message: `${prompt}:\n\nTitle: ${title}\nContent: ${content}`,
                provider: 'openai' // Default to OpenAI for editor assistance
            })
        });
        
        if (response.success) {
            currentAiSuggestion = response.response;
            document.getElementById('ai-content').textContent = response.response;
            document.getElementById('ai-result').style.display = 'block';
            updateEditorStatus('AI suggestion ready');
        } else {
            throw new Error(response.error || 'AI request failed');
        }
    } catch (error) {
        showError('AI assistance failed: ' + error.message);
        updateEditorStatus('AI request failed');
    }
}

function applyAiSuggestion() {
    if (currentAiSuggestion) {
        document.getElementById('page-content').value = currentAiSuggestion;
        updateContentCount();
        closeAiModal();
        updateEditorStatus('AI suggestion applied');
    }
}

function aiSuggest() {
    aiAssist();
}

// Utility functions
function clearEditor() {
    if (confirm('Are you sure you want to clear all content?')) {
        document.getElementById('page-title').value = '';
        document.getElementById('page-content').value = '';
        updateTitleCount();
        updateContentCount();
        hidePreview();
        hideValidation();
        updateEditorStatus('Editor cleared');
    }
}

async function autoSave() {
    const title = document.getElementById('page-title').value;
    const content = document.getElementById('page-content').value;
    
    if (!title && !content) return;
    
    try {
        updateEditorStatus('Auto-saving...');
        
        // Save to localStorage as backup
        localStorage.setItem('notion-editor-autosave', JSON.stringify({
            title: title,
            content: content,
            timestamp: new Date().toISOString(),
            pageId: currentPageId
        }));
        
        // If editing existing page, save to server
        if (isEditing && currentPageId) {
            const response = await apiCall(`/api/autosave_page/${currentPageId}`, {
                method: 'POST',
                body: JSON.stringify({
                    title: title,
                    content: content
                })
            });
            
            if (response.success) {
                markAsSaved();
                showInfo('Auto-saved to server', null);
            } else {
                throw new Error(response.error || 'Auto-save failed');
            }
        } else {
            markAsSaved();
            updateEditorStatus('Auto-saved locally');
        }
        
    } catch (error) {
        console.error('Auto-save failed:', error);
        updateEditorStatus('Auto-save failed');
        
        // Still save locally as fallback
        try {
            localStorage.setItem('notion-editor-autosave', JSON.stringify({
                title: title,
                content: content,
                timestamp: new Date().toISOString(),
                pageId: currentPageId
            }));
            updateEditorStatus('Saved locally only');
        } catch (localError) {
            console.error('Local save also failed:', localError);
        }
    }
}

// Restore from auto-save
function restoreAutoSave() {
    try {
        const saved = localStorage.getItem('notion-editor-autosave');
        if (saved) {
            const data = JSON.parse(saved);
            const savedTime = new Date(data.timestamp);
            const timeDiff = Date.now() - savedTime.getTime();
            
            // Only restore if saved within last hour
            if (timeDiff < 3600000) {
                const restore = confirm(
                    `Found auto-saved content from ${savedTime.toLocaleString()}. ` +
                    'Would you like to restore it?'
                );
                
                if (restore) {
                    document.getElementById('page-title').value = data.title || '';
                    document.getElementById('page-content').value = data.content || '';
                    updateTitleCount();
                    updateContentCount();
                    updateContentStats();
                    updateEditorStatus('Restored from auto-save');
                    hasUnsavedChanges = true;
                }
            }
        }
    } catch (error) {
        console.error('Failed to restore auto-save:', error);
    }
}

// Enhanced validation with real-time feedback
function validateContentRealTime() {
    const title = document.getElementById('page-title').value;
    const content = document.getElementById('page-content').value;
    const validationContainer = document.getElementById('validation-feedback');
    
    if (!validationContainer) return;
    
    const issues = [];
    const suggestions = [];
    
    // Real-time validation
    if (title.length > 0 && title.length < 3) {
        issues.push('Title too short');
    }
    
    if (content.length > 0 && content.length < 10) {
        issues.push('Content too short');
    }
    
    if (title && content && content.split(' ').length < 50) {
        suggestions.push('Consider adding more detail');
    }
    
    // Update validation display
    let html = '';
    if (issues.length > 0) {
        html += `<div class="validation-issues-mini">⚠️ ${issues.join(', ')}</div>`;
    }
    if (suggestions.length > 0) {
        html += `<div class="validation-suggestions-mini">💡 ${suggestions.join(', ')}</div>`;
    }
    
    validationContainer.innerHTML = html;
}

function formatMarkdown(text) {
    // Simple markdown to HTML conversion
    let html = escapeHtml(text);
    
    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Bold and italic
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    
    // Lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // Blockquotes
    html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
    
    // Line breaks and paragraphs
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';
    
    // Clean up empty paragraphs
    html = html.replace(/<p><\/p>/g, '');
    
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}