import time
from datetime import datetime
from backend import db
from jarvis import weather

class BasicAICore:
    def __init__(self):
        self.user_name = "JaQhai"

    def chat(self, message: str) -> str:
        def _generate_response() -> str:
            message_lower = message.lower().strip()

            # Enhanced responses
            if not message_lower:
                return "I'm listening, JaQhai..."

            elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                return f"Hello {self.user_name}! I'm J.A.R.V.I.S. Ready to assist with your AI project. How can I help?"

            elif 'time' in message_lower:
                current_time = datetime.now().strftime("%I:%M %p")
                return f"The current time is {current_time} on {datetime.now().strftime('%A, %B %d, %Y')}"

            elif 'date' in message_lower:
                current_date = datetime.now().strftime("%A, %B %d, %Y")
                return f"Today is {current_date}"

            elif 'how are you' in message_lower:
                return "I'm functioning at optimal levels! Excited to see our project coming together. What should we work on next?"

            elif any(word in message_lower for word in ['project', 'code', 'develop']):
                return "I can help with your J.A.R.V.I.S project! I see you have the backend running. Would you like to work on voice control, device integration, or the genetic designer next?"

            elif any(word in message_lower for word in ['thank', 'thanks']):
                return "You're welcome! It's my purpose to assist you. What's our next milestone?"

            elif any(word in message_lower for word in ['bye', 'exit', 'quit']):
                return "Goodbye! I'll be here when you need me. Remember to save your progress!"

            elif 'weather' in message_lower:
                try:
                    # Very simple parsing, expects "weather in city"
                    city = message_lower.split(" in ")[1].strip()
                    return weather.get_weather(city)
                except IndexError:
                    return "Of course. Which city's weather are you interested in? (e.g., 'weather in New York')"

            elif "list devices" in message_lower:
                all_devices = db.list_devices()
                if not all_devices:
                    return "There are no devices registered with me yet."
                response_lines = ["Here are your registered devices:"]
                for device in all_devices:
                    response_lines.append(f"- {device['name']} (Type: {device['type']}, ID: {device['id']})")
                return "\n".join(response_lines)

            elif message_lower.startswith("device "):
                parts = message.split(maxsplit=3)
                if len(parts) < 3:
                    return "To control a device, please use the format: 'device <name> <command> [json_payload]'"

                device_name = parts[1]
                command = parts[2]
                payload_str = parts[3] if len(parts) > 3 else None

                all_devices = db.list_devices()
                target_device = None
                for d in all_devices:
                    if d['name'].lower() == device_name.lower():
                        target_device = d
                        break

                if not target_device:
                    return f"I could not find a registered device named '{device_name}'. You can ask me to 'list devices'."

                payload = None
                if payload_str:
                    import json
                    try:
                        payload = json.loads(payload_str)
                    except json.JSONDecodeError:
                        return "The payload you provided is not valid JSON. Please check the format."

                db.add_command_to_queue(device_id=target_device['id'], command=command, payload=payload)
                return f"Okay, I've sent the '{command}' command to the {target_device['name']}."

            elif 'joke' in message_lower:
                return "Why don't scientists trust atoms? Because they make up everything! 😄 What else can I help with?"

            elif any(word in message_lower for word in ['goal', 'plan', 'schedule']):
                return "Based on our schedule, we should focus on: 1) Basic AI chat (DONE! 🎉), 2) Voice integration, 3) Mobile optimization. What would you like to tackle next?"

            else:
                # More helpful learning response
                return f"I'm processing your request: '{message}'. I'm still learning, but I can help with time, project planning, basic questions, or tell you a joke! What would you like to know?"

        response = _generate_response()
        db.add_to_history(user_message=message, jarvis_response=response)
        return response