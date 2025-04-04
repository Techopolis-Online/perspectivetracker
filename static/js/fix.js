// Fix for the JavaScript error
document.addEventListener('DOMContentLoaded', function() {
    // Add null check for form elements
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (form) {
            form.addEventListener('submit', function(e) {
                // Prevent default form submission
                e.preventDefault();
                
                // Get form data
                const formData = new FormData(this);
                
                // Submit form using fetch
                fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Show success message
                        const alertHtml = `
                            <div class="alert alert-success alert-dismissible fade show" role="alert">
                                <i class="bi bi-check-circle me-1"></i> ${data.message}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        `;
                        
                        // Insert alert before the form
                        this.insertAdjacentHTML('beforebegin', alertHtml);
                        
                        // Update the issues table if it exists
                        const issuesTable = document.querySelector('#issuesTable tbody');
                        if (issuesTable && data.issues_html) {
                            issuesTable.innerHTML = data.issues_html;
                        }
                    } else {
                        // Show error message
                        const alertHtml = `
                            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                                <i class="bi bi-exclamation-triangle me-1"></i> ${data.message}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        `;
                        this.insertAdjacentHTML('beforebegin', alertHtml);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Show error message
                    const alertHtml = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <i class="bi bi-exclamation-triangle me-1"></i> An error occurred. Please try again.
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                    this.insertAdjacentHTML('beforebegin', alertHtml);
                });
            });
        }
    });
}); 