import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from scipy.ndimage import label, find_objects
from io import BytesIO

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
    centers = []
    for obj in objects:
        if obj is None:
            continue
        area = np.sum(labeled_array[obj] > 0)
        if min_area <= area <= max_area:
            cx = (obj[1].start + obj[1].stop) // 2
            cy = (obj[0].start + obj[0].stop) // 2
            centers.append((cx, cy))
    return centers

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
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            if dist <= group_diameter / 2:
                gruppe.append((x2, y2))
                visited.add(j)
        grouped.append(gruppe)
    return grouped

# Sidebar-Einstellungen (geben eindeutige Keys)
modus = st.sidebar.radio("Analyse-Modus wählen", ["Fleckengruppen", "Kreis-Ausschnitt"], key="mode_radio")
circle_color = st.sidebar.color_picker("🎨 Farbe für Fleckengruppen", "#FF0000", key="circle_color")
spot_color   = st.sidebar.color_picker("🟦 Farbe für einzelne Flecken", "#00FFFF", key="spot_color")
circle_width = st.sidebar.slider("✒️ Liniendicke (Gruppen)", 1, 10, 6, key="circle_width")
spot_radius  = st.sidebar.slider("🔘 Flecken-Radius", 1, 20, 10, key="spot_radius")

# -----------------------
# Fleckengruppen-Modus
# -----------------------
def fleckengruppen_modus():
    st.subheader("🧠 Fleckengruppen erkennen")
    col1, col2 = st.columns([1, 2])

    with col1:
        # 1) Slots: zuerst definieren und ggf. laden, bevor die Slider erzeugt werden
        st.markdown("### 💾 Analyse-Parameter speichern/laden")
        slot = st.selectbox("Speicherplatz wählen", [1, 2, 3, 4], key="slot_selectbox")

        # Buttons in einer Form kapseln, um klare Submit-Momente zu haben
        with st.form(key="preset_form"):
            save_clicked = st.form_submit_button("📥 In Slot speichern")
            load_clicked = st.form_submit_button("📤 Aus Slot laden")

        # 2) Wenn laden gedrückt wurde: Defaults in separate Keys setzen, dann rerun
        if load_clicked:
            preset_key = f"preset{slot}"
            if preset_key in st.session_state:
                params = st.session_state[preset_key]
                # Nur Defaults setzen, NICHT direkt die existierenden Widget-Keys
                st.session_state["loaded_min_area"]       = int(params.get("min_area", 30))
                st.session_state["loaded_max_area"]       = int(params.get("max_area", 250))
                st.session_state["loaded_group_diameter"] = int(params.get("group_diameter", 60))
                st.session_state["loaded_intensity"]      = int(params.get("intensity", 25))
                st.success(f"Parameter aus Slot {slot} geladen!")
                st.rerun()
            else:
                st.warning(f"Slot {slot} ist noch leer.")

        # 3) Slider werden nun mit Defaults aus loaded_* erzeugt
        x_start = st.slider("Start-X", 0, w - 1, 0, key="x_start")
        x_end   = st.slider("End-X", x_start + 1, w, w, key="x_end")
        y_start = st.slider("Start-Y", 0, h - 1, 0, key="y_start")
        y_end   = st.slider("End-Y", y_start + 1, h, h, key="y_end")

        min_default = st.session_state.get("loaded_min_area", 30)
        max_default = st.session_state.get("loaded_max_area", 250)
        group_default = st.session_state.get("loaded_group_diameter", 60)
        intensity_default = st.session_state.get("loaded_intensity", 25)

        min_area = st.slider("Minimale Fleckengröße", 10, 500, value=min_default, key="min_area")
        # Achtung: Bound-Abhängigkeit. Der Default für max_area darf kleiner als min_area sein → clampen:
        max_default = max(max_default, min_area)
        max_area = st.slider("Maximale Fleckengröße", min_area, 1000, value=max_default, key="max_area")
        group_diameter = st.slider("Gruppendurchmesser", 20, 500, value=group_default, key="group_diameter")
        intensity = st.slider("Intensitäts-Schwelle", 0, 255, value=intensity_default, key="intensity")

        # 4) Speichern: schreibt in presetX, nicht in Widget-Keys
        if save_clicked:
            st.session_state[f"preset{slot}"] = {
                "min_area": min_area,
                "max_area": max_area,
                "group_diameter": group_diameter,
                "intensity": intensity,
            }
            st.success(f"Parameter in Slot {slot} gespeichert!")

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

# -----------------------
# Kreis-Ausschnitt-Modus (unverändert)
# -----------------------
def kreis_modus():
    st.subheader("🎯 Kreis-Ausschnitt wählen")
    col1, col2 = st.columns([1, 2])

    with col1:
        center_x = st.slider("🎄 Mittelpunkt-X", 0, w - 1, w // 2, key="center_x")
        center_y = st.slider("🎄 Mittelpunkt-Y", 0, h - 1, h // 2, key="center_y")
        radius = st.slider("🔵 Radius", 10, min(w, h) // 2, 500, key="radius")

    with col2:
        draw_img = img_rgb.copy()
        draw = ImageDraw.Draw(draw_img)
        draw.ellipse(
            [(center_x - radius, center_y - radius),
             (center_x + radius, center_y + radius)],
            outline=circle_color, width=circle_width
        )
        st.image(draw_img, caption="🖼️ Kreis-Vorschau", use_container_width=True)

# Modus ausführen
if modus == "Fleckengruppen":
    fleckengruppen_modus()
elif modus == "Kreis-Ausschnitt":
    kreis_modus()
