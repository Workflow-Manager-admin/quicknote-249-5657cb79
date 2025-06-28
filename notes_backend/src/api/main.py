from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import os
import json

# The relative file path for storing notes locally
NOTES_STORAGE_FILE = os.path.join(os.path.dirname(__file__), "notes.json")


# PUBLIC_INTERFACE
class Note(BaseModel):
    """
    Note model representing a note object.
    """
    id: str = Field(..., description="Unique identifier for the note")
    title: str = Field(..., description="Title of the note")
    description: str = Field(..., description="Description/content of the note")
    timestamp: str = Field(
        ...,
        description="Timestamp for when the note was created or last edited, ISO format"
    )


# PUBLIC_INTERFACE
class NoteCreate(BaseModel):
    """
    Model for note creation input.
    """
    title: str = Field(..., description="Title of the note")
    description: str = Field(..., description="Description/content of the note")


# PUBLIC_INTERFACE
class NoteUpdate(BaseModel):
    """
    Model for note update input.
    """
    title: Optional[str] = Field(None, description="Updated title of the note")
    description: Optional[str] = Field(None, description="Updated description of the note")


# File persistence utility functions

def _load_notes() -> List[Note]:
    """
    Load notes from the local JSON file.
    """
    if not os.path.exists(NOTES_STORAGE_FILE):
        return []
    with open(NOTES_STORAGE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [Note(**item) for item in data]


def _save_notes(notes: List[Note]) -> None:
    """
    Save notes list to local JSON file.
    """
    with open(NOTES_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump([note.dict() for note in notes], f, indent=2, sort_keys=True, ensure_ascii=False)


# Set up FastAPI app with CORS and OpenAPI tags
app = FastAPI(
    title="QuickNote API",
    description=(
        "A simple FastAPI backend for managing personal notes. "
        "Features include create, view, edit, and delete note endpoints. Notes are stored locally."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "notes", "description": "Operations related to note management"},
        {"name": "health", "description": "Health check & utility endpoints"}
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Quick health check endpoint"
)
def health_check():
    """Health check endpoint to verify the backend is running."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["notes"],
    summary="List notes",
    description="Get all notes in order of latest first"
)
def get_notes():
    """
    Retrieve all notes as a list, most recent first.
    Returns:
        List[Note]: All notes currently stored.
    """
    notes = _load_notes()
    return sorted(notes, key=lambda n: n.timestamp, reverse=True)


# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=201,
    tags=["notes"],
    summary="Create a note",
    description="Create a new note with title and description. Returns the created note."
)
def create_note(note_in: NoteCreate):
    """
    Create a new note.
    Args:
        note_in (NoteCreate): Request body with `title` and `description`.
    Returns:
        Note: Created note object with assigned id and timestamp.
    """
    notes = _load_notes()
    now_iso = datetime.utcnow().isoformat()
    note = Note(
        id=str(uuid.uuid4()),
        title=note_in.title.strip(),
        description=note_in.description.strip(),
        timestamp=now_iso
    )
    notes.append(note)
    _save_notes(notes)
    return note


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=204,
    tags=["notes"],
    summary="Delete a note",
    description="Remove a note by its unique ID. Returns no content.",
)
def delete_note(
    note_id: str = Path(
        ..., description="Unique id of the note to delete"
    )
):
    """
    Delete a note by id.
    Args:
        note_id (str): Unique id for the note.
    Returns:
        None
    Raises:
        404 if note is not found
    """
    notes = _load_notes()
    filtered_notes = [
        n for n in notes if n.id != note_id
    ]
    if len(filtered_notes) == len(notes):
        raise HTTPException(status_code=404, detail="Note not found")
    _save_notes(filtered_notes)
    return


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["notes"],
    summary="Update a note",
    description=(
        "Update the title and/or description of an existing note by ID."
    )
)
def update_note(
    note_in: NoteUpdate,
    note_id: str = Path(
        ..., description="Unique id of the note to update"
    )
):
    """
    Update note fields for a given note id.
    Args:
        note_in (NoteUpdate): New title/description (either optional).
        note_id (str): Unique id for the note.
    Returns:
        Note: The updated note object.
    Raises:
        404 if note is not found.
    """
    notes = _load_notes()
    for idx, note in enumerate(notes):
        if note.id == note_id:
            updated_data = note.dict()
            if note_in.title is not None:
                updated_data["title"] = note_in.title.strip()
            if note_in.description is not None:
                updated_data["description"] = note_in.description.strip()
            updated_data["timestamp"] = datetime.utcnow().isoformat()
            updated_note = Note(**updated_data)
            notes[idx] = updated_note
            _save_notes(notes)
            return updated_note
    raise HTTPException(status_code=404, detail="Note not found")


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["notes"],
    summary="Get a single note",
    description=(
        "Retrieve a single note by its unique identifier."
    )
)
def get_single_note(
    note_id: str = Path(
        ..., description="Unique id of the note to retrieve"
    )
):
    """
    Get a single note by id.
    Args:
        note_id (str): Unique id for the note.
    Returns:
        Note: Note object if found.
    Raises:
        404 if note not found.
    """
    notes = _load_notes()
    for note in notes:
        if note.id == note_id:
            return note
    raise HTTPException(status_code=404, detail="Note not found")
