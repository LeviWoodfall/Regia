# Regia Documentation Hub

> _This directory contains the living documentation for the Regia platform. Every pull request that changes runtime behavior, infrastructure, or developer workflows must update the relevant guides before merge._

## Audience Map

| Guide | Primary Audience | Purpose |
| --- | --- | --- |
| [Admin & Operations](./admin-guide.md) | System administrators, SREs | Deployment, upgrades, scheduler control, backups, security rotation |
| [Developer Handbook](./developer-guide.md) | Core maintainers, contributors | Architecture, local setup, testing matrix, release & CI processes |
| [User Journey Guide](./user-guide.md) | Analysts, finance teams, general users | Onboarding, navigation, review/approval, accessibility & theme settings |
| [Logging & Troubleshooting](./troubleshooting.md) | Admins, on-call engineers, support | Log locations, alerting, incident response, recovery recipes |
| [Documentation Style Guide](./doc-style.md) | Everyone documenting Regia | Voice, formatting, and checklist for consistent updates |

## Documentation Expectations

- Documentation is versioned with the codebase. Treat it as part of the definition of done.
- Every feature PR must update the appropriate guide(s) plus the root [README](../README.md) and [CHANGELOG](../CHANGELOG.md).
- Use present tense, include exact UI copy/API routes, and capture pre/post conditions for runbooks.
- Keep examples copy/paste friendly and note platform-specific differences (Windows vs Linux commands).

## Suggested Update Workflow

1. Identify impacted personas (admin, dev, user, ops) when authoring a change.
2. Update or add sections inside the relevant guide(s).
3. Run `python scripts/check_docs.py` locally to ensure the documentation lint passes.
4. Reference the documentation updates in the PR description and changelog entry.

## Future Enhancements

- Screenshot gallery for each workflow.
- Architecture diagrams for ingestion, processing, and AI subsystems.
- Localization of end-user docs.
