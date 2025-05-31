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

// Enhanced sidebar toggle functionality with desktop and mobile support
function initializeSidebarToggle() {
    const sidebarToggleBtn = document.querySelector('#sidebarToggle'); // Desktop toggle
    const mobileToggler = document.querySelector('#mobileToggle'); // Mobile toggle
    const sidebar = document.querySelector('#sidebarMenu');
    let overlay = document.querySelector('.sidebar-overlay');
    
    // Create overlay for mobile if it doesn't exist
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);
    }
    
    // Initialize tooltips for collapsed sidebar
    initializeTooltips();
    
    // Desktop sidebar toggle functionality
    if (sidebarToggleBtn && sidebar) {
        sidebarToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Toggle collapsed state for desktop
            toggleDesktopSidebar();
        });
    }
    
    // Mobile sidebar toggle functionality
    if (mobileToggler && sidebar) {
        mobileToggler.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const isExpanded = mobileToggler.getAttribute('aria-expanded') === 'true';
            toggleMobileSidebar(!isExpanded);
        });
    }
    
    // Close sidebar when clicking overlay (mobile only)
    if (overlay) {
        overlay.addEventListener('click', function() {
            toggleMobileSidebar(false);
        });
    }
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            if (window.innerWidth < 768 && sidebar.classList.contains('show')) {
                toggleMobileSidebar(false);
            }
        }
    });
    
    // Close mobile sidebar when clicking sidebar links
    const sidebarLinks = sidebar.querySelectorAll('.nav-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 768 && sidebar.classList.contains('show')) {
                setTimeout(() => toggleMobileSidebar(false), 150);
            }
        });
    });
    
    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            if (window.innerWidth >= 768) {
                // Desktop view - reset mobile states
                sidebar.classList.remove('show');
                overlay.style.display = 'none';
                document.body.style.overflow = '';
                if (mobileToggler) {
                    mobileToggler.setAttribute('aria-expanded', 'false');
                    mobileToggler.classList.add('collapsed');
                }
            } else {
                // Mobile view - reset desktop states
                document.body.classList.remove('sidebar-collapsed');
            }
            
            // Reinitialize tooltips
            initializeTooltips();
        }, 250);
    });
    
    // Desktop sidebar toggle function
    function toggleDesktopSidebar() {
        const isCollapsed = document.body.classList.contains('sidebar-collapsed');
        
        if (isCollapsed) {
            // Expand sidebar
            document.body.classList.remove('sidebar-collapsed');
            sidebar.classList.remove('sidebar-collapsed');
            sidebarToggleBtn.setAttribute('aria-expanded', 'true');
            localStorage.setItem('sidebarCollapsed', 'false');
        } else {
            // Collapse sidebar
            document.body.classList.add('sidebar-collapsed');
            sidebar.classList.add('sidebar-collapsed');
            sidebarToggleBtn.setAttribute('aria-expanded', 'false');
            localStorage.setItem('sidebarCollapsed', 'true');
        }
        
        // Update tooltips after toggle
        setTimeout(() => initializeTooltips(), 300);
    }
    
    // Mobile sidebar toggle function
    function toggleMobileSidebar(show) {
        if (show) {
            // Open mobile sidebar
            sidebar.classList.add('show');
            overlay.style.display = 'block';
            mobileToggler.setAttribute('aria-expanded', 'true');
            mobileToggler.classList.remove('collapsed');
            document.body.style.overflow = 'hidden';
            
            // Add backdrop blur effect
            overlay.style.backdropFilter = 'blur(2px)';
            
            // Focus management for accessibility
            const firstFocusableElement = sidebar.querySelector('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusableElement) {
                setTimeout(() => firstFocusableElement.focus(), 100);
            }
        } else {
            // Close mobile sidebar
            sidebar.classList.remove('show');
            overlay.style.display = 'none';
            mobileToggler.setAttribute('aria-expanded', 'false');
            mobileToggler.classList.add('collapsed');
            document.body.style.overflow = '';
            
            // Return focus to toggle button
            if (mobileToggler) {
                mobileToggler.focus();
            }
        }
    }
    
    // Initialize tooltips for collapsed sidebar
    function initializeTooltips() {
        const isCollapsed = document.body.classList.contains('sidebar-collapsed');
        const tooltipElements = sidebar.querySelectorAll('[data-bs-toggle="tooltip"]');
        
        // Dispose existing tooltips
        tooltipElements.forEach(element => {
            const existingTooltip = bootstrap.Tooltip.getInstance(element);
            if (existingTooltip) {
                existingTooltip.dispose();
            }
        });
        
        // Initialize tooltips only when collapsed and on desktop
        if (isCollapsed && window.innerWidth >= 768) {
            tooltipElements.forEach(element => {
                new bootstrap.Tooltip(element, {
                    placement: 'right',
                    boundary: 'viewport'
                });
            });
        }
    }
    
    // Restore sidebar state from localStorage
    const savedState = localStorage.getItem('sidebarCollapsed');
    if (savedState === 'true' && window.innerWidth >= 768) {
        document.body.classList.add('sidebar-collapsed');
        sidebar.classList.add('sidebar-collapsed');
        if (sidebarToggleBtn) {
            sidebarToggleBtn.setAttribute('aria-expanded', 'false');
        }
        setTimeout(() => initializeTooltips(), 100);
    }
}

