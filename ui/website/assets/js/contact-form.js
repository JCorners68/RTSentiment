// Contact Form Anti-Bot Measures and Validation

document.addEventListener('DOMContentLoaded', function() {
  // Time-based check: Set the form load time when the page loads
  const formTimeField = document.getElementById('form_time');
  if (formTimeField) {
    formTimeField.value = Date.now().toString();
  }

  // Get the contact form
  const contactForm = document.getElementById('contactForm');
  
  if (contactForm) {
    contactForm.addEventListener('submit', function(event) {
      // Prevent the default form submission
      event.preventDefault();
      
      // Perform bot checks
      if (isBotSubmission()) {
        // If it's a bot, silently "accept" the form but don't actually submit
        console.log('Bot submission detected');
        showSuccessMessage();
        return false;
      }
      
      // Validate the form
      if (validateForm()) {
        // In a real implementation, you would submit the form data via AJAX here
        // For now, we'll just show a success message
        showSuccessMessage();
      }
    });
  }
  
  // Check if the submission is likely from a bot
  function isBotSubmission() {
    // Honeypot check - If the hidden field is filled out, it's likely a bot
    const honeypotField = document.getElementById('website');
    if (honeypotField && honeypotField.value) {
      return true;
    }
    
    // Time-based check - If the form is submitted too quickly (less than 3 seconds), it's likely a bot
    const minTimeToFill = 3000; // 3 seconds in milliseconds
    const formTime = parseInt(formTimeField.value, 10);
    const currentTime = Date.now();
    const timeTaken = currentTime - formTime;
    
    if (timeTaken < minTimeToFill) {
      return true;
    }
    
    return false;
  }
  
  // Validate form inputs
  function validateForm() {
    let isValid = true;
    
    // Get form fields
    const nameField = document.getElementById('name');
    const emailField = document.getElementById('email');
    const subjectField = document.getElementById('subject');
    const messageField = document.getElementById('message');
    const privacyCheckbox = document.getElementById('privacy');
    
    // Clear any previous error messages
    clearErrors();
    
    // Validate name (at least 2 characters)
    if (!nameField.value || nameField.value.trim().length < 2) {
      showError(nameField, 'Please enter your name (at least 2 characters)');
      isValid = false;
    }
    
    // Validate email (basic format check)
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailField.value || !emailPattern.test(emailField.value)) {
      showError(emailField, 'Please enter a valid email address');
      isValid = false;
    }
    
    // Validate subject (must be selected)
    if (!subjectField.value) {
      showError(subjectField, 'Please select a subject');
      isValid = false;
    }
    
    // Validate message (at least 10 characters)
    if (!messageField.value || messageField.value.trim().length < 10) {
      showError(messageField, 'Please enter a message (at least 10 characters)');
      isValid = false;
    }
    
    // Validate privacy checkbox
    if (!privacyCheckbox.checked) {
      showError(privacyCheckbox, 'You must agree to the privacy policy');
      isValid = false;
    }
    
    return isValid;
  }
  
  // Show error message next to a field
  function showError(field, message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'form-error';
    errorElement.innerText = message;
    
    // Insert the error message after the field (or after the field's label for checkboxes)
    if (field.type === 'checkbox') {
      field.parentNode.after(errorElement);
    } else {
      field.after(errorElement);
    }
    
    // Add error class to the field
    field.classList.add('form-control-error');
  }
  
  // Clear all error messages
  function clearErrors() {
    const errorMessages = contactForm.querySelectorAll('.form-error');
    errorMessages.forEach(function(error) {
      error.remove();
    });
    
    const errorFields = contactForm.querySelectorAll('.form-control-error');
    errorFields.forEach(function(field) {
      field.classList.remove('form-control-error');
    });
  }
  
  // Show success message
  function showSuccessMessage() {
    // Hide the form
    contactForm.style.display = 'none';

    // Create success message
    const successMessage = document.createElement('div');
    successMessage.className = 'form-success';
    successMessage.innerHTML = `
      <h3>Thank You!</h3>
      <p>Your message has been received. This is a demo site - in a real implementation, your message would be securely stored and routed to the appropriate team.</p>
      <p style="margin-top: 1rem;"><small>Support for our Kickstarter campaign begins Summer 2025.</small></p>
    `;

    // Insert the success message after the form
    contactForm.parentNode.insertBefore(successMessage, contactForm.nextSibling);
  }
});