"""
services/subject_sync.py
Kept for import compatibility. Assignments now live in the `faculty_subjects` link collection
(see services/faculty_subject_links.py); this just re-derives the denormalised `faculty.subject_ids`.
"""
from app.services.faculty_subject_links import sync_denormalised


async def sync_faculty_subject_ids():
    await sync_denormalised()
