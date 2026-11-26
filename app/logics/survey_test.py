"""
테스트용 설문조사 (/survey_test/<survey_no>) 로직

- 설문 2종(1: 온라인 쇼핑, 2: 생활 습관), 각 2페이지 x 4문항 = 8문항
- 1페이지: q1~q4 = 5점 척도 (척도 문항 풀에서 랜덤 4개)
- 2페이지: q5 = 5점 척도 (1페이지에 나온 문항 제외), q6 = 복수 선택, q7/q8 = 단일 선택
- 페이지를 열(새로고침할) 때마다 문항 선택 + 문구 변형 + 척도 보기 문구가 랜덤으로 바뀜
- 세션에는 (문항 id, 문구 번호, 척도 번호)만 보관하고 문구는 여기서 다시 만든다 (쿠키 크기 절약)
"""
import json
import random
import uuid

from sqlalchemy import text

from app import db

# ---------------------------------------------------------------------------
# 5점 척도 보기 문구 (1~5 순서). 같은 종류 안에서 매번 하나를 랜덤 선택
# ---------------------------------------------------------------------------
SCALE_LABELS = {
    'agree': [
        ['전혀 그렇지 않다', '그렇지 않다', '보통이다', '그렇다', '매우 그렇다'],
        ['매우 아니다', '아니다', '보통', '그렇다', '매우 그렇다'],
        ['전혀 동의하지 않음', '동의하지 않음', '중립', '동의함', '매우 동의함'],
    ],
    'satisfy': [
        ['매우 불만족', '불만족', '보통', '만족', '매우 만족'],
        ['아주 불만족', '다소 불만족', '보통', '다소 만족', '아주 만족'],
        ['전혀 만족하지 않음', '만족하지 않음', '그저 그럼', '만족함', '매우 만족함'],
    ],
}

