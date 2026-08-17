import os
import sys
import json
import re
import urllib.request
import urllib.parse

try:
    import pypdf
except ImportError:
    print("pypdf required")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
PDF_PATH = os.path.join(BASE_DIR, "CIA exam", "CIA Part 1 ver14 new.pdf")
JSON_PATH = os.path.join(DATA_DIR, "questions_part1.json")

OFFICIAL_TERMS = [
    ("การประกันที่เป็นอิสระ", "การให้ความเชื่อมั่นที่เป็นอิสระ"),
    ("บริการการรับประกัน", "งานบริการให้ความเชื่อมั่น"),
    ("บริการรับประกัน", "งานบริการให้ความเชื่อมั่น"),
    ("ผู้บริหารการตรวจสอบหลัก", "หัวหน้าผู้บริหารงานตรวจสอบ"),
    ("หัวหน้าเจ้าหน้าที่ตรวจสอบ", "หัวหน้าผู้บริหารงานตรวจสอบ"),
    ("การตรวจสอบภายใน กิจกรรม", "กิจกรรมการตรวจสอบภายใน"),
    ("ฟังก์ชันการตรวจสอบภายใน", "หน่วยงานตรวจสอบภายใน"),
    ("กรอบแนวคิดการปฏิบัติงานวิชาชีพสากล", "มาตรฐานการตรวจสอบภายในสากล"),
    ("ความรอบคอบเยี่ยงผู้ประกอบวิชาชีพ", "ความระมัดระวังรอบคอบเยี่ยงผู้ประกอบวิชาชีพ"),
]

def translate_api(text):
    if not text or not text.strip(): return ""
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=th&dt=t&q=" + urllib.parse.quote(text)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            sentences = [item[0] for item in data[0] if item and item[0]]
            res = ''.join(sentences)
            for old_term, new_term in OFFICIAL_TERMS:
                res = res.replace(old_term, new_term)
            return res
    except Exception as e:
        return text

def parse_gleim_p1_all():
    reader = pypdf.PdfReader(PDF_PATH)
    full_text = '\n'.join([p.extract_text() for p in reader.pages if p.extract_text()])
    q_pattern = r'\[\d+\]\s+Gleim\s+#:'
    matches = list(re.finditer(q_pattern, full_text))
    
    questions = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx+1].start() if idx + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end]
        lines = [line.strip() for line in chunk.split('\n') if line.strip()]
        if not lines: continue
        
        header = lines[0]
        header_match = re.match(r'\[(\d+)\]\s+Gleim\s+#:\s+([\d\.]+)', header)
        orig_num = int(header_match.group(1)) if header_match else idx + 1
        topic = header_match.group(2) if header_match else f'1.{idx+1}'
        
        a_idx, b_idx, c_idx, d_idx = -1, -1, -1, -1
        for line_idx, line in enumerate(lines):
            if re.search(r'(?:[A-Z0-9\.\,\s]+|\b)A\.$', line) or re.search(r'\s+A\.\s*', line) or line.startswith('A.'): a_idx = line_idx
            if re.search(r'(?:[A-Z0-9\.\,\s]+|\b)B\.$', line) or re.search(r'\s+B\.\s*', line) or line.startswith('B.'): b_idx = line_idx
            if re.search(r'(?:[A-Z0-9\.\,\s]+|\b)C\.$', line) or re.search(r'\s+C\.\s*', line) or line.startswith('C.'): c_idx = line_idx
            if re.search(r'(?:[A-Z0-9\.\,\s]+|\b)D\.$', line) or re.search(r'\s+D\.\s*', line) or line.startswith('D.'): d_idx = line_idx
            
        ans_match = re.search(r'Answer\s+\(([A-D])\)\s+is\s+correct', chunk, re.IGNORECASE)
        
        if a_idx != -1 and b_idx != -1 and c_idx != -1 and d_idx != -1 and ans_match:
            q_text = ' '.join(lines[1:a_idx])
            
            def clean_opt(line):
                return re.sub(r'\s*[A-D]\.\s*$', '', line).strip()
                
            opt_a = clean_opt(lines[a_idx])
            opt_b = clean_opt(lines[b_idx])
            opt_c = clean_opt(lines[c_idx])
            opt_d = clean_opt(lines[d_idx])
            
            ans_index = ord(ans_match.group(1).upper()) - ord('A')
            
            exp_raw = chunk[ans_match.end():].strip()
            exp_raw = re.sub(r'Gleim CIA Test Prep.*', '', exp_raw, flags=re.DOTALL).strip()
            exp_raw = re.sub(r'Copyright.*', '', exp_raw, flags=re.DOTALL).strip()
            exp_raw = re.sub(r'\[\d+\].*', '', exp_raw).strip()
            
            questions.append({
                'id': len(questions) + 1,
                'qid': f'GL_P1_{orig_num}',
                'topic': topic,
                'question_en': q_text,
                'options_en': [opt_a, opt_b, opt_c, opt_d],
                'answer_index': ans_index,
                'explanation_en': exp_raw
            })
            
    return questions

def process_batch(batch_num, total_batches=5):
    print(f"Parsing Gleim Part 1 Ver 14 PDF (Full Extract)...")
    all_qs = parse_gleim_p1_all()
    total_qs = len(all_qs)
    
    batch_size = (total_qs + total_batches - 1) // total_batches
    start_idx = (batch_num - 1) * batch_size
    end_idx = min(batch_num * batch_size, total_qs)
    
    target_batch = all_qs[start_idx:end_idx]
    print(f"Total valid questions extracted: {total_qs}")
    print(f"Translating Batch {batch_num}/{total_batches} (Questions {start_idx + 1} to {end_idx} of {total_qs})...")
    
    existing = []
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except: pass

    existing_map = {q.get("qid", q.get("question_en")): q for q in existing}

    for idx, q in enumerate(target_batch):
        key = q["qid"]
        if key in existing_map and existing_map[key].get("question_th") != existing_map[key].get("question_en"):
            q["question_th"] = existing_map[key]["question_th"]
            q["options_th"] = existing_map[key]["options_th"]
            q["explanation_th"] = existing_map[key]["explanation_th"]
        else:
            q["question_th"] = translate_api(q["question_en"])
            q["options_th"] = [translate_api(opt) for opt in q["options_en"]]
            q["explanation_th"] = translate_api(q["explanation_en"])
            
        existing_map[key] = q
        
        if (idx + 1) % 15 == 0 or (idx + 1) == len(target_batch):
            updated_list = sorted(list(existing_map.values()), key=lambda x: x.get("id", 0))
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(updated_list, f, ensure_ascii=False, indent=2)
            print(f" Progress: Batch {batch_num} translated {idx + 1}/{len(target_batch)} questions...")

    print(f"Batch {batch_num} completed successfully! Total database size now: {len(existing_map)} questions.")

if __name__ == "__main__":
    batch = 1
    if len(sys.argv) > 1:
        try: batch = int(sys.argv[1])
        except: pass
    process_batch(batch)
