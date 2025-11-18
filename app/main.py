# app/main.py
# FastAPI application entry point
# - REST API endpoints
# - Static file serving
# - CORS configuration
# - Exception handlers

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import upload, products, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    print("[FastAPI] Application starting up...")
    
    # Create upload directory if it doesn't exist
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    print(f"[FastAPI] Upload directory: {upload_dir}")
    
    yield
    
    # Shutdown
    print("[FastAPI] Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Product Importer API",
    description="Backend API for importing and managing products from CSV files",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS - Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(products.router, prefix="/api", tags=["Products"])
app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "product-importer",
        "version": "1.0.0"
    }


# ============================================================================
# Mount Static Files (must be before route definitions)
# ============================================================================

# Mount static files for frontend UI
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


# ============================================================================
# Root Endpoint - Serve index.html
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Serve the main index.html file"""
    return FileResponse("static/index.html")


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    print(f"[FastAPI] Unhandled exception: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

