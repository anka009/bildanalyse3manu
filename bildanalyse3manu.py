import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from scipy.ndimage import label, find_objects
import pandas as pd
from io import BytesIO
import json
import os

# Pfad zur Preset-Datei
preset_datei = "einstellungen_presets.json"

# Presets laden oder leeres Dictionary erstellen
if os.path.exists(preset_datei):
    with open(preset_datei, "r") as f:
        presets = json.load(f)
else:
    presets = {}

# Seiteneinstellungen
st.set_page_config(page_title="Bildanalyse Komfort-App", layout="wide")
st.title("🧪 Bildanalyse Komfort-App")

# Bild-Upload
uploaded_file = st.sidebar.file_uploader("📁 Bild auswählen", type=["png", "jpg", "jpeg", "tif", "tiff"])
if not uploaded_file:
    st.warning("Bitte zuerst ein Bild hochladen.")
    st.stop()

img_rgb = Image.open(uploaded_file).convert("RGB")
img_gray = img_rgb.convert("L")
img_array = np.array(img_gray)
w, h = img_rgb.size

# Hilfsfunktionen
def finde_flecken(cropped_array, min_area, max_area, intensity):
    mask = cropped_array < intensity
    labeled_array, _ = label(mask)
    objects = find_objects(labeled_array)
    return [
        ((obj[1].start + obj[1].stop) // 2, (obj[0].start + obj[0].stop) // 2)
        for obj in objects
        if min_area <= np.sum(labeled_array[obj] > 0) <= max_area
    ]

def gruppiere_flecken(centers, group_diameter):
    grouped, visited = [], set()
    for i, (x1, y1) in enumerate(centers):
        if i in visited:
            continue
        gruppe = [(x1, y1)]
        visited.add(i)
        for j, (x2, y2) in enumerate(centers):
            if j in visited:
                continue
            if ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5 <= group_diameter / 2:
                gruppe.append((x2, y2))
                visited.add(j)
        grouped.append(gruppe)
    return grouped

# Sidebar-Einstellungen
modus = st.sidebar.radio("Analyse-Modus wählen", ["Fleckengruppen", "Kreis-Ausschnitt"])
circle_color = st.sidebar.color_picker("🎨 Farbe für Fleckengruppen", "#FF0000")
spot_color = st.sidebar.color_picker("🟦 Farbe für einzelne Flecken", "#00FFFF")
circle_width = st.sidebar.slider("✒️ Liniendicke (Gruppen)", 1, 10, 6)
spot_radius = st.sidebar.slider("🔘 Flecken-Radius", 1, 20, 10)
preset_auswahl = st.sidebar.selectbox("Preset wählen", ["Set1", "Set2", "Set3", "Set4"])
preset = presets.get(preset_auswahl, {})
min_fleck = st.sidebar.slider("Minimale Fleckengröße", 1, 100, preset.get("min_fleck", 10))
max_fleck = st.sidebar.slider("Maximale Fleckengröße", 1, 100, preset.get("max_fleck", 50))
gruppendurchmesser = st.sidebar.slider("Gruppendurchmesser", 1, 100, preset.get("gruppendurchmesser", 30))
intensitaetsschwelle = st.sidebar.slider("Intensitäts-Schwelle", 0.0, 1.0, preset.get("intensitaetsschwelle", 0.5))
liniendicke = st.sidebar.slider("Liniendicke", 1, 10, preset.get("liniendicke", 2))
flecken_radius = st.sidebar.slider("Flecken-Radius", 1, 50, preset.get("flecken_radius", 10))

# Fleckengruppen-Modus
def fleckengruppen_modus():
    st.subheader("🧠 Fleckengruppen erkennen")
    col1, col2 = st.columns([1, 2])
    with col1:
        x_start = st.slider("Start-X", 0, w - 1, 0)
        x_end = st.slider("End-X", x_start + 1, w, w)
        y_start = st.slider("Start-Y", 0, h - 1, 0)
        y_end = st.slider("End-Y", y_start + 1, h, h)
        min_area = st.slider("Minimale Fleckengröße", 10, 500, 30)
        max_area = st.slider("Maximale Fleckengröße", min_area, 1000, 250)
        group_diameter = st.slider("Gruppendurchmesser", 20, 500, 60)
        intensity = st.slider("Intensitäts-Schwelle", 0, 255, value=25)
    with col2:
        cropped_array = img_array[y_start:y_end, x_start:x_end]
        centers = finde_flecken(cropped_array, min_area, max_area, intensity)
        grouped = gruppiere_flecken(centers, group_diameter)
        draw_img = img_rgb.copy()
        draw = ImageDraw.Draw(draw_img)
        for x, y in centers:
            draw.ellipse(
                [(x + x_start - spot_radius, y + y_start - spot_radius),
                 (x + x_start + spot_radius, y + y_start + spot_radius)],
                fill=spot_color
            )
        for gruppe in grouped:
            if gruppe:
                xs, ys = zip(*gruppe)
                x_mean = int(np.mean(xs))
                y_mean = int(np.mean(ys))
                radius = group_diameter / 2
                draw.ellipse(
                    [(x_mean + x_start - radius, y_mean + y_start - radius),
                     (x_mean + x_start + radius, y_mean + y_start + radius)],
                    outline=circle_color, width=circle_width
                )
        st.image(draw_img, caption="🎯 Ergebnisbild mit Markierungen", use_container_width=True)
        st.markdown("---")
        st.markdown("### 🧮 Ergebnisse")
        col_fleck, col_gruppe = st.columns(2)
        col_fleck.metric("Erkannte Flecken", len(centers))
        col_gruppe.metric("Erkannte Gruppen", len(grouped))
if st.sidebar.button("Preset speichern"):
    presets[preset_auswahl] = {
        "min_fleck": min_fleck,
        "max_fleck": max_fleck,
        "gruppendurchmesser": gruppendurchmesser,
        "intensitaetsschwelle": intensitaetsschwelle,
        "liniendicke": liniendicke,
        "flecken_radius": flecken_radius
    }
    with open(preset_datei, "w") as f:
        json.dump(presets, f)
    st.sidebar.success(f"{preset_auswahl} gespeichert!")

# Kreis-Ausschnitt-Modus
def kreis_modus():
    st.subheader("🎯 Kreis-Ausschnitt wählen")
    col1, col2 = st.columns([1, 2])
    with col1:
        center_x = st.slider("🞄 Mittelpunkt-X", 0, w - 1, w // 2)
        center_y = st.slider("🞄 Mittelpunkt-Y", 0, h - 1, h // 2)
        radius = st.slider("🔵 Radius", 10, min(w, h) // 2, 500)
    with col2:
        draw_img = img_rgb.copy()
        draw = ImageDraw.Draw(draw_img)
        draw.ellipse(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            outline=circle_color, width=circle_width
        )
        st.image(draw_img, caption="🖼️ Kreis-Vorschau", use_container_width=True)

    if st.checkbox("🎬 Nur Ausschnitt anzeigen"):
        mask = Image.new("L", (w, h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            fill=255
        )
        cropped = Image.composite(
            img_rgb,
            Image.new("RGB", img_rgb.size, (255, 255, 255)),
            mask
        )
        st.image(cropped, caption="🧩 Kreis-Ausschnitt", use_container_width=True)

        # Download-Button für Ausschnitt
        img_buffer = BytesIO()
        cropped.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        st.download_button(
            label="📥 Kreis-Ausschnitt herunterladen",
            data=img_bytes,
            file_name="kreis_ausschnitt.png",
            mime="image/png"
        )

# Modus ausführen
if modus == "Fleckengruppen":
    fleckengruppen_modus()
elif modus == "Kreis-Ausschnitt":
    kreis_modus()
