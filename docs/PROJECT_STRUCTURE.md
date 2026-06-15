Group 1 — Root files like main files config files docker files
FILE: .env.example | PURPOSE: Template showing required environment variables | WHY: Developers copy this to .env to configure their environment
FILE: add_casual_filter.py | PURPOSE: Adds casual message detection filter | WHY: One-time feature script
FILE: audit_chat.py | PURPOSE: Audits chat functionality | WHY: Debug utility
FILE: audit_dom.py | PURPOSE: Audits DOM elements | WHY: Debug utility
FILE: check_console.py | PURPOSE: Checks for console errors | WHY: Debug utility
FILE: check_routes.py | PURPOSE: Checks registered API routes | WHY: Debug utility
FILE: check_sandbox.py | PURPOSE: Checks sandbox agent functionality | WHY: Debug utility
FILE: clean_db.py | PURPOSE: Clears specific tables in the database | WHY: Quick reset during development
FILE: concat_files.py | PURPOSE: Concatenates multiple files | WHY: Debug utility
FILE: delete_user.py | PURPOSE: Deletes a specific user | WHY: Admin utility for cleaning up test users
FILE: docker-compose.yml | PURPOSE: Orchestrates Docker services | WHY: Single command startup for the entire application stack
FILE: Dockerfile | PURPOSE: Defines the Docker image for the backend | WHY: Needed to containerize the backend service
FILE: eng_script_fixed.js | PURPOSE: Fixed version of engineering agent JavaScript | WHY: Backup script
FILE: eng_script.js | PURPOSE: Standalone copy of engineering agent JavaScript | WHY: Backup script
FILE: fix_all_syntax.py | PURPOSE: Fixes syntax errors across files | WHY: One-time repair script
FILE: fix_async_session_import.py | PURPOSE: Fixes async session import errors | WHY: One-time repair script
FILE: fix_bg.py | PURPOSE: Fixes background task issues | WHY: One-time repair script
FILE: fix_delete_session.py | PURPOSE: Fixes the session deletion endpoint | WHY: One-time repair script
FILE: fix_engineer_nav.py | PURPOSE: Fixes navigation links on engineer pages | WHY: One-time repair script
FILE: fix_imports.py | PURPOSE: Fixes import statements | WHY: One-time repair script
FILE: fix_layout.py | PURPOSE: Fixes HTML layout issues | WHY: One-time repair script
FILE: fix_log_action.py | PURPOSE: Fixes the log_action utility | WHY: One-time repair script
FILE: fix_mangled_routing.py | PURPOSE: Fixes corrupted routing | WHY: One-time repair script
FILE: fix_mangled.py | PURPOSE: Fixes corrupted file content | WHY: One-time repair script
FILE: fix_rbac_cache.py | PURPOSE: Fixes RBAC caching issues | WHY: One-time repair script
FILE: fix_routing.py | PURPOSE: Fixes routing issues | WHY: One-time repair script
FILE: fix_select_import.py | PURPOSE: Fixes sqlalchemy.future.select import errors | WHY: One-time repair script
FILE: fix_sessionlocal.py | PURPOSE: Fixes SessionLocal import | WHY: One-time repair script
FILE: fix.py | PURPOSE: Generic one-time fix script | WHY: Applied a specific bug fix
FILE: folder_structure.txt | PURPOSE: Previously generated project structure documentation | WHY: Reference file for understanding project layout
FILE: init_db.py | PURPOSE: Initializes the database | WHY: Quick setup script to create the SQLite schema
FILE: maintenance_wizard.db | PURPOSE: SQLite database file storing all application data | WHY: Primary data store for the application
FILE: migrate_to_async.py | PURPOSE: Script to convert sync SQLAlchemy to async | WHY: Used during an async migration attempt
FILE: migrate.py | PURPOSE: Runs database schema migrations | WHY: Needed when models change
FILE: nginx.conf | PURPOSE: Nginx reverse proxy configuration | WHY: Required by the frontend Docker container to route requests
FILE: package-lock.json | PURPOSE: Locks exact versions of npm dependencies | WHY: Ensures reproducible installs across machines
FILE: package.json | PURPOSE: Node.js package manifest | WHY: Manages frontend tooling dependencies
FILE: PROJECT_STRUCTURE.txt | PURPOSE: Current project structure documentation | WHY: Reference file for understanding project layout
FILE: raw_content.txt | PURPOSE: Temporary text content dump | WHY: Scratch file used during development
FILE: rename_links.py | PURPOSE: Renames navigation links across HTML files | WHY: One-time repair script
FILE: restore.py | PURPOSE: Restores files to a previous state | WHY: Emergency fix script
FILE: revert_async.py | PURPOSE: Reverts the async database migration | WHY: Emergency fix script
FILE: revert.py | PURPOSE: General revert script | WHY: Emergency fix script
FILE: route_renamer.py | PURPOSE: Renames route paths across HTML files | WHY: One-time repair script
FILE: sandbox_script.js | PURPOSE: Standalone copy of sandbox agent JavaScript | WHY: Backup script
FILE: scratch_manager.py | PURPOSE: Temporary scratch code for manager | WHY: Debug utility
FILE: scratch.py | PURPOSE: Temporary scratch code | WHY: Debug utility
FILE: seed_db.py | PURPOSE: Seeds the database with sample data | WHY: Provides demo data for testing
FILE: simulate.js | PURPOSE: Simulates frontend interactions | WHY: Debug utility
FILE: standardize_engineer_ui.py | PURPOSE: Standardizes UI elements across engineer pages | WHY: One-time repair script
FILE: temp_style.txt | PURPOSE: Temporary CSS style content | WHY: Scratch file used during development
FILE: test_global.js | PURPOSE: Test file for global JS functions | WHY: Debug utility
FILE: test_global2.js | PURPOSE: Test file for global JS functions | WHY: Debug utility
FILE: verify.py | PURPOSE: Verifies database state | WHY: Debug utility

