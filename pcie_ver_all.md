# Motherboard PCIe Lane Sharing Service Project Overview

## 1. 프로젝트 개요
사용자가 AMD 메인보드 조립 시 겪는 복잡한 PCIe 레인 공유(Bandwidth Sharing) 문제를 해결하기 위한 Node.js/Express 기반 웹 서비스.

---

## 2. 초기 구현 (Backend & Frontend)
- **기술 스택:** Node.js, Express, EJS, Vanilla CSS/JS
- **핵심 기능:**
    - 메인보드 목록 조회 및 검색
    - 인터랙티브 상세 페이지: M.2 슬롯 선택 시 영향을 받는 PCIe 슬롯 시각화
- **파일 구조:**
    - `app.js`: Express 서버 및 라우팅
    - `data/motherboards.json`: 메인보드 스펙 및 공유 규칙 데이터
    - `views/details.ejs`: 동적 시각화 로직이 포함된 상세 뷰

---

## 3. 데이터 출처 및 관리
- **출처:** 제조사 공식 매뉴얼 기반 (가이드 문서 및 샘플 데이터)
- **자동화 아이디어:** Gemini API를 활용하여 제조사 매뉴얼 텍스트에서 자동으로 PCIe 레인 정보를 추출하고 JSON으로 변환하는 기능 제안.
- **분석 스크립트 (`scripts/analyze_manual.js`):** Gemini 1.5 Flash 모델을 사용하여 비정형 텍스트를 구조화된 데이터로 변환.

---

## 4. 핵심 기능 리스트
1. **인터랙티브 시뮬레이터:** 슬롯 장착 시 대역폭 변화 실시간 확인.
2. **지능형 검색:** 모델명 및 칩셋 필터링.
3. **AI 기반 데이터 업데이트:** LLM을 통한 매뉴얼 분석 자동화.
4. **상세 기술 정보:** CPU/Chipset 레인 소스 및 PCIe 버전 명시.
5. **반응형 디자인:** 조립 현장에서의 접근성 확보.

---

## 5. RESTful API 설계
프로젝트 확장 시 필요한 API 리소스 및 메서드 설계:
- `GET /api/motherboards`: 목록 조회 및 검색
- `GET /api/motherboards/:id`: 상세 정보 조회
- `POST /api/analyze/manual`: AI를 통한 매뉴얼 분석
- `POST /api/motherboards`: **[Admin]** 신규 데이터 등록

---

## 6. JSON 데이터 스키마 (v1.0)
```json
{
  "motherboard": {
    "id": "string (kebab-case)",
    "name": "string",
    "brand": "string",
    "chipset": "string",
    "slots": [
      { "id": "pci_1", "name": "PCIEX16_1", "type": "PCIe 5.0 x16", "source": "CPU" }
    ],
    "storage": [
      { "id": "m2_1", "name": "M.2_1", "type": "PCIe 5.0 x4", "source": "CPU" }
    ],
    "sharingRules": [
      {
        "trigger": "m2_3",
        "impact": "pci_2",
        "effect": "disabled/reduced",
        "newSpeed": "x8",
        "description": "설명 (한국어)"
      }
    ]
  }
}
```

---
## 7. 사용자 프롬프트 내역 (History)
1. **서비스 제안:** "나는 컴퓨터 하드웨어에 관심이 많은 학생이다... PCIe 레인 공유 내역을 보여주는 웹 서비스를 만들 수 있는가?"
2. **데이터 출처 확인:** "너가 임의로 넣은 메인보드 데이터의 출처를 밝혀라"
3. **AI 자동화 제안:** "메인보드의 설명서를 gemini같은 외부 api에서 처리한 후 pcie 관련 결과를 받아오는 것이 좋다고 판단된다."
4. **기능 정의:** "이 프로젝트에서 필요한 핵심 기능들을 나열하라"
5. **아키텍처 질의:** "restful api가 이 프로젝트에서 반드시 필요한 존재인가? 얻는 이점은 무엇인가?"
6. **API 설계:** "필요한 restful api 리소스 경로와 http 메서드 리스트를 나열하라"
7. **데이터 설계:** "주요 데이터의 필드 이름과 자료형을 포함한 json 스키마 초안을 작성하라"
8. **문서화 및 복사:** "현재까지 나눈 대화 내용을 pcie_ver_all.md로 저장하고 midterm_pcie로 복사하라"

---
*본 문서는 사용자와 Gemini CLI 간의 대화 내용을 바탕으로 자동 생성되었습니다.*
