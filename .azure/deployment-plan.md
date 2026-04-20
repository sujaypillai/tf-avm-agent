# Azure Deployment Plan

> **Status:** Planning

Generated: 2026-04-20

---

## 1. Project Overview

**Goal:** Deploy the full tf-avm-agent solution (MCP server backend + React web frontend) to Azure Container Apps.

**Path:** Modernize Existing — The project already has a partial Terraform deployment (`deploy/`) that provisions infra for the **web frontend only**. This plan extends it to deploy the **complete solution**: both the MCP backend API and the web frontend as two Container Apps sharing a single Container Apps Environment.

---

## 2. Requirements

| Attribute        | Value                                  |
| ---------------- | -------------------------------------- |
| Classification   | Development (initial deployment)       |
| Scale            | Small (single-region, low traffic)     |
| Budget           | Cost-Optimized                         |
| **Subscription** | `bfafcd7f-e975-442d-bb77-1a727f794e23` |
| **Location**     | `swedencentral`                        |

---

## 3. Components Detected

| Component                | Type             | Technology                             | Path                     | Docker?                |
| ------------------------ | ---------------- | -------------------------------------- | ------------------------ | ---------------------- |
| **MCP Server (Backend)** | API / MCP Server | Python 3.12, FastMCP, FastAPI, Uvicorn | `server/main.py`, `src/` | ✅ `Dockerfile` (root) |
| **Web Frontend**         | Frontend SPA     | React, Vite, Tailwind, Nginx           | `web/`                   | ✅ `web/Dockerfile`    |

---

## 4. Recipe Selection

**Selected:** Terraform (extend existing `deploy/` configuration)

**Rationale:**

- The project already has a working Terraform setup in `deploy/` using AVM modules
- The infrastructure is partially built (RG, ACR, CAE, web Container App)
- The project **is** a Terraform AVM agent — using Terraform is natural and consistent
- Only needs extension: add a second Container App for the MCP backend + secrets configuration
- No need for `azd init` — would conflict with existing Terraform state

---

## 5. Architecture

**Stack:** Containers (Azure Container Apps)

### Architecture Diagram

```
                     External MCP Clients
                     (VS Code, Claude.ai)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Azure Resource Group                              │
│                    rg-tfavmagent-dev                                 │
│                                                                     │
│  ┌───────────────────────────────────┐                              │
│  │  API Management (APIM)             │                              │
│  │  apim-tfavmagent-dev               │                              │
│  │  SKU: Developer (dev) / Std v2     │                              │
│  │                                    │                              │
│  │  /mcp/* ──▶ MCP backend            │                              │
│  │  Policies: rate-limit, auth,       │                              │
│  │            subscription-key        │                              │
│  └──────────────┬────────────────────┘                              │
│                 │                                                    │
│  ┌──────────────┼───────────────────────────────────────────────┐   │
│  │  Container Apps Environment                                   │   │
│  │  cae-tfavmagent-dev                                           │   │
│  │              │                                                 │   │
│  │  ┌───────────▼─────────┐    ┌──────────────────────────────┐ │   │
│  │  │  ca-...-api          │    │  ca-...-web                  │ │   │
│  │  │  (MCP Server)        │    │  (React Frontend)            │ │   │
│  │  │                      │    │                              │ │   │
│  │  │  uvicorn:8000        │◀───│  nginx:80 (external)         │ │   │
│  │  │  Ingress: internal   │    │  Ingress: external           │ │   │
│  │  │  Image: api:latest   │    │  Image: web:latest           │ │   │
│  │  └──────────────────────┘    └──────────────────────────────┘ │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Container Registry│  │ Log Analytics     │  │ Key Vault        │  │
│  │ cr<name>          │  │ log-tfavmagent-dev│  │ kv-tfavmagent-dev│  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                     ┌──────────────────────┐
                     │  Azure OpenAI Service │
                     │  (External SaaS)      │
                     └──────────────────────┘
```

**Traffic Flow:**

1. **External MCP clients** (VS Code, Claude.ai) → APIM gateway (`/mcp/*`) → Container App API (internal, port 8000)
2. **Web frontend users** → Container App Web (external, port 80) → Container App API (internal, port 8000) via nginx proxy
3. APIM provides: subscription-key auth, rate limiting, request logging, and optional IP filtering

### Service Mapping

