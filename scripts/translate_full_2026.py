import os
import json
import time
import urllib.request
import urllib.parse
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")

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
    if not text or not text.strip():
        return ""
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
        print(f"Translation warning: {e}")
        return text

def process_file(part_num):
    json_path = os.path.join(DATA_DIR, f"questions_part{part_num}_2026.json")
    if not os.path.exists(json_path):
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    print(f"\nProcessing Part {part_num} (2026) - Total {len(questions)} questions...")
    
    updated = 0
    for idx, q in enumerate(questions):
        q["question_th"] = translate_api(q["question_en"])
        q["options_th"] = [translate_api(opt) for opt in q["options_en"]]
        q["explanation_th"] = translate_api(q["explanation_en"])
        updated += 1
        
        if (idx + 1) % 15 == 0 or (idx + 1) == len(questions):
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
            print(f"  Part {part_num}: Translated {idx + 1}/{len(questions)} questions...")
            time.sleep(1)

def main():
    print("Starting full automatic Thai translation for 2026 dataset (Part 1, Part 2, Part 3)...")
    for part in [1, 2, 3]:
        process_file(part)
    print("\nAll 2026 questions (Part 1, 2, 3) translated into full Thai successfully!")

if __name__ == "__main__":
    main()
