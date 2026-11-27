from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.logics.pickle_detail import (
    get_pickle_chart, get_pickle_detail, normalize_ym, normalize_flag, PICKLE_FLAGS,
    set_detail_redo,
)

pickle_detail_bp = Blueprint('pickle_detail_bp', __name__)


@pickle_detail_bp.route('/pickle_detail', methods=['GET'])
def pickle_detail():
    """작업상세: 처리완료 기록 조회 (조회 년월 like 검색 + 구분 필터, 예: /pickle_detail?base_mm=202611&flag=endream)"""
    base_mm = normalize_ym(request.args.get('base_mm'))
    flag = normalize_flag(request.args.get('flag'))
    groups, total = get_pickle_detail(base_mm, flag)
    shown = sum(len(g['details']) for g in groups)
    chart_data = get_pickle_chart(base_mm, flag)
    return render_template('marco/pickle_detail.html', base_mm=base_mm, flag=flag, flags=PICKLE_FLAGS,
                           groups=groups, total=total, shown=shown, chart_data=chart_data)


@pickle_detail_bp.route('/pickle_detail/redo', methods=['POST'])
def pickle_detail_redo():
    """처리구분 변경: 성공(y)/이상(n) → 재수행(a). 같은 조회 조건으로 복귀하고 해당 작업을 펼쳐서 보여줌"""
    detail_seq = request.form.get('detail_seq', '')
    mi_seq = request.form.get('mi_seq', '')
    if detail_seq.isdigit() and set_detail_redo(int(detail_seq)):
        flash(f'상세 No {detail_seq} 을(를) 재수행으로 변경했습니다.', 'info')
    else:
        flash('성공/이상 상태인 기록만 재수행으로 변경할 수 있습니다.', 'error')
    return redirect(url_for('pickle_detail_bp.pickle_detail',
                            base_mm=request.form.get('base_mm', ''),
                            flag=request.form.get('flag', ''),
                            _anchor=f'job-{mi_seq}' if mi_seq.isdigit() else None))