Group 2 — backend/routers/ folder all files
FILE: agent.py | PURPOSE: General AI agent chat endpoints | WHY: Powers the main AI chat interface and specialized analysis
FILE: alerts.py | PURPOSE: Alert management endpoints | WHY: Equipment alert system and real-time notifications
FILE: auth.py | PURPOSE: Authentication endpoints | WHY: Core authentication system and role-based user creation
FILE: documents.py | PURPOSE: Document management endpoints | WHY: Handles SOP/manual file uploads and retrieval
FILE: engineer.py | PURPOSE: Engineer dashboard endpoints | WHY: Provides engineer-specific dashboard data
FILE: engineering_agent.py | PURPOSE: Engineering agent endpoints | WHY: Powers the Engineering Workspace AI agent
FILE: feedback.py | PURPOSE: Feedback endpoints | WHY: Allows engineers to submit feedback on AI responses
FILE: inventory.py | PURPOSE: Inventory and spare parts endpoints | WHY: Manages the spare parts inventory
FILE: manager.py | PURPOSE: Manager dashboard endpoints | WHY: Admin panel functionality and user management
FILE: orchestrator.py | PURPOSE: Multi-agent orchestration endpoint | WHY: Routes user queries to appropriate specialized agents
FILE: sandbox.py | PURPOSE: Sandbox agent endpoints | WHY: Powers the Sandbox Workspace for experimentation
FILE: sessions.py | PURPOSE: Session management endpoints | WHY: Core CRUD and lifecycle management for maintenance sessions
FILE: supervisor.py | PURPOSE: Supervisor dashboard endpoints | WHY: Provides supervisor-specific views and metrics

