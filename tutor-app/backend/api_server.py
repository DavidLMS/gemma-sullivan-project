"""
FastAPI Server for Tutor App Backend
Manages students and content assignment
"""

import json
import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sync_service import SyncService, SyncRequest, SyncResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Gemma Tutor API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",  # Tutor frontend port
        "http://localhost:3000",  # Student frontend port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directories
CONTENT_DIR = Path("content")
STUDENTS_DIR = Path("students")
REPORTS_DIR = Path("reports")

# Ensure directories exist
CONTENT_DIR.mkdir(exist_ok=True)
STUDENTS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Initialize sync service
sync_service = SyncService(STUDENTS_DIR, CONTENT_DIR)

# Data models
class Student(BaseModel):
    id: str
    name: str
    display_name: Optional[str] = None  # Tutor's custom display name for the student
    assigned_files: Optional[List[str]] = []
    created_at: Optional[str] = None

class CreateStudentRequest(BaseModel):
    id: str
    name: str

class AssignFilesRequest(BaseModel):
    files: List[str]

class UpdateDisplayNameRequest(BaseModel):
    display_name: str

# Helper functions
def load_students() -> Dict[str, Student]:
    """Load all students from JSON files"""
    students = {}
    if STUDENTS_DIR.exists():
        for student_file in STUDENTS_DIR.glob("*.json"):
            try:
                with open(student_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Migration: Add display_name if it doesn't exist
                if 'display_name' not in data or data['display_name'] is None:
                    data['display_name'] = data['name']
                    # Save the updated data back to file
                    with open(student_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Migrated student {data['id']}: added display_name = '{data['name']}'")
                
                students[data['id']] = Student(**data)
            except Exception as e:
                logger.error(f"Error loading student {student_file}: {e}")
    return students

def save_student(student: Student) -> None:
    """Save student to JSON file"""
    student_file = STUDENTS_DIR / f"{student.id}.json"
    try:
        with open(student_file, 'w', encoding='utf-8') as f:
            json.dump(student.model_dump(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved student: {student.id} - {student.name}")
    except Exception as e:
        logger.error(f"Error saving student {student.id}: {e}")
        raise

def get_available_content_files() -> List[str]:
    """Get list of available .txt files in content directory"""
    files = []
    if CONTENT_DIR.exists():
        for txt_file in CONTENT_DIR.glob("*.txt"):
            files.append(txt_file.name)
    return sorted(files)

# API Endpoints

@app.get("/api/students")
async def list_students():
    """Get all students"""
    try:
        students = load_students()
        return {
            "success": True,
            "students": [student.model_dump() for student in students.values()]
        }
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        raise HTTPException(status_code=500, detail="Failed to load students")

@app.post("/api/students")
async def create_student(request: CreateStudentRequest):
    """Create a new student"""
    try:
        # Validate ID format (6 digits)
        if not request.id.isdigit() or len(request.id) != 6:
            raise HTTPException(status_code=400, detail="Student ID must be exactly 6 digits")
        
        # Check if student already exists
        students = load_students()
        if request.id in students:
            raise HTTPException(status_code=400, detail="Student with this ID already exists")
        
        # Create new student
        student = Student(
            id=request.id,
            name=request.name,
            display_name=request.name,  # Initially display_name equals name
            assigned_files=[],
            created_at=datetime.now().isoformat()
        )
        
        # Save student
        save_student(student)
        
        # Create student directories
        student_dir = STUDENTS_DIR / request.id / "content"
        reports_dir = REPORTS_DIR / request.id
        student_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "student": student.model_dump(),
            "message": f"Student {request.name} created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        raise HTTPException(status_code=500, detail="Failed to create student")

@app.get("/api/content/available")
async def list_available_content(student_id: Optional[str] = None):
    """Get available .txt files in content directory, optionally filtered by student assignments"""
    try:
        all_files = get_available_content_files()
        
        # Filter out already assigned files if student_id provided
        if student_id:
            students = load_students()
            if student_id in students:
                assigned_files = students[student_id].assigned_files or []
                available_files = [f for f in all_files if f not in assigned_files]
            else:
                available_files = all_files
        else:
            available_files = all_files
            
        return {
            "success": True,
            "files": available_files,
            "count": len(available_files)
        }
    except Exception as e:
        logger.error(f"Error listing content files: {e}")
        raise HTTPException(status_code=500, detail="Failed to load content files")

@app.get("/api/content/preview/{filename}")
async def preview_content_file(filename: str):
    """Get content of a specific .txt file for preview"""
    try:
        # Validate filename ends with .txt and exists
        if not filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files can be previewed")
        
        file_path = CONTENT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        return {
            "success": True,
            "filename": filename,
            "content": content,
            "size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file content")

@app.post("/api/content/upload")
async def upload_content_file(file: UploadFile = File(...)):
    """Upload a new .txt content file"""
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed")
        
        # Validate file size (10MB max)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB in bytes
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")
        
        # Sanitize filename to prevent path traversal
        filename = file.filename.replace('..', '').replace('/', '').replace('\\', '')
        if not filename or filename != file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check if file already exists
        file_path = CONTENT_DIR / filename
        if file_path.exists():
            raise HTTPException(status_code=409, detail=f"File '{filename}' already exists")
        
        # Validate content is text (try to decode as UTF-8)
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must contain valid UTF-8 text")
        
        # Save file to content directory
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"Successfully uploaded content file: {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "size": len(content),
            "message": f"File '{filename}' uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.delete("/api/content/{filename}")
async def delete_content_file(filename: str):
    """Delete a content file"""
    try:
        # Validate filename ends with .txt and exists
        if not filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files can be deleted")
        
        file_path = CONTENT_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file is assigned to any students before deleting
        students = load_students()
        assigned_to_students = []
        for student_id, student_data in students.items():
            if hasattr(student_data, 'assigned_files') and student_data.assigned_files:
                if filename in student_data.assigned_files:
                    assigned_to_students.append(f"{student_id} ({student_data.name})")
        
        if assigned_to_students:
            raise HTTPException(
                status_code=409, 
                detail=f"Cannot delete file '{filename}'. It is currently assigned to: {', '.join(assigned_to_students)}"
            )
        
        # Delete the file
        file_path.unlink()
        logger.info(f"Successfully deleted content file: {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "message": f"File '{filename}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

@app.get("/api/students/{student_id}/assigned")
async def get_assigned_content(student_id: str):
    """Get content assigned to a specific student"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = students[student_id]
        return {
            "success": True,
            "files": student.assigned_files or [],
            "count": len(student.assigned_files or [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assigned content for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load assigned content")

@app.post("/api/students/{student_id}/assign")
async def assign_content(student_id: str, request: AssignFilesRequest):
    """Assign content files to a student"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = students[student_id]
        available_files = get_available_content_files()
        
        # Validate that all requested files exist
        for file_name in request.files:
            if file_name not in available_files:
                raise HTTPException(status_code=400, detail=f"File '{file_name}' not found in content directory")
        
        # Add files to student's assigned list (avoid duplicates)
        if not student.assigned_files:
            student.assigned_files = []
        
        new_files = []
        for file_name in request.files:
            if file_name not in student.assigned_files:
                student.assigned_files.append(file_name)
                new_files.append(file_name)
                
                # Copy file to student's content directory
                source_file = CONTENT_DIR / file_name
                target_file = STUDENTS_DIR / student_id / "content" / file_name
                if source_file.exists():
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(source_file, 'r', encoding='utf-8') as src:
                        content = src.read()
                    with open(target_file, 'w', encoding='utf-8') as tgt:
                        tgt.write(content)
        
        # Save updated student
        save_student(student)
        
        return {
            "success": True,
            "assigned_files": student.assigned_files,
            "new_files": new_files,
            "message": f"Assigned {len(new_files)} new files to {student.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning content to {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign content")

@app.delete("/api/students/{student_id}/unassign")
async def unassign_content(student_id: str, request: AssignFilesRequest):
    """Remove assigned content from a student"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = students[student_id]
        
        if not student.assigned_files:
            student.assigned_files = []
        
        # Remove files from student's assigned list
        removed_files = []
        for file_name in request.files:
            if file_name in student.assigned_files:
                student.assigned_files.remove(file_name)
                removed_files.append(file_name)
                
                # Remove file from student's content directory
                target_file = STUDENTS_DIR / student_id / "content" / file_name
                if target_file.exists():
                    target_file.unlink()
        
        # Save updated student
        save_student(student)
        
        return {
            "success": True,
            "assigned_files": student.assigned_files,
            "removed_files": removed_files,
            "message": f"Removed {len(removed_files)} files from {student.name}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unassigning content from {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unassign content")

@app.get("/api/students/{student_id}/folder")
async def get_student_folder_path(student_id: str):
    """Get the file system path to student's content folder"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student_content_dir = STUDENTS_DIR / student_id / "content"
        student_content_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "student_id": student_id,
            "content_path": str(student_content_dir.absolute()),
            "reports_path": str((REPORTS_DIR / student_id).absolute())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting folder path for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get folder path")

@app.put("/api/students/{student_id}/display-name")
async def update_student_display_name(student_id: str, request: UpdateDisplayNameRequest):
    """Update the display name for a student (tutor's view only)"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Validate display name
        if not request.display_name or not request.display_name.strip():
            raise HTTPException(status_code=400, detail="Display name cannot be empty")
        
        if len(request.display_name.strip()) > 100:
            raise HTTPException(status_code=400, detail="Display name must be less than 100 characters")
        
        # Update display name
        student = students[student_id]
        old_display_name = student.display_name
        student.display_name = request.display_name.strip()
        
        # Save updated student
        save_student(student)
        
        logger.info(f"Updated display name for student {student_id}: '{old_display_name}' -> '{student.display_name}'")
        
        return {
            "success": True,
            "student_id": student_id,
            "display_name": student.display_name,
            "message": f"Display name updated to '{student.display_name}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating display name for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update display name")

@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    """Delete a student and all associated data"""
    try:
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student = students[student_id]
        student_name = student.display_name or student.name
        
        # Delete student JSON file
        student_file = STUDENTS_DIR / f"{student_id}.json"
        if student_file.exists():
            student_file.unlink()
        
        # Delete student directories
        student_content_dir = STUDENTS_DIR / student_id
        reports_dir = REPORTS_DIR / student_id
        
        # Remove student content directory
        if student_content_dir.exists():
            import shutil
            shutil.rmtree(student_content_dir)
        
        # Remove reports directory
        if reports_dir.exists():
            import shutil
            shutil.rmtree(reports_dir)
        
        logger.info(f"Deleted student {student_id} ({student_name}) and all associated data")
        
        return {
            "success": True,
            "student_id": student_id,
            "student_name": student_name,
            "message": f"Student '{student_name}' (ID: {student_id}) deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete student")

def validate_path_security(requested_path: str, student_id: str) -> Path:
    """Validate and secure file paths to prevent directory traversal attacks"""
    try:
        # Remove any path traversal attempts
        clean_path = os.path.normpath(requested_path).lstrip(os.sep)
        
        # Determine the base directory based on the path structure
        if clean_path.startswith("reports/"):
            # Reports folder access
            base_dir = REPORTS_DIR / student_id
            relative_path = clean_path[8:] if len(clean_path) > 8 else ""  # Remove "reports/" prefix
        elif clean_path.startswith("students/"):
            # Student folder access  
            base_dir = STUDENTS_DIR / student_id
            relative_path = clean_path[9:] if len(clean_path) > 9 else ""  # Remove "students/" prefix
        elif clean_path == "reports":
            # Root reports folder
            base_dir = REPORTS_DIR / student_id
            relative_path = ""
        elif clean_path == "students":
            # Root students folder
            base_dir = STUDENTS_DIR / student_id
            relative_path = ""
        else:
            # Default to student folder
            base_dir = STUDENTS_DIR / student_id
            relative_path = clean_path
        
        # Construct the final path
        if relative_path:
            final_path = base_dir / relative_path
        else:
            final_path = base_dir
            
        # Ensure the path is within the allowed directory
        final_path = final_path.resolve()
        base_dir = base_dir.resolve()
        
        if not str(final_path).startswith(str(base_dir)):
            raise HTTPException(status_code=403, detail="Access denied: Path outside allowed directory")
            
        return final_path
        
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid path")

@app.get("/api/files/browse/{student_id}")
async def browse_student_files(student_id: str, path: str = ""):
    """Browse files and folders for a specific student"""
    try:
        # Validate student exists
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        # Validate and construct the path
        if not path:
            # Return root level with students and reports folders
            return {
                "success": True,
                "path": "",
                "items": [
                    {
                        "name": "students",
                        "type": "directory",
                        "path": "students",
                        "size": None,
                        "modified": None
                    },
                    {
                        "name": "reports", 
                        "type": "directory",
                        "path": "reports",
                        "size": None,
                        "modified": None
                    }
                ],
                "parent": None
            }
        
        target_path = validate_path_security(path, student_id)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        
        if target_path.is_file():
            # Return file metadata
            stat = target_path.stat()
            mime_type, _ = mimetypes.guess_type(str(target_path))
            
            return {
                "success": True,
                "type": "file",
                "name": target_path.name,
                "path": path,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "mime_type": mime_type,
                "parent": str(target_path.parent.relative_to(target_path.parent.parent)) if target_path.parent != target_path.parent.parent else None
            }
        
        # Return directory contents
        items = []
        try:
            for item in sorted(target_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
                try:
                    stat = item.stat()
                    item_path = path + "/" + item.name if path else item.name
                    
                    items.append({
                        "name": item.name,
                        "type": "file" if item.is_file() else "directory",
                        "path": item_path,
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "mime_type": mimetypes.guess_type(str(item))[0] if item.is_file() else None
                    })
                except (OSError, PermissionError) as e:
                    logger.warning(f"Cannot access {item}: {e}")
                    continue
        except (OSError, PermissionError) as e:
            logger.error(f"Cannot read directory {target_path}: {e}")
            raise HTTPException(status_code=403, detail="Cannot read directory")
        
        # Calculate parent path
        parent_path = None
        if path:
            path_parts = path.split("/")
            if len(path_parts) > 1:
                parent_path = "/".join(path_parts[:-1])
            else:
                parent_path = ""
        
        return {
            "success": True,
            "type": "directory", 
            "path": path,
            "items": items,
            "parent": parent_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing files for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to browse files")

@app.get("/api/files/content/{student_id}")
async def get_file_content(student_id: str, path: str):
    """Get the content of a specific file for preview"""
    try:
        # Validate student exists
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        target_path = validate_path_security(path, student_id)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not target_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Check file size (limit to 1MB for preview)
        if target_path.stat().st_size > 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large for preview")
        
        mime_type, _ = mimetypes.guess_type(str(target_path))
        
        # Handle different file types
        if mime_type and mime_type.startswith('text/') or target_path.suffix.lower() in ['.json', '.log', '.txt', '.md']:
            try:
                content = target_path.read_text(encoding='utf-8')
                return {
                    "success": True,
                    "type": "text",
                    "content": content,
                    "mime_type": mime_type,
                    "size": len(content)
                }
            except UnicodeDecodeError:
                return {
                    "success": False,
                    "error": "File contains binary data and cannot be previewed as text"
                }
        elif mime_type and mime_type.startswith('image/'):
            # For images, return file info (actual image will be served via download endpoint)
            return {
                "success": True,
                "type": "image",
                "mime_type": mime_type,
                "download_url": f"/api/files/download/{student_id}?path={path}"
            }
        else:
            return {
                "success": False,
                "error": f"File type '{mime_type}' not supported for preview"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file content for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file content")

@app.get("/api/files/download/{student_id}")
async def download_file(student_id: str, path: str):
    """Download a specific file"""
    try:
        # Validate student exists
        students = load_students()
        if student_id not in students:
            raise HTTPException(status_code=404, detail="Student not found")
        
        target_path = validate_path_security(path, student_id)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not target_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Return the file
        return FileResponse(
            path=str(target_path),
            filename=target_path.name,
            media_type=mimetypes.guess_type(str(target_path))[0]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for {student_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Gemma Tutor API"
    }

@app.get("/api/debug/status")
async def debug_status():
    """Debug endpoint to check all service states"""
    return {
        "service": "Gemma Tutor API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "sync_service": {
            "discovery_running": sync_service.is_discovery_running(),
            "discovery_available": sync_service.is_discovery_running()
        },
        "directories": {
            "content_dir": str(CONTENT_DIR.absolute()),
            "students_dir": str(STUDENTS_DIR.absolute()),
            "reports_dir": str(REPORTS_DIR.absolute())
        },
        "cors_origins": [
            "http://localhost:3001",
            "http://localhost:3000"
        ]
    }

# Sync endpoints

@app.post("/api/sync/discovery/start")
async def start_discovery_service():
    """Start network discovery service for student connections"""
    try:
        success = sync_service.start_discovery_service()
        if success:
            return {
                "success": True,
                "message": "Discovery service started",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start discovery service")
    except Exception as e:
        logger.error(f"Error starting discovery service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync/discovery/stop")
async def stop_discovery_service():
    """Stop network discovery service"""
    try:
        success = sync_service.stop_discovery_service()
        if success:
            return {
                "success": True,
                "message": "Discovery service stopped",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to stop discovery service")
    except Exception as e:
        logger.error(f"Error stopping discovery service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/discovery/status")
async def get_discovery_status():
    """Get discovery service status"""
    return {
        "success": True,
        "is_running": sync_service.is_discovery_running(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/sync/discover")
async def discover_service():
    """Discovery endpoint for student-app to find this tutor service"""
    return {
        "service": "Gemma Tutor API",
        "version": "1.0.0",
        "available": sync_service.is_discovery_running(),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "sync_from_student": "/api/sync/from-student",
            "get_content": "/api/sync/content"
        }
    }

@app.post("/api/sync/from-student")
async def sync_from_student(sync_request: SyncRequest) -> SyncResponse:
    """Receive sync data from student-app"""
    try:
        if not sync_service.is_discovery_running():
            raise HTTPException(status_code=503, detail="Discovery service not running")
        
        response = await sync_service.sync_from_student(sync_request)
        logger.info(f"Successfully synced data from student {sync_request.student_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sync from student: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/content/{student_id}")
async def get_content_for_student(student_id: str):
    """Get content that should be synced to student"""
    try:
        if not sync_service.is_discovery_running():
            raise HTTPException(status_code=503, detail="Discovery service not running")
        
        content_data = await sync_service.get_content_for_student(student_id)
        return {
            "success": True,
            "student_id": student_id,
            "content": content_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting content for student {student_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting Gemma Tutor API server on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)