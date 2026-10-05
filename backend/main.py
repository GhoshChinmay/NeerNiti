import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router

# Initialize Socket.IO Async Server for real-time telemetry alerts
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

fastapi_app = FastAPI(
    title="NeerNiti API Engine",
    description="Spatial Decision Support System for Artificial Groundwater Recharge",
    version="1.0.0"
)

# Configure CORS so front-end dashboards can consume the API safely
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
fastapi_app.include_router(api_router, prefix="/api")

@fastapi_app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "NeerNiti Geospatial Engine",
        "version": "1.0.0"
    }

# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ):
    print(f"Socket.IO client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Socket.IO client disconnected: {sid}")

# Helper function to broadcast alerts across connected clients
async def broadcast_alert(title: str, message: str):
    await sio.emit("structure_alert", {"title": title, "message": message})

# Wrap FastAPI with Socket.IO ASGI app so uvicorn main:app serves both HTTP and WebSocket
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)