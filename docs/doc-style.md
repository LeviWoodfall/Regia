# Documentation Style Guide

This guide keeps every Regia document consistent, concise, and actionable. Refer to it before merging doc updates.

## 1. Voice & Tone
- **Authoritative but warm**: write like an expert teammate.
- Avoid marketing fluff; focus on factual, reproducible instructions.
- Use present tense and active voice.

## 2. Structure
- Start with a one-line purpose statement.
- Use `##` for primary sections, `###` for subsections.
- Prefer tables for matrices (environments, owners, feature flags).
- For procedures: introduce context, then numbered steps with command blocks.

## 3. Content Rules
- Include prerequisites and rollback steps for every risky operation.
- Reference exact UI labels, API endpoints, and file paths (`code` style).
- Provide platform-specific commands when they differ (PowerShell vs Bash).
- When adding new features, update: README, CHANGELOG, relevant guide(s), and troubleshooting if applicable.

## 4. Formatting
- Wrap lines at ~100 characters to ease diff review.
- Use fenced code blocks with language tags: ```bash ```, ```powershell ```, ```json ```.
- Capitalize UI terms exactly as seen in product (e.g., **Settings → Scheduler**).
- Prefer Markdown tables over bullet lists for multi-column data.

## 5. Terminology
| Term | Usage |
| --- | --- |
| Regia | The platform name (capitalize) |
| Reggie | AI assistant persona |
| Credential Store | Encrypted secrets vault unlocked via master password |
| Scheduler | APScheduler-based polling system |
| Dev Login | Deterministic account (`dev / DevPassword!123`) used for CI |

## 6. Review Checklist
Before merging documentation changes:
1. Verify affected personas are addressed (admin, dev, user, support).
2. Ensure cross-links exist (e.g., from README to relevant doc pages).
3. Run `python scripts/check_docs.py` locally.
4. Update CHANGELOG entry if the docs reflect new capabilities or fixes.

## 7. Diagram & Media Guidelines
- Store diagrams in `docs/assets/` as SVG or PNG.
- Provide alternative text captions below each image.
- Keep screenshots current with the UI theme (Warm Sunset) unless documenting dark mode.

## 8. Future Additions
- Automated link checker integration.
- Style lint rules in Vale or markdownlint.
- Localization guidelines.
