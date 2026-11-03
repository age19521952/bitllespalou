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
    
    # Normalitzar noms de columnes a minúscules
    df.columns = [str(c).strip().lower() for c in df.columns]

    # --- ZONA DE FILTROS ---
    col1, col2, col3 = st.columns(3)
    
    equip_filter = col1.text_input("Filtrar per Equip", value="palou")

    if 'temporada' in df.columns:
        temporades_unicas = sorted(df['temporada'].dropna().astype(str).unique())
        selected_temporada = col2.selectbox("Seleccionar Temporada", options=temporades_unicas)
    else:
        st.error("No s'ha trobat la columna 'temporada' a les dades.")
        selected_temporada = None

    filtered_df = df.copy()
    if equip_filter and 'equip' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['equip'].astype(str).str.lower().str.contains(equip_filter.lower(), na=False)]
        
    if selected_temporada:
        filtered_df = filtered_df[filtered_df['temporada'].astype(str) == selected_temporada]

    if 'jornada' in filtered_df.columns:
        jornadas_disponibles = sorted(filtered_df['jornada'].dropna().unique())
        selected_jornadas = col3.multiselect("Seleccionar Jornada(s)", options=jornadas_disponibles, default=jornadas_disponibles)
        if selected_jornadas:
            filtered_df = filtered_df[filtered_df['jornada'].isin(selected_jornadas)]
    else:
        st.error("No s'ha trobat la columna 'jornada' a les dades.")

    st.write(f"**Registres trobats:** {len(filtered_df)}")

    col_jugador = next((c for c in ['jugador', 'jugadors', 'nom'] if c in filtered_df.columns), None)
    col_ordre = next((c for c in ['ordre', 'orden'] if c in filtered_df.columns), None)
    col_total = next((c for c in ['total', 'totalc'] if c in filtered_df.columns), None)

    if col_jugador and col_ordre and col_total and not filtered_df.empty:
        filtered_df[col_total] = pd.to_numeric(filtered_df[col_total], errors='coerce')
        # Mantenim l'ordre com a text/string net per evitar qualsevol conflicte de tipus
        filtered_df['__ordre_str__'] = filtered_df[col_ordre].astype(str).str.strip()
        filtered_df['__jugador_key__'] = filtered_df[col_jugador].astype(str).str.strip().str.lower()

        # --- CONFECCIÓ DE LA TAULA DINÀMICA ---
        pivot_mean = filtered_df.pivot_table(index='__jugador_key__', columns='__ordre_str__', values=col_total, aggfunc='mean')
        pivot_count = filtered_df.pivot_table(index='__jugador_key__', columns='__ordre_str__', values=col_total, aggfunc='count').fillna(0).astype(int)

        resumen_jugador_mean = filtered_df.groupby('__jugador_key__')[col_total].mean()
        resumen_jugador_count = filtered_df.groupby('__jugador_key__')[col_total].count()

        orden_jugadores = resumen_jugador_mean.sort_values(ascending=False).index
        
        pivot_mean = pivot_mean.reindex(orden_jugadores)
        pivot_count = pivot_count.reindex(orden_jugadores)
        resumen_jugador_mean = resumen_jugador_mean.reindex(orden_jugadores)
        resumen_jugador_count = resumen_jugador_count.reindex(orden_jugadores)

        resumen_ordre_mean = filtered_df.groupby('__ordre_str__')[col_total].mean()
        resumen_ordre_count = filtered_df.groupby('__ordre_str__')[col_total].count()

        # Obtenim les columnes d'ordre ordenades numèricament si es pot, o alfabèticament
        raw_cols = [str(c) for c in pivot_mean.columns]
        try:
            col_names = sorted(raw_cols, key=lambda x: int(float(x)))
        except Exception:
            col_names = sorted(raw_cols)

        display_data = []
        for jugador_key in orden_jugadores:
            row_dict = {"Jugador": str(jugador_key).upper()}
            for col in col_names:
                m = pivot_mean.loc[jugador_key, col] if col in pivot_mean.columns else np.nan
                c = pivot_count.loc[jugador_key, col] if col in pivot_count.columns else 0
                if pd.isna(m) or c == 0:
                    row_dict[str(col)] = "-"
                else:
                    row_dict[str(col)] = f"{m:.2f} ({int(c)})"
            
            tot_m = resumen_jugador_mean[jugador_key]
            tot_c = resumen_jugador_count[jugador_key]
            row_dict["Total Resumen"] = f"{tot_m:.2f} ({int(tot_c)})" if not pd.isna(tot_m) else "-"
            display_data.append(row_dict)

        display_df = pd.DataFrame(display_data)

        row_resumen_dict = {"Jugador": "Total Resumen"}
        for col in col_names:
            m = resumen_ordre_mean.get(col, np.nan)
            c = resumen_ordre_count.get(col, 0)
            row_resumen_dict[str(col)] = f"{m:.2f} ({int(c)})" if not pd.isna(m) else "-"
        
        global_m = filtered_df[col_total].mean()
        global_c = filtered_df[col_total].count()
        row_resumen_dict["Total Resumen"] = f"{global_m:.2f} ({int(global_c)})" if not pd.isna(global_m) else "-"

        resumen_fila_df = pd.DataFrame([row_resumen_dict])
        tabla_final = pd.concat([display_df, resumen_fila_df], ignore_index=True)

        st.subheader("Tabla Dinámica Interactiva (Jugadores / Órdes)")
        st.info("Fes clic a qualsevol cel·la de la taula per veure el desglossament de registres.")

        # --- GESTIÓ D'ESTAT PER EVITAR BUCLES ---
        if "selected_cell" not in st.session_state:
            st.session_state.selected_cell = None

        event = st.dataframe(
            tabla_final,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-cell",
            key="tabla_dinamica_principal"
        )

        if event and hasattr(event, "selection") and event.selection:
            cells = event.selection.get("cells", [])
            if cells and len(cells) > 0:
                first_cell = cells[0]
                if isinstance(first_cell, (list, tuple)) and len(first_cell) >= 2:
                    r_idx, c_idx = int(first_cell[0]), int(first_cell[1])
                    if 0 <= r_idx < len(tabla_final) and 0 <= c_idx < len(tabla_final.columns):
                        st.session_state.selected_cell = (r_idx, c_idx)

        # --- MOSTRAR DESGLOSE SEGUR SENSE INT() EN "TOTAL RESUMEN" ---
        if st.session_state.selected_cell is not None:
            r_idx, c_idx = st.session_state.selected_cell
            if 0 <= r_idx < len(tabla_final) and 0 <= c_idx < len(tabla_final.columns):
                row_label = str(tabla_final.iloc[r_idx]["Jugador"])
                col_label = str(tabla_final.columns[c_idx])

                if col_label == "Jugador":
                    st.info("💡 Has seleccionat la casella de nom del jugador. Fes clic en una cel·la de puntuació.")
                else:
                    detalle_df = filtered_df.copy()

                    if row_label != "Total Resumen":
                        detalle_df = detalle_df[detalle_df['__jugador_key__'] == row_label.lower()]

                    # FILTRATGE BLINDAT: Si és Total Resumen no filtrem per ordre; si és un ordre, comparem directament com a text
                    if col_label == "Total Resumen":
                        pass
                    else:
                        detalle_df = detalle_df[detalle_df['__ordre_str__'] == col_label]

                    col_fecha = next((c for c in ['ddmmaa', 'fecha'] if c in detalle_df.columns), None)
                    if col_fecha:
                        detalle_df[col_fecha] = pd.to_datetime(detalle_df[col_fecha], errors='coerce')
                        detalle_df = detalle_df.sort_values(by=col_fecha, ascending=False)

                    st.markdown("---")
                    st.subheader(f"📋 Desglossament de Registres | Jugador: [{row_label}] - Ordre: [{col_label}]")
                    st.caption(f"Registres en aquesta casella: {len(detalle_df)}")

                    if not detalle_df.empty:
                        todas_columnas = [c for c in detalle_df.columns if c not in ['__jugador_key__', '__ordre_str__']]
                        cols_defecto = [c for c in [col_fecha, col_jugador, col_ordre, col_total, 'jornada', 'temporada'] if c in todas_columnas]

                        selected_display_cols = st.multiselect(
                            "⚙️ Triar variables/columnas a mostrar a la llista:",
                            options=todas_columnas,
                            default=cols_defecto if cols_defecto else todas_columnas,
                            key="multiselect_detalle_casilla"
                        )

                        if selected_display_cols:
                            st.dataframe(detalle_df[selected_display_cols], use_container_width=True)
                        else:
                            st.warning("Selecciona al menos una columna per mostrar la informació.")
                    else:
                        st.warning("No hi ha registres individuals disponibles per a aquesta combinació.")
    else:
        st.warning("No s'han trobat les dades necessàries amb els filtres actuals.")

except Exception as e:
    st.error(f"Error al carregar o processar el fitxer Excel: {e}")
