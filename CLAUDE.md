# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YourWork is an **Enterprise Project Management System** built with Python 3.12+ and FastAPI. It follows a minimalist design philosophy with only two external dependencies (FastAPI and uvicorn), using Python's built-in modules for everything else (sqlite3, hashlib, logging, json, uuid, datetime, os).

**Key architectural principle:** All business logic resides in a single `main.py` file (~2500 lines) for transparency and maintainability. The application uses a monolithic design with clear separation through modular directories.

## Development Commands

### Starting the Server
```bash
# Windows
start.bat

# Linux/Mac
./start.sh

# Direct (requires dependencies installed and database initialized)
python main.py
```

The application will be available at:
- Main app: http://localhost:8001
- API docs: http://localhost:8001/docs
- WebSocket: ws://localhost:8001/ws?token={session_token}

**Note:** The actual port is 8001 (configured in main.py), not 8000 as shown in start scripts.

### Database Operations
```bash
# Initialize database (creates tables, default admin user, and test data)
python init_db.py
```

Default credentials after initialization: `admin` / `admin123`

### Testing
```bash
# Run all tests
python test/test_runner.py

# Run specific test types
python test/test_runner.py --type unit        # Unit tests only
python test/test_runner.py --type integration # Integration tests only
python test/test_runner.py --type system      # System tests only

# Run specific test
python test/test_runner.py --type specific --test test.unit.test_database

# Run WebSocket tests
python test/run_websocket_tests.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Single-File Structure
`main.py` (~2460 lines) contains all business logic organized into clear sections:
- **Database functions** (get_db, row_to_dict, rows_to_list) - Direct SQLite3 access with Row factory
- **Utility functions** (generate_id, password hashing, format_file_size_static)
- **Authentication/authorization** (get_current_user, check_permission) - Cookie-based token auth with RBAC
- **API route handlers** (~50 endpoints) - All /api/v1/* routes (users, projects, milestones, deliverables, messages)
- **WebSocket endpoint handler** (websocket_endpoint) - Single endpoint that delegates to websocket/ module
- **Frontend route handlers** - Serve HTML templates for all pages
- **Background tasks** (check_milestone_deadlines) - Startup event runs periodic deadline checks
- **Logging functions** (log_api_request, log_response) - All API calls logged to file and database

### WebSocket Module
The `websocket/` directory handles real-time functionality:
- `manager.py` - Connection lifecycle, heartbeat, session management
- `handlers.py` - Message routing via ACTION_HANDLERS dictionary (each action maps to a handler function)
- `auth.py` - WebSocket authentication (validates user token from query params)
- `schemas.py` - Message models (WSRequest/WSResponse) and constants (ACTION_HANDLERS, WS_SESSION_TIMEOUT)

Key WebSocket concepts:
- Each user can have only one active connection (old connections are closed)
- Session timeout enforced via `WS_SESSION_TIMEOUT` constant
- Heartbeat mechanism for connection health
- All actions logged to `ws_logs` table

**WebSocket test structure mirrors the main test suite:**
- `test/websocket/unit/` - Schema validation, auth, handler logic
- `test/websocket/integration/` - Connection timeout, message broadcast, API integration
- `test/websocket/system/` - Full workflow scenarios

### Database Schema
SQLite database with tables for:
- `users`, `roles`, `user_roles` - Authentication and RBAC
- `sessions` - Session token management (token, user_id, expires_at, is_revoked)
- `projects`, `project_members` - Project management
- `milestones`, `milestone_dependencies`, `milestone_logs` - Milestone tracking
- `deliverables` - File attachments
- `messages` - User notifications
- `ws_logs` - WebSocket activity audit

### API Design
- **Base URL**: `/api/v1`
- **Authentication**: Cookie-based with session token (NOT user_id directly)
- **Session Management**: See `session.py` for token creation, validation, and revocation
- **Response format**: `{"code": 0, "message": "...", "data": {...}}`
- **Role-based access**: SYSTEM_ADMIN, ADMIN, WORKER
- **Logging**: All API calls logged via `log_api_request()` and `log_response()`

### Directory Layout
```
YourWork/
├── main.py              # Single-file application (all business logic)
├── session.py           # Session token management (avoids circular imports)
├── init_db.py           # Database initialization
├── requirements.txt     # Dependencies (only fastapi + uvicorn)
├── websocket/           # WebSocket implementation
├── templates/           # HTML templates (no templating engine)
├── static/              # CSS, JS, images
├── data/                # SQLite database files
├── uploads/             # User-uploaded files
├── logs/                # Application logs
├── test/                # Test suite (unit/integration/system)
└── doc/                 # Documentation
```

### Configuration Constants
Located at top of `main.py`:
- `DB_PATH = "data/yourwork.db"` - Database location
- `LOG_PATH = "logs/app.log"` - Log file location
- `UPLOAD_PATH = "uploads/projects"` - File upload directory
- `SESSION_TOKEN_LENGTH = 64` - Session token length
- `SESSION_DEFAULT_DURATION_HOURS = 24` - Default session duration
- `SESSION_CLEANUP_INTERVAL_MINUTES = 60` - Session cleanup interval

### File Naming
- All snake_case (no camelCase conversions)
- Chinese comments for better readability
- Clear, descriptive names

### Key Design Decisions
1. **No ORM** - Direct SQLite3 usage via `sqlite3` module with `conn.row_factory = sqlite3.Row`
2. **No templating engine** - Pure HTML files with manual rendering (FastAPI's HTMLResponse)
3. **Synchronous processing** - For easier debugging (no async/await in business logic, only in FastAPI route wrappers)
4. **Minimal dependencies** - Only FastAPI + uvicorn, everything else is built-in
5. **Comprehensive logging** - All API calls and WebSocket actions logged to both file (logs/app.log) and database
6. **Pure JavaScript frontend** - No frameworks, uses browser's native Fetch API and WebSocket APIs (static/js/)
7. **Status state machine** - Milestone status changes are validated through `validate_status_change()` with complex rules
8. **Session-based auth** - Secure token-based authentication with `session.py` module (NOT direct user_id exposure)

## Session Authentication Architecture

The system implements secure session-based authentication (replacing the previous insecure user_id-as-token approach):

### Session Module (`session.py`)
- **Purpose**: Standalone module to avoid circular imports between main.py and websocket/
- **Functions**:
  - `create_session(user_id, duration_hours)` - Generate 64-char random token
  - `validate_session(token)` - Validate token, check expiration/revocation, return user info
  - `revoke_session(token)` - Mark session as revoked (for logout)
  - `cleanup_expired_sessions()` - Remove expired/revoked sessions (called by background task)

### Session Lifecycle
1. **Login** (HTTP or WebSocket): `create_session()` generates random token, stores in `sessions` table
2. **Authentication**: `validate_session()` checks token exists, not expired, not revoked
3. **Auto-renewal**: Each validation updates `last_used_at` timestamp
4. **Logout**: `revoke_session()` marks `is_revoked = 1`
5. **Cleanup**: Background task runs every 60 minutes to delete old sessions

### Security Improvements
- **Before**: Token = user_id (predictable, never expires, cannot be revoked)
- **After**: Token = 64-char random string (expires in 24h, can be revoked)

### Integration Points
- **HTTP API**: Login endpoint sets cookie with session token, `get_current_user()` calls `validate_session()`
- **WebSocket**: `authenticate_websocket()` calls `validate_session()`, `system.login` and `system.logout` handlers
- **Background**: `cleanup_sessions_background()` task started in `@app.on_event("startup")`

## Milestone Status Flow

The system implements a complex milestone state machine with dependency tracking:

**Status transitions (validated in `validate_status_change()`):**
- `PENDING` → `IN_PROGRESS` (always allowed)
- `IN_PROGRESS` → `PENDING` (only if no dependent milestones)
- `IN_PROGRESS` → `COMPLETED` (all dependencies must be completed)
- `COMPLETED` → `IN_PROGRESS` (only if no dependent milestones)
- Any status → `CANCELLED` (checks for dependency conflicts)

**Types:** TASK (任务), DELIVERABLE (交付物), PHASE (阶段)

**Milestone items (deliverables within milestones):** Have their own status tracking
- `PENDING` → `IN_PROGRESS` → `COMPLETED` → `VERIFIED`

## Development Principles

**From `.cursorrules` and project culture:**

1. **Large Changes Require Planning & Approval**
   - Use EnterPlanMode tool for multi-file implementations or architectural decisions
   - Small changes (typos, single functions, clear bugs) can proceed without planning

2. **Testing Requirements for Large Changes**
   - Unit tests in `test/unit/` - Test individual functions/modules
   - Integration tests in `test/integration/` - Test API flows and multi-step operations
   - System tests in `test/system/` - End-to-end scenarios, security, concurrent users
   - WebSocket tests: `test/websocket/unit/`, `test/websocket/integration/`, `test/websocket/system/`
   - All tests run via `test/test_runner.py`

3. **Naming Consistency**
   - Use `snake_case` everywhere (Python and JavaScript)
   - No `camelCase` in frontend code (static/js/*.js uses snake_case for functions/variables)
   - Keep variable/function/file names consistent across backend and frontend

4. **Dependency Management**
   - Prefer native/built-in modules over external libraries
   - Only use external libraries when you can access and understand their source code
   - Avoid "black box" libraries unless absolutely necessary
   - Current external dependencies: FastAPI + uvicorn only

5. **Avoid Circular Imports**
   - Session functionality is in `session.py` (NOT in main.py) to prevent circular imports
   - WebSocket modules import from `session`, NOT from `main`
   - If adding shared functionality, create a separate module to avoid main.py ↔ websocket/ circular dependencies
