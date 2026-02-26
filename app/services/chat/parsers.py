import json
import re

from app.schemas.chat import TokenUsage

def model_dict(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def get_response_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(parts).strip()
    return str(content)


def _escape_control_chars_inside_json_strings(text: str) -> str:
    """Repair invalid raw control chars inside JSON string values."""
    out = []
    in_string = False
    escaping = False

    for ch in text:
        if in_string:
            if escaping:
                out.append(ch)
                escaping = False
                continue

            if ch == "\\":
                out.append(ch)
                escaping = True
                continue

            if ch == '"':
                out.append(ch)
                in_string = False
                continue

            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            if ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
                continue

            out.append(ch)
            continue

        out.append(ch)
        if ch == '"':
            in_string = True

    return "".join(out)


def parse_first_json(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    candidate = text[start:]
    decoder = json.JSONDecoder()
    try:
        return decoder.raw_decode(candidate)[0]
    except json.JSONDecodeError:
        repaired = _escape_control_chars_inside_json_strings(candidate)
        return decoder.raw_decode(repaired)[0]


def _decode_json_string_fragment(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        # Last resort for bad escaping from model output
        return value.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t")


def extract_sql_query(text: str) -> str:
    # 1) Best case: valid or repaired JSON
    try:
        parsed = parse_first_json(text)
        sql = parsed.get("sql_query") if isinstance(parsed, dict) else None
        if isinstance(sql, str) and sql.strip():
            return sql.strip()
    except Exception:
        pass

    # 2) Malformed JSON but still contains "sql_query": "..."
    json_sql_match = re.search(
        r'"sql_query"\s*:\s*"((?:\\.|[^"\\])*)"',
        text,
        flags=re.DOTALL,
    )
    if json_sql_match:
        sql = _decode_json_string_fragment(json_sql_match.group(1)).strip()
        if sql:
            return sql

    # 3) Fenced SQL block
    fenced_sql = re.search(r"```sql\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced_sql:
        sql = fenced_sql.group(1).strip()
        if sql:
            return sql

    # 4) Any fenced block (some models omit the language tag)
    fenced_any = re.search(r"```\s*(.*?)```", text, flags=re.DOTALL)
    if fenced_any:
        candidate = fenced_any.group(1).strip()
        if candidate.lower().startswith(("select", "with")):
            return candidate

    # 5) Last resort: first SELECT/WITH statement in raw output
    stmt = re.search(r"\b(select|with)\b[\s\S]*?(;|$)", text, flags=re.IGNORECASE)
    if stmt:
        sql = stmt.group(0).strip()
        if sql:
            return sql

    raise ValueError("Could not extract sql_query from model output")


def parse_sql_answer(text: str) -> dict:
    try:
        parsed = parse_first_json(text)
        if isinstance(parsed, dict):
            sql = parsed.get("sql_query")
            if isinstance(sql, str) and sql.strip():
                answer = parsed.get("natural_language_answer")
                if not isinstance(answer, str):
                    answer = ""
                return {
                    "natural_language_answer": answer,
                    "sql_query": sql,
                }
    except json.JSONDecodeError:
        pass

    return {
        "natural_language_answer": "",
        "sql_query": extract_sql_query(text),
    }


def get_token_usage(response) -> TokenUsage:
    def to_int(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def parse_usage(data):
        if not isinstance(data, dict):
            return None

        for key in ("usage", "usage_metadata", "token_usage", "token_count"):
            nested = data.get(key)
            if isinstance(nested, dict):
                usage = parse_usage(nested)
                if usage:
                    return usage

        prompt = data.get("prompt_tokens", data.get("input_tokens"))
        completion = data.get("completion_tokens", data.get("output_tokens"))
        total = data.get("total_tokens")

        if prompt is None and completion is None and total is None:
            return None

        prompt = to_int(prompt)
        completion = to_int(completion)
        total = to_int(total if total is not None else prompt + completion)
        return TokenUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    return (
        parse_usage(getattr(response, "usage_metadata", None))
        or parse_usage(getattr(response, "response_metadata", None))
        or TokenUsage()
    )



