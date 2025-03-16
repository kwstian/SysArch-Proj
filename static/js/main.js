// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize modals
    initModals();
    
    // Handle form validation
    initFormValidation();
    
    // Handle search student functionality
    initStudentSearch();
    
    // Handle sit-in checkout buttons
    initCheckoutButtons();
    
    // Handle flash messages dismissal
    initFlashMessages();
    
    // Initialize date pickers
    initDatePickers();
    
    // Initialize filters
    initFilters();
    
    // Initialize export buttons
    initExportButtons();
});

// Modal handling
function initModals() {
    // Get all modal open buttons
    const modalOpenButtons = document.querySelectorAll('[data-toggle="modal"]');
    
    modalOpenButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetModal = document.querySelector(this.getAttribute('data-target'));
            if (targetModal) {
                targetModal.style.display = 'block';
            }
        });
    });
    
    // Get all modal close buttons
    const modalCloseButtons = document.querySelectorAll('.close-btn, .btn-close');
    
    modalCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });
}

// Form validation
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Create error message if it doesn't exist
                    let errorMsg = field.nextElementSibling;
                    if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                        errorMsg = document.createElement('div');
                        errorMsg.classList.add('error-message');
                        errorMsg.style.color = 'red';
                        errorMsg.style.fontSize = '0.8rem';
                        errorMsg.style.marginTop = '5px';
                        field.after(errorMsg);
                    }
                    
                    errorMsg.textContent = 'This field is required';
                } else {
                    field.classList.remove('is-invalid');
                    
                    // Remove error message if it exists
                    const errorMsg = field.nextElementSibling;
                    if (errorMsg && errorMsg.classList.contains('error-message')) {
                        errorMsg.remove();
                    }
                }
            });
            
            if (!isValid) {
                event.preventDefault();
            }
        });
        
        // Clear validation errors on input
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                this.classList.remove('is-invalid');
                
                // Remove error message if it exists
                const errorMsg = this.nextElementSibling;
                if (errorMsg && errorMsg.classList.contains('error-message')) {
                    errorMsg.remove();
                }
            });
        });
    });
}

// Student search functionality
function initStudentSearch() {
    const searchForm = document.getElementById('student-search-form');
    const studentIdInput = document.getElementById('student-id-input');
    const studentNameInput = document.getElementById('student-name-input');
    
    if (searchForm && studentIdInput) {
        searchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const studentId = studentIdInput.value.trim();
            
            if (!studentId) {
                alert('Please enter a student ID');
                return;
            }
            
            // Fetch student data
            fetch(`/student/${studentId}`)
                .then(response => {
                    if (!response.ok) {
                        if (response.status === 404) {
                            if (confirm('Student not found. Do you want to register this student?')) {
                                // Populate student ID in the form
                                const sitInForm = document.getElementById('sit-in-form');
                                if (sitInForm) {
                                    const sitInStudentIdInput = document.getElementById('student_id');
                                    if (sitInStudentIdInput) {
                                        sitInStudentIdInput.value = studentId;
                                    }
                                }
                                
                                // Show sit-in modal if it exists
                                const sitInModal = document.getElementById('sit-in-modal');
                                if (sitInModal) {
                                    sitInModal.style.display = 'block';
                                }
                            }
                            throw new Error('Student not found');
                        }
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    // Populate student data in form
                    if (studentNameInput) {
                        studentNameInput.value = data.name;
                    }
                    
                    // Other fields can be populated here
                    
                    // Show sit-in modal if it exists
                    const sitInModal = document.getElementById('sit-in-modal');
                    if (sitInModal) {
                        // Populate student ID and name in the sit-in form
                        const sitInStudentIdInput = document.getElementById('student_id');
                        const sitInStudentNameInput = document.getElementById('student_name');
                        
                        if (sitInStudentIdInput) {
                            sitInStudentIdInput.value = data.id;
                        }
                        
                        if (sitInStudentNameInput) {
                            sitInStudentNameInput.value = data.name;
                        }
                        
                        sitInModal.style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        });
    }
}

// Checkout buttons
function initCheckoutButtons() {
    const checkoutButtons = document.querySelectorAll('.checkout-btn');
    
    checkoutButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (confirm('Are you sure you want to check out this student?')) {
                // Proceed with the checkout
                window.location.href = this.getAttribute('data-href');
            }
        });
    });
}

// Flash messages
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(message => {
        // Add close button if it doesn't exist
        if (!message.querySelector('.close')) {
            const closeButton = document.createElement('span');
            closeButton.classList.add('close');
            closeButton.innerHTML = '&times;';
            closeButton.style.float = 'right';
            closeButton.style.cursor = 'pointer';
            closeButton.style.fontWeight = 'bold';
            
            closeButton.addEventListener('click', function() {
                message.style.display = 'none';
            });
            
            message.insertBefore(closeButton, message.firstChild);
        }
        
        // Auto-hide flash messages after 5 seconds
        setTimeout(() => {
            message.style.display = 'none';
        }, 5000);
    });
}

// Date pickers
function initDatePickers() {
    const datePickers = document.querySelectorAll('input[type="date"]');
    
    datePickers.forEach(datePicker => {
        // Set default date to today if not already set
        if (!datePicker.value) {
            const today = new Date();
            const yyyy = today.getFullYear();
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');
            datePicker.value = `${yyyy}-${mm}-${dd}`;
        }
    });
}

// Filter handling
function initFilters() {
    const filterForms = document.querySelectorAll('.filter-form');
    
    filterForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            
            // Build query string from form fields
            const formData = new FormData(form);
            const queryString = new URLSearchParams(formData).toString();
            
            // Redirect to current page with filter parameters
            window.location.href = window.location.pathname + '?' + queryString;
        });
    });
}

// Export buttons
function initExportButtons() {
    const exportButtons = document.querySelectorAll('.export-btn');
    
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const format = this.getAttribute('data-format');
            const baseUrl = this.getAttribute('data-url') || '/export-report';
            
            // Get current filter parameters from URL
            const urlParams = new URLSearchParams(window.location.search);
            
            // Add format parameter
            urlParams.set('format', format);
            
            // Redirect to export URL with parameters
            window.location.href = baseUrl + '?' + urlParams.toString();
        });
    });
}
