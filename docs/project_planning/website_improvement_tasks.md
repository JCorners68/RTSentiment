# Sentimark Website Improvement Plan

This document outlines the comprehensive improvement tasks for the Sentimark website, organized by priority, category, and with clear validation criteria.

## Priority Tasks

### 1. Visual & Branding
- [ ] **Create and Add Real Images**
  - Hero/landing page image (brand, product, or AI concept)
  - Product screenshots or mockups
  - Team photos (real or professional placeholders)
  - Case study or testimonial images
  - Blog post cover images
- [ ] **Replace Placeholder Images**
  - Remove or update all stock placeholders with brand-aligned visuals
  - Implement proper alt text for all images for accessibility
- [ ] **Design Custom Icons/Graphics**
  - Feature icons (unique to Sentimark's value props)
  - Process/How It Works diagram
  - Kickstarter/Investor badges
- [ ] **Logo and Favicon Implementation**
  - Finalize logo designs (colored and white versions)
  - Create favicon.ico (16x16, 32x32)
  - Generate apple-touch-icon (180x180)
  - Create PNG fallbacks for SVG logos
  - Implement Open Graph and Twitter card images

### 2. Content & Copy
- [ ] **Finalize All Page Content**
  - Homepage: Clear value proposition, call to action, and summary
  - Product Overview: What, why, and differentiators
  - Product Features: Bullet points, visuals, and use cases
  - How It Works: Step-by-step with visuals/diagrams
  - Hidden Alpha: Explain the unique AI/alpha concept
  - Case Studies: Real or hypothetical, with outcomes
  - About: Company, team, and investor bios
  - Blog: At least 2–3 posts (even if short) to show momentum
  - Kickstarter Page: Campaign details, rewards, and timeline
  - Contact Page: Up-to-date info, privacy/disclaimer text
- [ ] **Complete Legal Pages**
  - Create privacy policy page
  - Create terms of service page
  - Add GDPR/CCPA compliance statements

### 3. Forms & Functionality
- [ ] **Newsletter Integration**
  - Create actual Mailchimp account 
  - Set up Mailchimp list for the website
  - Update newsletter form with actual Mailchimp credentials
  - Test subscription flow
  - Implement double opt-in confirmation
- [ ] **Contact Form Implementation**
  - Implement serverless function for form handling (AWS Lambda or Netlify Functions)
  - Set up email forwarding for form submissions
  - Add form validation with error messages
  - Implement spam protection (honeypot and/or reCAPTCHA)
  - Add success/error states and messages
- [ ] **Add Social Proof**
  - Testimonials, press mentions, or user logos
  - Add social share buttons to blog posts

### 4. UX & Accessibility
- [ ] **Review Responsive Design**
  - Test across mobile, tablet, and desktop
  - Fix layout or font issues on small screens
  - Optimize tap targets for mobile users
  - Ensure form fields are appropriately sized on mobile
- [ ] **Accessibility Improvements**
  - Add alt text to all images
  - Ensure color contrast meets WCAG standards (minimum AA)
  - Add keyboard navigation for all interactive elements
  - Implement ARIA attributes where needed
  - Test with screen readers
  - Add skip-to-content link
- [ ] **Navigation Enhancements**
  - Ensure all menu links work and are intuitive
  - Add sticky or mobile-friendly navigation
  - Test and optimize mobile menu behavior

### 5. Technical & Performance
- [ ] **Resolve All SCSS/Jekyll Deprecation Warnings**
  - Ensure no warnings on build (test in production mode)
- [ ] **Performance Optimization**
  - Optimize image file sizes and formats (WebP where possible)
  - Implement lazy loading for images
  - Minify CSS and JavaScript
  - Implement critical CSS for faster rendering
  - Set up browser caching with appropriate headers
- [ ] **SEO Enhancement**
  - Optimize page titles and meta descriptions
  - Implement structured data (JSON-LD)
  - Ensure sitemap.xml is comprehensive
  - Register site with Google Search Console and Bing Webmaster Tools
  - Fix any crawl errors or issues
- [ ] **Analytics Integration**
  - Set up Google Analytics or Plausible Analytics
  - Create custom events for key user interactions
  - Set up conversion tracking for newsletter signups and form submissions
  - Implement privacy-friendly analytics configuration

### 6. Deployment & Documentation
- [ ] **Update README.md**
  - Add clear setup, build, and deploy instructions
  - Document image and content update process
- [ ] **Deployment Process Improvement**
  - Test build output on Bluehost staging or equivalent
  - Check .htaccess or config for Jekyll static hosting
  - Set up continuous integration for the website
  - Create staging environment for pre-production testing
- [ ] **Cross-Browser Testing**
  - Test in Chrome, Firefox, Safari, Edge (desktop & mobile)
  - Document browser compatibility

### 7. Future Enhancements
- [ ] **Interactive Elements**
  - Add subtle animations on scroll
  - Interactive product demo or video
  - Real-time sentiment visualization widget
  - Create demo/preview of the platform UI
- [ ] **Content Expansion**
  - Investor/Press resource section
  - Create FAQ page with comprehensive questions and answers
  - Create case studies for the Hidden Alpha section
  - Develop resources section with whitepapers or guides
- [ ] **Social Media Integration**
  - Create actual social media accounts
  - Add social feed integration
  - Implement cross-posting functionality
- [ ] **Monitoring and Maintenance**
  - Set up uptime monitoring
  - Implement security headers and best practices
  - Create backup and restoration procedure
  - Document maintenance schedule and responsibilities

## Definition of Done

A task is considered complete when:

1. The implemented feature functions correctly across all supported browsers and devices
2. The code is validated, linted, and follows project conventions
3. The feature has been tested by at least one other team member
4. Any required documentation has been updated
5. The feature passes accessibility checks
6. The feature does not negatively impact performance metrics
7. The changes have been deployed to the production environment
8. Validation evidence has been documented (screenshots, test results, etc.)

## Validation Methods

For each implemented feature, the following validation methods should be used:

1. **Cross-browser testing**: Chrome, Firefox, Safari, Edge
2. **Device testing**: Desktop, tablet, and mobile
3. **Performance testing**: Lighthouse scores (aim for 90+ on all metrics)
4. **Accessibility testing**: WAVE or axe tools, screen reader testing
5. **User testing**: Test with 2-3 users unfamiliar with the project

## Verification Commands

```bash
# Build site for production
cd ui/website
JEKYLL_ENV=production bundle exec jekyll build

# Test site locally
bundle exec jekyll serve --livereload

# Run Lighthouse CI
npx lighthouse-ci https://sentimark.com

# Validate HTML
npx html-validate "_site/**/*.html"

# Check for broken links
npx broken-link-checker https://sentimark.com
```

## Implementation Timeline

- **Week 1**: Visual & Branding, Content & Copy
- **Week 2**: Forms & Functionality, UX & Accessibility
- **Week 3**: Technical & Performance, Deployment & Documentation
- **Week 4**: Final review and future enhancements planning

## Resources Required

- **Design**: Graphics designer for images, icons, and visual assets
- **Development**: Frontend developer with Jekyll experience
- **Content**: Copywriter for privacy policy, terms, and blog posts
- **QA**: Tester for cross-browser and device testing

## Suggested Implementation Approach

1. Start with high-visibility improvements (images, content, branding) for maximum stakeholder impact
2. Prioritize functionality improvements (forms, newsletter) that directly impact user engagement
3. Enhance technical aspects (performance, SEO) to improve discoverability and user experience
4. Document thoroughly to ensure maintainability and consistency

---

*Last Updated: May 12, 2025*