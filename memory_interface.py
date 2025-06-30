"""
memory_interface.py

Handles persistent memory storage and retrieval for Kai_WebNavigator.
Stores successful selector strategies by domain and intent.

Initial implementation uses JSON for simplicity.
"""

import json
from pathlib import Path
from datetime import datetime

class MemoryInterface:
    def __init__(self, memory_file):
        self.memory_file = Path(memory_file)
        self.memory = self._load_memory()

    def _load_memory(self):
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_memory(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)

    def get(self, domain, intent):
        """Retrieve stored strategy for a domain and intent."""
        return self.memory.get(domain, {}).get(intent)

    def store(self, domain, intent, strategy):
        """Store a successful strategy for a domain and intent."""
        if domain not in self.memory:
            self.memory[domain] = {}
        self.memory[domain][intent] = {
            "successful_selector": strategy,
            "last_used": datetime.utcnow().isoformat() + "Z"
        }
        self._save_memory()
