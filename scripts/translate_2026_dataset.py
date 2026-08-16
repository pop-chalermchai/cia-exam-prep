import os
import sys
import json
import time

try:
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library is not installed. Please run: pip install google-generativeai")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
STANDARDS_PDF = os.path.join(BASE_DIR, "2023-7726 GUI Global IA Standards-THAI 05-11.pdf")

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print("\n" + "="*60)
    print(" GEMINI API KEY REQUIRED")
    print("="*60)
    print("Please set your Gemini API key in your terminal:")
    print("  export GEMINI_API_KEY='your_key_here'")
    print("Or enter it below:")
    API_KEY = input("Enter Gemini API Key: ").strip()
    if not API_KEY:
        print("Error: API key is required to translate.")
        sys.exit(1)

genai.configure(api_key=API_KEY)

def translate_batch(model, reference_file_ref, batch_questions):
    to_translate = []
    for q in batch_questions:
        to_translate.append({
            "id": q["id"],
            "question_en": q["question_en"],
            "options_en": q["options_en"],
            "explanation_en": q["explanation_en"]
        })
        
    prompt = f"""
You are an expert internal audit instructor and official translator.
I have attached the official "Global Internal Audit Standards" PDF in Thai language.
Please translate the following batch of CIA multiple-choice exam questions from English to Thai.

CRITICAL INSTRUCTIONS FOR PROFESSIONAL AUDIT TERMINOLOGY:
- You MUST align your translation vocabulary precisely with the official Thai translation found in the attached Global Internal Audit Standards PDF.
- Use official Thai auditing terms:
  - "Internal Audit Activity" -> "กิจกรรมการตรวจสอบภายใน"
  - "Chief Audit Executive (CAE)" -> "หัวหน้าผู้บริหารงานตรวจสอบ"
  - "Board" -> "คณะกรรมการ"
  - "Senior Management" -> "ผู้บริหารระดับสูง"
  - "Independence" -> "ความเป็นอิสระ"
  - "Objectivity" -> "ความเที่ยงธรรม"
  - "Due Professional Care" -> "ความระมัดระวังรอบคอบเยี่ยงผู้ประกอบวิชาชีพ"
  - "Engagement" -> "งานบริการเกี่ยวกับการปฏิบัติงาน" หรือ "การปฏิบัติงานตรวจสอบ"
  - "Assurance Services" -> "งานบริการให้ความเชื่อมั่น"
  - "Consulting Services" -> "งานบริการให้คำปรึกษา"
  - "Control" -> "การควบคุม"
  - "Governance" -> "การกำกับดูแล"
  - "Risk Management" -> "การบริหารความเสี่ยง"
  - "Standards" -> "มาตรฐาน"
  
Format output strictly as a JSON array:
[
  {{
    "id": <id>,
    "question_th": "คำถามภาษาไทย...",
    "options_th": ["ตัวเลือก A ไทย", "ตัวเลือก B ไทย", "ตัวเลือก C ไทย", "ตัวเลือก D ไทย"],
    "explanation_th": "คำอธิบายเฉลยภาษาไทย..."
  }},
  ...
]

Here is the JSON batch of questions to translate:
{json.dumps(to_translate, ensure_ascii=False, indent=2)}
"""
    contents = [reference_file_ref, prompt] if reference_file_ref else [prompt]
    try:
        response = model.generate_content(contents)
        text_response = response.text.strip()
        if text_response.startswith("```json"): text_response = text_response[7:]
        if text_response.endswith("```"): text_response = text_response[:-3]
        translated_data = json.loads(text_response.strip())
        return {item["id"]: item for item in translated_data}
    except Exception as e:
        print(f"Error in batch translation: {e}")
        return None

def translate_part(part_num, ref_file):
    json_path = os.path.join(DATA_DIR, f"questions_part{part_num}_2026.json")
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
        
    untranslated = [q for q in questions if q.get("question_th") == q.get("question_en")]
    print(f"\nPart {part_num} (2026): Total {len(questions)} questions | {len(untranslated)} need Thai translation.")
    
    if not untranslated:
        print(f"Part {part_num} (2026) is already fully translated.")
        return
        
    model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"response_mime_type": "application/json"})
    batch_size = 15
    batches = [untranslated[i:i + batch_size] for i in range(0, len(untranslated), batch_size)]
    
    q_map = {q["id"]: q for q in questions}
    
    for idx, batch in enumerate(batches):
        print(f"Translating Part {part_num} batch {idx+1}/{len(batches)} (IDs {batch[0]['id']}..{batch[-1]['id']})...")
        res = translate_batch(model, ref_file, batch)
        if res:
            for b_item in batch:
                q_id = b_item["id"]
                if q_id in res:
                    q_map[q_id]["question_th"] = res[q_id]["question_th"]
                    q_map[q_id]["options_th"] = res[q_id]["options_th"]
                    q_map[q_id]["explanation_th"] = res[q_id].get("explanation_th", "")
            
            updated_list = sorted(list(q_map.values()), key=lambda x: x["id"])
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_list, f, ensure_ascii=False, indent=2)
            print(f"Batch {idx+1} saved.")
            time.sleep(4)

def main():
    print("="*60)
    print(" TRANSLATE 2026 CIA DATASET TO DUAL LANGUAGE (TH/EN)")
    print("="*60)
    
    ref_file = None
    if os.path.exists(STANDARDS_PDF):
        print("Uploading Thai Standard Reference PDF to Gemini...")
        try:
            ref_file = genai.upload_file(path=STANDARDS_PDF)
            time.sleep(3)
        except Exception as e:
            print(f"Upload warning: {e}")

    for part in [1, 2, 3]:
        translate_part(part, ref_file)
        
    if ref_file:
        try: genai.delete_file(name=ref_file.name)
        except: pass
        
    print("\nAll 2026 parts translated successfully!")

if __name__ == "__main__":
    main()
