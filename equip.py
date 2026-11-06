import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import t
import io
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

def generar_pdf(df_export, titulo="Tabla Dinámica - Bitlles Palou"):
    """Genera un archivo PDF landscape compactado con la tabla de resumen."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter),
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=16, alignment=1)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7, leading=8, alignment=1)
    header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8, leading=9, alignment=1, fontName="Helvetica-Bold", textColor=colors.white)

    story.append(Paragraph(titulo, title_style))
    story.append(Spacer(1, 10))

    # Preparar datos para la tabla ReportLab
    data = []
    headers = ["Jugador"] + list(df_export.columns)
    data.append([Paragraph(h, header_style) for h in headers])

    for row_name, row in df_export.iterrows():
        row_data = [Paragraph(str(row_name), cell_style)]
        for val in row:
            row_data.append(Paragraph(str(val), cell_style))
        data.append(row_data)

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f77b4')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f2f2f2')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#e6ecf2')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    
    story.append(t)
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

        display_df = pd.DataFrame(index=pivot_mean.index, columns=[str(int(c)) for c in pivot_mean.columns])
        
        for r in pivot_mean.index:
            for c in pivot_mean.columns:
                m_val = pivot_mean.loc[r, c]
                c_val = int(pivot_count.loc[r, c])
                display_df.loc[r, str(int(c))] = f"{m_val:.2f} ({c_val})" if c_val > 0 else "0.00 (0)"

        # --- CÁLCULO DE RESUMEN Y IC 95% INFERIOR (CON T DE STUDENT) ---
        resumen_jugador_mean = filtered_df.groupby(col_jugador)[col_total].mean()
        resumen_jugador_count = filtered_df.groupby(col_jugador)[col_total].count()
        resumen_jugador_std = filtered_df.groupby(col_jugador)[col_total].std(ddof=1).fillna(0)

        ic_lower_list = []
        for r in display_df.index:
            m = resumen_jugador_mean.get(r, 0)
            n = resumen_jugador_count.get(r, 0)
            s = resumen_jugador_std.get(r, 0)
            
            if n > 1:
                t_crit = t.ppf(0.975, df=n-1)
                ic_inf = m - (t_crit * (s / np.sqrt(n)))
            else:
                ic_inf = m
                
            ic_lower_list.append(max(0, ic_inf))

        display_df['Total Resumen'] = [
            f"{resumen_jugador_mean.loc[r]:.2f} ({int(resumen_jugador_count.loc[r])})" if r in resumen_jugador_mean else "0.00 (0)"
            for r in display_df.index
        ]
        
        display_df['IC 95% Inf'] = [f"{v:.2f}" for v in ic_lower_list]

        if not resumen_jugador_mean.empty:
            sorted_jugadores = resumen_jugador_mean.sort_values(ascending=False).index
            display_df = display_df.reindex([j for j in sorted_jugadores if j in display_df.index])

        # --- RESUMEN VERTICAL (Por Orden) ---
        resumen_orden_mean = filtered_df.groupby(col_ordre)[col_total].mean()
        resumen_orden_count = filtered_df.groupby(col_ordre)[col_total].count()
        
        fila_resumen_vals = {}
        for c in pivot_mean.columns:
            fila_resumen_vals[str(int(c))] = f"{resumen_orden_mean.loc[c]:.2f} ({int(resumen_orden_count.loc[c])})" if c in resumen_orden_mean else "0.00 (0)"
        
        total_general_mean = filtered_df[col_total].mean()
        total_general_count = filtered_df[col_total].count()
        total_general_std = filtered_df[col_total].std(ddof=1)
        
        if total_general_count > 1:
            t_crit_tot = t.ppf(0.975, df=total_general_count-1)
            total_ic_inf = total_general_mean - (t_crit_tot * (total_general_std / np.sqrt(total_general_count)))
        else:
            total_ic_inf = total_general_mean

        fila_resumen_vals['Total Resumen'] = f"{total_general_mean:.2f} ({int(total_general_count)})" if total_general_count > 0 else "0.00 (0)"
        fila_resumen_vals['IC 95% Inf'] = f"{max(0, total_ic_inf):.2f}" if total_general_count > 0 else "0.00"

        fila_resumen_df = pd.DataFrame([fila_resumen_vals], index=['Total Resumen'])
        display_completo = pd.concat([display_df, fila_resumen_df])

        # --- CABECERA SECCIÓN Y DESCARGA PDF ---
        c_title, c_pdf = st.columns([3, 1])
        c_title.subheader("Tabla Dinámica Compacta (Jugador vs Órdenes)")
        
        pdf_bytes = generar_pdf(display_completo)
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