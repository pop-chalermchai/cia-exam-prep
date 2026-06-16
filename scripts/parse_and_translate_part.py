import os
import sys
import json
import re
import time
import glob
from tqdm import tqdm

try:
    import pypdf
except ImportError:
    print("Error: 'pypdf' library is not installed. Please run: pip install pypdf")
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library is not installed. Please run: pip install google-generativeai")
    sys.exit(1)

def print_banner(text):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

# Configure API Key
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    print_banner("GEMINI API KEY REQUIRED")
    print("Please set your Gemini API key in the environment:")
    print("  export GEMINI_API_KEY='your_key_here'")
    print("Or paste it below to continue:")
    API_KEY = input("Enter Gemini API Key: ").strip()
    if not API_KEY:
        print("Error: API key is required to translate questions.")
        sys.exit(1)

genai.configure(api_key=API_KEY)

# Directory Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "public", "data")
STANDARDS_PDF = os.path.join(BASE_DIR, "2023-7726 GUI Global IA Standards-THAI 05-11.pdf")

def parse_english_questions_from_pdf(pdf_path):
    print(f"Reading and parsing PDF programmatically: {pdf_path}")
    reader = pypdf.PdfReader(pdf_path)
    
    questions = []
    current_q_text_block = []
    
    # Extract text from all pages
    full_text_list = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            full_text_list.append(page_text)
            
    full_text = "\n".join(full_text_list)
    
    # Regex to find each question block starting with [number] Gleim #:
    q_pattern = r'\[\d+\]\s+Gleim\s+#:'
    matches = list(re.finditer(q_pattern, full_text))
    
    print(f"Found {len(matches)} questions in PDF.")
    
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx+1].start() if idx + 1 < len(matches) else len(full_text)
        chunk = full_text[start:end]
        
        lines = [line.strip() for line in chunk.split('\n') if line.strip()]
        if not lines:
            continue
            
        header = lines[0]
        # Match header fields
        header_match = re.match(r'\[(\d+)\]\s+Gleim\s+#:\s+([\d\.]+)\s+--\s+Source:\s+(.*)', header)
        original_num = int(header_match.group(1)) if header_match else idx + 1
        
        # Locate options ending in A., B., C., D.
        a_idx, b_idx, c_idx, d_idx = -1, -1, -1, -1
        for line_idx, line in enumerate(lines):
            if line.endswith(' A.'): a_idx = line_idx
            elif line.endswith(' B.'): b_idx = line_idx
            elif line.endswith(' C.'): c_idx = line_idx
            elif line.endswith(' D.'): d_idx = line_idx
            
        if a_idx != -1 and b_idx != -1 and c_idx != -1 and d_idx != -1:
            q_text = " ".join(lines[1:a_idx])
            opt_a = lines[a_idx][:-3].strip()
            opt_b = lines[b_idx][:-3].strip()
            opt_c = lines[c_idx][:-3].strip()
            opt_d = lines[d_idx][:-3].strip()
            
            # Find correct answer index
            ans_match = re.search(r'Answer\s+\(([A-D])\)\s+is\s+correct', chunk, re.IGNORECASE)
            if ans_match:
                ans_letter = ans_match.group(1).upper()
                ans_index = ord(ans_letter) - ord('A')
            else:
                # Fallback check
                ans_index = 0
                
            # Extract explanation (everything after correct answer line, cleaned from headers)
            explanation = ""
            if ans_match:
                ans_pos = ans_match.end()
                exp_raw = chunk[ans_pos:].strip()
                # Clean up footer text which Gleim adds at bottom of pages
                exp_raw = re.sub(r'Gleim CIA Test Prep.*', '', exp_raw, flags=re.DOTALL).strip()
                exp_raw = re.sub(r'Copyright.*', '', exp_raw, flags=re.DOTALL).strip()
                # Clean up next question headers if leaked
                exp_raw = re.sub(r'\[\d+\].*', '', exp_raw).strip()
                explanation = exp_raw
                
            questions.append({
                "id": len(questions) + 1,
                "original_num": original_num,
                "question_en": q_text,
                "options_en": [opt_a, opt_b, opt_c, opt_d],
                "answer_index": ans_index,
                "explanation_en": explanation
            })
            
    return questions

