#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

: "${DEEPSEEK_API_KEY:?Export DEEPSEEK_API_KEY before running the controlled evaluation.}"

model_path="${REPOPILOT_QWEN_PATH:-/home/hp/.cache/modelscope/models/Qwen--Qwen3-0.6B/snapshots/master}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)"
output_dir="${1:-benchmark-results/e2e/deepseek-flash-${run_id}}"
qwen_log="benchmark-results/e2e/qwen-${run_id}.log"
mkdir -p "$(dirname "$qwen_log")"

qwen_pid=""
cleanup() {
  if [[ -n "$qwen_pid" ]] && kill -0 "$qwen_pid" 2>/dev/null; then
    kill "$qwen_pid" 2>/dev/null || true
    wait "$qwen_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if ! conda run -n repopilot repopilot-local health --timeout 30 >/dev/null 2>&1; then
  (
    unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
    export NO_PROXY=127.0.0.1,localhost
    export no_proxy=127.0.0.1,localhost
    exec conda run -n sglang --no-capture-output sglang serve \
      --model-path "$model_path" \
      --host 127.0.0.1 \
      --port 30000 \
      --mem-fraction-static 0.6 \
      --context-length 4096 \
      --chunked-prefill-size 512 \
      --cuda-graph-backend-decode disabled \
      --cuda-graph-backend-prefill disabled \
      --attention-backend triton \
      --sampling-backend pytorch
  ) >"$qwen_log" 2>&1 &
  qwen_pid="$!"

  ready=false
  for _attempt in $(seq 1 90); do
    if conda run -n repopilot repopilot-local health --timeout 30 >/dev/null 2>&1; then
      ready=true
      break
    fi
    if ! kill -0 "$qwen_pid" 2>/dev/null; then
      tail -80 "$qwen_log" >&2
      echo "Qwen SGLang exited before becoming healthy." >&2
      exit 1
    fi
    sleep 2
  done
  if [[ "$ready" != true ]]; then
    tail -80 "$qwen_log" >&2
    echo "Qwen SGLang did not become healthy within the startup deadline." >&2
    exit 1
  fi
fi

conda run -n repopilot --no-capture-output repopilot evaluate \
  --manifest benchmarks/e2e-v1/manifest.json \
  --output-dir "$output_dir" \
  --image repopilot-runner:py312 \
  --max-spend-cny 8 \
  --reserve-cny 2 \
  --estimated-pair-cost-cny 1.5

echo "Controlled evaluation artifacts: $output_dir"
