import os
import gc
import torch
from PIL import Image
from pdf2image import convert_from_path
from vllm import LLM, SamplingParams

os.environ["CUDA_VISIBLE_DEVICES"] = "0"


def convert_pdf_to_images(pdf_path, output_folder="./temp_images", dpi=130):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(f"[{pdf_path}] 변환 시작...")
    pages = convert_from_path(pdf_path, dpi=dpi)

    image_paths = []
    for i, page in enumerate(pages):
        image_path = os.path.join(output_folder, f"page_{i}.png")
        page.save(image_path, "PNG")
        image_paths.append(image_path)
        print(f"💾 {i+1}페이지 변환 완료: {image_path}")

    return image_paths


def pdf_analyze(pdf_path: str, llm_params: dict):
    """pdf_analyze
    pdf를 이미지로 파싱한 후 vlm 모델을 이용하여 텍스트로 변환하는 함수.

    Args:
        pdf_path (str): PDF 파일 경로
        llm_params (dict): config_loader.load_model_config() 가 반환한
                           vLLM LLM() 초기화 파라미터 딕셔너리.
                           예) {
                                 "model": "Qwen/Qwen2-VL-7B-Instruct-AWQ",
                                 "quantization": "awq_marlin",
                                 "gpu_memory_utilization": 0.9,
                                 "max_model_len": 2048,
                                 "trust_remote_code": True,
                                 "mm_processor_kwargs": {"max_pixels": 1048576}
                               }
    """
    pdf_path = pdf_path.strip()
    output_txt_path = "./manual_layout.txt"

    image_paths = convert_pdf_to_images(pdf_path)

    model_name = llm_params.get("model", "알 수 없는 모델")
    print(f"2. [VLM] 모델 로드 중... ({model_name})")

    llm = LLM(**llm_params)

    final_texts = []

    print("3. [VLM] 페이지별 이미지 분석 및 텍스트화 시작 (시간이 다소 소요됩니다)...")
    for i, img_path in enumerate(image_paths):
        pil_img = Image.open(img_path).convert("RGB")

        prompt = (
            "<|im_start|>user\n"
            "<|image_pad|>\n"
            "이 메인보드 매뉴얼 페이지에 있는 모든 텍스트, 표(Table), 조립 다이어그램 그림을 하나도 빠짐없이 "
            "대학원생 수준으로 아주 상세하게 기술 문서 형태로 받아적고 설명해줘. "
            "특히 메인보드의 확장 슬롯, M.2 슬롯 번호와 PCIe 레인 배정 정보는 절대 누락하면 안 돼.<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        sampling_params = SamplingParams(temperature=0.1, max_tokens=2048)

        outputs = llm.generate(
            {
                "prompt": prompt,
                "multi_modal_data": {"image": pil_img}
            },
            sampling_params
        )

        page_result = outputs[0].outputs[0].text.strip()
        final_texts.append(f"--- [PAGE {i+1}] ---\n{page_result}\n")

        print(f"[{i+1}/{len(image_paths)}] 페이지 분석 완료.")

        pil_img.close()
        os.remove(img_path)

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(final_texts))

    print(f"🎉 전처리 완료! 결과가 {output_txt_path}에 저장되었습니다.")