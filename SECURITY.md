# Security Policy

## Reporting a vulnerability

Report security vulnerabilities **privately**, never through a public issue.

Use GitHub's private advisory reporting:

**[Report a vulnerability](../../security/advisories/new)**

Include, where possible:

- A description of the issue and its impact
- Steps to reproduce or a proof of concept
- Affected component, version, or commit (if applicable)

You will receive an acknowledgement as soon as practicable. Please allow a
reasonable window for assessment and a fix before any public disclosure.

If private advisory reporting is unavailable, contact the maintainer directly
via the address listed on their GitHub profile
(<https://github.com/Siddhesh-ai-del>) and mark the subject
`SECURITY: re-frame`.

## Scope

In scope:

- This repository's code, build, and CI configuration (once implementation begins)
- The planned conversation pipeline: risk classification, escalation, output filtering, prompt-injection or jailbreak paths that could cause diagnostic, treatment, or crisis-handling failures
- Data handling in the planned product: secrets, credentials, personal or health-adjacent data

Out of scope:

- Third-party model providers and their platforms (report upstream)
- Social engineering of individual users
- Vulnerabilities in dependencies without a demonstrated path of exploitation in this project

## User guarantees

This project is pre-release: there is no production service and no user data
today. When a service exists, the following commitments apply:

- No secrets in the repository; credentials come from the environment or a key manager only
- Conversational data is minimized, encrypted in transit and at rest, and never sold or used for advertising
- Crisis and safety events are logged for audit, with access restricted and audited
- Security reports are never penalized; good-faith disclosure is welcomed and credited on request

## Supported versions

| Version | Supported |
|---------|-----------|
| pre-release (main) | ✔ security fixes land on `main` |

No numbered release exists yet; this table will be updated when releases begin.