# ---------------------------------------------------------------------------
# 설문 정의
#   scale  : 5점 척도 문항 풀 (q1~q5 에 사용, 중복 없이 5개 뽑음)
#   multi  : 복수 선택 문항 풀 (q6, 1개 뽑음) - 보기 코드 A, B, C ... 로 저장
#   single7/single8 : 단일 선택 문항 풀 (q7, q8 각 1개 뽑음) - 보기 문구로 저장
#   texts  : 같은 의미의 문구 변형들 (매번 하나 랜덤)
# ---------------------------------------------------------------------------
SURVEYS = {
    1: {
        'title': ['온라인 쇼핑 이용 경험 설문조사', '온라인 쇼핑 이용 만족도 조사', '온라인 쇼핑몰 이용자 설문'],
        'intro': [
            '안녕하세요. 온라인 쇼핑 이용 경험에 대한 간단한 설문입니다. 솔직하게 응답해 주세요.',
            '본 설문은 온라인 쇼핑 서비스 개선을 위한 조사입니다. 약 2분 정도 소요됩니다.',
            '온라인 쇼핑몰 이용 경험을 바탕으로 각 문항에 응답해 주시기 바랍니다.',
        ],
        'scale': [
            {'id': 's1_01', 'kind': 'satisfy', 'texts': [
                '온라인 쇼핑몰의 상품 검색 기능에 얼마나 만족하십니까?',
                '쇼핑몰에서 원하는 상품을 찾는 검색 기능은 만족스러우셨나요?',
                '상품 검색 기능에 대한 만족도를 선택해 주세요.']},
            {'id': 's1_02', 'kind': 'satisfy', 'texts': [
                '주문한 상품의 배송 속도에 얼마나 만족하십니까?',
                '최근 이용하신 쇼핑몰의 배송 속도는 만족스러우셨나요?',
                '배송 속도에 대한 만족도를 선택해 주세요.']},
            {'id': 's1_03', 'kind': 'agree', 'texts': [
                '온라인 쇼핑몰의 상품 가격이 합리적이라고 생각하십니까?',
                '온라인에서 판매되는 상품 가격은 적정한 편이라고 느끼시나요?',
                '"온라인 쇼핑몰의 가격은 합리적이다"에 얼마나 동의하십니까?']},
            {'id': 's1_04', 'kind': 'agree', 'texts': [
                '결제 과정이 간편하다고 느끼십니까?',
                '쇼핑몰의 결제 절차는 쉽고 빠른 편인가요?',
                '"결제 과정이 간편하다"에 얼마나 동의하십니까?']},
            {'id': 's1_05', 'kind': 'satisfy', 'texts': [
                '고객센터의 응대 품질에 얼마나 만족하십니까?',
                '문의하셨을 때 고객센터의 응대는 만족스러우셨나요?',
                '고객센터 응대에 대한 만족도를 선택해 주세요.']},
            {'id': 's1_06', 'kind': 'agree', 'texts': [
                '상품 상세 페이지의 정보가 충분하다고 생각하십니까?',
                '상품 설명과 사진만으로도 구매 결정을 내리기에 충분했나요?',
                '"상품 상세 정보가 충분히 제공된다"에 얼마나 동의하십니까?']},
            {'id': 's1_07', 'kind': 'satisfy', 'texts': [
                '반품 및 교환 절차에 얼마나 만족하십니까?',
                '반품·교환을 신청하셨을 때 처리 과정은 만족스러우셨나요?',
                '반품/교환 절차에 대한 만족도를 선택해 주세요.']},
            {'id': 's1_08', 'kind': 'agree', 'texts': [
                '이용 중인 쇼핑몰을 지인에게 추천할 의향이 있으십니까?',
                '주변 사람에게 지금 쓰시는 쇼핑몰을 권하고 싶으신가요?',
                '"이 쇼핑몰을 지인에게 추천하겠다"에 얼마나 동의하십니까?']},
            {'id': 's1_09', 'kind': 'agree', 'texts': [
                '쇼핑몰 모바일 앱이 사용하기 편리하다고 느끼십니까?',
                '모바일 앱으로 쇼핑할 때 불편함 없이 이용하셨나요?',
                '"모바일 앱 사용이 편리하다"에 얼마나 동의하십니까?']},
            {'id': 's1_10', 'kind': 'agree', 'texts': [
                '상품 리뷰를 신뢰하는 편이십니까?',
                '구매 전 확인하는 상품 후기를 믿을 만하다고 생각하시나요?',
                '"쇼핑몰의 상품 리뷰는 신뢰할 수 있다"에 얼마나 동의하십니까?']},
        ],
        'multi': [
            {'id': 'm1_01', 'texts': [
                '주로 구매하는 상품 분야를 모두 선택해 주세요.',
                '온라인에서 자주 구입하시는 품목을 모두 골라 주세요.',
                '다음 중 온라인으로 구매해 본 상품군을 모두 선택하세요.'],
             'options': ['의류/패션', '식품', '생활용품', '전자기기', '도서', '뷰티']},
            {'id': 'm1_02', 'texts': [
                '쇼핑몰을 선택할 때 중요하게 생각하는 요소를 모두 선택해 주세요.',
                '쇼핑몰 선택 시 고려하시는 점을 모두 골라 주세요.',
                '다음 중 쇼핑몰 선택에 영향을 주는 요소를 모두 선택하세요.'],
             'options': ['가격', '배송 속도', '상품 리뷰', '브랜드 신뢰도', '포인트/할인 혜택', '반품 정책']},
        ],
        'single7': [
            {'id': 'o1_01', 'texts': [
                '한 달 평균 온라인 쇼핑 이용 횟수는 어떻게 되십니까?',
                '온라인 쇼핑을 한 달에 몇 번 정도 이용하시나요?',
                '월 평균 온라인 구매 횟수를 선택해 주세요.'],
             'options': ['1회 미만', '1~2회', '3~5회', '6~9회', '10회 이상']},
            {'id': 'o1_02', 'texts': [
                '온라인 쇼핑 시 주로 사용하는 기기는 무엇입니까?',
                '쇼핑할 때 가장 많이 쓰시는 기기를 선택해 주세요.',
                '주 이용 기기를 골라 주세요.'],
             'options': ['PC/노트북', '스마트폰', '태블릿', '기타']},
        ],
        'single8': [
            {'id': 'o1_03', 'texts': [
                '한 달 평균 온라인 쇼핑 지출 금액은 어느 정도입니까?',
                '온라인 쇼핑에 한 달 동안 쓰시는 금액은 대략 얼마인가요?',
                '월 평균 온라인 쇼핑 지출액을 선택해 주세요.'],
             'options': ['5만원 미만', '5만원~10만원 미만', '10만원~30만원 미만', '30만원 이상']},
            {'id': 'o1_04', 'texts': [
                '가장 많이 사용하는 결제 수단은 무엇입니까?',
                '온라인 결제 시 주로 쓰시는 방법을 선택해 주세요.',
                '주 결제 수단을 골라 주세요.'],
             'options': ['신용/체크카드', '간편결제', '계좌이체', '무통장입금', '기타']},
        ],
    },
    2: {
        'title': ['일상 생활 습관 설문조사', '생활 습관 및 건강 관리 조사', '하루 생활 패턴 설문'],
        'intro': [
            '안녕하세요. 평소 생활 습관에 대한 간단한 설문입니다. 평소 모습을 기준으로 응답해 주세요.',
            '본 설문은 생활 습관과 건강 관리 실태를 알아보기 위한 조사입니다. 약 2분 정도 소요됩니다.',
            '최근 한 달 동안의 생활을 떠올리며 각 문항에 응답해 주시기 바랍니다.',
        ],
        'scale': [
            {'id': 's2_01', 'kind': 'agree', 'texts': [
                '평소 규칙적인 시간에 잠자리에 드는 편입니까?',
                '매일 비슷한 시간에 주무시는 편인가요?',
                '"나는 수면 시간이 규칙적이다"에 얼마나 동의하십니까?']},
            {'id': 's2_02', 'kind': 'agree', 'texts': [
                '아침 식사를 거르지 않고 챙겨 드시는 편입니까?',
                '평소 아침밥을 꾸준히 드시나요?',
                '"나는 아침 식사를 규칙적으로 한다"에 얼마나 동의하십니까?']},
            {'id': 's2_03', 'kind': 'agree', 'texts': [
                '일주일에 3회 이상 운동을 하는 편입니까?',
                '주 3회 이상 꾸준히 몸을 움직이시나요?',
                '"나는 주 3회 이상 운동한다"에 얼마나 동의하십니까?']},
            {'id': 's2_04', 'kind': 'agree', 'texts': [
                '스트레스를 스스로 잘 관리하고 있다고 생각하십니까?',
                '평소 받는 스트레스를 적절히 해소하고 계신가요?',
                '"나는 스트레스를 잘 관리한다"에 얼마나 동의하십니까?']},
            {'id': 's2_05', 'kind': 'agree', 'texts': [
                '하루에 물을 충분히 마시는 편입니까?',
                '평소 수분 섭취를 충분히 하고 계신가요?',
                '"나는 하루 물 섭취량이 충분하다"에 얼마나 동의하십니까?']},
            {'id': 's2_06', 'kind': 'agree', 'texts': [
                '스마트폰 사용 시간이 적절하다고 생각하십니까?',
                '하루 스마트폰 사용량을 스스로 잘 조절하고 계신가요?',
                '"내 스마트폰 사용 시간은 적당하다"에 얼마나 동의하십니까?']},
            {'id': 's2_07', 'kind': 'satisfy', 'texts': [
                '일과 개인 생활의 균형에 얼마나 만족하십니까?',
                '업무와 여가 사이의 균형은 만족스러우신가요?',
                '워라밸(일·생활 균형)에 대한 만족도를 선택해 주세요.']},
            {'id': 's2_08', 'kind': 'satisfy', 'texts': [
                '현재 본인의 건강 상태에 얼마나 만족하십니까?',
                '요즘 건강 상태는 만족스러우신가요?',
                '현재 건강 상태에 대한 만족도를 선택해 주세요.']},
            {'id': 's2_09', 'kind': 'satisfy', 'texts': [
                '여가 시간을 보내는 방식에 얼마나 만족하십니까?',
                '쉬는 시간을 보내는 방법은 만족스러우신가요?',
                '여가 활용에 대한 만족도를 선택해 주세요.']},
            {'id': 's2_10', 'kind': 'agree', 'texts': [
                '평소 건강한 식습관을 유지하고 있다고 생각하십니까?',
                '균형 잡힌 식사를 하고 계신 편인가요?',
                '"나는 건강한 식습관을 가지고 있다"에 얼마나 동의하십니까?']},
        ],
        'multi': [
            {'id': 'm2_01', 'texts': [
                '평소 즐기는 운동을 모두 선택해 주세요.',
                '자주 하시는 운동 종류를 모두 골라 주세요.',
                '다음 중 최근 한 달 동안 해 본 운동을 모두 선택하세요.'],
             'options': ['걷기/산책', '헬스', '요가/필라테스', '수영', '자전거', '등산']},
            {'id': 'm2_02', 'texts': [
                '스트레스를 해소하는 방법을 모두 선택해 주세요.',
                '스트레스를 풀 때 주로 하시는 일을 모두 골라 주세요.',
                '다음 중 본인의 스트레스 해소 방법을 모두 선택하세요.'],
             'options': ['잠자기', '운동', '맛있는 음식', '게임/영상 시청', '여행', '지인과 대화']},
        ],
        'single7': [
            {'id': 'o2_01', 'texts': [
                '하루 평균 수면 시간은 어떻게 되십니까?',
                '보통 하루에 몇 시간 정도 주무시나요?',
                '평균 수면 시간을 선택해 주세요.'],
             'options': ['5시간 미만', '5~6시간', '6~7시간', '7~8시간', '8시간 이상']},
            {'id': 'o2_02', 'texts': [
                '하루 평균 물 섭취량은 어느 정도입니까?',
                '하루에 물을 대략 얼마나 드시나요?',
                '하루 물 섭취량을 선택해 주세요.'],
             'options': ['0.5L 미만', '0.5~1L', '1~1.5L', '1.5~2L', '2L 이상']},
        ],
        'single8': [
            {'id': 'o2_03', 'texts': [
                '일주일 평균 운동 횟수는 어떻게 되십니까?',
                '한 주에 운동을 몇 번 정도 하시나요?',
                '주간 운동 횟수를 선택해 주세요.'],
             'options': ['거의 안 함', '1~2회', '3~4회', '5회 이상']},
            {'id': 'o2_04', 'texts': [
                '하루 평균 스마트폰 사용 시간은 어느 정도입니까?',
                '하루에 스마트폰을 대략 몇 시간 사용하시나요?',
                '하루 스마트폰 사용 시간을 선택해 주세요.'],
             'options': ['1시간 미만', '1~3시간', '3~5시간', '5시간 이상']},
        ],
    },
}

