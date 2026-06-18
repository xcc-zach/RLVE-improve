import argparse
import re
import shlex
import subprocess
from pathlib import Path


MODEL_PROFILES = {
    "deepseek-r1-distill-qwen-1.5b" : {
        "model_script" : "scripts/models/deepseek-r1-distill-qwen-1.5B.sh",
        "hf_checkpoint" : "../DeepSeek-R1-Distill-Qwen-1.5B",
        "ref_load" : "../DeepSeek-R1-Distill-Qwen-1.5B_torch_dist",
        "size" : "1.5b",
        "num_gpus" : 8,
        "context_parallel_size" : 8,
        "rollout_max_response_len" : 24576,
        "max_tokens_per_gpu" : 3072,
        "rollout_batch_size" : 128,
        "n_samples_per_prompt" : 16,
        "over_sampling_batch_size" : 384,
        "sglang_server_concurrency" : 256,
        "sglang_mem_fraction_static" : 0.7,
    },
    "nemotron-research-reasoning-qwen-1.5b-v2" : {
        "model_script" : "scripts/models/deepseek-r1-distill-qwen-1.5B.sh",
        "hf_checkpoint" : "../Nemotron-Research-Reasoning-Qwen-1.5B-v2",
        "ref_load" : "../Nemotron-Research-Reasoning-Qwen-1.5B-v2_torch_dist",
        "size" : "1.5b",
        "num_gpus" : 8,
        "context_parallel_size" : 8,
        "rollout_max_response_len" : 24576,
        "max_tokens_per_gpu" : 3072,
        "rollout_batch_size" : 128,
        "n_samples_per_prompt" : 16,
        "over_sampling_batch_size" : 384,
        "sglang_server_concurrency" : 256,
        "sglang_mem_fraction_static" : 0.7,
    },
    "openreasoning-nemotron-1.5b" : {
        "model_script" : "scripts/models/qwen2.5-1.5B.sh",
        "hf_checkpoint" : "../OpenReasoning-Nemotron-1.5B",
        "ref_load" : "../OpenReasoning-Nemotron-1.5B_torch_dist",
        "size" : "1.5b",
        "num_gpus" : 8,
        "context_parallel_size" : 8,
        "rollout_max_response_len" : 24576,
        "max_tokens_per_gpu" : 3072,
        "rollout_batch_size" : 128,
        "n_samples_per_prompt" : 16,
        "over_sampling_batch_size" : 384,
        "sglang_server_concurrency" : 256,
        "sglang_mem_fraction_static" : 0.7,
    },
    "openreasoning-nemotron-7b" : {
        "model_script" : "scripts/models/qwen2.5-7B.sh",
        "hf_checkpoint" : "../OpenReasoning-Nemotron-7B",
        "ref_load" : "../OpenReasoning-Nemotron-7B_torch_dist",
        "size" : "7b",
        "num_gpus" : 8,
        "context_parallel_size" : 4,
        "rollout_max_response_len" : 24576,
        "max_tokens_per_gpu" : 2048,
        "rollout_batch_size" : 128,
        "n_samples_per_prompt" : 16,
        "over_sampling_batch_size" : 384,
        "sglang_server_concurrency" : 512,
        "sglang_mem_fraction_static" : 0.7,
    },
    "deepseek-r1-distill-qwen-7b" : {
        "model_script" : "scripts/models/deepseek-r1-distill-qwen-7B.sh",
        "hf_checkpoint" : "../DeepSeek-R1-Distill-Qwen-7B",
        "ref_load" : "../DeepSeek-R1-Distill-Qwen-7B_torch_dist",
        "size" : "7b",
        "num_gpus" : 8,
        "context_parallel_size" : 4,
        "rollout_max_response_len" : 8192,
        "max_tokens_per_gpu" : 2048,
        "rollout_batch_size" : 128,
        "n_samples_per_prompt" : 16,
        "over_sampling_batch_size" : 384,
        "sglang_server_concurrency" : 512,
        "sglang_mem_fraction_static" : 0.7,
    },
}


