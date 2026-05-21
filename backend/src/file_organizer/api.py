import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from .core import FileOrganizer, scan_folder_for_extensions
from .config import load_extension_map, save_extension_map

app = FastAPI(title="ORDO API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, dict] = {}


# --- Request / Response models ---

class ScanRequest(BaseModel):
    path: str


class OrganizeRequest(BaseModel):
    source_path: str
    destination_path: str
    extension_map: dict[str, str]
    dry_run: bool = False


class UpdateConfigRequest(BaseModel):
    extension_map: dict[str, str]

    @field_validator('extension_map')
    @classmethod
    def keys_must_have_dot(cls, v: dict[str, str]) -> dict[str, str]:
        invalid = [k for k in v if not k.startswith('.')]
        if invalid:
            raise ValueError(
                f"Extension keys must start with '.': {invalid}"
            )
        empty_values = [k for k, val in v.items() if not val.strip()]
        if empty_values:
            raise ValueError(
                f"Folder names must be non-empty for: {empty_values}"
            )
        return v


# --- Endpoints ---

@app.post("/api/scan")
def scan_folder(req: ScanRequest):
    path = Path(req.path)
    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail={"code": "PATH_NOT_FOUND", "message": f"Path is not a directory: {req.path}"},
        )

    scan_data = scan_folder_for_extensions(path)
    default_map = load_extension_map()

    result = []
    for ext, count in scan_data["file_counts"].items():
        default_folder = default_map.get(ext, "")
        result.append({
            "extension": ext,
            "count": count,
            "default_folder": default_folder or "Unmapped",
            "is_unmapped": not bool(default_folder),
        })

    return {
        "extensions": result,
        "total_files": scan_data["total_files"],
        "scan_path": req.path,
    }


@app.post("/api/organize", status_code=202)
def start_organize(req: OrganizeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "processed_files": 0,
        "total_files": 0,
        "errors": [],
    }
    background_tasks.add_task(_run_organize, job_id, req)
    return {"job_id": job_id}


@app.get("/api/organize/{job_id}/status")
def get_job_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job not found: {job_id}"},
        )
    return _jobs[job_id]


@app.get("/api/config")
def get_config():
    return {"extension_map": load_extension_map()}


@app.put("/api/config")
def update_config(body: UpdateConfigRequest):
    save_extension_map(body.extension_map)
    return {"extension_map": load_extension_map()}


# --- Background task ---

def _run_organize(job_id: str, req: OrganizeRequest) -> None:
    job = _jobs[job_id]
    job["status"] = "running"

    def on_progress(processed: int, total: int) -> None:
        job["processed_files"] = processed
        job["total_files"] = total
        job["progress"] = int((processed / total) * 100) if total else 0

    try:
        organizer = FileOrganizer(
            source_dir=Path(req.source_path),
            dest_dir=Path(req.destination_path),
        )
        organizer.organize(
            extension_map=req.extension_map,
            dry_run=req.dry_run,
            progress_callback=on_progress,
        )
        job["status"] = "complete"
        job["progress"] = 100
    except Exception as e:
        job["status"] = "error"
        job["errors"].append(str(e))


# --- Entry point para pyproject.toml scripts ---

def run() -> None:
    import uvicorn
    uvicorn.run("file_organizer.api:app", host="0.0.0.0", port=8000, reload=True)
