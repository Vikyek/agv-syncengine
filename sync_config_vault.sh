#!/usr/bin/env bash
# ==============================================================================
# Gemini Config Vault Sync & Interactive Merge Conflict Resolver
# Usage: ./sync_config_vault.sh
# Synchronizes GEMINI.md, machine profiles, rules, and skills across machines.
# Detects merge conflicts from different machines and resolves them interactively.
# ==============================================================================

set -euo pipefail

VAULT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${VAULT_DIR}/.vault_credentials.env"

cleanup_secrets() {
    unset GITHUB_TOKEN VAULT_PAT GH_TOKEN 2>/dev/null || true
}
trap cleanup_secrets EXIT INT TERM

echo "======================================================================"
echo "🔄 Gemini Config Vault Synchronization Engine"
echo "Directory: '${VAULT_DIR}'"
echo "======================================================================"

cd "${VAULT_DIR}"

GITHUB_USER=""
GITHUB_TOKEN=""
REPO_NAME="agy-syncvault"

# Load saved vault credentials if available
if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${CONFIG_FILE}"
fi

# Override with environment variable if present
if [[ -n "${VAULT_PAT:-${GH_TOKEN:-}}" ]]; then
    GITHUB_TOKEN="${VAULT_PAT:-${GH_TOKEN:-}}"
fi

# Sanitize token to remove trailing Ctrl-C (^C) or control characters
GITHUB_TOKEN="$(echo "${GITHUB_TOKEN:-}" | tr -cd '[:alnum:]_')"

# ------------------------------------------------------------------------------
# MASKED SECRET INPUT (shows * for user typed characters, strips control codes)
# ------------------------------------------------------------------------------
read_secret() {
    local prompt="$1"
    local input=""
    local char=""
    
    tput civis >&2 2>/dev/null || true
    printf "%s" "$prompt" >&2
    
    while IFS= read -r -s -n1 char; do
        if [[ -z "$char" ]]; then
            break
        fi
        if [[ "$char" == $'\x7f' || "$char" == $'\b' ]]; then
            if [[ -n "$input" ]]; then
                input="${input%?}"
                printf "\b \b" >&2
            fi
        else
            input+="$char"
            printf "*" >&2
        fi
    done
    
    tput cnorm >&2 2>/dev/null || true
    echo "" >&2
    echo "${input}" | tr -cd '[:alnum:]_'
}

save_credentials() {
    cat <<EOF > "${CONFIG_FILE}"
GITHUB_USER="${GITHUB_USER}"
GITHUB_TOKEN="${GITHUB_TOKEN}"
REPO_NAME="${REPO_NAME}"
EOF
    chmod 600 "${CONFIG_FILE}"
    echo "💾 Credentials saved to './.vault_credentials.env'."
}

# ------------------------------------------------------------------------------
# USERNAME & TOKEN PROMPTING (Bypasses if already configured)
# ------------------------------------------------------------------------------
prompt_credentials() {
    if [[ -n "${GITHUB_USER:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
        echo "ℹ️  Using saved credentials for GitHub user '${GITHUB_USER}'."
        return 0
    fi

    if [[ -z "${GITHUB_USER:-}" || "${GITHUB_USER}" == "" ]]; then
        read -r -p "👤 Enter your GitHub Username: " GITHUB_USER || GITHUB_USER=""
        if [[ -z "${GITHUB_USER}" ]]; then
            echo "❌ GitHub Username is required!" >&2
            exit 1
        fi
    else
        read -r -p "👤 Enter your GitHub Username [default: ${GITHUB_USER}]: " INPUT_USER || INPUT_USER=""
        if [[ -n "${INPUT_USER}" ]]; then
            GITHUB_USER="${INPUT_USER}"
        fi
    fi

    local saved_token="${GITHUB_TOKEN:-}"
    if [[ -z "${saved_token}" ]]; then
        GITHUB_TOKEN="$(read_secret "🔑 Enter your GitHub Personal Access Token (PAT): ")"
    else
        local typed_token=""
        typed_token="$(read_secret "🔑 Enter your GitHub Personal Access Token (PAT) [default: last token]: ")"
        GITHUB_TOKEN="${typed_token:-$saved_token}"
    fi

    GITHUB_TOKEN="$(echo "${GITHUB_TOKEN}" | tr -cd '[:alnum:]_')"

    if [[ -z "${GITHUB_TOKEN}" ]]; then
        echo "❌ GitHub Personal Access Token is required!" >&2
        exit 1
    fi
    save_credentials
}

prompt_token_retry() {
    local err_msg="$1"
    echo ""
    echo "======================================================================"
    echo "⚠️  GitHub Vault Sync / Push Failure!"
    echo "Details: ${err_msg}"
    echo "======================================================================"
    
    echo "Options:"
    echo "  1) Re-try using last entered token [default: last token]"
    echo "  2) Enter a NEW GitHub Personal Access Token (PAT)"
    echo "  3) Abort sync"
    read -r -p "Select option [1-3] (Default: 2): " RETRY_CHOICE || RETRY_CHOICE="2"
    RETRY_CHOICE="${RETRY_CHOICE:-2}"
    
    case "${RETRY_CHOICE}" in
        1)
            if [[ -z "${GITHUB_TOKEN}" ]]; then
                GITHUB_TOKEN="$(read_secret "🔑 Enter GitHub Personal Access Token (PAT): ")"
                GITHUB_TOKEN="$(echo "${GITHUB_TOKEN}" | tr -cd '[:alnum:]_')"
                save_credentials
            fi
            ;;
        2)
            GITHUB_TOKEN="$(read_secret "🔑 Enter NEW GitHub Personal Access Token (PAT): ")"
            GITHUB_TOKEN="$(echo "${GITHUB_TOKEN}" | tr -cd '[:alnum:]_')"
            if [[ -n "${GITHUB_TOKEN}" ]]; then
                save_credentials
            fi
            ;;
        3)
            echo "❌ Sync aborted by user."
            exit 1
            ;;
        *)
            echo "❌ Invalid choice. Aborting sync."
            exit 1
            ;;
    esac
}