Group 3 — backend/services/ folder all files
FILE: ai_service.py | PURPOSE: Advanced AI analysis functions | WHY: Powers specialized industrial analysis endpoints
FILE: audit_service.py | PURPOSE: Audit logging | WHY: Compliance and traceability
FILE: document_service.py | PURPOSE: Document processing | WHY: Processes uploaded SOPs into searchable chunks for RAG
FILE: memory_service.py | PURPOSE: Agent memory extraction and retrieval | WHY: Gives the AI agent persistent memory
FILE: ollama_service.py | PURPOSE: Core Ollama LLM integration | WHY: Central service for all AI chat endpoints
FILE: project_context_manager.py | PURPOSE: Manages global project context | WHY: Keeps overarching project logic available for LLMs
FILE: rag_service.py | PURPOSE: Retrieval Augmented Generation | WHY: Enables AI agent to answer questions based on documents
FILE: requirement_discovery.py | PURPOSE: Requirement profile extraction | WHY: Automatically builds requirement profiles
FILE: safety_service.py | PURPOSE: Safety checklist generation | WHY: Ensures maintenance tasks have proper safety checklists
FILE: transfer_service.py | PURPOSE: Session transfer between agents | WHY: Enables seamless handoff of context
FILE: websocket_manager.py | PURPOSE: WebSocket connection manager | WHY: Powers real-time alert notifications

Group 4 — backend/models/ folder or models.py file
FILE: __init__.py | PURPOSE: Defines all SQLAlchemy ORM models | WHY: Central schema definition for the database

Group 5 — backend/ folder remaining files like database.py schemas.py main.py
FILE: database.py | PURPOSE: SQLAlchemy database configuration | WHY: Central database connection setup
FILE: main.py | PURPOSE: FastAPI application entry point | WHY: The main file that runs the backend
FILE: maintenance.db | PURPOSE: Secondary SQLite database file | WHY: Stores temporary or secondary application data
FILE: requirements.txt | PURPOSE: Python pip dependencies | WHY: Specifies all packages needed to run the backend
FILE: schemas/__init__.py | PURPOSE: Pydantic request/response schemas | WHY: Validates API request bodies and responses

Group 6 — frontend HTML files in root
FILE: agent_sandbox.html | PURPOSE: Sandbox Workspace | WHY: Safe experimentation space for AI chat
FILE: chat.html | PURPOSE: General chat interface | WHY: Simplified chat view
FILE: engineering_agent_backup.html | PURPOSE: Backup of engineering_agent.html | WHY: Backup file
FILE: engineering_agent.html | PURPOSE: Engineering Workspace | WHY: Primary AI agent interface for engineers
FILE: equipment.html | PURPOSE: Equipment registry page | WHY: Equipment catalog
FILE: history.html | PURPOSE: Session history page | WHY: Lists all past maintenance sessions
FILE: home_page_engineer.html | PURPOSE: Engineer home dashboard | WHY: Central hub for engineer role
FILE: home_page_manager.html | PURPOSE: Manager home dashboard | WHY: Central hub for manager role
FILE: home_page_supervisor.html | PURPOSE: Supervisor home dashboard | WHY: Central hub for supervisor role
FILE: index.html | PURPOSE: Login and registration page | WHY: Entry point of the application
FILE: manager_asset_health.html | PURPOSE: Manager asset health page | WHY: Plant-wide equipment health dashboard
FILE: manager_audit_log.html | PURPOSE: Manager audit log page | WHY: Searchable log of all system actions
FILE: manager_documents.html | PURPOSE: Manager documents page | WHY: Full document library with management capabilities
FILE: manager_users.html | PURPOSE: Manager user management page | WHY: CRUD interface for managing all users
FILE: profile.html | PURPOSE: User profile page | WHY: User self-service for profile management
FILE: safety.html | PURPOSE: Safety verification page | WHY: Displays safety checklists for active sessions
FILE: supervisor_documents.html | PURPOSE: Supervisor documents page | WHY: Document library view for supervisors
FILE: supervisor_escalations.html | PURPOSE: Supervisor escalations page | WHY: Lists escalated sessions
FILE: supervisor_plant_health.html | PURPOSE: Supervisor plant health page | WHY: Equipment health overview
FILE: upload.html | PURPOSE: Document upload page | WHY: Feeds the RAG system with searchable documents

Group 7 — js/ folder all JavaScript files
FILE: agent-chat.js | PURPOSE: Chat interface logic | WHY: Reusable chat logic for AI interfaces
FILE: app.js | PURPOSE: Common application initialization | WHY: Base JavaScript for shared initialization
FILE: dashboard.js | PURPOSE: Dashboard data loader | WHY: Powers dynamic content on dashboards
FILE: rbac.js | PURPOSE: Role-Based Access Control | WHY: Enforces role-based navigation and security

