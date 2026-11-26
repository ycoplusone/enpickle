-- 테스트용 설문조사(/survey_test) 저장 테이블 보완
-- 기존 survey_test (q1~q8 응답 컬럼) 에 설문 구분 / 노출 문항 기록 컬럼 추가
ALTER TABLE survey_test
  ADD COLUMN survey_no TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '설문 구분 (1: 온라인 쇼핑, 2: 생활 습관)' AFTER respondent_id,
  ADD COLUMN question_log JSON DEFAULT NULL COMMENT '응답 당시 노출된 문항 id/문구 (q1~q8)' AFTER q8_answer,
  ADD KEY idx_survey_no (survey_no),
  MODIFY COLUMN q7_answer varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '7번 문항 응답 (단일 선택 보기 문구)',
  MODIFY COLUMN q8_answer text COLLATE utf8mb4_unicode_ci COMMENT '8번 문항 응답 (단일 선택 보기 문구)';
