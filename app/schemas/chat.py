from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "session_id": "11",
                "message": "what is the total sales for last month?",
                "context": {
                    "role": "analyst"
                }
            }
        }
    )

    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)
    context: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    natural_language_answer: str
    sql_query: str
    token_usage: TokenUsage
    latency_ms: int
    provider: Literal["cohere", "groq"]
    model: str
    status: Literal["ok", "error"]
    row_count: int = 0
    rows_preview: List[Dict[str, Any]] = Field(default_factory=list)

class SqlAnswer(BaseModel):
    natural_language_answer: str = ""
    sql_query: str



