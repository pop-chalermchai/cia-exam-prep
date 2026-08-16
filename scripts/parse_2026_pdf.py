import os
import sys
import json
import re
try:
    import pypdf
except ImportError:
    print("Error: pypdf not installed.")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
PDF1_PATH = os.path.join(BASE_DIR, "CIA exam", "CIA Practice 2026", "1. CIA Practice Questions 2026.pdf")
PDF2_PATH = os.path.join(BASE_DIR, "CIA exam", "CIA Practice 2026", "2. Answer_CIA Practice Questions 2026.pdf")

def clean_text(text):
    text = re.sub(r'Copyright ©.*?\n', '', text)
    text = re.sub(r'Ordinal Question ID Exam Part Syllabus Topic Stem Response A Response B Response C Response D\n', '', text)
    text = re.sub(r'Ordinal Question ID Exam Part Syllabus Topic Stem Key Rationale for Correct Response\n', '', text)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    return text

def parse_pdf2_answers(full_text2):
    ans_pattern = r'(\d+)\s+([A-Z0-9]+)\s+(CIA Part \d+)\s+([\S]+)'
    matches2 = list(re.finditer(ans_pattern, full_text2))
    
    answers_db = {}
    for i, m in enumerate(matches2):
        start = m.start()
        end = matches2[i+1].start() if i+1 < len(matches2) else len(full_text2)
        chunk = full_text2[start:end].strip()
        
        ordinal = int(m.group(1))
        qid = m.group(2)
        part_str = m.group(3)
        topic = m.group(4)
        
        part_num = 1
        if "Part 2" in part_str: part_num = 2
        elif "Part 3" in part_str: part_num = 3
        
        rest = chunk[m.end()-m.start():].strip()
        key_match = re.search(r'\s+([A-D])\s+(Correct.*)', rest, re.DOTALL)
        if key_match:
            stem = rest[:key_match.start()].replace('\n', ' ').strip()
            key_letter = key_match.group(1)
            rationale = key_match.group(2).replace('\n', ' ').strip()
            
            answers_db[qid] = {
                'ordinal': ordinal,
                'qid': qid,
                'part': part_num,
                'topic': topic,
                'stem': stem,
                'key': key_letter,
                'answer_index': ord(key_letter) - ord('A'),
                'rationale': rationale
            }
    return answers_db

def parse_pdf1_options(full_text1, answers_db):
    ans_pattern = r'(\d+)\s+([A-Z0-9]+)\s+(CIA Part \d+)\s+([\S]+)'
    matches1 = list(re.finditer(ans_pattern, full_text1))
    
    questions_by_part = {1: [], 2: [], 3: []}
    
    for i, m in enumerate(matches1):
        start = m.start()
        end = matches1[i+1].start() if i+1 < len(matches1) else len(full_text1)
        chunk = full_text1[start:end].strip()
        qid = m.group(2)
        
        if qid not in answers_db:
            continue
            
        ans = answers_db[qid]
        part = ans['part']
        stem = ans['stem']
        
        # Clean lines in chunk
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        full_chunk_str = re.sub(r'\s+', ' ', ' '.join(lines)).strip()
        
        # Remove header from chunk
        full_chunk_str = re.sub(r'^\d+\s+[A-Z0-9]+\s+CIA Part \d+\s+[\S]+\s+', '', full_chunk_str)
        
        # Remove stem from full_chunk_str
        stem_norm = re.sub(r'\s+', ' ', stem).strip()
        
        if stem_norm in full_chunk_str:
            opt_str = full_chunk_str.split(stem_norm, 1)[1].strip()
        else:
            # Fallback substring match using last 20 chars of stem
            stem_end = stem_norm[-25:] if len(stem_norm) > 25 else stem_norm
            if stem_end in full_chunk_str:
                opt_str = full_chunk_str.split(stem_end, 1)[1].strip()
            else:
                opt_str = full_chunk_str
                
        # Split opt_str into 4 options
        opts = re.split(r'\.\s+(?=[A-Z])', opt_str)
        
        # Format options
        options_en = []
        if len(opts) == 4:
            options_en = [opt if opt.endswith('.') else opt + '.' for opt in opts]
        else:
            # If split yields != 4, chunk by length or approximate 4 pieces
            if len(opts) > 4:
                # Merge extras into 4 items
                options_en = [
                    opts[0] + '.',
                    opts[1] + '.',
                    opts[2] + '.',
                    '. '.join(opts[3:]) + ('.' if not opts[-1].endswith('.') else '')
                ]
            else:
                # Pad to 4
                options_en = opts + [""] * (4 - len(opts))
                
        q_item = {
            "id": len(questions_by_part[part]) + 1,
            "qid": qid,
            "topic": ans['topic'],
            "question_en": stem,
            "options_en": options_en[:4],
            "answer_index": ans['answer_index'],
            "explanation_en": ans['rationale'],
            "question_th": stem,  # Placeholder / English for dual view fallback
            "options_th": options_en[:4],
            "explanation_th": ans['rationale']
        }
        
        questions_by_part[part].append(q_item)
        
    return questions_by_part

def main():
    print(f"Reading PDFs...")
    r1 = pypdf.PdfReader(PDF1_PATH)
    r2 = pypdf.PdfReader(PDF2_PATH)
    
    full1 = clean_text('\n'.join([p.extract_text() for p in r1.pages]))
    full2 = clean_text('\n'.join([p.extract_text() for p in r2.pages]))
    
    print("Parsing PDF 2 (Answers & Rationales)...")
    answers_db = parse_pdf2_answers(full2)
    print(f"Extracted {len(answers_db)} answers.")
    
    print("Parsing PDF 1 (Questions & Options)...")
    questions_by_part = parse_pdf1_options(full1, answers_db)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for part, q_list in questions_by_part.items():
        out_file = os.path.join(DATA_DIR, f"questions_part{part}_2026.json")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(q_list, f, ensure_ascii=False, indent=2)
        print(f"Saved Part {part} (2026 version): {len(q_list)} questions -> {out_file}")

if __name__ == "__main__":
    main()
