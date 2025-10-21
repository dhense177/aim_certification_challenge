from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
# from rag_utils import get_qa_chain
from agent import app as agent_app
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Configure LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "solar-certification-assistant"

app = FastAPI(title="Solar Certification Assistant", description="AI-powered solar potential analysis and zoning regulations")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
# qa_chain = get_qa_chain()

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/query")
async def query_endpoint(request: Request):
    body = await request.json()
    query = body.get("query", "")
    if not query:
        return JSONResponse({"error": "Query required"}, status_code=400)
    
    try:
        # Use the LangGraph agent to process the query with LangSmith monitoring
        result = agent_app.invoke(
            {"query": query},
            config={
                "metadata": {
                    "user_query": query,
                    "endpoint": "/query",
                    "timestamp": str(time.time()),
                    "source": "web_interface"
                }
            }
        )
        return {"answer": result["result"]}
    except Exception as e:
        return JSONResponse({"error": f"Processing error: {str(e)}"}, status_code=500)