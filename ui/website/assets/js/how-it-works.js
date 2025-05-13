document.addEventListener('DOMContentLoaded', function() {
  // Add animation classes to elements
  const animateElements = document.querySelectorAll('.tech-animate');
  
  // Set up Intersection Observer
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // Unobserve after animation is triggered
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.15
  });
  
  // Observe all elements with animation class
  animateElements.forEach(element => {
    observer.observe(element);
  });
  
  // 3D effect for the use case cards
  const useCards = document.querySelectorAll('.use-case-card');
  
  useCards.forEach(card => {
    card.addEventListener('mousemove', function(e) {
      const cardRect = card.getBoundingClientRect();
      const cardCenterX = cardRect.left + cardRect.width / 2;
      const cardCenterY = cardRect.top + cardRect.height / 2;
      
      // Calculate mouse position relative to card center (in px)
      const mouseX = e.clientX - cardCenterX;
      const mouseY = e.clientY - cardCenterY;
      
      // Calculate rotation (max 10 degrees)
      const rotateY = (mouseX / (cardRect.width / 2)) * 5;
      const rotateX = (mouseY / (cardRect.height / 2)) * -5;
      
      // Apply transform to card
      card.style.transform = `perspective(1000px) rotateY(${rotateY}deg) rotateX(${rotateX}deg) translateZ(10px)`;
      
      // Move card icon for extra depth effect
      const cardIcon = card.querySelector('.use-case-icon');
      if (cardIcon) {
        cardIcon.style.transform = `translateX(${mouseX * 0.05}px) translateY(${mouseY * 0.05}px)`;
      }
    });
    
    // Reset transform on mouse leave
    card.addEventListener('mouseleave', function() {
      card.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) translateZ(0)';
      
      const cardIcon = card.querySelector('.use-case-icon');
      if (cardIcon) {
        cardIcon.style.transform = 'translateX(0) translateY(0)';
      }
    });
  });
  
  // Animate process steps on scroll
  const processSteps = document.querySelectorAll('.process-step');
  
  processSteps.forEach((step, index) => {
    step.style.transitionDelay = `${index * 0.1}s`;
    
    const stepObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          step.classList.add('active');
          stepObserver.unobserve(step);
        }
      });
    }, { threshold: 0.3 });
    
    stepObserver.observe(step);
  });
  
  // Create animation for metric numbers
  const metricStats = document.querySelectorAll('.metric-stat');
  let metricsAnimated = false;
  
  // Function to animate metrics
  function animateMetrics() {
    if (metricsAnimated) return;
    
    metricStats.forEach(stat => {
      const targetValue = parseFloat(stat.getAttribute('data-value'));
      const duration = 2000; // Animation duration in ms
      const decimals = stat.getAttribute('data-decimals') || 0;
      const suffix = stat.getAttribute('data-suffix') || '';
      let startTime;
      
      // Counter animation function
      function updateCounter(timestamp) {
        if (!startTime) startTime = timestamp;
        const elapsed = timestamp - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function - cubic ease out
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        // Calculate current value
        const currentValue = (targetValue * easeProgress).toFixed(decimals);
        
        // Update DOM
        stat.textContent = currentValue + suffix;
        
        // Continue animation if not complete
        if (progress < 1) {
          requestAnimationFrame(updateCounter);
        }
      }
      
      // Start animation
      requestAnimationFrame(updateCounter);
    });
    
    metricsAnimated = true;
  }
  
  // Observe metrics section
  const metricsSection = document.querySelector('.performance-metrics');
  if (metricsSection) {
    const metricsObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          animateMetrics();
          metricsObserver.unobserve(metricsSection);
        }
      });
    }, { threshold: 0.2 });
    
    metricsObserver.observe(metricsSection);
  }
  
  // Parallax effect for tech hero section
  const techHero = document.querySelector('.tech-hero');
  const heroContent = document.querySelector('.tech-hero__content');
  const heroImage = document.querySelector('.tech-hero__image');
  
  if (techHero && heroImage) {
    window.addEventListener('scroll', function() {
      const scrollTop = window.pageYOffset;
      const heroTop = techHero.offsetTop;
      const heroHeight = techHero.offsetHeight;
      
      // Only apply parallax when hero section is visible
      if (scrollTop < heroTop + heroHeight) {
        const parallaxOffset = (scrollTop - heroTop) * 0.3;
        
        // Move content and image at different speeds
        if (heroImage) {
          heroImage.style.transform = `translateY(${parallaxOffset}px)`;
        }
        
        if (heroContent) {
          heroContent.style.transform = `translateY(${parallaxOffset * 0.5}px)`;
        }
      }
    });
  }
  
  // Add particle effects to tech architecture section
  const architectureSection = document.querySelector('.tech-architecture');
  
  if (architectureSection) {
    const techParticles = document.createElement('div');
    techParticles.className = 'tech-particles';
    architectureSection.appendChild(techParticles);
    
    // Create particles
    for (let i = 0; i < 30; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      
      // Random size between 2px and 6px
      const size = Math.random() * 4 + 2;
      particle.style.width = `${size}px`;
      particle.style.height = `${size}px`;
      
      // Random position
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.top = `${Math.random() * 100}%`;
      
      // Random opacity
      particle.style.opacity = Math.random() * 0.3 + 0.1;
      
      // Add animation with random duration
      const duration = Math.random() * 30 + 15;
      particle.style.animation = `float ${duration}s infinite ease-in-out`;
      
      // Add to container
      techParticles.appendChild(particle);
    }
  }
});