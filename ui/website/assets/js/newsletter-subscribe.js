/**
 * Sentimark Newsletter Subscription Handler
 * Secure, low-cost serverless implementation
 */

(function() {
  document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('sentimark-subscribe-form');
    const emailInput = document.getElementById('subscriber-email');
    const errorMessage = document.getElementById('email-error-message');
    const successMessage = document.getElementById('subscribe-success');
    const errorResponse = document.getElementById('subscribe-error');
    const submitButton = document.getElementById('subscribe-button');
    
    if (!form || !emailInput || !submitButton) return;
    
    // Email validation
    emailInput.addEventListener('input', function() {
      validateEmail(this.value);
    });
    
    // Form submission handling
    form.addEventListener('submit', async function(event) {
      event.preventDefault();
      
      if (!validateEmail(emailInput.value)) return;
      
      // Show loading state
      submitButton.disabled = true;
      submitButton.innerText = 'Subscribing...';
      errorResponse.style.display = 'none';
      
      try {
        // Send to AWS Lambda function via API Gateway
        const response = await submitSubscription(emailInput.value);
        
        // Handle success
        if (response.success) {
          form.reset();
          successMessage.style.display = 'block';
          successMessage.textContent = 'Thank you for subscribing!';
          
          // Hide success message after 5 seconds
          setTimeout(() => {
            successMessage.style.display = 'none';
          }, 5000);
        } else {
          // Handle error from server
          throw new Error(response.message || 'Subscription failed');
        }
      } catch (error) {
        // Show error message
        errorResponse.style.display = 'block';
        errorResponse.textContent = error.message || 'An error occurred. Please try again later.';
        
        // Hide error message after 5 seconds
        setTimeout(() => {
          errorResponse.style.display = 'none';
        }, 5000);
      } finally {
        // Reset button state
        submitButton.disabled = false;
        submitButton.innerText = 'Subscribe';
      }
    });
    
    // Email validation function
    function validateEmail(email) {
      const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      const isValid = regex.test(email);
      
      if (email && !isValid) {
        errorMessage.textContent = 'Please enter a valid email address';
        errorMessage.style.display = 'block';
        return false;
      } else {
        errorMessage.textContent = '';
        errorMessage.style.display = 'none';
        return true;
      }
    }
    
    // Function to submit subscription to serverless endpoint
    async function submitSubscription(email) {
      // API Gateway URL - this would be created in AWS and linked to a Lambda function
      const apiEndpoint = 'https://api.sentimark.ai/subscribe';
      
      // Add recaptcha token if present
      const recaptchaToken = document.getElementById('g-recaptcha-response') ?
        document.getElementById('g-recaptcha-response').value : null;
      
      const data = {
        email: email,
        source: window.location.pathname,
        timestamp: new Date().toISOString(),
        recaptchaToken: recaptchaToken
      };
      
      // For development/testing purposes, return mock success response
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({ success: true, message: 'Subscription successful (test mode)' });
          }, 1000);
        });
      }
      
      // Production API call
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Api-Key': 'sm_newsletter_webapp' // This public key only identifies the source
        },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Error: ${response.status}`);
      }
      
      return await response.json();
    }
  });
})();