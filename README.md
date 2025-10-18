# Infra Orchestrator (Fabric + Azure Pipelines)

## Overview
This project centralizes orchestration of Terraform stacks using Fabric.
It integrates with Azure Pipelines and AWS Service Connections to manage IaC deployments across multiple environments.

## Key Features
- Syncs tfvars from S3
- Uploads zip artifacts to S3 (checksum deduplication)
- Runs terraform plan/apply/destroy across multiple stacks
- Designed for Azure DevOps resource repositories

## Usage
Run locally:
```bash
poetry install
poetry run fab plan_all:dev1
```


## Project Structure

```
infra-orchestrator/
├── utils/
│   └── s3_sync.py
├── fabfile.py
├── pyproject.toml
├── azure-pipelines.yml
└── README.md










