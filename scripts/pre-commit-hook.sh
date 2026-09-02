#!/usr/bin/env bash
# pre-commit hook for secret/credential detection
# Installation: cp hooks/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}🔐 Running security audit (pre-commit)...${NC}"

PATTERNS=(
    'BEGIN RSA PRIVATE KEY'
    'BEGIN OPENSSH PRIVATE KEY'
    'BEGIN ENCRYPTED PRIVATE KEY'
    'GITHUB_TOKEN["'\'']?[[:space:]]*=[[:space:]]*["'\''\"][a-zA-Z0-9_-]{20,}'
    'github_token["'\'']?[[:space:]]*=[[:space:]]*["'\''\"][a-zA-Z0-9_-]{20,}'
    'api_key["'\'']?[[:space:]]*=[[:space:]]*["'\''\"][a-zA-Z0-9_-]{20,}'
    'API_KEY["'\'']?[[:space:]]*=[[:space:]]*["'\''\"][a-zA-Z0-9_-]{20,}'
    'AKIA[0-9A-Z]{16}'
    'aws_secret_access_key["'\'']?[[:space:]]*=[[:space:]]*["'\''\"][a-zA-Z0-9_-]{20,}'
    'ghp_[0-9a-zA-Z]{36}'
    'github_pat_'
    'xox[baprs]-'
    'AIzaSy'
)

FOUND_SECRETS=0
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM || true)

[[ -z "$STAGED_FILES" ]] && echo -e "${GREEN}✅ No files staged${NC}" && exit 0

while IFS= read -r file; do
    [[ "$file" == *.lock || "$file" == .git* || "$file" == *pre-commit* ]] && continue
    STAGED_CONTENT=$(git show ":$file" 2>/dev/null || echo "")
    for pattern in "${PATTERNS[@]}"; do
        if echo "$STAGED_CONTENT" | grep -qE "$pattern"; then
            echo -e "${RED}🚨 BLOCKED: Found '$pattern' in: $file${NC}"
            FOUND_SECRETS=$((FOUND_SECRETS + 1))
        fi
    done
done <<< "$STAGED_FILES"

[[ $FOUND_SECRETS -gt 0 ]] && echo -e "${RED}❌ COMMIT BLOCKED${NC}" && exit 1
echo -e "${GREEN}✅ Security audit passed${NC}"
exit 0
