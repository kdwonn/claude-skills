#!/usr/bin/env bash
# Scaffold a dated experiment launcher under experiment/MMDD/<name>.sh.
#
# Creates the dated folder, drafts a runnable bash script that calls
# scripts/train.sh with the given Hydra overrides, and prepends a header
# comment describing what the experiment is for.
#
# Usage:
#   ${CLAUDE_PLUGIN_ROOT}/skills/launch-experiment/new_experiment.sh \
#       --name jeda_robocasa_pickplace \
#       --purpose "First PickPlace bring-up: qformer-16, L, bs64x2." \
#       [--date 0630] [--gpus 2] \
#       -- <hydra overrides, one token each>
#
# Everything after `--` is passed through verbatim as Hydra overrides, e.g.
#       -- data=robocasa model=jeda_robocasa model.size=l trainer.batch_size=64
#
# The script is created executable and is NEVER overwritten if it exists.
set -euo pipefail

NAME=""
PURPOSE=""
DATE=""
GPUS="2"
OVERRIDES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)    NAME="$2"; shift 2 ;;
        --purpose) PURPOSE="$2"; shift 2 ;;
        --date)    DATE="$2"; shift 2 ;;
        --gpus)    GPUS="$2"; shift 2 ;;
        --)        shift; OVERRIDES=("$@"); break ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

[[ -n "$NAME" ]] || { echo "error: --name is required" >&2; exit 2; }
[[ ${#OVERRIDES[@]} -gt 0 ]] || { echo "error: pass Hydra overrides after --" >&2; exit 2; }

# Date folder: MMDD.
[[ -n "$DATE" ]] || DATE="$(date +%m%d)"

# Resolve the target repo from the CURRENT DIRECTORY, not from the script's own
# location: as an installed plugin this script lives in the plugin cache, which
# is a different git repo (or none at all). Run it from the repo root.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "error: not inside a git repository — run this from your project root" >&2
    exit 1
}
DIR="$ROOT/experiment/$DATE"
OUT="$DIR/$NAME.sh"

mkdir -p "$DIR"
if [[ -e "$OUT" ]]; then
    echo "error: $OUT already exists — refusing to overwrite" >&2
    exit 1
fi

[[ -n "$PURPOSE" ]] || PURPOSE="TODO: describe what this experiment tests and why."

# Build the indented override block (one override per line, backslash-continued).
OVR_BLOCK=""
for o in "${OVERRIDES[@]}"; do
    OVR_BLOCK+="    $o \\"$'\n'
done
# trainer.notes pins the run name to the experiment name; append if not given.
if ! printf '%s\n' "${OVERRIDES[@]}" | grep -q '^trainer.notes='; then
    OVR_BLOCK+="    trainer.notes=$NAME \\"$'\n'
fi
# Forward launch-time extra args (e.g. `launch.sh <script> trainer.fast_dev_run=true`)
# into train.py — without this, launch.sh's pass-through overrides are silently dropped.
OVR_BLOCK+='    "$@"'$'\n'

{
    echo "#!/usr/bin/env bash"
    echo "set -euo pipefail"
    echo ""
    echo "# $NAME"
    echo "#"
    # Wrap the purpose into comment lines.
    echo "$PURPOSE" | fold -s -w 72 | sed 's/^/# /; s/ *$//'
    echo "#"
    echo "# Created: $DATE  |  Drafted by /launch-experiment"
    echo ""
    echo "NUM_GPUS=\${NUM_GPUS:-$GPUS} bash scripts/train.sh \\"
    printf '%s' "$OVR_BLOCK"
} > "$OUT"

chmod +x "$OUT"
echo "created $OUT"
echo "--- drafted script ---"
cat "$OUT"

# How to launch it: a dedicated detached tmux session named exp-<name>, so the
# run survives an SSH disconnect and is reattachable. See launch.sh.
REL_OUT="${OUT#"$ROOT"/}"
echo ""
echo "--- launch in tmux session exp-$NAME ---"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "$SELF_DIR/launch.sh $REL_OUT"
