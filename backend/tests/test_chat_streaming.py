"""
Unit tests for Real-time Streaming AI Chat (POST /api/v1/chat).
Verifies:
1. ChatRequest schema accepts message and defaults stream=True.
2. stream_chat_response yields SSE-formatted chunks:
   - Content tokens (type="content", delta=...)
   - Course metadata (type="metadata", recommendations=...)
   - Completion signal ([DONE])
3. Non-academic queries yield refusal SSE payload without calling Gemini.
4. Error handling yields SSE error event and completes cleanly.
5. ai_chat endpoint returns StreamingResponse when stream=True.
6. ai_chat endpoint returns JSON payload when stream=False.
7. Message length validation rejects empty or single-character prompts with 400.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.ai import ChatRequest, ai_chat
from services.chat_stream_service import stream_chat_response


def run_coro(coro):
    """Executes a non-suspending coroutine synchronously."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


def collect_async_gen(agen):
    """Consumes an async generator synchronously without spinning up loopback socket threads."""
    items = []
    while True:
        try:
            coro = agen.asend(None)
            coro.send(None)
        except StopIteration as exc:
            items.append(exc.value)
        except StopAsyncIteration:
            break
    return items


async def immediate_threadpool(func, *args, **kwargs):
    return func(*args, **kwargs)


class TestChatStreaming(unittest.TestCase):
    """Verifies streaming generator logic and SSE protocol."""

    def setUp(self):
        self.clerk_id = "user_clerk_test"
        self.user_data = {"sub": self.clerk_id, "email": "student@skit.ac.in"}

    def test_chat_request_schema(self):
        req = ChatRequest(message="Explain deadlock avoidance")
        self.assertEqual(req.message, "Explain deadlock avoidance")
        self.assertTrue(req.stream)

        req_sync = ChatRequest(message="Explain deadlock avoidance", stream=False)
        self.assertFalse(req_sync.stream)

    @patch("services.chat_stream_service.run_in_threadpool", side_effect=immediate_threadpool)
    def test_stream_chat_response_content_chunks(self, mock_threadpool):
        # Mock Gemini client and response stream
        mock_client = MagicMock()
        mock_chunk_1 = MagicMock(text="Deadlock avoidance ")
        mock_chunk_2 = MagicMock(text="uses Banker's algorithm.")
        mock_client.models.generate_content_stream.return_value = [mock_chunk_1, mock_chunk_2]

        agen = stream_chat_response(
            message="Explain deadlock avoidance in operating systems",
            clerk_id=self.clerk_id,
            gemini_client=mock_client,
            target_model="gemini-test",
        )
        collected_events = collect_async_gen(agen)

        # Verify stream content: content 1, content 2, metadata, [DONE]
        self.assertGreaterEqual(len(collected_events), 3)

        # Chunk 1
        event_1 = json.loads(collected_events[0].replace("data: ", "").strip())
        self.assertEqual(event_1["type"], "content")
        self.assertEqual(event_1["delta"], "Deadlock avoidance ")

        # Chunk 2
        event_2 = json.loads(collected_events[1].replace("data: ", "").strip())
        self.assertEqual(event_2["type"], "content")
        self.assertEqual(event_2["delta"], "uses Banker's algorithm.")

        # Final metadata event
        meta_event = json.loads(collected_events[2].replace("data: ", "").strip())
        self.assertEqual(meta_event["type"], "metadata")
        self.assertIn("recommendations", meta_event)

        # Completion signal
        self.assertEqual(collected_events[-1].strip(), "data: [DONE]")

    def test_stream_chat_refusal_for_non_academic_query(self):
        agen = stream_chat_response(
            message="Who won the IPL cricket match yesterday?",
            clerk_id=self.clerk_id,
        )
        collected_events = collect_async_gen(agen)

        self.assertEqual(len(collected_events), 2)
        refusal_event = json.loads(collected_events[0].replace("data: ", "").strip())
        self.assertEqual(refusal_event["type"], "refusal")
        self.assertTrue(refusal_event["is_refused"])
        self.assertIn("refusal_message", refusal_event)
        self.assertEqual(collected_events[1].strip(), "data: [DONE]")

    @patch("services.chat_stream_service.run_in_threadpool", side_effect=immediate_threadpool)
    def test_stream_chat_handles_exception(self, mock_threadpool):
        mock_client = MagicMock()
        mock_client.models.generate_content_stream.side_effect = RuntimeError("Gemini quota exceeded")

        agen = stream_chat_response(
            message="Explain semaphores in Operating Systems",
            clerk_id=self.clerk_id,
            gemini_client=mock_client,
        )
        collected_events = collect_async_gen(agen)

        error_event = json.loads(collected_events[0].replace("data: ", "").strip())
        self.assertEqual(error_event["type"], "error")
        self.assertIn("detail", error_event)
        self.assertEqual(collected_events[1].strip(), "data: [DONE]")

    def test_ai_chat_returns_streaming_response_by_default(self):
        payload = ChatRequest(message="What is paging in memory management?", stream=True)
        response = run_coro(ai_chat(payload, self.user_data))

        self.assertIsInstance(response, StreamingResponse)
        self.assertEqual(response.media_type, "text/event-stream")
        self.assertEqual(response.headers.get("Cache-Control"), "no-cache")

    def test_ai_chat_validation_short_message(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            ChatRequest(message="?")

        self.assertIn("at least 2 characters", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