| Component          | Azure Service              | SKU / Config                                       |
| ------------------ | -------------------------- | -------------------------------------------------- |
| **API Gateway**    | Azure API Management       | Developer (dev) / StandardV2 (prod)                |
| MCP Backend API    | Azure Container App        | 0.5 vCPU / 1Gi, 1–3 replicas, **internal ingress** |
| Web Frontend       | Azure Container App        | 0.25 vCPU / 0.5Gi, 1–3 replicas, external ingress  |
| Container Registry | Azure Container Registry   | Basic                                              |
| Orchestration      | Container Apps Environment | Consumption                                        |
| Logging            | Log Analytics Workspace    | Per-GB                                             |
| **Azure OpenAI**   | Azure Cognitive Services   | OpenAI, S0, gpt-4o deployment (30K TPM)            |
| Secrets            | Azure Key Vault            | Standard                                           |

### Supporting Services

| Service                       | Purpose                                                               |
| ----------------------------- | --------------------------------------------------------------------- |
| **API Management**            | Gateway for external MCP clients — auth, rate limiting, logging (NEW) |
| **Log Analytics Workspace**   | Centralized container logs & metrics (already in Terraform)           |
| **Azure Key Vault**           | Store `AZURE_OPENAI_API_KEY`, `MCP_API_KEY` securely (NEW)            |
| **Managed Identity (System)** | All services get system-assigned MI for ACR pull + Key Vault access   |
| **Azure OpenAI**              | LLM inference — provisioned in this plan (swedencentral, gpt-4o)      |

---

## 6. Gap Analysis — What Exists vs. What's Needed

### Current State (`deploy/main.tf`)

| Resource                          | Status                                       |
| --------------------------------- | -------------------------------------------- |
| Resource Group                    | ✅ Exists                                    |
| Log Analytics Workspace           | ✅ Exists                                    |
| Container Registry                | ✅ Exists                                    |
| Container Apps Environment        | ✅ Exists                                    |
| Container App — Web (frontend)    | ✅ Exists                                    |
| Container App — API (MCP backend) | ❌ **Missing**                               |
| Azure OpenAI (Cognitive Services) | ❌ **Missing** — deploy new in swedencentral |
| API Management                    | ❌ **Missing** (Phase 2)                     |
| Key Vault (for secrets)           | ❌ **Missing**                               |
| ACR Push CI/CD                    | ❌ **Missing** (manual docker push today)    |

### Changes Required

| #   | Change                            | File                              | Description                                                                                                                                                                           |
| --- | --------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Add MCP backend Container App** | `deploy/main.tf`                  | New `module "container-app-api"` using `avm-res-app-containerapp` with **internal ingress** on port 8000, env vars for Azure OpenAI                                                   |
| 2   | **Add API Management**            | `deploy/main.tf`                  | New `azurerm_api_management` resource (Developer SKU for dev), with system-assigned MI                                                                                                |
| 3   | **Add APIM API + backend**        | `deploy/main.tf`                  | `azurerm_api_management_api` importing MCP endpoint, `azurerm_api_management_backend` pointing to the internal CA API FQDN                                                            |
| 4   | **Add APIM policies**             | `deploy/main.tf`                  | Rate limiting, subscription-key validation, CORS for MCP clients                                                                                                                      |
| 5   | **Add Key Vault**                 | `deploy/main.tf`                  | New `module "key-vault"` using `avm-res-keyvault-vault` to store `AZURE_OPENAI_API_KEY`                                                                                               |
| 6   | **Add Key Vault secrets**         | `deploy/main.tf`                  | `azurerm_key_vault_secret` resources for each secret                                                                                                                                  |
| 7   | **Add RBAC for Key Vault**        | `deploy/main.tf`                  | Key Vault Secrets User role for Container App API managed identity                                                                                                                    |
| 8   | **Add ACR Pull role for API**     | `deploy/main.tf`                  | `azurerm_role_assignment` for the API container's system MI                                                                                                                           |
| 9   | **Add new variables**             | `deploy/variables.tf`             | `azure_openai_endpoint`, `azure_openai_deployment`, `azure_openai_api_key` (sensitive), `publisher_name`, `publisher_email`, `apim_sku`, `api_image_name`, `api_container_cpu/memory` |
| 10  | **Add new outputs**               | `deploy/outputs.tf`               | APIM gateway URL, API container internal FQDN, Key Vault URI                                                                                                                          |
| 11  | **Wire web→api backend_url**      | `deploy/main.tf`                  | Set `backend_url` env var on web container to point at the API container's internal FQDN                                                                                              |
| 12  | **Update tfvars example**         | `deploy/terraform.tfvars.example` | Add new variables with example values                                                                                                                                                 |

