MATCH (n) DETACH DELETE n;

CREATE CONSTRAINT course_code IF NOT EXISTS FOR (c:Course) REQUIRE c.code IS UNIQUE;
CREATE CONSTRAINT student_book IF NOT EXISTS FOR (s:Student) REQUIRE s.book IS UNIQUE;
CREATE CONSTRAINT teacher_email IF NOT EXISTS FOR (t:Teacher) REQUIRE t.email IS UNIQUE;
CREATE CONSTRAINT group_code IF NOT EXISTS FOR (g:Group) REQUIRE g.code IS UNIQUE;

UNWIND [
  {code: 'SE101', name: 'Основи програмування', ects: 6},
  {code: 'MA101', name: 'Дискретна математика', ects: 5},
  {code: 'MA102', name: 'Математичний аналіз', ects: 6},
  {code: 'SE201', name: "Об'єктно-орієнтоване програмування", ects: 5},
  {code: 'CS201', name: 'Бази даних', ects: 5},
  {code: 'CS202', name: 'Алгоритми та структури даних', ects: 5},
  {code: 'EC101', name: 'Мікроекономіка', ects: 5},
  {code: 'EC201', name: 'Макроекономіка', ects: 5},
  {code: 'MA201', name: 'Статистика', ects: 4},
  {code: 'CS301', name: 'NoSQL бази даних', ects: 4},
  {code: 'SE301', name: 'Веб-технології', ects: 5},
  {code: 'CS501', name: 'Машинне навчання', ects: 6},
  {code: 'CS502', name: 'Розподілені системи', ects: 5}
] AS row
CREATE (:Course {code: row.code, name: row.name, ects: row.ects});

UNWIND [
  ['SE201', 'SE101'], ['CS201', 'SE101'], ['CS201', 'MA101'], ['CS202', 'SE101'], ['CS202', 'MA101'],
  ['EC201', 'EC101'], ['MA201', 'MA102'], ['CS301', 'CS201'], ['SE301', 'SE201'], ['SE301', 'CS201'],
  ['CS501', 'CS202'], ['CS501', 'MA201'], ['CS502', 'CS301'], ['CS502', 'CS202']
] AS p
MATCH (c:Course {code: p[0]}), (r:Course {code: p[1]})
CREATE (c)-[:REQUIRES]->(r);

UNWIND [
  {email: 'kovalenko@univ.ua', name: 'Коваленко О.В.', courses: ['SE101', 'SE201', 'SE301']},
  {email: 'melnyk@univ.ua', name: 'Мельник І.П.', courses: ['MA101', 'MA102']},
  {email: 'savchenko@univ.ua', name: 'Савченко Т.М.', courses: ['CS201', 'CS301', 'CS502']},
  {email: 'rudenko@univ.ua', name: 'Руденко А.С.', courses: ['CS202', 'CS501']},
  {email: 'lysenko@univ.ua', name: 'Лисенко Н.Г.', courses: ['EC101', 'EC201', 'MA201']}
] AS row
CREATE (t:Teacher {email: row.email, name: row.name})
WITH t, row
UNWIND row.courses AS code
MATCH (c:Course {code: code})
CREATE (t)-[:TEACHES]->(c);

UNWIND ['ІПЗ-25', 'КН-25-1', 'ЕК-25'] AS g
CREATE (:Group {code: g});

UNWIND [
  {book: 'КВ-0001', name: 'Іваненко Марія',   grp: 'ІПЗ-25',  passed: [['SE101', 92], ['MA101', 85], ['MA102', 74], ['SE201', 88], ['CS201', 95]]},
  {book: 'КВ-0002', name: 'Шевченко Андрій',  grp: 'ІПЗ-25',  passed: [['SE101', 67], ['MA101', 61]]},
  {book: 'КВ-0003', name: 'Бондаренко Олег',  grp: 'КН-25-1', passed: [['SE101', 81], ['MA101', 90], ['CS202', 79], ['MA102', 70], ['MA201', 83]]},
  {book: 'КВ-0004', name: 'Ткаченко Ірина',   grp: 'КН-25-1', passed: [['SE101', 99], ['MA101', 97], ['CS201', 91], ['CS202', 93], ['CS301', 96]]},
  {book: 'КВ-0005', name: 'Кравченко Дмитро', grp: 'КН-25-1', passed: [['SE101', 75], ['MA101', 72], ['CS201', 64]]},
  {book: 'КВ-0006', name: 'Олійник Софія',    grp: 'ЕК-25',   passed: [['EC101', 88], ['MA102', 91], ['EC201', 84]]},
  {book: 'КВ-0007', name: 'Мороз Владислав',  grp: 'ЕК-25',   passed: [['EC101', 60]]}
] AS row
MATCH (g:Group {code: row.grp})
CREATE (s:Student {book: row.book, name: row.name})-[:MEMBER_OF]->(g)
WITH s, row
UNWIND row.passed AS p
MATCH (c:Course {code: p[0]})
CREATE (s)-[:PASSED {points: p[1]}]->(c);
