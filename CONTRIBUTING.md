# Contributing to RE:FRAME

Thank you for your interest in contributing. This project sits in a sensitive domain (mental-health wellness), so contributions are held to a higher bar than usual: **accuracy over speed, safety over features, evidence over enthusiasm.**

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Search [existing issues](../../issues) to avoid duplicates.
- For substantial changes, open a feature request first describing the problem before the solution.
- Never commit secrets, API keys, tokens, credentials, or personal health data of any kind.

## Reporting bugs

Use the **Bug report** issue template. It asks for:

- A clear description of the problem and steps to reproduce it
- Environment details (OS, runtime, version, model/provider if relevant)
- Expected vs. actual behavior

**Redaction warning:** this project deals with conversational and mental-health-adjacent data. Before attaching logs or transcripts, redact all personal data, crisis content involving real individuals, API keys, and model credentials. The template includes a confirmation checkbox — please actually check it.

## Proposing features

Use the **Feature request** form. It is problem-first: describe the user problem before the proposed solution, and indicate which product principle the proposal advances (non-diagnostic design, architectural safety, evidence-tiered content, or evaluate-before-claim).

Feature ideas that would require diagnostic, treatment, or risk-assessment claims are out of scope by design — the product operates in the wellness lane.

## Development standards

From the first line of implementation code:

1. **Test-driven development is mandatory.** Write a failing test first (RED), implement the minimum to pass (GREEN), then refactor (IMPROVE). Never write production code without a failing test driving it.
2. **Coverage gate: 80%+** for every stage, enforced in CI. Safety-critical paths (risk classification, escalation, output filtering) are held to a higher internal standard — their behavior is specified by tests before implementation.
3. **Conventional commits only:**

   ```
   <type>: <description>
   ```

   Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.
4. **Security scanning before every commit:** no hardcoded secrets (env/keyring only), validate all user input at the boundary, parameterized queries, sanitized output.
5. **Immutability over mutation** and small, cohesive files — follow the style of the surrounding code once code exists.

## Pull requests

- Use the pull-request template: fill in the change type and complete the checklist.
- All CI checks must pass; coverage must not drop below the gate.
- One stage of work per pull request where practical — stages are pushed to the main branch only after their tests pass.
- Reference the issue your change addresses.

## Questions

Open a [discussion or issue](../../issues) for general questions. For security matters, follow [SECURITY.md](SECURITY.md) instead — never disclose vulnerabilities publicly.
