# Security Policy

## Supported Scope

FEA Copilot is an early-stage open-source engineering tool. Security work should focus on:

- dependency vulnerabilities
- unsafe file-handling or archive-export behavior
- command-execution or container-runtime issues
- accidental disclosure of local run artifacts or secrets

## Reporting A Vulnerability

Do not post exploit details in a public issue.

Preferred disclosure path:

1. Use GitHub private vulnerability reporting if it is enabled for the repository.
2. If that path is unavailable, contact the maintainers privately.
3. If no private contact is visible, open a short public issue requesting a disclosure channel without sharing exploit steps or sensitive data.

## What To Include

- affected version or commit
- clear reproduction steps
- impact description
- suggested mitigation if known

## Response Expectations

This repository does not currently promise a formal SLA. Triage will be faster when the report includes a minimal reproduction and a concrete impact statement.
