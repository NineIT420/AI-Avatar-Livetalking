import asyncio
from typing import Any


async def llm_response(text: str, nerfreal: Any) -> str:
    return f"Echo: {text}"
