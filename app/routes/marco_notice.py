from flask import Blueprint, render_template, request, redirect, url_for, flash, Response

from app.logics.marco_notice import add_notice, get_notice_list, get_latest_notice

marco_notice_bp = Blueprint('marco_notice_bp', __name__)

NOTE_MAX_LEN = 5000


@marco_notice_bp.route('/marco_notice', methods=['GET', 'POST'])
def marco_notice():
    """
    피클 공지 게시판 (marco_notice) - 입력 + 이력 조회만 (수정/삭제 없음)
    로그인 인증: app/__init__.py 전역 before_request(check_device_auth) 적용 (예외 목록 미등록)
    """
    if request.method == 'POST':
        note = (request.form.get('note') or '').strip()
        if not note:
            flash('공지 내용을 입력해 주세요.', 'error')
        elif len(note) > NOTE_MAX_LEN:
            flash(f'공지는 {NOTE_MAX_LEN:,}자 이하로 입력해 주세요.', 'error')
        elif add_notice(note):
            flash('공지를 등록했습니다.', 'info')
        return redirect(url_for('marco_notice_bp.marco_notice'))

    rows, total = get_notice_list()
    return render_template('marco/marco_notice.html', rows=rows, total=total, note_max_len=NOTE_MAX_LEN)


@marco_notice_bp.route('/marco_notice/latest', methods=['GET'])
def marco_notice_latest():
    """
    가장 최근 공지(seq 최대) 1건의 내용을 일반 텍스트(text/plain)로 반환 (메뉴 미등록, 로그인 인증 제외)
    """
    # 공지 내용만 일반 텍스트로 그대로 출력 (줄바꿈·따옴표 원문 유지), 공지가 없으면 빈 응답
    return Response(get_latest_notice() or '', mimetype='text/plain')   # Flask 가 charset=utf-8 을 자동으로 붙임
