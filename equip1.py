import streamlit as st
import pandas as pd
import numpy as np

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
    
    # Filtro 1: Equip
    equip_filter = col1.text_input("Filtrar por Equip", value="palou")

    # Filtro 2: Temporada (lista única)
    if 'temporada' in df.columns:
        temporadas_unicas = sorted(df['temporada'].dropna().astype(str).unique())
        selected_temporada = col2.selectbox("Seleccionar Temporada", options=temporadas_unicas)
    else:
        st.error("No se encontró la columna 'temporada' en los datos.")
        selected_temporada = None

    # Aplicar filtros iniciales
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

    # Validar presencia de columnas clave
    col_jugador = next((c for c in ['jugador', 'jugadors', 'nom'] if c in filtered_df.columns), None)
    col_ordre = next((c for c in ['ordre', 'orden'] if c in filtered_df.columns), None)
    col_total = next((c for c in ['total', 'totalc'] if c in filtered_df.columns), None)

    if col_jugador and col_ordre and col_total and not filtered_df.empty:
        # Asegurar tipo numérico en total
        filtered_df[col_total] = pd.to_numeric(filtered_df[col_total], errors='coerce')

        # --- CONFECCIÓN DE LA TABLA DINÁMICA ---
        pivot_mean = filtered_df.pivot_table(index=col_jugador, columns=col_ordre, values=col_total, aggfunc='mean')
        pivot_count = filtered_df.pivot_table(index=col_jugador, columns=col_ordre, values=col_total, aggfunc='count').fillna(0).astype(int)

        resumen_jugador_mean = filtered_df.groupby(col_jugador)[col_total].mean()
        resumen_jugador_count = filtered_df.groupby(col_jugador)[col_total].count()

        orden_jugadores = resumen_jugador_mean.sort_values(ascending=False).index
        
        pivot_mean = pivot_mean.reindex(orden_jugadores)
        pivot_count = pivot_count.reindex(orden_jugadores)
        resumen_jugador_mean = resumen_jugador_mean.reindex(orden_jugadores)
        resumen_jugador_count = resumen_jugador_count.reindex(orden_jugadores)

        resumen_ordre_mean = filtered_df.groupby(col_ordre)[col_total].mean()
        resumen_ordre_count = filtered_df.groupby(col_ordre)[col_total].count()

        display_data = []
        col_names = list(pivot_mean.columns)

        for jugador in orden_jugadores:
            row_dict = {}
            for col in col_names:
                m = pivot_mean.loc[jugador, col]
                c = pivot_count.loc[jugador, col]
                if pd.isna(m) or c == 0:
                    row_dict[str(col)] = "-"
                else:
                    row_dict[str(col)] = f"{m:.2f} ({int(c)})"
            
            tot_m = resumen_jugador_mean[jugador]
            tot_c = resumen_jugador_count[jugador]
            row_dict["Total Resumen"] = f"{tot_m:.2f} ({int(tot_c)})" if not pd.isna(tot_m) else "-"
            display_data.append(row_dict)

        display_df = pd.DataFrame(display_data, index=orden_jugadores)

        row_resumen_dict = {}
        for col in col_names:
            m = resumen_ordre_mean[col]
            c = resumen_ordre_count[col]
            row_resumen_dict[str(col)] = f"{m:.2f} ({int(c)})" if not pd.isna(m) else "-"
        
        global_m = filtered_df[col_total].mean()
        global_c = filtered_df[col_total].count()
        row_resumen_dict["Total Resumen"] = f"{global_m:.2f} ({int(global_c)})" if not pd.isna(global_m) else "-"

        resumen_fila_df = pd.DataFrame([row_resumen_dict], index=["Total Resumen"])
        tabla_final = pd.concat([display_df, resumen_fila_df])

        st.subheader("Tabla Dinámica Interactiva (Jugadores / Órdes)")
        st.info("Haz clic en cualquier celda de la tabla (incluyendo las de resumen) para ver el desglose de registros.")

        # --- TABLA INTERACTIVA CON CAPTURA DE EVENTO ---
        event = st.dataframe(
            tabla_final,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-cell"
        )

        # --- GESTIÓN DE CLIC EN CASILLA ---
        if event and event.selection and event.selection.rows and event.selection.columns:
            r_idx = event.selection.rows[0]
            c_idx = event.selection.columns[0]

            row_label = tabla_final.index[r_idx]
            col_label = tabla_final.columns[c_idx]

            detalle_df = filtered_df.copy()

            is_row_summary = (str(row_label) == "Total Resumen")
            is_col_summary = (str(col_label) == "Total Resumen")

            # Filtrar según la celda seleccionada (manejando celdas normales y de resumen)
            if not is_row_summary:
                detalle_df = detalle_df[detalle_df[col_jugador] == row_label]
            
            if not is_col_summary:
                try:
                    original_col_type = filtered_df[col_ordre].dtype
                    val_conv = original_col_type.type(col_label)
                except Exception:
                    val_conv = col_label
                detalle_df = detalle_df[detalle_df[col_ordre] == val_conv]

            # Ordenar descendentemente por la variable fecha ('ddmmaa' o 'fecha')
            col_fecha = next((c for c in ['ddmmaa', 'fecha'] if c in detalle_df.columns), None)
            if col_fecha:
                detalle_df[col_fecha] = pd.to_datetime(detalle_df[col_fecha], errors='coerce')
                detalle_df = detalle_df.sort_values(by=col_fecha, ascending=False)

            st.markdown("---")
            st.subheader(f"📋 Desglose de Registros | Jugador: [{row_label}] - Órdes: [{col_label}]")

            todas_columnas = list(detalle_df.columns)
            cols_defecto = [c for c in [col_fecha, col_jugador, col_ordre, col_total, 'jornada', 'temporada'] if c in todas_columnas]

            selected_display_cols = st.multiselect(
                "⚙️ Escoger variables/columnas a mostrar en la lista:",
                options=todas_columnas,
                default=cols_defecto if cols_defecto else todas_columnas,
                key="multiselect_detalle_casilla"
            )

            if selected_display_cols:
                st.dataframe(detalle_df[selected_display_cols], use_container_width=True)
            else:
                st.warning("Selecciona al menos una columna para mostrar la información.")
    else:
        st.warning("No se encontraron los datos necesarios con los filtros actuales.")

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")
