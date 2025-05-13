# Sentimark Website

This repository contains the Jekyll-based website for Sentimark, a financial sentiment analysis platform. The website is designed to be hosted on Bluehost and serves as the main marketing platform for our Kickstarter campaign and product information.

## Project Overview

The Sentimark website is built using Jekyll, a static site generator that allows for easy content management through Markdown files while providing the performance benefits of static HTML. The site follows a responsive, mobile-first design approach and incorporates our brand colors:

- Primary: #2E5BFF (blue)
- Secondary: #8C54FF (purple)
- Accent: #00D1B2 (teal)
- Text: #333333 (dark gray)

## Directory Structure

The website follows Jekyll's standard directory structure with some customizations:

```
sentimark-website/
├── _config.yml                  # Jekyll configuration
├── _data/                       # Data files
├── _includes/                   # Reusable components
│   ├── header.html              # Site header
│   ├── footer.html              # Site footer
│   ├── newsletter-signup.html   # Mailchimp signup form
│   └── social-links.html        # Social media links
├── _layouts/                    # Layout templates
│   ├── default.html             # Main layout template
│   ├── page.html                # Page layout
│   ├── post.html                # Blog post layout
│   └── home.html                # Homepage layout
├── _posts/                      # Blog posts
├── _sass/                       # SCSS files
│   ├── _variables.scss          # Color and sizing variables
│   ├── _base.scss               # Base styles
│   ├── _layout.scss             # Layout styles
│   └── _components.scss         # Component styles
├── assets/                      # Static assets
│   ├── css/
│   │   └── main.scss            # Main CSS file
│   ├── js/
│   │   └── main.js              # JavaScript functionality
│   └── images/
│       └── placeholders/        # Placeholder images
├── pages/                       # Content pages
├── .gitignore                   # Git ignore file
├── Gemfile                      # Ruby dependencies
├── _config.yml                  # Jekyll configuration
├── index.html                   # Homepage
└── README.md                    # This file
```

## Local Development Environment Setup in WSL

### Prerequisites

- Windows 10/11 with WSL2 installed
- Ubuntu 20.04 or newer on WSL
- Ruby 2.7 or newer
- RubyGems
- GCC and Make
- Bundler

### WSL Jekyll Setup

Follow these steps to set up the development environment in WSL:

1. Update package lists and install dependencies:
   ```bash
   sudo apt update
   sudo apt install ruby-full build-essential zlib1g-dev
   ```

2. Configure Ruby gems to install to your user account:
   ```bash
   echo '# Install Ruby Gems to ~/gems' >> ~/.bashrc
   echo 'export GEM_HOME="$HOME/gems"' >> ~/.bashrc
   echo 'export PATH="$HOME/gems/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. Install Jekyll and Bundler:
   ```bash
   gem install jekyll bundler
   ```

4. Verify Jekyll installation:
   ```bash
   jekyll -v
   ```

### Running the Development Server

To run the local development server:

1. Navigate to the website directory:
   ```bash
   cd /path/to/sentimark/ui/website
   ```

2. Install project dependencies:
   ```bash
   bundle install
   ```

3. Start the Jekyll development server:
   ```bash
   bundle exec jekyll serve --livereload --host=0.0.0.0
   ```

4. Access the website in your browser:
   - Local: `http://localhost:4000`
   - From Windows: `http://<WSL-IP>:4000`

To find your WSL IP address:
```bash
ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
```

## Testing Procedure

### Responsive Testing

1. Use Chrome DevTools responsive design mode to test different screen sizes
2. Verify breakpoints work correctly at the following widths:
   - Mobile: 576px and below
   - Tablet: 768px
   - Desktop: 992px
   - Large Desktop: 1200px and above

### Browser Compatibility

Test the website in the following browsers:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### Performance Testing

1. Run Lighthouse in Chrome DevTools:
   - Aim for scores above 90 for Performance, Accessibility, Best Practices, and SEO
   - Address any critical issues identified

2. Run WebPageTest.org to check loading performance:
   - Target First Contentful Paint under 1.5s
   - Target Total Blocking Time under 200ms

## Bluehost Deployment Process

### Prerequisites

- Bluehost account with SFTP access credentials
- `lftp` installed on your WSL environment (`sudo apt install lftp`)

