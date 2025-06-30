"""
log_writer.py

Captures detailed decision trails for each navigation session.
Creates a structured JSON log showing:
- intent
- domain
- strategies attempted
- memory usage
- timing info
- success/failure
"""

import json
from pathlib import Path
from datetime import datetime

class LogWriter:
    def __init__(self, logs_dir):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "events": []
        }

    def start_session(self, domain, intent_name):
        self.session_data.update({
            "domain": domain,
            "intent": intent_name,
            "strategies_tried": [],
            "memory_used": None,
            "final_strategy": None,
            "success": False,
            "error": None
        })

    def log_memory_strategy(self, strategy_type):
        self.session_data["memory_used"] = strategy_type
        self.log_event(f"Memory strategy prioritized: {strategy_type}")

    def log_attempt(self, strategy_label):
        self.session_data["strategies_tried"].append(strategy_label)
        self.log_event(f"Attempted strategy: {strategy_label}")

    def log_success(self, strategy_label):
        self.session_data["final_strategy"] = strategy_label
        self.session_data["success"] = True
        self.log_event(f"✅ Success using: {strategy_label}")

    def log_failure(self, error=None):
        self.session_data["success"] = False
        self.session_data["error"] = str(error) if error else "No element found"
        self.log_event(f"❌ Failed to locate element. {self.session_data['error']}")

    def log_event(self, message):
        self.session_data["events"].append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": message
        })

    def save(self, domain, intent_name):
        filename = f"log_{domain.replace('.', '_')}_{intent_name}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
        path = self.logs_dir / filename
        with open(path, "w") as f:
            json.dump(self.session_data, f, indent=2)
        print(f"📝 Log saved to: {path}")
