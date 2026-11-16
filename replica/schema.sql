-- PROPOSED EXTENSIONS ONLY. Not an application migration and not run at startup.
-- Requires an existing Traccia schema-6 database; apply only to disposable copies.
-- No PRAGMA user_version change: production integration needs a new schema gate.
-- UUIDs are generated/validated by Python uuid4/Pydantic, not Postgres functions.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
CREATE UNIQUE INDEX arch_lessons_subject ON lessons(id,subject_id);
CREATE UNIQUE INDEX arch_transcripts_lesson ON transcripts(id,lesson_id);
CREATE UNIQUE INDEX arch_materials_subject ON materials(id,subject_id);
CREATE TABLE archive_identity (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 singleton INTEGER NOT NULL DEFAULT 1 UNIQUE CHECK(singleton=1),
 label TEXT NOT NULL CHECK(length(label) BETWEEN 1 AND 120)
);
CREATE TABLE note_templates (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 120),
 prompt TEXT NOT NULL CHECK(length(prompt) BETWEEN 1 AND 12000),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 favorite INTEGER NOT NULL DEFAULT 0 CHECK(favorite IN (0,1)),
 UNIQUE(id,archive_id), UNIQUE(archive_id,name)
);
CREATE INDEX arch_note_templates_archive_id ON note_templates(archive_id);
CREATE TABLE subject_preferences (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL UNIQUE REFERENCES subjects(id) ON DELETE RESTRICT,
 template_id TEXT,
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 settings_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(settings_json) AND json_type(settings_json)='object'),
 FOREIGN KEY(template_id,archive_id) REFERENCES note_templates(id,archive_id) ON DELETE RESTRICT
);
CREATE INDEX arch_subject_preferences_archive_id ON subject_preferences(archive_id);
CREATE INDEX arch_subject_preferences_subject_id ON subject_preferences(subject_id);
CREATE INDEX arch_subject_preferences_template_id ON subject_preferences(template_id);
CREATE TABLE import_items (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
 batch_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'receiving' CHECK(state IN ('receiving','review','ready','imported','duplicate','failed','cancelled')),
 staged_name TEXT UNIQUE, sha256 TEXT CHECK(sha256 IS NULL OR length(sha256)=64),
 size_bytes INTEGER NOT NULL DEFAULT 0 CHECK(size_bytes>=0 AND size_bytes<=536870912),
 suggestions_json TEXT NOT NULL DEFAULT '{}' CHECK(json_valid(suggestions_json) AND json_type(suggestions_json)='object'),
 confirmed_json TEXT CHECK(confirmed_json IS NULL OR (json_valid(confirmed_json) AND json_type(confirmed_json)='object')),
 lesson_id TEXT, error_code TEXT,
 FOREIGN KEY(lesson_id,subject_id) REFERENCES lessons(id,subject_id) ON DELETE RESTRICT,
 UNIQUE(archive_id,idempotency_key),
 CHECK((state IN ('imported','duplicate') AND lesson_id IS NOT NULL) OR (state NOT IN ('imported','duplicate') AND lesson_id IS NULL))
);
CREATE INDEX arch_import_items_archive_id ON import_items(archive_id);
CREATE INDEX arch_import_items_subject_id ON import_items(subject_id);
CREATE INDEX arch_import_items_lesson_id ON import_items(lesson_id);
CREATE TABLE lecture_annotations (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
 lesson_id TEXT NOT NULL, material_id TEXT,
 kind TEXT NOT NULL CHECK(kind IN ('highlight','text','image')),
 start_ms INTEGER NOT NULL CHECK(start_ms>=0), end_ms INTEGER CHECK(end_ms IS NULL OR end_ms>=start_ms),
 body TEXT NOT NULL DEFAULT '' CHECK(length(body)<=12000),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>0),
 FOREIGN KEY(lesson_id,subject_id) REFERENCES lessons(id,subject_id) ON DELETE RESTRICT,
 FOREIGN KEY(material_id,subject_id) REFERENCES materials(id,subject_id) ON DELETE RESTRICT,
 CHECK((kind='image' AND material_id IS NOT NULL) OR (kind!='image' AND material_id IS NULL)),
 CHECK(kind!='text' OR length(trim(body))>0)
);
CREATE INDEX arch_lecture_annotations_archive_id ON lecture_annotations(archive_id);
CREATE INDEX arch_lecture_annotations_subject_id ON lecture_annotations(subject_id);
CREATE INDEX arch_lecture_annotations_lesson_id ON lecture_annotations(lesson_id);
CREATE TABLE processing_runs (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
 lesson_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('queued','running','blocked','completed','failed','cancelled','interrupted')),
 config_json TEXT NOT NULL CHECK(json_valid(config_json) AND json_type(config_json)='object'),
 error_code TEXT,
 FOREIGN KEY(lesson_id,subject_id) REFERENCES lessons(id,subject_id) ON DELETE RESTRICT,
 UNIQUE(id,archive_id), UNIQUE(archive_id,idempotency_key)
);
CREATE INDEX arch_processing_runs_archive_id ON processing_runs(archive_id);
CREATE INDEX arch_processing_runs_subject_id ON processing_runs(subject_id);
CREATE INDEX arch_processing_runs_lesson_id ON processing_runs(lesson_id);
CREATE TABLE processing_steps (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 run_id TEXT NOT NULL,
 position INTEGER NOT NULL CHECK(position>=0),
 kind TEXT NOT NULL CHECK(kind IN ('enhance','transcribe','speakers','index','notes')),
 state TEXT NOT NULL CHECK(state IN ('pending','queued','running','completed','failed','skipped','cancelled','interrupted')),
 audio_job_id TEXT REFERENCES audio_jobs(id) ON DELETE RESTRICT,
 study_job_id TEXT REFERENCES study_jobs(id) ON DELETE RESTRICT,
 result_ref TEXT, error_code TEXT,
 FOREIGN KEY(run_id,archive_id) REFERENCES processing_runs(id,archive_id) ON DELETE CASCADE,
 UNIQUE(run_id,position),
 CHECK(audio_job_id IS NULL OR study_job_id IS NULL)
);
CREATE INDEX arch_processing_steps_archive_id ON processing_steps(archive_id);
CREATE INDEX arch_processing_steps_run_id ON processing_steps(run_id);
CREATE INDEX arch_processing_steps_audio_job_id ON processing_steps(audio_job_id);
CREATE INDEX arch_processing_steps_study_job_id ON processing_steps(study_job_id);
CREATE TABLE search_segments (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
 lesson_id TEXT NOT NULL, transcript_id TEXT NOT NULL, segment_id TEXT NOT NULL,
 start_ms INTEGER NOT NULL CHECK(start_ms>=0), end_ms INTEGER NOT NULL CHECK(end_ms>=start_ms),
 body TEXT NOT NULL CHECK(length(body)>0),
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 FOREIGN KEY(lesson_id,subject_id) REFERENCES lessons(id,subject_id) ON DELETE RESTRICT,
 FOREIGN KEY(transcript_id,lesson_id) REFERENCES transcripts(id,lesson_id) ON DELETE RESTRICT,
 UNIQUE(id,archive_id), UNIQUE(transcript_id,segment_id)
);
CREATE INDEX arch_search_segments_archive_id ON search_segments(archive_id);
CREATE INDEX arch_search_segments_subject_id ON search_segments(subject_id);
CREATE INDEX arch_search_segments_lesson_id ON search_segments(lesson_id);
CREATE TABLE qa_threads (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
 lesson_id TEXT,
 title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 200),
 FOREIGN KEY(lesson_id,subject_id) REFERENCES lessons(id,subject_id) ON DELETE RESTRICT,
 UNIQUE(id,archive_id)
);
CREATE INDEX arch_qa_threads_archive_id ON qa_threads(archive_id);
CREATE INDEX arch_qa_threads_subject_id ON qa_threads(subject_id);
CREATE INDEX arch_qa_threads_lesson_id ON qa_threads(lesson_id);
CREATE TABLE qa_messages (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 thread_id TEXT NOT NULL, request_key TEXT NOT NULL,
 question TEXT NOT NULL CHECK(length(question) BETWEEN 1 AND 4000),
 answer TEXT,
 state TEXT NOT NULL CHECK(state IN ('queued','running','completed','abstained','failed','cancelled','interrupted')),
 retrieval_snapshot TEXT NOT NULL CHECK(json_valid(retrieval_snapshot) AND json_type(retrieval_snapshot)='object'),
 model_json TEXT NOT NULL CHECK(json_valid(model_json) AND json_type(model_json)='object'),
 error_code TEXT,
 FOREIGN KEY(thread_id,archive_id) REFERENCES qa_threads(id,archive_id) ON DELETE CASCADE,
 UNIQUE(id,archive_id), UNIQUE(thread_id,request_key),
 CHECK(state NOT IN ('completed','abstained') OR length(trim(COALESCE(answer,'')))>0)
);
CREATE INDEX arch_qa_messages_archive_id ON qa_messages(archive_id);
CREATE INDEX arch_qa_messages_thread_id ON qa_messages(thread_id);
CREATE TABLE qa_citations (
 id TEXT PRIMARY KEY NOT NULL CHECK(length(id)=36),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(created_at,-1)='Z' AND julianday(created_at) IS NOT NULL),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')) CHECK(substr(updated_at,-1)='Z' AND julianday(updated_at) IS NOT NULL),
 archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
 message_id TEXT NOT NULL, source_segment_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL CHECK(ordinal>0),
 quote TEXT NOT NULL CHECK(length(trim(quote))>0),
 FOREIGN KEY(message_id,archive_id) REFERENCES qa_messages(id,archive_id) ON DELETE CASCADE,
 FOREIGN KEY(source_segment_id,archive_id) REFERENCES search_segments(id,archive_id) ON DELETE RESTRICT,
 UNIQUE(message_id,ordinal)
);
CREATE INDEX arch_qa_citations_archive_id ON qa_citations(archive_id);
CREATE INDEX arch_qa_citations_message_id ON qa_citations(message_id);