// Enhanced form validation and mobile-friendly features
function initializeFormEnhancements() {
    // Auto-hide alert messages after 5 seconds with better animation
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        // Add close button for manual dismissal
        if (!alert.querySelector('.btn-close')) {
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'btn-close';
            closeBtn.setAttribute('aria-label', 'Close');
            closeBtn.onclick = () => dismissAlert(alert);
            alert.appendChild(closeBtn);
        }
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => dismissAlert(alert), 5000);
    });
    
    // Enhanced form submission handling
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const submitBtn = form.querySelector('button[type="submit"]');
        
        // Add form validation
        form.addEventListener('submit', function(e) {
            const formType = form.querySelector('input[name="form_type"]')?.value;
            
            // Password change confirmation
            if (formType === 'change_password') {
                const newPassword1 = form.querySelector('input[name="new_password1"]')?.value;
                const newPassword2 = form.querySelector('input[name="new_password2"]')?.value;
                
                if (newPassword1 !== newPassword2) {
                    e.preventDefault();
                    showToast('Passwords do not match', 'error');
                    return;
                }
                
                if (newPassword1.length < 8) {
                    e.preventDefault();
                    showToast('Password must be at least 8 characters long', 'error');
                    return;
                }
                
                if (!confirm('Are you sure you want to change your password? You will need to use the new password for future logins.')) {
                    e.preventDefault();
                    return;
                }
            }
            
            // Disable submit button and show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('loading');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving...';
                
                // Re-enable button after 10 seconds (fallback)
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('loading');
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
        
        // Real-time form validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                // Clear validation errors on input
                clearFieldError(this);
            });
        });
    });
    
    // Enhanced password strength indicator
    initializePasswordStrength();
    
    // Mobile form improvements
    initializeMobileFormFeatures();
}

// Dismiss alert with animation
function dismissAlert(alert) {
    if (!alert || !alert.parentNode) return;
    
    alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 300);
}

// Enhanced password strength functionality
function initializePasswordStrength() {
    const newPasswordField = document.querySelector('input[name="new_password1"]');
    if (!newPasswordField) return;
    
    // Create enhanced password strength indicator
    const existingStrength = newPasswordField.parentNode.querySelector('.password-strength');
    if (existingStrength) {
        existingStrength.remove();
    }
    
    const strengthContainer = document.createElement('div');
    strengthContainer.className = 'password-strength mt-2';
    strengthContainer.innerHTML = `
        <div class="progress" style="height: 6px; border-radius: 3px;">
            <div class="progress-bar transition-all" role="progressbar" style="width: 0%; transition: all 0.3s ease;"></div>
        </div>
        <div class="d-flex justify-content-between mt-1">
            <small class="strength-text text-muted"></small>
            <small class="requirements-text text-muted"></small>
        </div>
    `;
    newPasswordField.parentNode.appendChild(strengthContainer);
    
    const progressBar = strengthContainer.querySelector('.progress-bar');
    const strengthText = strengthContainer.querySelector('.strength-text');
    const requirementsText = strengthContainer.querySelector('.requirements-text');
    
    newPasswordField.addEventListener('input', function() {
        const password = this.value;
        const analysis = analyzePassword(password);
        updatePasswordDisplay(progressBar, strengthText, requirementsText, analysis);
    });
}

