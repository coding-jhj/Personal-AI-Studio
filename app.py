from __future__ import annotations

import datetime as dt
import html
import ast
import json
import os
import re
import tempfile
import textwrap
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from PIL import Image
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import streamlit as st
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover - CLI fallback when Streamlit is unavailable.
    st = None
    components = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:  # pragma: no cover - optional LLM provider.
    ChatGoogleGenerativeAI = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional STT/LLM provider.
    OpenAI = None


warnings.filterwarnings("ignore", category=DeprecationWarning)

BASE_DIR = Path(__file__).resolve().parent
PHOTO_DIR = BASE_DIR / "photos"
PHOTO_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")


def secret_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    if st is not None:
        try:
            if name in st.secrets:
                return str(st.secrets[name])
        except Exception:
            pass
    return default


DB_NAME = secret_value("MONGO_DB_NAME", "LocalAssistantDB") or "LocalAssistantDB"
MONGO_URI = secret_value("MONGO_URI", "mongodb://localhost:27017/") or "mongodb://localhost:27017/"
DEFAULT_GEMINI_MODEL = secret_value("GEMINI_MODEL", "gemini-3.5-flash") or "gemini-3.5-flash"
DEFAULT_OPENAI_MODEL = secret_value("OPENAI_MODEL", "gpt-5.5") or "gpt-5.5"
DEFAULT_STT_MODEL = secret_value("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe") or "gpt-4o-mini-transcribe"


@dataclass
class KnowledgeDocument:
    id: str
    title: str
    source: str
    kind: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedDocument:
    doc: KnowledgeDocument
    score: float


DEMO_DATA: dict[str, list[dict[str, Any]]] = {
    "trips": [
        {
            "_seed_id": "project_ai_coding_lab",
            "destination": "AI 코딩 랩",
            "purpose": "LangChain, Gemini, MongoDB, 로컬 파일 검색을 묶은 개인 RAG 비서 프로토타입 개발",
            "start_date": "2026-05-10",
            "end_date": "2026-05-12",
            "status": "완료",
            "people": ["백엔드 개발자", "AI 엔지니어", "프롬프트 설계자"],
            "highlights": [
                "질문 의도를 분석해 적절한 지식 소스로 라우팅",
                "LLM 호출 실패 시 로컬 RAG 요약으로 자연스럽게 fallback",
                "발표용으로 출처, 근거, 다음 액션이 한 화면에 남는 구조 설계",
            ],
            "next_action": "실제 질문 10개 이상으로 검색 품질과 답변 톤을 비교",
        },
        {
            "_seed_id": "project_prompt_studio",
            "destination": "프롬프트 스튜디오",
            "purpose": "AI 답변 톤, 출력 형식, 시스템 프롬프트 커스텀",
            "start_date": "2026-05-20",
            "end_date": "2026-05-21",
            "status": "완료",
            "people": ["프롬프트 엔지니어", "서비스 기획자", "테스트 사용자"],
            "highlights": [
                "핵심 요약, 근거, 실행 제안, 다음 질문으로 답변 골격 고정",
                "없는 내용을 지어내지 않도록 근거 기반 응답 규칙 강화",
                "콘솔과 웹 UI 양쪽에서 읽히는 문장 밀도 조정",
            ],
            "next_action": "자주 쓰는 질문 템플릿을 추가하고 답변 품질 비교",
        },
        {
            "_seed_id": "project_voice_rag",
            "destination": "보이스 RAG 테스트룸",
            "purpose": "음성 질문을 텍스트로 바꾸고 로컬 지식 검색과 LLM 답변으로 연결",
            "start_date": "2026-05-27",
            "end_date": "2026-05-27",
            "status": "진행중",
            "people": ["개발자", "데모 발표자", "QA 담당자"],
            "highlights": [
                "OpenAI Whisper API 업로드형 STT 지원",
                "브라우저 Web Speech API를 이용한 빠른 받아쓰기 보조 패널 제공",
                "음성으로 만든 질문을 RAG 검색과 바로 연결하는 데모 플로우 구성",
            ],
            "next_action": "실제 마이크 녹음 파일로 한국어 인식 품질 확인",
        },
        {
            "_seed_id": "project_vision_ai",
            "destination": "비전 AI 테스트룸",
            "purpose": "이미지 메타데이터 자동 스캔 및 사진 검색 기능 개선",
            "start_date": "2026-06-02",
            "end_date": "2026-06-04",
            "status": "예정",
            "people": ["컴퓨터비전 개발자", "데이터 라벨러", "QA 담당자"],
            "highlights": [
                "photos 폴더의 실제 이미지 파일을 자동으로 DB와 RAG 지식에 반영",
                "파일 경로, 크기, 확장자, 태그를 함께 보여주는 답변 구성",
                "이미지 갤러리에서 발표 자료처럼 바로 확인 가능",
            ],
            "next_action": "테스트 이미지를 넣고 검색 결과가 자연스럽게 나오는지 확인",
        },
    ],
    "expenses": [
        {
            "_seed_id": "expense_ai_credit",
            "item": "AI API 테스트 크레딧",
            "amount": 30000,
            "category": "AI 사용료",
            "date": "2026-05-10",
            "payment": "법인카드",
            "linked_trip": "AI 코딩 랩",
            "memo": "Gemini 모델 호출 및 RAG 답변 테스트",
        },
        {
            "_seed_id": "expense_prompt_material",
            "item": "프롬프트 테스트 자료 정리",
            "amount": 12000,
            "category": "자료비",
            "date": "2026-05-11",
            "payment": "개인카드",
            "linked_trip": "프롬프트 스튜디오",
            "memo": "답변 톤과 출력 포맷 비교용 시나리오 작성",
        },
        {
            "_seed_id": "expense_camera",
            "item": "코딩용 웹캠",
            "amount": 85000,
            "category": "개발장비",
            "date": "2026-05-25",
            "payment": "법인카드",
            "linked_trip": "보이스 RAG 테스트룸",
            "memo": "음성 입력과 화면 공유 데모 테스트용",
        },
        {
            "_seed_id": "expense_flowchart",
            "item": "RAG 데모 플로우차트 제작",
            "amount": 17000,
            "category": "문서화",
            "date": "2026-05-27",
            "payment": "개인카드",
            "linked_trip": "AI 코딩 랩",
            "memo": "질문 라우팅, DB 검색, 답변 생성 흐름 정리",
        },
    ],
    "photos": [
        {
            "_seed_id": "photo_rag_dashboard",
            "file_name": "rag_dashboard_mockup.jpg",
            "file_path": "photos/rag_dashboard_mockup.jpg",
            "description": "RAG 개인 비서 콘솔 화면과 MongoDB 조회 흐름을 정리한 목업",
            "date": "2026-05-11",
            "location": "AI 코딩 랩",
            "tags": ["rag", "mongodb", "gemini", "dashboard"],
            "linked_trip": "AI 코딩 랩",
            "status": "샘플 메타데이터",
            "visual_note": "질문 입력, 라우팅 결과, 최종 답변이 한 화면에 보이는 데모 이미지",
        },
        {
            "_seed_id": "photo_voice_rag",
            "file_name": "voice_rag_flow.png",
            "file_path": "photos/voice_rag_flow.png",
            "description": "STT 입력이 RAG 검색과 LLM 답변으로 이어지는 흐름도",
            "date": "2026-05-27",
            "location": "보이스 RAG 테스트룸",
            "tags": ["stt", "rag", "llm", "demo"],
            "linked_trip": "보이스 RAG 테스트룸",
            "status": "샘플 메타데이터",
            "visual_note": "마이크, 텍스트 변환, 검색 근거, 최종 답변 단계가 연결된 구성",
        },
    ],
    "notes": [
        {
            "_seed_id": "note_assistant_idea",
            "topic": "AI 코딩 비서 개선 아이디어",
            "date": "2026-05-27",
            "content": "질문 라우팅 결과, 조회 데이터 수, 최종 답변을 분리해서 보여주면 디버깅과 발표가 모두 쉬워진다.",
            "tags": ["rag", "coding", "assistant"],
        },
        {
            "_seed_id": "note_voice_checklist",
            "topic": "STT 데모 체크리스트",
            "date": "2026-05-27",
            "content": "녹음 파일 업로드, 브라우저 받아쓰기, 직접 입력을 같은 질문창으로 모으면 발표 흐름이 자연스럽다.",
            "tags": ["stt", "voice", "demo"],
        },
        {
            "_seed_id": "note_safety",
            "topic": "RAG 답변 안전 규칙",
            "date": "2026-05-27",
            "content": "근거가 없으면 모른다고 말하고, 답변에는 어떤 파일이나 DB 기록을 참고했는지 남긴다.",
            "tags": ["rag", "grounding", "quality"],
        },
    ],
    "showcase": [
        {
            "_seed_id": "showcase_identity",
            "title": "나만의 AI 워크스페이스 컨셉",
            "summary": "로컬 자료, MongoDB, 엑셀, 사진, 음성 질문을 한 곳에서 다루는 개인 AI 작업실",
            "stack": ["Streamlit", "MongoDB", "Gemini", "OpenAI Whisper", "scikit-learn TF-IDF RAG"],
            "demo_script": [
                "1분 안에 지식 소스 현황을 보여준다.",
                "음성으로 질문을 만들고 RAG 검색 근거를 확인한다.",
                "LLM 답변과 로컬 fallback 답변의 차이를 비교한다.",
            ],
        },
        {
            "_seed_id": "showcase_quality_bar",
            "title": "감탄 포인트",
            "summary": "예쁜 화면보다 중요한 것은 죽지 않는 데모, 출처가 남는 답변, 내가 가진 파일을 바로 이해하는 흐름이다.",
            "principles": [
                "MongoDB가 꺼져도 앱은 로컬 seed와 파일 스캔으로 계속 동작",
                "RAG 검색 점수와 출처를 숨기지 않고 보여줌",
                "API 키가 없거나 LLM이 실패하면 로컬 요약으로 대체",
            ],
        },
    ],
}


