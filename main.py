"""
main.py
-------
메인보드 PDF 분석 파이프라인의 진입점.

사용법:
    # YAML 파일명으로 모델 지정 (확장자 생략 가능)
    python main.py --vlm_config Qwen2-VL-7B --rag_config Qwen2.5-7B \\
                   --pdf_path mb_manual/MAG_B850M_MORTAR_MAX_WIFI_Korean.pdf

    # 사용 가능한 config 목록 확인
    python main.py --list_configs
"""

import argparse
import multiprocessing
import os
import torch

import lib.vlm as vlm
import lib.analyze as analyze
from lib.config_loader import load_model_config, list_available_configs


def parse_args():
    parser = argparse.ArgumentParser(
        description="메인보드 PDF 분석 파이프라인 (config 파일로 모델 선택)"
    )

    parser.add_argument(
        "--vlm_config",
        default="Qwen2-VL-7B",
        help=(
            "config/vlm-model/ 폴더 안의 YAML 파일명 (확장자 생략 가능).\n"
            "예) --vlm_config Qwen2-VL-7B"
        ),
    )
    parser.add_argument(
        "--rag_config",
        default="Qwen2.5-7B",
        help=(
            "config/rag-model/ 폴더 안의 YAML 파일명 (확장자 생략 가능).\n"
            "예) --rag_config Qwen2.5-7B"
        ),
    )
    parser.add_argument(
        "--pdf_path",
        default="mb_manual/MAG_B850M_MORTAR_MAX_WIFI_Korean.pdf",
        help="분석할 PDF 파일 경로",
    )
    parser.add_argument(
        "--list_configs",
        action="store_true",
        help="사용 가능한 VLM / RAG config 목록을 출력하고 종료합니다.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # ── config 목록 출력 모드 ───────────────────────────────────────────────
    if args.list_configs:
        vlm_configs = list_available_configs("config/vlm-model")
        rag_configs = list_available_configs("config/rag-model")
        print("\n📂 사용 가능한 VLM config (config/vlm-model/):")
        for name in vlm_configs:
            print(f"   - {name}")
        print("\n📂 사용 가능한 RAG config (config/rag-model/):")
        for name in rag_configs:
            print(f"   - {name}")
        print()
        return

    # ── CUDA 확인 ──────────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # ── PDF 경로 정규화 ────────────────────────────────────────────────────
    pdf_path = args.pdf_path.strip()
    if not pdf_path.startswith("mb_manual/"):
        pdf_path = "mb_manual/" + pdf_path

    # ── config 로드 ────────────────────────────────────────────────────────
    vlm_params = load_model_config(args.vlm_config, "config/vlm-model")
    rag_params = load_model_config(args.rag_config, "config/rag-model")

    # ── Step 1: PDF → 텍스트 (VLM) ────────────────────────────────────────
    vlm.pdf_analyze(pdf_path, vlm_params)

    # ── Step 2: 텍스트 → RAG → JSON (LLM) ────────────────────────────────
    analyze.text_analyze(pdf_path, rag_params)


if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass
    main()