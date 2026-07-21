import os
import json
import re

# 환경 변수 고정
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from vllm import LLM, SamplingParams
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def text_analyze(pdf_path: str, llm_params: dict):
    """
    VLM이 생성한 텍스트 파일을 바탕으로 RAG를 실행하고 메인보드 JSON을 추출하는 함수.

    Args:
        pdf_path (str): 원본 PDF 파일 경로 (출력 JSON 파일명 결정에 사용).
        llm_params (dict): config_loader.load_model_config() 가 반환한
                           vLLM LLM() 초기화 파라미터 딕셔너리.
                           예) {
                                 "model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
                                 "quantization": "awq_marlin",
                                 "gpu_memory_utilization": 0.85,
                                 "max_model_len": 8192,
                                 "trust_remote_code": True
                               }
    """
    pdf_path = pdf_path.strip()

    # ── 1. VLM 전처리 결과 텍스트 로드 ──────────────────────────────────────
    print(f"1. [RAG] VLM이 분석한 텍스트 파일({pdf_path}) 로드 중...")
    txt_path = "./manual_layout.txt"

    if not os.path.exists(txt_path):
        raise FileNotFoundError("⚠️ 1단계 전처리 파일(manual_layout.txt)이 없습니다. 1단계를 먼저 실행하세요.")

    with open(txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # ── 2. 청크 분할 & 벡터 DB ────────────────────────────────────────────
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    splits = text_splitter.create_documents([full_text])
    print(f"총 {len(splits)}개의 의미론적 문서 조각으로 분할되었습니다.")

    embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    print("벡터 데이터베이스 구축 완료!")

    # ── 3. LLM 로드 (config 에서 읽은 파라미터 사용) ──────────────────────
    model_name = llm_params.get("model", "알 수 없는 모델")
    print(f"2. [RAG] 추론 모델 로드 중... ({model_name})")

    llm = LLM(**llm_params)
    tokenizer = llm.get_tokenizer()

    # ── 4. RAG Q&A ────────────────────────────────────────────────────────
    user_questions = [
        "M.2 1번 슬롯의 상세 스펙과 CPU 직결 여부를 알려줘.",
    ]

    prompts = []
    for question in user_questions:
        relevant_docs = retriever.invoke(question)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        rag_prompt = f"""당신은 메인보드 기술 지원 전문가입니다. 
제공된 [매뉴얼 내용]은 그림과 표가 모두 텍스트로 치환된 결과물입니다. 이에 기반하여 질문에 정확히 답하세요.

[매뉴얼 내용]:
{context}

[사용자 질문]:
{question}"""

        chat = [{"role": "user", "content": rag_prompt}]
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        prompts.append(formatted_prompt)

    sampling_params = SamplingParams(temperature=0.0, max_tokens=512)
    outputs = llm.generate(prompts, sampling_params)

    for i, output in enumerate(outputs):
        print(f"\n[질문]: {user_questions[i]}")
        print(f"[RAG 답변]:\n{output.outputs[0].text.strip()}")
        print("=" * 60)

    # ── 5. JSON 추출 ──────────────────────────────────────────────────────
    print("\n5. [JSON] 메인보드 사양 정보 추출 시작...")

    extraction_queries = [
        "메인보드 모델명과 칩셋 정보",
        "PCIe 확장 슬롯 목록 및 배속 정보 (Gen, x16, x8, x4 등)",
        "M.2 NVMe 슬롯 구성 정보",
        "PCIe 슬롯과 M.2 슬롯 간의 대역폭 공유(Sharing) 및 비활성화(Disabled) 규칙"
    ]

    extraction_context_docs = []
    for q in extraction_queries:
        extraction_context_docs.extend(retriever.invoke(q, k=2))

    # 중복 제거
    unique_contents = []
    seen = set()
    for doc in extraction_context_docs:
        if doc.page_content not in seen:
            unique_contents.append(doc.page_content)
            seen.add(doc.page_content)

    extraction_context = "\n\n".join(unique_contents)
    print(f"추출용 컨텍스트 크기: {len(extraction_context)}자")

    # ID 정제: Korean/English 접미사 제거, 언더바→공백
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    clean_name = re.sub(r'(_?Korean|_?English)$', '', base_name, flags=re.IGNORECASE)
    final_id = clean_name.replace('_', ' ')

    json_extraction_prompt = f"""당신은 메인보드 사양 분석 전문가입니다. 
제공된 [매뉴얼 내용]을 바탕으로 메인보드의 사양 정보를 아래 JSON 형식에 맞춰 추출하세요.

[매뉴얼 내용]:
{extraction_context}

[JSON 형식 지침]
반드시 아래 키와 구조를 정확히 준수하는 하나의 JSON 객체만 출력하세요.

- id: 반드시 "{final_id}"를 사용하세요.
- name: 공식 제품 명칭 (예: "{final_id}")
- chipset: 메인보드 칩셋 명칭 (예: "B850")
- slots: PCIe 확장 슬롯(Expansion Slots) 리스트. **M.2 슬롯은 여기에 포함하지 마세요.** 각 항목은 반드시 다음 필드를 포함해야 합니다:
    * "id": 소문자/언더바 형식 (예: "pci_e1")
    * "name": 공식 명칭 (예: "PCI_E1 Slot")
    * "type": 버전 및 배속 (예: "PCIe 5.0 x16")
    * "source": "CPU" 또는 "Chipset"
- storage: M.2 NVMe 저장장치 슬롯 리스트. **PCIe 확장 슬롯은 여기에 포함하지 마세요.** 각 항목은 반드시 다음 필드를 포함해야 합니다:
    * "id": 소문자/언더바 형식 (예: "m2_1")
    * "name": 공식 명칭 (예: "M2_1 Slot")
    * "type": 버전 및 배속 (예: "PCIe 5.0 x4")
    * "source": "CPU" 또는 "Chipset"
- sharingRules: 슬롯 간 대역폭 공유 규칙 리스트. 각 항목은 반드시 다음 필드를 포함해야 합니다:
    * "trigger": 원인이 되는 슬롯의 id (예: "m2_3")
    * "impact": 영향을 받는 슬롯의 id (예: "pci_e3")
    * "effect": "disabled" 또는 "reduced"
    * "newSpeed": (선택사항) 변경된 배속 (예: "x2")
    * "description": 규칙에 대한 상세 설명 (한글)

[응답 가이드]
- **중요:** SATA 포트, USB 헤더, 팬 커넥터 등 PCIe/M.2와 무관한 장치는 **절대로 포함하지 마세요.**
- **절대로** 위 스키마를 벗어나는 다른 필드명(예: slot1, slot2, lanes 등)을 사용하지 마세요.
- 매뉴얼에 명시된 실제 슬롯과 규칙만 정확히 추출하세요.
- 오직 유효한 JSON 객체만 출력하세요.

"""

    json_chat = [{"role": "user", "content": json_extraction_prompt}]
    json_formatted_prompt = tokenizer.apply_chat_template(json_chat, tokenize=False, add_generation_prompt=True)

    json_sampling_params = SamplingParams(temperature=0.0, max_tokens=3072)
    json_output = llm.generate([json_formatted_prompt], json_sampling_params)

    raw_json_text = json_output[0].outputs[0].text.strip()

    # 마크다운 코드 블록 제거
    clean_json_text = re.sub(r'^```(?:json)?\s*', '', raw_json_text)
    clean_json_text = re.sub(r'\s*```$', '', clean_json_text)

    # 가장 바깥쪽 { } 추출
    try:
        start_idx = clean_json_text.find('{')
        end_idx = clean_json_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_json_text = clean_json_text[start_idx:end_idx+1]
    except Exception:
        pass

    clean_json_text = clean_json_text.strip()

    try:
        parsed_json = json.loads(clean_json_text)
        parsed_json['id'] = final_id  # AI 실수 방지 강제 재확인

        output_json_path = f"data/{clean_name}.json"
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)

        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 JSON 추출 완료! 결과가 {output_json_path}에 저장되었습니다.")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 파싱 오류 발생: {e}")
        print("Raw output:", raw_json_text)