# q 번호 -> 문항 풀 이름
SLOT_POOL = {
    'q1': 'scale', 'q2': 'scale', 'q3': 'scale', 'q4': 'scale',
    'q5': 'scale', 'q6': 'multi', 'q7': 'single7', 'q8': 'single8',
}
PAGE_SLOTS = {1: ['q1', 'q2', 'q3', 'q4'], 2: ['q5', 'q6', 'q7', 'q8']}
OPTION_CODES = 'ABCDEFGHIJ'


def survey_exists(survey_no: int) -> bool:
    return survey_no in SURVEYS


def survey_list():
    """설문 목록 화면용 (대표 제목 = 첫 번째 문구)"""
    return [{'no': no, 'title': s['title'][0]} for no, s in SURVEYS.items()]


def _find(survey_no: int, pool: str, qid: str):
    for q in SURVEYS[survey_no][pool]:
        if q['id'] == qid:
            return q
    return None


def pick_page(survey_no: int, page: int, exclude_ids=()):
    """
    페이지 문항 랜덤 선택. 세션 저장용 picks 반환
    picks = {'q1': [문항id, 문구번호, 척도번호], ...}
    exclude_ids: 1페이지에서 이미 나온 척도 문항 (2페이지 q5 중복 방지)
    """
    survey = SURVEYS[survey_no]
    slots = PAGE_SLOTS[page]
    picks = {}

    scale_slots = [s for s in slots if SLOT_POOL[s] == 'scale']
    if scale_slots:
        pool = [q for q in survey['scale'] if q['id'] not in exclude_ids]
        for slot, q in zip(scale_slots, random.sample(pool, len(scale_slots))):
            labels_cnt = len(SCALE_LABELS[q['kind']])
            picks[slot] = [q['id'], random.randrange(len(q['texts'])), random.randrange(labels_cnt)]

    for slot in slots:
        if slot in picks:
            continue
        q = random.choice(survey[SLOT_POOL[slot]])
        picks[slot] = [q['id'], random.randrange(len(q['texts'])), 0]

    return picks


