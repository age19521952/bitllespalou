import streamlit as st

st.set_page_config(page_title="Visualizador 90.html", layout="wide")
st.title("Visualización del archivo 90.html")

try:
    with open("90.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Renderizar el HTML en Streamlit
    st.components.v1.html(html_content, height=800, scrolling=True)
    
except FileNotFoundError:
    st.error("No se encontró el archivo 90.html en el repositorio.")
