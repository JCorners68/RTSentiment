#!/bin/bash
# Script to fix common SASS deprecation warnings in Jekyll

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Fixing SASS deprecation warnings...${NC}"

# Function to backup a file before modifying it
backup_file() {
    local file="$1"
    local backup="${file}.bak"
    
    if [[ ! -f "$backup" ]]; then
        echo -e "${YELLOW}Creating backup of ${file}${NC}"
        cp "$file" "$backup"
    fi
}

# Replace deprecated lighten/darken functions with color.scale
fix_lighten_darken() {
    local sass_files=()
    
    # Find all SASS files that use lighten or darken
    echo -e "${YELLOW}Finding SASS files with deprecated lighten/darken functions...${NC}"
    while IFS= read -r file; do
        sass_files+=("$file")
    done < <(grep -l -r "lighten\|darken" --include="*.scss" . || true)
    
    if [[ ${#sass_files[@]} -eq 0 ]]; then
        echo -e "${GREEN}No files with lighten/darken functions found.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found ${#sass_files[@]} files with deprecated functions.${NC}"
    
    for file in "${sass_files[@]}"; do
        echo -e "${YELLOW}Processing ${file}...${NC}"
        backup_file "$file"
        
        # Replace lighten($color, $amount) with color.scale($color, $lightness: $amount)
        sed -i 's/lighten(\([^,]*\), \([^)]*\))/color.scale(\1, $lightness: \2)/g' "$file"
        
        # Replace darken($color, $amount) with color.scale($color, $lightness: -$amount)
        sed -i 's/darken(\([^,]*\), \([^)]*\))/color.scale(\1, $lightness: -\2)/g' "$file"
        
        echo -e "${GREEN}Fixed ${file}${NC}"
    done
}

# Replace deprecated transparentize function with color.adjust
fix_transparentize() {
    local sass_files=()
    
    # Find all SASS files that use transparentize or fade-out
    echo -e "${YELLOW}Finding SASS files with deprecated transparentize/fade-out functions...${NC}"
    while IFS= read -r file; do
        sass_files+=("$file")
    done < <(grep -l -r "transparentize\|fade-out" --include="*.scss" . || true)
    
    if [[ ${#sass_files[@]} -eq 0 ]]; then
        echo -e "${GREEN}No files with transparentize/fade-out functions found.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found ${#sass_files[@]} files with deprecated functions.${NC}"
    
    for file in "${sass_files[@]}"; do
        echo -e "${YELLOW}Processing ${file}...${NC}"
        backup_file "$file"
        
        # Replace transparentize($color, $amount) with color.adjust($color, $alpha: -$amount)
        sed -i 's/transparentize(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: -\2)/g' "$file"
        
        # Replace fade-out($color, $amount) with color.adjust($color, $alpha: -$amount)
        sed -i 's/fade-out(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: -\2)/g' "$file"
        
        echo -e "${GREEN}Fixed ${file}${NC}"
    done
}

# Replace deprecated opacify function with color.adjust
fix_opacify() {
    local sass_files=()
    
    # Find all SASS files that use opacify or fade-in
    echo -e "${YELLOW}Finding SASS files with deprecated opacify/fade-in functions...${NC}"
    while IFS= read -r file; do
        sass_files+=("$file")
    done < <(grep -l -r "opacify\|fade-in" --include="*.scss" . || true)
    
    if [[ ${#sass_files[@]} -eq 0 ]]; then
        echo -e "${GREEN}No files with opacify/fade-in functions found.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found ${#sass_files[@]} files with deprecated functions.${NC}"
    
    for file in "${sass_files[@]}"; do
        echo -e "${YELLOW}Processing ${file}...${NC}"
        backup_file "$file"
        
        # Replace opacify($color, $amount) with color.adjust($color, $alpha: $amount)
        sed -i 's/opacify(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: \2)/g' "$file"
        
        # Replace fade-in($color, $amount) with color.adjust($color, $alpha: $amount)
        sed -i 's/fade-in(\([^,]*\), \([^)]*\))/color.adjust(\1, $alpha: \2)/g' "$file"
        
        echo -e "${GREEN}Fixed ${file}${NC}"
    done
}

# Add @use "sass:color"; to the beginning of files that need it
add_sass_color_module() {
    local sass_files=()
    
    # Find all SASS files that use color functions
    echo -e "${YELLOW}Finding SASS files that need sass:color module...${NC}"
    while IFS= read -r file; do
        sass_files+=("$file")
    done < <(grep -l -r "color\.scale\|color\.adjust" --include="*.scss" . || true)
    
    if [[ ${#sass_files[@]} -eq 0 ]]; then
        echo -e "${GREEN}No files need sass:color module.${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found ${#sass_files[@]} files that need sass:color module.${NC}"
    
    for file in "${sass_files[@]}"; do
        echo -e "${YELLOW}Processing ${file}...${NC}"
        backup_file "$file"
        
        # Check if sass:color is already imported
        if ! grep -q "@use \"sass:color\";" "$file"; then
            # Add import at the beginning of the file
            sed -i '1i @use "sass:color";' "$file"
            echo -e "${GREEN}Added sass:color module to ${file}${NC}"
        else
            echo -e "${GREEN}sass:color module already present in ${file}${NC}"
        fi
    done
}

# Run all fixes
fix_lighten_darken
fix_transparentize
fix_opacify
add_sass_color_module

echo -e "${GREEN}SASS deprecation fixes completed!${NC}"
echo -e "${YELLOW}You may need to restart your Jekyll server for changes to take effect.${NC}"