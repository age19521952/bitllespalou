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
        # Asegurar tipo numérico en total y estandarizar clave de jugador
        filtered_df[col_total] = pd.to_numeric(filtered_df[col_total], errors='coerce')
        
        # Convertir la columna de ordre de forma segura a numérico si es posible, o mantenerla limpia
        filtered_df[col_ordre] = pd.to_numeric(filtered_df[col_ordre], errors='coerce')
        
        filtered_df['__jugador_key__'] = filtered_df[col_jugador].astype(str).str.strip().str.lower()

        # --- CONFECCIÓN DE LA TABLA DINÁMICA ---
        pivot_mean = filtered_df.pivot_table(index='__jugador_key__', columns=col_ordre, values=col_total, aggfunc='mean')
        pivot_count = filtered_df.pivot_table(index='__jugador_key__', columns=col_ordre, values=col_total, aggfunc='count').fillna(0).astype(int)

        resumen_jugador_mean = filtered_df.groupby('__jugador_key__')[col_total].mean()
        resumen_jugador_count = filtered_df.groupby('__jugador_key__')[col_total].count()

        orden_jugadores = resumen_jugador_mean.sort_values(ascending=False).index
        
        pivot_mean = pivot_mean.reindex(orden_jugadores)
        pivot_count = pivot_count.reindex(orden_jugadores)
        resumen_jugador_mean = resumen_jugador_mean.reindex(orden_jugadores)
        resumen_jugador_count = resumen_jugador_count.reindex(orden_jugadores)

        resumen_ordre_mean = filtered_df.groupby(col_ordre)[col_total].mean()
        resumen_ordre_count = filtered_df.groupby(col_ordre)[col_total].count()

        display_data = []
        # Ordenar las columnas numéricamente de forma segura (ej: 1, 2, 3... 9, 10)
        raw_cols = list(pivot_mean.columns)
        try:
            col_names = sorted(raw_cols, key=lambda x: float(x))
        except Exception:
            col_names = sorted(raw_cols, key=lambda x: str(x))

        for jugador_key in orden_jugadores:
            row_dict = {"Jugador": str(jugador_key).upper()}
            for col in col_names:
                m = pivot_mean.loc[jugador_key, col]
                c = pivot_count.loc[jugador_key, col]
                if pd.isna(m) or c == 0:
                    row_dict[str(col)] = "-"
                else:
                    row_dict[str(col)] = f"{m:.2f} ({int(c)})"
            
            tot_m = resumen_jugador_mean[jugador_key]
            tot_c = resumen_jugador_count[jugador_key]
            row_dict["Total Resumen"] = f"{tot_m:.2f} ({int(tot_c)})" if not pd.isna(tot_m) else "-"
            display_data.append(row_dict)

        display_df = pd.DataFrame(display_data)

        # Fila resumen general al final
        row_resumen_dict = {"Jugador": "Total Resumen"}
        for col in col_names:
            m = resumen_ordre_mean[col]
            c = resumen_ordre_count[col]
            row_resumen_dict[str(col)] = f"{m:.2f} ({int(c)})" if not pd.isna(m) else "-"
        
        global_m = filtered_df[col_total].mean()
        global_c = filtered_df[col_total].count()
        row_resumen_dict["Total Resumen"] = f"{global_m:.2f} ({int(global_c)})" if not pd.isna(global_m) else "-"

        resumen_fila_df = pd.DataFrame([row_resumen_dict])
        tabla_final = pd.concat([display_df, resumen_fila_df], ignore_index=True)

        st.subheader("Tabla Dinámica Interactiva (Jugadores / Órdes)")
        st.info("Haz clic en cualquier celda de la tabla para ver el desglose de registros.")

        # --- TABLA INTERACTIVA ---
        event = st.dataframe(
            tabla_final,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-cell"
        )

        r_idx, c_idx = None, None

        if event and hasattr(event, "selection") and event.selection:
            cells = event.selection.get("cells", [])
            if cells and len(cells) > 0:
                first_cell = cells[0]
                if isinstance(first_cell, (list, tuple)) and len(first_cell) >= 2:
                    r_idx, c_idx = int(first_cell[0]), int(first_cell[1])
            
            if r_idx is None or c_idx is None:
                rows = event.selection.get("rows", [])
                cols = event.selection.get("columns", [])
                if rows and cols and len(rows) > 0 and len(cols) > 0:
                    r_idx, c_idx = int(rows[0]), int(cols[0])

        if r_idx is not None and c_idx is not None:
            if 0 <= r_idx < len(tabla_final) and 0 <= c_idx < len(tabla_final.columns):
                row_label = str(tabla_final.iloc[r_idx]["Jugador"])
                col_label = str(tabla_final.columns[c_idx])

                if col_label == "Jugador":
                    st.info("💡 Has seleccionado la casilla de nombre del jugador. Haz clic en una celda de puntuación para ver los datos de esa casilla.")
                else:
                    detalle_df = filtered_df.copy()

                    # 1. Filtrar por Jugador (si no es la fila de resumen general)
                    if row_label != "Total Resumen":
                        detalle_df = detalle_df[detalle_df['__jugador_key__'] == row_label.lower()]

                    # 2. Filtrar por Órden de forma totalmente blindada (evitando errores en 9, 10 y Total Resumen)
                    if col_label != "Total Resumen":
                        matched_val = None
                        for orig_c in col_names:
                            if str(orig_c) == col_label:
                                matched_val = orig_c
                                break
                        
                        if matched_val is not None:
                            detalle_df = detalle_df[detalle_df[col_ordre] == matched_val]
                        else:
                            try:
                                num_val = float(col_label)
                                if num_val.is_integer():
                                    num_val = int(num_val)
                                detalle_df = detalle_df[detalle_df[col_ordre] == num_val]
                            except Exception:
                                detalle_df = detalle_df[detalle_df[col_ordre].astype(str) == col_label]
                    # Si se hace clic en "Total Resumen", no se filtra por orden, mostrando todos los registros acumulados.

                    # 3. Ordenar por Fecha (ddmmaa) Descendentemente
                    col_fecha = next((c for c in ['ddmmaa', 'fecha'] if c in detalle_df.columns), None)
                    if col_fecha:
                        detalle_df[col_fecha] = pd.to_datetime(detalle_df[col_fecha], errors='coerce')
                        detalle_df = detalle_df.sort_values(by=col_fecha, ascending=False)

                    st.markdown("---")
                    st.subheader(f"📋 Desglose de Registros | Jugador: [{row_label}] - Órdes: [{col_label}]")
                    st.caption(f"Registros en esta casilla: {len(detalle_df)}")

                    if not detalle_df.empty:
                        todas_columnas = [c for c in detalle_df.columns if c != '__jugador_key__']
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
                        st.warning("No hay registros individuales disponibles para esta combinación.")
    else:
        st.warning("No se encontraron los datos necesarios con los filtros actuales.")

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")