RESOURCE_KEYS = [
    "num_gpus",
    "context_parallel_size",
    "rollout_max_response_len",
    "max_tokens_per_gpu",
    "rollout_batch_size",
    "n_samples_per_prompt",
    "over_sampling_batch_size",
    "sglang_server_concurrency",
    "sglang_mem_fraction_static",
]


def q(value) -> str :
    return shlex.quote(str(value))


def shell_name(name : str) -> str :
    return name.upper()


def assignment(name : str, value) -> str :
    return "{}={}\n".format(shell_name(name), q(value))


def submission_id_for(run_name : str) -> str :
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", run_name).strip("_")
    return "rlve_{}".format(cleaned[:80] or "run")


def explicit_or_repo_assignments(args, profile) -> str :
    lines = []
    for key in RESOURCE_KEYS :
        value = getattr(args, key)
        if value is None and args.resource_profile == "repo" :
            value = profile[key]
        if value is not None :
            lines.append(assignment(key, value))
    if args.gpu_mem_gb is not None :
        lines.append(assignment("gpu_mem_gb", args.gpu_mem_gb))
    return "".join(lines)


def valid_checkpoint_dir(path : Path | None) -> bool :
    if path is None or not path.exists() :
        return False
    tracker = path / "latest_checkpointed_iteration.txt"
    if not tracker.exists() :
        return False
    try :
        return int(tracker.read_text().strip()) > 0
    except Exception :
        return False


