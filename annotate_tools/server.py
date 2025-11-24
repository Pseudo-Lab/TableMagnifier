
import json
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_JSON_PATH = BASE_DIR / "output.json"

# Serve static files (for images if needed, though we might need to be careful with paths)
# Assuming images are relative to BASE_DIR
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


class UpdateRequest(BaseModel):
    synthetic_json: Dict[str, Any]


@app.get("/api/data")
async def get_data():
    if not OUTPUT_JSON_PATH.exists():
        raise HTTPException(status_code=404, detail="output.json not found. Run the generation flow first.")

    try:
        with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Read HTML content if paths exist
        html_table_path = data.get("html_table_path")
        synthetic_table_path = data.get("synthetic_table_path")
        
        html_content = ""
        if html_table_path:
            p = Path(html_table_path)
            if not p.is_absolute():
                p = BASE_DIR / p
            if p.exists():
                html_content = p.read_text(encoding="utf-8")

        synthetic_html_content = ""
        if synthetic_table_path:
            p = Path(synthetic_table_path)
            if not p.is_absolute():
                p = BASE_DIR / p
            if p.exists():
                synthetic_html_content = p.read_text(encoding="utf-8")

        return {
            "image_path": data.get("image_path"),
            "html_table": html_content,
            "synthetic_table": synthetic_html_content,
            "synthetic_json": data.get("synthetic_json"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/save")
async def save_data(request: UpdateRequest):
    if not OUTPUT_JSON_PATH.exists():
        raise HTTPException(status_code=404, detail="output.json not found.")

    try:
        # 1. Update output.json
        with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        data["synthetic_json"] = request.synthetic_json
        
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 2. Update synthetic_json file if it exists
        # We need to find the path. In output.json it might not be explicitly stored as a separate key 
        # other than what we put in there.
        # But based on runner.py: 
        # synthetic_json_path = base.with_name(base.name + "_synthetic.json")
        # And we know output.json path.
        
        synthetic_json_path = OUTPUT_JSON_PATH.with_name(OUTPUT_JSON_PATH.stem + "_synthetic.json")
        if synthetic_json_path.exists():
             with open(synthetic_json_path, "w", encoding="utf-8") as f:
                json.dump(request.synthetic_json, f, ensure_ascii=False, indent=2)

        return {"status": "success", "message": "Data saved successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
