import streamlit as st
import pandas as pd

st.set_page_config(page_title="Analizador Bitlles Palou", layout="wide")

st.title("Analizador Bitlles Palou")

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/age19521952/bitllespalou/main/bitllespalou.xlsx"
    return pd.read_excel(url)

try:
    df = load_data()
    
    # Normalizar nombres de columnas a minúsculas
    df.columns = [str(c).strip().lower() for c in df.columns]

    # --- ZONA DE FILTROS ---
    col1, col2, col3 = st.columns(3)
    
    # Filtro 1: Equip (texto/búsqueda)
    equip_filter = col1.text_input("Filtrar por Equip", value="palou")

    # Filtro 2: Temporada (lista única)
    if 'temporada' in df.columns:
        temporadas_unicas = sorted(df['temporada'].dropna().astype(str).unique())
        selected_temporada = col2.selectbox("Seleccionar Temporada", options=temporadas_unicas)
    else:
        st.error("No se encontró la columna 'temporada' en los datos.")
        selected_temporada = None

    # Aplicar filtro de equipo y temporada para actualizar las jornadas disponibles
    filtered_df = df.copy()
    if equip_filter and 'equip' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['equip'].astype(str).str.lower().str.contains(equip_filter.lower(), na=False)]
        
    if selected_temporada:
        filtered_df = filtered_df[filtered_df['temporada'].astype(str) == selected_temporada]

    # Filtro 3: Jornada (multiselección)
    if 'jornada' in filtered_df.columns:
        jornadas_disponibles = sorted(filtered_df['jornada'].dropna().unique())
        selected_jornadas = col3.multiselect("Seleccionar Jornada(s)", options=jornadas_disponibles, default=jornadas_disponibles)
        if selected_jornadas:
            filtered_df = filtered_df[filtered_df['jornada'].isin(selected_jornadas)]
    else:
        st.error("No se encontró la columna 'jornada' en los datos.")

    st.write(f"**Registros encontrados:** {len(filtered_df)}")

    # Validar presencia de columnas clave para la tabla dinámica
    col_jugador = next((c for c in ['jugador', 'jugadors', 'nom'] if c in filtered_df.columns), None)
    col_ordre = next((c for c in ['ordre', 'orden'] if c in filtered_df.columns), None)
    col_total = next((c for c in ['total', 'totalc'] if c in filtered_df.columns), None)

    if col_jugador and col_ordre and col_total and not filtered_df.empty:
        # --- TABLA DINÁMICA ---
        pivot_df = filtered_df.pivot_table(
            index=col_ordre, 
            columns=col_jugador, 
            values=col_total, 
            aggfunc='sum', 
            fill_value=0
        )

        # Calcular fila resumen (suma por columna) y ordenar columnas descendentemente
        resumen_fila = pivot_df.sum(axis=0)
        orden_columnas = resumen_fila.sort_values(ascending=False).index
        pivot_df = pivot_df[orden_columnas]
        
        # Añadir la columna de resumen horizontal
        pivot_df['Total Resumen'] = pivot_df.sum(axis=1)

        # Añadir la fila de resumen general al final
        fila_resumen_dict = pivot_df.sum(axis=0).to_dict()
        fila_resumen_df = pd.DataFrame(fila_resumen_dict, index=['Total Resumen'])
        pivot_completo = pd.concat([pivot_df, fila_resumen_df])

        st.subheader("Tabla Dinámica Interactiva (Jugador vs Órdenes sobre Total)")
        st.info("Haz clic en una celda de la tabla para ver el desglose detallado de los registros correspondientes.")

        # Evento de selección interactiva
        event = st.dataframe(
            pivot_completo,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-cell"
        )

        # --- DETALLE AL HACER CLIC EN UNA CASILLA ---
        if event and event.selection and event.selection.rows and event.selection.columns:
            selected_row_idx = event.selection.rows[0]
            selected_col_idx = event.selection.columns[0]

            row_label = pivot_completo.index[selected_row_idx]
            col_label = pivot_completo.columns[selected_col_idx]

            # Filtrar los registros base según la casilla seleccionada
            detalle_df = filtered_df.copy()

            if str(row_label) != 'Total Resumen':
                detalle_df = detalle_df[detalle_df[col_ordre] == row_label]
            
            if str(col_label) != 'Total Resumen':
                detalle_df = detalle_df[detalle_df[col_jugador] == col_label]

            # Ordenar descendentemente por la variable 'ddmmaa' (fecha)
            col_fecha = next((c for c in ['ddmmaa', 'fecha'] if c in detalle_df.columns), None)
            if col_fecha:
                detalle_df[col_fecha] = pd.to_datetime(detalle_df[col_fecha], errors='coerce')
                detalle_df = detalle_df.sort_values(by=col_fecha, ascending=False)

            st.markdown("---")
            st.subheader(f"Desglose de registros: Jugador [{col_label}] - Órden [{row_label}]")

            # Selector interactivo (multiselect) de columnas a visualizar
            todas_columnas = list(detalle_df.columns)
            cols_defecto = [c for c in [col_fecha, col_jugador, col_ordre, col_total, 'jornada', 'temporada'] if c in todas_columnas]
            
            selected_display_cols = st.multiselect(
                "⚙️ Escoger variables/columnas a mostrar en la lista:",
                options=todas_columnas,
                default=cols_defecto if cols_defecto else todas_columnas
            )

            if selected_display_cols:
                st.dataframe(detalle_df[selected_display_cols], use_container_width=True)
            else:
                st.warning("Selecciona al menos una columna para mostrar la información.")
    else:
        st.warning("No se encontraron los datos necesarios para generar la tabla dinámica con los filtros actuales.")

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")