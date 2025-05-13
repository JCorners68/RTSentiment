# Website Structure & Content Strategy for Bluehost

This document outlines a comprehensive website structure and content strategy for Sentimark's Bluehost-hosted website, designed to appeal to both investors and potential Kickstarter backers.

## Site Architecture Recommendation

We recommend a **static site with minimal dynamic components** for the Sentimark website:

1. **Primary Technology**: Jekyll static site generator
   - Enables content management through Markdown
   - Provides templating for consistent design
   - Generates optimized HTML/CSS for fast load times
   - Supports version control through Git
   - Easy deployment to Bluehost

2. **Hosting Implementation**:
   - Static site files deployed to Bluehost via SFTP/Git
   - Minimal server requirements (no database needed)
   - Content updates through Jekyll regeneration and re-upload
   - Configure Bluehost for optimal caching and performance

3. **Dynamic Elements**:
   - Embedded Mailchimp for newsletter signups
   - Disqus for blog comments (optional)
   - Integrated Kickstarter widgets (during campaign)
   - Minimal JavaScript for interactive elements

## Site Structure

```
sentimark.com/
├── index.html                   # Homepage
├── product/                     # Product information
│   ├── index.html              # Overview
│   ├── features.html           # Detailed features
│   └── how-it-works.html       # Workflow explanation
├── alpha/                       # "Hidden Alpha" explanation
│   ├── index.html              # Concept overview
│   └── case-studies.html       # Example use cases
├── about/                       # Company information
│   ├── index.html              # Company overview
│   ├── team.html               # Team profiles
│   └── investors.html          # Investor information
├── blog/                        # Blog/updates
│   ├── index.html              # Blog listing
│   └── posts/                  # Individual posts
├── kickstarter/                 # Kickstarter campaign info
│   └── index.html              # Campaign details
└── contact/                     # Contact information
    └── index.html              # Contact form
```

## Page Content Strategy

### Homepage Components
- Hero section with bold value proposition highlighting "hidden alpha" sentiment analysis
- Problem/solution statement framing market sentiment challenges and Sentimark's unique approach
- Key features with visual icons emphasizing the agentic AI system capabilities
- Social proof (testimonials from beta users, potential partnerships)
- Call to action (pre-launch: newsletter signup; during campaign: Kickstarter link)
- Brief technical credibility section highlighting your role as Lead Technical Architect at a top consulting firm

### Product Page Components
- Detailed feature explanations of both basic and advanced sentiment analysis
- Visual demonstrations of sentiment analysis results (before/after comparisons)
- Mobile app mockups/screenshots showing the user interface
- Competitive differentiation table comparing Sentimark to conventional solutions
- Technical overview (appropriate for investor audience) emphasizing the agentic AI architecture
- Integration possibilities and API potential (for technical audiences)

### About Page Components
- Company mission and vision for transforming financial sentiment analysis
- Founding story focused on your technical leadership and AI expertise
- Team profiles highlighting your background and any advisors/contributors
- Investor-oriented information (market opportunity, growth strategy)
- Technical background section showcasing relevant experience and achievements

### Kickstarter Campaign Section
- Campaign timeline and goals
- Reward tier previews
- Funding allocation explanation
- Development roadmap
- Backer FAQ

## CCA Content Generation Prompt

Here's a comprehensive prompt to generate website content with CCA that specifically emphasizes your unique agentic AI approach and technical leadership background:

```
You are an expert copywriter for fintech products specializing in creating compelling website content for sophisticated financial tools. I need you to create content for the Sentimark website - a mobile application leveraging unique "hidden alpha" sentiment analysis features for financial markets. The key differentiator is our advanced agentic AI system that provides deeper insights than conventional sentiment tools.

AUDIENCE:
1. Sophisticated retail investors (primary Kickstarter backers)
2. Potential angel investors and VCs
3. Financial professionals seeking market insights
4. Technical enthusiasts interested in advanced AI applications

BRAND VOICE:
- Professional but accessible
- Data-driven and analytical
- Confident without being hyperbolic
- Focus on concrete value proposition
- Technically credible but not overwhelming

CONTENT NEEDED:
1. Homepage hero section (headline, subheadline, and brief value proposition - 100 words max)
2. "How It Works" section explaining our sentiment analysis approach with emphasis on the agentic AI system (200-300 words)
3. Feature descriptions for 3 key features:
   a. Advanced sentiment detection (beyond basic positive/negative classification)
   b. "Hidden alpha" identification through multi-agent analysis
   c. Mobile-first design for on-the-go financial insights
4. About section highlighting technical leadership (200 words) emphasizing my background as Lead Technical Architect at a market-leading management consulting firm
5. FAQ section with 5 questions investors or users might ask
6. "Technical Advantage" section (150 words) explaining how our agentic AI approach offers superior insights

KEY POINTS TO INCLUDE:
- Our unique agentic AI system detects subtle market mood shifts that conventional tools miss
- We identify "hidden alpha" through specialized AI agents that analyze different aspects of financial content
- Mobile-first design for on-the-go financial insights with sophisticated analysis
- Founded by an experienced Lead Technical Architect from a top consulting firm with AI expertise
- Launching on Kickstarter [date]
- The technical architecture leverages multiple specialized AI agents working together to provide deeper insights than single-model approaches

For each section, provide both the content and a brief explanation of why this messaging will resonate with our audience. Format in Markdown for easy integration with our Jekyll site.
```

## Jekyll Implementation with CCA

This prompt will help you build the Jekyll framework for the Sentimark website:

```
As a senior software developer familiar with Jekyll static site generators, please create the foundational files needed for the Sentimark website that will be hosted on Bluehost. I need:

1. The basic Jekyll configuration file (_config.yml) with SEO optimizations
2. A suitable directory structure following Jekyll conventions
3. The homepage template (index.html or index.md) with sections for:
   - Hero (with headline, subheadline, CTA button)
   - How It Works
   - Key Features (3 features)
   - About/Team
   - Newsletter signup
   - Kickstarter campaign info
4. A reusable layout template for content pages (_layouts/default.html)
5. CSS structure (preferably using SCSS with variables for branding)
6. Implementation notes for deploying to Bluehost

Our branding uses the following colors:
- Primary: #2E5BFF (blue)
- Secondary: #8C54FF (purple)
- Accent: #00D1B2 (teal)
- Text: #333333 (dark gray)

Include responsive design considerations for our mobile-focused brand and ensure fast load times. The site should look professional and trustworthy while highlighting our technical capabilities with sentiment analysis and agentic AI.

Please include any necessary HTML, CSS, and Jekyll liquid tag examples for each component, focusing on clean, maintainable code that I can easily expand upon.
```
