import os
import multiprocessing

# 환경 변수 고정 (안정적인 v0 백엔드 및 가속 설정)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["VLLM_USE_V1"] = "0"
os.environ["VLLM_ATTENTION_BACKEND"] = "FLASH_ATTN"

from vllm import LLM, SamplingParams
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

def main():
    print("1. [RAG] VLM이 분석한 텍스트 파일 로드 중...")
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
        quantization="awq",
        gpu_memory_utilization=0.75,   
        max_model_len=4096,            
        trust_remote_code=True
    )
    tokenizer = llm.get_tokenizer()

    # 3. 질문 수행
    user_questions = [
        "M.2 1번 슬롯의 상세 스펙과 CPU 직결 여부를 알려줘.",
        "DDR5 램을 2개만 꽂을 때 추천하는 슬롯 위치는 어디야?"
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

if __name__ == '__main__':
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
    main()