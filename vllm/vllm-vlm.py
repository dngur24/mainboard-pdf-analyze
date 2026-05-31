import os
import multiprocessing
import json
import re

# 환경 변수 고정 (안정적인 v0 백엔드 및 가속 설정)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# os.environ["VLLM_USE_V1"] = "0"
# os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"

from vllm import LLM, SamplingParams
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

def main():
    # 분석 대상 메인보드 매뉴얼 파일명 (확장자 제외)
    # vllm-pre-vlm.py에서 사용한 파일명과 동일하게 설정하세요.
    print("1. [RAG] VLM이 분석한 텍스트 파일 로드 중...")
    manual_name = "MAG_B850M_MORTAR_MAX_WIFI_Korean"
    
    print(f"1. [RAG] VLM이 분석한 텍스트 파일({manual_name}) 로드 중...")
    txt_path = "./manual_layout.txt"
    
    if not os.path.exists(txt_path):
        raise FileNotFoundError("⚠️ 1단계 전처리 파일(manual_layout.txt)이 없습니다. 1단계를 먼저 실행하세요.")
        
    with open(txt_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 페이지 단위 구분을 보존하며 청크 분할
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    splits = text_splitter.create_documents([full_text])
    print(f"총 {len(splits)}개의 의미론적 문서 조각으로 분할되었습니다.")

    # 임베딩 및 벡터 DB 구축
    embeddings = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
    vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4}) # 정보 밀도가 높으므로 k=4로 상향
    print("벡터 데이터베이스 구축 완료!")

    # 2. 메인 vLLM 모델 로드 (여기서 원래 쓰시던 12.5GB 소모)
    print("2. [RAG] 메인 Qwen2.5 추론 모델 로드 중...")
    model_name = "Qwen/Qwen2.5-7B-Instruct-AWQ"

    llm = LLM(
        model=model_name,
        # quantization="awq",
        quantization="awq_marlin",
        gpu_memory_utilization=0.80,   
        max_model_len=8192,            
        trust_remote_code=True
    )

    tokenizer = llm.get_tokenizer()

    # 3. 질문 수행
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

    # 4. 결과 출력
    sampling_params = SamplingParams(temperature=0.0, max_tokens=512) 
    outputs = llm.generate(prompts, sampling_params)

    for i, output in enumerate(outputs):
        print(f"\n[질문]: {user_questions[i]}")
        print(f"[RAG 답변]:\n{output.outputs[0].text.strip()}")
        print("=" * 60)

    # 5. JSON 추출 (추가된 기능)
    print("\n5. [JSON] 메인보드 사양 정보 추출 시작...")
    
    # 정보 수집을 위한 다양한 검색 쿼리
    extraction_queries = [
        "메인보드 모델명과 칩셋 정보",
        "PCIe 확장 슬롯 목록 및 배속 정보 (Gen, x16, x8, x4 등)",
        "M.2 NVMe 슬롯 구성 정보",
        "PCIe 슬롯과 M.2 슬롯 간의 대역폭 공유(Sharing) 및 비활성화(Disabled) 규칙"
    ]
    
    extraction_context_docs = []
    for q in extraction_queries:
        # 토큰 절약을 위해 k=2로 하향 조정
        extraction_context_docs.extend(retriever.invoke(q, k=2))
    
    # 중복 제거 (내용 기준)
    unique_contents = []
    seen = set()
    for doc in extraction_context_docs:
        if doc.page_content not in seen:
            unique_contents.append(doc.page_content)
            seen.add(doc.page_content)
    
    extraction_context = "\n\n".join(unique_contents)
    print(f"추출용 컨텍스트 크기: {len(extraction_context)}자")
    
    # ID 정제 로직: Korean/English 제거 및 언더바(_)를 공백( )으로 변환
    clean_name = re.sub(r'(_?Korean|_?English)$', '', manual_name, flags=re.IGNORECASE)
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
# - 마크다운 코드 블록(```json ... ```)을 사용해도 좋습니다.
    
    json_chat = [{"role": "user", "content": json_extraction_prompt}]
    json_formatted_prompt = tokenizer.apply_chat_template(json_chat, tokenize=False, add_generation_prompt=True)
    
    # JSON 생성을 위해 max_tokens를 넉넉하게 설정 (중복 생성 방지를 위해 temperature 0 유지)
    json_sampling_params = SamplingParams(temperature=0.0, max_tokens=3072)
    json_output = llm.generate([json_formatted_prompt], json_sampling_params)
    
    raw_json_text = json_output[0].outputs[0].text.strip()
    
    # 마크다운 태그 및 추가 텍스트 제거 로직 (더 견고하게 수정)
    clean_json_text = raw_json_text
    # 1. 마크다운 코드 블록 제거
    clean_json_text = re.sub(r'^```(?:json)?\s*', '', clean_json_text)
    clean_json_text = re.sub(r'\s*```$', '', clean_json_text)
    
    # 2. JSON 객체 부분만 추출 (가장 바깥쪽 { } 찾기)
    # LLM이 JSON 뒤에 설명을 덧붙이는 경우(Extra data 오류)를 방지
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
        
        # ID 강제 재확인 및 덮어쓰기 (AI 실수를 방지하는 2중 장치)
        parsed_json['id'] = final_id
        
        # 파일명도 정제된 이름을 사용
        output_json_path = f"data/{clean_name}.json"
        
        # data 폴더가 없으면 생성
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)
        
        print(f"\n🎉 JSON 추출 완료! 결과가 {output_json_path}에 저장되었습니다.")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 파싱 오류 발생: {e}")
        print("Raw output:", raw_json_text)

if __name__ == '__main__':
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
    main()