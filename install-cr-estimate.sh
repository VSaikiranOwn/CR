#!/usr/bin/env bash
# Install the cr-estimate skill into the DCP AI harness.
#
# For Git Bash on Windows, WSL, macOS and Linux.
#
#   ./install-cr-estimate.sh                        auto-detect the harness
#   ./install-cr-estimate.sh <harnessRoot>          point it explicitly
#   ./install-cr-estimate.sh <harnessRoot> 41000    ...and smoke-test a batch
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE="$REPO_ROOT/harness/bundle"

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    OK   %s\n' "$1"; }
warn() { printf '    !    %s\n' "$1"; }
die()  { printf '\n    ERROR: %s\n\n=== FAILED ===\n\n' "$1" >&2; exit 1; }

printf '\n=== Installing cr-estimate ===\n'

# ------------------------------------------------------------------ bundle
step "Checking the bundle"
if [ ! -f "$BUNDLE/skills/cr-estimate/SKILL.md" ]; then
    die "no bundle at '$BUNDLE'.
    You are probably on the wrong branch. Run this, then try again:
        git checkout claude/cr-generation-utility-s8sfrz"
fi
ok "$BUNDLE"

# --------------------------------------------------------- harness location
is_harness() {
    [ -d "$1/.github/skills" ] && [ -d "$1/.github/validators" ] && [ -d "$1/.github/workspace" ]
}

step "Locating the harness"
HARNESS="${1:-}"
if [ -n "$HARNESS" ]; then
    HARNESS="$(cd "$HARNESS" 2>/dev/null && pwd)" || die "'${1}' is not a folder."
else
    # The clone usually sits inside the harness workspace, so try the parent
    # folder first, then its parent.
    for candidate in "$REPO_ROOT/.." "$REPO_ROOT/../.."; do
        resolved="$(cd "$candidate" && pwd)"
        if is_harness "$resolved"; then HARNESS="$resolved"; break; fi
    done
fi

[ -n "$HARNESS" ] || die "could not find a harness near '$REPO_ROOT'.
    Pass it explicitly, for example:
        ./install-cr-estimate.sh /c/Microservices/Workspace/aiv2"
is_harness "$HARNESS" || die "'$HARNESS' has no .github/skills, .github/validators and .github/workspace.
    Pass the folder that contains the harness .github directory."
ok "$HARNESS"

# -------------------------------------------------------------- copy files
step "Installing files"
if [ -d "$HARNESS/.github/skills/cr-estimate" ]; then
    warn "replacing the existing skill"
    rm -rf "$HARNESS/.github/skills/cr-estimate"
fi
cp -r "$BUNDLE/skills/cr-estimate" "$HARNESS/.github/skills/"
ok ".github/skills/cr-estimate"
cp "$BUNDLE/validators/cr_complete.py" "$HARNESS/.github/validators/"
ok ".github/validators/cr_complete.py"

# ------------------------------------------------------------------ python
step "Checking python"
PY=""
for candidate in python python3 py; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    # Reject the Microsoft Store stub, a 0-byte shim that just opens the Store.
    case "$(command -v "$candidate")" in *WindowsApps*) continue ;; esac
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
        PY="$candidate"; break
    fi
done

if [ -z "$PY" ]; then
    warn "no usable python 3.10+ on PATH."
    warn "install Python from python.org (not the Microsoft Store), then: pip install openpyxl"
else
    ok "using '$PY'"
    if ! "$PY" -c "import openpyxl" >/dev/null 2>&1; then
        warn "openpyxl missing, installing"
        "$PY" -m pip install --quiet openpyxl
    fi
    ok "openpyxl available"
fi

# ------------------------------------------------------------- smoke test
BATCH="${2:-}"
if [ -n "$BATCH" ] && [ -n "$PY" ]; then
    step "Smoke test on batch $BATCH"
    ( cd "$HARNESS" && "$PY" .github/skills/cr-estimate/scripts/cr_estimate.py \
        ".github/workspace/$BATCH" --dry-run )
fi

printf '\n=== Installed ===\n\n'
cat <<EOF
Next:
  1. Make the three edits in harness/INSTALL.md section 3
     (design.agent.md, docs/design.md, copilot-instructions.md)
  2. Generate an estimate:
       cd "$HARNESS"
       ${PY:-python} .github/skills/cr-estimate/scripts/cr_estimate.py .github/workspace/41000

Output lands in .github/workspace/<batch>/02-design/cr/
EOF
