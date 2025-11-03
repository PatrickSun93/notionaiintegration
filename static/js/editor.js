// Editor functionality for page creation and editing

document.addEventListener('DOMContentLoaded', function() {
    const pageForm = document.getElementById('page-form');
    const databaseSelect = document.getElementById('database-select');
    const previewButton = document.getElementById('preview-button');
    const previewContainer = document.getElementById('preview-container');
    const previewContent = document.getElementById('preview-content');
    
    // Load available databases
    loadDatabases();
    
    // Handle form submission
    pageForm.addEventListener('submit', handlePageSave);
    
    // Handle preview
    previewButton.addEventListener('click', showPreview);
});

async function loadDatabases() {
    try {
        const response = await apiCall('/api/databases');
        const databaseSelect = document.getElementById('database-select');
        
        if (response.databases) {
            response.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db.id;
                option.textContent = db.title;
                databaseSelect.appendChild(option);
            });
        }
    } catch (error) {
        showError('Failed to load databases: ' + error.message);
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
    
    if (!pageData.database_id || !pageData.title || !pageData.content) {
        showError('Please fill in all required fields');
        return;
    }
    
    setLoading(saveButton, true);
    
    try {
        const response = await apiCall('/api/create_page', {
            method: 'POST',
            body: JSON.stringify(pageData)
        });
        
        showSuccess('Page created successfully in Notion!');
        
        // Optionally redirect to the created page or reset form
        if (response.page_url) {
            const openPage = confirm('Page created! Would you like to open it in Notion?');
            if (openPage) {
                window.open(response.page_url, '_blank');
            }
        }
        
        // Reset form
        e.target.reset();
        hidePreview();
        
    } catch (error) {
        showError('Failed to create page: ' + error.message);
    } finally {
        setLoading(saveButton, false);
    }
}

function showPreview() {
    const title = document.getElementById('page-title').value;
    const content = document.getElementById('page-content').value;
    const previewContainer = document.getElementById('preview-container');
    const previewContent = document.getElementById('preview-content');
    
    if (!title || !content) {
        showError('Please enter both title and content to preview');
        return;
    }
    
    // Simple preview - convert line breaks to paragraphs
    const formattedContent = content
        .split('\n\n')
        .map(paragraph => `<p>${paragraph.replace(/\n/g, '<br>')}</p>`)
        .join('');
    
    previewContent.innerHTML = `
        <h1>${title}</h1>
        ${formattedContent}
    `;
    
    previewContainer.style.display = 'block';
    previewContainer.scrollIntoView({ behavior: 'smooth' });
}

function hidePreview() {
    const previewContainer = document.getElementById('preview-container');
    previewContainer.style.display = 'none';
}