def now_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(amount: Any) -> str:
    try:
        return f"{int(amount):,}원"
    except Exception:
        return str(amount)


def compact_text(value: Any, limit: int = 1400) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def readable_text(value: Any, limit: int = 1800) -> str:
    text = str(value).replace("\\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalize_llm_text(content: Any) -> str:
    """LangChain providers may return text blocks; render only human text."""
    if content is None:
        return ""
    if hasattr(content, "content"):
        return normalize_llm_text(getattr(content, "content"))
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in {"text", "output_text"} and item.get("text"):
                    parts.append(str(item["text"]))
                elif item.get("content"):
                    parts.append(normalize_llm_text(item["content"]))
            else:
                parts.append(normalize_llm_text(item))
        return clean_answer_text("\n\n".join(part for part in parts if part.strip()))
    if isinstance(content, dict):
        if content.get("text"):
            return clean_answer_text(content["text"])
        if content.get("content"):
            return clean_answer_text(normalize_llm_text(content["content"]))
        return clean_answer_text(json.dumps(content, ensure_ascii=False))

    text = str(content).strip()
    if text.startswith("[{") or text.startswith("{'type':") or text.startswith('{"type":'):
        try:
            return normalize_llm_text(ast.literal_eval(text))
        except Exception:
            pass
    return clean_answer_text(text)


def clean_answer_text(text: Any) -> str:
    cleaned = str(text).strip()
    cleaned = cleaned.replace("\\n", "\n").replace("\\t", " ")
    cleaned = re.sub(r"^```(?:markdown|md|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.replace("**근거**", "### 🔎 근거")
    return cleaned.strip()


FIELD_LABELS = {
    "destination": "프로젝트",
    "purpose": "목적",
    "start_date": "시작",
    "end_date": "종료",
    "status": "상태",
    "people": "참여",
    "highlights": "핵심",
    "next_action": "다음 액션",
    "item": "항목",
    "amount": "금액",
    "category": "분류",
    "date": "날짜",
    "payment": "결제",
    "linked_trip": "연결 작업",
    "memo": "메모",
    "file_name": "파일",
    "file_path": "경로",
    "description": "설명",
    "location": "위치",
    "tags": "태그",
    "visual_note": "시각 메모",
    "topic": "주제",
    "content": "내용",
    "title": "제목",
    "summary": "요약",
    "stack": "스택",
    "demo_script": "데모 흐름",
    "principles": "원칙",
}


IMPORTANT_FIELDS = [
    "purpose",
    "summary",
    "content",
    "description",
    "highlights",
    "next_action",
    "date",
    "status",
    "amount",
    "category",
    "file_path",
    "location",
    "tags",
    "visual_note",
]


def parse_doc_fields(content: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key = ""
    for raw_line in str(content).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z가-힣_][\w가-힣 ]{0,32}):\s*(.*)$", line)
        if match:
            current_key = match.group(1).strip()
            fields[current_key] = match.group(2).strip()
        elif current_key:
            fields[current_key] = f"{fields[current_key]} {line}".strip()
    return fields


def source_summary_lines(doc: KnowledgeDocument, max_fields: int = 5) -> list[tuple[str, str]]:
    fields = parse_doc_fields(doc.content)
    lines: list[tuple[str, str]] = []
    for key in IMPORTANT_FIELDS:
        value = fields.get(key)
        if not value or value in {"None", "nan"}:
            continue
        label = FIELD_LABELS.get(key, key)
        lines.append((label, readable_text(value, 260)))
        if len(lines) >= max_fields:
            break

    if not lines:
        lines.append(("요약", readable_text(doc.content, 360)))
    return lines


def format_source_for_prompt(item: RetrievedDocument, idx: int) -> str:
    doc = item.doc
    lines = [
        f"[S{idx}] {doc.title}",
        f"출처: {doc.source}",
        f"유형: {doc.kind}",
        f"점수: {item.score:.3f}",
    ]
    for label, value in source_summary_lines(doc, max_fields=8):
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def mask_status(name: str) -> str:
    return "설정됨" if secret_value(name) else "없음"


def to_plain(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if value.__class__.__name__ == "ObjectId":
        return str(value)
    return value


def record_to_text(record: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in record.items():
        if str(key).startswith("_"):
            continue
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            value = json.dumps(to_plain(value), ensure_ascii=False)
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def get_mongo_client() -> tuple[MongoClient | None, dict[str, Any]]:
    info = {"connected": False, "message": "MongoDB 미연결", "uri": MONGO_URI, "db": DB_NAME}
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1200)
        client.admin.command("ping")
        info.update({"connected": True, "message": "MongoDB 연결됨"})
        return client, info
    except (ServerSelectionTimeoutError, PyMongoError, OSError) as exc:
        info["message"] = f"MongoDB fallback 사용: {exc.__class__.__name__}"
        return None, info


def init_mongo_indexes(db: Any) -> None:
    for collection_name in DEMO_DATA:
        db[collection_name].create_index([("_seed_id", ASCENDING)], unique=True, sparse=True)
    db["trips"].create_index([("destination", ASCENDING), ("start_date", ASCENDING)])
    db["expenses"].create_index([("date", ASCENDING), ("category", ASCENDING)])
    db["photos"].create_index([("date", ASCENDING), ("tags", ASCENDING)])
    db["notes"].create_index([("date", ASCENDING), ("topic", ASCENDING)])


def seed_demo_data(db: Any) -> None:
    init_mongo_indexes(db)
    for collection_name, records in DEMO_DATA.items():
        collection = db[collection_name]
        for record in records:
            collection.update_one(
                {"_seed_id": record["_seed_id"]},
                {"$set": to_plain(record)},
                upsert=True,
            )


def build_seed_documents() -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    for collection_name, records in DEMO_DATA.items():
        for idx, record in enumerate(records, start=1):
            title = (
                record.get("destination")
                or record.get("topic")
                or record.get("title")
                or record.get("item")
                or record.get("file_name")
                or f"{collection_name} {idx}"
            )
            docs.append(
                KnowledgeDocument(
                    id=f"seed:{collection_name}:{idx}",
                    title=str(title),
                    source=f"seed/{collection_name}",
                    kind=f"demo-{collection_name}",
                    content=record_to_text(record),
                    metadata={"collection": collection_name, "fallback": True},
                )
            )
    return docs


def build_mongo_documents(client: MongoClient | None) -> list[KnowledgeDocument]:
    if client is None:
        return build_seed_documents()

    db = client[DB_NAME]
    seed_demo_data(db)
    docs: list[KnowledgeDocument] = []
    for collection_name in DEMO_DATA:
        try:
            rows = list(db[collection_name].find({}, {"_id": 0}).limit(250))
        except PyMongoError:
            rows = []
        for idx, record in enumerate(rows, start=1):
            plain = to_plain(record)
            title = (
                plain.get("destination")
                or plain.get("topic")
                or plain.get("title")
                or plain.get("item")
                or plain.get("file_name")
                or f"{collection_name} {idx}"
            )
            docs.append(
                KnowledgeDocument(
                    id=f"mongo:{collection_name}:{idx}",
                    title=str(title),
                    source=f"MongoDB/{collection_name}",
                    kind="mongodb",
                    content=record_to_text(plain),
                    metadata={"collection": collection_name},
                )
            )
    return docs or build_seed_documents()


def safe_read_text(path: Path, limit: int = 12000) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=encoding, errors="ignore")[:limit]
        except Exception:
            continue
    return ""


def extract_notebook_text(path: Path, limit: int = 12000) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return ""

    chunks: list[str] = []
    for cell in payload.get("cells", []):
        cell_type = cell.get("cell_type", "")
        if cell_type not in {"markdown", "code"}:
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        if source:
            chunks.append(f"[{cell_type}]\n{source}")
        if sum(len(chunk) for chunk in chunks) > limit:
            break
    return "\n\n".join(chunks)[:limit]


def scan_workspace_files() -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    blocked_parts = {".git", "__pycache__", ".claude", ".streamlit"}
    allowed_suffixes = {".md", ".py", ".ipynb", ".txt"}

    for path in sorted(BASE_DIR.rglob("*")):
        if len(docs) >= 80:
            break
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if path.name == Path(__file__).name:
            continue
        if any(part in blocked_parts for part in path.parts):
            continue

        if path.suffix.lower() == ".ipynb":
            content = extract_notebook_text(path)
        else:
            content = safe_read_text(path)
        if not content.strip():
            continue

        rel = path.relative_to(BASE_DIR).as_posix()
        docs.append(
            KnowledgeDocument(
                id=f"file:{rel}",
                title=rel,
                source=rel,
                kind=path.suffix.lower().replace(".", "") or "file",
                content=compact_text(content, 9000),
                metadata={"path": rel, "size": path.stat().st_size},
            )
        )
    return docs


def summarize_dataframe(df: pd.DataFrame) -> str:
    columns = ", ".join(str(col) for col in df.columns)
    sample = df.head(8).fillna("").astype(str).to_string(index=False)
    lines = [
        f"행 수(로드 기준): {len(df)}",
        f"열: {columns}",
        "",
        "샘플 행:",
        sample,
    ]
    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        lines.extend(["", "숫자 열 요약:", numeric.describe().round(2).to_string()])
    return "\n".join(lines)


def scan_excel_files() -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    for path in sorted(BASE_DIR.glob("*.xlsx")):
        try:
            workbook = pd.ExcelFile(path)
        except Exception as exc:
            docs.append(
                KnowledgeDocument(
                    id=f"excel-error:{path.name}",
                    title=f"{path.name} 읽기 오류",
                    source=path.name,
                    kind="excel",
                    content=f"엑셀 파일을 읽지 못했습니다: {exc}",
                    metadata={"path": path.name},
                )
            )
            continue

        for sheet_name in workbook.sheet_names[:4]:
            try:
                df = pd.read_excel(path, sheet_name=sheet_name, nrows=300)
                content = summarize_dataframe(df)
            except Exception as exc:
                content = f"시트 읽기 오류: {exc}"
            docs.append(
                KnowledgeDocument(
                    id=f"excel:{path.name}:{sheet_name}",
                    title=f"{path.name} / {sheet_name}",
                    source=path.name,
                    kind="excel",
                    content=content,
                    metadata={"path": path.name, "sheet": sheet_name},
                )
            )
    return docs


def read_image_brief(file_path: Path) -> str:
    try:
        with Image.open(file_path) as image:
            return f"{image.format} / {image.width}x{image.height}px / {image.mode}"
    except Exception as exc:
        return f"이미지 메타데이터 확인 실패: {exc}"


def scan_photo_files() -> list[KnowledgeDocument]:
    docs: list[KnowledgeDocument] = []
    supported = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    for path in sorted(PHOTO_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        rel = path.relative_to(BASE_DIR).as_posix()
        brief = read_image_brief(path)
        docs.append(
            KnowledgeDocument(
                id=f"photo:{rel}",
                title=path.name,
                source=rel,
                kind="photo",
                content=(
                    f"file_name: {path.name}\n"
                    f"file_path: {rel}\n"
                    f"date: {dt.datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d')}\n"
                    f"status: 실제 파일 확인됨\n"
                    f"visual_note: {brief}\n"
                    f"tags: local, uploaded, {path.suffix.lower().replace('.', '')}"
                ),
                metadata={"path": rel, "visual_note": brief},
            )
        )
    return docs


def manual_profile_documents() -> list[KnowledgeDocument]:
    content = """
나만의 AI 스튜디오는 개인 자료를 바로 이해하는 로컬 중심 AI 작업실이다.
핵심 흐름은 STT 음성 입력, RAG 지식 검색, LLM 답변 생성, 출처 확인, 다음 액션 정리다.
좋은 데모의 기준은 화면이 예쁜 것만이 아니라 API 키가 없거나 DB가 꺼져도 멈추지 않는 안정성,
검색 근거를 보여주는 투명성, 파일을 추가하면 지식 베이스가 확장되는 확장성이다.
추천 발표 순서는 전체 현황 질문, 음성 질문, 엑셀 데이터 질문, 사진/이미지 질문, 개선 아이디어 질문이다.
"""
    return [
        KnowledgeDocument(
            id="profile:personal-ai-studio",
            title="Personal AI Studio 운영 원칙",
            source="built-in/profile",
            kind="profile",
            content=compact_text(content, 4000),
            metadata={"owner": "local-user"},
        )
    ]


def load_knowledge_snapshot(
    include_mongo: bool = True,
    include_files: bool = True,
    include_excel: bool = True,
    include_photos: bool = True,
) -> tuple[list[KnowledgeDocument], dict[str, Any]]:
    client, mongo_info = get_mongo_client()
    docs = manual_profile_documents()
    if include_mongo:
        docs.extend(build_mongo_documents(client))
    if include_files:
        docs.extend(scan_workspace_files())
    if include_excel:
        docs.extend(scan_excel_files())
    if include_photos:
        docs.extend(scan_photo_files())
    return docs, mongo_info


def tokenize_query(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", text)]


def retrieve_documents(question: str, docs: list[KnowledgeDocument], top_k: int = 6) -> list[RetrievedDocument]:
    if not question.strip() or not docs:
        return []

    corpus = [
        f"{doc.title}\n{doc.kind}\n{doc.source}\n{doc.content}\n"
        + " ".join(str(value) for value in doc.metadata.values())
        for doc in docs
    ]

    try:
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        matrix = vectorizer.fit_transform(corpus)
        query_vector = vectorizer.transform([question])
        scores = cosine_similarity(query_vector, matrix).ravel()
    except ValueError:
        scores = [0.0 for _ in docs]

    query_tokens = tokenize_query(question)
    ranked: list[RetrievedDocument] = []
    for index, doc in enumerate(docs):
        haystack = f"{doc.title} {doc.source} {doc.kind} {doc.content}".lower()
        keyword_bonus = sum(0.025 for token in query_tokens if token in haystack)
        score = float(scores[index]) + keyword_bonus
        ranked.append(RetrievedDocument(doc=doc, score=score))

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: max(1, top_k)]


def format_context(retrieved: list[RetrievedDocument]) -> str:
    return "\n\n".join(format_source_for_prompt(item, idx) for idx, item in enumerate(retrieved, start=1))


def build_answer_prompt(question: str, retrieved: list[RetrievedDocument], answer_style: str) -> str:
    style_rule = {
        "짧고 선명하게": "핵심만 5~8문장으로 답한다.",
        "풍부하게": "핵심 요약, 근거, 실행 제안, 다음 질문까지 충분히 답한다.",
        "발표용 리포트": "발표자가 그대로 읽을 수 있게 섹션형 리포트로 답한다.",
    }.get(answer_style, "핵심 요약과 근거를 균형 있게 답한다.")

    return f"""
너는 사용자의 로컬 자료, MongoDB 기록, 엑셀 요약, 사진 메타데이터를 근거로 답하는 개인 AI 오케스트레이터다.
반드시 검색된 근거 안에서만 답하고, 추측이 필요한 부분은 "현재 지식 베이스 기준"이라고 범위를 밝혀라.
출처를 언급할 때는 [S1], [S2]처럼 근거 번호를 붙여라.

응답 규칙:
- 절대 JSON, Python dict, 배열, escaped newline(\\n)을 출력하지 않는다.
- Markdown만 사용한다. 코드블록도 쓰지 않는다.
- 아래 형식을 반드시 지킨다.

### ✨ 한 줄 요약
질문에 대한 결론을 2~3문장으로 먼저 말한다.

### 🔎 근거
- [S1] 근거 제목: 이 근거가 답변에 필요한 이유를 짧게 설명한다.
- [S2] 근거 제목: 필요한 경우 이어서 설명한다.

### 🛠 실행 제안
1. 바로 할 일
2. 확인할 일
3. 더 좋아지게 만들 일

### 💬 다음 질문
- 사용자가 이어서 물어보면 좋은 질문 2개

- 한국어로 자연스럽고 발표 자료처럼 읽히게 답한다.
- 파일 경로, 금액, 날짜가 있으면 정확히 유지한다.
- {style_rule}

현재 시각: {now_text()}
사용자 질문:
{question}

검색된 근거:
{format_context(retrieved)}
""".strip()


def generate_with_gemini(prompt: str, temperature: float, model: str) -> tuple[str | None, str | None]:
    api_key = secret_value("GOOGLE_API_KEY") or secret_value("GEMINI_API_KEY")
    if not api_key:
        return None, "GOOGLE_API_KEY 또는 GEMINI_API_KEY가 없습니다."
    if ChatGoogleGenerativeAI is None:
        return None, "langchain_google_genai를 불러오지 못했습니다."

    try:
        llm = ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            temperature=temperature,
        )
        response = llm.invoke(prompt)
        return normalize_llm_text(response), None
    except Exception as exc:
        return None, f"Gemini 호출 실패: {exc}"


def generate_with_openai(prompt: str, temperature: float, model: str) -> tuple[str | None, str | None]:
    openai_key = secret_value("OPENAI_API_KEY")
    if not openai_key:
        return None, "OPENAI_API_KEY가 없습니다."
    if OpenAI is None:
        return None, "openai 패키지를 불러오지 못했습니다."

    try:
        client = OpenAI(api_key=openai_key)
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": "You are a grounded Korean personal AI assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            return normalize_llm_text(getattr(response, "output_text", response)), None

        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": "You are a grounded Korean personal AI assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return normalize_llm_text(response.choices[0].message.content or ""), None
    except Exception as exc:
        return None, f"OpenAI 호출 실패: {exc}"


def build_local_answer(question: str, retrieved: list[RetrievedDocument], answer_style: str) -> str:
    if not retrieved:
        return (
            "### ✨ 한 줄 요약\n"
            "현재 지식 베이스 기준으로는 질문과 직접 연결되는 근거를 찾지 못했습니다.\n\n"
            "### 🛠 실행 제안\n"
            "1. 질문에 포함된 핵심 단어를 더 구체적으로 적어 주세요.\n"
            "2. `C:\\RAG` 폴더에 관련 문서, 엑셀, 이미지 파일을 추가해 주세요.\n"
            "3. MongoDB에 직접 기록을 넣으면 검색 근거가 더 풍부해집니다."
        )

    lines = [
        "### ✨ 한 줄 요약",
        "현재 지식 베이스 기준으로 답하면, 질문과 가장 가까운 자료는 아래 근거들입니다. LLM 호출이 실패하거나 API 키가 없어도 로컬 RAG가 출처를 기반으로 답변을 유지합니다.",
        "",
        "### 🔎 근거",
    ]
    for idx, item in enumerate(retrieved, start=1):
        summary = " / ".join(f"{label}: {value}" for label, value in source_summary_lines(item.doc, max_fields=3))
        lines.append(f"- [S{idx}] **{item.doc.title}** `{item.doc.source}`  \n  {summary}")

    if answer_style == "짧고 선명하게":
        lines.extend(
            [
                "",
                "### 🛠 실행 제안",
                "1. 점수가 높은 근거부터 확인하세요.",
                "2. LLM API 키를 설정하면 같은 근거를 바탕으로 더 자연스러운 문장으로 재구성됩니다.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "### 🛠 실행 제안",
                "1. 관련 파일이나 MongoDB 기록을 더 추가하면 RAG 답변 밀도가 올라갑니다.",
                "2. 발표용으로는 상위 근거 3개를 열어 출처를 보여준 뒤 답변을 생성하면 설득력이 좋습니다.",
                "3. 음성 질문은 STT로 텍스트화한 뒤 같은 질문창에 넣으면 동일한 RAG 흐름을 탑니다.",
                "",
                "### 💬 다음 질문",
                "- `이 프로젝트를 발표용으로 1분 스크립트로 정리해줘`",
                "- `내 자료 기준으로 다음에 보강할 기능을 우선순위로 뽑아줘`",
            ]
        )
    return "\n\n".join(lines)


def answer_question(
    question: str,
    docs: list[KnowledgeDocument],
    provider: str,
    answer_style: str,
    top_k: int,
    temperature: float,
    gemini_model: str,
    openai_model: str,
) -> dict[str, Any]:
    retrieved = retrieve_documents(question, docs, top_k=top_k)
    prompt = build_answer_prompt(question, retrieved, answer_style)
    errors: list[str] = []
    answer: str | None = None
    used_provider = provider

    if provider == "Gemini":
        answer, error = generate_with_gemini(prompt, temperature, gemini_model)
        if error:
            errors.append(error)
    elif provider == "OpenAI":
        answer, error = generate_with_openai(prompt, temperature, openai_model)
        if error:
            errors.append(error)
    elif provider == "자동 선택":
        answer, error = generate_with_gemini(prompt, temperature, gemini_model)
        used_provider = "Gemini"
        if error:
            errors.append(error)
            answer, error = generate_with_openai(prompt, temperature, openai_model)
            used_provider = "OpenAI"
            if error:
                errors.append(error)

    if not answer:
        used_provider = "Local RAG fallback"
        answer = build_local_answer(question, retrieved, answer_style)
    answer = clean_answer_text(answer)

    return {
        "question": question,
        "answer": answer,
        "retrieved": retrieved,
        "provider": used_provider,
        "errors": errors,
        "created_at": now_text(),
    }


def transcribe_audio(uploaded_file: Any) -> tuple[str | None, str | None]:
    if OpenAI is None:
        return None, "openai 패키지를 불러오지 못했습니다."
    openai_key = secret_value("OPENAI_API_KEY")
    if not openai_key:
        return None, "OPENAI_API_KEY가 없어서 Whisper STT를 호출할 수 없습니다."
    if uploaded_file is None:
        return None, "음성 파일을 먼저 업로드해 주세요."

    suffix = Path(uploaded_file.name).suffix or ".wav"
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            temp_path = tmp.name

        client = OpenAI(api_key=openai_key)
        with open(temp_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model=DEFAULT_STT_MODEL,
                file=audio_file,
                language="ko",
            )
        return getattr(result, "text", str(result)), None
    except Exception as exc:
        return None, f"STT 변환 실패: {exc}"
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def is_streamlit_runtime() -> bool:
    if st is None:
        return False
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #18211f;
            --muted: #60706a;
            --line: rgba(24, 33, 31, .13);
            --paper: rgba(255, 255, 255, .82);
            --teal: #0f8b8d;
            --coral: #d95d39;
            --gold: #c89b3c;
            --green: #3a7d44;
        }
        .stApp {
            background:
                linear-gradient(135deg, rgba(15,139,141,.10), transparent 32%),
                linear-gradient(220deg, rgba(217,93,57,.10), transparent 30%),
                #f7f4ef;
            color: var(--ink);
        }
        .stApp, .stApp p, .stApp label, .stApp span, .stApp div {
            color: var(--ink);
        }
        .main .block-container {
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }
        .app-header {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--paper);
            padding: 1.15rem 1.25rem;
            box-shadow: 0 18px 50px rgba(24, 33, 31, .08);
            margin-bottom: 1rem;
        }
        .app-header h1 {
            font-size: 2rem;
            line-height: 1.15;
            margin: 0 0 .35rem 0;
            letter-spacing: 0;
        }
        .app-header p {
            color: var(--muted);
            margin: 0;
            font-size: .98rem;
        }
        .status-row {
            display: flex;
            gap: .45rem;
            flex-wrap: wrap;
            margin-top: .8rem;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: .28rem .62rem;
            background: rgba(255,255,255,.72);
            color: #25302d;
            font-size: .82rem;
            white-space: nowrap;
        }
        .panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255,255,255,.78);
            padding: 1rem;
        }
        .answer-title {
            display: flex;
            align-items: center;
            gap: .55rem;
            margin: 1.15rem 0 .55rem;
        }
        .answer-title h3 {
            margin: 0;
            font-size: 1.35rem;
            letter-spacing: 0;
        }
        .answer-dot {
            width: .72rem;
            height: .72rem;
            border-radius: 999px;
            background: var(--coral);
            box-shadow: 0 0 0 5px rgba(217, 93, 57, .13);
        }
        .answer-wrap {
            border: 1px solid rgba(24, 33, 31, .12);
            border-radius: 8px;
            background: rgba(255,255,255,.86);
            padding: 1.05rem 1.15rem;
        }
        .answer-wrap h3 {
            font-size: 1.08rem;
            margin: 1rem 0 .45rem;
            letter-spacing: 0;
        }
        .answer-wrap h3:first-child {
            margin-top: 0;
        }
        .answer-wrap p, .answer-wrap li {
            line-height: 1.72;
            font-size: .98rem;
        }
        .source-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255,255,255,.76);
            padding: .92rem .98rem;
            margin-bottom: .8rem;
        }
        .source-card b {
            color: var(--ink);
        }
        .source-meta {
            color: var(--muted);
            font-size: .82rem;
            margin: .15rem 0 .45rem 0;
        }
        .source-row {
            border-top: 1px solid rgba(24,33,31,.08);
            display: grid;
            grid-template-columns: 4.8rem 1fr;
            gap: .65rem;
            padding: .48rem 0;
        }
        .source-row:first-of-type {
            border-top: 0;
        }
        .source-label {
            color: var(--muted);
            font-size: .78rem;
            font-weight: 800;
        }
        .source-value {
            color: var(--ink);
            font-size: .88rem;
            line-height: 1.58;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }
        .source-scorebar {
            height: .34rem;
            border-radius: 999px;
            background: rgba(15,139,141,.11);
            overflow: hidden;
            margin: .45rem 0 .55rem;
        }
        .source-scorebar span {
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, var(--teal), var(--gold));
        }
        .score {
            color: var(--teal);
            font-weight: 700;
        }
        div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: rgba(255,255,255,.74);
            padding: .8rem .9rem;
        }
        div[data-testid="stMetricValue"] {
            color: var(--ink);
            font-size: 1.5rem;
        }
        .stButton > button {
            border-radius: 8px;
            border: 1px solid rgba(24, 33, 31, .18);
            background: #ffffff;
            color: var(--ink);
            font-weight: 650;
        }
        .stButton > button:hover {
            border-color: var(--coral);
            color: var(--ink);
        }
        button[data-testid="stBaseButton-primary"] {
            background: #ff4b4b;
            border-color: #ff4b4b;
            color: #ffffff;
        }
        button[data-testid="stBaseButton-primary"] p,
        button[data-testid="stBaseButton-primary"] span {
            color: #ffffff;
        }
        .stTextArea textarea {
            border-radius: 8px;
            border-color: rgba(24, 33, 31, .22);
            background: #ffffff;
            color: var(--ink);
            font-size: 1rem;
            line-height: 1.55;
        }
        div[data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-weight: 700;
        }
        div[data-testid="stMetricValue"] {
            color: var(--ink);
        }
        div[data-baseweb="tab-list"] button p {
            color: var(--muted);
            font-weight: 700;
        }
        div[data-baseweb="tab-list"] button[aria-selected="true"] p {
            color: #ff4b4b;
        }
        section[data-testid="stSidebar"] {
            background: #efe9df;
            border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p {
            color: var(--ink);
        }
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] [data-baseweb="select"] div {
            color: var(--ink);
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div,
        section[data-testid="stSidebar"] input {
            background: #ffffff;
            border-color: rgba(24, 33, 31, .18);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(doc_count: int, mongo_info: dict[str, Any], provider: str) -> None:
    mongo_label = "MongoDB 연결" if mongo_info.get("connected") else "MongoDB fallback"
    st.markdown(
        f"""
        <div class="app-header">
            <h1>Personal AI Studio</h1>
            <p>STT, LLM, RAG, MongoDB, 로컬 파일, 엑셀, 사진 메타데이터를 한 화면에서 다루는 개인 AI 작업실</p>
            <div class="status-row">
                <span class="chip">지식 {doc_count}개</span>
                <span class="chip">{html.escape(mongo_label)}</span>
                <span class="chip">LLM {html.escape(provider)}</span>
                <span class="chip">STT Whisper / Browser</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_source_cards(retrieved: list[RetrievedDocument]) -> None:
    if not retrieved:
        st.info("검색된 근거가 없습니다.")
        return
    for idx, item in enumerate(retrieved, start=1):
        doc = item.doc
        rows = "\n".join(
            f"""
            <div class="source-row">
                <div class="source-label">{html.escape(label)}</div>
                <div class="source-value">{html.escape(value)}</div>
            </div>
            """
            for label, value in source_summary_lines(doc, max_fields=5)
        )
        score_width = max(8, min(100, int(item.score * 420)))
        st.markdown(
            f"""
            <div class="source-card">
                <b>[S{idx}] {html.escape(doc.title)}</b>
                <div class="source-meta">{html.escape(doc.kind)} · {html.escape(doc.source)} ·
                <span class="score">{item.score:.3f}</span></div>
                <div class="source-scorebar"><span style="width:{score_width}%"></span></div>
                {rows}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_browser_speech_panel() -> None:
    if components is None:
        st.warning("Streamlit components를 사용할 수 없습니다.")
        return

    components.html(
        """
        <!doctype html>
        <html lang="ko">
        <head>
        <meta charset="utf-8" />
        <style>
            body {
                margin: 0;
                font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                color: #18211f;
                background: transparent;
            }
            .voice {
                border: 1px solid rgba(24,33,31,.16);
                border-radius: 8px;
                padding: 14px;
                background: rgba(255,255,255,.78);
            }
            .row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
            button {
                border: 1px solid rgba(24,33,31,.18);
                border-radius: 8px;
                padding: 9px 12px;
                background: #ffffff;
                color: #18211f;
                font-weight: 700;
                cursor: pointer;
            }
            button.primary { background: #0f8b8d; color: white; border-color: #0f8b8d; }
            button.stop { background: #d95d39; color: white; border-color: #d95d39; }
            textarea {
                width: 100%;
                min-height: 115px;
                box-sizing: border-box;
                border: 1px solid rgba(24,33,31,.18);
                border-radius: 8px;
                padding: 12px;
                line-height: 1.5;
                resize: vertical;
                font-size: 15px;
            }
            .status { color: #60706a; font-size: 13px; margin-top: 8px; }
        </style>
        </head>
        <body>
            <div class="voice">
                <div class="row">
                    <button class="primary" id="start">마이크 시작</button>
                    <button class="stop" id="stop">정지</button>
                    <button id="copy">복사</button>
                    <button id="clear">지우기</button>
                </div>
                <textarea id="result" placeholder="브라우저 음성 인식 결과가 여기에 표시됩니다. 복사 후 앱의 질문 입력창에 붙여넣으세요."></textarea>
                <div class="status" id="status">Chrome/Edge의 Web Speech API를 사용합니다.</div>
            </div>
            <script>
                const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const statusEl = document.getElementById("status");
                const resultEl = document.getElementById("result");
                let recognition = null;

                if (!Recognition) {
                    statusEl.textContent = "이 브라우저는 Web Speech API를 지원하지 않습니다. 음성 파일 업로드 STT를 사용하세요.";
                    document.getElementById("start").disabled = true;
                    document.getElementById("stop").disabled = true;
                } else {
                    recognition = new Recognition();
                    recognition.lang = "ko-KR";
                    recognition.interimResults = true;
                    recognition.continuous = true;
                    recognition.onstart = () => statusEl.textContent = "듣는 중입니다.";
                    recognition.onerror = event => statusEl.textContent = "음성 인식 오류: " + event.error;
                    recognition.onend = () => statusEl.textContent = "정지되었습니다.";
                    recognition.onresult = event => {
                        let transcript = "";
                        for (let i = 0; i < event.results.length; i++) {
                            transcript += event.results[i][0].transcript;
                        }
                        resultEl.value = transcript.trim();
                    };
                }

                document.getElementById("start").onclick = () => recognition && recognition.start();
                document.getElementById("stop").onclick = () => recognition && recognition.stop();
                document.getElementById("clear").onclick = () => resultEl.value = "";
                document.getElementById("copy").onclick = async () => {
                    await navigator.clipboard.writeText(resultEl.value);
                    statusEl.textContent = "복사되었습니다. 질문 입력창에 붙여넣으세요.";
                };
            </script>
        </body>
        </html>
        """,
        height=265,
    )


def render_sidebar() -> dict[str, Any]:
    st.sidebar.title("Control")
    provider = st.sidebar.selectbox("LLM", ["자동 선택", "Gemini", "OpenAI", "Local fallback"], index=0)
    answer_style = st.sidebar.selectbox("답변 스타일", ["풍부하게", "짧고 선명하게", "발표용 리포트"], index=0)
    top_k = st.sidebar.slider("RAG 근거 수", min_value=3, max_value=10, value=6)
    temperature = st.sidebar.slider("창의성", min_value=0.0, max_value=1.0, value=0.25, step=0.05)

    st.sidebar.divider()
    st.sidebar.caption("지식 소스")
    include_mongo = st.sidebar.checkbox("MongoDB / seed", value=True)
    include_files = st.sidebar.checkbox("로컬 문서/코드", value=True)
    include_excel = st.sidebar.checkbox("엑셀 요약", value=True)
    include_photos = st.sidebar.checkbox("사진 메타데이터", value=True)

    st.sidebar.divider()
    gemini_model = st.sidebar.text_input("Gemini model", value=DEFAULT_GEMINI_MODEL)
    openai_model = st.sidebar.text_input("OpenAI model", value=DEFAULT_OPENAI_MODEL)

    return {
        "provider": provider,
        "answer_style": answer_style,
        "top_k": top_k,
        "temperature": temperature,
        "include_mongo": include_mongo,
        "include_files": include_files,
        "include_excel": include_excel,
        "include_photos": include_photos,
        "gemini_model": gemini_model,
        "openai_model": openai_model,
    }


def render_ask_tab(docs: list[KnowledgeDocument], settings: dict[str, Any]) -> None:
    if "question_input" not in st.session_state:
        st.session_state.question_input = "내 AI 스튜디오 전체 현황을 발표용으로 정리해줘"
    if "history" not in st.session_state:
        st.session_state.history = []

    prompt_bank = [
        "내 AI 스튜디오 전체 현황을 발표용으로 정리해줘",
        "STT, LLM, RAG 기능이 어떻게 연결되는지 설명해줘",
        "엑셀 방문자 정보 파일에서 확인할 수 있는 내용을 요약해줘",
        "사진 데이터와 비전 AI 관련 자료를 찾아줘",
    ]
    cols = st.columns(4)
    for col, prompt in zip(cols, prompt_bank):
        if col.button(prompt, width="stretch"):
            st.session_state.question_input = prompt
            st.rerun()

    left, right = st.columns([0.64, 0.36], gap="large")
    with left:
        st.text_area("질문", key="question_input", height=132)
        ask = st.button("답변 생성", type="primary", width="stretch")

        if ask:
            question = st.session_state.question_input.strip()
            if not question:
                st.warning("질문을 입력해 주세요.")
            else:
                with st.spinner("RAG 검색과 LLM 답변을 생성하는 중입니다..."):
                    result = answer_question(
                        question=question,
                        docs=docs,
                        provider=settings["provider"],
                        answer_style=settings["answer_style"],
                        top_k=settings["top_k"],
                        temperature=settings["temperature"],
                        gemini_model=settings["gemini_model"],
                        openai_model=settings["openai_model"],
                    )
                st.session_state.history.insert(0, result)

        if st.session_state.history:
            result = st.session_state.history[0]
            st.markdown(
                """
                <div class="answer-title">
                    <span class="answer-dot"></span>
                    <h3>AI 답변</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.markdown(normalize_llm_text(result["answer"]))
            if result["errors"]:
                with st.expander("Fallback 로그"):
                    for error in result["errors"]:
                        st.write(error)
        else:
            st.info("질문을 입력하면 로컬 자료 검색, 출처 확인, LLM 답변 생성이 한 번에 실행됩니다.")

    with right:
        preview_question = st.session_state.question_input.strip()
        retrieved = retrieve_documents(preview_question, docs, settings["top_k"]) if preview_question else []
        st.markdown("### 실시간 RAG 근거")
        render_source_cards(retrieved)


def render_voice_tab() -> None:
    left, right = st.columns([0.52, 0.48], gap="large")
    with left:
        st.markdown("### 음성 파일 STT")
        audio = st.file_uploader(
            "음성 파일",
            type=["wav", "mp3", "m4a", "webm", "ogg", "mp4"],
            accept_multiple_files=False,
        )
        if st.button("Whisper로 텍스트 변환", type="primary", width="stretch"):
            with st.spinner("음성을 텍스트로 변환하는 중입니다..."):
                transcript, error = transcribe_audio(audio)
            if error:
                st.warning(error)
            else:
                st.session_state.question_input = transcript or ""
                st.success("질문 입력창에 변환 결과를 넣었습니다.")
                st.text_area("변환 결과", value=transcript or "", height=160)
    with right:
        st.markdown("### 브라우저 음성 입력")
        render_browser_speech_panel()


def render_knowledge_tab(docs: list[KnowledgeDocument]) -> None:
    rows = [
        {
            "title": doc.title,
            "kind": doc.kind,
            "source": doc.source,
            "length": len(doc.content),
        }
        for doc in docs
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    kinds = pd.Series([doc.kind for doc in docs]).value_counts().reset_index()
    kinds.columns = ["kind", "count"]
    st.bar_chart(kinds.set_index("kind"))


def render_gallery_tab(docs: list[KnowledgeDocument]) -> None:
    photo_docs = [doc for doc in docs if doc.kind == "photo"]
    image_paths = [PHOTO_DIR / Path(doc.metadata.get("path", "")).name for doc in photo_docs]
    image_paths = [path for path in image_paths if path.exists()]

    if not image_paths:
        st.info(f"{PHOTO_DIR} 폴더에 이미지를 넣으면 갤러리와 RAG 지식에 자동 반영됩니다.")
        render_source_cards([RetrievedDocument(doc=doc, score=1.0) for doc in photo_docs[:6]])
        return

    cols = st.columns(3)
    for index, path in enumerate(image_paths):
        with cols[index % 3]:
            st.image(str(path), caption=path.name, width="stretch")


def render_system_tab(docs: list[KnowledgeDocument], mongo_info: dict[str, Any]) -> None:
    env_rows = [
        {"항목": "GOOGLE_API_KEY / GEMINI_API_KEY", "상태": "설정됨" if (secret_value("GOOGLE_API_KEY") or secret_value("GEMINI_API_KEY")) else "없음"},
        {"항목": "OPENAI_API_KEY", "상태": mask_status("OPENAI_API_KEY")},
        {"항목": "MONGO_URI", "상태": "설정됨" if secret_value("MONGO_URI") else "기본 localhost"},
        {"항목": "MongoDB", "상태": mongo_info.get("message", "")},
    ]
    st.dataframe(pd.DataFrame(env_rows), width="stretch", hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("MongoDB 데모 데이터 보강", width="stretch"):
            client, info = get_mongo_client()
            if client is None:
                st.warning(info["message"])
            else:
                seed_demo_data(client[DB_NAME])
                st.success("MongoDB 데모 데이터를 upsert했습니다.")
    with col2:
        if st.button("세션 기록 초기화", width="stretch"):
            st.session_state.history = []
            st.success("대화 기록을 비웠습니다.")

    with st.expander("지식 베이스 원본 미리보기"):
        for doc in docs[:20]:
            st.write(f"{doc.kind} · {doc.title} · {doc.source}")


def render_app() -> None:
    st.set_page_config(
        page_title="Personal AI Studio",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    settings = render_sidebar()

    docs, mongo_info = load_knowledge_snapshot(
        include_mongo=settings["include_mongo"],
        include_files=settings["include_files"],
        include_excel=settings["include_excel"],
        include_photos=settings["include_photos"],
    )

    render_header(len(docs), mongo_info, settings["provider"])

    metric_cols = st.columns(4)
    metric_cols[0].metric("지식 문서", f"{len(docs)}")
    metric_cols[1].metric("로컬 파일", f"{sum(1 for doc in docs if doc.kind in {'md', 'py', 'ipynb', 'txt'})}")
    metric_cols[2].metric("엑셀 시트", f"{sum(1 for doc in docs if doc.kind == 'excel')}")
    metric_cols[3].metric("사진", f"{sum(1 for doc in docs if doc.kind == 'photo')}")

    ask_tab, voice_tab, knowledge_tab, gallery_tab, system_tab = st.tabs(
        ["Ask", "Voice", "Knowledge", "Gallery", "System"]
    )
    with ask_tab:
        render_ask_tab(docs, settings)
    with voice_tab:
        render_voice_tab()
    with knowledge_tab:
        render_knowledge_tab(docs)
    with gallery_tab:
        render_gallery_tab(docs)
    with system_tab:
        render_system_tab(docs, mongo_info)


def print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def pretty_print(text: str, width: int = 92) -> None:
    for raw_line in str(text).splitlines():
        line = raw_line.rstrip()
        if not line:
            print()
        else:
            print(textwrap.fill(line, width=width, subsequent_indent="    "))


def run_cli_demo() -> None:
    print_section("Personal AI Studio CLI Demo")
    print("웹 UI 실행 명령: streamlit run app.py")
    docs, mongo_info = load_knowledge_snapshot()
    print(f"지식 문서: {len(docs)}개")
    print(f"MongoDB: {mongo_info['message']}")

    scenarios = [
        "내 AI 스튜디오 전체 현황을 발표용으로 정리해줘",
        "STT, LLM, RAG 기능이 어떻게 연결되는지 설명해줘",
        "엑셀 방문자 정보 파일에서 확인할 수 있는 내용을 요약해줘",
    ]
    for scenario in scenarios:
        print_section(f"User: {scenario}")
        result = answer_question(
            question=scenario,
            docs=docs,
            provider="자동 선택",
            answer_style="풍부하게",
            top_k=5,
            temperature=0.2,
            gemini_model=DEFAULT_GEMINI_MODEL,
            openai_model=DEFAULT_OPENAI_MODEL,
        )
        print(f"Provider: {result['provider']}")
        pretty_print(result["answer"])


if __name__ == "__main__":
    if is_streamlit_runtime():
        render_app()
    else:
        run_cli_demo()
