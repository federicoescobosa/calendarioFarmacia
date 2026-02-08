from __future__ import annotations

DAYS = ["L", "M", "X", "J", "V", "S", "D"]

# --------------------------
# Turnos
# --------------------------
TURN_DEFS = {
    "M1": {"label": "Mañana 08:30–14:30", "hours": "08:30–14:30", "bg": "#DDEBFF", "fg": "#1F4E79"},
    "M2": {"label": "Mañana 09:00–14:00", "hours": "09:00–14:00", "bg": "#DFF7FF", "fg": "#0B4F6C"},
    "M3": {"label": "Mañana 09:30–14:00", "hours": "09:30–14:00", "bg": "#E4FFF0", "fg": "#0C5A2A"},
    "M4": {"label": "Mañana 10:00–14:30", "hours": "10:00–14:30", "bg": "#E9E4FF", "fg": "#3B2A7A"},
    "M5": {"label": "Mañana 10:00–13:30", "hours": "10:00–13:30", "bg": "#FFF2CC", "fg": "#6B4E00"},
    "T": {"label": "Tarde 17:00–20:30", "hours": "17:00–20:30", "bg": "#FFE6CC", "fg": "#7A3E00"},
    "L": {"label": "Libre", "hours": "No trabaja", "bg": "#F2F2F2", "fg": "#444444"},
    # ✅ Guardia
    "G": {"label": "Guardia", "hours": "Guardia (pendiente de concretar)", "bg": "#FFD9E6", "fg": "#7A0036"},
}

# Orden mostrado en combos (Reglas y Calendario)
TURN_ORDER = ["M1", "M2", "M3", "M4", "M5", "T", "G", "L"]
