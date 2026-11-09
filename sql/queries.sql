\echo '--- insert (5 таблиць в одній транзакції)'
DELETE FROM lms_pages WHERE course_code = 'DEMO-1';
BEGIN;
WITH p AS (
    INSERT INTO lms_pages (course_code, title, department, lecturer_name, lecturer_email, term)
    VALUES ('DEMO-1', 'Бази даних', 'Кафедра ПЗ', 'Петренко О.І.', 'petrenko@univ.ua', '2026/2027-1')
    RETURNING id
), tg AS (
    INSERT INTO lms_page_tags (page_id, tag) SELECT id, t FROM p, unnest(ARRAY['sql', 'nosql']) t
), t1 AS (
    INSERT INTO lms_topics (page_id, no, title) SELECT id, 1, 'Реляційна модель' FROM p RETURNING id
), t2 AS (
    INSERT INTO lms_topics (page_id, no, title) SELECT id, 2, 'Документні БД' FROM p RETURNING id
), m1 AS (
    INSERT INTO lms_materials (topic_id, position, type, title, url, duration_sec, pages, size_kb)
    SELECT id, x.pos, x.type, x.title, x.url, x.dur, x.pages, x.kb FROM t1,
        (VALUES (1, 'video', 'Вступ', 'https://video/1', 3000, NULL::int, NULL::int),
                (2, 'pdf', 'Конспект', 'https://files/1.pdf', NULL, 18, 900)) x(pos, type, title, url, dur, pages, kb)
), m2 AS (
    INSERT INTO lms_materials (topic_id, position, type, title) SELECT id, 1, 'quiz', 'Тест 1' FROM t2 RETURNING id
)
INSERT INTO lms_quiz_questions (material_id, position, question, options, answer)
SELECT id, 1, 'Що таке BSON?', ARRAY['формат', 'мова', 'СУБД'], 0 FROM m2;
COMMIT;

\echo '--- вибірка сторінки курсу як одного JSON (аналог findOne)'
SELECT jsonb_pretty(jsonb_build_object(
    'title', p.title,
    'topics', (SELECT jsonb_agg(jsonb_build_object('no', t.no, 'title', t.title) ORDER BY t.no)
               FROM lms_topics t WHERE t.page_id = p.id)))
FROM lms_pages p WHERE p.course_code = 'DEMO-1';

\echo '--- курси з тегом nosql, де є відео довше 40 хв'
SELECT p.course_code, p.title
FROM lms_pages p
JOIN lms_page_tags g ON g.page_id = p.id AND g.tag = 'nosql'
WHERE EXISTS (SELECT 1 FROM lms_topics t JOIN lms_materials m ON m.topic_id = t.id
              WHERE t.page_id = p.id AND m.type = 'video' AND m.duration_sec > 2400)
ORDER BY p.course_code LIMIT 5;

\echo '--- коментар'
INSERT INTO lms_comments (page_id, student, text)
SELECT id, 'КН-21 Іваненко', 'Де лаба 2?' FROM lms_pages WHERE course_code = 'DEMO-1';

\echo '--- змінити url відео в темі 1'
UPDATE lms_materials m SET url = 'https://video/1-new'
FROM lms_topics t JOIN lms_pages p ON p.id = t.page_id
WHERE m.topic_id = t.id AND p.course_code = 'DEMO-1' AND t.no = 1 AND m.type = 'video';

\echo '--- CHECK не пропускає матеріал невідомого типу'
\set ON_ERROR_STOP 0
INSERT INTO lms_materials (topic_id, position, type, title)
SELECT t.id, 9, 'mp3', 'x' FROM lms_topics t JOIN lms_pages p ON p.id = t.page_id WHERE p.course_code = 'DEMO-1' LIMIT 1;

\echo '--- топ-5 кафедр за сумарною тривалістю відео (год)'
SELECT p.department, round(sum(m.duration_sec) / 3600.0, 1) AS hours
FROM lms_pages p
JOIN lms_topics t ON t.page_id = p.id
JOIN lms_materials m ON m.topic_id = t.id
WHERE m.type = 'video'
GROUP BY p.department ORDER BY hours DESC LIMIT 5;

\echo '--- план пошуку по тегу'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF) SELECT page_id FROM lms_page_tags WHERE tag = 'nosql';

\echo '--- видалення (каскадом з усіх таблиць)'
DELETE FROM lms_pages WHERE course_code = 'DEMO-1';
