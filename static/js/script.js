// script.js

// Dark Mode Toggle
document.querySelector('.dark-mode-toggle').addEventListener('click', function() {
    document.body.classList.toggle('dark-mode');
});

// Real-time Form Validation
const inputs = document.querySelectorAll('input');
inputs.forEach(input => {
    input.addEventListener('input', function() {
        if (this.checkValidity()) {
            this.classList.add('valid');
            this.classList.remove('invalid');
        } else {
            this.classList.add('invalid');
            this.classList.remove('valid');
        }
    });
});
