
import json

from services.learning_loop import get_learning_loop_json

clerk_id = input("Enter your Clerk user ID: ").strip()

if not clerk_id:
    raise ValueError("Clerk user ID cannot be empty")

try:
    payload = get_learning_loop_json(clerk_id)
    print("\nLearning Loop JSON Payload:\n")
    print(json.dumps(json.loads(payload), indent=2))
except Exception as exc:
    print(f"Test failed: {type(exc).__name__}: {exc}")