---

## 7. Provisioning Limit Checklist

### Phase 1: Resource Inventory

| Resource Type                            | Number to Deploy | Total After Deployment | Limit/Quota       | Notes                           |
| ---------------------------------------- | ---------------- | ---------------------- | ----------------- | ------------------------------- |
| Microsoft.App/managedEnvironments        | 0 (exists)       | 1                      | 15/subscription   | Already deployed                |
| Microsoft.App/containerApps              | 1 (new API)      | 2                      | 100/environment   | Adding MCP backend (Phase 1)    |
| Microsoft.ApiManagement/service          | 1 (new)          | 1                      | 20/subscription   | Developer SKU ~15 min (Phase 2) |
| Microsoft.ContainerRegistry/registries   | 0 (exists)       | 1                      | 100/subscription  | Already deployed                |
| Microsoft.OperationalInsights/workspaces | 0 (exists)       | 1                      | 100/subscription  | Already deployed                |
| Microsoft.KeyVault/vaults                | 1 (new)          | 1                      | 1000/subscription | New addition                    |
| Microsoft.Resources/resourceGroups       | 0 (exists)       | 1                      | 980/subscription  | Already deployed                |

> Phase 2 (actual limit verification) will be done during execution via `azure-quotas` skill.

---

## 8. Security Considerations

| Area                   | Approach                                                                                                         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Secrets**            | Stored in Key Vault, referenced via managed identity — no env-var plaintext                                      |
| **Container Registry** | Admin disabled, ACR Pull via system-assigned managed identity                                                    |
| **Ingress — API**      | **Internal** — only reachable within CAE (web frontend); APIM added in Phase 2 for external MCP clients          |
| **APIM Gateway (P2)**  | External MCP clients go through APIM with subscription-key auth, rate limiting (calls/min), and request logging  |
| **APIM → CA (P2)**     | APIM backend points to the API Container App's internal FQDN (`ca-...-api.internal.<env>.azurecontainerapps.io`) |
| **MCP Auth**           | Dual-layer: APIM subscription key (external) + optional `MCP_API_KEY` (app-level)                                |
| **Azure OpenAI**       | Prefer Entra ID auth (`DefaultAzureCredential`) over API key where possible                                      |
| **Non-root**           | Dockerfile already runs as UID 10001                                                                             |
| **Health Probes**      | `GET /health` endpoint configured in Dockerfile HEALTHCHECK                                                      |

---

## 9. Deployment Workflow

```
1. terraform init -backend-config=...
2. terraform plan -var-file=terraform.tfvars
3. terraform apply
4. az acr login --name <acr>
5. docker build -t <acr>.azurecr.io/tf-avm-agent-api:latest .
6. docker build -t <acr>.azurecr.io/tf-avm-agent-web:latest ./web
7. docker push <acr>.azurecr.io/tf-avm-agent-api:latest
8. docker push <acr>.azurecr.io/tf-avm-agent-web:latest
9. az containerapp update ... (trigger new revision)
```

---

## 10. Open Questions for User

### Phase 1 (blocking — needed to implement core infra)

1. ~~**Azure Subscription & Region**~~ → ✅ Subscription: `bfafcd7f-e975-442d-bb77-1a727f794e23`, Region: `swedencentral`
2. ~~**API Ingress**~~ → ✅ External via APIM (Phase 2), MCP backend Container App uses **internal ingress**
3. ~~**Azure OpenAI**~~ → ✅ Deploy new Azure OpenAI resource in swedencentral (gpt-4o, 30K TPM)
4. ~~**Key Vault**~~ → ✅ Use Key Vault for all secrets (Azure OpenAI key stored in KV, referenced via MI)

### Phase 2 (deferred — APIM, can answer later)

5. **APIM SKU** — Developer (cheap, no SLA) or StandardV2 (99.95% SLA)?
6. **APIM Publisher** — What publisher name and email for the APIM instance?

### Optional

7. **CI/CD** — Do you want a GitHub Actions workflow for automated build + push + deploy?

---

## Outputs (after execution)

| Artifact               | Location                                                          |
| ---------------------- | ----------------------------------------------------------------- |
| Phase 1 Terraform      | `deploy/main.tf`, `deploy/variables.tf`, `deploy/outputs.tf`      |
| Phase 2 Terraform      | `deploy/apim.tf` (separate file, added after Phase 1 is deployed) |
| Updated tfvars example | `deploy/terraform.tfvars.example`                                 |
| Deployment plan        | `.azure/deployment-plan.md`                                       |