Group 8 — css/ folder all CSS files
FILE: components.css | PURPOSE: Reusable component styles | WHY: Shared UI component library
FILE: style.css | PURPOSE: Global styles | WHY: Central design system for visual consistency

Group 9 — assets/ folder
FILE: assets/images/ | PURPOSE: Image directory | WHY: Stores graphical assets

Group 10 — Any other folders
FILE: node_modules/ | PURPOSE: npm dependencies | WHY: Contains installed JavaScript packages
FILE: backend/chroma_db/ | PURPOSE: Vector database storage | WHY: Stores document embeddings
FILE: backend/storage/ | PURPOSE: Document storage | WHY: Location for uploaded documents
FILE: backend/uploads/ | PURPOSE: Upload directory | WHY: Secondary file storage location
FILE: backend/utils/ | PURPOSE: Utilities directory | WHY: Reserved for shared utility code
FILE: backend/__pycache__/ | PURPOSE: Python bytecode cache | WHY: Auto-generated by Python for performance

SECTION A — WHAT IS WORKING RIGHT NOW
1. Login and registration system — users can create accounts and log in with JWT tokens
2. Role-based access control — navigation menus change based on user role
3. Role-based home dashboards — each role sees their own dashboard
4. Sandbox Agent chat — streaming AI responses via Ollama work correctly
5. Sandbox session creation — creates new sandbox sessions and stores them
6. Sandbox session history — lists previous sandbox sessions
7. Sandbox file upload — engineers can upload files during sandbox chat
8. Sandbox session escalation — transfers context from sandbox to formal session
9. Engineering Agent chat — streaming AI responses with industrial maintenance prompt
10. Engineering session creation — creates formal maintenance sessions
11. Engineering context retrieval — loads agent memory for context panel
12. Engineering requirements retrieval — loads requirement profile
13. Session history listing — shows all past sessions
14. Session lifecycle management — create, escalate, resolve, and delete sessions
15. Safety checklist system — submit safety verification data
16. Manager user management — full CRUD for users
17. Manager audit log viewing — view all system actions
18. Equipment registry — view and add equipment
19. Inventory management — spare parts CRUD and low-stock alerts
20. Document upload system — upload SOPs and manuals
21. AI agent memory system — extracts and stores key facts from conversations
22. AI requirement discovery — builds requirement profiles from chat
23. Ollama streaming integration — real-time token streaming to frontend
24. CORS properly configured — handles localhost development
25. Health check endpoint — basic API status check
26. FastAPI auto-generated API docs — available at /docs
27. Docker Compose deployment setup — ready for production

SECTION B — WHAT IS BROKEN RIGHT NOW
1. Engineering Agent on_stream_complete — was crashing with NameError; fix applied but needs verification
2. Engineering Agent network error — caused by the stream completion issue; needs verification
3. Session list in Engineering Agent sidebar — was parsing data incorrectly; fix applied but needs verification
4. Stale imports in backend routers — unused imports from failed async migration
5. ChromaDB/RAG integration — may not work if ChromaDB is not running
6. WebSocket alerts — endpoint exists but has no frontend consumer actively connecting
7. Requirement discovery — uses async patterns but database is sync; may fail silently

SECTION C — WHAT IS MISSING AND NEEDS TO BE BUILT
1. Password reset or forgot password functionality
2. Email or SMS notification system
3. Real-time WebSocket consumer in the frontend
4. Equipment health trending/charts
5. Predictive maintenance AI models
6. Shift roster management UI
7. Image upload and analysis in Engineering Agent UI
8. PDF/Excel export functionality
9. Global search functionality across sessions
10. User profile edit capabilities
11. Notification center in the frontend UI
12. Dark mode toggle switch
13. Mobile responsive testing and optimizations
14. Automated test suite (unit, integration, e2e)
15. CI/CD pipeline automation
16. Rate limiting and advanced API security
17. Automated database migration system (Alembic)
18. Multi-language and localization support
19. Session recording and playback features
20. SLA tracking and reporting
21. Integrations with external ERP/CMMS systems
22. Offline capability (PWA)