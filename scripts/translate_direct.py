import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")

TERMS_MAP = [
    ("Chief Audit Executive (CAE)", "หัวหน้าผู้บริหารงานตรวจสอบ (CAE)"),
    ("chief audit executive", "หัวหน้าผู้บริหารงานตรวจสอบ"),
    ("Chief Audit Executive", "หัวหน้าผู้บริหารงานตรวจสอบ"),
    ("internal audit activity", "กิจกรรมการตรวจสอบภายใน"),
    ("Internal audit activity", "กิจกรรมการตรวจสอบภายใน"),
    ("Internal Audit Activity", "กิจกรรมการตรวจสอบภายใน"),
    ("internal audit function", "หน่วยงานตรวจสอบภายใน"),
    ("Internal Audit Function", "หน่วยงานตรวจสอบภายใน"),
    ("internal audit charter", "กฎบัตรการตรวจสอบภายใน"),
    ("Internal Audit Charter", "กฎบัตรการตรวจสอบภายใน"),
    ("internal audit plan", "แผนการตรวจสอบภายใน"),
    ("Internal Audit Plan", "แผนการตรวจสอบภายใน"),
    ("internal auditing", "การตรวจสอบภายใน"),
    ("Internal auditing", "การตรวจสอบภายใน"),
    ("Internal Auditing", "การตรวจสอบภายใน"),
    ("internal auditor", "ผู้ตรวจสอบภายใน"),
    ("internal auditors", "ผู้ตรวจสอบภายใน"),
    ("Internal Auditor", "ผู้ตรวจสอบภายใน"),
    ("Internal Auditors", "ผู้ตรวจสอบภายใน"),
    ("Senior Management", "ผู้บริหารระดับสูง"),
    ("senior management", "ผู้บริหารระดับสูง"),
    ("Board of Directors", "คณะกรรมการบริษัท"),
    ("the board", "คณะกรรมการ"),
    ("The board", "คณะกรรมการ"),
    ("Board", "คณะกรรมการ"),
    ("independence", "ความเป็นอิสระ"),
    ("Independence", "ความเป็นอิสระ"),
    ("objectivity", "ความเที่ยงธรรม"),
    ("Objectivity", "ความเที่ยงธรรม"),
    ("due professional care", "ความระมัดระวังรอบคอบเยี่ยงผู้ประกอบวิชาชีพ"),
    ("Due professional care", "ความระมัดระวังรอบคอบเยี่ยงผู้ประกอบวิชาชีพ"),
    ("Due Professional Care", "ความระมัดระวังรอบคอบเยี่ยงผู้ประกอบวิชาชีพ"),
    ("professional skepticism", "ความสงสัยเยี่ยงผู้ประกอบวิชาชีพ"),
    ("Professional skepticism", "ความสงสัยเยี่ยงผู้ประกอบวิชาชีพ"),
    ("assurance services", "งานบริการให้ความเชื่อมั่น"),
    ("Assurance services", "งานบริการให้ความเชื่อมั่น"),
    ("Assurance Services", "งานบริการให้ความเชื่อมั่น"),
    ("consulting services", "งานบริการให้คำปรึกษา"),
    ("Consulting services", "งานบริการให้คำปรึกษา"),
    ("Consulting Services", "งานบริการให้คำปรึกษา"),
    ("engagement objectives", "วัตถุประสงค์ของการปฏิบัติงานตรวจสอบ"),
    ("engagement workpapers", "กระดาษทำการของการปฏิบัติงานตรวจสอบ"),
    ("audit engagement", "การปฏิบัติงานตรวจสอบ"),
    ("Audit engagement", "การปฏิบัติงานตรวจสอบ"),
    ("engagement", "การปฏิบัติงานตรวจสอบ"),
    ("Engagement", "การปฏิบัติงานตรวจสอบ"),
    ("risk management", "การบริหารความเสี่ยง"),
    ("Risk management", "การบริหารความเสี่ยง"),
    ("Risk Management", "การบริหารความเสี่ยง"),
    ("internal control", "การควบคุมภายใน"),
    ("Internal control", "การควบคุมภายใน"),
    ("Internal Control", "การควบคุมภายใน"),
    ("internal controls", "การควบคุมภายใน"),
    ("Internal controls", "การควบคุมภายใน"),
    ("governance", "การกำกับดูแล"),
    ("Governance", "การกำกับดูแล"),
    ("quality assurance and improvement program", "โปรแกรมการประกันและปรับปรุงคุณภาพ (QAIP)"),
    ("Quality Assurance and Improvement Program", "โปรแกรมการประกันและปรับปรุงคุณภาพ (QAIP)"),
    ("Global Internal Audit Standards", "มาตรฐานการตรวจสอบภายในสากล (Global Internal Audit Standards)"),
    ("Code of Ethics", "จรรยาบรรณวิชาชีพ"),
]

def translate_sentence(text):
    if not text: return ""
    # Base professional translation logic for exam stems and options
    res = text
    
    # Common Sentence Pattern translations for audit questions
    patterns = [
        (r"^What is the primary purpose of (.*?)\?", r"วัตถุประสงค์หลักของ \1 คืออะไร?"),
        (r"^What is a primary benefit of (.*?)\?", r"ประโยชน์หลักของ \1 คืออะไร?"),
        (r"^Which condition is most critical in (.*?)\?", r"เงื่อนไขใดสำคัญที่สุดในการ \1?"),
        (r"^How does (.*?) typically (.*?)\?", r"\1 กำหนด \2 อย่างไรโดยทั่วไป?"),
        (r"^Which of the following is the best example of (.*?)\?", r"ข้อใดต่อไปนี้เป็นตัวอย่างที่ดีที่สุดของ \1?"),
        (r"^Which of the following is most effective in (.*?)\?", r"ข้อใดต่อไปนี้มีประสิทธิผลมากที่สุดในการ \1?"),
        (r"^When planning an engagement, (.*?)\?", r"เมื่อวางแผนการปฏิบัติงานตรวจสอบ \1 อย่างไร?"),
        (r"^During an audit engagement, (.*?)\?", r"ระหว่างการปฏิบัติงานตรวจสอบ \1 อย่างไร?"),
        (r"^Correct\.\s*", r"ถูกต้อง: "),
    ]
    
    for pat, repl in patterns:
        res = re.sub(pat, repl, res)
        
    for eng, th in TERMS_MAP:
        res = res.replace(eng, th)
        
    return res

def process_file(part_num):
    json_path = os.path.join(DATA_DIR, f"questions_part{part_num}_2026.json")
    if not os.path.exists(json_path):
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    print(f"Translating Part {part_num} (2026): {len(questions)} questions...")
    
    for q in questions:
        q["question_th"] = translate_sentence(q["question_en"])
        q["options_th"] = [translate_sentence(opt) for opt in q["options_en"]]
        q["explanation_th"] = translate_sentence(q["explanation_en"])
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        
    print(f"Saved Part {part_num} translated JSON to {json_path}")

def main():
    for p in [1, 2, 3]:
        process_file(p)
    print("Direct translation completed successfully.")

if __name__ == "__main__":
    main()
