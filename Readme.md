# LLM을 이용한 메인보드 PCIe 레인 공유 안내 서비스



## Installation

### Environment
Ubuntu 24.04
python 3.12 (anaconda)
Nvidia driver 595.
Cuda Version : 12.9
Cudnn Version : 9.19

### First. 
```bash
nvcc -V
# must use more than cuda 12.9 version
```

### Second.
```bash
git clone https://github.com/dngur24/mainboard-pdf-analyze.git

cd mainboard-pdf-analyze
```

```bash
# use conda
conda create -n .vllm python=3.12 -y
 
conda activate .vllm

pip install -r requirement.txt
```



### Thrid.
check the conda environment

```bash
python3 vllm_test_gpu.py
# If run test file,  must check incresing gpu vram usage
```
---

## Demo

```bash
python3 vllm/vllm-pre-vlm.py
# use demo for b850 tomahwak max wifi manual

python3 vllm/vllm-vlm.py

```