/**
 * Kickstarter Countdown Timer Script
 * Counts down to July 4, 2025 at 9:00am
 *
 * Features:
 * - Robust initialization that tries multiple times
 * - Works with both DOMContentLoaded and window.onload events
 * - Runs even if the DOM isn't fully loaded yet
 * - Comprehensive error handling
 * - Animation when digits update
 * - Automatic update to campaign UI when countdown ends
 *
 * Note: There's also an inline fallback script in the HTML
 * for immediate display of countdown values.
 */

(function() {
  // Make sure we run this as soon as possible and again when DOM is fully loaded
  initCountdown();

  // Use both DOMContentLoaded and window.onload for maximum compatibility
  document.addEventListener('DOMContentLoaded', initCountdown);
  window.addEventListener('load', initCountdown);

  // Store the interval ID globally within this IIFE
  let countdownInterval;

  function initCountdown() {
    try {
      console.log('Initializing countdown timer...');

      // Set the date we're counting down to (July 4, 2025)
      const countdownDate = new Date("July 4, 2025 09:00:00").getTime();

      // Get the countdown container
      const countdownContainer = document.getElementById('countdown-timer');

      // Only proceed if the countdown element exists on the page
      if (!countdownContainer) {
        console.warn('Countdown container not found, will try again later.');
        return;
      }

      console.log('Countdown container found:', countdownContainer);

      // Get the countdown elements
      const daysElement = document.getElementById('countdown-days');
      const hoursElement = document.getElementById('countdown-hours');
      const minutesElement = document.getElementById('countdown-minutes');
      const secondsElement = document.getElementById('countdown-seconds');

      // Check if all elements were found
      if (!daysElement || !hoursElement || !minutesElement || !secondsElement) {
        console.warn('One or more countdown elements not found, will try again later:', {
          daysElement: !!daysElement,
          hoursElement: !!hoursElement,
          minutesElement: !!minutesElement,
          secondsElement: !!secondsElement
        });
        return;
      }

      console.log('All countdown elements found!');

      // Add animated class to the countdown container
      countdownContainer.classList.add('animated');

      // Clear any existing interval to prevent duplicates
      if (countdownInterval) {
        clearInterval(countdownInterval);
      }

      // Initialize with current countdown values
      updateCountdown();

      // Update the countdown every 1 second
      countdownInterval = setInterval(updateCountdown, 1000);

      // Function to update the countdown
      function updateCountdown() {
        try {
          // Get current date and time
          const now = new Date().getTime();

          // Find the time difference between now and the countdown date
          const timeRemaining = countdownDate - now;

          // Calculate days, hours, minutes and seconds remaining
          const days = Math.floor(timeRemaining / (1000 * 60 * 60 * 24));
          const hours = Math.floor((timeRemaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
          const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
          const seconds = Math.floor((timeRemaining % (1000 * 60)) / 1000);

          // Display the result with leading zeros
          if (daysElement) daysElement.textContent = days.toString().padStart(2, '0');
          if (hoursElement) hoursElement.textContent = hours.toString().padStart(2, '0');
          if (minutesElement) minutesElement.textContent = minutes.toString().padStart(2, '0');
          if (secondsElement) secondsElement.textContent = seconds.toString().padStart(2, '0');

          // If the countdown is finished, display a message
          if (timeRemaining < 0) {
            clearInterval(countdownInterval);

            if (daysElement) daysElement.textContent = '00';
            if (hoursElement) hoursElement.textContent = '00';
            if (minutesElement) minutesElement.textContent = '00';
            if (secondsElement) secondsElement.textContent = '00';

            // Change the status label
            const statusLabel = document.querySelector('.status-label');
            if (statusLabel) {
              statusLabel.textContent = 'Campaign Live Now!';
              statusLabel.classList.add('live');
            }

            // Update the CTA button
            const ctaButton = countdownContainer.nextElementSibling;
            if (ctaButton && ctaButton.classList.contains('btn')) {
              ctaButton.textContent = 'Back Us On Kickstarter';
              ctaButton.setAttribute('href', '#');
              ctaButton.classList.add('btn-accent');
            }
          }
        } catch (error) {
          console.error('Error updating countdown:', error);
        }
      }
    } catch (error) {
      console.error('Error initializing countdown:', error);
    }
  }
})();