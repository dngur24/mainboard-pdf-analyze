import os
import gc
import torch
from PIL import Image  
from pdf2image import convert_from_path
from vllm import LLM, SamplingParams

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

def main():
    # pdf_path = "mb_manual/MAG_B850M_MORTAR_MAX_WIFI_Korean.pdf"
    pdf_path = "mb_manual/MAGB850TOMAHAWKMAXWIFI_Korean.pdf"
    output_txt_path = "./manual_layout.txt"
    
    print("1. [VLM] PDF를 이미지로 변환 중...")
    image_paths = convert_pdf_to_images(pdf_path)
    
    # image_paths = [f"./temp_images/page_{i}.png" for i in range(10)]  # 테스트용으로 10페이지만 처리 (실제 사용 시에는 전체 페이지로 변경)
    # image_paths = [f"./temp_images/page_{i}.png" for i in range(16, 20)]  # 테스트용으로 10페이지만 처리 (실제 사용 시에는 전체 페이지로 변경)
    image_paths = [f"./temp_images/page_{i}.png" for i in range(16, 20)] + ["./temp_images/page_60.png"]

    print("2. [VLM] Qwen2-VL-7B-AWQ 모델 로드 중...")
    vlm_model = "Qwen/Qwen2-VL-7B-Instruct-AWQ"
    
    # Qwen2-VL의 이미지 픽셀 제한 및 VRAM 방어 설정
    llm = LLM(
        model=vlm_model,
        quantization="awq_marlin",
        gpu_memory_utilization=0.9,
        max_model_len=2048,
        trust_remote_code=True,
        # 이미지 글씨가 깨지지 않도록 최대 픽셀 제한을 넉넉하게 설정 (기본값으로 두거나 아래처럼 인자 추가 가능)
        mm_processor_kwargs={"max_pixels": 1024 * 1024} 
    )
    
    final_texts = []
    
    print("3. [VLM] 페이지별 이미지 분석 및 텍스트화 시작 (시간이 다소 소요됩니다)...")
    for i, img_path in enumerate(image_paths):
        # ★ 1. 이미지 경로가 아닌 PIL 이미지 객체로 변환
        pil_img = Image.open(img_path).convert("RGB")
        
        # ★ 2. Qwen2-VL 전용 프롬프트 템플릿 및 특수 토큰(<|image_pad|>) 적용
        prompt = (
            "<|im_start|>user\n"
            "<|image_pad|>\n"
            "이 메인보드 매뉴얼 페이지에 있는 모든 텍스트, 표(Table), 조립 다이어그램 그림을 하나도 빠짐없이 "
            "대학원생 수준으로 아주 상세하게 기술 문서 형태로 받아적고 설명해줘. "
            "특히 메인보드의 확장 슬롯, M.2 슬롯 번호와 PCIe 레인 배정 정보는 절대 누락하면 안 돼.<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        
        # 긴 텍스트 출력을 위해 max_tokens를 2048로 확장
        sampling_params = SamplingParams(temperature=0.1, max_tokens=2048)
        
        # ★ 3. 주입 구조 변경 (image 객체를 전달)
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
        
        # 메모리 해제를 위해 PIL 이미지 닫기 및 임시 이미지 삭제
        pil_img.close()
        os.remove(img_path)
        
    # 결과를 텍스트 파일로 저장
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(final_texts))
        
    print(f"🎉 전처리 완료! 결과가 {output_txt_path}에 저장되었습니다.")

if __name__ == "__main__":
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    # pdf_path = "mb_manual/MAG_B850M_MORTAR_MAX_WIFI_Korean.pdf"
    # convert_pdf_to_images(pdf_path)
    main()