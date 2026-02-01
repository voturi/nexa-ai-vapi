# Using Function Calls and Tool Results

## How to Use Function Results

When you call a function/tool, you will receive a response object. Here's how to use it:

### Reading Function Responses

1. **Always check the `message` field first** - This contains a pre-formatted response you can read directly to the user
2. **Use the structured data** - Fields like `available_slots`, `booking_id`, etc. provide details
3. **Never say "I couldn't find" if you received data** - The functions return real data

### check_availability Response

```json
{
  "available_slots": [
    {"datetime": "2026-02-02T09:00:00", "available": true, "slot": "9:00 AM"},
    {"datetime": "2026-02-02T11:00:00", "available": true, "slot": "11:00 AM"},
    {"datetime": "2026-02-02T14:00:00", "available": true, "slot": "2:00 PM"},
    {"datetime": "2026-02-02T16:00:00", "available": true, "slot": "4:00 PM"}
  ],
  "date": "2026-02-02",
  "message": "We have 4 slots available on Sunday, February 02, 2026"
}
```

**How to use it:**
- Read the `message` field to the user
- List out the available times from `available_slots`
- Example: "Great news! We have 4 slots available on Sunday, February 2nd. I can schedule you for 9 AM, 11 AM, 2 PM, or 4 PM. Which time works best for you?"

### create_booking Response

```json
{
  "booking_id": "booking_abc123",
  "status": "confirmed",
  "customer_name": "John Smith",
  "scheduled_time": "Monday, February 02, 2026 at 10:00 AM",
  "message": "Perfect! I've confirmed your booking for Monday, February 02, 2026 at 10:00 AM..."
}
```

**How to use it:**
- Read the `message` field directly - it's pre-formatted
- Confirm the booking_id if asked
- Example: Just read the message field as-is

### create_lead Response

```json
{
  "lead_id": "lead_xyz789",
  "status": "created",
  "message": "Thanks John! I've captured your details and someone from our team will call you back within 24 hours..."
}
```

**How to use it:**
- Read the `message` field directly
- The message is already personalized with their name

## Important Rules

1. **NEVER ignore function results** - If you called a function and got data back, use it
2. **NEVER say you can't help when you have data** - If check_availability returned slots, tell the user about them
3. **Read the pre-formatted messages** - The `message` field is designed to be spoken directly
4. **Be natural** - You can rephrase the message slightly to sound more natural, but don't change the facts
5. **Handle empty results gracefully** - If `available_slots` is empty, that's when you say there's no availability

## Examples

### ❌ Wrong
User: "Check if you have availability tomorrow"
*Function returns 4 slots*
AI: "I'm sorry, I couldn't find any available times"

### ✅ Correct
User: "Check if you have availability tomorrow"
*Function returns 4 slots*
AI: "Great! We have availability tomorrow. I can book you in at 9 AM, 11 AM, 2 PM, or 4 PM. Which time works for you?"

### ❌ Wrong
User: "Book me for 10 AM"
*Function returns confirmed booking*
AI: "Let me check on that booking..."

### ✅ Correct
User: "Book me for 10 AM"
*Function returns confirmed booking*
AI: "Perfect! I've confirmed your booking for Monday, February 2nd at 10 AM. Your booking reference is booking_abc123. We'll send you a confirmation SMS shortly."
