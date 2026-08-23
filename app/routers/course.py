"""
Cloud Engineer 90-Day Course — FastAPI router.
Prefix: /course
"""
from __future__ import annotations
import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.course import CourseDay
from app.models.user import User
from app.routers.auth import get_optional_current_user

router = APIRouter(prefix="/course", tags=["course"])

# ── 90-Day plan seed data (from Cloud_Engineer_90_Day_Master_Tracker.xlsx) ─────

COURSE_DAYS = [
    # Week 1 — Foundations
    {"day": 1,  "week": 1, "domain": "Linux",      "topic": "Linux Basics",         "subtopic": "Filesystem, pwd, ls, cd, mkdir, rm",       "lab": "Ubuntu VM practice",        "resource_url": "https://kodekloud.com/courses/linux-for-beginners/",           "planned_hours": 3},
    {"day": 2,  "week": 1, "domain": "Linux",      "topic": "Permissions",          "subtopic": "chmod, chown, users, groups",               "lab": "Create users",              "resource_url": "https://linuxjourney.com/",                                    "planned_hours": 3},
    {"day": 3,  "week": 1, "domain": "Networking", "topic": "TCP/IP",               "subtopic": "OSI, TCP/IP, DNS, HTTP",                    "lab": "Packet capture",            "resource_url": "https://www.practicalnetworking.net/",                         "planned_hours": 3},
    {"day": 4,  "week": 1, "domain": "Git",        "topic": "Git & GitHub",         "subtopic": "Commit, Branch, Merge",                     "lab": "Push repo",                 "resource_url": "https://learngitbranching.js.org/",                            "planned_hours": 3},
    {"day": 5,  "week": 1, "domain": "AWS",        "topic": "IAM",                  "subtopic": "Users, Groups, Roles",                      "lab": "Create IAM",                "resource_url": "https://docs.aws.amazon.com/",                                 "planned_hours": 3},
    {"day": 6,  "week": 1, "domain": "AWS",        "topic": "EC2",                  "subtopic": "Launch EC2",                                "lab": "Deploy Node app",           "resource_url": "https://docs.aws.amazon.com/",                                 "planned_hours": 3},
    {"day": 7,  "week": 1, "domain": "Docker",     "topic": "Docker Basics",        "subtopic": "Images, Containers",                        "lab": "Dockerize app",             "resource_url": "https://docs.docker.com/get-started/",                         "planned_hours": 3},
    # Week 2
    {"day": 8,  "week": 2, "domain": "Terraform",  "topic": "Terraform",            "subtopic": "Providers, State",                          "lab": "Provision EC2",             "resource_url": "https://developer.hashicorp.com/terraform/tutorials",          "planned_hours": 3},
    {"day": 9,  "week": 2, "domain": "Kubernetes", "topic": "Pods",                 "subtopic": "Pods & Deployments",                        "lab": "Minikube",                  "resource_url": "https://kubernetes.io/docs/tutorials/",                        "planned_hours": 3},
    {"day": 10, "week": 2, "domain": "CI/CD",      "topic": "GitHub Actions",       "subtopic": "Workflow",                                  "lab": "Pipeline",                  "resource_url": "https://docs.github.com/actions",                              "planned_hours": 3},
    {"day": 11, "week": 2, "domain": "Linux",      "topic": "Processes",            "subtopic": "ps, top, kill, systemd, journalctl",        "lab": "Service management",        "resource_url": "https://linuxjourney.com/",                                    "planned_hours": 3},
    {"day": 12, "week": 2, "domain": "Linux",      "topic": "Shell Scripting",      "subtopic": "Bash scripts, loops, conditionals",         "lab": "Automate backups",          "resource_url": "https://www.shellscript.sh/",                                  "planned_hours": 3},
    {"day": 13, "week": 2, "domain": "Networking", "topic": "DNS & HTTP",           "subtopic": "DNS resolution, HTTP methods, curl",         "lab": "DNS lookup lab",            "resource_url": "https://www.cloudflare.com/learning/",                         "planned_hours": 3},
    {"day": 14, "week": 2, "domain": "AWS",        "topic": "S3",                   "subtopic": "Buckets, policies, versioning, lifecycle",   "lab": "Host static site on S3",    "resource_url": "https://docs.aws.amazon.com/s3/",                              "planned_hours": 3},
    # Week 3
    {"day": 15, "week": 3, "domain": "AWS",        "topic": "VPC",                  "subtopic": "Subnets, Route Tables, IGW, NAT",            "lab": "Build custom VPC",          "resource_url": "https://docs.aws.amazon.com/vpc/",                             "planned_hours": 3},
    {"day": 16, "week": 3, "domain": "AWS",        "topic": "RDS",                  "subtopic": "Multi-AZ, snapshots, parameter groups",     "lab": "Deploy PostgreSQL RDS",     "resource_url": "https://docs.aws.amazon.com/rds/",                             "planned_hours": 3},
    {"day": 17, "week": 3, "domain": "Docker",     "topic": "Dockerfile",           "subtopic": "Multi-stage builds, ENTRYPOINT vs CMD",     "lab": "Optimise image size",       "resource_url": "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/", "planned_hours": 3},
    {"day": 18, "week": 3, "domain": "Docker",     "topic": "Docker Compose",       "subtopic": "Multi-container apps, volumes, networks",   "lab": "MERN stack compose",        "resource_url": "https://docs.docker.com/compose/",                             "planned_hours": 3},
    {"day": 19, "week": 3, "domain": "Kubernetes", "topic": "Services",             "subtopic": "ClusterIP, NodePort, LoadBalancer",          "lab": "Expose deployment",         "resource_url": "https://kubernetes.io/docs/concepts/services-networking/",     "planned_hours": 3},
    {"day": 20, "week": 3, "domain": "Kubernetes", "topic": "Ingress",              "subtopic": "nginx ingress, TLS, path routing",           "lab": "Configure ingress",         "resource_url": "https://kubernetes.io/docs/concepts/services-networking/ingress/", "planned_hours": 3},
    {"day": 21, "week": 3, "domain": "Terraform",  "topic": "Variables & Outputs",  "subtopic": "Input vars, locals, outputs, tfvars",       "lab": "Modular Terraform",         "resource_url": "https://developer.hashicorp.com/terraform/language/values",    "planned_hours": 3},
    # Week 4
    {"day": 22, "week": 4, "domain": "Terraform",  "topic": "State & Backends",     "subtopic": "Remote state, S3 backend, state locking",   "lab": "Shared state with S3",      "resource_url": "https://developer.hashicorp.com/terraform/language/state",     "planned_hours": 3},
    {"day": 23, "week": 4, "domain": "Terraform",  "topic": "Modules",              "subtopic": "Module structure, registry, versioning",     "lab": "Create reusable module",    "resource_url": "https://registry.terraform.io/",                               "planned_hours": 3},
    {"day": 24, "week": 4, "domain": "CI/CD",      "topic": "Jenkins",              "subtopic": "Pipelines, Jenkinsfile, agents",             "lab": "Build Java app",            "resource_url": "https://www.jenkins.io/doc/",                                  "planned_hours": 3},
    {"day": 25, "week": 4, "domain": "CI/CD",      "topic": "Pipeline Stages",      "subtopic": "Build, Test, Scan, Push, Deploy stages",    "lab": "Full CI/CD pipeline",       "resource_url": "https://docs.github.com/en/actions/using-workflows",           "planned_hours": 3},
    {"day": 26, "week": 4, "domain": "Kubernetes", "topic": "ConfigMaps & Secrets", "subtopic": "Env vars, mounted files, external secrets",  "lab": "Inject DB creds",           "resource_url": "https://kubernetes.io/docs/concepts/configuration/",          "planned_hours": 3},
    {"day": 27, "week": 4, "domain": "Kubernetes", "topic": "Persistent Volumes",   "subtopic": "PV, PVC, StorageClass, StatefulSets",       "lab": "Stateful PostgreSQL pod",   "resource_url": "https://kubernetes.io/docs/concepts/storage/",                 "planned_hours": 3},
    {"day": 28, "week": 4, "domain": "AWS",        "topic": "CloudWatch",           "subtopic": "Metrics, Alarms, Logs, Dashboards",         "lab": "Monitor EC2 CPU",           "resource_url": "https://docs.aws.amazon.com/cloudwatch/",                      "planned_hours": 3},
    # Week 5
    {"day": 29, "week": 5, "domain": "AWS",        "topic": "Route 53",             "subtopic": "Hosted zones, A records, alias, health checks", "lab": "Domain routing",         "resource_url": "https://docs.aws.amazon.com/route53/",                         "planned_hours": 3},
    {"day": 30, "week": 5, "domain": "AWS",        "topic": "ALB",                  "subtopic": "Target groups, rules, sticky sessions",     "lab": "Load balance EC2 fleet",    "resource_url": "https://docs.aws.amazon.com/elasticloadbalancing/",            "planned_hours": 3},
    {"day": 31, "week": 5, "domain": "Python",     "topic": "Python Basics",        "subtopic": "Types, functions, loops, error handling",   "lab": "Script AWS cleanup",        "resource_url": "https://docs.python.org/3/tutorial/",                          "planned_hours": 3},
    {"day": 32, "week": 5, "domain": "Python",     "topic": "Boto3",                "subtopic": "EC2, S3, IAM via boto3",                    "lab": "Automate S3 uploads",       "resource_url": "https://boto3.amazonaws.com/v1/documentation/api/latest/",    "planned_hours": 3},
    {"day": 33, "week": 5, "domain": "Networking", "topic": "Subnetting",           "subtopic": "CIDR, subnet masks, IP planning",           "lab": "Design VPC subnets",        "resource_url": "https://www.practicalnetworking.net/",                         "planned_hours": 3},
    {"day": 34, "week": 5, "domain": "Networking", "topic": "Firewall & Security",  "subtopic": "iptables, Security Groups, NACLs",          "lab": "Restrict traffic rules",    "resource_url": "https://www.cloudflare.com/learning/",                         "planned_hours": 3},
    {"day": 35, "week": 5, "domain": "Kubernetes", "topic": "RBAC",                 "subtopic": "Roles, RoleBindings, ServiceAccounts",      "lab": "Least-privilege setup",     "resource_url": "https://kubernetes.io/docs/reference/access-authn-authz/rbac/","planned_hours": 3},
    # Week 6
    {"day": 36, "week": 6, "domain": "Kubernetes", "topic": "Helm",                 "subtopic": "Charts, values.yaml, release management",   "lab": "Deploy app with Helm",      "resource_url": "https://helm.sh/docs/",                                        "planned_hours": 3},
    {"day": 37, "week": 6, "domain": "CI/CD",      "topic": "ArgoCD",               "subtopic": "GitOps, sync, app definitions",             "lab": "Deploy via ArgoCD",         "resource_url": "https://argo-cd.readthedocs.io/",                              "planned_hours": 3},
    {"day": 38, "week": 6, "domain": "AWS",        "topic": "Lambda",               "subtopic": "Functions, triggers, layers, env vars",     "lab": "S3 trigger Lambda",         "resource_url": "https://docs.aws.amazon.com/lambda/",                          "planned_hours": 3},
    {"day": 39, "week": 6, "domain": "AWS",        "topic": "ECS / EKS",            "subtopic": "Fargate, task definitions, EKS node groups","lab": "Deploy container on ECS",   "resource_url": "https://docs.aws.amazon.com/ecs/",                             "planned_hours": 3},
    {"day": 40, "week": 6, "domain": "AWS",        "topic": "EBS & EFS",            "subtopic": "Volume types, snapshots, shared storage",   "lab": "Mount EFS to EC2",          "resource_url": "https://docs.aws.amazon.com/ebs/",                             "planned_hours": 3},
    {"day": 41, "week": 6, "domain": "Linux",      "topic": "SSH & Security",       "subtopic": "SSH keys, config, bastion host pattern",    "lab": "Secure SSH access",         "resource_url": "https://www.ssh.com/academy/",                                 "planned_hours": 3},
    {"day": 42, "week": 6, "domain": "Linux",      "topic": "Cron & Automation",    "subtopic": "Crontab, systemd timers, at command",       "lab": "Schedule backup script",    "resource_url": "https://linuxjourney.com/",                                    "planned_hours": 3},
    # Week 7
    {"day": 43, "week": 7, "domain": "Docker",     "topic": "Docker Networking",    "subtopic": "Bridge, host, overlay networks",            "lab": "Multi-host networking",     "resource_url": "https://docs.docker.com/network/",                             "planned_hours": 3},
    {"day": 44, "week": 7, "domain": "Docker",     "topic": "Docker Volumes",       "subtopic": "Named volumes, bind mounts, tmpfs",         "lab": "Persist DB data",           "resource_url": "https://docs.docker.com/storage/volumes/",                     "planned_hours": 3},
    {"day": 45, "week": 7, "domain": "Kubernetes", "topic": "HPA & Resource Limits","subtopic": "CPU/memory limits, HPA, VPA",              "lab": "Auto-scale deployment",     "resource_url": "https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/", "planned_hours": 3},
    {"day": 46, "week": 7, "domain": "Kubernetes", "topic": "Network Policies",     "subtopic": "Ingress/egress rules, Calico, Cilium",      "lab": "Isolate namespaces",        "resource_url": "https://kubernetes.io/docs/concepts/services-networking/network-policies/", "planned_hours": 3},
    {"day": 47, "week": 7, "domain": "Terraform",  "topic": "Workspaces",           "subtopic": "dev/staging/prod workspaces",               "lab": "Multi-env Terraform",       "resource_url": "https://developer.hashicorp.com/terraform/cli/workspaces",     "planned_hours": 3},
    {"day": 48, "week": 7, "domain": "AWS",        "topic": "CloudFormation",       "subtopic": "Templates, stacks, parameters, drift",      "lab": "Deploy VPC via CFn",        "resource_url": "https://docs.aws.amazon.com/cloudformation/",                  "planned_hours": 3},
    {"day": 49, "week": 7, "domain": "CI/CD",      "topic": "Testing in CI",        "subtopic": "Unit tests, integration tests, quality gates","lab": "Add pytest to pipeline",   "resource_url": "https://docs.pytest.org/",                                     "planned_hours": 3},
    # Week 8
    {"day": 50, "week": 8, "domain": "AWS",        "topic": "Auto Scaling",         "subtopic": "Launch templates, ASG, scaling policies",   "lab": "Scale on CPU alarm",        "resource_url": "https://docs.aws.amazon.com/autoscaling/",                     "planned_hours": 3},
    {"day": 51, "week": 8, "domain": "AWS",        "topic": "SQS & SNS",            "subtopic": "Queues, topics, fan-out patterns",           "lab": "Decouple app with SQS",     "resource_url": "https://docs.aws.amazon.com/sqs/",                             "planned_hours": 3},
    {"day": 52, "week": 8, "domain": "Linux",      "topic": "Logs & Monitoring",    "subtopic": "journalctl, rsyslog, log shipping",          "lab": "Ship logs to CloudWatch",   "resource_url": "https://www.loggly.com/ultimate-guide/linux-logging-basics/",   "planned_hours": 3},
    {"day": 53, "week": 8, "domain": "Python",     "topic": "Python Automation",    "subtopic": "Paramiko, Fabric, subprocess",               "lab": "Remote SSH automation",     "resource_url": "https://www.paramiko.org/",                                    "planned_hours": 3},
    {"day": 54, "week": 8, "domain": "Networking", "topic": "VPN & Peering",        "subtopic": "Site-to-site VPN, VPC peering, Transit GW",  "lab": "Connect two VPCs",          "resource_url": "https://docs.aws.amazon.com/vpn/",                             "planned_hours": 3},
    {"day": 55, "week": 8, "domain": "Kubernetes", "topic": "Monitoring",           "subtopic": "Prometheus, Grafana, kube-state-metrics",    "lab": "Dashboard cluster health",  "resource_url": "https://prometheus.io/docs/",                                  "planned_hours": 3},
    {"day": 56, "week": 8, "domain": "Kubernetes", "topic": "Logging",              "subtopic": "EFK stack, Loki, log aggregation",           "lab": "Centralise pod logs",        "resource_url": "https://www.elastic.co/what-is/elk-stack",                     "planned_hours": 3},
    # Week 9
    {"day": 57, "week": 9, "domain": "AWS",        "topic": "Security Best Practices","subtopic": "GuardDuty, Security Hub, AWS Config",     "lab": "Enable GuardDuty",          "resource_url": "https://docs.aws.amazon.com/guardduty/",                       "planned_hours": 3},
    {"day": 58, "week": 9, "domain": "AWS",        "topic": "KMS & Secrets Manager","subtopic": "Key rotation, envelope encryption",          "lab": "Encrypt RDS with KMS",      "resource_url": "https://docs.aws.amazon.com/kms/",                             "planned_hours": 3},
    {"day": 59, "week": 9, "domain": "Docker",     "topic": "Image Security",       "subtopic": "Trivy, Docker Scout, distroless images",    "lab": "Scan image vulnerabilities","resource_url": "https://aquasecurity.github.io/trivy/",                        "planned_hours": 3},
    {"day": 60, "week": 9, "domain": "CI/CD",      "topic": "Security in CI",       "subtopic": "SAST, DAST, secret scanning, Snyk",         "lab": "Add Snyk to pipeline",      "resource_url": "https://snyk.io/",                                             "planned_hours": 3},
    {"day": 61, "week": 9, "domain": "Terraform",  "topic": "Security & Compliance","subtopic": "tfsec, Checkov, OPA policies",              "lab": "Scan Terraform code",       "resource_url": "https://github.com/aquasecurity/tfsec",                        "planned_hours": 3},
    {"day": 62, "week": 9, "domain": "AWS",        "topic": "Cost Optimisation",    "subtopic": "Cost Explorer, Budgets, Savings Plans",     "lab": "Identify waste",            "resource_url": "https://aws.amazon.com/aws-cost-management/",                  "planned_hours": 3},
    {"day": 63, "week": 9, "domain": "Kubernetes", "topic": "Cluster Upgrades",     "subtopic": "Rolling upgrade strategy, kubeadm",         "lab": "Upgrade control plane",     "resource_url": "https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/", "planned_hours": 3},
    # Week 10
    {"day": 64, "week": 10,"domain": "Projects",   "topic": "Project 1",            "subtopic": "Deploy MERN app on AWS EC2 + Nginx",        "lab": "Full deployment",           "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 4},
    {"day": 65, "week": 10,"domain": "Projects",   "topic": "Project 1",            "subtopic": "Add HTTPS with Let's Encrypt",              "lab": "SSL setup",                 "resource_url": "https://letsencrypt.org/",                                     "planned_hours": 3},
    {"day": 66, "week": 10,"domain": "Projects",   "topic": "Project 1",            "subtopic": "Set up CloudWatch alarms & dashboards",     "lab": "Observability",             "resource_url": "https://docs.aws.amazon.com/cloudwatch/",                      "planned_hours": 3},
    {"day": 67, "week": 10,"domain": "Projects",   "topic": "Project 2",            "subtopic": "Dockerize MERN — multi-stage Dockerfile",   "lab": "Build optimised image",     "resource_url": "https://docs.docker.com/",                                     "planned_hours": 4},
    {"day": 68, "week": 10,"domain": "Projects",   "topic": "Project 2",            "subtopic": "docker-compose with Nginx reverse proxy",   "lab": "Full compose stack",        "resource_url": "https://docs.docker.com/compose/",                             "planned_hours": 3},
    {"day": 69, "week": 10,"domain": "Projects",   "topic": "Project 2",            "subtopic": "Push image to ECR, deploy on ECS Fargate",  "lab": "Container on cloud",        "resource_url": "https://docs.aws.amazon.com/ecs/",                             "planned_hours": 3},
    {"day": 70, "week": 10,"domain": "Projects",   "topic": "Project 3",            "subtopic": "Terraform: provision VPC + EC2 + RDS",      "lab": "IaC full stack",            "resource_url": "https://developer.hashicorp.com/terraform/tutorials",          "planned_hours": 4},
    # Week 11
    {"day": 71, "week": 11,"domain": "Projects",   "topic": "Project 3",            "subtopic": "Terraform remote state + S3 backend",       "lab": "Team-friendly state",       "resource_url": "https://developer.hashicorp.com/terraform/language/state/remote","planned_hours": 3},
    {"day": 72, "week": 11,"domain": "Projects",   "topic": "Project 3",            "subtopic": "Terraform modules + workspace per env",      "lab": "DRY infrastructure",        "resource_url": "https://developer.hashicorp.com/terraform/language/modules",   "planned_hours": 3},
    {"day": 73, "week": 11,"domain": "Projects",   "topic": "Project 4",            "subtopic": "Kubernetes: deploy on Minikube/EKS",         "lab": "Production-like cluster",   "resource_url": "https://kubernetes.io/docs/tutorials/",                        "planned_hours": 4},
    {"day": 74, "week": 11,"domain": "Projects",   "topic": "Project 4",            "subtopic": "Helm chart for app, ConfigMap & Secrets",    "lab": "Helm-managed deploy",       "resource_url": "https://helm.sh/",                                             "planned_hours": 3},
    {"day": 75, "week": 11,"domain": "Projects",   "topic": "Project 4",            "subtopic": "HPA + Prometheus + Grafana dashboards",      "lab": "Autoscale & observe",       "resource_url": "https://prometheus.io/",                                       "planned_hours": 3},
    {"day": 76, "week": 11,"domain": "Projects",   "topic": "Project 5",            "subtopic": "Full CI/CD: GitHub Actions → ECR → ECS",    "lab": "End-to-end pipeline",       "resource_url": "https://docs.github.com/actions",                              "planned_hours": 4},
    {"day": 77, "week": 11,"domain": "Projects",   "topic": "Project 5",            "subtopic": "Add SAST (Snyk) + image scan to pipeline",  "lab": "Secure pipeline",           "resource_url": "https://snyk.io/",                                             "planned_hours": 3},
    # Week 12 — Job prep
    {"day": 78, "week": 12,"domain": "Interview",  "topic": "Linux Interview Q&A",  "subtopic": "Top 30 Linux interview questions",          "lab": "Mock interview practice",   "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 3},
    {"day": 79, "week": 12,"domain": "Interview",  "topic": "AWS Interview Q&A",    "subtopic": "Top 30 AWS interview questions",            "lab": "Mock interview practice",   "resource_url": "https://roadmap.sh/aws",                                       "planned_hours": 3},
    {"day": 80, "week": 12,"domain": "Interview",  "topic": "Docker Interview Q&A", "subtopic": "Top 20 Docker interview questions",         "lab": "Mock interview practice",   "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 3},
    {"day": 81, "week": 12,"domain": "Interview",  "topic": "K8s Interview Q&A",    "subtopic": "Top 20 Kubernetes interview questions",     "lab": "Mock interview practice",   "resource_url": "https://roadmap.sh/kubernetes",                                "planned_hours": 3},
    {"day": 82, "week": 12,"domain": "Interview",  "topic": "Terraform Interview Q&A","subtopic": "Top 15 Terraform interview questions",   "lab": "Mock interview practice",   "resource_url": "https://developer.hashicorp.com/terraform",                    "planned_hours": 3},
    {"day": 83, "week": 12,"domain": "Interview",  "topic": "CI/CD Interview Q&A",  "subtopic": "Top 15 CI/CD interview questions",          "lab": "Mock interview practice",   "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 3},
    {"day": 84, "week": 12,"domain": "Interview",  "topic": "System Design Basics", "subtopic": "Scalability, availability, CAP theorem",    "lab": "Design MERN deployment",    "resource_url": "https://github.com/donnemartin/system-design-primer",          "planned_hours": 4},
    # Week 13 — Polish & apply
    {"day": 85, "week": 13,"domain": "Career",     "topic": "Resume Review",        "subtopic": "Tailor for cloud roles, ATS keywords",      "lab": "Update resume",             "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 3},
    {"day": 86, "week": 13,"domain": "Career",     "topic": "Portfolio",            "subtopic": "GitHub README, project documentation",      "lab": "Document all 5 projects",   "resource_url": "https://docs.github.com/",                                     "planned_hours": 3},
    {"day": 87, "week": 13,"domain": "Career",     "topic": "LinkedIn",             "subtopic": "Headline, about, skills, endorsements",     "lab": "Optimise profile",          "resource_url": "https://www.linkedin.com/",                                    "planned_hours": 2},
    {"day": 88, "week": 13,"domain": "Career",     "topic": "Apply & Network",      "subtopic": "Job boards, cold outreach, referrals",      "lab": "Apply to 10 jobs",          "resource_url": "https://roadmap.sh/devops",                                    "planned_hours": 2},
    {"day": 89, "week": 13,"domain": "Interview",  "topic": "Mock Full Interview",  "subtopic": "60-min full interview simulation",          "lab": "Record & review",           "resource_url": "https://interviewing.io/",                                     "planned_hours": 3},
    {"day": 90, "week": 13,"domain": "Career",     "topic": "Day 90 — Reflect",     "subtopic": "Review journey, plan next 30 days",         "lab": "Write a blog post",         "resource_url": "https://dev.to/",                                              "planned_hours": 2},
]

DOMAIN_META = {
    "Linux":      {"icon": "🐧", "color": "#f59e0b"},
    "Networking": {"icon": "🌐", "color": "#22d3ee"},
    "Git":        {"icon": "🔀", "color": "#f97316"},
    "AWS":        {"icon": "☁️", "color": "#f97316"},
    "Docker":     {"icon": "🐳", "color": "#0ea5e9"},
    "Terraform":  {"icon": "🏗️", "color": "#8b5cf6"},
    "Kubernetes": {"icon": "⚓", "color": "#6366f1"},
    "Python":     {"icon": "🐍", "color": "#10b981"},
    "CI/CD":      {"icon": "🔄", "color": "#10b981"},
    "Projects":   {"icon": "🛠️", "color": "#ec4899"},
    "Interview":  {"icon": "🎤", "color": "#f43f5e"},
    "Career":     {"icon": "💼", "color": "#a855f7"},
}


import urllib.parse

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CourseDayOut(BaseModel):
    id: str
    day: int
    week: int
    domain: str
    topic: str
    subtopic: Optional[str]
    lab: Optional[str]
    resource_url: Optional[str]
    youtube_url: Optional[str] = None
    planned_hours: int
    completed: bool
    completed_date: Optional[date]
    notes: Optional[str]
    domain_icon: str
    domain_color: str

    class Config:
        from_attributes = True


class CourseDayUpdate(BaseModel):
    completed: Optional[bool] = None
    notes: Optional[str] = None
    youtube_url: Optional[str] = None


# ── Course Design Schemas ─────────────────────────────────────────────────────

class CourseDayCreate(BaseModel):
    day: int
    week: int
    domain: str
    topic: str
    subtopic: Optional[str] = None
    lab: Optional[str] = None
    resource_url: Optional[str] = None
    youtube_url: Optional[str] = None
    planned_hours: int = 3


class CourseDesignSave(BaseModel):
    days: List[CourseDayCreate]


class AITopicSuggestRequest(BaseModel):
    domain: str
    week_num: int
    day_num: int
    duration_days: int
    course_name: Optional[str] = None
    context: Optional[str] = None


class AIGenerateQuestionsRequest(BaseModel):
    topic: str
    duration_days: int = 30


class AIGenerateCourseRequest(BaseModel):
    topic: str
    duration_days: int = 30
    answers: Optional[dict] = None
    context: Optional[str] = None


class CourseStatsOut(BaseModel):
    total_days: int
    completed_days: int
    completion_pct: float
    current_week: int
    current_day: int
    weeks_done: int
    domains_completed: dict
    planned_hours_total: int
    planned_hours_done: int
    streak_days: int


DOMAIN_PALETTE = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316",
    "#f59e0b", "#10b981", "#14b8a6", "#0ea5e9", "#22d3ee", "#84cc16", "#a855f7",
]


def _domain_icon(name: str) -> str:
    name_lower = (name or "").lower()
    map_icons = {
        "frontend": "🖥️", "backend": "⚙️", "fullstack": "💻", "javascript": "🟨", "typescript": "🔷",
        "react": "⚛️", "nextjs": "▲", "node": "🟢", "python": "🐍", "database": "🗄️", "sql": "📊",
        "postgres": "🐘", "mongodb": "🍃", "devops": "🔄", "cloud": "☁️", "aws": "🟧", "docker": "🐳",
        "kubernetes": "⚓", "terraform": "🏗️", "linux": "🐧", "networking": "🌐", "git": "🔀",
        "security": "🔒", "api": "🔌", "testing": "🧪", "project": "🛠️", "capstone": "🏆",
        "interview": "🎤", "career": "💼", "ai": "🤖", "ml": "🧠", "data": "📈", "mobile": "📱",
        "flutter": "💙", "design": "🎨", "system": "📐", "architecture": "🏛️",
    }
    for k, v in map_icons.items():
        if k in name_lower:
            return v
    return "📚"


def _domain_color(name: str) -> str:
    if not name:
        return "#6366f1"
    h = sum(ord(c) for c in name)
    return DOMAIN_PALETTE[h % len(DOMAIN_PALETTE)]


def _enrich(day: CourseDay) -> dict:
    icon = _domain_icon(day.domain)
    color = _domain_color(day.domain)
    d = {c.name: getattr(day, c.name) for c in day.__table__.columns}
    d["domain_icon"] = icon
    d["domain_color"] = color
    # Fallback youtube_url if missing
    if not d.get("youtube_url") and d.get("topic"):
        q = f"{day.domain} {day.topic} tutorial"
        d["youtube_url"] = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
    return d


def _seed_course(db: Session):
    if db.query(CourseDay).count() == 0:
        for entry in COURSE_DAYS:
            db.add(CourseDay(id=str(uuid.uuid4()), **entry))
        db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/days", response_model=List[CourseDayOut])
def list_days(
    week: Optional[int] = None,
    domain: Optional[str] = None,
    completed: Optional[bool] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    q = db.query(CourseDay)
    if user:
        # Check if user has their own custom days
        user_days_count = db.query(CourseDay).filter(CourseDay.user_id == user.id).count()
        if user_days_count > 0:
            q = q.filter(CourseDay.user_id == user.id)
        else:
            q = q.filter((CourseDay.user_id == user.id) | (CourseDay.user_id.is_(None)))
    if week:
        q = q.filter(CourseDay.week == week)
    if domain:
        q = q.filter(CourseDay.domain == domain)
    if completed is not None:
        q = q.filter(CourseDay.completed == completed)
    return [_enrich(d) for d in q.order_by(CourseDay.day).all()]


@router.patch("/days/{day_id}", response_model=CourseDayOut)
def update_day(day_id: str, body: CourseDayUpdate, db: Session = Depends(get_db)):
    day = db.query(CourseDay).filter(CourseDay.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    if body.completed is not None:
        day.completed = body.completed
        day.completed_date = date.today() if body.completed else None
        if body.completed:
            try:
                _award_course_xp_and_badges(db, day)
            except Exception:
                pass
    if body.notes is not None:
        day.notes = body.notes
    if body.youtube_url is not None:
        day.youtube_url = body.youtube_url
    db.commit()
    db.refresh(day)
    try:
        sync_topics_from_course(db)
    except Exception:
        pass
    return _enrich(day)


def _award_course_xp_and_badges(db: Session, day: CourseDay):
    from app.models.cloudprep import Achievement

    # 1. Base XP for completing the daily lesson
    db.add(Achievement(
        id=str(uuid.uuid4()),
        achievement_type="xp",
        xp_amount=50,
        description=f"Completed Day {day.day}: {day.topic}",
    ))

    # 2. Check milestone badge thresholds
    completed_days = db.query(CourseDay).filter(CourseDay.completed == True).all()
    completed_count = len(completed_days)
    total_days = db.query(CourseDay).count()

    existing_badges = {
        r[0] for r in db.query(Achievement.badge_id).filter(Achievement.achievement_type == "badge").all()
        if r[0]
    }

    def grant_badge(badge_id: str, name: str, icon: str, desc: str, bonus_xp: int = 50):
        if badge_id not in existing_badges:
            db.add(Achievement(
                id=str(uuid.uuid4()),
                achievement_type="badge",
                badge_id=badge_id,
                badge_name=name,
                badge_icon=icon,
                xp_amount=bonus_xp,
                description=desc,
            ))
            existing_badges.add(badge_id)

    if completed_count >= 1:
        grant_badge("first_lesson", "First Step", "🌱", "Completed your very first course lesson!", 50)
    if completed_count >= 3:
        grant_badge("momentum_builder", "Momentum Builder", "⚡", "Completed 3 course lessons!", 75)

    week_1_days = db.query(CourseDay).filter(CourseDay.week == 1).all()
    if week_1_days and all(d.completed for d in week_1_days):
        grant_badge("week_1_master", "Week 1 Master", "🔥", "Completed all lessons in Week 1!", 100)

    if total_days > 0 and (completed_count / total_days) >= 0.5:
        grant_badge("halfway_hero", "Halfway Hero", "🚀", "Reached 50% completion of your course!", 200)

    if total_days > 0 and completed_count == total_days:
        grant_badge("course_graduate", "Course Champion", "👑", "Completed 100% of your course!", 500)

    db.flush()


@router.get("/stats", response_model=CourseStatsOut)
def course_stats(db: Session = Depends(get_db)):
    all_days = db.query(CourseDay).order_by(CourseDay.day).all()
    completed = [d for d in all_days if d.completed]
    total = len(all_days)
    done = len(completed)

    # Streak
    completed_dates = sorted({d.completed_date for d in completed if d.completed_date})
    streak = 0
    if completed_dates:
        check = date.today()
        for d in reversed(completed_dates):
            if d == check:
                streak += 1
                check = date(check.year, check.month, check.day - 1) if check.day > 1 else check
            else:
                break

    # Current progress
    current_day = done + 1 if done < total else total
    current_week = next((d.week for d in all_days if d.day == current_day), 13)

    # Domain breakdown
    domains_completed = {}
    domain_totals = {}
    for d in all_days:
        domain_totals[d.domain] = domain_totals.get(d.domain, 0) + 1
        if d.completed:
            domains_completed[d.domain] = domains_completed.get(d.domain, 0) + 1

    domain_pcts = {
        dom: round((domains_completed.get(dom, 0) / tot) * 100, 1)
        for dom, tot in domain_totals.items()
    }

    hours_done = sum(d.planned_hours for d in completed)
    hours_total = sum(d.planned_hours for d in all_days)

    return {
        "total_days": total,
        "completed_days": done,
        "completion_pct": round(done / total * 100, 1) if total else 0,
        "current_week": current_week,
        "current_day": current_day,
        "weeks_done": max(0, current_week - 1),
        "domains_completed": domain_pcts,
        "planned_hours_total": hours_total,
        "planned_hours_done": hours_done,
        "streak_days": streak,
    }


@router.get("/today", response_model=Optional[CourseDayOut])
def today_task(db: Session = Depends(get_db)):
    next_day = db.query(CourseDay).filter(CourseDay.completed == False).order_by(CourseDay.day).first()
    return _enrich(next_day) if next_day else None


@router.get("/week/{week_num}", response_model=List[CourseDayOut])
def week_plan(week_num: int, db: Session = Depends(get_db)):
    days = db.query(CourseDay).filter(CourseDay.week == week_num).order_by(CourseDay.day).all()
    return [_enrich(d) for d in days]


# ── Course Design Endpoints ───────────────────────────────────────────────────

@router.get("/design/status")
def design_status(db: Session = Depends(get_db)):
    """Check whether the user has designed a course yet."""
    count = db.query(CourseDay).count()
    return {"has_course": count > 0, "total_days": count}


def sync_topics_from_course(db: Session):
    """
    Syncs LearningTopic table in cloudprep from the current CourseDay records.
    If CourseDay has days, replaces/updates cloudprep_topics with the domains
    and subtopics from the course.
    """
    from app.models.cloudprep import LearningTopic

    course_days = db.query(CourseDay).order_by(CourseDay.day).all()
    if not course_days:
        return

    domain_map: dict = {}
    for d in course_days:
        if d.domain not in domain_map:
            domain_map[d.domain] = []
        domain_map[d.domain].append(d)

    db.query(LearningTopic).delete()
    db.flush()

    order_idx = 1
    for domain_name, days in domain_map.items():
        completed_count = sum(1 for d in days if d.completed)
        progress = (completed_count / len(days) * 100) if days else 0.0

        sub_topics = [
            {
                "name": f"Day {d.day}: {d.topic}",
                "progress_pct": 100.0 if d.completed else 0.0,
                "order": d.day,
                "completed": bool(d.completed),
            }
            for d in days
        ]

        icon = _domain_icon(domain_name)
        color = _domain_color(domain_name)

        db.add(LearningTopic(
            id=str(uuid.uuid4()),
            name=domain_name,
            icon=icon,
            color=color,
            order=order_idx,
            progress_pct=round(progress, 1),
            sub_topics=sub_topics,
            total_study_minutes=sum(d.planned_hours * 60 for d in days if d.completed),
        ))
        order_idx += 1

    db.commit()


@router.post("/design/save")
def design_save(
    body: CourseDesignSave,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Save a course design.
    Smart merge: for days where (day_number, domain) matches a previously
    completed day, the completed flag and date are preserved.
    All other days are reset.
    """
    user_id = user.id if user else None

    # Query existing completed days for this user
    q_existing = db.query(CourseDay).filter(CourseDay.completed == True)
    if user_id:
        q_existing = q_existing.filter((CourseDay.user_id == user_id) | (CourseDay.user_id.is_(None)))

    existing_completed: dict = {
        (d.day, d.domain): {
            "completed": d.completed,
            "completed_date": d.completed_date,
            "notes": d.notes,
        }
        for d in q_existing.all()
    }

    # Wipe existing course for this user
    if user_id:
        db.query(CourseDay).filter(CourseDay.user_id == user_id).delete()
    else:
        db.query(CourseDay).delete()
    db.flush()

    # Insert new days, restoring progress where applicable
    for entry in body.days:
        key = (entry.day, entry.domain)
        preserved = existing_completed.get(key, {})
        yt = entry.youtube_url
        if not yt and entry.topic:
            q = f"{entry.domain} {entry.topic} tutorial"
            yt = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
        db.add(CourseDay(
            id=str(uuid.uuid4()),
            user_id=user_id,
            day=entry.day,
            week=entry.week,
            domain=entry.domain,
            topic=entry.topic,
            subtopic=entry.subtopic,
            lab=entry.lab,
            resource_url=entry.resource_url,
            youtube_url=yt,
            planned_hours=entry.planned_hours,
            completed=preserved.get("completed", False),
            completed_date=preserved.get("completed_date"),
            notes=preserved.get("notes"),
        ))

    db.commit()

    # Automatically synchronize CloudPrep learning topics & subtopics from the new course
    try:
        sync_topics_from_course(db)
    except Exception:
        pass

    return {"saved": len(body.days)}


@router.delete("/days", status_code=204)
def reset_course(db: Session = Depends(get_db)):
    """Hard-reset the course (removes all days including progress)."""
    db.query(CourseDay).delete()
    db.commit()
    try:
        from app.models.cloudprep import LearningTopic
        db.query(LearningTopic).delete()
        db.commit()
    except Exception:
        pass


@router.post("/ai-suggest")
def ai_suggest_topic(body: AITopicSuggestRequest):
    """Use the AI Mentor to suggest a topic for a given day slot."""
    import json
    import re
    from app.services.cloudprep_ai import mentor_reply

    course_label = body.course_name or "learning"
    prompt = (
        f"I am designing a {body.duration_days}-day {course_label} course. "
        f"For Day {body.day_num} in Week {body.week_num}, I want to cover the '{body.domain}' topic area. "
        f"{'Additional context: ' + body.context + '. ' if body.context else ''}"
        f"Suggest a specific, concise topic name, key subtopics/concepts to cover (comma-separated), "
        f"a short hands-on exercise or project description, an official documentation resource URL, and a YouTube tutorial video search/watch link. "
        f"Respond ONLY with valid JSON using exactly these keys: "
        f'{{"topic": "...", "subtopic": "...", "lab": "...", "resource_url": "https://...", "youtube_url": "https://www.youtube.com/..."}}'
    )

    try:
        reply = mentor_reply(prompt, [], body.domain)
        match = re.search(r'\{[^{}]*"topic"[^{}]*\}', reply, re.DOTALL)
        if match:
            data = json.loads(match.group())
            top = data.get("topic", f"{body.domain} Fundamentals")
            yt = data.get("youtube_url")
            if not yt:
                yt = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(body.domain + ' ' + top + ' tutorial')}"
            return {
                "topic": top,
                "subtopic": data.get("subtopic", ""),
                "lab": data.get("lab", ""),
                "resource_url": data.get("resource_url", ""),
                "youtube_url": yt,
            }
    except Exception:
        pass

    top = f"{body.domain} — Day {body.day_num}"
    return {
        "topic": top,
        "subtopic": f"Core {body.domain} concepts and practices",
        "lab": f"Hands-on {body.domain} exercise",
        "resource_url": "https://roadmap.sh",
        "youtube_url": f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(body.domain + ' tutorial')}",
    }


@router.post("/ai-generate-questions")
def ai_generate_questions_endpoint(body: AIGenerateQuestionsRequest):
    """Generate clarifying questions to customize a course."""
    from app.services.cloudprep_ai import generate_course_questions
    questions = generate_course_questions(body.topic, body.duration_days)
    return {"questions": questions}


@router.post("/ai-generate-course")
def ai_generate_course_endpoint(body: AIGenerateCourseRequest):
    """Generate a complete day-by-day course plan using AI."""
    from app.services.cloudprep_ai import generate_full_course
    result = generate_full_course(body.topic, body.duration_days, body.answers, body.context)
    return result

