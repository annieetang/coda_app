from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.endpoints import router, MUSIC_DIR
from services.database import RedisDatabase

# Create FastAPI app
app = FastAPI(
    title="Coda Backend",
    debug=True  # Enable debug mode
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/music", StaticFiles(directory=MUSIC_DIR), name="music")

# Include API routes
app.include_router(router, prefix="/api")

print("Routes registered:")
for route in app.routes:
    print(f"  {route.path}")

# Initialize database connection on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and load score hashes."""
    db = RedisDatabase()
    print("Loading score hashes from Redis...")
    print(f"Music directory: {MUSIC_DIR}")
    print(f"Available music files: {[f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mxl', '.musicxml', '.xml'))]}")
    print("Backend startup complete") 