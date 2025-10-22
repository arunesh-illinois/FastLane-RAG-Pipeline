from backend.services.utils import detect_intent_regex
from backend.services.appointments import  schedule_appointment, reschedule_appointment  # All regex-based, no LLM

# Test 1: Intent detection
print("=== Test 1: Intent Detection ===")
test_messages = [
    "What's our late policy and can you book Chen tomorrow at 10:30 in Midtown?",
    "Where do patients park?",
    "Schedule Rivera Monday 9am at Midtown",
    "Make it 11:00 instead"
]

for msg in test_messages:
    intent = detect_intent_regex(msg, session_id="test-session")
    print(f"\nMessage: {msg}")
    print(f"Intent: {intent}")

# Test 2: Scheduling
print("\n\n=== Test 2: Scheduling ===")
result1 = schedule_appointment({
    "patient": "Chen",
    "preferred_slot_iso": "2025-10-21T10:30:00-04:00",
    "location": "Midtown"
}, session_id="session1")
print(f"First booking: {result1}")

# Test idempotency
result2 = schedule_appointment({
    "patient": "Chen",
    "preferred_slot_iso": "2025-10-21T10:30:00-04:00",
    "location": "Midtown"
}, session_id="session1")
print(f"Duplicate booking: {result2}")
assert result1["appt_id"] == result2["appt_id"], "Idempotency failed!"
assert result2["status"] == "already_booked", "Status should be already_booked"

# Test 3: Rescheduling
print("\n\n=== Test 3: Rescheduling ===")
result3 = reschedule_appointment("session1", "2025-10-21T11:00:00-04:00")
print(f"Rescheduled: {result3}")
assert result3["status"] == "rescheduled", "Rescheduling failed!"
assert result3["appt_id"] == result1["appt_id"], "Should be same appointment"

print("\n✅ All tool tests passed!")