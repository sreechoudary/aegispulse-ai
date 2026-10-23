# AegisPulse AI — Repository Security-Review Report (2026-10-18)

Pre-publication review. Scope: the files that would be committed to the public repository.

## Automated scans
- **Secret scan** (AKIA keys, aws_secret_access_key, PRIVATE/RSA key headers) across
  *.py/*.ts/*.tsx/*.json/*.md, excluding node_modules/.venv: **0 findings.**
- **AWS account-id scan** (12-digit) in shippable code/config: **0 findings.** The only account
  reference anywhere is the masked `<redacted-account-id>` inside a validation report (docs/validation), which
  is gitignored.
- **Credentials in env/config:** no `.env`, `.pem`, `.key`, or credential files in the tree.
  AWS auth is via local SSO profile (`ar-dev`) resolved at runtime — never stored in the repo.

## Code-level safety posture (verified by tests)
- The only outbound AWS call in the codebase is Bedrock `converse` (inference, read-only).
  No `create_`/`delete_`/`put_`/`update_`/`terminate_`/`modify_` AWS calls exist.
- The simulation engine holds no AWS client; all remediation is in-memory simulation.
- Deterministic policy never reads model text (prompt-injection safe); high-blast-radius actions
  require human approval regardless of confidence; fail-closed on Decider failure. All test-covered.

## Hygiene handled
- Added `.gitignore` excluding: venvs, __pycache__, .pytest_cache/.mypy_cache/.ruff_cache,
  *.db/*.db-wal/*.db-shm, node_modules, dist, .env/*.pem/*.key, and the local dev helper scripts
  under docs/validation/*.sh (which contain absolute local paths).

## Items requiring human action before publishing
1. **Absolute local paths** exist only in `docs/validation/*.sh` (dev helpers) — gitignored, so
   they won't ship. Confirm you don't want them in the repo; if you do, parameterize the paths.
2. **LICENSE** contains the Apache-2.0 header + a placeholder note — paste the full license text
   from apache.org before publishing.
3. **NOTICE.md** license identifiers were read from installed package metadata; do a final
   human license review (especially torch's multi-license and Hypothesis MPL-2.0 dev-only usage).
4. **Validation artifacts** under `docs/validation/` (M0 report with masked account, raw logs) —
   decide whether to include. They are currently gitignored (*.log, *.sh) except the *.md reports.
   The M0 report's account id is masked; no unmasked secrets.
5. Run `git init` and review `git status` against `.gitignore` before the first commit — confirm no
   venv/db/cache is staged.

## Verdict
No secrets, credentials, or customer data found. No real-AWS-mutation code paths. Safe to proceed
to repository preparation after the human completes items 2–5 above. Publishing itself remains
gated on your explicit approval (not done here).
