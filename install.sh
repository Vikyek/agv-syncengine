#!/usr/bin/env bash
# ==============================================================================
# agv-syncengine Installer & Vault Bootstrapper
# Usage: ./install.sh
# Initializes personal AI Knowledge Vault (~/.gemini/config), installs scripts &
# pre-commit hooks, and creates a private GitHub repository for cross-device sync.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.gemini/config"

cleanup_secrets() {
    unset GITHUB_TOKEN VAULT_PAT GH_TOKEN 2>/dev/null || true
}
trap cleanup_secrets EXIT INT TERM

echo "======================================================================"
echo "⚡ AGV-SyncEngine Bootstrapper"
echo "Target Vault Directory: '${TARGET_DIR}'"
echo "======================================================================"

mkdir -p "${TARGET_DIR}"

# 1. Copy template files to vault directory
echo "📦 Copying engine files to '${TARGET_DIR}'..."
cp -rn "${SCRIPT_DIR}"/scripts "${TARGET_DIR}/" 2>/dev/null || cp -r "${SCRIPT_DIR}"/scripts "${TARGET_DIR}/"
cp -rn "${SCRIPT_DIR}"/hooks "${TARGET_DIR}/" 2>/dev/null || cp -r "${SCRIPT_DIR}"/hooks "${TARGET_DIR}/"
cp -n "${SCRIPT_DIR}"/hooks.json "${TARGET_DIR}/" 2>/dev/null || true
cp -n "${SCRIPT_DIR}"/sync_config_vault.sh "${TARGET_DIR}/" 2>/dev/null || true
cp -n "${SCRIPT_DIR}"/init_vault_sync.sh "${TARGET_DIR}/" 2>/dev/null || true

if [[ ! -f "${TARGET_DIR}/GEMINI.md" ]]; then
    cp "${SCRIPT_DIR}/GEMINI.md" "${TARGET_DIR}/GEMINI.md"
fi
if [[ ! -f "${TARGET_DIR}/AGENTS.md" ]]; then
    cp "${SCRIPT_DIR}/AGENTS.md" "${TARGET_DIR}/AGENTS.md"
fi

chmod +x "${TARGET_DIR}"/scripts/*.py "${TARGET_DIR}"/scripts/*.sh "${TARGET_DIR}"/hooks/*.sh "${TARGET_DIR}"/*.sh 2>/dev/null || true

# 2. Run initialization
echo "🚀 Running vault sync initializer..."
cd "${TARGET_DIR}"

if [[ -f "./init_vault_sync.sh" ]]; then
    chmod +x ./init_vault_sync.sh
    ./init_vault_sync.sh
fi

echo "======================================================================"
echo "✅ AGV-SyncEngine setup complete!"
echo "Your AI Knowledge Vault is active at: ${TARGET_DIR}"
echo "======================================================================"
