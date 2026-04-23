"""GET /api/health — liveness + data-freshness check used by the frontend dashboard."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Article

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    total_count = db.query(Article).count()

    # "fresh" = published within the last 48 h (wider window to survive slow feeds)
    cutoff_48h = datetime.utcnow() - timedelta(hours=48)
    recent_count = db.query(Article).filter(Article.published_at >= cutoff_48h).count()

    # If nothing in the last 48 h, fall back to total — articles may have older pub dates
    effective_count = recent_count if recent_count > 0 else total_count

    return {
        "status": "ok",
        # mock_data is only true when the DB is completely empty
        "mock_data": total_count == 0,
        "recent_articles": recent_count,
        "total_articles": total_count,
    }
