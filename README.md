Lab2 STBD, NoSQL. Предметна область з Lab1 (університет, PostgreSQL): https://github.com/Alemek1075/STDB_task

1. Види NoSQL (документні, ключ-значення, широкостовпцеві, графові) розібрані за лекціями 5-9.

2. Винести є що: сторінку курсу в LMS (теми, матеріали, тести, коментарі). Її завжди читають цілою, а матеріали мають різну структуру залежно від типу (у відео є тривалість, у pdf сторінки, у тесту питання). У SQL це 6 таблиць і купа NULL-колонок. Оцінки, зарахування й оплати лишаються в PostgreSQL, бо там потрібні транзакції, FK і тригери з Lab1. Обрав MongoDB. Коментарі в документі обрізаю до 50 останніх, щоб масив не ріс без меж.

3. MongoDB: mongo/init.js (валідатор $jsonSchema, індекси), mongo/queries.js (insert, find, update, arrayFilters, aggregate, explain, delete). Скріни 01, 02.

4. Те саме в PostgreSQL: sql/schema.sql (6 таблиць), sql/indexes.sql, sql/queries.sql. Скріни 03, 04.

5. Бенчмарк: bench/gen.py генерує 20 000 однакових сторінок в обидві бази (у PG це 2.6 млн рядків), bench/bench.py міряє, результат у bench/results.csv і bench/bench_output.txt. Скріни 05, 06.
Умови: обидві бази по 2 CPU і 2 GB, клієнт запускається контейнером у тій самій docker-мережі (через проксі Docker Desktop на Windows вставка в PG давала зайві 40 мс), спершу прогрів, рахую медіану і p95. Для запису в Mongo стоїть j:true, щоб чекати журнал так само, як PG чекає fsync.
Результат: відкрити сторінку курсу в Mongo в 2.6 раза швидше (0.41 проти 1.09 мс), створити сторінку теж швидше (4.3 проти 5.7 мс). PG виграє на пошуку з фільтром (0.49 проти 0.61 мс), на аналітиці по всіх курсах (119 проти 501 мс, $unwind дорогий) і на дрібних записах, тобто на коментарі й оновленні одного поля (1.9 проти 4.0 мс). Висновок: Mongo має сенс там, де дані читаються і пишуться цілим агрегатом, а звіти краще рахувати в SQL.

6. Інший тип, графова Neo4j: граф пререквізитів курсів, студенти, викладачі, групи. neo4j/graph.cypher (обмеження, дані), neo4j/queries.cypher (MATCH, шляхи змінної довжини, shortestPath, які курси студенту вже доступні, рекомендація, агрегація, MERGE, SET, перевірка циклу, DELETE). Скріни 07, 08.

Запуск:
docker compose up -d
docker compose exec -T mongo mongosh --quiet /mongo/init.js
docker compose run --rm bench bench/gen.py 20000
docker compose exec -T mongo mongosh --quiet /mongo/queries.js
docker compose exec -T pg psql -U postgres -d lms -f /sql/queries.sql
docker compose run --rm bench bench/bench.py
python bench/chart.py
docker compose exec -T neo4j cypher-shell -u neo4j -p lab2pass123 -f /cypher/graph.cypher
docker compose exec -T neo4j cypher-shell -u neo4j -p lab2pass123 -f /cypher/queries.cypher
