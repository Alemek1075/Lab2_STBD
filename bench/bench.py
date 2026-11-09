import csv
import random
import statistics
import sys
import time
from datetime import datetime, timezone

from pymongo import WriteConcern

from common import AGG_MONGO, AGG_SQL, READ_COMMENTS, READ_PAGE_FLAT, READ_PAGE_JSON, READ_TAGS, SEARCH_SQL, mongo, pg
from gen import TAGS, make_page

rnd = random.Random(7)
db = mongo()
pages = db.course_pages
pages_j = pages.with_options(write_concern=WriteConcern(w=1, j=True))
conn = pg()
N_PAGES = conn.execute("SELECT count(*) FROM lms_pages").fetchone()[0]
codes = [f"C-{i:06d}" for i in range(1, N_PAGES + 1)]
results = []


def measure(test, engine, fn, args_list, warmup=30):
    for a in args_list[:warmup]:
        fn(a)
    times = []
    for a in args_list:
        t0 = time.perf_counter()
        fn(a)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    row = {
        "test": test, "engine": engine, "runs": len(times),
        "median_ms": round(statistics.median(times), 3),
        "p95_ms": round(times[int(len(times) * 0.95) - 1], 3),
        "ops_per_sec": round(1000 * len(times) / sum(times), 1),
    }
    results.append(row)
    print(f"{test:<22} {engine:<18} median {row['median_ms']:>9.3f} ms   p95 {row['p95_ms']:>9.3f} ms   {row['ops_per_sec']:>8.1f} op/s")


def mongo_read(code):
    return pages.find_one({"course_code": code})


def pg_read_flat(code):
    with conn.cursor() as cur:
        rows = cur.execute(READ_PAGE_FLAT, (code,)).fetchall()
        pid = rows[0][0]
        doc = {"course_code": rows[0][1], "title": rows[0][2], "department": rows[0][3],
               "lecturer": {"name": rows[0][4], "email": rows[0][5]}, "term": rows[0][6], "topics": []}
        topic = material = None
        for r in rows:
            if topic is None or topic["no"] != r[7]:
                topic = {"no": r[7], "title": r[8], "materials": []}
                doc["topics"].append(topic)
                material = None
            if material is None or material["_pos"] != r[9]:
                material = {"_pos": r[9], "type": r[10], "title": r[11], "url": r[12],
                            "duration_sec": r[13], "pages": r[14], "size_kb": r[15]}
                topic["materials"].append(material)
            if r[16] is not None:
                material.setdefault("questions", []).append({"q": r[17], "options": r[18], "answer": r[19]})
        doc["tags"] = [t for (t,) in cur.execute(READ_TAGS, (pid,)).fetchall()]
        doc["comments"] = cur.execute(READ_COMMENTS, (pid,)).fetchall()
        return doc


def pg_read_json(code):
    return conn.execute(READ_PAGE_JSON, (code,)).fetchone()[0]


def mongo_search(a):
    tag, dur = a
    return list(pages.find(
        {"tags": tag, "topics.materials": {"$elemMatch": {"type": "video", "duration_sec": {"$gt": dur}}}},
        {"_id": 0, "course_code": 1, "title": 1}).sort("course_code", 1).limit(20))


def pg_search(a):
    return conn.execute(SEARCH_SQL, a).fetchall()


def mongo_insert(doc):
    pages_j.insert_one(doc)


def pg_insert(doc):
    topics = doc["topics"]
    mats = [(ti, pos, m) for ti, t in enumerate(topics) for pos, m in enumerate(t["materials"], 1)]
    qs = [(mi, qp, q) for mi, (_, _, m) in enumerate(mats) for qp, q in enumerate(m.get("questions", []), 1)]
    with conn.transaction(), conn.cursor() as cur:
        pid, topic_ids, mat_ids = cur.execute(
            "SELECT nextval(pg_get_serial_sequence('lms_pages', 'id')),"
            " array(SELECT nextval(pg_get_serial_sequence('lms_topics', 'id')) FROM generate_series(1, %s)),"
            " array(SELECT nextval(pg_get_serial_sequence('lms_materials', 'id')) FROM generate_series(1, %s))",
            (len(topics), len(mats))).fetchone()
        cur.execute(
            "INSERT INTO lms_pages (id, course_code, title, department, lecturer_name, lecturer_email, term) "
            "OVERRIDING SYSTEM VALUE VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (pid, doc["course_code"], doc["title"], doc["department"], doc["lecturer"]["name"],
             doc["lecturer"]["email"], doc["term"]))
        cur.execute("INSERT INTO lms_page_tags (page_id, tag) SELECT %s, unnest(%s::text[])", (pid, doc["tags"]))
        cur.execute("INSERT INTO lms_topics (id, page_id, no, title) OVERRIDING SYSTEM VALUE "
                    "SELECT i, %s, n, t FROM unnest(%s::int[], %s::int[], %s::text[]) AS x(i, n, t)",
                    (pid, topic_ids, [t["no"] for t in topics], [t["title"] for t in topics]))
        cur.execute(
            "INSERT INTO lms_materials (id, topic_id, position, type, title, url, duration_sec, pages, size_kb) "
            "OVERRIDING SYSTEM VALUE SELECT * FROM unnest(%s::int[], %s::int[], %s::int[], %s::text[], %s::text[], "
            "%s::text[], %s::int[], %s::int[], %s::int[])",
            (mat_ids, [topic_ids[ti] for ti, _, _ in mats], [p for _, p, _ in mats], [m["type"] for *_, m in mats],
             [m["title"] for *_, m in mats], [m.get("url") for *_, m in mats],
             [m.get("duration_sec") for *_, m in mats], [m.get("pages") for *_, m in mats],
             [m.get("size_kb") for *_, m in mats]))
        if qs:
            cur.execute(
                "INSERT INTO lms_quiz_questions (material_id, position, question, options, answer) "
                "SELECT mid, p, q, string_to_array(o, chr(31)), a "
                "FROM unnest(%s::int[], %s::int[], %s::text[], %s::text[], %s::int[]) AS x(mid, p, q, o, a)",
                ([mat_ids[mi] for mi, _, _ in qs], [p for _, p, _ in qs], [q["q"] for *_, q in qs],
                 [chr(31).join(q["options"]) for *_, q in qs], [q["answer"] for *_, q in qs]))
        if doc["comments"]:
            cs = doc["comments"]
            cur.execute("INSERT INTO lms_comments (page_id, student, text, created_at) "
                        "SELECT %s, s, t, a FROM unnest(%s::text[], %s::text[], %s::timestamptz[]) AS x(s, t, a)",
                        (pid, [c["student"] for c in cs], [c["text"] for c in cs], [c["at"] for c in cs]))


