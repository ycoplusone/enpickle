from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.marco_qna import get_qna_list, add_question, set_answer, only_digits

marco_qna_bp = Blueprint('marco_qna_bp', __name__)

TEXT_MAX_LEN = 5000
URL_MAX_LEN = 1024


# ------------------------------------------------------------------
# 피클 질문 화면: 전화번호 기준 조회 + 질문 등록 (전체보기·답변등록 없음)
# ------------------------------------------------------------------
@marco_qna_bp.route('/marco_qna', methods=['GET'])
def marco_qna():
    """
    예) /marco_qna?phone=01012345678   (전화번호를 입력해야 목록 표시)
    로그인 인증 제외 (app/__init__.py check_device_auth 예외 목록, 질문 등록 POST 포함) / 메뉴 미등록
    """
    phone = only_digits(request.args.get('phone'))
    rows, total, unanswered = get_qna_list(phone) if phone else ([], 0, 0)
    return render_template(
        'marco/marco_qna.html',
        phone=phone, rows=rows, total=total, unanswered=unanswered, searched=bool(phone),
        text_max_len=TEXT_MAX_LEN, url_max_len=URL_MAX_LEN,
    )


@marco_qna_bp.route('/marco_qna/question', methods=['POST'])
def marco_qna_question():
    """질문 등록 후 같은 전화번호로 목록 복귀"""
    phone = only_digits(request.form.get('phone'))
    url = (request.form.get('url') or '').strip()
    question = (request.form.get('question') or '').strip()

    if not phone:
        flash('전화번호를 입력해 주세요.', 'error')
    elif not question:
        flash('질문 내용을 입력해 주세요.', 'error')
    elif len(question) > TEXT_MAX_LEN:
        flash(f'질문은 {TEXT_MAX_LEN:,}자 이하로 입력해 주세요.', 'error')
    elif len(url) > URL_MAX_LEN:
        flash(f'url 은 {URL_MAX_LEN:,}자 이하로 입력해 주세요.', 'error')
    elif add_question(phone, question, url):
        flash('질문을 등록했습니다.', 'info')

    return redirect(url_for('marco_qna_bp.marco_qna', phone=phone or None))


# ------------------------------------------------------------------
# 관리자 화면: 전체 질문 보기 + 답변 등록
# ------------------------------------------------------------------
@marco_qna_bp.route('/marco_qna/admin', methods=['GET'])
def marco_qna_admin():
    """전체 질문 최신 순, 답변 없는 질문에 답변 입력칸 표시 (로그인 인증 필요)"""
    rows, total, unanswered = get_qna_list()
    return render_template(
        'marco/marco_qna_admin.html',
        rows=rows, total=total, unanswered=unanswered, text_max_len=TEXT_MAX_LEN,
    )


@marco_qna_bp.route('/marco_qna/answer', methods=['POST'])
def marco_qna_answer():
    """답변 등록 후 관리자 화면으로 복귀"""
    seq = request.form.get('seq', '')
    seq = int(seq) if seq.isdigit() else 0
    answer = (request.form.get('answer') or '').strip()

    if not answer:
        flash('답변 내용을 입력해 주세요.', 'error')
    elif len(answer) > TEXT_MAX_LEN:
        flash(f'답변은 {TEXT_MAX_LEN:,}자 이하로 입력해 주세요.', 'error')
    elif set_answer(seq, answer):
        flash(f'{seq}번 질문에 답변을 등록했습니다.', 'info')
    else:
        flash('이미 답변됐거나 없는 질문입니다.', 'error')

    return redirect(url_for('marco_qna_bp.marco_qna_admin'))