def build_command(args) -> str :
    profile = MODEL_PROFILES[args.model]
    save_dir = Path(args.output_root) / args.run_name
    requested_load_dir = Path(args.load_dir) if args.load_dir else save_dir
    load_dir = str(requested_load_dir) if valid_checkpoint_dir(requested_load_dir) else None
    submission_id = submission_id_for(args.run_name)
    environment_args = " ".join(q(environment) for environment in args.environment_list)
    eval_prompt_data_args = " ".join(q(item) for item in args.eval_prompt_data)
    eval_only_arg = "--eval-only" if args.eval_only else ""
    load_arg = "--load {}".format(q(load_dir)) if load_dir is not None else ""

    rollout_function_args = []
    if args.difficulty_mode == "static" :
        rollout_function_args.append("--rollout-function-path experiments.static_rollout.generate_rollout")

    dynamic_filter_args = []
    if args.dynamic_sampling_filter_path :
        dynamic_filter_args.extend([
            "--dynamic-sampling-filter-path",
            args.dynamic_sampling_filter_path,
        ])

    difficulty_args = []
    if args.difficulty_mode == "adaptive" :
        difficulty_args.extend([
            "--initial-difficulty 0",
            "--difficulty-sliding-window-size 2",
        ])
    else :
        difficulty_args.extend([
            "--initial-difficulty {}".format(args.static_max_difficulty),
            "--difficulty-sliding-window-size {}".format(args.static_max_difficulty - args.static_min_difficulty + 1),
        ])

    resource_assignments = explicit_or_repo_assignments(args, profile)

    bash = f"""
set -ex
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY="127.0.0.1,localhost,0.0.0.0,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
export no_proxy="$NO_PROXY"
pkill -9 sglang || true
sleep 3
ray stop --force || true
pkill -9 ray || true
sleep 3

cleanup() {{
    pkill -9 sglang || true
    ray stop --force || true
    pkill -9 ray || true
}}
trap cleanup EXIT

export PYTHONBUFFERED=16
export TOKENIZERS_PARALLELISM=false

RESOURCE_PROFILE={q(args.resource_profile)}
MODEL_SIZE={q(profile["size"])}
{resource_assignments}
if [ "$RESOURCE_PROFILE" = "auto" ]; then
    NUM_GPUS=${{NUM_GPUS:-$(nvidia-smi -L | wc -l)}}
else
    NUM_GPUS=${{NUM_GPUS:-{profile["num_gpus"]}}}
fi

GPU_MEM_GB=${{GPU_MEM_GB:-$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | sort -n | head -1 | awk '{{print int($1 / 1024)}}')}}

if [ "$NUM_GPUS" -le 0 ]; then
    echo "No GPU detected. Set --num-gpus explicitly if nvidia-smi is unavailable."
    exit 1
fi

if [ "$RESOURCE_PROFILE" = "auto" ]; then
    if [ -z "${{CONTEXT_PARALLEL_SIZE:-}}" ]; then
        CONTEXT_PARALLEL_SIZE=1
        for candidate in 8 4 2; do
            if [ "$NUM_GPUS" -ge "$candidate" ] && [ $((NUM_GPUS % candidate)) -eq 0 ]; then
                CONTEXT_PARALLEL_SIZE=$candidate
                break
            fi
        done
    fi

    if [ -z "${{ROLLOUT_MAX_RESPONSE_LEN:-}}" ]; then
        if [ "$MODEL_SIZE" = "7b" ]; then
            if [ "$GPU_MEM_GB" -ge 70 ] && [ "$NUM_GPUS" -ge 8 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=8192
            elif [ "$GPU_MEM_GB" -ge 40 ] && [ "$NUM_GPUS" -ge 4 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=8192
            elif [ "$GPU_MEM_GB" -ge 40 ] && [ "$NUM_GPUS" -ge 2 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=4096
            else
                ROLLOUT_MAX_RESPONSE_LEN=2048
            fi
        else
            if [ "$GPU_MEM_GB" -ge 70 ] && [ "$NUM_GPUS" -ge 8 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=24576
            elif [ "$GPU_MEM_GB" -ge 40 ] && [ "$NUM_GPUS" -ge 4 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=24576
            elif [ "$GPU_MEM_GB" -ge 40 ] && [ "$NUM_GPUS" -ge 2 ]; then
                ROLLOUT_MAX_RESPONSE_LEN=24576
            else
                ROLLOUT_MAX_RESPONSE_LEN=24576
            fi
        fi
    fi

    if [ -z "${{MAX_TOKENS_PER_GPU:-}}" ]; then
        MAX_TOKENS_PER_GPU=$((ROLLOUT_MAX_RESPONSE_LEN / CONTEXT_PARALLEL_SIZE))
        if [ "$MAX_TOKENS_PER_GPU" -lt 512 ]; then
            MAX_TOKENS_PER_GPU=512
        fi
        if [ "$MODEL_SIZE" != "7b" ] && [ "$MAX_TOKENS_PER_GPU" -gt 3072 ]; then
            MAX_TOKENS_PER_GPU=3072
        fi
        if [ "$MODEL_SIZE" = "7b" ] && [ "$MAX_TOKENS_PER_GPU" -gt 2048 ]; then
            MAX_TOKENS_PER_GPU=2048
        fi
    fi

    if [ -z "${{ROLLOUT_BATCH_SIZE:-}}" ]; then
        if [ "$NUM_GPUS" -ge 8 ]; then
            ROLLOUT_BATCH_SIZE=128
        elif [ "$NUM_GPUS" -ge 4 ]; then
            ROLLOUT_BATCH_SIZE=64
        elif [ "$NUM_GPUS" -ge 2 ]; then
            ROLLOUT_BATCH_SIZE=16
        else
            ROLLOUT_BATCH_SIZE=8
        fi
    fi

    if [ -z "${{N_SAMPLES_PER_PROMPT:-}}" ]; then
        if [ "$GPU_MEM_GB" -ge 40 ] && [ "$NUM_GPUS" -ge 4 ]; then
            N_SAMPLES_PER_PROMPT=16
        else
            N_SAMPLES_PER_PROMPT=8
        fi
    fi

    OVER_SAMPLING_BATCH_SIZE=${{OVER_SAMPLING_BATCH_SIZE:-$((ROLLOUT_BATCH_SIZE * 3))}}
    if [ -z "${{SGLANG_SERVER_CONCURRENCY:-}}" ]; then
        if [ "$NUM_GPUS" -ge 4 ]; then
            SGLANG_SERVER_CONCURRENCY=$((NUM_GPUS * 32))
        else
            SGLANG_SERVER_CONCURRENCY=$((NUM_GPUS * 16))
        fi
    fi
    if [ "$SGLANG_SERVER_CONCURRENCY" -gt 256 ]; then
        SGLANG_SERVER_CONCURRENCY=256
    fi
    if [ -z "${{SGLANG_MEM_FRACTION_STATIC:-}}" ]; then
        if [ "$GPU_MEM_GB" -ge 40 ]; then
            SGLANG_MEM_FRACTION_STATIC=0.7
        else
            SGLANG_MEM_FRACTION_STATIC=0.6
        fi
    fi
fi

if [ $((NUM_GPUS % CONTEXT_PARALLEL_SIZE)) -ne 0 ]; then
    echo "CONTEXT_PARALLEL_SIZE must divide NUM_GPUS; got CONTEXT_PARALLEL_SIZE=$CONTEXT_PARALLEL_SIZE NUM_GPUS=$NUM_GPUS"
    echo "Use --resource-profile auto or set --context-parallel-size explicitly for non-8-GPU machines."
    exit 1
fi

NVLINK_COUNT=$(nvidia-smi | grep -o "NVLink" | wc -l || true)
if [ "$NVLINK_COUNT" -gt 0 ]; then
    HAS_NVLINK=1
else
    HAS_NVLINK=0
fi

echo "RESOURCE_PROFILE=$RESOURCE_PROFILE MODEL_SIZE=$MODEL_SIZE"
echo "NUM_GPUS=$NUM_GPUS GPU_MEM_GB=$GPU_MEM_GB CONTEXT_PARALLEL_SIZE=$CONTEXT_PARALLEL_SIZE ROLLOUT_MAX_RESPONSE_LEN=$ROLLOUT_MAX_RESPONSE_LEN MAX_TOKENS_PER_GPU=$MAX_TOKENS_PER_GPU"
echo "ROLLOUT_BATCH_SIZE=$ROLLOUT_BATCH_SIZE N_SAMPLES_PER_PROMPT=$N_SAMPLES_PER_PROMPT OVER_SAMPLING_BATCH_SIZE=$OVER_SAMPLING_BATCH_SIZE SGLANG_SERVER_CONCURRENCY=$SGLANG_SERVER_CONCURRENCY SGLANG_MEM_FRACTION_STATIC=$SGLANG_MEM_FRACTION_STATIC"

source {q(profile["model_script"])}

export MASTER_ADDR=${{MASTER_ADDR:-"127.0.0.1"}}
export NO_PROXY="$NO_PROXY,$MASTER_ADDR"
export no_proxy="$NO_PROXY"
ray start --head --node-ip-address ${{MASTER_ADDR}} --num-gpus ${{NUM_GPUS}} --disable-usage-stats --dashboard-host=0.0.0.0 --dashboard-port=8265

python3 - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:8265/api/version"
last_error = None
for _ in range(90):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                sys.exit(0)
    except Exception as exc:
        last_error = exc
    time.sleep(1)

raise SystemExit("Ray dashboard did not become ready at {{}}: {{}}".format(url, last_error))
PY

RUNTIME_ENV_JSON="{{
  \\\"env_vars\\\": {{
    \\\"PYTHONPATH\\\": \\\"/root/Megatron-LM/\\\",
    \\\"CUDA_DEVICE_MAX_CONNECTIONS\\\": \\\"1\\\",
    \\\"NCCL_NVLS_ENABLE\\\": \\\"${{HAS_NVLINK}}\\\",
    \\\"PYTORCH_CUDA_ALLOC_CONF\\\": \\\"max_split_size_mb:1024\\\",
    \\\"http_proxy\\\": \\\"\\\",
    \\\"https_proxy\\\": \\\"\\\",
    \\\"all_proxy\\\": \\\"\\\",
    \\\"HTTP_PROXY\\\": \\\"\\\",
    \\\"HTTPS_PROXY\\\": \\\"\\\",
    \\\"ALL_PROXY\\\": \\\"\\\",
    \\\"NO_PROXY\\\": \\\"${{NO_PROXY}}\\\",
    \\\"no_proxy\\\": \\\"${{no_proxy}}\\\"
  }}
}}"

export SUBMISSION_ID={q(submission_id)}
ray job submit --address="http://127.0.0.1:8265" \
   --submission-id "${{SUBMISSION_ID}}" \
   --runtime-env-json="${{RUNTIME_ENV_JSON}}" \
   --no-wait \
   --log-style record \
   -- python3 train.py \
   --actor-num-nodes 1 \
   --actor-num-gpus-per-node ${{NUM_GPUS}} \
   --colocate \
   ${{MODEL_ARGS[@]}} \
   --hf-checkpoint {q(profile["hf_checkpoint"])} \
   --ref-load {q(profile["ref_load"])} \
   {load_arg} \
   --save {q(str(save_dir))} \
   --save-interval {args.save_interval} \
   --disable-rollout-global-dataset \
   --rlve \
   --environment-list {environment_args} \
   --custom-prompt-preprocessor ChatTemplate_NoSystemPrompt \
   --apply-chat-template \
   --rm-type rlve \
   --reward-key reward \
   --num-rollout {args.steps} \
   --rollout-batch-size ${{ROLLOUT_BATCH_SIZE}} \
   --n-samples-per-prompt ${{N_SAMPLES_PER_PROMPT}} \
   --rollout-max-response-len ${{ROLLOUT_MAX_RESPONSE_LEN}} \
   --rollout-temperature 1.0 \
   --over-sampling-batch-size ${{OVER_SAMPLING_BATCH_SIZE}} \
   {" ".join(dynamic_filter_args)} \
   --partial-rollout \
   --num-steps-per-rollout 1 \
   --wandb-always-use-train-step \
   --balance-data \
   --eval-interval {args.eval_interval} \
   {eval_only_arg} \
   --eval-prompt-data {eval_prompt_data_args} \
   --n-samples-per-eval-prompt 1 \
   --eval-top-p 0.7 \
   {"--eval-max-response-len " + q(args.eval_max_response_len) if args.eval_max_response_len is not None else ""} \
   --eval-input-key user_prompt \
   --eval-reward-key accuracy \
   --tensor-model-parallel-size 1 \
   --pipeline-model-parallel-size 1 \
   --context-parallel-size ${{CONTEXT_PARALLEL_SIZE}} \
   --expert-model-parallel-size 1 \
   --expert-tensor-parallel-size 1 \
   --recompute-granularity full \
   --recompute-method uniform \
   --recompute-num-layers 1 \
   --use-dynamic-batch-size \
   --max-tokens-per-gpu ${{MAX_TOKENS_PER_GPU}} \
   --advantage-estimator grpo \
   --entropy-coef 0.00 \
   --eps-clip 0.2 \
   --eps-clip-high 0.28 \
   --use-tis \
   --optimizer adam \
   --lr 2e-6 \
   --lr-decay-style constant \
   --weight-decay 0.01 \
   --adam-beta1 0.9 \
   --adam-beta2 0.98 \
   --use-wandb \
   --wandb-project {q(args.wandb_project)} \
   --wandb-group {q(args.run_name)} \
   --wandb-key "${{WANDB_API_KEY}}" \
   {"--wandb-mode " + q(args.wandb_mode) if args.wandb_mode else ""} \
   --rollout-num-gpus-per-engine 1 \
   --sglang-mem-fraction-static ${{SGLANG_MEM_FRACTION_STATIC}} \
   --sglang-server-concurrency ${{SGLANG_SERVER_CONCURRENCY}} \
   --attention-dropout 0.0 \
   --hidden-dropout 0.0 \
   --accumulate-allreduce-grads-in-fp32 \
   --attention-softmax-in-fp32 \
   --attention-backend flash \
   {" ".join(difficulty_args)} \
   {" ".join(rollout_function_args)}

python3 - <<'PY'
import json
import os
from pathlib import Path
import sys
import time
import urllib.request


base_url = "http://127.0.0.1:8265"
job_id = os.environ["SUBMISSION_ID"]
status_url = f"{{base_url}}/api/jobs/{{job_id}}"
logs_url = f"{{base_url}}/api/jobs/{{job_id}}/logs"
log_path = Path("/tmp/ray/session_latest/logs") / f"job-driver-{{job_id}}.log"
terminal_status = {{"SUCCEEDED", "FAILED", "STOPPED"}}
last_status = None
last_error = None
printed_log_bytes = 0


def stream_new_logs():
    global printed_log_bytes
    try:
        with urllib.request.urlopen(logs_url, timeout=5) as response:
            payload = json.load(response)
    except Exception:
        return

    logs = payload.get("logs") or ""
    if not logs:
        return
    data = logs.encode("utf-8", errors="replace")
    if len(data) <= printed_log_bytes:
        return
    chunk = data[printed_log_bytes:].decode("utf-8", errors="replace")
    print(chunk, end="" if chunk.endswith("\\n") else "\\n", flush=True)
    printed_log_bytes = len(data)

while True:
    status = None
    message = ""
    try:
        with urllib.request.urlopen(status_url, timeout=5) as response:
            payload = json.load(response)
        status = payload.get("status")
        message = payload.get("message") or ""
        last_error = None
    except Exception as exc:
        last_error = exc

    if status and status != last_status:
        print(f"Ray job {{job_id}} status: {{status}} {{message}}", flush=True)
        last_status = status
    elif last_error:
        print(f"Waiting for Ray job {{job_id}} status: {{last_error}}", flush=True)

    stream_new_logs()

    if status in terminal_status:
        if status == "SUCCEEDED":
            sys.exit(0)

        if log_path.exists():
            print(f"Last lines from {{log_path}}:", flush=True)
            lines = log_path.read_text(errors="replace").splitlines()
            for line in lines[-200:]:
                print(line, flush=True)
        raise SystemExit(f"Ray job {{job_id}} ended with status {{status}}: {{message}}")

    time.sleep(15)
PY
"""
    return bash


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb-project", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--environment-list", nargs="+", required=True)
    parser.add_argument("--model", choices=sorted(MODEL_PROFILES), default="openreasoning-nemotron-1.5b")
    parser.add_argument("--difficulty-mode", choices=("adaptive", "static"), default="adaptive")
    parser.add_argument("--static-min-difficulty", type=int, default=0)
    parser.add_argument("--static-max-difficulty", type=int, default=4)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--save-interval", type=int, default=10)
    parser.add_argument("--eval-interval", type=int, default=20)
    parser.add_argument("--eval-max-response-len", type=int, default=None)
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument(
        "--eval-prompt-data",
        nargs="+",
        default=["HELD-OUT_ENVIRONMENTS_128", "data/HELD-OUT_ENVIRONMENTS/test_128.json"],
    )
    parser.add_argument("--output-root", default="outputs/checkpoints")
    parser.add_argument("--load-dir", default=None)
    parser.add_argument("--resource-profile", choices=("repo", "auto"), default="repo")
    parser.add_argument("--wandb-mode", choices=("online", "offline", "disabled"), default=None)
    parser.add_argument("--dynamic-sampling-filter-path", default="slime.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std")
    parser.add_argument("--num-gpus", type=int, default=None)
    parser.add_argument("--gpu-mem-gb", type=int, default=None)
    parser.add_argument("--context-parallel-size", type=int, default=None)
    parser.add_argument("--rollout-max-response-len", type=int, default=None)
    parser.add_argument("--max-tokens-per-gpu", type=int, default=None)
    parser.add_argument("--rollout-batch-size", type=int, default=None)
    parser.add_argument("--n-samples-per-prompt", type=int, default=None)
    parser.add_argument("--over-sampling-batch-size", type=int, default=None)
    parser.add_argument("--sglang-server-concurrency", type=int, default=None)
    parser.add_argument("--sglang-mem-fraction-static", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.difficulty_mode == "static" and args.static_min_difficulty > args.static_max_difficulty :
        raise SystemExit("--static-min-difficulty must be <= --static-max-difficulty")

    command = build_command(args)
    if args.dry_run :
        try :
            print(command)
        except BrokenPipeError :
            pass
        return

    subprocess.run(["bash", "-lc", command], check=True)


if __name__ == "__main__" :
    main()
