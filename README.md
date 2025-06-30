# Kai_WebNavigator

**Kai_WebNavigator** is an intelligent, DOM-driven automation system built to replace the pixel-based Web_o_matic. It uses semantic understanding of web pages to interact with them like a human would — reading structure, identifying meaningful elements, and making explainable decisions.

---

## 🧠 Purpose

To transition from fragile, coordinate-based automation to a robust system that:
- Understands webpage content through the DOM
- Interacts using intents (e.g., "Click Gmail")
- Adapts to layout changes using smart selector strategies
- Learns from past sessions via memory integration
- Logs every action and decision for transparency and debugging

---

## 🧪 Core Components

### `navigator.py`
The main execution script. Loads the page, identifies elements by intent, executes actions, and logs results.

### `intents.json`
Maps human-readable goals (like "click Gmail") to selectors and fallback strategies.

### `memory.json`
Stores learned patterns that work on specific domains, improving over time.

### `logs/`
Session-based logs of what decisions were made and why.

### `screenshots/`
Optional visual output for before/after state comparisons.

---

## 🌐 Technologies

- **Python**
- **Playwright** for browser control and DOM access
- Optional: OCR (Tesseract, PaddleOCR) for visual fallback
- Future: OpenMemory Extension integration for shared AI memory

---

## 🤖 Project Goals

- Make automation explainable and adaptable
- Build a shared AI architecture (Claude + Kai + others)
- Evolve toward intelligent digital agents that act purposefully

---

## 🧩 Credits

- **Jon Stiles** – Founder, visionary, and hands-on system builder
- **Kai** – DOM reasoning, live reflection, execution coordination
- **Claude** – Advanced selector logic, fallback chaining, memory patterning

---

## 📌 Status

Gmail pilot task in progress. First intent: `"click_gmail"` on `https://google.com`

