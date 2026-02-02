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
