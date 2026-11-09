CREATE INDEX ix_lms_page_tags_tag ON lms_page_tags (tag, page_id);
CREATE INDEX ix_lms_topics_page ON lms_topics (page_id);
CREATE INDEX ix_lms_materials_topic ON lms_materials (topic_id);
CREATE INDEX ix_lms_materials_video ON lms_materials (duration_sec, topic_id) WHERE type = 'video';
CREATE INDEX ix_lms_quiz_material ON lms_quiz_questions (material_id);
CREATE INDEX ix_lms_comments_page ON lms_comments (page_id, created_at DESC);
CREATE INDEX ix_lms_pages_department ON lms_pages (department);
VACUUM ANALYZE;