def translate_batch(model, reference_file_ref, batch_questions):
    # Formulate JSON to translate
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
  
Ensure the Thai phrasing is grammatically natural, highly professional, and accurate to the accounting and auditing profession.

Format the output strictly as a JSON array where each object has these exact translated fields:
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
    
    # We include the uploaded reference standards file in the content list if available
    if reference_file_ref:
        contents = [reference_file_ref, prompt]
    else:
        contents = [prompt]
    
    max_retries = 3
    retry_delay = 60
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(contents)
            text_response = response.text.strip()
            
            # Clean potential markdown wrappers
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
                
            translated_data = json.loads(text_response.strip())
            return {item["id"]: item for item in translated_data}
            
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower() or "ResourceExhausted" in err_msg:
                if attempt < max_retries - 1:
                    print(f"\n[Quota Exceeded/Rate Limit (429)] Attempt {attempt + 1}/{max_retries} failed.")
                    print(f"Waiting {retry_delay} seconds for quota to reset before retrying...")
                    time.sleep(retry_delay)
                else:
                    print(f"\nFailed to translate batch after {max_retries} attempts due to quota limit.")
                    print(f"Error details: {e}")
                    return None
            else:
                print(f"\nError in batch translation: {e}")
                return None

def main():
    print_banner("CIA EXAM EXTRACTOR & TRANSLATOR (BY GEMINI)")
    
    # 1. Select Part
    print("Please select which CIA exam part you want to process:")
    print(" [1] CIA Part 1 (Essentials of Internal Auditing)")
    print(" [2] CIA Part 2 (Practice of Internal Auditing)")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice not in ["1", "2"]:
        print("Invalid choice. Exiting.")
        sys.exit(1)
        
    part_num = int(choice)
    pdf_name = f"CIA Part {part_num} ver14 new.pdf" if part_num == 1 else "CIA Part 2 ver 14 new.pdf"
    pdf_path = os.path.join(BASE_DIR, pdf_name)
    output_json_path = os.path.join(DATA_DIR, f"questions_part{part_num}.json")
    
    if not os.path.exists(pdf_path):
        print(f"Error: Exam PDF file not found at: {pdf_path}")
        print("Please place the exam PDF in the CIA-Exam-Prep directory and try again.")
        sys.exit(1)
        
    if not os.path.exists(STANDARDS_PDF):
        print(f"Error: Thai Global IA Standards reference PDF not found at: {STANDARDS_PDF}")
        print("Please make sure '2023-7726 GUI Global IA Standards-THAI 05-11.pdf' is in the project folder.")
        sys.exit(1)
        
    # 2. Parse English
    print_banner(f"STEP 1: PARSING ENGLISH QUESTIONS FROM {pdf_name}")
    parsed_questions = parse_english_questions_from_pdf(pdf_path)
    total_parsed = len(parsed_questions)
    
    if total_parsed == 0:
        print("Error: Could not parse any questions. Please check the PDF layout.")
        sys.exit(1)
        
    print(f"Successfully parsed {total_parsed} questions in English.")
    
    # 3. Handle Checkpoints (Check if some questions are already translated)
    existing_translated = {}
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                # Map by id or question text to identify already translated questions
                for q in existing_data:
                    if "question_th" in q and q["question_th"] and len(q.get("options_th", [])) == 4:
                        # Store existing translation mapped by question_en to be robust against id changes
                        existing_translated[q["question_en"]] = {
                            "question_th": q["question_th"],
                            "options_th": q["options_th"],
                            "explanation_th": q.get("explanation_th", "")
                        }
            print(f"Found existing translations for {len(existing_translated)} questions. These will be kept.")
        except Exception as e:
            print(f"Warning reading existing JSON file: {e}")
            
    # Apply existing translations
    merged_questions = []
    untranslated_questions = []
    
    for q in parsed_questions:
        en_text = q["question_en"]
        if en_text in existing_translated:
            trans = existing_translated[en_text]
            q["question_th"] = trans["question_th"]
            q["options_th"] = trans["options_th"]
            q["explanation_th"] = trans["explanation_th"]
            merged_questions.append(q)
        else:
            untranslated_questions.append(q)
            
    print(f"Status:")
    print(f" - Already translated: {len(merged_questions)} questions")
    print(f" - Need translation: {len(untranslated_questions)} questions")
    
    if len(untranslated_questions) == 0:
        print_banner("ALL QUESTIONS ARE ALREADY TRANSLATED")
        # Save full list to output path to ensure correct ordering
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(merged_questions, f, ensure_ascii=False, indent=2)
        print(f"Saved complete database to: {output_json_path}")
        sys.exit(0)
        
    # 4. Select batch size to translate
    print_banner("STEP 2: SELECT TRANSLATION MODE")
    print("Please choose how many of the remaining questions you want to translate:")
    print(" [1] Test Batch: 15 questions (Recommended to quickly verify quality)")
    print(" [2] Mid Batch: 100 questions")
    print(" [3] Full Translation: ALL remaining questions")
    print(" [4] Custom count")
    mode_choice = input("Enter option (1-4): ").strip()
    
    limit = len(untranslated_questions)
    if mode_choice == "1":
        limit = 15
    elif mode_choice == "2":
        limit = 100
    elif mode_choice == "4":
        try:
            limit = int(input(f"Enter number of questions to translate (1-{len(untranslated_questions)}): ").strip())
        except ValueError:
            limit = 15
            
    to_translate_now = untranslated_questions[:limit]
    print(f"\nWe will proceed to translate {len(to_translate_now)} questions now.")
    
    # 5. Connect to Gemini File API and Upload reference PDF
    print_banner("STEP 3: UPLOADING STANDARD REFERENCE PDF TO GEMINI")
    print("Uploading '2023-7726 GUI Global IA Standards-THAI 05-11.pdf'...")
    try:
        ref_file = genai.upload_file(path=STANDARDS_PDF)
        print(f"Successfully uploaded. File URI: {ref_file.uri}")
        # Give API a moment to process the file
        print("Waiting for file processing...")
        time.sleep(3)
    except Exception as e:
        print(f"Error uploading reference PDF: {e}")
        print("Attempting to run translation without reference PDF (quality might be slightly lower)...")
        ref_file = None
        
    # 6. Translate in batches of 15 questions
    print_banner("STEP 4: RUNNING TRANSLATION")
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={"response_mime_type": "application/json"}
    )
    
    batch_size = 15
    batches = [to_translate_now[i:i + batch_size] for i in range(0, len(to_translate_now), batch_size)]
    
    translated_count = 0
    
    for idx, batch in enumerate(batches):
        print(f"\nTranslating batch {idx + 1} of {len(batches)} (Questions {batch[0]['id']} - {batch[-1]['id']})...")
        
        # Call Gemini
        result_map = translate_batch(model, ref_file, batch)
        
        if result_map:
            for q in batch:
                q_id = q["id"]
                if q_id in result_map:
                    trans = result_map[q_id]
                    q["question_th"] = trans["question_th"]
                    q["options_th"] = trans["options_th"]
                    q["explanation_th"] = trans.get("explanation_th", "")
                    merged_questions.append(q)
                    translated_count += 1
            
            # Sort full list by ID
            merged_questions.sort(key=lambda x: x["id"])
            
            # Save checkpoint
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(merged_questions, f, ensure_ascii=False, indent=2)
                
            print(f"Batch {idx + 1} saved successfully. Total translated so far: {len(merged_questions)}/{total_parsed}")
            time.sleep(6) # Rate limit safety buffer for free tier (10 RPM)
        else:
            print(f"Failed to translate batch {idx + 1}. Saving current progress and pausing...")
            # Still save what we have
            merged_questions.sort(key=lambda x: x["id"])
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(merged_questions, f, ensure_ascii=False, indent=2)
            break
            
    # Clean up uploaded file from Gemini File API
    if ref_file:
        try:
            print("\nCleaning up reference file from Gemini API storage...")
            genai.delete_file(name=ref_file.name)
            print("Cleaned up successfully.")
        except Exception as e:
            print(f"Could not delete reference file: {e}")
            
    print_banner("TRANSLATION REPORT")
    print(f"Successfully translated and added {translated_count} new questions.")
    print(f"Total compiled questions in database: {len(merged_questions)} / {total_parsed}")
    print(f"Database saved to: {output_json_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
