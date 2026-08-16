import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
SQL_FILE = os.path.join(BASE_DIR, "database", "full_neon_dump.sql")

def dollar_quote(val):
    if val is None:
        return "NULL"
    # Postgres dollar quoting $str$...$str$ avoids any quote/semicolon escaping errors
    return f"$q${val}$q$"

def main():
    sql_lines = []
    sql_lines.append("-- ========================================================")
    sql_lines.append("-- CIA EXAM PREP - FULL NEON POSTGRESQL SEED DUMP")
    sql_lines.append("-- Generated for Neon Serverless Postgres (https://neon.tech)")
    sql_lines.append("-- ========================================================\n")
    
    sql_lines.append("DROP TABLE IF EXISTS questions CASCADE;")
    sql_lines.append("DROP TABLE IF EXISTS exam_results CASCADE;\n")
    
    sql_lines.append("""CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    qid VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL DEFAULT '2026',
    part INT NOT NULL,
    topic VARCHAR(100),
    question_en TEXT NOT NULL,
    question_th TEXT NOT NULL,
    options_en JSONB NOT NULL,
    options_th JSONB NOT NULL,
    answer_index INT NOT NULL,
    explanation_en TEXT,
    explanation_th TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_questions_lookup ON questions (version, part);
CREATE INDEX idx_questions_qid ON questions (qid);

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
\n""")

    files_to_export = [
        ("2026", 1, "questions_part1_2026.json"),
        ("2026", 2, "questions_part2_2026.json"),
        ("2026", 3, "questions_part3_2026.json"),
        ("standard", 1, "questions_part1.json"),
        ("standard", 2, "questions_part2.json"),
    ]

    total_inserted = 0

    for version, part, filename in files_to_export:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        sql_lines.append(f"-- Inserting {len(data)} items for Version '{version}', Part {part} from {filename}")
        
        for q in data:
            qid = q.get("qid", f"STD_{part}_{q.get('id', 0)}")
            topic = q.get("topic", f"P{part}")
            q_en = dollar_quote(q.get("question_en", ""))
            q_th = dollar_quote(q.get("question_th", q.get("question_en", "")))
            opts_en = f"$q${json.dumps(q.get('options_en', []), ensure_ascii=False)}$q$::jsonb"
            opts_th = f"$q${json.dumps(q.get('options_th', q.get('options_en', [])), ensure_ascii=False)}$q$::jsonb"
            ans_idx = int(q.get("answer_index", 0))
            exp_en = dollar_quote(q.get("explanation_en", ""))
            exp_th = dollar_quote(q.get("explanation_th", q.get("explanation_en", "")))
            
            stmt = f"INSERT INTO questions (qid, version, part, topic, question_en, question_th, options_en, options_th, answer_index, explanation_en, explanation_th) VALUES ('{qid}', '{version}', {part}, '{topic}', {q_en}, {q_th}, {opts_en}, {opts_th}, {ans_idx}, {exp_en}, {exp_th});"
            sql_lines.append(stmt)
            total_inserted += 1
            
        sql_lines.append("")

    with open(SQL_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))

    print(f"Exported {total_inserted} questions into SQL file: {SQL_FILE}")

if __name__ == "__main__":
    main()
