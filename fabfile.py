from fabric import task
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.s3_sync import upload_to_s3_if_changed

# ------------------------
# GLOBAL CONFIG
# ------------------------
S3_DEPLOY_BUCKET = "my-deployment-artifacts"
S3_TFVARS_BUCKET = "s3://my-tfvars-bucket/env-tfvars"
LOCAL_TFVARS_PATH = "/opt/agent/agent-dev"
DEPLOY_FILES_PATH = "/opt/agent/agent-dev/deployments"
TF_BIN = "terraform"

STACKS = [
    "vpc", "eks", "rds", "monitoring", "app", "bastion",
    "network", "iam", "s3", "cloudfront", "dynamodb",
    "lambda", "api", "ecs", "logs", "metrics", "secrets",
    "ecr", "kinesis", "elasticache", "cdn", "edge", "batch",
    "vpn", "ad", "cloudtrail", "glue", "athena", "redshift", "config"
]

# ------------------------
# HELPERS
# ------------------------
def run_cmd(cmd):
    print(f"\n→ {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def get_tfvars_path(env):
    return f"{LOCAL_TFVARS_PATH}/{env}_v2.tfvars"

def ensure_tfvars(env):
    path = get_tfvars_path(env)
    if not os.path.exists(path):
        raise FileNotFoundError(f"tfvars not found: {path}. Run `fab sync_tfvars:{env}` first.")
    return path

# ------------------------
# FABRIC TASKS
# ------------------------
@task
def upload_artifacts(c, env):
    """Upload ZIP artifacts to S3 if changed."""
    uploads = []
    for file_name in os.listdir(DEPLOY_FILES_PATH):
        if file_name.endswith(".zip"):
            local_file = os.path.join(DEPLOY_FILES_PATH, file_name)
            s3_key = f"{env}/deployments/{file_name}"
            s3_uri = f"s3://{S3_DEPLOY_BUCKET}/{s3_key}"
            uploaded = upload_to_s3_if_changed(local_file, s3_uri)
            uploads.append((file_name, uploaded))

    print("\nSummary:")
    for name, uploaded in uploads:
        status = "uploaded" if uploaded else "skipped"
        print(f" - {name}: {status}")

@task
def sync_tfvars(c, env):
    """Sync tfvars from S3 to agent."""
    s3_path = f"{S3_TFVARS_BUCKET}/{env}_v2.tfvars"
    local_path = get_tfvars_path(env)
    run_cmd(f"aws s3 cp {s3_path} {local_path}")
    print(f"✅ Synced tfvars: {s3_path} → {local_path}")

@task
def plan_all(c, env, parallel=False):
    """Run Terraform plan for all stacks."""
    tfvars_file = ensure_tfvars(env)

    def plan_stack(stack):
        print(f"\n===== Planning {stack} ({env}) =====")
        path = f"./stacks/{stack}"
        backend_cfg = f"../../backend-config/{env}.config"
        tfplan_out = f"../../plans/{stack}-{env}.tfplan"

        run_cmd(f"cd {path} && rm -rf .terraform")
        run_cmd(f"cd {path} && {TF_BIN} init -input=false -reconfigure -backend-config={backend_cfg}")
        run_cmd(f"cd {path} && {TF_BIN} fmt -recursive")
        run_cmd(f"cd {path} && {TF_BIN} validate")
        run_cmd(f"cd {path} && {TF_BIN} plan -input=false -var-file={tfvars_file} -out={tfplan_out}")
        return f"{stack} planned"

    if parallel:
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = [executor.submit(plan_stack, s) for s in STACKS]
            for future in as_completed(results):
                print(f"✅ {future.result()}")
    else:
        for s in STACKS:
            plan_stack(s)

@task
def apply_all(c, env):
    """Apply all Terraform stacks."""
    for stack in STACKS:
        print(f"\n===== Applying {stack} ({env}) =====")
        path = f"./stacks/{stack}"
        tfplan_out = f"../../plans/{stack}-{env}.tfplan"
        run_cmd(f"cd {path} && {TF_BIN} apply -auto-approve {tfplan_out}")

@task
def destroy_all(c, env):
    """Destroy all stacks (use with care)."""
    tfvars_file = ensure_tfvars(env)
    for stack in reversed(STACKS):
        print(f"\n⚠️ Destroying {stack} ({env})")
        path = f"./stacks/{stack}"
        backend_cfg = f"../../backend-config/{env}.config"
        run_cmd(f"cd {path} && {TF_BIN} init -input=false -reconfigure -backend-config={backend_cfg}")
        run_cmd(f"cd {path} && {TF_BIN} destroy -auto-approve -var-file={tfvars_file}")
