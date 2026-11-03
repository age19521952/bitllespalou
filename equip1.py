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

    # --- FORMATRE DE DATA ROBUST (dd/mm/aaaa) ---
    col_fecha_orig = next((c for c in ['ddmmaa', 'fecha', 'data', 'date'] if c in df.columns), None)
    if col_fecha_orig:
        parsed_dates = pd.to_datetime(df[col_fecha_orig], errors='coerce')
        df[col_fecha_orig] = parsed_dates.dt.strftime('%d/%m/%Y').fillna('—')
    
    # --- ZONA DE FILTROS ---
    col1, col2, col3 = st.columns(3)
    
    equip_filter = col1.text_input("Filtrar per Equip", value="palou")

    if 'temporada' in df.columns:
        temporadas_unicas = sorted(df['temporada'].dropna().astype(str).unique())
        selected_temporada = col2.selectbox("Seleccionar Temporada", options=temporadas_unicas)
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
        filtered_df['__ordre_str__'] = filtered_df[col_ordre].astype(str).str.strip()
        filtered_df['__jugador_key__'] = filtered_df[col_jugador].astype(str).str.strip().str.lower()

        # --- CONFECCIÓ DE LA MATRIU ---
        jugMap = {}
        ordresSet = set()

        for _, row in filtered_df.iterrows():
            jug = str(row[col_jugador]).strip().upper()
            ord_val = row['__ordre_str__']
            ordresSet.add(ord_val)
            
            if jug not in jugMap:
                jugMap[jug] = {}
            if ord_val not in jugMap[jug]:
                jugMap[jug][ord_val] = {'sum': 0.0, 'count': 0}
            
            val = row[col_total]
            if not pd.isna(val):
                jugMap[jug][ord_val]['sum'] += float(val)
                jugMap[jug][ord_val]['count'] += 1

        try:
            ordresList = sorted(list(ordresSet), key=lambda x: int(float(x)))
        except Exception:
            ordresList = sorted(list(ordresSet))

        rowAverages = {}
        for jug, jObj in jugMap.items():
            r_sum, r_cnt = 0.0, 0
            for ord in ordresList:
                if ord in jObj:
                    r_sum += jObj[ord]['sum']
                    r_cnt += jObj[ord]['count']
            if r_cnt > 0:
                rowAverages[jug] = {'avg': r_sum / r_cnt, 'count': r_cnt}
            else:
                rowAverages[jug] = {'avg': 0.0, 'count': 0}

        jugadorsList = sorted(jugMap.keys(), key=lambda j: rowAverages[j]['avg'], reverse=True)

        colAverages = {}
        for ord in ordresList:
            c_sum, c_cnt = 0.0, 0
            for jug in jugadorsList:
                if ord in jugMap[jug]:
                    c_sum += jugMap[jug][ord]['sum']
                    c_cnt += jugMap[jug][ord]['count']
            if c_cnt > 0:
                colAverages[ord] = {'avg': round(c_sum / c_cnt, 2), 'count': c_cnt}
            else:
                colAverages[ord] = None

        totalRegistres = len(filtered_df)
        globalSum = filtered_df[col_total].sum()
        mitjanaTotalGlobal = round(globalSum / totalRegistres, 2) if totalRegistres > 0 else 0.0

        st.subheader("Taula Dinàmica Interactiva (Jugadores / Órdes)")

        table_data = []
        for jug in jugadorsList:
            row_dict = {"Jugador": jug}
            for ord in ordresList:
                cell = jugMap[jug].get(ord)
                if cell and cell['count'] > 0:
                    row_dict[str(ord)] = f"{(cell['sum']/cell['count']):.2f} ({cell['count']})"
                else:
                    row_dict[str(ord)] = "-"
            
            tot = rowAverages[jug]
            row_dict["Total Resumen"] = f"{tot['avg']:.2f} ({tot['count']})" if tot['count'] > 0 else "-"
            table_data.append(row_dict)

        summary_row = {"Jugador": "Total Resumen"}
        for ord in ordresList:
            cRes = colAverages.get(ord)
            if cRes:
                summary_row[str(ord)] = f"{cRes['avg']:.2f} ({cRes['count']})"
            else:
                summary_row[str(ord)] = "-"
        summary_row["Total Resumen"] = f"{mitjanaTotalGlobal:.2f} ({totalRegistres})"
        table_data.append(summary_row)

        final_display_df = pd.DataFrame(table_data)

        st.dataframe(final_display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🔍 Selector de Desglossament per Casella")
        
        col_sel1, col_sel2 = st.columns(2)
        sel_jugador_opt = col_sel1.selectbox("Selecciona Jugador:", options=["-- Tria un jugador --"] + jugadorsList + ["Total Resumen"])
        sel_ordre_opt = col_sel2.selectbox("Selecciona Ordre / Resum:", options=["Total Resumen"] + [str(o) for o in ordresList])

        # --- MOSTRAR RESULTATS DEL DETALL ---
        if sel_jugador_opt and sel_jugador_opt != "-- Tria un jugador --":
            detalle_df = filtered_df.copy()
            if sel_jugador_opt != "Total Resumen":
                detalle_df = detalle_df[detalle_df['__jugador_key__'] == sel_jugador_opt.lower()]
            
            if sel_ordre_opt != "Total Resumen":
                detalle_df = detalle_df[detalle_df['__ordre_str__'] == str(sel_ordre_opt)]

            st.markdown(f"### 📋 Desglossament | Jugador: [{sel_jugador_opt}] - Ordre: [{sel_ordre_opt}]")
            st.caption(f"Registros trobats: {len(detalle_df)}")

            if not detalle_df.empty:
                # Ordenar las columnas estrictamente como en la foto de referencia
                desired_order = [col_fecha_orig, 'temporada', 'jornada', 'np', 'partit', col_jugador, col_total, 'totalc', 'punts', col_ordre]
                todas_columnas = [c for c in detalle_df.columns if c not in ['__jugador_key__', '__ordre_str__']]
                
                # Filtrar solo las que existan realmente en el DataFrame para evitar errores
                default_cols_ordered = [c for c in desired_order if c and c in todas_columnas]
                # Añadir cualquier otra columna restante que no estuviera en la lista fija
                for c in todas_columnas:
                    if c not in default_cols_ordered:
                        default_cols_ordered.append(c)

                selected_display_cols = st.multiselect(
                    "⚙️ Triar variables a mostrar:",
                    options=default_cols_ordered,
                    default=default_cols_ordered,
                    key="multiselect_detalle_casilla_final"
                )

                if selected_display_cols:
                    st.dataframe(detalle_df[selected_display_cols], use_container_width=True)
            else:
                st.warning("No hi ha registres individuals disponibles per a aquesta combinació.")

    else:
        st.warning("No s'han trobat les dades necessàries amb els filtres actuals.")

except Exception as e:
    st.error(f"Error al carregar o processar el fitxer Excel: {e}")
