db = db.getSiblingDB("lms");
db.course_pages.drop();

db.createCollection("course_pages", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["course_code", "title", "department", "lecturer", "term", "topics"],
      properties: {
        course_code: { bsonType: "string" },
        title: { bsonType: "string" },
        department: { bsonType: "string" },
        term: { bsonType: "string", pattern: "^\\d{4}/\\d{4}-[12]$" },
        lecturer: {
          bsonType: "object",
          required: ["name", "email"],
          properties: { name: { bsonType: "string" }, email: { bsonType: "string" } }
        },
        tags: { bsonType: "array", items: { bsonType: "string" } },
        topics: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["no", "title", "materials"],
            properties: {
              no: { bsonType: "int" },
              materials: {
                bsonType: "array",
                items: {
                  bsonType: "object",
                  required: ["type", "title"],
                  properties: {
                    type: { enum: ["video", "pdf", "quiz", "link"] },
                    duration_sec: { bsonType: "int", minimum: 1 },
                    pages: { bsonType: "int", minimum: 1 }
                  }
                }
              }
            }
          }
        },
        comments: { bsonType: "array", maxItems: 50 }
      }
    }
  }
});

db.course_pages.createIndex({ course_code: 1 }, { unique: true });
db.course_pages.createIndex({ tags: 1 });
db.course_pages.createIndex({ "topics.materials.type": 1, "topics.materials.duration_sec": 1 });
db.course_pages.createIndex({ department: 1 });
print("ok");
