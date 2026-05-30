import os
# GPU 가시성 설정 (필요시 사용, 0번 GPU 사용)
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from vllm import LLM, SamplingParams

# 1. 모델 로드 (성공하셨던 안전 설정 유지)
# model_name = "Qwen/Qwen2.5-1.5B-Instruct"
model_name = "Qwen/Qwen2.5-7B-Instruct-AWQ"  # 안전한 모델로 변경

llm = LLM(
    model=model_name,
    gpu_memory_utilization=0.7,
    trust_remote_code=True
)

# 2. Instruct 모델을 위한 챗 템플릿 적용 (이 부분이 핵심입니다!)
tokenizer = llm.get_tokenizer()

raw_prompts = [
    "인공지능의 미래에 대해 한 문장으로 요약해줘.",
    "맛있는 김치찌개를 끓이는 비법은?"
]

# 모델이 인지할 수 있는 대화형 포맷([{'role': 'user', 'content': ...}])으로 변환
prompts = []
for p in raw_prompts:
    chat = [{"role": "user", "content": p}]
    formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    prompts.append(formatted_prompt)

# 3. 추론 파라미터 설정 (생성 토큰을 512로 늘려 김치찌개 답변이 끊기지 않게 함)
sampling_params = SamplingParams(temperature=0.7, max_tokens=512)

# 4. 추론 요청
outputs = llm.generate(prompts, sampling_params)

# 5. 결과 출력
for i, output in enumerate(outputs):
    prompt = raw_prompts[i]
    generated_text = output.outputs[0].text
    print(f"\n[Prompt]: {prompt}")
    print(f"[Response]: {generated_text.strip()}")
