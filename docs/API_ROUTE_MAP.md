# API Route Map

## Authentication (`/api/auth`)
- `POST /api/auth/login` - Login with credentials
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/manager/create-supervisor` - Create a supervisor (Manager only)
- `POST /api/auth/supervisor/create-engineer` - Create an engineer (Supervisor only)

## AI Agents (`/api/agent`, `/api/engineering`, `/api/sandbox`)
- `POST /api/engineering/chat` - Chat with Engineering Agent (Streaming)
- `GET /api/engineering/context/{session_id}` - Retrieve agent memory context
- `GET /api/engineering/requirements/{session_id}` - Retrieve requirement profile
- `POST /api/sandbox/chat` - Chat with Sandbox Agent (Streaming)
- `POST /api/agent/analyze/bolt` - Bolt torque analysis
- `POST /api/agent/analyze/equipment` - Equipment diagnosis analysis

## Sessions (`/api/sessions`)
- `POST /api/sessions/` - Create a formal maintenance session
- `GET /api/sessions/history/list` - List session history
- `GET /api/sessions/{id}` - Get specific session details
- `POST /api/sessions/{id}/safety` - Verify session safety
- `POST /api/sessions/{id}/escalate` - Escalate session
- `DELETE /api/sessions/{id}` - Delete session

## Sandbox (`/api/sandbox`)
- `POST /api/sandbox/session` - Create sandbox session
- `GET /api/sandbox/sessions` - List sandbox sessions
- `POST /api/sandbox/upload` - Upload document to sandbox context
- `POST /api/sandbox/escalate` - Transfer sandbox context to formal engineering session

## Documents (`/api/documents`)
- `POST /api/documents/upload` - Upload a technical document
- `GET /api/documents/` - List all documents
- `GET /api/documents/{id}` - Get document metadata
- `DELETE /api/documents/{id}` - Delete a document

## Users & Roles (`/api/supervisor`, `/api/manager`, `/api/engineer`)
- `GET /api/manager/users` - List all users
- `POST /api/manager/users` - Create a user
- `GET /api/supervisor/team` - List team members
- `GET /api/supervisor/escalations` - List escalated sessions
- `GET /api/engineer/dashboard` - Get engineer metrics

## Equipment & Inventory (`/api/inventory`, `/api/alerts`)
- `GET /api/manager/equipment` - List equipment
- `GET /api/inventory/` - List spare parts
- `GET /api/alerts/` - List active alerts
- `WS /api/alerts/ws/` - WebSocket for real-time alerts
