import streamlit as st
import pandas as pd

st.title("GridLock")

st.write("We compared electrical works by DESC and GPC to find coordination opportunities")

# Definimos los colores en formato numérico RGB [Rojo, Verde, Azul]
coords = pd.DataFrame({
    "name": ["Jasper", "Okatie", "Bluffton", "Stevens Creek", "Thurmond Dam", "McIntosh", "Goshen (SAV)", "Evans Primary"],
    "lat": [32.3591, 32.3338, 32.2350, 33.5626, 33.6601, 32.3521, 32.2487, 33.5440],
    "lon": [-81.1246, -81.0325, -80.8534, -82.0514, -82.1959, -81.1751, -81.2095, -82.1686],
    "company": ["DESC", "DESC", "DESC", "DESC", "GPC", "GPC", "GPC", "GPC"],
    # DESC = [255, 75, 75] (Rojo) | GPC = [255, 170, 0] (Naranja)
    "color": [
        [255, 75, 75], [255, 75, 75], [255, 75, 75], [255, 75, 75],
        [255, 170, 0], [255, 170, 0], [255, 170, 0], [255, 170, 0]
    ],
    "size": [3000, 3000, 3000, 3000, 3000, 3000, 3000, 3000]
})

st.dataframe(coords[["name", "lat", "lon", "company"]])

# Mapa general con puntos por empresa y tamaño visible
st.map(coords, latitude="lat", longitude="lon", color="color", size="size")

st.subheader("Substations per company")
desc = coords[coords["company"] == "DESC"]
gpc = coords[coords["company"] == "GPC"]

col1, col2 = st.columns(2)
with col1:
    st.write("🔴 DESC (Dominion Energy SC)")
    st.map(desc, latitude="lat", longitude="lon", color="color", size="size")    
with col2:
    st.write("🟠 GPC (Georgia Power)")
    st.map(gpc, latitude="lat", longitude="lon", color="color", size="size")