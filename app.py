from fastapi import FastAPI, HTTPException
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from common import successify, errorify
from services import DownloadService, DownloadStatus
from routers import DmanRouter
import logging
import os
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager









@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.dservice = DownloadService()
    yield


# Initialize the FastAPI app
app = FastAPI(
    title="Godseye the one true backend",
    description="combines a set of apis that I use for my daily workflows",
    version="1.0.0",
    lifespan=lifespan
)






# Set up CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(DmanRouter, prefix="/api/dman")

# Set up logging
# Create a logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging
log_file_path = "logs/app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        RotatingFileHandler(
            log_file_path, maxBytes=1024 * 1024 * 5, backupCount=5
        ),  # Log to file (5MB per file, max 5 backups)
    ],
)
logger = logging.getLogger(__name__)

# Ping route
@app.get("/ping", tags=["Health Check"])
def ping():
    """
    A simple health check endpoint.
    Returns a JSON response with a "message" key.
    """
    logger.info("Ping endpoint called")
    return successify({"message": "pong"})


# Run the app (for development)
# if __name__ == "__main__":
    #should we need this at the time of removal
    # uvicorn.run(app, host="0.0.0.0", port=8000)
