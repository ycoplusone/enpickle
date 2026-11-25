from sqlalchemy import text

from app import db


def only_digits(phone: str) -> str:
    """전화번호 숫자만 남김 (010-1234-5678 → 01012345678)"""
    return ''.join(ch for ch in (phone or '') if ch.isdigit())


def get_qna_list(phone: str = '', limit: int = 300):
    """
    피클 질문/답변 목록 (marco_qna)
    phone : 있으면 해당 전화번호만, 없으면 전체
    반환  : (rows, total, unanswered) 최신 순, 최대 limit 건
    """
    digits = only_digits(phone)
    where = "WHERE a.phone_number = :phone" if digits else ""
    params = {'phone': digits}

    stat = db.session.execute(text(f"""
        SELECT COUNT(*) AS total
             , SUM(CASE WHEN a.a_ask IS NULL OR TRIM(a.a_ask) = '' THEN 1 ELSE 0 END) AS unanswered
        FROM marco_qna a
        {where}
    """), params).mappings().first()

    rows = db.session.execute(text(f"""
        SELECT a.seq
             , a.phone_number
             , a.url
             , a.p_qution
             , a.a_ask
             , a.created_at
        FROM marco_qna a
        {where}
        ORDER BY a.seq DESC
        LIMIT :limit
    """), {**params, 'limit': limit}).mappings().all()

    return rows, int(stat['total'] or 0), int(stat['unanswered'] or 0)


def add_question(phone: str, question: str, url: str = None) -> bool:
    """질문 등록. 등록 시각은 NOW()"""
    digits = only_digits(phone)
    question = (question or '').strip()
    if not digits or not question:
        return False
    db.session.execute(text("""
        INSERT INTO marco_qna (phone_number, url, p_qution, created_at)
        VALUES (:phone, :url, :question, NOW())
    """), {'phone': digits, 'url': (url or '').strip() or None, 'question': question})
    db.session.commit()
    return True


def set_answer(seq: int, answer: str) -> bool:
    """
    답변 등록 (a_ask)
    - 아직 답변이 없는 질문에만 등록 (이미 답변된 건은 덮어쓰지 않음)
    반환 : 등록했으면 True
    """
    answer = (answer or '').strip()
    if not seq or not answer:
        return False
    result = db.session.execute(text("""
        UPDATE marco_qna
        SET a_ask = :answer
        WHERE seq = :seq
          AND (a_ask IS NULL OR TRIM(a_ask) = '')
    """), {'seq': seq, 'answer': answer})
    db.session.commit()
    return result.rowcount > 0
