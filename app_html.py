import streamlit as st

st.set_page_config(page_title="Visualizador 90.html", layout="wide")

# Leer el archivo 90.html del repositorio
try:
    with open("90.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Renderizar el HTML con mayor altura para que no se corte
    st.components.v1.html(html_content, height=1200, scrolling=True)
    
except FileNotFoundError:
    st.error("No se encontró el archivo 90.html en el repositorio.")
