-- Schema definition for CIA Exam Prep App (Neon Postgres Compatible)

-- Drop existing table if recreating
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS exam_results CASCADE;

-- 1. Questions Table
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    qid VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '2026', -- '2026' or 'standard'
    part INT NOT NULL,                           -- 1, 2, or 3
    topic VARCHAR(100),                         -- Syllabus topic (e.g. A.1.a)
    question_en TEXT NOT NULL,
    question_th TEXT NOT NULL,
    options_en JSONB NOT NULL,                   -- ['Option A', 'Option B', 'Option C', 'Option D']
    options_th JSONB NOT NULL,                   -- ['ตัวเลือก A', 'ตัวเลือก B', 'ตัวเลือก C', 'ตัวเลือก D']
    answer_index INT NOT NULL,                   -- 0, 1, 2, or 3
    explanation_en TEXT,
    explanation_th TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high performance querying
CREATE INDEX idx_questions_lookup ON questions (version, part);
CREATE INDEX idx_questions_qid ON questions (qid);

-- 2. User Exam Results Table (Optional for online history tracking)
CREATE TABLE exam_results (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) DEFAULT 'anonymous',
    version VARCHAR(20) NOT NULL,
    part INT NOT NULL,
    score INT NOT NULL,
    total_questions INT NOT NULL,
    percentage INT NOT NULL,
    is_pass BOOLEAN NOT NULL,
    is_real_exam BOOLEAN NOT NULL,
    time_spent_seconds INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exam_results_user ON exam_results (user_id, created_at DESC);
