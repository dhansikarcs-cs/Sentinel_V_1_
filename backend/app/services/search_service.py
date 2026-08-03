import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("sentinel.search")


class SearchService:
    def __init__(self):
        self._initialized = False

    def ensure_fts(self, db: Session):
        if self._initialized:
            return
        try:
            db.execute(
                text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts USING fts5(
                    patient_username, raw_content, summary, emotions,
                    content=journal_entries, content_rowid=id
                )
            """)
            )
            db.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS journal_ai AFTER INSERT ON journal_entries BEGIN
                    INSERT INTO journal_fts(rowid, patient_username, raw_content, summary, emotions)
                    VALUES (new.id, new.patient_username, new.raw_content, new.summary, new.emotions);
                END
            """)
            )
            db.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS journal_ad AFTER DELETE ON journal_entries BEGIN
                    INSERT INTO journal_fts(journal_fts, rowid, patient_username, raw_content, summary, emotions)
                    VALUES('delete', old.id, old.patient_username, old.raw_content, old.summary, old.emotions);
                END
            """)
            )
            db.execute(
                text("""
                CREATE TRIGGER IF NOT EXISTS journal_au AFTER UPDATE ON journal_entries BEGIN
                    INSERT INTO journal_fts(journal_fts, rowid, patient_username, raw_content, summary, emotions)
                    VALUES('delete', old.id, old.patient_username, old.raw_content, old.summary, old.emotions);
                    INSERT INTO journal_fts(rowid, patient_username, raw_content, summary, emotions)
                    VALUES (new.id, new.patient_username, new.raw_content, new.summary, new.emotions);
                END
            """)
            )
            db.commit()
            self._initialized = True
        except Exception as e:
            logger.warning("FTS5 init failed (non-critical): %s", e)

    def search_journals(self, db: Session, query: str, patient_username: str = "", limit: int = 20) -> list[dict]:
        self.ensure_fts(db)
        try:
            if patient_username:
                rows = db.execute(
                    text(
                        "SELECT rowid, rank, snippet(journal_fts, 1, '<b>', '</b>', '...', 20) as snippet FROM journal_fts WHERE journal_fts MATCH :query AND patient_username = :username ORDER BY rank LIMIT :limit"
                    ),
                    {"query": query, "username": patient_username, "limit": limit},
                ).fetchall()
            else:
                rows = db.execute(
                    text(
                        "SELECT rowid, rank, snippet(journal_fts, 1, '<b>', '</b>', '...', 20) as snippet FROM journal_fts WHERE journal_fts MATCH :query ORDER BY rank LIMIT :limit"
                    ),
                    {"query": query, "limit": limit},
                ).fetchall()
            return [{"journal_id": r[0], "rank": r[1], "snippet": r[2]} for r in rows]
        except Exception as e:
            logger.warning("FTS search failed: %s", e)
            return []


search_service = SearchService()
