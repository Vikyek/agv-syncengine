# Universal Agent Preferences, Rules & Machine Configuration

---

## 🌐 Universal Preferences & Cross-Machine Rules

- **Autonomous Repository Creation & Maintenance**:
  - Never instruct the user to create GitHub repositories manually. Always autonomously create repositories via `gh repo create` or GitHub REST API using available tokens/SSH/CLI credentials.
  - **Sensitive Content Privacy Invariant**: Remote knowledge vault repositories MUST be created as **Private** (using `--private` with `gh repo create`).
  - **Automatic Repository Promotion**: When a standalone tool, script, or workspace directory reaches a functional state ("project-worthy"), autonomously promote it into a proper Git repository (`git init`, `.gitignore`, `README.md`, `LICENSE`, `gh repo create`).
  - **Document & Build System Synchronization**: For all projects, maintain and update standard documentation (`README.md`, `.gitignore`, `GEMINI.md` / `AGENTS.md`, `LICENSE`).

- **Private Configuration Vault Synchronization**:
  - All learned preferences, rules, skills, and configuration options are tracked in a private GitHub repository located at `~/.gemini/config/`.
  - Always execute automated sync (`git pull --rebase` / `git push`) whenever rules or configurations are updated.
  - **Interactive Conflict Detection**: If merge conflicts occur when pulling machine-originating rules from another device, display diff and resolve interactively.
  - **Explicit Confirmation Invariant**: Always explicitly state/confirm when repository commit and vault sync (push) have successfully completed.

- **Script Security & Secret Isolation Invariants**:
  - **Exit Trap Secret Cleanup**: Whenever writing bash/shell scripts processing sensitive credentials (PATs, passwords, secret keys), ALWAYS implement an exit trap: `trap 'unset GITHUB_TOKEN DECRYPT_PASS ENCRYPT_PASS GH_TOKEN VAULT_PAT 2>/dev/null || true' EXIT INT TERM`.
  - **Secret Input Sanitization**: When prompting for secrets with visual `*` character masking, redirect cursor controls (`tput civis >&2`, `tput cnorm >&2`) to `stderr` and sanitize captured tokens (`tr -cd '[:alnum:]_'`).
  - **POSIX Permission Invariants**: Credentials/config files containing secrets MUST be created with `chmod 600` (`-rw-------`) and whitelisted in `.gitignore`.
  - **Log Secret Redaction**: Ensure execution log files and live output NEVER print plaintext secrets or tokens.

- **Rule Injection & Prompt Poisoning Defense**:
  - Keep the rule scanner script (`~/.gemini/config/scripts/scan_rules.py`) updated with fresh patterns for prompt injection/data exfiltration checks.
  - Never disable or bypass git `pre-commit` hook validations for `GEMINI.md`, `AGENTS.md`, and other rule manifests.

- **Continuous Learning & Rule Compaction**:
  - Proactively identify reusable rules/skills during tasks or conversations.
  - Continuously sanity-check and compact stored rules to keep token footprint minimal without losing meaning or functionality.
  - **Post-Edit Audit Invariant**: Immediately after editing `GEMINI.md`, read the file to audit for duplicate rules or redundant phrasing, compacting text to minimize token overhead.

- **tokless — Token-Saving Pipeline (codegraph + context-mode + rtk)**:
  - tokless wires codegraph, context-mode, and rtk into every supported agent to reduce token usage.
  - On every new or existing project/repo encountered, run `tokless index` once in the repo root before any codegraph queries if `.codegraph/` is absent.

---

## 💡 Principles & Coding Guidelines

- **Think Before Coding**: State assumptions explicitly. If multiple interpretations exist, present them.
- **Simplicity First**: Minimum code that solves the problem. No speculative abstractions or single-use wrappers.
- **Surgical Changes**: Touch only what you must. Match existing style. Remove unused imports/variables created by your edits.
- **Goal-Driven Execution**: Define success criteria. Test and loop until verified.

---

## 🗣️ Response Style (Caveman)

Respond terse like smart caveman. All technical substance stays. Only fluff dies.
- Drop articles (a/an/the), filler words, pleasantries, decorative tables/emoji, tool-call narration.
- Keep code, commands, paths, API names, and exact error strings verbatim.
- Pattern: `[thing] [action]. [reason]. [next step].`
