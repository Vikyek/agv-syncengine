# AGV-SyncEngine ⚡

**AGV-SyncEngine** is a lightweight, self-contained template framework and knowledge engine for managing multi-device AI agent configurations, rule enforcement, token optimizations, rule poisoning defense, and automated cross-machine synchronization.

Derived from `agv-syncvault`, `agv-syncengine` comes scrubbed of personal user data and pre-packaged with the **Standard Dev Pack** baseline rules for AI coding assistants (Antigravity, Gemini, Claude, Cursor, Aider).

---

## 🚀 Features

- **Automated Private Vault Sync**: Synchronizes system rules (`GEMINI.md`, `AGENTS.md`), skills, and configuration files across multiple machines using git rebase/push workflows.
- **Rule Injection Defense**: Automated pre-commit & pre-invocation scanner (`scan_rules.py`) detecting prompt poisoning, credential exfiltration, and malicious instruction injections.
- **`tokless` Token Savings**: Integrated rules and hooks for pre-indexing repositories (`codegraph`) and utilizing context sandboxes (`context-mode`).
- **Standard Dev Rules**: Out-of-the-box support for:
  - Thinking before coding & goal-driven loops.
  - Caveman concise response style.
  - Ponytail lazy-developer build discipline (reuse before writing).
  - Secret isolation & exit trap security invariants.
- **Interactive Installer**: Self-contained `install.sh` that sets up `~/.gemini/config` and provisions a **Private** remote GitHub vault repository.

---

## 🛠️ Quick Start

```bash
# 1. Clone agv-syncengine
git clone https://github.com/Vikyek/agv-syncengine.git
cd agv-syncengine

# 2. Run the installer
./install.sh
```

---

## 📁 Repository Structure

```
agv-syncengine/
├── GEMINI.md             # Standard Dev Pack universal agent rules template
├── AGENTS.md             # Baseline agent instructions manifest
├── install.sh            # Automated installer & vault bootstrapper
├── init_vault_sync.sh    # Initializer for private GitHub vault creation
├── sync_config_vault.sh  # Multi-device rule sync & conflict resolver
├── hooks.json            # Agent pre-invocation & pre-commit hook configuration
├── hooks/
│   └── pre-commit.sh     # Git pre-commit rule scanner validation
├── scripts/
│   ├── scan_rules.py     # Prompt poisoning and security rule auditor
│   ├── tag_conversations.py # Conversation learning marker
│   ├── check_unprocessed_convos.py # Unlearned conversation discovery helper
│   └── auto_sync_vault.py   # Non-blocking sync daemon/helper
├── LICENSE               # MIT License
└── README.md             # Documentation
```

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for details.
