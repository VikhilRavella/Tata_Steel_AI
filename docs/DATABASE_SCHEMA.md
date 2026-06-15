# Database Schema

The application uses SQLAlchemy with SQLite.

## Core Models

### User
Stores user accounts and RBAC details.
- `id`: Integer (Primary Key)
- `employee_id`: String (Unique)
- `role`: String ('engineer', 'supervisor', 'manager')
- `specialization`: String
- `department`: String
- `supervisor_id`: Integer (Foreign Key to User)
- `password_hash`: String

### Session
Tracks formal maintenance operations.
- `id`: String (UUID)
- `primary_engineer_id`: Integer (FK to User)
- `equipment_id`: Integer (FK to Equipment)
- `task_domain`: String
- `status`: String
- `started_at` / `ended_at`: DateTime

### Message
Chat messages within sessions.
- `id`: Integer
- `session_id`: String (FK to Session)
- `sender`: String
- `content`: Text
- `message_type`: String

### Equipment
Plant equipment registry.
- `id`: Integer
- `equipment_name`: String
- `health_status`: String
- `health_score`: Integer

## AI Support Models

### AgentMemory
Stores persistent agent knowledge.
- `session_id`: String
- `memory_type`: String
- `content`: Text

### RequirementProfile
Extracted requirements from engineering sessions.
- `session_id`: String
- `problem_statement`: Text
- `business_goal`: Text
- `constraints`: Text

### SandboxSession & AgentTransfer
Tracks informal sandbox chats and their escalation to formal sessions.

### Document & DocumentMetadata
Stores uploaded technical manuals, their physical paths, and ChromaDB vector chunk metadata.