### Deployment Script

We've created a deployment script (`deploy.sh`) to automate the process of building and deploying the website to Bluehost:

```bash
#!/bin/bash
# Script for deploying the Jekyll site to Bluehost

set -e

# Configuration
SITE_DIR="ui/website"
BUILD_DIR="_site"
FTP_HOST="ftp.sentimark.com"
FTP_USER=$(cat .secrets/ftp_user 2>/dev/null || echo "")
FTP_PASS=$(cat .secrets/ftp_pass 2>/dev/null || echo "")
REMOTE_DIR="/public_html"

# Check if credentials are available
if [ -z "$FTP_USER" ] || [ -z "$FTP_PASS" ]; then
  echo "Error: FTP credentials not found"
  echo "Please create .secrets/ftp_user and .secrets/ftp_pass files with your Bluehost FTP credentials"
  exit 1
fi

# Function for logging
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

# Build the site
log "Building Jekyll site..."
cd $SITE_DIR
bundle install
JEKYLL_ENV=production bundle exec jekyll build
cd -

# Deploy via FTP
log "Deploying to Bluehost..."
cd "$SITE_DIR/$BUILD_DIR"

# Create a temporary lftp script
LFTP_SCRIPT=$(mktemp)
cat > $LFTP_SCRIPT << EOF
open -u $FTP_USER,$FTP_PASS $FTP_HOST
lcd .
cd $REMOTE_DIR
# mirror with only newer files
mirror -R --only-newer .
bye
EOF

# Execute the lftp script
lftp -f $LFTP_SCRIPT

# Clean up
rm $LFTP_SCRIPT

log "Deployment completed successfully!"

# Verify deployment
log "Verifying deployment..."
curl -s -o /dev/null -w "%{http_code}" https://sentimark.com/
if [ $? -eq 0 ]; then
  log "Verification successful: Site is accessible"
else
  log "Warning: Site verification failed. Please check manually."
fi
```

### Secrets Management

1. Create a directory for secrets (do not commit to Git):
   ```bash
   mkdir -p .secrets
   chmod 700 .secrets
   ```

2. Add your credentials (never commit these to Git):
   ```bash
   echo "your_username" > .secrets/ftp_user
   echo "your_password" > .secrets/ftp_pass
   chmod 600 .secrets/ftp_user
   chmod 600 .secrets/ftp_pass
   ```

3. Add the secrets directory to `.gitignore`:
   ```
   # Secrets
   .secrets/
   ```

### Manual Deployment Steps

If you need to deploy manually:

1. Build the site:
   ```bash
   cd ui/website
   JEKYLL_ENV=production bundle exec jekyll build
   ```

2. Upload the contents of the `_site` directory to your Bluehost public_html folder using SFTP

### Post-Deployment Verification

After deployment, verify:
1. The website loads correctly at your domain
2. All links and navigation work
3. Images and assets load properly
4. Forms function as expected

## Content Management

### Adding Blog Posts

1. Create a new Markdown file in the `_posts` directory with the naming format: `YYYY-MM-DD-title.md`
2. Add front matter at the top of the file:
   ```yaml
   ---
   layout: post
   title: "Your Post Title"
   date: YYYY-MM-DD HH:MM:SS -0700
   author: Author Name
   categories: [category1, category2]
   tags: [tag1, tag2]
   ---
   ```
3. Add your content in Markdown format below the front matter

### Modifying Pages

Main site pages are located in the `pages` directory. To modify them:

1. Open the desired page (HTML file) in your editor
2. Update the content, preserving the front matter at the top
3. For major layout changes, check the corresponding templates in `_layouts`

## Customization

### Changing Colors

Brand colors can be modified in `_sass/_variables.scss`.

### Updating Images

Replace placeholder images in the `assets/images/placeholders` directory with actual images. Be sure to maintain the same file names or update the references in the HTML files.

### Modifying Styles

The CSS is organized using SCSS:
- `_variables.scss`: Color variables and basic settings
- `_base.scss`: Global base styles
- `_layout.scss`: Layout structures
- `_components.scss`: Individual UI components

## License

This project is proprietary and confidential. Unauthorized copying, transfer, or reproduction of the contents is strictly prohibited.

## Contact

For any questions regarding the website, please contact the development team.
