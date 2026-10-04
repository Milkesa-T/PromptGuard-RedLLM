import uvicorn
from core.config import SERVER_HOST, SERVER_PORT

if __name__ == "__main__":
    print(f"🚀 Starting PromptGuard / RedLLM Server at http://localhost:{SERVER_PORT}")
    print(f"📖 API Documentation: http://localhost:{SERVER_PORT}/docs")
    print(f"🖥️ Web Dashboard: http://localhost:{SERVER_PORT}/")
    uvicorn.run("backend.app:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
