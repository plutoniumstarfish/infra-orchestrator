# infra-orchestrator
Orchestrator using fabric/ fabtask


infra-orchestrator/
├── fabfile.py
├── utils/
│   ├── __init__.py
│   └── s3_sync.py
├── stacks/
│   ├── vpc/
│   ├── eks/
│   ├── rds/
│   ├── app/
│   ├── monitoring/
│   └── ... (30 stacks total)
├── backend-config/
│   ├── dev1.config
│   ├── qa1.config
│   ├── uat.config
│   └── prod.config
├── tfvars/
│   └── ...
├── plans/
│   └── ...
├── pyproject.toml
└── README.md
