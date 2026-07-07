import configparser
import argparse
import os 
import multiprocessing
import re
import torch
import json

import lib.analyze as analyze
import lib.vlm  as vlm

config = configparser.ConfigParser()

config.read('config/config.yaml')


config.get()

def main():
    try:
        multiprocessing.set_start_method('spawn')

        parser = argparse.ArgumentParser(description='vllm 모델 선택')
        parser.add_argument('--vlm_model', default='Qwen/Qwen2-VL-7B-Instruct-AWQ',
                            help='전처리에 사용할 모델 이름')
        parser.add_argument('--llm_model', default='Qwen/Qwen2.5-7B-Instruct-AWQ',
                            help='분석에 사용할 모델 이름')
        parser.add_argument('--pdf_path', default='mb_manual/MAG_B850M_MORTAR_MAX_WIFI_Korean.pdf',
                            help='분석할 PDF 파일 경로')
        
        args = parser.parse_args()

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")

        # PDF를 이미지로 변환하고 VLM 모델을 사용하여 텍스트로 변환
        pdf_path = args.pdf_path.strip()  # 공백 제거
        pdf_path = 'mb_manual/' + pdf_path if not pdf_path.startswith('mb_manual/') else pdf_path
        
        vlm.pdf_analyze(pdf_path, args.vlm_model)

        analyze.pdf_analyze()

    except RuntimeError:
        pass    