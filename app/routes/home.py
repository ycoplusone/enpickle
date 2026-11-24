from flask import Blueprint, render_template, request, jsonify


# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
def home():
    """루트(/) : 빈 페이지 (상단 메뉴만 표시)"""
    return render_template('home/blank.html')


