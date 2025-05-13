#!/bin/bash
# install_helm_hooks.sh
# Script to install Git hooks for validating Helm charts

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPTS_DIR="$REPO_ROOT/scripts"
HELM_VALIDATION_SCRIPT="$SCRIPTS_DIR/validate_securitycontext.sh"

echo -e "${YELLOW}Installing Git hooks for Helm chart validation...${NC}"

# Create pre-commit hook file
PRE_COMMIT_HOOK="$HOOKS_DIR/pre-commit"

cat > "$PRE_COMMIT_HOOK" << 'EOF'
#!/bin/bash

# Get the list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR | grep "infrastructure/helm/.*\.yaml$" || true)

# Exit early if there are no Helm files to check
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

REPO_ROOT=$(git rev-parse --show-toplevel)
VALIDATION_SCRIPT="$REPO_ROOT/scripts/validate_securitycontext.sh"

echo "Running Helm chart validation..."
if [ -x "$VALIDATION_SCRIPT" ]; then
    # Run the validation script
    $VALIDATION_SCRIPT
    VALIDATION_EXIT_CODE=$?
    
    if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
        echo "❌ Helm chart validation failed! Please fix the issues before committing."
        exit 1
    else
        echo "✅ Helm chart validation passed!"
    fi
else
    echo "⚠️ Validation script not found or not executable: $VALIDATION_SCRIPT"
    exit 1
fi

# Helm lint check
cd "$REPO_ROOT/infrastructure/helm/sentimark-services"
helm lint .
HELM_LINT_EXIT_CODE=$?

if [ $HELM_LINT_EXIT_CODE -ne 0 ]; then
    echo "❌ helm lint failed! Please fix the issues before committing."
    exit 1
else
    echo "✅ helm lint passed!"
fi

exit 0
EOF

# Make the hook executable
chmod +x "$PRE_COMMIT_HOOK"

# Make sure the validation script is executable
chmod +x "$HELM_VALIDATION_SCRIPT"

echo -e "${GREEN}Git hooks installed successfully!${NC}"
echo -e "Helm charts will be validated before each commit."