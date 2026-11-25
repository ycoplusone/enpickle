from sqlalchemy import text

from app import db


def add_notice(note: str) -> bool:
    """공지 등록 (입력 전용 - 수정/삭제 없음). 등록 시각은 NOW()"""
    note = (note or '').strip()
    if not note:
        return False
    db.session.execute(
        text("INSERT INTO marco_notice (note, created_at) VALUES (:note, NOW())"),
        {'note': note},
    )
    db.session.commit()
    return True


def get_notice_list(limit: int = 500):
    """
    공지 등록 이력 (marco_notice)
    반환 : (rows, total) 최신 순, 최대 limit 건
    """
    total = db.session.execute(text("SELECT COUNT(*) FROM marco_notice")).scalar() or 0
    rows = db.session.execute(text("""
        SELECT a.seq
             , a.note
             , a.created_at
        FROM marco_notice a
        ORDER BY a.seq DESC
        LIMIT :limit
    """), {'limit': limit}).mappings().all()
    return rows, total


def get_latest_notice():
    """가장 마지막에 입력된(seq 최대) 공지 내용(note). 없으면 None"""
    return db.session.execute(text("""
        SELECT a.note
        FROM marco_notice a
        ORDER BY a.seq DESC
        LIMIT 1
    """)).scalar()
