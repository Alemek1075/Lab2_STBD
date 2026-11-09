db = db.getSiblingDB("lms");

print("--- insertOne");
db.course_pages.deleteOne({ course_code: "DEMO-1" });
printjson(db.course_pages.insertOne({
  course_code: "DEMO-1",
  title: "Бази даних",
  department: "Кафедра ПЗ",
  term: "2026/2027-1",
  lecturer: { name: "Петренко О.І.", email: "petrenko@univ.ua" },
  tags: ["sql", "nosql"],
  topics: [
    { no: 1, title: "Реляційна модель", materials: [
      { type: "video", title: "Вступ", url: "https://video/1", duration_sec: 3000 },
      { type: "pdf", title: "Конспект", url: "https://files/1.pdf", pages: 18, size_kb: 900 }
    ] },
    { no: 2, title: "Документні БД", materials: [
      { type: "quiz", title: "Тест 1", questions: [
        { q: "Що таке BSON?", options: ["формат", "мова", "СУБД"], answer: 0 }
      ] }
    ] }
  ],
  comments: []
}));

print("--- findOne з проєкцією");
printjson(db.course_pages.findOne({ course_code: "DEMO-1" }, { _id: 0, title: 1, "topics.title": 1 }));

print("--- find: курси з тегом nosql, де є відео довше 40 хв");
printjson(db.course_pages.find(
  { tags: "nosql", "topics.materials": { $elemMatch: { type: "video", duration_sec: { $gt: 2400 } } } },
  { _id: 0, course_code: 1, title: 1 }
).sort({ course_code: 1 }).limit(5).toArray());

print("--- updateOne: коментар, у документі тримаємо лише 50 останніх");
printjson(db.course_pages.updateOne(
  { course_code: "DEMO-1" },
  { $push: { comments: { $each: [{ student: "КН-21 Іваненко", text: "Де лаба 2?", at: new Date() }], $slice: -50 } } }
));

print("--- updateOne: змінити url відео в темі 1 (arrayFilters)");
printjson(db.course_pages.updateOne(
  { course_code: "DEMO-1" },
  { $set: { "topics.$[t].materials.$[m].url": "https://video/1-new" } },
  { arrayFilters: [{ "t.no": 1 }, { "m.type": "video" }] }
));

print("--- валідатор не пропускає матеріал невідомого типу");
try {
  db.course_pages.insertOne({ course_code: "BAD", title: "x", department: "x", term: "2026/2027-1",
    lecturer: { name: "x", email: "x" }, topics: [{ no: 1, title: "x", materials: [{ type: "mp3", title: "x" }] }] });
} catch (e) { print("помилка: code " + e.code + ", " + e.errmsg); }

print("--- aggregate: топ-5 кафедр за сумарною тривалістю відео (год)");
printjson(db.course_pages.aggregate([
  { $unwind: "$topics" },
  { $unwind: "$topics.materials" },
  { $match: { "topics.materials.type": "video" } },
  { $group: { _id: "$department", hours: { $sum: { $divide: ["$topics.materials.duration_sec", 3600] } } } },
  { $sort: { hours: -1 } },
  { $limit: 5 },
  { $project: { hours: { $round: ["$hours", 1] } } }
]).toArray());

print("--- explain: пошук по тегу йде по індексу");
const ex = db.course_pages.find({ tags: "nosql" }).explain("executionStats");
const plan = ex.queryPlanner.winningPlan;
printjson({ stage: plan.stage, input: plan.inputStage && plan.inputStage.stage,
  index: plan.inputStage && plan.inputStage.indexName,
  keysExamined: ex.executionStats.totalKeysExamined, returned: ex.executionStats.nReturned,
  ms: ex.executionStats.executionTimeMillis });

print("--- deleteOne");
printjson(db.course_pages.deleteOne({ course_code: "DEMO-1" }));
