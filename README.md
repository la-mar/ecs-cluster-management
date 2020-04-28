# ecs-cluster-management

Serverless functions for ECS cluster management using [Chalice](https://github.com/aws/chalice)

## Functions

1. Routinely check all cluster instances and terminate those that have a disconnected ECS agent

## Chalice Configuration

```json
{
  "version": "2.0",
  "app_name": "ecs-cluster-management",
  "lambda_memory_size": 128,
  "lambda_timeout": 300,
  "reserved_concurrency": 1,
  "api_gateway_stage": "api",
  "manage_iam_role": false,
  "iam_role_arn": "arn:aws:iam::<account_id>:role/ecs-cluster-management-role",
  "environment_variables": {
    "PYTHONPATH": "./chalicelib:./:$PYTHONPATH",
    "APP_NAME": "ecs-cluster-management"
  },
  "subnet_ids": ["<subnet-1>", "<subnet-2>", "...", "<subnet-n>"],
  "security_group_ids": ["<security-group-name>"],
  "tags": {
    "service_name": "ecs-cluster-management",
    "terraform": "false",
    "environment": "prod"
  }
}
```
