#!/bin/zsh

set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
dist_dir="$repo_root/dist"
workflow_dir="$repo_root/workflow"
artifact="$dist_dir/YT Audio Player.alfredworkflow"

mkdir -p "$dist_dir"
rm -f "$artifact"
(
  cd "$workflow_dir"
  zip -qr "$artifact" .
)

echo "Created $artifact"
