// Main JavaScript for Sentimark website

document.addEventListener('DOMContentLoaded', function() {
  // Mobile menu toggle
  setupMobileMenu();

  // Header scroll effect
  setupHeaderScroll();

  // Form handling
  setupForms();

  // Image lazy loading
  setupLazyLoading();

  // Accessibility enhancements
  setupAccessibility();
});

/**
 * Setup mobile menu functionality
 */
function setupMobileMenu() {
  const menuToggle = document.querySelector('.menu-toggle');
  const navMenu = document.querySelector('.nav-menu');

  if (menuToggle && navMenu) {
    menuToggle.addEventListener('click', function() {
      const expanded = this.getAttribute('aria-expanded') === 'true' || false;
      this.setAttribute('aria-expanded', !expanded);
      navMenu.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(event) {
      if (
        !event.target.closest('.main-nav') &&
        navMenu.classList.contains('active')
      ) {
        menuToggle.setAttribute('aria-expanded', 'false');
        navMenu.classList.remove('active');
      }
    });

    // Add keyboard navigation for menu
    navMenu.querySelectorAll('a').forEach(item => {
      item.addEventListener('keydown', function(e) {
        // Handle Tab key navigation
        if (e.key === 'Escape') {
          menuToggle.setAttribute('aria-expanded', 'false');
          navMenu.classList.remove('active');
          menuToggle.focus();
        }
      });
    });
  }
}

/**
 * Setup header scroll effect
 */
function setupHeaderScroll() {
  const header = document.querySelector('.site-header');

  if (header) {
    window.addEventListener('scroll', function() {
      if (window.scrollY > 50) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    });
  }
}

/**
 * Setup all forms
 */
function setupForms() {
  // Set up newsletter form
  setupNewsletterForm();

  // Set up contact form
  setupContactForm();
}

/**
 * Setup newsletter form handling
 */
function setupNewsletterForm() {
  const form = document.getElementById('mc-embedded-subscribe-form');

  if (form) {
    const emailInput = document.getElementById('mce-EMAIL');
    const errorElement = document.getElementById('email-error-message');
    const successElement = document.getElementById('mce-success-response');
    const errorResponse = document.getElementById('mce-error-response');

    if (emailInput) {
      // Validate on input change
      emailInput.addEventListener('input', function() {
        validateInput(emailInput, errorElement);
      });

      // Validate on blur
      emailInput.addEventListener('blur', function() {
        validateInput(emailInput, errorElement);
      });
    }

    // Handle form submission
    form.addEventListener('submit', function(event) {
      // Demo mode handling - remove for production
      if (window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1' ||
          window.location.hostname.includes('github.io')) {
        event.preventDefault();

        // Simulate successful submission
        if (validateForm(form)) {
          if (successElement) {
            successElement.textContent = 'Thank you for subscribing! (Demo mode)';
            successElement.style.display = 'block';

            // Reset form
            form.reset();

            // Hide success message after delay
            setTimeout(() => {
              successElement.style.display = 'none';
            }, 5000);
          }
        }
        return;
      }

      // Production validation
      if (!validateForm(form)) {
        event.preventDefault();
      }
    });
  }
}

/**
 * Setup contact form handling
 */
function setupContactForm() {
  const form = document.getElementById('contactForm');

  if (form) {
    const formFields = form.querySelectorAll('input[required], textarea[required], select[required]');

    // Validate each required field on blur
    formFields.forEach(field => {
      field.addEventListener('blur', function() {
        validateInput(field);
      });
    });

    // Handle form submission
    form.addEventListener('submit', function(event) {
      // Demo mode handling - remove for production
      if (window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1' ||
          window.location.hostname.includes('github.io')) {
        event.preventDefault();

        if (validateForm(form)) {
          // Show success message
          const formActions = form.querySelector('.form-actions');
          const successMessage = document.createElement('div');
          successMessage.className = 'form-success-message';
          successMessage.textContent = 'Thank you for your message! We will get back to you soon. (Demo mode)';

          if (formActions.nextElementSibling && formActions.nextElementSibling.classList.contains('form-success-message')) {
            formActions.nextElementSibling.remove();
          }

          formActions.insertAdjacentElement('afterend', successMessage);

          // Reset form
          form.reset();
        }
        return;
      }

      // Production validation
      if (!validateForm(form)) {
        event.preventDefault();
      }
    });
  }
}

/**
 * Validate an individual form input
 * @param {HTMLElement} input - Input element to validate
 * @param {HTMLElement} errorElement - Element to show error message (optional)
 * @returns {boolean} - Whether input is valid
 */
function validateInput(input, errorElement) {
  let isValid = true;
  let errorMessage = '';

  // Check for empty required field
  if (input.hasAttribute('required') && !input.value.trim()) {
    isValid = false;
    errorMessage = 'This field is required';
  }
  // Email validation
  else if (input.type === 'email' && input.value.trim() && !isValidEmail(input.value)) {
    isValid = false;
    errorMessage = 'Please enter a valid email address';
  }

  // Show error message if provided an error element
  if (errorElement) {
    errorElement.textContent = errorMessage;
    errorElement.style.display = isValid ? 'none' : 'block';
  } else {
    // If no error element provided, add/remove error class
    if (isValid) {
      input.classList.remove('error');
      // Remove any existing error message
      const existingError = input.parentNode.querySelector('.input-error-message');
      if (existingError) existingError.remove();
    } else {
      input.classList.add('error');
      // Add error message if not exists
      let errorEl = input.parentNode.querySelector('.input-error-message');
      if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.className = 'input-error-message';
        input.insertAdjacentElement('afterend', errorEl);
      }
      errorEl.textContent = errorMessage;
    }
  }

  return isValid;
}

