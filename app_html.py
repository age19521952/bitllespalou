import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analizador Bitlles Palou", layout="wide")

st.title("Analizador Bitlles Palou (Total = 90)")

@st.cache_data
def load_data():
    # Lee el Excel directamente desde el repositorio de GitHub
    url = "https://raw.githubusercontent.com/age19521952/bitllespalou/main/bitllespalou.xlsx"
    return pd.read_excel(url)

try:
    df = load_data()
    
    # Filtros en barra lateral o superior
    col1, col2, col3 = st.columns(3)
    with col1:
        equip_filter = st.text_input("Equip (Filtrado)", value="palou")
    with col2:
        total_filter = st.text_input("Total (Puntos)", value="90")
    with col3:
        search_jugador = st.text_input("Buscar Jugador", value="")

    # Normalizar columnas para evitar errores de mayúsculas/minúsculas
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Filtrado básico
    filtered_df = df.copy()
    if equip_filter and 'equip' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['equip'].astype(str).str.lower() == equip_filter.lower()]
        
    if total_filter and ('total' in filtered_df.columns or 'totalc' in filtered_df.columns):
        col_total = 'total' if 'total' in filtered_df.columns else 'totalc'
        filtered_df = filtered_df[filtered_df[col_total].astype(str) == total_filter]

    if search_jugador and 'jugadors' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['jugadors'].astype(str).str.lower().str.contains(search_jugador.lower())]

    st.write(f"Registros encontrados: {len(filtered_df)}")
    
    # Mostrar tabla dinámica o datos filtrados
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")
