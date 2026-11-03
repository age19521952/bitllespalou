import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analizador Bitlles Palou", layout="wide")

st.title("Analizador Bitlles Palou (Total = 90)")

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/age19521952/bitllespalou/main/bitllespalou.xlsx"
    return pd.read_excel(url)

try:
    df = load_data()
    
    # Normalizar nombres de columnas a minúsculas
    df.columns = [str(c).strip().lower() for c in df.columns]

    col1, col2, col3 = st.columns(3)
    with col1:
        equip_filter = st.text_input("Equip (Filtrado)", value="palou")
    with col2:
        total_filter = st.text_input("Total (Puntos)", value="90")
    with col3:
        search_jugador = st.text_input("Buscar Jugador", value="")

    filtered_df = df.copy()

    # Filtrar por equipo
    if equip_filter and 'equip' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['equip'].astype(str).str.lower() == equip_filter.lower()]
        
    # Filtrar por total
    if total_filter != '':
        if 'total' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['total'].astype(str) == total_filter]
        elif 'totalc' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['totalc'].astype(str) == total_filter]

    # Filtrar por jugador (buscando en la columna 'jugador')
    if search_jugador:
        jugador_col = None
        for col in ['jugador', 'jugadors', 'nom']:
            if col in filtered_df.columns:
                jugador_col = col
                break
        if jugador_col:
            filtered_df = filtered_df[filtered_df[jugador_col].astype(str).str.lower().str.contains(search_jugador.lower(), na=False)]

    st.write(f"Registros encontrados: {len(filtered_df)}")
    
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")
