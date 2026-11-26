from flask import Blueprint, render_template, request, redirect, url_for, session, abort

from app.logics.survey_test import (
    survey_exists,
    survey_list,
    pick_page,
    build_questions,
    page_header,
    parse_answers,
    save_response,
)

survey_test_bp = Blueprint('survey_test_bp', __name__)

# 진행 상태는 Flask 세션에 설문별로 보관: {'p1': picks, 'a1': 1페이지 응답, 'p2': picks}
def _key(survey_no):
    return f'survey_test_{survey_no}'


def _render(survey_no, page, picks, error=None, values=None):
    title, intro = page_header(survey_no)
    return render_template(
        'survey/survey_test.html',
        survey_no=survey_no, page=page, title=title, intro=intro,
        questions=build_questions(survey_no, picks),
        error=error, values=values or {},
    )


@survey_test_bp.route('/survey_test', methods=['GET'])
def survey_test_list():
    """테스트용 설문 목록 (독립 화면, 로그인 불필요)"""
    return render_template('survey/survey_test_list.html', surveys=survey_list())


@survey_test_bp.route('/survey_test/<int:survey_no>', methods=['GET', 'POST'])
def survey_test_page1(survey_no):
    """1페이지(q1~q4). GET(새로고침)마다 문항/문구 새로 랜덤 선택"""
    if not survey_exists(survey_no):
        abort(404)
    key = _key(survey_no)

    if request.method == 'GET':
        picks = pick_page(survey_no, 1)
        session[key] = {'p1': picks}
        return _render(survey_no, 1, picks)

    state = session.get(key) or {}
    if 'p1' not in state:
        return redirect(url_for('survey_test_bp.survey_test_page1', survey_no=survey_no))

    answers, error = parse_answers(build_questions(survey_no, state['p1']), request.form)
    if error:
        # 같은 문항 그대로 다시 보여주며 오류 표시 (입력값 유지)
        return _render(survey_no, 1, state['p1'], error, request.form.to_dict(flat=False))

    state['a1'] = answers
    session[key] = state
    return redirect(url_for('survey_test_bp.survey_test_page2', survey_no=survey_no))


@survey_test_bp.route('/survey_test/<int:survey_no>/2', methods=['GET', 'POST'])
def survey_test_page2(survey_no):
    """2페이지(q5~q8). 1페이지 응답이 없으면 1페이지로 되돌림"""
    if not survey_exists(survey_no):
        abort(404)
    key = _key(survey_no)
    state = session.get(key) or {}
    if 'a1' not in state:
        return redirect(url_for('survey_test_bp.survey_test_page1', survey_no=survey_no))

    if request.method == 'GET':
        used = [v[0] for v in state['p1'].values()]   # 1페이지 척도 문항과 중복 방지
        picks = pick_page(survey_no, 2, exclude_ids=used)
        state['p2'] = picks
        session[key] = state
        return _render(survey_no, 2, picks)

    if 'p2' not in state:
        return redirect(url_for('survey_test_bp.survey_test_page2', survey_no=survey_no))

    q2 = build_questions(survey_no, state['p2'])
    answers, error = parse_answers(q2, request.form)
    if error:
        return _render(survey_no, 2, state['p2'], error, request.form.to_dict(flat=False))

    q1 = build_questions(survey_no, state['p1'])
    response_id = save_response(survey_no, {**state['a1'], **answers}, q1 + q2)
    session.pop(key, None)
    return redirect(url_for('survey_test_bp.survey_test_done', survey_no=survey_no, rid=response_id))


@survey_test_bp.route('/survey_test/<int:survey_no>/done', methods=['GET'])
def survey_test_done(survey_no):
    if not survey_exists(survey_no):
        abort(404)
    return render_template(
        'survey/survey_test_done.html',
        survey_no=survey_no, response_id=request.args.get('rid', ''),
    )
