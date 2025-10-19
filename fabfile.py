from fabric import task
import subprocess
import os
from utils.s3_sync import upload_to_s3_if_changed

# Environment paths (these are set in Azure Pipeline env vars)
STACKS_PATH = os.getenv("FAB_STACKS_PATH", "/opt/iac/stacks")
BACKEND_PATH = os.path.join(STACKS_PATH, "../backend-config")
LOCAL_TFVARS_PATH = "/opt/agent/agent-dev"
DEPLOY_FILES_PATH = "/opt/agent/agent-dev/deployments"

# S3 configuration
S3_TFVARS_BUCKET = "s3://my-tfvars-bucket/env-tfvars"
S3_DEPLOY_BUCKET = "my-deployment-artifacts"


def run_cmd(cmd):
    """Executes shell command with logging."""
    print(f"\n→ {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def get_tfvars_path(env):
    """Return full path of local tfvars."""
    return f"{LOCAL_TFVARS_PATH}/{env}_v2.tfvars"


@task
def sync_tfvars(c, env):
    """
    Sync tfvars from S3 to agent path.
    Example: fab sync_tfvars:dev1
    """
    s3_path = f"{S3_TFVARS_BUCKET}/{env}_v2.tfvars"
    local_path = get_tfvars_path(env)
    run_cmd(f"aws s3 cp {s3_path} {local_path}")
    print(f"✅ Synced tfvars: {s3_path} → {local_path}")


@task
def upload_artifacts(c, env):
    """
    Upload zip deployment files to S3 if changed.
    Example: fab upload_artifacts:dev1
    """
    print(f"📦 Checking deployment zips in {DEPLOY_FILES_PATH}...")
    for file_name in os.listdir(DEPLOY_FILES_PATH):
        if file_name.endswith(".zip"):
            local_file = os.path.join(DEPLOY_FILES_PATH, file_name)
            s3_key = f"{env}/deployments/{file_name}"
            s3_uri = f"s3://{S3_DEPLOY_BUCKET}/{s3_key}"
            upload_to_s3_if_changed(local_file, s3_uri)


@task
def plan_stack(c, env, stack):
    """
    Terraform plan for a single stack.
    Example: fab plan_stack:dev1,vpc
    """
    tfvars_file = get_tfvars_path(env)
    path = f"{STACKS_PATH}/{stack}"
    backend_cfg = f"{BACKEND_PATH}/{env}.config"
    tfplan_out = f"{path}/plan-{env}.tfplan"

    print(f"\n===== Terraform PLAN for {stack} ({env}) =====")
    run_cmd(f"cd {path} && rm -rf .terraform")
    run_cmd(f"cd {path} && terraform init -input=false -reconfigure -backend-config={backend_cfg}")
    run_cmd(f"cd {path} && terraform fmt -recursive")
    run_cmd(f"cd {path} && terraform validate")
    run_cmd(f"cd {path} && terraform plan -input=false -var-file={tfvars_file} -out={tfplan_out}")


@task
def apply_stack(c, env, stack):
    """
    Terraform apply for a single stack.
    Example: fab apply_stack:dev1,vpc
    """
    path = f"{STACKS_PATH}/{stack}"
    tfplan_out = f"{path}/plan-{env}.tfplan"
    print(f"\n===== Terraform APPLY for {stack} ({env}) =====")
    run_cmd(f"cd {path} && terraform apply -auto-approve {tfplan_out}")


@task
def destroy_stack(c, env, stack):
    """
    Terraform destroy for a single stack.
    Example: fab destroy_stack:qa1,vpc
    """
    tfvars_file = get_tfvars_path(env)
    path = f"{STACKS_PATH}/{stack}"
    backend_cfg = f"{BACKEND_PATH}/{env}.config"
    print(f"\n⚠️ Destroying stack: {stack} ({env})")
    run_cmd(f"cd {path} && terraform init -input=false -reconfigure -backend-config={backend_cfg}")
    run_cmd(f"cd {path} && terraform destroy -auto-approve -var-file={tfvars_file}")