/**
 * Validate an entire form
 * @param {HTMLFormElement} form - Form to validate
 * @returns {boolean} - Whether form is valid
 */
function validateForm(form) {
  const requiredFields = form.querySelectorAll('input[required], textarea[required], select[required]');
  let isValid = true;

  requiredFields.forEach(field => {
    // Find error element for this field
    const fieldName = field.name || field.id;
    const errorElement = form.querySelector(`#${fieldName}-error`) || null;

    const fieldValid = validateInput(field, errorElement);
    if (!fieldValid) isValid = false;
  });

  return isValid;
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} - Whether email is valid
 */
function isValidEmail(email) {
  const regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return regex.test(email);
}

/**
 * Setup lazy loading for images
 */
function setupLazyLoading() {
  if ('loading' in HTMLImageElement.prototype) {
    // Browser supports native lazy loading
    document.querySelectorAll('img[data-src]').forEach(img => {
      img.src = img.dataset.src;
      if (img.dataset.srcset) {
        img.srcset = img.dataset.srcset;
      }
      img.classList.add('loaded');
    });
  } else {
    // Fallback for browsers that don't support native lazy loading
    const lazyImages = document.querySelectorAll('img[data-src]');

    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const lazyImage = entry.target;
            lazyImage.src = lazyImage.dataset.src;
            if (lazyImage.dataset.srcset) {
              lazyImage.srcset = lazyImage.dataset.srcset;
            }
            lazyImage.classList.add('loaded');
            imageObserver.unobserve(lazyImage);
          }
        });
      });

      lazyImages.forEach(image => {
        imageObserver.observe(image);
      });
    } else {
      // Fallback for older browsers without IntersectionObserver
      let lazyLoadThrottleTimeout;

      function lazyLoad() {
        if (lazyLoadThrottleTimeout) {
          clearTimeout(lazyLoadThrottleTimeout);
        }

        lazyLoadThrottleTimeout = setTimeout(() => {
          const scrollTop = window.pageYOffset;

          lazyImages.forEach(lazyImage => {
            if (lazyImage.offsetTop < window.innerHeight + scrollTop) {
              lazyImage.src = lazyImage.dataset.src;
              if (lazyImage.dataset.srcset) {
                lazyImage.srcset = lazyImage.dataset.srcset;
              }
              lazyImage.classList.add('loaded');
            }
          });

          if (lazyImages.length === 0) {
            document.removeEventListener('scroll', lazyLoad);
            window.removeEventListener('resize', lazyLoad);
            window.removeEventListener('orientationChange', lazyLoad);
          }
        }, 20);
      }

      document.addEventListener('scroll', lazyLoad);
      window.addEventListener('resize', lazyLoad);
      window.addEventListener('orientationChange', lazyLoad);

      // Initial load
      lazyLoad();
    }
  }
}

/**
 * Setup accessibility enhancements
 */
function setupAccessibility() {
  // Add skip to content link functionality
  const skipLink = document.querySelector('.skip-to-content');
  if (skipLink) {
    skipLink.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.setAttribute('tabindex', '-1');
        target.focus();
      }
    });
  }

  // Ensure all interactive elements are keyboard accessible
  document.querySelectorAll('a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])').forEach(element => {
    if (!element.hasAttribute('tabindex')) {
      element.setAttribute('tabindex', '0');
    }
  });

  // Add proper ARIA attributes to any expandable sections
  document.querySelectorAll('.expandable-content').forEach(section => {
    const trigger = section.previousElementSibling;
    const content = section.querySelector('.content');

    if (trigger && content) {
      const id = `expandable-content-${Math.random().toString(36).substring(2, 11)}`;
      content.id = id;

      trigger.setAttribute('aria-expanded', 'false');
      trigger.setAttribute('aria-controls', id);

      trigger.addEventListener('click', function() {
        const expanded = this.getAttribute('aria-expanded') === 'true' || false;
        this.setAttribute('aria-expanded', !expanded);
        content.classList.toggle('active');
      });
    }
  });
}
