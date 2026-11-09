import os
import psycopg
from pymongo import MongoClient

PG_DSN = os.getenv("LAB2_PG", "host=localhost port=5434 dbname=lms user=postgres password=lab2")
MONGO_URI = os.getenv("LAB2_MONGO", "mongodb://localhost:27018")


def pg():
    return psycopg.connect(PG_DSN, autocommit=True)


def mongo():
    return MongoClient(MONGO_URI)["lms"]


READ_PAGE_FLAT = """
SELECT p.id, p.course_code, p.title, p.department, p.lecturer_name, p.lecturer_email, p.term,
       t.no, t.title, m.position, m.type, m.title, m.url, m.duration_sec, m.pages, m.size_kb,
       q.position, q.question, q.options, q.answer
FROM lms_pages p
JOIN lms_topics t ON t.page_id = p.id
JOIN lms_materials m ON m.topic_id = t.id
LEFT JOIN lms_quiz_questions q ON q.material_id = m.id
WHERE p.course_code = %s
ORDER BY t.no, m.position, q.position
"""

READ_TAGS = "SELECT tag FROM lms_page_tags WHERE page_id = %s"
READ_COMMENTS = "SELECT student, text, created_at FROM lms_comments WHERE page_id = %s ORDER BY created_at DESC LIMIT 50"

READ_PAGE_JSON = """
SELECT jsonb_build_object(
  'course_code', p.course_code, 'title', p.title, 'department', p.department,
  'lecturer', jsonb_build_object('name', p.lecturer_name, 'email', p.lecturer_email),
  'term', p.term,
  'tags', (SELECT coalesce(jsonb_agg(g.tag), '[]') FROM lms_page_tags g WHERE g.page_id = p.id),
  'topics', (SELECT jsonb_agg(jsonb_build_object('no', t.no, 'title', t.title, 'materials',
      (SELECT jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
          'type', m.type, 'title', m.title, 'url', m.url, 'duration_sec', m.duration_sec,
          'pages', m.pages, 'size_kb', m.size_kb,
          'questions', (SELECT jsonb_agg(jsonb_build_object('q', q.question, 'options', q.options, 'answer', q.answer)
                                         ORDER BY q.position)
                        FROM lms_quiz_questions q WHERE q.material_id = m.id))) ORDER BY m.position)
       FROM lms_materials m WHERE m.topic_id = t.id)) ORDER BY t.no)
     FROM lms_topics t WHERE t.page_id = p.id),
  'comments', (SELECT coalesce(jsonb_agg(c), '[]') FROM
      (SELECT student, text, created_at AS at FROM lms_comments WHERE page_id = p.id
       ORDER BY created_at DESC LIMIT 50) c))
FROM lms_pages p WHERE p.course_code = %s
"""

SEARCH_SQL = """
SELECT p.course_code, p.title
FROM lms_pages p
JOIN lms_page_tags g ON g.page_id = p.id AND g.tag = %s
WHERE EXISTS (SELECT 1 FROM lms_topics t JOIN lms_materials m ON m.topic_id = t.id
              WHERE t.page_id = p.id AND m.type = 'video' AND m.duration_sec > %s)
ORDER BY p.course_code LIMIT 20
"""

AGG_SQL = """
SELECT p.department, sum(m.duration_sec) / 3600.0 AS hours
FROM lms_pages p
JOIN lms_topics t ON t.page_id = p.id
JOIN lms_materials m ON m.topic_id = t.id
WHERE m.type = 'video'
GROUP BY p.department ORDER BY hours DESC LIMIT 10
"""

AGG_MONGO = [
    {"$unwind": "$topics"},
    {"$unwind": "$topics.materials"},
    {"$match": {"topics.materials.type": "video"}},
    {"$group": {"_id": "$department", "hours": {"$sum": {"$divide": ["$topics.materials.duration_sec", 3600]}}}},
    {"$sort": {"hours": -1}},
    {"$limit": 10},
]
