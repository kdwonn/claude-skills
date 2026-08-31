#!/usr/bin/env bash
# Launch a drafted experiment in a dedicated, detached tmux session.
#
# The session is named  exp-<name>  where <name> is the script basename (without
# .sh). Running inside tmux means a long training job survives an SSH disconnect
# and you can reattach later with `tmux attach -t exp-<name>`. stdout+stderr are
# teed to experiment/MMDD/<name>.log so the run stays inspectable even after the
# pane closes.
#
# Usage:
#   ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/0701/jeda_robocasa_pickplace.sh
#   NUM_GPUS=4 ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/0701/foo.sh
#   ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/launch.sh experiment/0701/foo.sh trainer.fast_dev_run=true
#
# Extra args after the script path pass through to the experiment script (and on
# into train.py as Hydra overrides). NUM_GPUS / CUDA_VISIBLE_DEVICES / PORT from
# the calling environment are forwarded into the session.
set -euo pipefail

command -v tmux >/dev/null || { echo "error: tmux not found on PATH" >&2; exit 127; }

SCRIPT="${1:-}"
[[ -n "$SCRIPT" ]] || { echo "usage: launch.sh experiment/MMDD/<name>.sh [hydra overrides...]" >&2; exit 2; }
shift || true

# Resolve everything relative to the repo root, since the experiment script calls
# `bash scripts/train.sh` with a root-relative path.
# Resolve the target repo from the CURRENT DIRECTORY, not from the script's own
# location: as an installed plugin this script lives in the plugin cache, which
# is a different git repo (or none at all). Run it from the repo root.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "error: not inside a git repository — run this from your project root" >&2
    exit 1
}
cd "$ROOT"
[[ -f "$SCRIPT" ]] || { echo "error: $SCRIPT not found (from repo root $ROOT)" >&2; exit 1; }

NAME="$(basename "$SCRIPT" .sh)"
SESSION="exp-$NAME"
LOG="${SCRIPT%.sh}.log"

# A session named exp-<name> is the per-experiment identity. If it already exists
# the run is (or was) already going — don't silently start a second copy.
# "=" forces exact-name matching — plain -t prefix-matches, so exp-foo would
# falsely collide with a leftover exp-foo005 session.
if tmux has-session -t "=$SESSION" 2>/dev/null; then
    echo "error: tmux session '$SESSION' already exists." >&2
    echo "  attach:  tmux attach -t $SESSION" >&2
    echo "  or kill: tmux kill-session -t $SESSION" >&2
    exit 1
fi

# Forward the env vars that steer the launch into the session command.
ENV_PREFIX=""
for v in NUM_GPUS CUDA_VISIBLE_DEVICES PORT; do
    [[ -n "${!v:-}" ]] && ENV_PREFIX+="$v=$(printf %q "${!v}") "
done

# Pass-through Hydra overrides, each token shell-quoted.
EXTRA=""
for a in "$@"; do EXTRA+=" $(printf %q "$a")"; done

# Run the whole thing under `bash -c` so semantics don't depend on the login
# shell (this box's default is zsh, where $PIPESTATUS would differ). pipefail
# makes $? reflect the training command rather than tee. The trailing `read`
# keeps the pane — and the exit status — visible after the run ends instead of
# tmux closing the window out from under you.
RUNNER="set -o pipefail; ${ENV_PREFIX}bash $(printf %q "$SCRIPT")${EXTRA} 2>&1 | tee $(printf %q "$LOG"); \
status=\$?; echo; echo \"[exp-$NAME exited \$status — press enter to close]\"; read"

tmux new-session -d -s "$SESSION" -c "$ROOT" "bash -c $(printf %q "$RUNNER")"

echo "launched: $SESSION"
echo "  attach:  tmux attach -t $SESSION"
echo "  detach:  Ctrl-b then d   (training keeps running)"
echo "  log:     $LOG"
echo "  kill:    tmux kill-session -t $SESSION"
