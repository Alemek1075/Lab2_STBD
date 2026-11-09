// 1. скільки вершин і ребер кожного типу
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;
MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS edges ORDER BY rel;

// 2. прямі пререквізити курсу
MATCH (:Course {code: 'CS502'})-[:REQUIRES]->(p:Course)
RETURN p.code AS code, p.name AS name ORDER BY code;

// 3. усі пререквізити ланцюжком (шлях змінної довжини)
MATCH path = (:Course {code: 'CS502'})-[:REQUIRES*1..]->(p:Course)
RETURN p.code AS code, p.name AS name, min(length(path)) AS depth ORDER BY depth, code;

// 4. найкоротший шлях між двома курсами
MATCH path = shortestPath((:Course {code: 'CS501'})-[:REQUIRES*]->(:Course {code: 'MA102'}))
RETURN [c IN nodes(path) | c.code] AS chain, length(path) AS hops;

// 5. що студент може записати зараз: усі пререквізити складено, сам курс ще ні
MATCH (s:Student {book: 'КВ-0001'}), (c:Course)
WHERE NOT (s)-[:PASSED]->(c)
  AND ALL(p IN [(c)-[:REQUIRES]->(x) | x] WHERE (s)-[:PASSED]->(p))
RETURN c.code AS code, c.name AS name ORDER BY code;

// 6. чого бракує студенту до "Розподілених систем"
MATCH (s:Student {book: 'КВ-0003'}), (:Course {code: 'CS502'})-[:REQUIRES*1..]->(p:Course)
WHERE NOT (s)-[:PASSED]->(p)
RETURN DISTINCT p.code AS missing;

// 7. рекомендація: що складали студенти з подібною історією
MATCH (me:Student {book: 'КВ-0005'})-[:PASSED]->(c:Course)<-[:PASSED]-(other:Student)-[:PASSED]->(rec:Course)
WHERE NOT (me)-[:PASSED]->(rec) AND me <> other
RETURN rec.code AS course, count(DISTINCT other) AS students ORDER BY students DESC, course LIMIT 5;

// 8. агрегація: середній бал і кількість студентів по курсах викладача
MATCH (t:Teacher)-[:TEACHES]->(c:Course)<-[r:PASSED]-(:Student)
RETURN t.name AS teacher, c.code AS course, count(r) AS students, round(avg(r.points), 1) AS avg_points
ORDER BY teacher, course;

// 9. MERGE ідемпотентний: другий запуск нічого не створить
MERGE (c:Course {code: 'CS303'}) ON CREATE SET c.name = 'Графові бази даних', c.ects = 3
MERGE (r:Course {code: 'CS301'})
MERGE (c)-[:REQUIRES]->(r)
RETURN c.code, c.name;
MERGE (c:Course {code: 'CS303'}) ON CREATE SET c.name = 'дубль'
RETURN c.code, c.name;

// 10. SET: оновити бал студента
MATCH (:Student {book: 'КВ-0002'})-[r:PASSED]->(:Course {code: 'MA101'})
SET r.points = 70
RETURN r.points AS new_points;

// 11. перевірка циклу перед додаванням MA101 -> CS303 (MA101 став би вимагати CS303)
MATCH path = (:Course {code: 'CS303'})-[:REQUIRES*]->(:Course {code: 'MA101'})
RETURN count(path) > 0 AS would_create_cycle;

// 12. спроба порушити унікальність
CREATE (:Course {code: 'SE101', name: 'дубль'});

// 13. DELETE: прибрати доданий курс разом з ребрами
MATCH (c:Course {code: 'CS303'}) DETACH DELETE c;
MATCH (c:Course {code: 'CS303'}) RETURN count(c) AS left;
