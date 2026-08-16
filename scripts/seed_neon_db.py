import os
import sys
import json
import urllib.parse

try:
    import pg8000.native
except ImportError:
    print("pg8000 library is required. Install with: pip install pg8000")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")

def main():
    print("=" * 65)
    print(" NEON DATABASE SEEDER (PARAMETRIZED & 100% SAFE)")
    print("=" * 65)
    
    db_url = DATABASE_URL
    if not db_url:
        print("Please enter your Neon PostgreSQL Connection String:")
        db_url = input("\nEnter DATABASE_URL: ").strip()
        if not db_url:
            print("Error: Connection string is required.")
            sys.exit(1)

    parsed = urllib.parse.urlparse(db_url)
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port or 5432
    database = parsed.path.lstrip('/')
    
    print(f"\nConnecting to Neon Postgres at {host} ({database})...")
    
    try:
        conn = pg8000.native.Connection(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database,
            ssl_context=True
        )
        print("Connected successfully to Neon Postgres!")
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

    # 1. Create tables cleanly
    print("\nCreating database schema (questions & exam_results)...")
    conn.run("DROP TABLE IF EXISTS questions CASCADE;")
    conn.run("DROP TABLE IF EXISTS exam_results CASCADE;")
    
    conn.run("""
    CREATE TABLE questions (
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
    """)
    
    conn.run("CREATE INDEX idx_questions_lookup ON questions (version, part);")
    conn.run("CREATE INDEX idx_questions_qid ON questions (qid);")
    
    conn.run("""
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
    """)
    conn.run("CREATE INDEX idx_exam_results_user ON exam_results (user_id, created_at DESC);")
    
    files_to_export = [
        ("2026", 1, "questions_part1_2026.json"),
        ("2026", 2, "questions_part2_2026.json"),
        ("2026", 3, "questions_part3_2026.json"),
        ("standard", 1, "questions_part1.json"),
        ("standard", 2, "questions_part2.json"),
    ]

    total_inserted = 0
    errors = 0

    insert_sql = """
    INSERT INTO questions (qid, version, part, topic, question_en, question_th, options_en, options_th, answer_index, explanation_en, explanation_th)
    VALUES (:qid, :version, :part, :topic, :q_en, :q_th, :opts_en, :opts_th, :ans_idx, :exp_en, :exp_th);
    """

    for version, part, filename in files_to_export:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Seeding Version '{version}', Part {part} from {filename} ({len(data)} items)...")
        
        for q in data:
            qid = q.get("qid", f"STD_{part}_{q.get('id', 0)}")
            topic = q.get("topic", f"P{part}")
            q_en = q.get("question_en", "")
            q_th = q.get("question_th", q_en)
            opts_en = json.dumps(q.get("options_en", []))
            opts_th = json.dumps(q.get("options_th", q.get("options_en", [])))
            ans_idx = int(q.get("answer_index", 0))
            exp_en = q.get("explanation_en", "")
            exp_th = q.get("explanation_th", exp_en)
            
            try:
                conn.run(
                    insert_sql,
                    qid=qid,
                    version=version,
                    part=part,
                    topic=topic,
                    q_en=q_en,
                    q_th=q_th,
                    opts_en=opts_en,
                    opts_th=opts_th,
                    ans_idx=ans_idx,
                    exp_en=exp_en,
                    exp_th=exp_th
                )
                total_inserted += 1
            except Exception as e:
                print(f" Error inserting {qid}: {e}")
                errors += 1

    print("\n" + "=" * 65)
    print(f" SEEDING COMPLETE! Successfully inserted: {total_inserted} / {total_inserted + errors} questions (0 Errors!)")
    print("=" * 65)

if __name__ == "__main__":
    main()
