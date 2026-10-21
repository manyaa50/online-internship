// Smart Internship Management System Client Interactions
document.addEventListener('DOMContentLoaded', () => {

    // Auto-dismiss alert messages after 5 seconds
    const flashAlerts = document.querySelectorAll('.alert-dismissible');
    flashAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Mark single notification read
    window.markNotifRead = function(notifId, element) {
        fetch(`/auth/notifications/mark-read/${notifId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && element) {
                element.classList.remove('bg-light');
                element.classList.add('text-muted');
                const badge = element.querySelector('.badge');
                if (badge) badge.remove();
            }
        })
        .catch(err => console.error('Error marking notification read:', err));
    };

    // Helper to get CSRF token from meta or input
    function getCsrfToken() {
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) return csrfInput.value;
        const metaCsrf = document.querySelector('meta[name="csrf-token"]');
        return metaCsrf ? metaCsrf.getAttribute('content') : '';
    }

    // Role switcher on registration page
    const roleRadios = document.querySelectorAll('input[name="role"]');
    const studentFields = document.getElementById('studentRegistrationFields');
    const companyFields = document.getElementById('companyRegistrationFields');

    if (roleRadios.length > 0 && studentFields && companyFields) {
        roleRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if (e.target.value === 'student') {
                    studentFields.classList.remove('d-none');
                    companyFields.classList.add('d-none');
                } else if (e.target.value === 'company') {
                    studentFields.classList.add('d-none');
                    companyFields.classList.remove('d-none');
                }
            });
        });
    }

    // Client-side file size and format validation
    const resumeInputs = document.querySelectorAll('input[type="file"][name*="resume"]');
    resumeInputs.forEach(input => {
        input.addEventListener('change', () => {
            const file = input.files[0];
            if (file) {
                const maxBytes = 8 * 1024 * 1024; // 8MB
                const allowedExts = ['pdf', 'docx'];
                const ext = file.name.split('.').pop().toLowerCase();

                if (!allowedExts.includes(ext)) {
                    alert('Invalid file format. Please upload a PDF or DOCX file.');
                    input.value = '';
                    return;
                }

                if (file.size > maxBytes) {
                    alert('File is too large! Maximum allowed file size is 8MB.');
                    input.value = '';
                }
            }
        });
    });

});
}
