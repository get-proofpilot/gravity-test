# ProofPilot Agency Hub — Project Context

## What This Is
ProofPilot Agency Hub is an SEO operations dashboard UI for an AI-powered SEO agency tool. It allows agency owners to manage clients, run AI-powered SEO workflows, monitor agent tasks, and generate ad creative — all from a single dashboard.

## Current State
- **Frontend only** — all data is hardcoded mock data in `script.js`
- **No backend yet** — workflows launch but don't call any real APIs
- **No Claude integration yet** — the agent terminal is a simulated typewriter animation

## Stack
- Pure HTML / CSS / JavaScript (no frameworks, no build step)
- `index.html` — all views and markup
- `style.css` — all styles (dark-blue / electric-blue / neon-green brand)
- `script.js` — data models, view routing, rendering, terminal animation

## Brand
- **Name:** ProofPilot Agency Hub
- **Colors:** Dark Blue `#00184D`, Electric Blue `#0051FF`, Neon Green `#C8FF00`
- **Fonts:** Bebas Neue (display), Martian Mono (code/mono), Inter (body)

## Views
| View | Route | Description |
|------|-------|-------------|
| Dashboard | `dashboard` | KPIs, agent terminal, task queue, client roster, alerts, ad preview |
| Workflows | `workflows` | 8 SEO workflow cards + run launcher |
| Clients | `clients` | Client table with search |
| Agent Tasks | `jobs` | Job list with progress bars + filter tabs |
| Reports | `reports` | Report cards grid |
| Content | `content` | Content pieces grid |
| Activity Log | `logs` | Terminal-style log stream |
| Ad Studio | `ads` | Ad creative cards |
| Campaigns | `campaigns` | Placeholder |

## Key Functions (script.js)
- `showView(viewId)` — SPA routing
- `renderDashboard()` — renders all dashboard panels
- `launchWorkflow()` — creates a job (currently mock only)
- `startTerminal()` — typewriter animation for agent terminal
- `toggleAgent()` — pause/resume agent state

## Next Steps (Planned)
1. Wire `launchWorkflow()` to real Claude API calls via a lightweight backend
2. Stream real Claude output into the agent terminal
3. Connect "Generate New Ad" button to Claude for real ad creative generation
4. Replace hardcoded mock data with a real data layer

## Working in This Repo
- Open `index.html` directly in a browser — no build step needed
- All edits to `script.js` or `style.css` reflect immediately on refresh
- When adding real Claude API calls, a backend (Python/Node) will be needed since the API key cannot live in the browser