// Advanced password analysis
function analyzePassword(password) {
    const criteria = {
        length: password.length >= 8,
        lowercase: /[a-z]/.test(password),
        uppercase: /[A-Z]/.test(password),
        numbers: /[0-9]/.test(password),
        special: /[^a-zA-Z0-9]/.test(password)
    };
    
    const score = Object.values(criteria).filter(Boolean).length;
    const metCriteria = Object.keys(criteria).filter(key => criteria[key]).length;
    
    return {
        score,
        criteria,
        metCriteria,
        totalCriteria: Object.keys(criteria).length
    };
}

// Update password strength display
function updatePasswordDisplay(progressBar, strengthText, requirementsText, analysis) {
    const { score, metCriteria, totalCriteria } = analysis;
    const colors = ['bg-danger', 'bg-warning', 'bg-info', 'bg-success', 'bg-success'];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const widths = [20, 40, 60, 80, 100];
    
    // Remove all color classes
    progressBar.className = 'progress-bar transition-all';
    
    if (score > 0) {
        progressBar.style.width = widths[score - 1] + '%';
        progressBar.classList.add(colors[score - 1]);
        strengthText.textContent = labels[score - 1];
        strengthText.className = `strength-text text-${colors[score - 1].replace('bg-', '')}`;
        requirementsText.textContent = `${metCriteria}/${totalCriteria} requirements met`;
    } else {
        progressBar.style.width = '0%';
        strengthText.textContent = '';
        requirementsText.textContent = '';
    }
}

// Mobile-specific form improvements
function initializeMobileFormFeatures() {
    // Auto-scroll to form errors on mobile
    const errorFields = document.querySelectorAll('.is-invalid, .text-danger');
    if (errorFields.length > 0 && window.innerWidth < 768) {
        errorFields[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // Improve input focus behavior on mobile
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        // Prevent zoom on iOS when focusing inputs
        if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
            input.addEventListener('focus', function() {
                this.style.fontSize = '16px';
            });
        }
        
        // Auto-advance focus for OTP-style inputs
        if (input.type === 'text' && input.maxLength === 1) {
            input.addEventListener('input', function() {
                if (this.value && this.nextElementSibling) {
                    this.nextElementSibling.focus();
                }
            });
        }
    });
    
    // Haptic feedback for mobile interactions (if supported)
    if (navigator.vibrate) {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', function() {
                if (window.innerWidth < 768) {
                    navigator.vibrate(10); // Subtle haptic feedback
                }
            });
        });
    }
}

// Field validation
function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    let message = '';
    
    // Required field validation
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        message = 'This field is required';
    }
    
    // Email validation
    if (field.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        isValid = false;
        message = 'Please enter a valid email address';
    }
    
    // Password validation
    if (field.type === 'password' && value && value.length < 8) {
        isValid = false;
        message = 'Password must be at least 8 characters long';
    }
    
    // Show/hide validation feedback
    if (!isValid) {
        showFieldError(field, message);
    } else {
        clearFieldError(field);
    }
    
    return isValid;
}

// Show field error
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    let errorElement = field.parentNode.querySelector('.invalid-feedback');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'invalid-feedback';
        field.parentNode.appendChild(errorElement);
    }
    errorElement.textContent = message;
}