def mongo_comment(code):
    pages_j.update_one({"course_code": code}, {"$push": {"comments": {
        "$each": [{"student": "Бенч КН-21", "text": "Коли дедлайн?", "at": datetime.now(timezone.utc)}],
        "$slice": -50}}})


def pg_comment(code):
    conn.execute("INSERT INTO lms_comments (page_id, student, text) "
                 "SELECT id, 'Бенч КН-21', 'Коли дедлайн?' FROM lms_pages WHERE course_code = %s", (code,))


def mongo_update_nested(a):
    code, no = a
    pages_j.update_one({"course_code": code},
                       {"$set": {"topics.$[t].materials.$[m].url": f"https://video.univ.ua/new-{no}"}},
                       array_filters=[{"t.no": no}, {"m.type": "video"}])


def pg_update_nested(a):
    code, no = a
    conn.execute("UPDATE lms_materials m SET url = %s FROM lms_topics t JOIN lms_pages p ON p.id = t.page_id "
                 "WHERE m.topic_id = t.id AND p.course_code = %s AND t.no = %s AND m.type = 'video'",
                 (f"https://video.univ.ua/new-{no}", code, no))


def main():
    scale = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    n = lambda k: max(20, int(k * scale))
    print(f"pages in db: {N_PAGES}\n")

    read_args = [rnd.choice(codes) for _ in range(n(2000))]
    measure("1 read page", "mongo", mongo_read, read_args)
    measure("1 read page", "pg 3 queries", pg_read_flat, read_args)
    measure("1 read page", "pg json_agg", pg_read_json, read_args)

    search_args = [(rnd.choice(TAGS), rnd.randint(3000, 5300)) for _ in range(n(300))]
    measure("2 search tag+video", "mongo", mongo_search, search_args)
    measure("2 search tag+video", "pg", pg_search, search_args)

    measure("3 aggregate dept", "mongo", lambda _: list(pages.aggregate(AGG_MONGO)), list(range(n(20))), warmup=3)
    measure("3 aggregate dept", "pg", lambda _: conn.execute(AGG_SQL).fetchall(), list(range(n(20))), warmup=3)

    gen_rnd = random.Random(99)
    new_docs = [make_page(gen_rnd, 900000 + i) for i in range(n(500) + 30)]
    for d in new_docs:
        d["course_code"] = d["course_code"].replace("C-", "N-")
    for d in new_docs[:30]:
        mongo_insert(dict(d))
        pg_insert(d)
    measure("4 insert page", "mongo", lambda d: mongo_insert(dict(d)), new_docs[30:], warmup=0)
    measure("4 insert page", "pg", pg_insert, new_docs[30:], warmup=0)

    comment_args = [rnd.choice(codes) for _ in range(n(2000))]
    measure("5 add comment", "mongo", mongo_comment, comment_args)
    measure("5 add comment", "pg", pg_comment, comment_args)

    upd_args = [(rnd.choice(codes), rnd.randint(1, 8)) for _ in range(n(1000))]
    measure("6 update nested", "mongo", mongo_update_nested, upd_args)
    measure("6 update nested", "pg", pg_update_nested, upd_args)

    pages.delete_many({"course_code": {"$regex": "^N-"}})
    conn.execute("DELETE FROM lms_pages WHERE course_code LIKE 'N-%'")

    with open("bench/results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)


if __name__ == "__main__":
    main()
