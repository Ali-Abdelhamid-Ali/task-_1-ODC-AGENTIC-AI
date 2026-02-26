import logging
import time
import json

from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
from langchain_cohere import ChatCohere
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from app.prompts.chat_sql_prompt import prompt as system_prompt
from app.schemas.chat import ChatRequest, ChatResponse, SqlAnswer, TokenUsage
from app.services.chat.parsers import (
    get_response_text,
    get_token_usage,
    parse_sql_answer,
)
from app.services.chat.sql_runner import run_sql_query

load_dotenv()
logger = logging.getLogger(__name__)

MODEL_NAME = "command-a-03-2025"

prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("user", "Question: {question}\nContext (JSON): {context_json}"),
    ]
)

llm = ChatCohere(model=MODEL_NAME, temperature=0.0)

result_summary_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a data results summarizer for a chat API. "
                "Write a concise natural-language answer grounded ONLY in the provided query result preview. "
                "Do not invent values. Do not mention SQL or technical internals. "
                "If only a preview is shown (preview_count < row_count), clearly mention that the answer is based on the preview. "
                "Answer in the same language as the user's question when possible. "
                "Return plain text only (no JSON, no markdown)."
            ),
        ),
        (
            "user",
            (
                "User question: {question}\n"
                "Total rows returned: {row_count}\n"
                "Rows in preview: {preview_count}\n"
                "rows_preview (JSON): {rows_preview_json}"
            ),
        ),
    ]
)


async def _invoke_llm(messages):
    if hasattr(llm, "ainvoke"):
        return await llm.ainvoke(messages)
    return await run_in_threadpool(llm.invoke, messages)


def _merge_token_usage(*usages: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=sum(u.prompt_tokens for u in usages),
        completion_tokens=sum(u.completion_tokens for u in usages),
        total_tokens=sum(u.total_tokens for u in usages),
    )


def _build_grounded_answer(row_count: int, rows_preview: list[dict]) -> str:
    if row_count == 0:
        return "No rows matched your question."

    if row_count == 1 and rows_preview:
        first_row = rows_preview[0]
        if len(first_row) == 1:
            col, value = next(iter(first_row.items()))
            return f"Query executed successfully. {col} = {value}."

    return f"Query executed successfully and returned {row_count} rows."


async def _summarize_rows_preview(
    question: str,
    row_count: int,
    rows_preview: list[dict],
) -> tuple[str, TokenUsage]:
    if row_count == 0:
        return _build_grounded_answer(row_count, rows_preview), TokenUsage()

    try:
        messages = result_summary_prompt_template.format_messages(
            question=question,
            row_count=row_count,
            preview_count=len(rows_preview),
            rows_preview_json=json.dumps(rows_preview, ensure_ascii=False, default=str),
        )
        llm_response = await _invoke_llm(messages)
        summary_text = get_response_text(llm_response).strip()
        if not summary_text:
            raise ValueError("Empty summary from LLM")
        return summary_text, get_token_usage(llm_response)
    except Exception:
        logger.exception("Result summarization failed")
        return _build_grounded_answer(row_count, rows_preview), TokenUsage()


async def process_chat(req: ChatRequest) -> ChatResponse:
    raw_output = ""
    token_usage = TokenUsage()
    start = time.perf_counter()

    try:
        messages = prompt_template.format_messages(
            question=req.message,
            context_json=json.dumps(req.context or {}, ensure_ascii=False),
        )
        llm_response = await _invoke_llm(messages)
        raw_output = get_response_text(llm_response)
        token_usage = get_token_usage(llm_response)
        logger.info("LLM raw output preview: %r", raw_output[:1000])

        sql_answer = SqlAnswer(**parse_sql_answer(raw_output))
        db_result = await run_in_threadpool(run_sql_query, sql_answer.sql_query)
        row_count = int(db_result.get("row_count", 0))
        rows_preview = list(db_result.get("rows", []))[:20]

        final_answer, summary_token_usage = await _summarize_rows_preview(
            question=req.message,
            row_count=row_count,
            rows_preview=rows_preview,
        )
        token_usage = _merge_token_usage(token_usage, summary_token_usage)

        return ChatResponse(
            natural_language_answer=final_answer,
            sql_query=db_result["sql"],
            token_usage=token_usage,
            latency_ms=int((time.perf_counter() - start) * 1000),
            provider="cohere",
            model=MODEL_NAME,
            status="ok",
            row_count=row_count,
            rows_preview=rows_preview,
        )

    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.exception("Chat processing failed (parse/validation/sql)")
        return ChatResponse(
            natural_language_answer=f"Failed to parse/validate/execute SQL: {exc}",
            sql_query="",
            token_usage=token_usage,
            latency_ms=int((time.perf_counter() - start) * 1000),
            provider="cohere",
            model=MODEL_NAME,
            status="error",
            row_count=0,
            rows_preview=[],
        )

    except Exception:
        logger.exception("Chat processing failed")
        return ChatResponse(
            natural_language_answer="Unexpected error while generating or executing SQL.",
            sql_query="",
            token_usage=token_usage,
            latency_ms=int((time.perf_counter() - start) * 1000),
            provider="cohere",
            model=MODEL_NAME,
            status="error",
            row_count=0,
            rows_preview=[],
        )

