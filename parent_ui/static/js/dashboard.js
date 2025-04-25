// parent_ui/static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    // Get token from cookies or localStorage
    function getToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('access_token='))
            ?.split('=')[1];
        return cookieValue || localStorage.getItem('access_token');
    }

    const token = getToken();
    
    if (!token) {
        console.error('No authentication token found');
        window.location.href = '/login/';
        return;
    }

    console.log('Token exists:', token ? '****' + token.slice(-4) : 'None');

    function fetchWithAuth(url, options = {}) {
        return fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken') || ''
            },
            credentials: 'include'
        }).then(response => {
            if (response.status === 401) {
                return handleUnauthorized().then(() => fetchWithAuth(url, options));
            }
            return response;
        });
    }

    function handleUnauthorized() {
        console.log('Attempting token refresh...');
        return fetch('/api/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                refresh: getCookie('refresh_token') || localStorage.getItem('refresh_token')
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.access) {
                console.log('Token refreshed successfully');
                document.cookie = `access_token=${data.access}; path=/; SameSite=Lax`;
                localStorage.setItem('access_token', data.access);
                token = data.access; // Update the token variable
                return true;
            }
            throw new Error('Token refresh failed');
        })
        .catch(error => {
            console.error('Refresh token error:', error);
            window.location.href = '/login/';
            return false;
        });
    }

    // Initialize charts
    document.querySelectorAll('.usage-chart').forEach(chart => {
        const deviceId = chart.dataset.deviceId;
        console.log(`Loading data for device: ${deviceId}`);
        
        fetchWithAuth(`/api/usage-data/${deviceId}/`)
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                console.log('Received data:', data);
                // Initialize chart with data
                renderChart(chart, data);
            })
            .catch(error => {
                console.error('Chart data error:', error);
                chart.innerHTML = `<div class="alert alert-danger">Error loading data</div>`;
            });
    });

    function renderChart(element, data) {
        new Chart(element, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#8AC24A', '#607D8B'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'right' },
                    title: {
                        display: true,
                        text: `Usage for ${data.device}`,
                        font: { size: 16 }
                    }
                }
            }
        });
    }
});

// parent_ui/static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    // Real-time updates using EventSource
    if (typeof(EventSource) !== "undefined") {
        const eventSource = new EventSource('/events/');
        
        eventSource.onmessage = function(e) {
            const data = JSON.parse(e.data);
            console.log("Update received:", data);
            
            // Here you could refresh specific parts of the page
            // For example, update charts or notification counts
        };
        
        eventSource.onerror = function(e) {
            console.error("EventSource failed:", e);
            eventSource.close();
        };
    } else {
        console.log("Your browser doesn't support server-sent events");
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});