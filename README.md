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

## Support & Sponsorship

`agv-syncengine` is authored and maintained by **[Vikyek](https://github.com/Vikyek)** as an independent open-source project. Everything is 100% open-source, telemetry-free, and public.

<div align="center">

<!-- Official GitHub Sponsors Button & Card (Rendered in web/HTML environments; GitHub markdown sanitizer strips iframes, falling back to native badges) -->
<iframe src="https://github.com/sponsors/Vikyek/button" title="Sponsor Vikyek" height="32" width="114" style="border: 0; border-radius: 6px;"></iframe>
<iframe src="https://github.com/sponsors/Vikyek/card" title="Sponsor Vikyek" height="225" width="600" style="border: 0;"></iframe>

[![Sponsor Vikyek](https://img.shields.io/badge/Sponsor-%E2%9D%A4-ea4aaa?logo=github&style=for-the-badge)](https://github.com/sponsors/Vikyek)
[![Donate on Liberapay](https://img.shields.io/badge/Donate-Liberapay-f6c915?style=for-the-badge&logo=liberapay&logoColor=black)](https://liberapay.com/Vikyek)
[![Sponsor on Polar](https://img.shields.io/badge/Sponsor-Polar-0062FF?style=for-the-badge&logo=polar&logoColor=white)](https://polar.sh/vikyek)
[![Donate with Stripe](https://img.shields.io/badge/Donate-Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://profile.stripe.com/@vikyek)

</div>

> ### 🎯 Active Sponsorship Goal: Monthly Living Essentials
> **Target:** **2,710 PLN / ~$675 USD per month** (`630 PLN / week`) — Rent & Essential Utilities  
> Covering basic living essentials directly unlocks dedicated, sustainable full-time independent open-source engineering across Arch Linux utilities, developer tools, and AI middleware free from corporate telemetry, ads, or paywalls.

If this project saves you time, optimizes your setup, or accelerates your workflow, consider supporting ongoing work:

- **GitHub Sponsors**: [github.com/sponsors/Vikyek](https://github.com/sponsors/Vikyek) *(Monthly tiers and one-time tips)*
- **Liberapay**: [liberapay.com/Vikyek](https://liberapay.com/Vikyek) *(0% platform fee recurrent patronage in EUR/USD/PLN)*
- **Polar**: [polar.sh/vikyek](https://polar.sh/vikyek) *(Developer subscriptions & commercial passes)*
- **Direct Stripe Profile**: [profile.stripe.com/@vikyek](https://profile.stripe.com/@vikyek) *(Direct one-time tips & sponsorship)*

Every contribution—monthly or one-time—directly supports active maintenance, hardware testbeds, and new feature development!

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for details.
