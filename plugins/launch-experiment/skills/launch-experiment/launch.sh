#!/usr/bin/env bash
# Launch one experiment arm as a window in its round's tmux session.
#
# A "round" is a folder experiment/<MMDD_topic>/ holding several arm scripts.
# All arms of a round share ONE detached tmux session named  exp-<MMDD_topic>,
# with one window per arm — so a round is a single attachable, killable unit:
#
#   tmux attach       -t exp-<round>            # all arms as windows (Ctrl-b n/p)
#   tmux kill-window  -t exp-<round>:<arm>      # stop one arm
#   tmux kill-session -t exp-<round>            # stop the whole round tree
#
# The session survives an SSH disconnect. stdout+stderr of each arm are teed to
# experiment/<round>/logs/<arm>.log so runs stay inspectable after windows close.
#
# Usage (from the repo root):
#   launch.sh experiment/<MMDD_topic>/<arm>.sh [extra args...]
#   NUM_GPUS=4 CUDA_VISIBLE_DEVICES=0,1,2,3 launch.sh experiment/0901_foo/arm_a.sh
#   launch.sh experiment/0901_foo/arm_a.sh trainer.fast_dev_run=true   # smoke window
#
# Extra args pass through to the arm script (and typically on into train.py as
# Hydra overrides). NUM_GPUS / CUDA_VISIBLE_DEVICES / PORT from the calling
# environment are forwarded into the window.
#
# GPU guard: when CUDA_VISIBLE_DEVICES is set, every listed GPU must have less
# than GPU_BUSY_MIB (default 5000) MiB in use or the launch is refused — the
# co-located-job check that keeps benchmarks and training honest. When it is
# unset the guard is skipped, on the assumption the arm script pins its own
# GPUs and does its own checking.
set -euo pipefail

command -v tmux >/dev/null || { echo "error: tmux not found on PATH" >&2; exit 127; }

SCRIPT="${1:-}"
[[ -n "$SCRIPT" ]] || { echo "usage: launch.sh experiment/<MMDD_topic>/<arm>.sh [extra args...]" >&2; exit 2; }
shift || true

# Resolve the target repo from the CURRENT DIRECTORY, not from this script's own
# location: as an installed plugin it lives in the plugin cache, which is a
# different git repo (or none at all). Run it from the project root.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "error: not inside a git repository — run this from your project root" >&2
    exit 1
}
cd "$ROOT"
[[ -f "$SCRIPT" ]] || { echo "error: $SCRIPT not found (from repo root $ROOT)" >&2; exit 1; }

ROUND_DIR="$(dirname "$SCRIPT")"
ROUND="$(basename "$ROUND_DIR")"
ARM="$(basename "$SCRIPT" .sh)"
SESSION="exp-$ROUND"
LOG_DIR="$ROUND_DIR/logs"
LOG="$LOG_DIR/$ARM.log"
mkdir -p "$LOG_DIR"

# GPU busy guard — refuse to stack onto GPUs that already hold a job.
if [[ -n "${CUDA_VISIBLE_DEVICES:-}" ]] && command -v nvidia-smi >/dev/null; then
    BUSY_MIB="${GPU_BUSY_MIB:-5000}"
    IFS=',' read -ra _GPUS <<< "$CUDA_VISIBLE_DEVICES"
    for g in "${_GPUS[@]}"; do
        used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$g")"
        if (( used >= BUSY_MIB )); then
            echo "error: GPU $g busy (${used} MiB >= ${BUSY_MIB}) — refusing to launch $ARM" >&2
            echo "  check who's on it: nvidia-smi" >&2
            exit 1
        fi
    done
fi

# One window per arm inside the round's session. "=" forces exact-name matching
# — plain -t prefix-matches, so exp-0901_foo would falsely collide with a
# leftover exp-0901_foo2 session (and window "arm" with "arm_long").
if tmux has-session -t "=$SESSION" 2>/dev/null; then
    if tmux list-windows -t "=$SESSION" -F '#W' | grep -Fxq "$ARM"; then
        echo "error: window '$ARM' already exists in session '$SESSION' — arm already running?" >&2
        echo "  attach:  tmux attach -t $SESSION" >&2
        echo "  or kill: tmux kill-window -t =$SESSION:$ARM" >&2
        exit 1
    fi
    MODE="window"
else
    MODE="session"
fi

# Forward the env vars that steer the launch into the window command.
ENV_PREFIX=""
for v in NUM_GPUS CUDA_VISIBLE_DEVICES PORT; do
    [[ -n "${!v:-}" ]] && ENV_PREFIX+="$v=$(printf %q "${!v}") "
done

# Pass-through extra args, each token shell-quoted.
EXTRA=""
for a in "$@"; do EXTRA+=" $(printf %q "$a")"; done

# Run under `bash -c` so semantics don't depend on the login shell (on a zsh box
# $PIPESTATUS would differ). pipefail makes $? reflect the training command
# rather than tee. The trailing `read` keeps the window — and the exit status —
# visible after the run ends instead of tmux closing it out from under you;
# tee -a so a relaunched arm appends to its log instead of clobbering it.
RUNNER="set -o pipefail; ${ENV_PREFIX}bash $(printf %q "$SCRIPT")${EXTRA} 2>&1 | tee -a $(printf %q "$LOG"); \
status=\$?; echo; echo \"[$SESSION:$ARM exited \$status — press enter to close]\"; read"

if [[ "$MODE" == "session" ]]; then
    tmux new-session -d -s "$SESSION" -n "$ARM" -c "$ROOT" "bash -c $(printf %q "$RUNNER")"
else
    tmux new-window -d -t "=$SESSION" -n "$ARM" -c "$ROOT" "bash -c $(printf %q "$RUNNER")"
fi

echo "launched: $SESSION:$ARM  (new $MODE)"
echo "  attach:  tmux attach -t $SESSION      # Ctrl-b n/p between arms, Ctrl-b d to detach"
echo "  log:     $LOG"
echo "  kill arm:   tmux kill-window -t =$SESSION:$ARM"
echo "  kill round: tmux kill-session -t $SESSION"