// Clear field error
function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorElement = field.parentNode.querySelector('.invalid-feedback');
    if (errorElement) {
        errorElement.remove();
    }
}

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `
        <div class="toast-header bg-${type === 'error' ? 'danger' : type} text-white">
            <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;
    
    document.body.appendChild(toast);
    
    // Initialize Bootstrap toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after hiding
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

// Password strength calculation
function calculatePasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8) strength += 1;
    if (password.match(/[a-z]/)) strength += 1;
    if (password.match(/[A-Z]/)) strength += 1;
    if (password.match(/[0-9]/)) strength += 1;
    if (password.match(/[^a-zA-Z0-9]/)) strength += 1;
    return strength;
}

// Update password strength visual indicator
function updatePasswordStrength(strengthBar, strength) {
    const colors = ['#dc3545', '#fd7e14', '#ffc107', '#198754', '#198754'];
    const widths = [20, 40, 60, 80, 100];
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    
    if (strength > 0) {
        strengthBar.style.width = widths[strength - 1] + '%';
        strengthBar.style.backgroundColor = colors[strength - 1];
        strengthBar.textContent = labels[strength - 1];
        strengthBar.style.display = 'block';
    } else {
        strengthBar.style.display = 'none';
    }
}

// Initialize when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize responsive utilities
    initializeResponsiveUtils();
    
    // Initialize sidebar toggle
    initializeSidebarToggle();
    
    // Initialize form enhancements
    initializeFormEnhancements();
    
    // Initialize touch improvements for mobile
    initializeTouchImprovements();
    
    // Setup event polling if authenticated
    if (isAuthenticated()) {
        setupEventPolling();
    }
});

// Responsive utilities
function initializeResponsiveUtils() {
    // Detect device type
    const isMobile = window.innerWidth < 768;
    const isTablet = window.innerWidth >= 768 && window.innerWidth < 992;
    const isDesktop = window.innerWidth >= 992;
    
    // Set CSS custom properties for JavaScript access
    document.documentElement.style.setProperty('--is-mobile', isMobile ? '1' : '0');
    document.documentElement.style.setProperty('--is-tablet', isTablet ? '1' : '0');
    document.documentElement.style.setProperty('--is-desktop', isDesktop ? '1' : '0');
    
    // Handle orientation changes
    window.addEventListener('orientationchange', function() {
        setTimeout(() => {
            // Trigger a resize event after orientation change
            window.dispatchEvent(new Event('resize'));
        }, 100);
    });
    
    // Optimize images for different screen sizes
    optimizeImages();
    
    // Handle viewport height changes (mobile browsers)
    handleViewportHeight();
}

// Touch improvements for mobile devices
function initializeTouchImprovements() {
    if ('ontouchstart' in window) {
        // Add touch class to body
        document.body.classList.add('touch-device');
        
        // Improve touch targets
        const touchTargets = document.querySelectorAll('.btn, .nav-link, .card');
        touchTargets.forEach(target => {
            target.style.minHeight = Math.max(44, parseInt(getComputedStyle(target).height)) + 'px';
        });
        
        // Add touch feedback
        document.addEventListener('touchstart', function(e) {
            if (e.target.classList.contains('btn') || e.target.classList.contains('nav-link')) {
                e.target.style.transform = 'scale(0.98)';
                e.target.style.transition = 'transform 0.1s ease';
            }
        });
        
        document.addEventListener('touchend', function(e) {
            if (e.target.classList.contains('btn') || e.target.classList.contains('nav-link')) {
                setTimeout(() => {
                    e.target.style.transform = '';
                }, 100);
            }
        });
        
        // Prevent double-tap zoom on buttons
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(e) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                if (e.target.classList.contains('btn') || 
                    e.target.classList.contains('nav-link') ||
                    e.target.closest('.btn') ||
                    e.target.closest('.nav-link')) {
                    e.preventDefault();
                }
            }
            lastTouchEnd = now;
        }, false);
    }
}

// Optimize images for different screen densities
function optimizeImages() {
    const images = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    } else {
        // Fallback for browsers without IntersectionObserver
        images.forEach(img => {
            img.src = img.dataset.src;
            img.classList.remove('lazy');
        });
    }
}

// Handle viewport height changes (especially important for mobile browsers)
function handleViewportHeight() {
    function setVH() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }
    
    setVH();
    window.addEventListener('resize', setVH);
    window.addEventListener('orientationchange', () => {
        setTimeout(setVH, 100);
    });
}

// Utility function to check if element is in viewport
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// Smooth scroll to element with offset for fixed header
function scrollToElement(element, offset = 80) {
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

// Debounce function for performance optimization
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}