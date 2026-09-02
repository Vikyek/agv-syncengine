#!/usr/bin/env bash
# ==============================================================================
# Initializer & First Sync Runner for Gemini Config Vault
# Usage: ./init_vault_sync.sh
# Autonomously creates the private GitHub repository 'agy-syncvault',
# initializes local Git repository, stages rules/configs, and performs first sync.
# ==============================================================================

set -euo pipefail

VAULT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${VAULT_DIR}/.vault_credentials.env"

cleanup_secrets() {
    unset GITHUB_TOKEN VAULT_PAT GH_TOKEN 2>/dev/null || true
}
trap cleanup_secrets EXIT INT TERM

echo "======================================================================"
echo "🚀 Initializing Gemini Config Vault Project Repo"
echo "Vault Directory: '${VAULT_DIR}'"
echo "======================================================================"

cd "${VAULT_DIR}"

if [[ -d "${VAULT_DIR}/.git" ]]; then
    echo "⚠️  Vault directory already contains a .git repository."
    read -r -p "Are you sure you want to re-initialize and potentially overwrite settings? (y/N) " CONFIRM_INIT
    if [[ ! "${CONFIRM_INIT}" =~ ^[Yy]$ ]]; then
        echo "❌ Initialization aborted by user."
        exit 0
    fi
fi

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
    echo "⚠️  GitHub API / Authentication Failure!"
    echo "Details: ${err_msg}"
    echo "======================================================================"
    
    echo "Options:"
    echo "  1) Re-try using last entered token [default: last token]"
    echo "  2) Enter a NEW GitHub Personal Access Token (PAT)"
    echo "  3) Abort setup"
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
            echo "❌ Setup aborted by user."
            exit 1
            ;;
        *)
            echo "❌ Invalid choice. Aborting setup."
            exit 1
            ;;
    esac
}

prompt_credentials

# ------------------------------------------------------------------------------
# STEP 1: Autonomously Create Private GitHub Repository & Retry Loop
# ------------------------------------------------------------------------------
while true; do
    echo "☁️ Creating private GitHub repository: '${GITHUB_USER}/${REPO_NAME}'..."

    CREATE_RESP="$(curl -s -w "\n%{http_code}" -H "Authorization: token ${GITHUB_TOKEN}" \
         -d "{\"name\":\"${REPO_NAME}\",\"private\":true,\"description\":\"Private configuration vault for Gemini & Antigravity rules across machines\"}" \
         "https://api.github.com/user/repos")"

    HTTP_CODE="$(echo "${CREATE_RESP}" | tail -n 1)"
    BODY="$(echo "${CREATE_RESP}" | sed '$d')"

    if [[ "${HTTP_CODE}" == "201" ]]; then
        echo "✅ Private GitHub repository '${REPO_NAME}' created successfully."
        break
    elif [[ "${HTTP_CODE}" == "422" ]]; then
        echo "ℹ️ Private GitHub repository '${REPO_NAME}' already exists on GitHub."
        break
    else
        prompt_token_retry "HTTP ${HTTP_CODE} - ${BODY}"
    fi
done

# ------------------------------------------------------------------------------
# STEP 2: Initialize Git Repository & Remote Setup
# ------------------------------------------------------------------------------
if [[ ! -d "${VAULT_DIR}/.git" ]]; then
    git init --quiet
fi

# Integrate existing local config files and symlink config directory
ACTIVE_CONFIG="${HOME}/.gemini/config"
if [[ -d "${ACTIVE_CONFIG}" && ! -L "${ACTIVE_CONFIG}" ]]; then
    echo "🔄 Active local config directory found at '${ACTIVE_CONFIG}'."
    echo "📦 Integrating existing projects, plugins, and custom settings into the vault..."
    
    # Merge projects
    mkdir -p "${VAULT_DIR}/projects"
    if [[ -d "${ACTIVE_CONFIG}/projects" ]]; then
        cp -n "${ACTIVE_CONFIG}/projects"/*.json "${VAULT_DIR}/projects/" 2>/dev/null || true
    fi
    
    # Merge plugins
    mkdir -p "${VAULT_DIR}/plugins"
    if [[ -d "${ACTIVE_CONFIG}/plugins" ]]; then
        cp -as "${ACTIVE_CONFIG}/plugins"/* "${VAULT_DIR}/plugins/" 2>/dev/null || true
    fi
    
    # Backup active configuration
    mv "${ACTIVE_CONFIG}" "${ACTIVE_CONFIG}.bak"
    ln -s "${VAULT_DIR}" "${ACTIVE_CONFIG}"
    echo "✅ Replaced active config with vault symlink and backed up old files to '${ACTIVE_CONFIG}.bak'."
elif [[ ! -e "${ACTIVE_CONFIG}" ]]; then
    mkdir -p "$(dirname "${ACTIVE_CONFIG}")"
    ln -s "${VAULT_DIR}" "${ACTIVE_CONFIG}"
    echo "✅ Created vault symlink at '${ACTIVE_CONFIG}'."
fi

if [[ -f "${HOME}/GEMINI.md" ]]; then
    cp -f "${HOME}/GEMINI.md" "${VAULT_DIR}/GEMINI.md"
fi

# ------------------------------------------------------------------------------
# STEP 3: Stage, Commit & Push to Remote with Retry Loop
# ------------------------------------------------------------------------------
while true; do
    REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${REPO_NAME}.git"
    git remote set-url origin "${REMOTE_URL}" 2>/dev/null || git remote add origin "${REMOTE_URL}"

    echo "📦 Staging vault configuration files..."
    git add .gitignore GEMINI.md README.md init_vault_sync.sh sync_config_vault.sh machines/ rules/ skills/ 2>/dev/null || git add .

    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        HOSTNAME_STR="$(hostname 2>/dev/null || echo 'machine')"
        git commit -m "Initial sync of Gemini config vault from ${HOSTNAME_STR}: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" --quiet
    fi

    echo "⬆️ Executing private sync push to GitHub..."
    git branch -M master 2>/dev/null || true

    if git push -u origin master --quiet 2>/dev/null || git push -u origin main --quiet 2>/dev/null; then
        echo "======================================================================"
        echo "🎉 Private Vault Sync Complete!"
        echo "👉 Remote Private Vault: https://github.com/${GITHUB_USER}/${REPO_NAME}"
        echo "======================================================================"
        break
    else
        prompt_token_retry "Git push failed. Token may lack 'repo' scope or write permissions."
    fi
done

# Automatically apply the configuration to the local machine
APPLY_SCRIPT="${VAULT_DIR}/scripts/apply_setup.sh"
if [[ -f "${APPLY_SCRIPT}" ]]; then
    echo "🔄 Applying vault configurations to local environment..."
    bash "${APPLY_SCRIPT}"
fi
