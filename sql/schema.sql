DROP TABLE IF EXISTS lms_comments, lms_quiz_questions, lms_materials, lms_topics, lms_page_tags, lms_pages CASCADE;

CREATE TABLE lms_pages (
    id              int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    course_code     varchar(20)  NOT NULL UNIQUE,
    title           varchar(200) NOT NULL,
    department      varchar(200) NOT NULL,
    lecturer_name   varchar(150) NOT NULL,
    lecturer_email  varchar(100) NOT NULL,
    term            varchar(11)  NOT NULL CHECK (term ~ '^\d{4}/\d{4}-[12]$'),
    updated_at      timestamptz  NOT NULL DEFAULT now()
);

CREATE TABLE lms_page_tags (
    page_id  int         NOT NULL REFERENCES lms_pages (id) ON DELETE CASCADE,
    tag      varchar(50) NOT NULL,
    PRIMARY KEY (page_id, tag)
);

CREATE TABLE lms_topics (
    id       int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    page_id  int          NOT NULL REFERENCES lms_pages (id) ON DELETE CASCADE,
    no       smallint     NOT NULL,
    title    varchar(200) NOT NULL,
    UNIQUE (page_id, no)
);

CREATE TABLE lms_materials (
    id            int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    topic_id      int          NOT NULL REFERENCES lms_topics (id) ON DELETE CASCADE,
    position      smallint     NOT NULL,
    type          varchar(10)  NOT NULL CHECK (type IN ('video', 'pdf', 'quiz', 'link')),
    title         varchar(200) NOT NULL,
    url           varchar(300),
    duration_sec  int CHECK (duration_sec > 0),
    pages         int CHECK (pages > 0),
    size_kb       int,
    CHECK (type <> 'video' OR duration_sec IS NOT NULL),
    CHECK (type <> 'pdf' OR pages IS NOT NULL)
);

CREATE TABLE lms_quiz_questions (
    id           int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_id  int      NOT NULL REFERENCES lms_materials (id) ON DELETE CASCADE,
    position     smallint NOT NULL,
    question     text     NOT NULL,
    options      text[]   NOT NULL,
    answer       smallint NOT NULL
);

CREATE TABLE lms_comments (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    page_id     int          NOT NULL REFERENCES lms_pages (id) ON DELETE CASCADE,
    student     varchar(150) NOT NULL,
    text        text         NOT NULL,
    created_at  timestamptz  NOT NULL DEFAULT now()
);