def build_questions(survey_no: int, picks: dict):
    """세션 picks -> 화면 표시용 문항 리스트"""
    questions = []
    for slot in sorted(picks, key=lambda s: int(s[1:])):
        qid, ti, si = picks[slot]
        pool = SLOT_POOL[slot]
        q = _find(survey_no, pool, qid)
        if pool == 'scale':
            labels = SCALE_LABELS[q['kind']][si]
            options = [{'value': str(i + 1), 'label': lb} for i, lb in enumerate(labels)]
            qtype = 'scale'
        elif pool == 'multi':
            options = [{'value': OPTION_CODES[i], 'label': lb} for i, lb in enumerate(q['options'])]
            qtype = 'multi'
        else:
            options = [{'value': str(i), 'label': lb} for i, lb in enumerate(q['options'])]
            qtype = 'single'
        questions.append({
            'slot': slot, 'no': int(slot[1:]), 'id': qid, 'type': qtype,
            'text': q['texts'][ti], 'options': options,
        })
    return questions


def page_header(survey_no: int):
    """제목/안내 문구도 새로고침마다 랜덤"""
    s = SURVEYS[survey_no]
    return random.choice(s['title']), random.choice(s['intro'])


def parse_answers(questions, form):
    """
    폼 응답 검증. (answers, error_msg) 반환
    answers = {'q1': 3, 'q6': ['A', 'C'], 'q7': '1~2회', ...}
    """
    answers = {}
    for q in questions:
        valid = {o['value']: o['label'] for o in q['options']}
        if q['type'] == 'multi':
            vals = [v for v in form.getlist(q['slot']) if v in valid]
            if not vals:
                return None, f"{q['no']}번 문항을 하나 이상 선택해 주세요."
            answers[q['slot']] = sorted(set(vals))
        else:
            v = form.get(q['slot'], '')
            if v not in valid:
                return None, f"{q['no']}번 문항에 응답해 주세요."
            answers[q['slot']] = int(v) if q['type'] == 'scale' else valid[v]
    return answers, None


def save_response(survey_no: int, answers: dict, questions: list) -> int:
    """8문항 응답 1건 저장. response_id 반환"""
    log = {q['slot']: {'id': q['id'], 'text': q['text']} for q in questions}
    sql = text("""
        INSERT INTO survey_test
            (respondent_id, survey_no,
             q1_answer, q2_answer, q3_answer, q4_answer, q5_answer,
             q6_answer, q7_answer, q8_answer, question_log)
        VALUES
            (:rid, :survey_no,
             :q1, :q2, :q3, :q4, :q5,
             :q6, :q7, :q8, :log)
    """)
    params = {
        'rid': uuid.uuid4().hex,
        'survey_no': survey_no,
        **{k: answers[k] for k in ('q1', 'q2', 'q3', 'q4', 'q5', 'q7', 'q8')},
        'q6': json.dumps(answers['q6'], ensure_ascii=False),
        'log': json.dumps(log, ensure_ascii=False),
    }
    result = db.session.execute(sql, params)
    db.session.commit()
    return result.lastrowid
