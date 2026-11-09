import random
import sys
import time
from datetime import datetime, timedelta, timezone

from common import mongo, pg

DEPARTMENTS = [
    "Кафедра програмної інженерії", "Кафедра комп'ютерних наук", "Кафедра прикладної математики",
    "Кафедра кібербезпеки", "Кафедра штучного інтелекту", "Кафедра інформаційних систем",
    "Кафедра вищої математики", "Кафедра фізики", "Кафедра економіки", "Кафедра менеджменту",
    "Кафедра філології", "Кафедра історії", "Кафедра права", "Кафедра психології",
    "Кафедра електроніки", "Кафедра автоматизації",
]
TAGS = ["sql", "nosql", "python", "java", "c#", "web", "ml", "math", "stats", "security", "networks",
        "os", "algorithms", "design", "devops", "cloud", "mobile", "economics", "law", "history",
        "physics", "english", "testing", "agile", "data", "graphs", "linux", "ui", "research", "lab"]
WORDS = ["основи", "моделі", "методи", "аналіз", "системи", "дані", "алгоритми", "проєктування",
         "теорія", "практика", "мережі", "безпека", "оптимізація", "структури", "архітектура",
         "розробка", "тестування", "обчислення", "статистика", "інтеграція"]
SURNAMES = ["Петренко", "Коваленко", "Бондаренко", "Шевченко", "Ткаченко", "Кравченко", "Мельник",
            "Олійник", "Лисенко", "Мороз", "Савченко", "Руденко", "Іваненко", "Гончаренко"]
BASE_TIME = datetime(2026, 9, 1, tzinfo=timezone.utc)


def phrase(rnd, n):
    return " ".join(rnd.choice(WORDS) for _ in range(n)).capitalize()


def make_material(rnd, i):
    kind = rnd.choices(["video", "pdf", "quiz", "link"], [4, 3, 2, 1])[0]
    m = {"type": kind, "title": phrase(rnd, 3)}
    if kind == "video":
        m["url"] = f"https://video.univ.ua/{rnd.getrandbits(40):x}"
        m["duration_sec"] = rnd.randint(300, 5400)
    elif kind == "pdf":
        m["url"] = f"https://files.univ.ua/{rnd.getrandbits(40):x}.pdf"
        m["pages"] = rnd.randint(2, 80)
        m["size_kb"] = rnd.randint(100, 12000)
    elif kind == "quiz":
        m["questions"] = [
            {"q": phrase(rnd, 6) + "?", "options": [phrase(rnd, 2) for _ in range(4)], "answer": rnd.randint(0, 3)}
            for _ in range(rnd.randint(3, 8))
        ]
    else:
        m["url"] = f"https://wiki.univ.ua/{rnd.getrandbits(40):x}"
    return m


def make_page(rnd, n):
    surname = rnd.choice(SURNAMES)
    year = rnd.choice([2024, 2025, 2026])
    return {
        "course_code": f"C-{n:06d}",
        "title": phrase(rnd, 3),
        "department": rnd.choice(DEPARTMENTS),
        "lecturer": {"name": f"{surname} {rnd.choice('АБВГДІКЛМОП')}.{rnd.choice('АБВГДІКЛМОП')}.",
                     "email": f"{surname.lower()}{rnd.randint(1, 99)}@univ.ua"},
        "term": f"{year}/{year + 1}-{rnd.randint(1, 2)}",
        "tags": rnd.sample(TAGS, rnd.randint(1, 5)),
        "topics": [
            {"no": t + 1, "title": phrase(rnd, 4), "materials": [make_material(rnd, i) for i in range(rnd.randint(2, 6))]}
            for t in range(rnd.randint(8, 14))
        ],
        "comments": [
            {"student": f"{rnd.choice(SURNAMES)} {rnd.choice(['КН', 'ПЗ', 'КБ', 'ІС'])}-{rnd.randint(21, 25)}",
             "text": phrase(rnd, rnd.randint(3, 12)),
             "at": BASE_TIME + timedelta(minutes=k * 37 + rnd.randint(0, 30))}
            for k in range(rnd.randint(0, 50))
        ],
    }


