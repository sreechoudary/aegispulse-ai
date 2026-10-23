# AegisPulse AI — Publication-Readiness Report (2026-10-18)

Pre-publication audit. The repository is NOT published and NO AWS deployment was performed.

## 1. LICENSE — RESOLVED
- `LICENSE` now contains the complete, unmodified Apache License 2.0 text fetched from
  https://www.apache.org/licenses/LICENSE-2.0.txt (full TERMS AND CONDITIONS 1-9 + APPENDIX;
  "END OF TERMS AND CONDITIONS" present; 203 lines).
- The project copyright notice is kept SEPARATE from the standard license body: a single line
  `Copyright 2026 M Sreenivasarao` sits at the top, above the verbatim Apache text.

## 2. Copyright owner — RESOLVED
- Owner confirmed by the maintainer: **M Sreenivasarao** (individual). Applied in LICENSE and
  the NOTICE header.

## 3. NOTICE.md — RESOLVED / corrected
- Strands Decider 2B model attributed as Apache-2.0 (verified against the strands-labs/strands-decider
  README statement and the installed strands-decider package metadata `License-Expression: Apache-2.0`).
- Python dependency licenses verified from installed package metadata. torch corrected to primary
  BSD-3-Clause (with a note on its bundled multi-license components) rather than a blanket claim.
- MPL-2.0 (Hypothesis) corrected: described accurately as a file-level/weak copyleft used ONLY as a
  dev/test dependency, imposing no copyleft obligation on AegisPulse code. Removed the prior
  unsupported "all permissive" blanket statement.
- Amazon Bedrock attributed as a hosted service under AWS Service Terms (no weights redistributed).

## 4. Frontend dependencies — VERIFIED against lockfile
- `package-lock.json` present. Scanned 237 installed packages: MIT 210, ISC 14, Apache-2.0 7,
  BSD-2-Clause 2, BSD-3-Clause 2, MIT-0 1, CC-BY-4.0 1. No GPL/LGPL/AGPL/MPL present.
- `caniuse-lite` (CC-BY-4.0) attributed in NOTICE (build-time data, not emitted to the bundle).
- Internal malformed test-fixture packages (baz, browser_field, false_main, invalid_main, unnamed)
  identified as non-dependencies; noted in NOTICE.

## 5. Third-party NOTICE/copyright statements — PRESERVED
- No third-party source is vendored; each dependency retains its own LICENSE in node_modules /
  site-packages. NOTICE instructs retaining upstream notices on redistribution. No third-party
  NOTICE files were stripped (none were copied in).

## 6. Bundled assets — NONE
- No model weights, *.safetensors/*.bin/*.pt, fonts, icons, images, or binaries anywhere in the
  committable tree. Decider weights live in ~/.cache/huggingface (outside the repo), downloaded at
  runtime. The frontend has no committed font/icon assets.

## 7. Secrets & sensitive-data scan — CLEAN (over the exact committable set)
- 100 files would be committed. Scanned for AWS keys (AKIA/ASIA), secret access keys, private-key
  headers, 12-digit account ids, absolute user paths, company references, and high-entropy secrets.
- Findings: NONE real. The only matches are documentation TEXT: the scan description in
  SECURITY_REVIEW.md, and the MASKED account `<redacted-account-id>` in SECURITY_REVIEW.md and tasks.md.
- No unmasked account id, no credentials, no absolute `/Users/...` paths in the committable set.

## 8. .gitignore / staging — VERIFIED
- `.gitignore` excludes venvs, __pycache__, pytest/mypy/ruff caches, *.db/-wal/-shm, node_modules,
  dist, .env/*.pem/*.key, and the entire `docs/validation/` dev-scaffolding directory (which held
  absolute paths, the `ar-dev` profile name, and raw run outputs).
- `git add -A --dry-run` confirms 100 files would be committed and ZERO gitignored artifacts
  (node_modules, venv, caches, DBs, docs/validation) would be staged.
- NOTHING has been staged or committed by this review (staging left to the maintainer).

## 9. Offline quality gate — GREEN
- Backend 81 tests pass; ruff clean; mypy clean on core modules; frontend 2 tests pass.

## Remaining items for the maintainer BEFORE public release
1. (Optional) Decide whether to scrub even the MASKED account `<redacted-account-id>` from
   docs/SECURITY_REVIEW.md and .kiro/specs/chaospilot-ai/tasks.md. It is masked and harmless, but
   some teams prefer zero account references in public repos.
2. (Optional) The `.kiro/specs/` design/requirements/tasks docs would be committed (4 files). They
   contain no secrets but are internal planning artifacts — confirm you want them public.
3. Review `git status` and `git diff --cached` yourself after staging, as a final human check.
4. Fill REPO_URL_PLACEHOLDER and VIDEO_URL_PLACEHOLDER in the article after publishing + recording.
5. Export architecture.png from the design.md Mermaid diagram for the article.
6. Final human license sign-off (especially the torch multi-license note).

## Unresolved licensing/copyright/attribution/security issues
- NONE that block preparation. All items above are optional maintainer preferences or post-publish
  placeholders. No real secret, credential, unmasked account id, bundled third-party asset, or
  copyleft-contamination risk was found.

## Explicitly NOT done (per instructions)
- Repository NOT published. No commit made. No AWS infrastructure provisioned. Hackathon NOT submitted.
