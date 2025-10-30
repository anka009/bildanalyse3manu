import streamlit as st
import json
import os
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Bildanalyse Komfort-App", layout="wide")
st.title("🔍 Bildanalyse Komfort-App")

# === Preset-Verwaltung ===
preset_datei = "einstellungen_presets.json"
if os.path.exists(preset_datei):
    with open(preset_datei, "r") as f:
        presets = json.load(f)
else:
    presets = {}

preset_auswahl = st.sidebar.selectbox("🎛 Preset wählen", ["Set1", "Set2", "Set3", "Set4"])
preset = presets.get(preset_auswahl, {})

# === Sidebar: Parameter mit geladenen Werten ===
min_fleck = st.sidebar.slider("Minimale Fleckengröße", 1, 100, preset.get("min_fleck", 10))
max_fleck = st.sidebar.slider("Maximale Fleckengröße", 1, 100, preset.get("max_fleck", 50))
gruppendurchmesser = st.sidebar.slider("Gruppendurchmesser", 1, 100, preset.get("gruppendurchmesser", 30))
intensitaetsschwelle = st.sidebar.slider("Intensitäts-Schwelle", 0.0, 1.0, preset.get("intensitaetsschwelle", 0.5))
liniendicke = st.sidebar.slider("Liniendicke", 1, 10, preset.get("liniendicke", 2))
flecken_radius = st.sidebar.slider("Flecken-Radius", 1, 50, preset.get("flecken_radius", 10))

# === Preset speichern ===
if st.sidebar.button("💾 Preset speichern"):
    presets[preset_auswahl] = {
        "min_fleck": min_fleck,
        "max_fleck": max_fleck,
        "gruppendurchmesser": gruppendurchmesser,
        "intensitaetsschwelle": intensitaetsschwelle,
        "liniendicke": liniendicke,
        "flecken_radius": flecken_radius
    }
    with open(preset_datei, "w") as f:
        json.dump(presets, f, indent=2)
    st.sidebar.success(f"{preset_auswahl} wurde gespeichert ✅")

# === Bild-Upload ===
bilddatei = st.file_uploader("📷 Bild hochladen", type=["jpg", "jpeg", "png"])
if bilddatei:
    bild = Image.open(bilddatei).convert("RGB")
    bild_np = np.array(bild)

    # === Bildanalyse mit OpenCV ===
    grau = cv2.cvtColor(bild_np, cv2.COLOR_RGB2GRAY)
    _, schwelle = cv2.threshold(grau, int(intensitaetsschwelle * 255), 255, cv2.THRESH_BINARY)

    konturen, _ = cv2.findContours(schwelle, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    analysiert = bild_np.copy()

    for kontur in konturen:
        flaeche = cv2.contourArea(kontur)
        if min_fleck <= flaeche <= max_fleck:
            (x, y), radius = cv2.minEnclosingCircle(kontur)
            if radius <= flecken_radius:
                cv2.circle(analysiert, (int(x), int(y)), int(radius), (255, 0, 0), liniendicke)

    # === Anzeige: Original & Analysebild
    col1, col2 = st.columns(2)
    col1.image(bild, caption="📷 Originalbild", use_column_width=True)
    col2.image(analysiert, caption="🧪 Analysebild", use_column_width=True)
