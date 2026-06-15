from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
import backend.models as models
from backend.routers import auth, agent, sessions, documents, supervisor, manager, manager_portal, sandbox, feedback, engineering_agent, engineer, inventory, equipment, alerts, orchestrator, work_orders, reports, company_documents, notification, profile, text_correction

app = FastAPI(title="Maintenance Wizard API")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    
    # Load the local T5 grammar correction model into memory at startup
    try:
        from backend.services.text_correction_service import load_model as load_correction_model
        load_correction_model()
    except Exception as e:
        print(f"Warning: Text correction model failed to load at startup: {e}")

    # Load the local BGE embedding model into memory at startup
    try:
        from backend.services.embedding_service import load_embedding_model
        load_embedding_model()
        
        # Check Chroma dimensions and auto-reset/re-index if needed
        from backend.services.chroma_reset_service import auto_check_chroma_dimension
        auto_check_chroma_dimension()
    except Exception as e:
        print(f"Warning: Embedding model failed to load at startup: {e}")


app.mount("/company_documents", StaticFiles(directory="backend/storage/company_documents"), name="company_documents")
app.mount("/uploads", StaticFiles(directory="backend/storage/uploads"), name="uploads")


# Configure CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5500", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(notification.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(supervisor.router, prefix="/api/supervisor", tags=["Supervisor"])
app.include_router(manager.router, prefix="/api/manager", tags=["Manager"])
app.include_router(manager_portal.router, prefix="/api", tags=["Manager Portal"])
app.include_router(sandbox.router, prefix="/api/sandbox", tags=["Sandbox"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(profile.router, prefix="/api")
app.include_router(profile.notification_router, prefix="/api")
app.include_router(engineering_agent.router, prefix="/api/engineering", tags=["Engineering"])
app.include_router(engineer.router, prefix="/api/engineer", tags=["Engineer Dashboard"])
app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
app.include_router(equipment.router, prefix="/api", tags=["Equipment"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(orchestrator.router, prefix="/api/orchestrate", tags=["Orchestrator"])
app.include_router(work_orders.router, prefix="/api/work-orders", tags=["Work Orders"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(company_documents.router, prefix="/api/company-documents", tags=["Company Documents"])
app.include_router(text_correction.router, prefix="/api", tags=["Text Correction"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Maintenance Wizard API"}

from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

