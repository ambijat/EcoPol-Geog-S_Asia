# Public GitHub Bootstrap Plan

```yaml
status: APPROVED
authority: INSTRUCTOR_RULING
approved_date: 2026-07-21
public_repository: ambijat/EcoPol-Geog-S_Asia
publication_status: NOT_YET_AUTHORISED
```

## History boundary

The existing local Git repository and its history remain authoritative internally. They must never be pushed to the public remote. Public GitHub history begins from a clean, public-safe root with no parent relationship to the local internal root commit.

The canonical governance preamble, canonical ledger, and canonical retrospective event source remain private. Their public projections are informational, redacted, and non-canonical.

## Public branch model

- Public `main` begins with only the approved public repository scaffold.
- Public `semester/2026` contains the approved public Semester 2026 baseline.
- A draft pull request proposes `semester/2026` into public `main`.
- The pull request must not be merged without explicit instructor approval.

No private canonical file, local mapping, imported historical source, student information, credential, restricted assessment, or machine-specific report may enter either public branch.

## Assembly rule

The public bootstrap must be assembled in a separate linked worktree using `reports/public_include_manifest.txt`. `git add .` is prohibited. The include manifest is an allowlist, while `reports/public_exclude_manifest.txt` documents mandatory exclusions.

The worktree receives a new orphan public root. Removing files from that separate worktree affects only the public assembly checkout; the authoritative local worktree and its canonical files remain untouched. Before any commit, compare the staged names against the include manifest and rerun all public-projection safety checks.

## Publication gate

This plan authorises preparation only. Creating the worktree, orphan branch, root commit, remote, push, or pull request requires a later explicit instructor instruction.

## Future clean-bootstrap procedure

After an explicit instruction to publish, use a new independent temporary repository rather than changing branches in the authoritative worktree:

```bash
project_root="$(pwd -P)"
public_root="$(mktemp -d -p "$(dirname "$project_root")" IS529N_PUBLIC_BOOTSTRAP.XXXXXX)"

git init -b main "$public_root"
rsync -a --relative \
  --files-from="$project_root/reports/public_include_manifest.txt" \
  "$project_root/" "$public_root/"

cd "$public_root"
git add .gitignore README.md config/public_projection_paths.example.json
git add docs/GIT_VERSIONING_POLICY.md docs/PUBLIC_REPOSITORY_BOUNDARY.md
git add docs/ANNUAL_RELEASE_PROTOCOL.md docs/PUBLIC_GITHUB_BOOTSTRAP_PLAN.md
git add public/ledger/README.md
git add reports/public_include_manifest.txt reports/public_exclude_manifest.txt
git diff --cached --check
git diff --cached --name-status
git commit -m "chore(repo): establish public-safe IS529N scaffold"

git remote add origin git@github.com:ambijat/EcoPol-Geog-S_Asia.git
git push -u origin main

git switch -c semester/2026
git add --pathspec-from-file=reports/public_include_manifest.txt
git diff --cached --check
git diff --cached --name-status
git commit -m "chore(repo): establish governed IS529N Semester 2026 public baseline"
git push -u origin semester/2026

gh pr create \
  --repo ambijat/EcoPol-Geog-S_Asia \
  --draft \
  --base main \
  --head semester/2026 \
  --title "Establish governed IS529N Semester 2026 baseline" \
  --body "Adds the approved public Semester 2026 projection, paired lecture architecture, non-canonical ledger projection, validation evidence, exclusions, and unresolved governance notes."
```

Before either commit, compare every staged path with the include manifest and rerun the local authoritative tests, repository validation, ledger verification, and projection dry-run. Do not run `git add .`.
