"""
config_loader.py
----------------
config/vlm-model/*.yaml 또는 config/rag-model/*.yaml 파일을 읽어
vLLM LLM 초기화에 필요한 파라미터 딕셔너리를 반환하는 모듈.

YAML 구조 (vlm-model 예시):
    vlm-model:
      - name: Qwen/Qwen2-VL-7B-Instruct-AWQ
        type: qwen2_vl
    input:
      - model: Qwen/Qwen2-VL-7B-Instruct-AWQ
        quantization: awq_marlin
        gpu_memory_utilization: 0.90
        max_model_len: 2048
        trust_remote_code: True
        mm_processor_kwargs:        # VLM 전용 (선택)
          max_pixels: 1048576

YAML 구조 (rag-model 예시):
    rag-model:
      - name: Qwen/Qwen2.5-7B-Instruct-AWQ
        type: qwen
    input:
      - model: Qwen/Qwen2.5-7B-Instruct-AWQ
        quantization: awq_marlin
        gpu_memory_utilization: 0.85
        max_model_len: 8192
        trust_remote_code: True
"""

import os
import yaml


# input 섹션에서 허용되는 vLLM LLM() 파라미터 목록
_ALLOWED_LLM_PARAMS = {
    "model",
    "quantization",
    "gpu_memory_utilization",
    "max_model_len",
    "trust_remote_code",
    "dtype",
    "tensor_parallel_size",
    "enforce_eager",
    "mm_processor_kwargs",
}


def _load_yaml(yaml_path: str) -> dict:
    """YAML 파일을 읽어 dict 로 반환. 파일이 없으면 FileNotFoundError."""
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_input_params(raw: dict) -> dict:
    """
    YAML의 'input' 리스트 첫 번째 항목에서 vLLM LLM() 파라미터만 추출.
    알 수 없는 키는 경고 후 무시한다.
    """
    input_list = raw.get("input", [])
    if not input_list:
        raise ValueError("YAML 'input' 섹션이 비어 있거나 없습니다.")

    raw_params: dict = input_list[0]

    params = {}
    unknown_keys = []
    for key, value in raw_params.items():
        if key in _ALLOWED_LLM_PARAMS:
            params[key] = value
        else:
            unknown_keys.append(key)

    if unknown_keys:
        print(f"[config_loader] ⚠️  알 수 없는 파라미터 무시됨: {unknown_keys}")

    if "model" not in params:
        raise ValueError("YAML 'input' 섹션에 'model' 키가 반드시 있어야 합니다.")

    return params


def _resolve_yaml_path(config_dir: str, yaml_name: str) -> str:
    """
    yaml_name 이 확장자 없이 들어올 경우 .yaml 을 자동으로 붙여 경로를 반환.
    예) "Qwen2.5-7B"  ->  "config/rag-model/Qwen2.5-7B.yaml"
    예) "Qwen2.5-7B.yaml" -> 그대로 사용
    """
    if not yaml_name.endswith(".yaml"):
        yaml_name = yaml_name + ".yaml"
    return os.path.join(config_dir, yaml_name)


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def load_model_config(yaml_name: str, config_base: str) -> dict:
    """
    지정된 디렉터리의 YAML 설정을 로드하여 vLLM LLM() 파라미터 딕셔너리를 반환.

    Args:
        yaml_name: YAML 파일명 (확장자 생략 가능).
        config_base: config 디렉터리 경로. 예) "config/vlm-model" 또는 "config/rag-model"

    Returns:
        dict: vLLM LLM() 에 **kwargs 로 전달 가능한 파라미터 딕셔너리.

    Raises:
        FileNotFoundError: YAML 파일이 없을 때
        ValueError: 필수 키가 없거나 input 섹션이 비어 있을 때
    """
    yaml_path = _resolve_yaml_path(config_base, yaml_name)
    print(f"[config_loader] config 로드: {yaml_path}")
    raw = _load_yaml(yaml_path)
    params = _extract_input_params(raw)
    print(f"[config_loader] 모델 파라미터: {params}")
    return params



def list_available_configs(config_base: str) -> list[str]:
    """
    지정된 config 디렉터리에 있는 YAML 파일 목록(확장자 제거)을 반환.

    Args:
        config_base: 탐색할 config 디렉터리 경로

    Returns:
        list[str]: YAML 파일명 목록 (확장자 없음). 예) ["Qwen2.5-7B", "Qwen2-VL-7B"]
    """
    if not os.path.isdir(config_base):
        return []
    return [
        os.path.splitext(f)[0]
        for f in sorted(os.listdir(config_base))
        if f.endswith(".yaml")
    ]
