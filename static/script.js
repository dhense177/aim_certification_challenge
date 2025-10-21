// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
const queryInput = document.getElementById('queryInput');
const submitBtn = document.getElementById('submitBtn');
const resultsSection = document.getElementById('resultsSection');
const loadingSection = document.getElementById('loadingSection');
const resultsContent = document.getElementById('resultsContent');
const exampleBtns = document.querySelectorAll('.example-btn');
const statusIndicator = document.getElementById('statusIndicator');

// State Management
let isLoading = false;

// Event Listeners
submitBtn.addEventListener('click', handleSubmit);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
    }
});

// Example button click handlers
exampleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        queryInput.value = query;
        handleSubmit();
    });
});

// Main submit handler
async function handleSubmit() {
    const query = queryInput.value.trim();
    
    console.log('Submitting query:', query);
    
    if (!query) {
        showError('Please enter a query');
        return;
    }
    
    if (isLoading) return;
    
    setLoading(true);
    hideResults();
    
    try {
        console.log('Making request to:', `${API_BASE_URL}/query`);
        
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.error) {
            showError(data.error);
        } else if (data.answer) {
            showResults(data.answer);
        } else {
            showError('No answer received from server');
        }
        
    } catch (error) {
        console.error('Detailed error:', error);
        showError(`Failed to process query: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

// UI Helper Functions
function setLoading(loading) {
    isLoading = loading;
    submitBtn.disabled = loading;
    
    if (loading) {
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        loadingSection.style.display = 'block';
    } else {
        submitBtn.innerHTML = '<i class="fas fa-search"></i> Analyze';
        loadingSection.style.display = 'none';
    }
}

function showResults(answer) {
    resultsContent.textContent = answer;
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

function showError(message) {
    resultsContent.innerHTML = `
        <div style="color: #e74c3c; background: #fdf2f2; padding: 1rem; border-radius: 8px; border-left: 4px solid #e74c3c;">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Error:</strong> ${message}
        </div>
    `;
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

function hideResults() {
    resultsSection.style.display = 'none';
}

// Format results based on content type
function formatResults(answer) {
    // Check if it's a solar potential analysis
    if (answer.includes('Solar Resource Data') || answer.includes('Extracted Address')) {
        return formatSolarAnalysis(answer);
    }
    
    // Check if it's a zoning/regulation query
    if (answer.includes('RAG output') || answer.includes('zoning') || answer.includes('regulation')) {
        return formatZoningInfo(answer);
    }
    
    // Default formatting
    return answer;
}

function formatSolarAnalysis(answer) {
    const parts = answer.split('\n\n');
    let formatted = '';
    
    parts.forEach(part => {
        if (part.includes('Extracted Address:')) {
            formatted += `<div class="result-section">
                <h3><i class="fas fa-map-marker-alt"></i> Address</h3>
                <p>${part.replace('Extracted Address: ', '')}</p>
            </div>`;
        } else if (part.includes('Latitude:') && part.includes('Longitude:')) {
            formatted += `<div class="result-section">
                <h3><i class="fas fa-globe"></i> Coordinates</h3>
                <p>${part}</p>
            </div>`;
        } else if (part.includes('Solar Resource Data:')) {
            formatted += `<div class="result-section">
                <h3><i class="fas fa-solar-panel"></i> Solar Resource Data</h3>
                <p>${part.replace('Solar Resource Data:', '')}</p>
            </div>`;
        } else {
            formatted += `<p>${part}</p>`;
        }
    });
    
    return formatted;
}

function formatZoningInfo(answer) {
    const cleanAnswer = answer.replace('RAG output: ', '');
    
    return `<div class="result-section">
        <h3><i class="fas fa-building"></i> Zoning Information</h3>
        <p>${cleanAnswer}</p>
    </div>`;
}

// Add CSS for result formatting
const style = document.createElement('style');
style.textContent = `
    .result-section {
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    
    .result-section h3 {
        color: #667eea;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .result-section h3 i {
        font-size: 1.1rem;
    }
    
    .result-section p {
        margin: 0;
        line-height: 1.6;
    }
`;
document.head.appendChild(style);

// Status indicator functions
function updateStatus(status, message) {
    statusIndicator.className = `status-indicator ${status}`;
    statusIndicator.querySelector('span').textContent = message;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Solar Certification Assistant Frontend Loaded');
    
    // Check if API is available
    updateStatus('connecting', 'Connecting...');
    
    fetch(`${API_BASE_URL}/docs`)
        .then(response => {
            if (response.ok) {
                console.log('API is available');
                updateStatus('connected', 'Connected');
            } else {
                console.warn('API might not be running');
                updateStatus('error', 'API Error');
            }
        })
        .catch(error => {
            console.warn('Cannot connect to API:', error.message);
            updateStatus('error', 'Connection Failed');
        });
});
