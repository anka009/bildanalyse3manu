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
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image, ImageDraw
import numpy as np
import streamlit as st

def fleckengruppen_modus():
    global img_rgb, img_array  # Originalbild und Graustufenarray

    st.subheader("🧠 Fleckengruppen erkennen")
    col1, col2 = st.columns([1, 2])

    # -------------------------------
    # 1️⃣ Linke Spalte: Parameter + Buttons
    # -------------------------------
    with col1:
        st.markdown("### Analyse-Parameter")
        min_area = st.slider("Minimale Fleckengröße", 10, 500, 30, key="min_area")
        max_area = st.slider("Maximale Fleckengröße", min_area, 1000, 250, key="max_area")
        group_diameter = st.slider("Gruppendurchmesser", 20, 500, 60, key="group_diameter")
        intensity = st.slider("Intensitäts-Schwelle", 0, 255, 25, key="intensity")

        # manuelle Punkteverwaltung
        if "manual_points" not in st.session_state:
            st.session_state["manual_points"] = []

        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("❌ Letzten Punkt löschen"):
            if st.session_state["manual_points"]:
                st.session_state["manual_points"].pop()
        if col_btn2.button("♻️ Alle manuell gesetzten Punkte löschen"):
            st.session_state["manual_points"].clear()

    # -------------------------------
    # 2️⃣ Rechte Spalte: Bild & Klicks
    # -------------------------------
    with col2:
        # Anzeigegröße fixieren
        display_w = 800
        scale = display_w / img_rgb.width
        display_h = int(img_rgb.height * scale)
        display_img = img_rgb.resize((display_w, display_h), resample=Image.LANCZOS)

        # Klickerfassung auf skaliertem Bild
        clicked = streamlit_image_coordinates(display_img, key="click_img")
        if clicked is not None:
            x_scaled = int(clicked["x"] / scale)
            y_scaled = int(clicked["y"] / scale)
            st.session_state["manual_points"].append((x_scaled, y_scaled))
            st.rerun()

        # -------------------------------
        # Bild mit allen Punkten vorbereiten
        # -------------------------------
        final_img = img_rgb.copy()  # Kopie des Originalbildes
        draw = ImageDraw.Draw(final_img)

        # automatische Flecken
        centers = finde_flecken(img_array, min_area, max_area, intensity)
        for x, y in centers:
            draw.ellipse([(x-4, y-4), (x+4, y+4)], fill="#00FFFF")

        # manuelle Punkte
        for x, y in st.session_state["manual_points"]:
            draw.ellipse([(x-4, y-4), (x+4, y+4)], fill="#00FF00")

        # Gruppenkreise (rot)
        grouped = gruppiere_flecken(centers, group_diameter)
        for gruppe in grouped:
            if gruppe:
                xs, ys = zip(*gruppe)
                x_mean = int(np.mean(xs))
                y_mean = int(np.mean(ys))
                radius = group_diameter / 2
                draw.ellipse(
                    [(x_mean - radius, y_mean - radius),
                     (x_mean + radius, y_mean + radius)],
                    outline="#FF0000", width=3
                )

        # -------------------------------
        # 3️⃣ RGB-Fix + Anzeige
        # -------------------------------
        final_img = final_img.convert("RGB")
        show_img_np = np.array(final_img)
        st.image(show_img_np, caption="🎯 Bild mit automatischen + manuellen Punkten", use_container_width=True)

        # -------------------------------
        # 4️⃣ Statistik
        # -------------------------------
        st.markdown("---")
        col_a, col_b = st.columns(2)
        col_a.metric("Automatische Flecken", len(centers))
        col_b.metric("Manuelle Punkte", len(st.session_state["manual_points"]))

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
