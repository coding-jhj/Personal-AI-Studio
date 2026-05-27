---
title: Personal AI Studio
emoji: 🧠
colorFrom: green
colorTo: red
sdk: docker
app_port: 8501
app_file: app.py
pinned: false
license: mit
---

<div align="center">

# Personal AI Studio

**음성 입력, 로컬 문서, MongoDB, 엑셀, 사진 메타데이터를 하나의 RAG 워크스페이스로 연결한 개인 AI 스튜디오**

<br />

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Optional-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![RAG](https://img.shields.io/badge/RAG-TF--IDF%20Retrieval-0F8B8D?style=for-the-badge)

<br />

[공개 앱 바로가기](https://jeonghwanju-personal-ai-studio.hf.space) ·
[GitHub 저장소](https://github.com/coding-jhj/Personal-AI-Studio)

</div>

---

## 프로젝트 소개

**Personal AI Studio**는 사용자의 개인 자료를 한 곳에 모아 질문하고, 검색 근거를 확인하고, LLM 답변까지 생성하는 Streamlit 기반 AI 워크스페이스입니다.

일반적인 챗봇처럼 질문과 답변만 보여주는 것이 아니라, **어떤 파일·DB 기록·엑셀 시트·사진 메타데이터를 근거로 답했는지**를 함께 보여주도록 설계했습니다. API 키나 MongoDB 연결이 없어도 앱이 멈추지 않도록 seed 데이터와 로컬 RAG fallback을 포함한 점이 핵심입니다.

> 이 프로젝트의 목표는 “예쁜 AI 데모”가 아니라, 실제 발표와 포트폴리오에서 설명 가능한 **출처 기반 개인 AI 작업실**을 만드는 것입니다.

---

## 핵심 가치

| 가치 | 구현 방식 |
| --- | --- |
| 근거가 남는 답변 | TF-IDF 기반 로컬 검색 결과를 `[S1]`, `[S2]` 형태의 출처 카드로 표시 |
| 멈추지 않는 데모 | Gemini, OpenAI 호출 실패 시 로컬 RAG fallback 답변 생성 |
| 여러 지식 소스 통합 | MongoDB, seed 데이터, 로컬 문서, 코드, 노트북, 엑셀, 사진 메타데이터 스캔 |
| 음성 질문 지원 | OpenAI Whisper 업로드 STT와 브라우저 Web Speech API 보조 패널 제공 |
| 배포 친화성 | Hugging Face Spaces Docker SDK 기준으로 바로 배포 가능한 구조 |
| 보안 기본값 | `.env`, `.streamlit/secrets.toml`, 로컬 수업 자료, 캐시 파일을 Git에서 제외 |

---

## 전체 아키텍처

```mermaid
flowchart LR
    A[사용자 질문] --> B[Streamlit UI]
    V[음성 파일 / 브라우저 음성 입력] --> B

    B --> C[지식 스냅샷 생성]
    C --> D1[MongoDB 또는 Seed 데이터]
    C --> D2[로컬 문서 / 코드 / 노트북]
    C --> D3[Excel 요약]
    C --> D4[photos 폴더 이미지 메타데이터]

    D1 --> E[TF-IDF 검색]
    D2 --> E
    D3 --> E
    D4 --> E

    E --> F[출처 카드 표시]
    E --> G[근거 기반 Prompt 생성]

    G --> H{LLM Provider}
    H --> I[Gemini]
    H --> J[OpenAI]
    H --> K[Local RAG Fallback]

    I --> L[최종 답변]
    J --> L
    K --> L
    F --> L
```

---

## 기능 요약

### 1. Ask

질문을 입력하면 현재 선택된 지식 소스에서 관련 문서를 검색하고, 검색 근거와 AI 답변을 함께 보여줍니다.

- 프롬프트 버튼으로 데모 질문 빠르게 실행
- 질문 입력과 동시에 실시간 RAG 근거 미리보기
- 답변 스타일 선택: `풍부하게`, `짧고 선명하게`, `발표용 리포트`
- LLM 선택: `자동 선택`, `Gemini`, `OpenAI`, `Local fallback`
- fallback 로그를 expander로 확인 가능

### 2. Voice

음성 질문을 텍스트로 변환한 뒤 Ask 탭의 질문 입력창으로 연결합니다.

- 업로드 STT: `wav`, `mp3`, `m4a`, `webm`, `ogg`, `mp4`
- OpenAI transcription 모델 사용
- 브라우저 Web Speech API 기반 한국어 받아쓰기 패널 제공
- 마이크 결과 복사, 정지, 지우기 기능 포함

### 3. Knowledge

현재 앱이 읽고 있는 지식 베이스를 표와 차트로 확인합니다.

- 문서 제목, 유형, 출처, 본문 길이 표시
- 지식 유형별 개수 bar chart
- 어떤 자료가 RAG에 들어갔는지 확인 가능

### 4. Gallery

`photos/` 폴더의 이미지 파일을 갤러리와 RAG 지식에 자동 반영합니다.

- 지원 형식: `jpg`, `jpeg`, `png`, `webp`, `bmp`
- 이미지 포맷, 해상도, 모드 등 메타데이터 추출
- 실제 이미지가 없으면 seed 사진 메타데이터를 근거 카드로 표시

### 5. System

앱의 실행 환경과 연결 상태를 확인합니다.

- `GOOGLE_API_KEY` / `GEMINI_API_KEY` 설정 여부
- `OPENAI_API_KEY` 설정 여부
- `MONGO_URI` 설정 여부
- MongoDB 연결 또는 fallback 상태
- MongoDB 데모 데이터 upsert 버튼
- 세션 기록 초기화 버튼
- 지식 베이스 원본 미리보기

---

## 데이터 흐름

```mermaid
flowchart TD
    A[앱 실행] --> B[환경 변수 / Streamlit Secrets 로드]
    B --> C{MongoDB 연결 가능?}

    C -->|가능| D[MongoDB 컬렉션 조회]
    C -->|불가| E[내장 Seed 데이터 사용]

    D --> F[KnowledgeDocument 변환]
    E --> F

    F --> G[로컬 파일 스캔]
    G --> H[Excel 파일 요약]
    H --> I[사진 메타데이터 스캔]
    I --> J[통합 지식 스냅샷]

    J --> K[질문별 TF-IDF 검색]
    K --> L[상위 근거 선택]
    L --> M[LLM Prompt 구성]
    M --> N[Gemini / OpenAI / Local fallback 답변]
```

---

## 주요 구현 포인트

| 영역 | 구현 내용 |
| --- | --- |
| 데이터 모델 | `KnowledgeDocument`, `RetrievedDocument` dataclass로 지식 문서와 검색 결과 구조화 |
| MongoDB | `trips`, `expenses`, `photos`, `notes`, `showcase` 컬렉션 seed 및 index 구성 |
| 로컬 검색 | `TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))` 기반 한국어 친화 검색 |
| 검색 보정 | 질문 토큰이 문서 본문에 포함되면 keyword bonus 추가 |
| 답변 생성 | Gemini 우선, 실패 시 OpenAI, 모두 실패하면 Local RAG fallback |
| STT | OpenAI audio transcription API로 업로드 파일 변환 |
| 브라우저 음성 | Streamlit component 내부에서 Web Speech API 실행 |
| 파일 스캔 | `.md`, `.py`, `.ipynb`, `.txt` 파일을 최대 80개까지 지식화 |
| 엑셀 요약 | 시트별 행 수, 열 목록, 샘플 행, 숫자 열 통계를 자동 요약 |
| 이미지 메타데이터 | `Pillow`로 이미지 포맷, 크기, 모드 추출 |
| UI 스타일링 | Streamlit 기본 UI에 커스텀 CSS를 주입해 포트폴리오용 화면 구성 |

---

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| UI | Streamlit |
| Language | Python 3.11 |
| RAG 검색 | scikit-learn TF-IDF, cosine similarity |
| LLM | Gemini via `langchain-google-genai`, OpenAI |
| STT | OpenAI transcription API |
| Database | MongoDB, seed fallback |
| Data | pandas, openpyxl |
| Image | Pillow |
| Config | python-dotenv, Streamlit secrets |
| Deploy | Docker, Hugging Face Spaces |

---

## 화면 구성

| 탭 | 목적 | 보여주는 것 |
| --- | --- | --- |
| Ask | 질문과 답변 생성 | 질문 입력, AI 답변, 실시간 RAG 근거 카드 |
| Voice | 음성 질문 변환 | 음성 파일 STT, 브라우저 음성 입력 패널 |
| Knowledge | 지식 베이스 확인 | 문서 목록, 지식 유형별 통계 |
| Gallery | 이미지 자료 확인 | `photos/` 폴더 이미지와 메타데이터 |
| System | 운영 상태 확인 | API 키, MongoDB 상태, seed 데이터 보강, 세션 초기화 |

---

## 기본 모델 설정

코드와 예시 secrets의 기본값은 아래와 같습니다. 배포 환경에서는 Streamlit Secrets 또는 `.env`에서 원하는 모델명으로 바꿀 수 있습니다.

```env
GEMINI_MODEL=gemini-3.5-flash
OPENAI_MODEL=gpt-5.5
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

---

## 로컬 실행

```powershell
git clone https://github.com/coding-jhj/Personal-AI-Studio.git
cd Personal-AI-Studio

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 다음 주소로 접속합니다.

```text
http://localhost:8501
```

---

## 선택 환경 변수

로컬에서는 프로젝트 루트에 `.env` 파일을 만들 수 있습니다.

```env
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.5
OPENAI_STT_MODEL=gpt-4o-mini-transcribe

MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=LocalAssistantDB
```

Streamlit 배포 환경에서는 `.streamlit/secrets.example.toml`을 참고해 플랫폼 Secrets에 등록합니다.

> 실제 키가 들어간 `.env`와 `.streamlit/secrets.toml`은 절대 커밋하지 않습니다.

---

## Docker 실행

이 저장소는 Hugging Face Spaces Docker SDK 기준으로 구성되어 있습니다.

```powershell
docker build -t personal-ai-studio .
docker run --rm -p 8501:8501 personal-ai-studio
```

Dockerfile은 다음 흐름으로 동작합니다.

1. `python:3.11-slim` 이미지 사용
2. 일반 사용자 `user` 생성
3. `requirements.txt` 설치
4. 전체 앱 파일 복사
5. `streamlit run app.py`를 `0.0.0.0:8501`로 실행

---

## Hugging Face Spaces 배포

이 프로젝트는 Hugging Face Spaces의 Docker SDK로 배포할 수 있습니다.

필수 파일은 다음과 같습니다.

```text
Dockerfile
requirements.txt
README.md
app.py
.streamlit/config.toml
```

배포 시 API 키와 MongoDB URI는 Hugging Face Space의 Secrets에 등록합니다.

```toml
GOOGLE_API_KEY = "your-gemini-api-key"
OPENAI_API_KEY = "your-openai-api-key"
MONGO_URI = "mongodb+srv://user:password@cluster.example.mongodb.net/"
MONGO_DB_NAME = "LocalAssistantDB"
```

---

## 보안 설계

이 저장소는 포트폴리오 공개를 전제로, 민감 정보와 로컬 수업 자료를 커밋하지 않도록 구성했습니다.

`.gitignore`에서 제외하는 주요 항목은 다음과 같습니다.

```text
.env
.streamlit/secrets.toml
__pycache__/
.venv/
venv/
env/
.claude/
streamlit_screenshot*.png
streamlit_cdp_screenshot*.png
chatgpt.md
rag.md
q1.py
q2/
q*.ipynb
test.ipynb
*.xlsx
```

공개 저장소에는 앱 실행과 배포에 필요한 코드와 설정만 남기고, 개인 키·수업 자료·로컬 캐시·실제 엑셀 파일은 제외합니다.

---

## 프로젝트 구조

```text
Personal-AI-Studio/
├─ app.py
├─ Dockerfile
├─ requirements.txt
├─ runtime.txt
├─ README.md
├─ .gitignore
└─ .streamlit/
   ├─ config.toml
   └─ secrets.example.toml
```

---

## 포트폴리오 관점에서의 강조점

### 1. RAG를 “답변 생성”이 아니라 “근거 확인 UI”로 구현

답변만 보여주면 데모가 그럴듯해 보여도 신뢰하기 어렵습니다. 이 프로젝트는 답변 옆에 실시간 검색 근거를 카드 형태로 보여주고, 각 근거의 점수와 출처를 함께 표시합니다.

### 2. 실패해도 멈추지 않는 구조

MongoDB가 꺼져 있으면 seed 데이터를 사용하고, LLM API 키가 없거나 호출이 실패하면 로컬 RAG fallback 답변을 생성합니다. 포트폴리오 시연에서 가장 중요한 “죽지 않는 데모”를 목표로 설계했습니다.

### 3. 개인 자료를 확장 가능한 지식 베이스로 변환

문서, 코드, 노트북, 엑셀, 사진 메타데이터가 모두 같은 `KnowledgeDocument` 구조로 통합됩니다. 새로운 파일을 추가하면 앱이 지식 베이스로 읽고, 질문 검색의 근거로 활용할 수 있습니다.

### 4. 음성 입력부터 근거 기반 답변까지 한 화면에서 연결

음성 파일 업로드 STT와 브라우저 음성 입력을 모두 제공해, 음성 질문이 바로 RAG 검색과 LLM 답변으로 이어지는 흐름을 시연할 수 있습니다.

---

## 데모 시나리오

포트폴리오 발표에서는 아래 순서로 보여주면 프로젝트 의도가 가장 잘 드러납니다.

1. `System` 탭에서 API 키와 MongoDB 상태를 확인합니다.
2. `Knowledge` 탭에서 현재 지식 베이스가 어떤 자료로 구성되는지 보여줍니다.
3. `Ask` 탭에서 “내 AI 스튜디오 전체 현황을 발표용으로 정리해줘”를 실행합니다.
4. 오른쪽의 실시간 RAG 근거 카드와 왼쪽의 AI 답변을 함께 설명합니다.
5. `Voice` 탭에서 음성 질문을 텍스트로 변환한 뒤 Ask 질문창에 연결합니다.
6. API 키나 MongoDB가 없어도 Local fallback으로 답변이 유지되는 점을 강조합니다.

---

## 앞으로 개선하고 싶은 점

| 개선 방향 | 설명 |
| --- | --- |
| 벡터 DB 도입 | TF-IDF 검색 이후 FAISS, Chroma 등 임베딩 검색으로 확장 |
| 파일 업로드 UI | 사용자가 브라우저에서 직접 문서와 엑셀을 업로드해 지식 베이스에 반영 |
| 답변 평가 | 질문별 검색 근거, 사용 모델, 답변 품질을 저장해 비교 |
| 이미지 이해 | 현재는 메타데이터 중심이므로 이미지 캡션 생성 또는 비전 모델 연동 |
| 사용자별 워크스페이스 | 개인별 자료와 히스토리를 분리하는 인증/세션 구조 추가 |

---

## 라이선스

이 프로젝트는 MIT License를 따릅니다.

---

<div align="center">

**Personal AI Studio는 개인 자료를 검색 가능한 지식으로 바꾸고, 음성 질문부터 근거 기반 답변까지 연결하는 포트폴리오용 AI 워크스페이스입니다.**

</div>
