import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import t
import io
import re
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Analizador Bitlles Palou", layout="wide")

st.title("Analizador Bitlles Palou")

# --- ESTILOS CSS PARA CONGELAR INTERFAZ Y RECTIFICAR LA TABLA ---
st.markdown("""
    <style>
    /* Fijar la cabecera (header) superior de Streamlit */
    header[data-testid="stHeader"] {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        z-index: 999;
    }
    
    /* Congelar y fijar las cabeceras de los dataframes */
    [data-testid="stDataFrame"] div[role="grid"] {
        max-height: 450px;
        overflow-y: auto;
    }
    
    [data-testid="stDataFrame"] div[role="columnheader"] {
        position: sticky;
        top: 0;
        background-color: #1e1e1e !important;
        z-index: 10;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/age19521952/bitllespalou/main/bitllespalou.xlsx"
    return pd.read_excel(url)

def extraer_media(val_str):
    """Extrae el valor numérico de la media contenido en cadenas tipo '12.34 (5)'."""
    if not isinstance(val_str, str):
        return float(val_str) if pd.notna(val_str) else 0.0
    match = re.match(r"^([0-9]+\.?[0-9]*)", val_str.strip())
    if match:
        return float(match.group(1))
    return 0.0

def generar_pdf(df_export, titulo="Tabla Dinámica - Bitlles Palou"):
    """Genera un archivo PDF landscape compactado ajustando el ancho de columnas y padding."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=12, leading=14, alignment=1)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=6.5, leading=7.5, alignment=1)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=7.5, leading=8.5, alignment=1, fontName="Helvetica-Bold", textColor=colors.white)

    story.append(Paragraph(titulo, title_style))
    story.append(Spacer(1, 8))

    headers = ["Jugador"] + list(df_export.columns)
    data = [[Paragraph(h, header_style) for h in headers]]

    for row_name, row in df_export.iterrows():
        row_data = [Paragraph(str(row_name), cell_style)]
        for val in row:
            row_data.append(Paragraph(str(val), cell_style))
        data.append(row_data)

    # --- DEFINIR ANCHOS COMPACTADOS DE COLUMNA ---
    num_cols = len(headers)
    col_widths = [110] + [45] * (num_cols - 1)

    t_table = Table(data, colWidths=col_widths, repeatRows=1)
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f2f2f2')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e6ecf2')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    
    story.append(t_table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

try:
    df = load_data()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # --- NORMALIZAR NOMBRES DE JUGADORES ---
    col_jugador_raw = next((c for c in ['jugador', 'jugadors', 'nom'] if c in df.columns), None)
    if col_jugador_raw:
        df[col_jugador_raw] = df[col_jugador_raw].astype(str).str.strip().str.title()

    # --- ZONA DE FILTROS ---
    col1, col2, col3 = st.columns(3)
    equip_filter = col1.text_input("Filtrar por Equip", value="palou")

    if 'temporada' in df.columns:
        temporadas_unicas = sorted(df['temporada'].dropna().astype(str).unique())
        selected_temporada = col2.selectbox("Seleccionar Temporada", options=temporadas_unicas)
    else:
        st.error("No se encontró la columna 'temporada' en los datos.")
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
        st.error("No se encontró la columna 'jornada' en los datos.")
        selected_jornadas = []

    st.write(f"**Registros encontrados:** {len(filtered_df)}")

    col_jugador = next((c for c in ['jugador', 'jugadors', 'nom'] if c in filtered_df.columns), None)
    col_ordre = next((c for c in ['ordre', 'orden'] if c in filtered_df.columns), None)
    col_total = next((c for c in ['total', 'totalc'] if c in filtered_df.columns), None)

    if col_jugador and col_ordre and col_total and not filtered_df.empty:
        filtered_df[col_ordre] = pd.to_numeric(filtered_df[col_ordre], errors='coerce')

        # --- TABLA DINÁMICA ---
        pivot_mean = filtered_df.pivot_table(index=col_jugador, columns=col_ordre, values=col_total, aggfunc='mean', fill_value=0)
        pivot_count = filtered_df.pivot_table(index=col_jugador, columns=col_ordre, values=col_total, aggfunc='count', fill_value=0)

        orden_cols = sorted([c for c in pivot_mean.columns if pd.notna(c)], key=lambda x: int(x))
        pivot_mean = pivot_mean[orden_cols]
        pivot_count = pivot_count[orden_cols]

        display_df = pd.DataFrame(index=pivot_mean.index)
        
        # 1. Rellenar columnas de órdenes individuales (1 a 5, reserves, entreno)
        for c in orden_cols:
            c_int = int(c)
            if c_int == 9:
                col_name = 'reserves'
            elif c_int == 10:
                col_name = 'entreno'
            else:
                col_name = str(c_int)

            display_df[col_name] = [
                f"{pivot_mean.loc[r, c]:.2f} ({int(pivot_count.loc[r, c])})" if pivot_count.loc[r, c] > 0 else "-"
                for r in pivot_mean.index
            ]

        # 2. Calcular Lliga Pura (Exclusivamente órdenes 1, 2, 3, 4, 5)
        df_lliga_filtered = filtered_df[filtered_df[col_ordre].isin([1, 2, 3, 4, 5])]
        resumen_lliga_mean = df_lliga_filtered.groupby(col_jugador)[col_total].mean()
        resumen_lliga_count = df_lliga_filtered.groupby(col_jugador)[col_total].count()
        
        lliga_series = [
            f"{resumen_lliga_mean.loc[r]:.2f} ({int(resumen_lliga_count.loc[r])})" if r in resumen_lliga_mean and resumen_lliga_count.loc[r] > 0 else "-"
            for r in pivot_mean.index
        ]

        if 'entreno' not in display_df.columns:
            display_df['entreno'] = "-"

        # --- ORDENAR COLUMNAS INTERCAMBIANDO 'Lliga' TRAS LA COLUMNA '5' ---
        cols_actuales = list(display_df.columns)
        nuevas_cols_orden = []
        for c in cols_actuales:
            nuevas_cols_orden.append(c)
            if c == '5':
                nuevas_cols_orden.append('Lliga')
        
        if 'Lliga' not in nuevas_cols_orden:
            nuevas_cols_orden.append('Lliga')

        # Reconstruir dataframe temporal con el orden deseado
        temp_ordered_df = pd.DataFrame(index=display_df.index)
        for c in nuevas_cols_orden:
            if c == 'Lliga':
                temp_ordered_df['Lliga'] = lliga_series
            else:
                if c in display_df.columns:
                    temp_ordered_df[c] = display_df[c]
        display_df = temp_ordered_df

        # --- CÁLCULO DE RANKING (PONDERACIÓN: Titulares 100%, Reserves 80%, Entreno 50%) ---
        ranking_vals = []
        ic_lower_list = []

        for r in display_df.index:
            df_jugador = filtered_df[filtered_df[col_jugador] == r]
            
            df_titular = df_jugador[df_jugador[col_ordre].isin([1, 2, 3, 4, 5])]
            df_reserva = df_jugador[df_jugador[col_ordre] == 9]
            df_entreno = df_jugador[df_jugador[col_ordre] == 10]
            
            n_tit = len(df_titular)
            n_res = len(df_reserva)
            n_entr = len(df_entreno)
            
            val_tit = df_titular[col_total].values if n_tit > 0 else np.array([])
            val_res = df_reserva[col_total].values if n_res > 0 else np.array([])
            val_entr = df_entreno[col_total].values if n_entr > 0 else np.array([])
            
            peso_res = 0.8  # 80% peso para reservas
            peso_entr = 0.5 # 50% peso para entrenos
            
            n_efectivo = n_tit + (n_res * peso_res) + (n_entr * peso_entr)
            
            suma_tit = val_tit.sum() if n_tit > 0 else 0
            suma_res = (val_res.sum() * peso_res) if n_res > 0 else 0
            suma_entr = (val_entr.sum() * peso_entr) if n_entr > 0 else 0
            
            if n_efectivo > 0:
                media_ponderada = (suma_tit + suma_res + suma_entr) / n_efectivo
                
                todos_los_datos = np.concatenate([v for v in [val_tit, val_res, val_entr] if len(v) > 0])
                n_total = len(todos_los_datos)
                
                if n_total > 1:
                    std_dev = np.std(todos_los_datos, ddof=1)
                    t_crit = t.ppf(0.975, df=n_total - 1)
                    ic_inf = media_ponderada - (t_crit * (std_dev / np.sqrt(n_total)))
                else:
                    ic_inf = media_ponderada
                    
                ranking_vals.append(media_ponderada)
                ic_lower_list.append(max(0, ic_inf))
            else:
                ranking_vals.append(0.0)
                ic_lower_list.append(0.0)

        display_df['Ranking'] = [f"{v:.2f}" if v > 0 else "-" for v in ranking_vals]
        display_df['IC 95% Inf'] = [f"{v:.2f}" if v > 0 else "-" for v in ic_lower_list]

        #display_df['temp_rank'] = ranking_vals
        display_df['temp_rank'] = ic_lower_list
        display_df = display_df.sort_values(by='temp_rank', ascending=False).drop(columns=['temp_rank'])

        # --- RESUMEN VERTICAL (Por Orden) ---
        resumen_orden_mean = filtered_df.groupby(col_ordre)[col_total].mean()
        resumen_orden_count = filtered_df.groupby(col_ordre)[col_total].count()
        
        fila_resumen_vals = {}
        for c in orden_cols:
            c_int = int(c)
            col_name = 'reserves' if c_int == 9 else ('entreno' if c_int == 10 else str(c_int))
            fila_resumen_vals[col_name] = f"{resumen_orden_mean.loc[c]:.2f} ({int(resumen_orden_count.loc[c])})" if c in resumen_orden_mean else "-"

        total_lliga_general_mean = df_lliga_filtered[col_total].mean() if not df_lliga_filtered.empty else 0
        total_lliga_general_count = df_lliga_filtered[col_total].count() if not df_lliga_filtered.empty else 0
        fila_resumen_vals['Lliga'] = f"{total_lliga_general_mean:.2f} ({int(total_lliga_general_count)})" if total_lliga_general_count > 0 else "-"

        tot_lliga_val = extraer_media(fila_resumen_vals.get('Lliga', '0'))
        tot_entreno_val = extraer_media(fila_resumen_vals.get('entreno', '0'))
        if tot_lliga_val > 0 and tot_entreno_val > 0:
            tot_ranking = (tot_lliga_val * 0.7) + (tot_entreno_val * 0.3)
        elif tot_lliga_val > 0:
            tot_ranking = tot_lliga_val
        elif tot_entreno_val > 0:
            tot_ranking = tot_entreno_val
        else:
            tot_ranking = 0.0

        fila_resumen_vals['Ranking'] = f"{tot_ranking:.2f}" if tot_ranking > 0 else "-"

        total_general_mean = filtered_df[col_total].mean() if not filtered_df.empty else 0
        total_general_count = filtered_df[col_total].count() if not filtered_df.empty else 0
        total_general_std = filtered_df[col_total].std(ddof=1) if total_general_count > 1 else 0
        
        if total_general_count > 1:
            t_crit_tot = t.ppf(0.975, df=total_general_count-1)
            total_ic_inf = total_general_mean - (t_crit_tot * (total_general_std / np.sqrt(total_general_count)))
        else:
            total_ic_inf = total_general_mean

        fila_resumen_vals['IC 95% Inf'] = f"{max(0, total_ic_inf):.2f}" if total_general_count > 0 else "-"

        fila_resumen_df = pd.DataFrame([{col: fila_resumen_vals.get(col, "-") for col in display_df.columns}], index=['Total Resumen'])
        display_completo = pd.concat([display_df, fila_resumen_df])

        # --- CABECERA SECCIÓN Y DESCARGA PDF ---
        c_title, c_pdf = st.columns([3, 1])
        c_title.subheader("Tabla Dinámica Compacta (Jugador vs Órdenes)")
        
        # Título dinámico del PDF con las jornadas seleccionadas
        jornadas_str = ", ".join(map(str, selected_jornadas)) if selected_jornadas else "Todas"
        titulo_pdf = f"Tabla Dinámica - Bitlles Palou - Jornades: {jornadas_str}"
        
        pdf_bytes = generar_pdf(display_completo, titulo=titulo_pdf)
        c_pdf.download_button(
            label="📄 Descargar Tabla en PDF",
            data=pdf_bytes,
            file_name="tabla_dinamica_bitlles_palou.pdf",
            mime="application/pdf"
        )

        st.dataframe(display_completo, use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Desglose detallado por Jugador y Orden")

        col_sel1, col_sel2 = st.columns(2)
        lista_jugadores = ["Todos"] + list(display_df.index)
        lista_ordens = ["Todos"] + [str(int(c)) for c in orden_cols]

        sel_jugador_filtro = col_sel1.selectbox("Seleccionar Jugador para desglose:", options=lista_jugadores)
        sel_orden_filtro = col_sel2.selectbox("Seleccionar Orden para desglose:", options=lista_ordens)

        detalle_df = filtered_df.copy()

        if sel_jugador_filtro != "Todos":
            detalle_df = detalle_df[detalle_df[col_jugador] == sel_jugador_filtro]
        
        if sel_orden_filtro != "Todos":
            detalle_df = detalle_df[detalle_df[col_ordre] == int(sel_orden_filtro)]

        col_fecha = next((c for c in ['ddmmaa', 'fecha'] if c in detalle_df.columns), None)
        if col_fecha:
            detalle_df['temp_dt'] = pd.to_datetime(detalle_df[col_fecha], format='%d/%m/%Y', errors='coerce')
            mask_nat = detalle_df['temp_dt'].isna() & detalle_df[col_fecha].notna()
            if mask_nat.any():
                detalle_df.loc[mask_nat, 'temp_dt'] = pd.to_datetime(detalle_df.loc[mask_nat, col_fecha], errors='coerce')

            detalle_df = detalle_df.sort_values(by='temp_dt', ascending=False, na_position='last')
            detalle_df[col_fecha] = detalle_df['temp_dt'].dt.strftime('%d/%m/%Y').fillna('Sin Fecha')
            detalle_df = detalle_df.drop(columns=['temp_dt'])

        st.write(f"**Registros en el desglose:** {len(detalle_df)}")

        columnas_deseadas = ['ddmmaa', 'temporada', 'jornada', 'np', 'partit', 'jugador', 'total', 'totalc', 'punts', 'ordre']
        cols_a_mostrar = [c for c in columnas_deseadas if c in detalle_df.columns]

        if cols_a_mostrar:
            num_filas = len(detalle_df)
            altura_tabla = min(max(100, (num_filas + 1) * 35 + 10), 800) if num_filas > 0 else 100
            st.dataframe(detalle_df[cols_a_mostrar], use_container_width=True, height=altura_tabla)
        else:
            st.warning("No se encontraron las columnas especificadas para mostrar el desglose.")
    else:
        st.warning("No se encontraron los datos necesarios para generar la tabla dinámica con los filtros actuales.")

except Exception as e:
    st.error(f"Error al cargar o procesar el fichero Excel: {e}")
