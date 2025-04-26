// Create this file at parent_ui/static/js/dashboard.js

// Function to check if user is authenticated
function isAuthenticated() {
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];
    return !!token;
}

// Function to get the access token
function getAccessToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('access_token='))
        ?.split('=')[1];
}

// Function to handle API requests
async function fetchWithAuth(url, options = {}) {
    const token = getAccessToken();
    if (!token) {
        window.location.href = '/login/';
        return;
    }

    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        if (response.status === 401) {
            // Token expired or invalid
            window.location.href = '/login/';
            return;
        }
        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Setup event polling only if authenticated
function setupEventPolling() {
    if (!isAuthenticated()) {
        return; // Don't setup polling if not authenticated
    }

    function pollEvents() {
        const token = getAccessToken();
        if (!token) return;

        fetchWithAuth(`/events/?token=${token}`)
            .then(response => {
                if (!response) return;
                if (response.ok) {
                    return response.text().then(text => {
                        console.log('Raw response:', text);  // 👈 This is what the server sent back
                        try {
                            return JSON.parse(text);
                        } catch (e) {
                            console.error('Failed to parse JSON:', e);
                            throw e;
                        }
                    });
                }
                throw new Error('Network response was not ok');
            })        
            .then(data => {
                if (data) {
                    // Handle the update data here
                    console.log('Received update:', data);
                    // Update your UI components as needed
                }
                // Schedule next poll
                setTimeout(pollEvents, 5000);
            })
            .catch(error => {
                console.error('Polling error:', error);
                // Retry after a delay
                setTimeout(pollEvents, 10000);
            });
    }

    // Start polling
    pollEvents();
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    if (isAuthenticated()) {
        setupEventPolling();
    }
});