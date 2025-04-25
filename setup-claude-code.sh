#!/bin/bash

# Claude Code Setup Script
# This script ensures that claude-code commands are available in your PATH

# Print with colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Claude Code Path Setup ===${NC}"
echo "This script will configure your system to run Claude Code commands."

# Step 1: Check if Claude Code is installed
echo -e "\n${YELLOW}Checking if Claude Code is installed...${NC}"
CLAUDE_INSTALLED=$(npm list -g | grep "claude-code")

if [ -z "$CLAUDE_INSTALLED" ]; then
    echo -e "${RED}Claude Code doesn't appear to be installed globally.${NC}"
    read -p "Would you like to install it now? (y/n): " INSTALL_CHOICE
    
    if [[ $INSTALL_CHOICE == "y" || $INSTALL_CHOICE == "Y" ]]; then
        echo "Installing Claude Code globally..."
        npm install -g @anthropic-ai/claude-code
        
        # Check if installation was successful
        if [ $? -ne 0 ]; then
            echo -e "${RED}Installation failed. Please check npm logs for details.${NC}"
            exit 1
        fi
        echo -e "${GREEN}Claude Code installed successfully!${NC}"
    else
        echo "Skipping installation."
    fi
else
    echo -e "${GREEN}Claude Code is installed: $CLAUDE_INSTALLED${NC}"
fi

# Step 2: Find npm global bin directory
echo -e "\n${YELLOW}Locating npm global bin directory...${NC}"
NPM_PREFIX=$(npm config get prefix)
NPM_BIN="$NPM_PREFIX/bin"

echo "npm global bin directory: $NPM_BIN"

# Step 3: Check if directory exists and contains Claude executables
if [ ! -d "$NPM_BIN" ]; then
    echo -e "${RED}npm bin directory doesn't exist: $NPM_BIN${NC}"
    exit 1
fi

echo "Checking for Claude executables in $NPM_BIN:"
CLAUDE_EXECS=$(ls -la $NPM_BIN | grep -E "claude|claude-code")
echo "$CLAUDE_EXECS"

# Step 4: Check if npm bin directory is in PATH
echo -e "\n${YELLOW}Checking if npm bin directory is in PATH...${NC}"
if [[ ":$PATH:" == *":$NPM_BIN:"* ]]; then
    echo -e "${GREEN}$NPM_BIN is already in your PATH.${NC}"
    NPM_IN_PATH=true
else
    echo -e "${RED}$NPM_BIN is NOT in your PATH.${NC}"
    NPM_IN_PATH=false
    
    # Ask if user wants to add it to PATH
    read -p "Would you like to add it to your PATH in ~/.bashrc? (y/n): " ADD_PATH_CHOICE
    
    if [[ $ADD_PATH_CHOICE == "y" || $ADD_PATH_CHOICE == "Y" ]]; then
        echo -e "\nexport PATH=\"$NPM_BIN:\$PATH\"" >> ~/.bashrc
        echo -e "${GREEN}Added to ~/.bashrc${NC}"
        echo "You'll need to run 'source ~/.bashrc' or restart your terminal for this to take effect."
        
        # Also export it for current session
        export PATH="$NPM_BIN:$PATH"
        echo "Also exported for current session."
    fi
fi

# Step 5: Create symbolic links as a backup solution
echo -e "\n${YELLOW}Setting up symbolic links to /usr/local/bin/ as a backup...${NC}"

# Check if we have sudo rights
if command -v sudo >/dev/null 2>&1; then
    HAS_SUDO=true
else
    HAS_SUDO=false
    echo -e "${RED}sudo is not available. Skipping symbolic link creation.${NC}"
fi

if [ "$HAS_SUDO" = true ]; then
    # Check for claude executable
    if [ -f "$NPM_BIN/claude" ]; then
        sudo ln -sf "$NPM_BIN/claude" /usr/local/bin/claude
        echo -e "${GREEN}Created symbolic link for claude in /usr/local/bin/claude${NC}"
    else
        echo -e "${RED}claude executable not found in $NPM_BIN${NC}"
    fi
    
    # Check for claude-code executable
    if [ -f "$NPM_BIN/claude-code" ]; then
        sudo ln -sf "$NPM_BIN/claude-code" /usr/local/bin/claude-code
        echo -e "${GREEN}Created symbolic link for claude-code in /usr/local/bin/claude-code${NC}"
    else
        echo -e "${YELLOW}Note: claude-code executable not found in $NPM_BIN${NC}"
        echo "Claude Code might be using 'claude' as the main executable."
    fi
fi

# Step 6: Test if commands work
echo -e "\n${YELLOW}Testing claude command...${NC}"
if command -v claude >/dev/null 2>&1; then
    echo -e "${GREEN}claude command is now available!${NC}"
    CLAUDE_WORKS=true
else
    echo -e "${RED}claude command is still not available.${NC}"
    CLAUDE_WORKS=false
fi

if command -v claude-code >/dev/null 2>&1; then
    echo -e "${GREEN}claude-code command is now available!${NC}"
    CLAUDE_CODE_WORKS=true
else
    echo -e "${YELLOW}claude-code command is not available.${NC}"
    echo "This is okay if Claude Code uses 'claude' as the main executable."
    CLAUDE_CODE_WORKS=false
fi

# Step 7: Final instructions
echo -e "\n${YELLOW}=== Final Instructions ===${NC}"

if [ "$NPM_IN_PATH" = false ]; then
    echo -e "1. Run the following command to update your current terminal session:"
    echo -e "   ${GREEN}source ~/.bashrc${NC}"
fi

if [ "$CLAUDE_WORKS" = false ] && [ "$CLAUDE_CODE_WORKS" = false ]; then
    echo "2. You can try running Claude Code using the full path:"
    echo -e "   ${GREEN}$NPM_BIN/claude${NC}"
    
    echo "3. Alternative installation methods:"
    echo "   a. Reinstall Claude Code: npm uninstall -g @anthropic-ai/claude-code && npm install -g @anthropic-ai/claude-code"
    echo "   b. Check the Anthropic documentation for specific instructions for your system"
else
    echo "You should now be able to use Claude Code! Navigate to your project directory and run:"
    echo -e "   ${GREEN}claude${NC}"
fi

echo -e "\n${GREEN}Setup completed!${NC}"
