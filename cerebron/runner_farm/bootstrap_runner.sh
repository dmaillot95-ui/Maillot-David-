#!/usr/bin/env bash
set -euo pipefail

# CEREBRON OMEGA self-hosted runner bootstrap helper.
# This script does not create compute. It enrolls an existing Linux machine as a
# GitHub Actions runner after the operator supplies a valid GitHub registration token.

: "${CEREBRON_REPO_URL:?Set CEREBRON_REPO_URL, e.g. https://github.com/owner/repo}"
: "${CEREBRON_RUNNER_TOKEN:?Set CEREBRON_RUNNER_TOKEN to a valid short-lived runner registration token}"

RUNNER_NAME="${CEREBRON_RUNNER_NAME:-cerebron-$(hostname)-$(cat /etc/machine-id 2>/dev/null | cut -c1-8 || echo local)}"
RUNNER_LABELS="${CEREBRON_RUNNER_LABELS:-cerebron,physical,self-hosted,linux,x64}"
RUNNER_ROOT="${CEREBRON_RUNNER_ROOT:-$HOME/actions-runner}"
RUNNER_VERSION="${CEREBRON_RUNNER_VERSION:-2.337.0}"

mkdir -p "$RUNNER_ROOT"
cd "$RUNNER_ROOT"

if [ ! -x ./config.sh ]; then
  ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  curl -fsSLo "$ARCHIVE" "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${ARCHIVE}"
  tar xzf "$ARCHIVE"
fi

./config.sh --unattended --replace \
  --url "$CEREBRON_REPO_URL" \
  --token "$CEREBRON_RUNNER_TOKEN" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --work "_work"

echo "CEREBRON_RUNNER_ENROLLED name=$RUNNER_NAME labels=$RUNNER_LABELS"
echo "Start with: cd '$RUNNER_ROOT' && ./run.sh"