class Ids:
    def __init__(self):
        self.page = self.topic = self.material = self.question = self.comment = 0


def page_rows(doc, ids, out):
    ids.page += 1
    pid = ids.page
    out["lms_pages"].append((pid, doc["course_code"], doc["title"], doc["department"],
                             doc["lecturer"]["name"], doc["lecturer"]["email"], doc["term"]))
    for tag in doc["tags"]:
        out["lms_page_tags"].append((pid, tag))
    for t in doc["topics"]:
        ids.topic += 1
        tid = ids.topic
        out["lms_topics"].append((tid, pid, t["no"], t["title"]))
        for pos, m in enumerate(t["materials"], 1):
            ids.material += 1
            mid = ids.material
            out["lms_materials"].append((mid, tid, pos, m["type"], m["title"], m.get("url"),
                                         m.get("duration_sec"), m.get("pages"), m.get("size_kb")))
            for qpos, q in enumerate(m.get("questions", []), 1):
                ids.question += 1
                out["lms_quiz_questions"].append((ids.question, mid, qpos, q["q"], q["options"], q["answer"]))
    for c in doc["comments"]:
        ids.comment += 1
        out["lms_comments"].append((ids.comment, pid, c["student"], c["text"], c["at"]))


COLUMNS = {
    "lms_pages": "id, course_code, title, department, lecturer_name, lecturer_email, term",
    "lms_page_tags": "page_id, tag",
    "lms_topics": "id, page_id, no, title",
    "lms_materials": "id, topic_id, position, type, title, url, duration_sec, pages, size_kb",
    "lms_quiz_questions": "id, material_id, position, question, options, answer",
    "lms_comments": "id, page_id, student, text, created_at",
}


def main(n_pages):
    rnd = random.Random(42)
    db = mongo()
    db.course_pages.delete_many({})
    conn = pg()
    with open("sql/schema.sql", encoding="utf-8") as f:
        conn.execute(f.read())

    ids = Ids()
    t_mongo = t_pg = 0.0
    batch = 1000
    for start in range(0, n_pages, batch):
        docs = [make_page(rnd, n) for n in range(start + 1, min(start + batch, n_pages) + 1)]
        rows = {k: [] for k in COLUMNS}
        for d in docs:
            page_rows(d, ids, rows)

        t0 = time.perf_counter()
        db.course_pages.insert_many(docs, ordered=False)
        t_mongo += time.perf_counter() - t0

        t0 = time.perf_counter()
        with conn.transaction(), conn.cursor() as cur:
            for table, cols in COLUMNS.items():
                with cur.copy(f"COPY {table} ({cols}) FROM STDIN") as cp:
                    for r in rows[table]:
                        cp.write_row(r)
        t_pg += time.perf_counter() - t0
        print(f"{min(start + batch, n_pages)}/{n_pages}", end="\r")

    for table in ["lms_pages", "lms_topics", "lms_materials", "lms_quiz_questions", "lms_comments"]:
        conn.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT max(id) FROM {table}))")
    with open("sql/indexes.sql", encoding="utf-8") as f:
        for stmt in f.read().split(";"):
            if stmt.strip():
                conn.execute(stmt)

    print()
    print(f"pages={ids.page} topics={ids.topic} materials={ids.material} "
          f"questions={ids.question} comments={ids.comment}")
    print(f"bulk load: mongo {t_mongo:.1f}s, postgres {t_pg:.1f}s")
    size_pg = conn.execute("SELECT pg_size_pretty(sum(pg_total_relation_size(c.oid))) FROM pg_class c "
                           "WHERE c.relname LIKE 'lms_%' AND c.relkind = 'r'").fetchone()[0]
    st = db.command("collStats", "course_pages")
    print(f"size: postgres {size_pg}, mongo {(st['storageSize'] + st['totalIndexSize']) / 2**20:.0f} MB")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10000)