# Ensure origin remote is set
if ! git remote get-url origin &>/dev/null; then
    DEFAULT_REMOTE="https://github.com/<YOUR_USER>/agv-syncvault.git"
    echo "ℹ️  Origin remote not set. Defaulting to '${DEFAULT_REMOTE}'."
    git remote add origin "${DEFAULT_REMOTE}" 2>/dev/null || true
fi

# Synchronize local GEMINI.md with vault copy
if [[ -f "${HOME}/GEMINI.md" ]]; then
    cp -f "${HOME}/GEMINI.md" "${VAULT_DIR}/GEMINI.md"
fi

# ------------------------------------------------------------------------------
# Fetch, Rebase & Push Loop
# ------------------------------------------------------------------------------

if [[ -z "${NO_COLOR:-}" ]]; then
    C_RED="\033[1;31m"
    C_YELLOW="\033[1;33m"
    C_CYAN="\033[1;36m"
    C_BOLD="\033[1m"
    C_RESET="\033[0m"
else
    C_RED=""
    C_YELLOW=""
    C_CYAN=""
    C_BOLD=""
    C_RESET=""
fi

while true; do
    if [[ -n "${GITHUB_USER:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
        REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
        git remote set-url origin "${REMOTE_URL}" 2>/dev/null || git remote add origin "${REMOTE_URL}" 2>/dev/null || true
    fi

    # Commit Local Updates first so pull --rebase works cleanly
    git add .
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        HOSTNAME_STR="$(hostname 2>/dev/null || echo 'machine')"
        git commit -m "Update GEMINI.md & config vault from ${HOSTNAME_STR}: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" --quiet
    fi

    echo "📥 Pulling latest rules from remote config vault..."
    if ! git pull --rebase origin master --quiet 2>/dev/null && ! git pull --rebase origin main --quiet 2>/dev/null; then
        if git status | grep -q "rebase in progress"; then
            echo -e "${C_RED}======================================================================${C_RESET}"
            echo -e "${C_RED}⚠️  MERGE CONFLICT DETECTED across machine-originating rules!${C_RESET}"
            echo -e "${C_RED}======================================================================${C_RESET}"
            echo -e "${C_BOLD}Conflicting configuration files:${C_RESET}"
            git diff --name-only --diff-filter=U | while read -r line; do
                if [[ -n "${line}" ]]; then
                    echo -e "  - ${C_YELLOW}${line}${C_RESET}"
                fi
            done || true
            echo -e "${C_CYAN}----------------------------------------------------------------------${C_RESET}"
            echo -e "${C_BOLD}Choose conflict resolution strategy:${C_RESET}"
            echo -e "  ${C_CYAN}1)${C_RESET} Keep LOCAL machine rules (ours)"
            echo -e "  ${C_CYAN}2)${C_RESET} Accept REMOTE machine rules (theirs)"
            echo -e "  ${C_CYAN}3)${C_RESET} Open editor (micro) to resolve manually"
            read -r -p "$(echo -e "${C_BOLD}Select option [1/2/3]: ${C_RESET}")" CHOICE || CHOICE="1"

            case "${CHOICE}" in
                1)
                    git checkout --ours .
                    git add .
                    git rebase --continue 2>/dev/null || git commit -m "Resolved conflict using local machine rules" --quiet
                    ;;
                2)
                    git checkout --theirs .
                    git add .
                    git rebase --continue 2>/dev/null || git commit -m "Resolved conflict using remote machine rules" --quiet
                    ;;
                3)
                    micro GEMINI.md
                    git add .
                    git rebase --continue 2>/dev/null || git commit -m "Resolved conflict manually via micro" --quiet
                    ;;
                *)
                    echo "❌ Invalid choice! Aborting sync until conflict is manually resolved." >&2
                    exit 1
                    ;;
            esac
            echo "✅ Merge conflict successfully resolved!"
        else
            # Pull failed, check if we should fallback to token authentication
            if [[ -z "${GITHUB_USER:-}" || -z "${GITHUB_TOKEN:-}" ]]; then
                echo "⚠️  Git pull failed. Attempting token authentication..."
                prompt_credentials
                continue
            fi
            echo "❌ Git pull failed. Please verify your connection or repository permissions." >&2
            exit 1
        fi
    fi

    echo "☁️ Pushing updated rules to private GitHub vault..."
    if git push -u origin master --quiet 2>/dev/null || git push -u origin main --quiet 2>/dev/null; then
        echo "======================================================================"
        echo "🎉 Config Vault Sync Completed!"
        echo "======================================================================"
        break
    else
        if [[ -z "${GITHUB_USER:-}" || -z "${GITHUB_TOKEN:-}" ]]; then
            echo "⚠️  Git push failed. Attempting token authentication..."
            prompt_credentials
            continue
        fi
        prompt_token_retry "Git push failed. Token may lack write permissions or repo scope."
    fi
done

# Copy updated master back to home directory
cp -f "${VAULT_DIR}/GEMINI.md" "${HOME}/GEMINI.md"

# Automatically apply the configuration to the local machine
APPLY_SCRIPT="${VAULT_DIR}/scripts/apply_setup.sh"
if [[ -f "${APPLY_SCRIPT}" ]]; then
    echo "🔄 Applying vault configurations to local environment..."
    bash "${APPLY_SCRIPT}"
fi
