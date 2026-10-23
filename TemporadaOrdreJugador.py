import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(
    page_title="Bitlles Palou — AWWARDS Edition",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estils CSS optimitzats per a màxima visibilitat vertical i estil AWWARDS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    h3 {
        margin-top: 0rem !important;
        padding-top: 0.2rem !important;
        font-size: 1.3rem !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_dades():
    excel_filename = "bitllespalou.xlsx"
    xls = pd.ExcelFile(excel_filename)
    df_list = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    df_all = pd.concat(df_list, ignore_index=True)
    
    palou_df = df_all[df_all['equip'].astype(str).str.strip().str.upper() == 'PALOU'].copy()
    palou_df['total'] = pd.to_numeric(palou_df['total'], errors='coerce')
    palou_df['temporada'] = palou_df['temporada'].astype(str).str.strip()
    palou_df['ordre'] = pd.to_numeric(palou_df['ordre'], errors='coerce')
    palou_df['np'] = pd.to_numeric(palou_df['np'], errors='coerce').fillna(1).astype(int)
    
    # Normalització estricta de majúscules/minúscules per evitar duplicitats de noms
    palou_df['jugador'] = palou_df['jugador'].astype(str).str.strip().str.title()
    
    if 'ddmmaa' in palou_df.columns:
        palou_df['ddmmaa'] = pd.to_datetime(palou_df['ddmmaa'], errors='coerce')
        
    return palou_df

try:
    palou_df = carregar_dades()
except Exception as e:
    st.error(f"No s'ha pogut carregar el fitxer 'bitllespalou.xlsx': {e}")
    st.stop()

# Inicialitzar estat de sessió
if 'selected_cell_t1' not in st.session_state:
    st.session_state.selected_cell_t1 = None
if 'selected_ordres_t2' not in st.session_state:
    st.session_state.selected_ordres_t2 = []

# --- PAS 1: TAULA DINÀMICA JUGADOR / TEMPORADA ---
st.markdown("### 📊 Pas 1: Taula Dinàmica (Jugador vs Temporada)")

pivot_t1 = pd.pivot_table(
    palou_df, 
    values='total', 
    index='jugador', 
    columns='temporada', 
    aggfunc='mean',
    margins=True,
    margins_name='Mitjana Global'
).round(1)

pivot_t1_display = pivot_t1.fillna('-')

num_rows = len(pivot_t1_display)
calculated_height = (num_rows + 1) * 35 + 10

event_t1 = st.dataframe(
    pivot_t1_display,
    use_container_width=True,
    height=calculated_height,
    on_select="rerun",
    selection_mode="single-cell",
    key="tabla_t1"
)

if event_t1 and event_t1.selection and event_t1.selection.get('cells'):
    cell_info = event_t1.selection['cells'][0]
    row_idx = cell_info[0]
    col_idx = cell_info[1]
    try:
        selected_jugador = str(pivot_t1.index[row_idx])
        if isinstance(col_idx, int):
            selected_temporada = str(pivot_t1.columns[col_idx])
        else:
            selected_temporada = str(col_idx)
            
        if selected_jugador != 'Mitjana Global' and selected_temporada != 'Mitjana Global':
            st.session_state.selected_cell_t1 = (selected_jugador, selected_temporada)
            st.session_state.selected_ordres_t2 = []
    except Exception:
        pass

current_t1 = st.session_state.get('selected_cell_t1', None)

if current_t1:
    selected_jugador, selected_temporada = current_t1
    
    st.markdown(f"""
    <div style="background: rgba(56, 189, 248, 0.1); border-left: 4px solid #38bdf8; padding: 0.6rem 1rem; border-radius: 8px; margin: 0.5rem 0;">
        <b>🎯 Selecció activa:</b> Jugador: <span style="color: #38bdf8;">{selected_jugador}</span> | Temporada: <span style="color: #38bdf8;">{selected_temporada}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # --- PAS 2: TAULA DINÀMICA JUGADOR / ORDRE AMB MITJANA I RECOMPTE (MULTICASSELLA) ---
    st.markdown("---")
    st.markdown("### 📋 Pas 2: Taula Dinàmica (Jugador vs Ordre — Mitjana i N d'observacions)")
    st.markdown("<p style='color: #94a3b8; font-size: 0.9rem;'>S'indica la <b>Mitjana (n=Registres)</b> en cada casella. Pots seleccionar múltiples ordres per analitzar la seva evolució conjunta.</p>", unsafe_allow_html=True)
    
    df_filtrat_t2 = palou_df[
        (palou_df['temporada'] == selected_temporada) & 
        (palou_df['jugador'] == selected_jugador)
    ]
    
    if not df_filtrat_t2.empty:
        pivot_mean = pd.pivot_table(
            df_filtrat_t2, values='total', index='jugador', columns='ordre', aggfunc='mean'
        ).round(1)
        
        pivot_count = pd.pivot_table(
            df_filtrat_t2, values='total', index='jugador', columns='ordre', aggfunc='count'
        ).fillna(0).astype(int)
        
        pivot_t2_combined = pd.DataFrame(index=pivot_mean.index, columns=pivot_mean.columns)
        for col in pivot_mean.columns:
            m_val = pivot_mean[col].values[0]
            c_val = pivot_count[col].values[0]
            if pd.isna(m_val):
                pivot_t2_combined[col] = '-'
            else:
                pivot_t2_combined[col] = f"{m_val:.1f} (n={c_val})"

        m_global = df_filtrat_t2['total'].mean()
        c_global = df_filtrat_t2['total'].count()
        pivot_t2_combined['Mitjana Total'] = f"{m_global:.1f} (n={c_global})" if c_global > 0 else '-'

        ordres_disponibles = [col for col in pivot_t2_combined.columns if col != 'Mitjana Total']

        st.dataframe(pivot_t2_combined, use_container_width=True)

        selected_ordres = st.multiselect(
            "📍 Selecciona una o diverses caselles (Ordres) per generar la gràfica de barres:",
            options=ordres_disponibles,
            default=st.session_state.selected_ordres_t2 if st.session_state.selected_ordres_t2 else [ordres_disponibles[0]] if ordres_disponibles else []
        )
        st.session_state.selected_ordres_t2 = selected_ordres

        # --- PAS 3: GRÀFICA D'EVOLUCIÓ TEMPORAL AMB ANTISOLAPAMENT DE ETIQUETES ---
        if selected_ordres:
            st.markdown("---")
            st.markdown("### 📈 Pas 3: Gràfica d'Evolució Temporal (Barres, Partit i Mitjana Acumulada)")
            
            ordres_floats = [float(o) for o in selected_ordres]
            df_grafica = df_filtrat_t2[df_filtrat_t2['ordre'].isin(ordres_floats)].copy()
            
            if not df_grafica.empty:
                sort_cols = ['ddmmaa', 'np'] if 'ddmmaa' in df_grafica.columns and not df_grafica['ddmmaa'].isna().all() else ['jornada', 'np']
                df_grafica = df_grafica.sort_values(by=sort_cols, ascending=[True, True])
                
                # Calcular la mitjana acumulada
                df_grafica['mitjana_acumulada'] = df_grafica['total'].expanding().mean().round(1)
                
                if 'ddmmaa' in df_grafica.columns and not df_grafica['ddmmaa'].isna().all():
                    eix_x_labels = df_grafica['ddmmaa'].dt.strftime('%d/%m/%Y') + ' [O:' + df_grafica['ordre'].astype(int).astype(str) + ' P' + df_grafica['np'].astype(str) + ']'
                else:
                    eix_x_labels = 'Jor. ' + df_grafica['jornada'].astype(str) + ' [O:' + df_grafica['ordre'].astype(int).astype(str) + ' P' + df_grafica['np'].astype(str) + ']'
                    
                eix_y_vals = df_grafica['total'].values
                mitjana_acum_vals = df_grafica['mitjana_acumulada'].values
                
                partit_col = 'partit' if 'partit' in df_grafica.columns else ('rival' if 'rival' in df_grafica.columns else None)
                partit_vals = df_grafica[partit_col].fillna('').astype(str).values if partit_col else [''] * len(df_grafica)
                
                x_pos = np.arange(len(df_grafica))
                
                plt.style.use('dark_background')
                fig, ax = plt.subplots(figsize=(13, 6.5))
                fig.patch.set_facecolor('#0f172a')
                ax.set_facecolor('#1e1b4b')
                
                bars = ax.bar(x_pos, eix_y_vals, color='#38bdf8', alpha=0.85, width=0.55, edgecolor='#818cf8', linewidth=1.5)
                
                # Etiquetes de punts damunt de cada barra
                for bar in bars:
                    height = bar.get_height()
                    if not np.isnan(height):
                        ax.annotate(
                            f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 4),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=9, fontweight='bold', color='#f8fafc'
                        )
                
                # Text del partit DINTRE de cada barra
                for i, bar in enumerate(bars):
                    height = bar.get_height()
                    txt_partit = partit_vals[i]
                    if txt_partit and not np.isnan(height) and height > 0:
                        ax.text(
                            bar.get_x() + bar.get_width() / 2,
                            height / 2,
                            txt_partit,
                            ha='center', va='center',
                            rotation=90,
                            fontsize=8, fontweight='bold', color='#ffffff',
                            clip_on=True
                        )

                # Línia de Mitjana Acumulada
                ax.plot(x_pos, mitjana_acum_vals, color='#34d399', linestyle='-', linewidth=2.5, marker='o', markersize=6, label='Mitjana Acumulada')
                
                # Etiquetes de la mitjana acumulada ben espaiades per evitar solapaments
                for idx, val in enumerate(mitjana_acum_vals):
                    if not np.isnan(val):
                        ax.annotate(
                            f'{val:.1f}',
                            xy=(x_pos[idx], val),
                            xytext=(0, 18),  # Desplaçament vertical major per evitar xocar amb la barra
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=9, fontweight='bold', color='#34d399',
                            bbox=dict(boxstyle="round,pad=0.25", fc="#0f172a", ec="#34d399", lw=1, alpha=0.9)
                        )
                
                # Ampliar el marge superior del gràfic automàticament per encabir totes les etiquetes sense talls
                max_val = max(max(eix_y_vals), max(mitjana_acum_vals))
                ax.set_ylim(0, max_val * 1.25)
                        
                ax.set_xticks(x_pos)
                ax.set_xticklabels(eix_x_labels, rotation=45, ha='right', color='#94a3b8', fontsize=9)
                
                ordres_str = ", ".join(map(str, selected_ordres))
                ax.set_title(f"Evolució Temporal — Jugador: {selected_jugador} | Temporada: {selected_temporada} | Ordre(s): {ordres_str}", fontsize=12, fontweight='bold', color='#f8fafc', pad=15)
                ax.set_xlabel("Data / Jornada [Ordre i Partida]", fontsize=10, color='#cbd5e1', labelpad=8)
                ax.set_ylabel("Punts (Total)", fontsize=10, color='#cbd5e1', labelpad=8)
                
                legend = ax.legend(facecolor='#0f172a', edgecolor='#334155', loc='upper left')
                for text in legend.get_texts():
                    text.set_color('#cbd5e1')
                    
                ax.grid(True, linestyle='--', alpha=0.15, color='#cbd5e1', axis='y')
                plt.tight_layout()
                
                st.pyplot(fig)
                
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
                buf.seek(0)
                st.download_button(
                    label="📥 Descarregar gràfica en alta definició",
                    data=buf,
                    file_name="grafica_barres_mitjana_acumulada.png",
                    mime="image/png"
                )
            else:
                st.info("No s'han trobat partides registrades per als ordres seleccionats.")
        else:
            st.info("👆 Selecciona almenys un ordre per generar la gràfica de barres.")
    else:
        st.warning(f"No hi ha registres disponibles per a {selected_jugador} a la temporada {selected_temporada}.")
else:
    st.info("👆 Fes clic a qualsevol casella de la Taula 1 (Jugador vs Temporada) per començar.")