# TF AVM Agent Web

React frontend for the Terraform Azure Verified Modules (AVM) Agent.

## Quick Start

```bash
npm install
npm run dev
```

The app will be available at http://localhost:5173

## Project Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui base components
│   ├── chat/            # Chat interface components
│   ├── services/        # Azure service selector
│   ├── diagram/         # Diagram upload and analysis
│   ├── code/            # Code viewer and file tree
│   └── layout/          # App shell (Header, Sidebar, MainLayout)
├── hooks/               # React hooks for API integration
├── lib/                 # API client and utilities
├── types/               # TypeScript type definitions
├── App.tsx              # Main app component with routing
└── main.tsx             # Entry point with providers
```

## Key Technologies

- **Vite** - Build tool and dev server
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library
- **TanStack Query** - Server state management
- **React Router** - Client-side routing
- **react-markdown** - Markdown rendering in chat
- **react-syntax-highlighter** - Code highlighting

## Environment Variables

Create a `.env.local` file:

```
VITE_API_URL=http://localhost:8000
```

## Features

1. **Chat Mode**: Conversational interface for interacting with the TF AVM Agent
2. **Service Selector**: Visual grid for selecting Azure services
3. **Diagram Upload**: Upload architecture diagrams for analysis
4. **Code Viewer**: View and download generated Terraform files

## API Integration

The frontend expects a backend API at `VITE_API_URL` with these endpoints:

- `POST /api/chat` - Send chat messages
- `POST /api/generate` - Generate Terraform from services
- `POST /api/analyze` - Analyze uploaded diagrams
- `GET /api/modules` - List/search AVM modules
- `WS /api/ws/chat` - WebSocket for streaming responses

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Docker / Container Build

A multi-stage `Dockerfile` is provided in this directory:

- **Stage 1 (build)** – Node 22 Alpine, runs `npm ci && npm run build`
- **Stage 2 (serve)** – nginx 1.27 Alpine, serves the static assets

The nginx config (`nginx.conf`) supports:
- SPA routing (all non-asset paths redirect to `index.html`)
- Runtime API proxy: requests to `/api/` are proxied to `$BACKEND_URL`

```bash
# Build the image locally
docker build -t tf-avm-agent-web:local .

# Run locally (proxying to a backend running on localhost:8000)
docker run -p 8080:80 -e BACKEND_URL=host.docker.internal:8000 tf-avm-agent-web:local
```

## Deploying to Azure Container Apps

Infrastructure-as-Code lives in `../deploy/` and uses
[Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/).

Resources provisioned:
| Resource | AVM module |
|---|---|
| Resource Group | `Azure/avm-res-resources-resourcegroup/azurerm` |
| Log Analytics Workspace | `Azure/avm-res-operationalinsights-workspace/azurerm` |
| Container Registry | `Azure/avm-res-containerregistry-registry/azurerm` |
| Container Apps Environment | `Azure/avm-res-app-managedenvironment/azurerm` |
| Container App (web) | `Azure/avm-res-app-containerapp/azurerm` |

### One-time setup

```bash
cd ../deploy
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your subscription ID and settings
terraform init
terraform apply
```

### CI/CD (GitHub Actions)

The workflow `.github/workflows/deploy-web.yml` runs automatically on every
push to `main` that touches `web/**` or `deploy/**`.  It also supports manual
triggers with an `environment` and optional `image_tag` input.

Required GitHub **secrets** (set per environment):
- `AZURE_CLIENT_ID` – service principal / workload identity client ID
- `AZURE_TENANT_ID` – Azure tenant ID
- `AZURE_SUBSCRIPTION_ID` – Azure subscription ID

Required GitHub **variables** (set per environment):
- `ACR_LOGIN_SERVER` – e.g. `crfoodev.azurecr.io`
- `BACKEND_URL` – e.g. `ca-tfavmagent-dev-api.internal.azurecontainerapps.io:80`
