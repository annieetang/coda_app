import uvicorn
import os

if __name__ == "__main__":
    # Use PORT environment variable provided by Render, or default to 5000
    port = int(os.getenv("PORT", 5000))
    
    # Use 0.0.0.0 for production, allowing external access
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        # Only use reload in development
        reload=os.getenv("ENVIRONMENT") == "development"
    ) 