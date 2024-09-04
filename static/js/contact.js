// contact.js

document.getElementById('contact-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;

    // Simulate form submission
    alert('Thank you for contacting us, ' + name + '! We will get back to you soon.');

    // Clear the form
    this.reset();
});
