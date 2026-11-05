from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_creator
from ..models import Idea, IdeaDocument, User
from ..permissions import idea_access
from ..services.files import MAX_DOCS_PER_IDEA, delete_stored, save_upload, upload_root

router = APIRouter(tags=["documents"])


@router.post("/ideas/{idea_id}/documents", status_code=201)
async def upload_document(idea_id: int, file: UploadFile = File(...), user: User = Depends(require_creator),
                          db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea or idea.creator_id != user.id:
        raise HTTPException(404, "Idea not found")
    count = db.scalar(select(func.count()).select_from(IdeaDocument).where(IdeaDocument.idea_id == idea_id)) or 0
    if count >= MAX_DOCS_PER_IDEA:
        raise HTTPException(400, f"A maximum of {MAX_DOCS_PER_IDEA} documents is allowed per idea")
    stored, size, ctype, name = await save_upload(file)
    doc = IdeaDocument(idea_id=idea_id, filename=name, stored_name=stored, content_type=ctype, size=size)
    db.add(doc)
    db.commit()
    return {"id": doc.id, "filename": doc.filename, "size": doc.size, "content_type": doc.content_type}


def _doc_for(db: Session, doc_id: int, user: Optional[User]) -> IdeaDocument:
    doc = db.get(IdeaDocument, doc_id)
    if not doc or idea_access(db, user, doc.idea) != "full":
        raise HTTPException(404, "Document not found")  # identical response for 'missing' and 'forbidden'
    return doc


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = _doc_for(db, doc_id, user)
    path = upload_root() / doc.stored_name
    if not path.is_file():
        raise HTTPException(404, "File is no longer available")
    return FileResponse(path, media_type=doc.content_type, filename=doc.filename,
                        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, user: User = Depends(require_creator), db: Session = Depends(get_db)):
    doc = db.get(IdeaDocument, doc_id)
    if not doc or doc.idea.creator_id != user.id:
        raise HTTPException(404, "Document not found")
    delete_stored(doc.stored_name)
    db.delete(doc)
    db.commit()
