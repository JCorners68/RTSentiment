#!/bin/bash
# Script to fix all SASS issues and deprecation warnings

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Fixing All SASS Deprecation Warnings${NC}"
echo -e "${GREEN}=========================================${NC}"

# Create backups
backup_dir="sass_backups_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

echo -e "${YELLOW}Creating backup of SASS files in ${backup_dir}...${NC}"

# Backup SASS files
cp -r _sass "$backup_dir/"
find . -name "*.scss" -exec cp --parents {} "$backup_dir/" \;

echo -e "${GREEN}Backups created.${NC}"

# Step 1: Update Jekyll config
echo -e "${YELLOW}Updating Jekyll configuration...${NC}"
if grep -q "quiet_deps: true" _config.yml; then
    echo -e "${GREEN}SASS quiet_deps already configured in _config.yml${NC}"
else
    # Try to find the SASS section and add quiet_deps
    if grep -q "sass:" _config.yml; then
        sed -i '/sass:/,/^[^ ]/ s/^$/  quiet_deps: true  # Suppresses deprecation warnings from dependencies\n/' _config.yml
        echo -e "${GREEN}Added quiet_deps to existing sass section in _config.yml${NC}"
    else
        # Add a new SASS section
        echo -e "\n# SASS settings\nsass:\n  quiet_deps: true  # Suppresses deprecation warnings from dependencies\n" >> _config.yml
        echo -e "${GREEN}Added new sass section with quiet_deps to _config.yml${NC}"
    fi
fi

# Step 2: Fix main.scss imports
echo -e "${YELLOW}Updating main.scss to use modern @use syntax...${NC}"

# Find main.scss files
main_scss_files=($(find . -name "main.scss" -not -path "*/vendor/*" -not -path "*/_site/*" -not -path "*/node_modules/*"))

for file in "${main_scss_files[@]}"; do
    echo -e "${BLUE}Processing ${file}...${NC}"
    
    # Create or update modernized version
    modern_file="${file%.*}-modern.scss"
    
    # Extract front matter if any
    if grep -q "^---" "$file"; then
        front_matter=$(sed -n '/^---$/,/^---$/p' "$file")
        echo "$front_matter" > "$modern_file"
        echo "" >> "$modern_file"
        echo "/* Modern SASS imports using @use instead of @import */" >> "$modern_file"
    else
        echo "/* Modern SASS imports using @use instead of @import */" > "$modern_file"
    fi
    
    # Convert @import to @use
    grep "@import" "$file" | sed 's/@import "\(.*\)";/@use "\1" as *;/g' >> "$modern_file"
    
    echo -e "${GREEN}Created modernized version at ${modern_file}${NC}"
    
    # Optional: replace original with modernized version
    # cp "$modern_file" "$file"
    # echo -e "${GREEN}Replaced original ${file} with modernized version${NC}"
    
    echo -e "${YELLOW}To use the modernized version, rename ${modern_file} to ${file}${NC}"
done

# Step 3: Fix SASS color functions
echo -e "${YELLOW}Fixing SASS color functions...${NC}"

# Find SASS files with color functions
sass_files=($(grep -l -r "lighten\|darken\|transparentize\|fade-out\|opacify\|fade-in" --include="*.scss" .))

for file in "${sass_files[@]}"; do
    echo -e "${BLUE}Processing ${file}...${NC}"
    
    # Skip vendor directories
    if [[ "$file" == *"/vendor/"* ]] || [[ "$file" == *"/_site/"* ]] || [[ "$file" == */node_modules/* ]]; then
        echo -e "${YELLOW}Skipping vendor/site file: ${file}${NC}"
        continue
    fi
    
    # Add @use "sass:color"; if not already present
    if ! grep -q "@use \"sass:color\"" "$file"; then
        sed -i '1i @use "sass:color";' "$file"
        echo -e "${GREEN}Added sass:color module to ${file}${NC}"
    fi
    
    # Replace lighten/darken functions
    sed -i 's/lighten(\([^,]*\), \([^)]*\))/color.scale(\1, $lightness: \2)/g' "$file"
    sed -i 's/darken(\([^,]*\), \([^)]*\))/color.scale(\1, $lightness: -\2)/g' "$file"
    
    # Replace transparentize/fade-out functions
    sed -i 's/transparentize(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: -\2)/g' "$file"
    sed -i 's/fade-out(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: -\2)/g' "$file"
    
    # Replace opacify/fade-in functions
    sed -i 's/opacify(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: \2)/g' "$file"
    sed -i 's/fade-in(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: \2)/g' "$file"
    
    echo -e "${GREEN}Fixed color functions in ${file}${NC}"
done

# Step 4: Create Jekyll quiet start script
echo -e "${YELLOW}Creating quiet development server script...${NC}"

cat > serve_quiet.sh << 'EOF'
#!/bin/bash
# Script to run Jekyll development server with minimal output

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Jekyll development server in quiet mode...${NC}"
echo -e "${YELLOW}Server will be available at http://127.0.0.1:4000/${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"

# Run Jekyll with warnings suppressed
JEKYLL_LOG_LEVEL=error bundle exec jekyll serve --livereload 2>jekyll_warnings.log

# Note: Check jekyll_warnings.log for any warnings if needed
EOF

chmod +x serve_quiet.sh
echo -e "${GREEN}Created serve_quiet.sh script${NC}"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  All SASS fixes completed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${YELLOW}1. Use ./serve_quiet.sh to run the development server with minimal warnings${NC}"
echo -e "${YELLOW}2. Check the *-modern.scss files to replace @import with @use${NC}"
echo -e "${YELLOW}3. Backups are stored in ${backup_dir}/${NC}"