CREATE INDEX arch_import_batch ON import_items(archive_id,batch_id,created_at,id);
CREATE INDEX arch_import_state ON import_items(archive_id,state,updated_at);
CREATE INDEX arch_annotation_time ON lecture_annotations(lesson_id,start_ms,id);
CREATE INDEX arch_template_name ON note_templates(archive_id,name);
CREATE INDEX arch_run_state ON processing_runs(archive_id,state,created_at);
CREATE UNIQUE INDEX arch_run_active ON processing_runs(lesson_id) WHERE state IN ('queued','running','blocked','interrupted');
CREATE INDEX arch_step_state ON processing_steps(run_id,state,position);
CREATE INDEX arch_search_subject ON search_segments(subject_id,transcript_id,start_ms);
CREATE INDEX arch_thread_updated ON qa_threads(archive_id,subject_id,updated_at,id);
CREATE INDEX arch_message_state ON qa_messages(archive_id,state,created_at);
CREATE INDEX arch_message_thread ON qa_messages(thread_id,created_at,id);
CREATE INDEX arch_template_favorite ON note_templates(archive_id,favorite,name);
CREATE VIRTUAL TABLE search_segments_fts USING fts5(body,content='search_segments',content_rowid='rowid',tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER arch_search_insert AFTER INSERT ON search_segments BEGIN
 INSERT INTO search_segments_fts(rowid,body) VALUES(new.rowid,new.body);
END;
CREATE TRIGGER arch_search_delete AFTER DELETE ON search_segments BEGIN
 INSERT INTO search_segments_fts(search_segments_fts,rowid,body) VALUES('delete',old.rowid,old.body);
END;
CREATE TRIGGER arch_search_update AFTER UPDATE OF body ON search_segments BEGIN
 INSERT INTO search_segments_fts(search_segments_fts,rowid,body) VALUES('delete',old.rowid,old.body);
 INSERT INTO search_segments_fts(rowid,body) VALUES(new.rowid,new.body);
END;
CREATE INDEX arch_fk_subject_preferences_template_id_archive_id ON subject_preferences(template_id,archive_id);
CREATE INDEX arch_fk_import_items_lesson_id_subject_id ON import_items(lesson_id,subject_id);
CREATE INDEX arch_fk_lecture_annotations_material_id_subject_id ON lecture_annotations(material_id,subject_id);
CREATE INDEX arch_fk_lecture_annotations_lesson_id_subject_id ON lecture_annotations(lesson_id,subject_id);
CREATE INDEX arch_fk_processing_runs_lesson_id_subject_id ON processing_runs(lesson_id,subject_id);
CREATE INDEX arch_fk_processing_steps_run_id_archive_id ON processing_steps(run_id,archive_id);
CREATE INDEX arch_fk_search_segments_transcript_id_lesson_id ON search_segments(transcript_id,lesson_id);
CREATE INDEX arch_fk_search_segments_lesson_id_subject_id ON search_segments(lesson_id,subject_id);
CREATE INDEX arch_fk_qa_threads_lesson_id_subject_id ON qa_threads(lesson_id,subject_id);
CREATE INDEX arch_fk_qa_messages_thread_id_archive_id ON qa_messages(thread_id,archive_id);
CREATE INDEX arch_fk_qa_citations_source_segment_id_archive_id ON qa_citations(source_segment_id,archive_id);
CREATE INDEX arch_fk_qa_citations_message_id_archive_id ON qa_citations(message_id,archive_id);
COMMIT;
