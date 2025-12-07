
import json
import os
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Global state for the server
class ServerState:
    output_json_path: Path | None = None
    base_dir: Path | None = None

state = ServerState()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UpdateRequest(BaseModel):
    synthetic_json: Dict[str, Any]
    qa_results: list[Dict[str, Any]] | None = None


@app.get("/api/data")
async def get_data():
    if not state.output_json_path or not state.output_json_path.exists():
        raise HTTPException(status_code=404, detail="Output JSON file not found.")

    try:
        with open(state.output_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Read HTML content if paths exist
        html_table_path = data.get("html_table_path")
        synthetic_table_path = data.get("synthetic_table_path")
        
        html_content = ""
        if html_table_path:
            p = Path(html_table_path)
            if not p.is_absolute() and state.base_dir:
                p = state.base_dir / p
            if p.exists():
                html_content = p.read_text(encoding="utf-8")

        synthetic_html_content = ""
        if synthetic_table_path:
            p = Path(synthetic_table_path)
            if not p.is_absolute() and state.base_dir:
                p = state.base_dir / p
            if p.exists():
                synthetic_html_content = p.read_text(encoding="utf-8")

        return {
            "image_path": data.get("image_path"),
            "html_table": html_content,
            "synthetic_table": synthetic_html_content,
            "synthetic_json": data.get("synthetic_json"),
            "qa_results": data.get("qa_results", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save")
async def save_data(request: UpdateRequest):
    if not state.output_json_path or not state.output_json_path.exists():
        raise HTTPException(status_code=404, detail="Output JSON file not found.")

    try:
        # 1. Update output.json
        with open(state.output_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        data["synthetic_json"] = request.synthetic_json
        if request.qa_results is not None:
            data["qa_results"] = request.qa_results
        
        with open(state.output_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 2. Update synthetic_json file if it exists
        synthetic_json_path = state.output_json_path.with_name(state.output_json_path.stem + "_synthetic.json")
        if synthetic_json_path.exists():
             with open(synthetic_json_path, "w", encoding="utf-8") as f:
                json.dump(request.synthetic_json, f, ensure_ascii=False, indent=2)

        return {"status": "success", "message": "Data saved successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_server():
    parser = argparse.ArgumentParser(description="Run the annotation tool server.")
    parser.add_argument(
        "--file", 
        type=Path, 
        default=Path("output.json"),
        help="Path to the output.json file to serve (default: output.json)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Port to bind to (default: 8000)"
    )
    
    args = parser.parse_args()
    
    state.output_json_path = args.file.resolve()
    state.base_dir = state.output_json_path.parent
    
    if not state.output_json_path.exists():
        print(f"Warning: {state.output_json_path} does not exist yet.")
    else:
        print(f"Serving data from: {state.output_json_path}")

    # Mount static files relative to the output file's directory
    # This allows serving images if they are in the same directory structure
    app.mount("/static", StaticFiles(directory=str(state.base_dir)), name="static")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    start_server()
