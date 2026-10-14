import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
st.title("Evolució Bitlles Palou — Doble Eix Y (Punts Partit vs. Acumulats)")

@st.cache_data
def carregar_dades():
    excel_filename = "bitllespalou.xlsx"
    xls = pd.ExcelFile(excel_filename)
    df_list = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    df_all = pd.concat(df_list, ignore_index=True)
    
    df_all['temporada'] = df_all['temporada'].astype(str)
    df_all['ordre'] = pd.to_numeric(df_all['ordre'], errors='coerce')
    df_all['np'] = pd.to_numeric(df_all['np'], errors='coerce').fillna(1).astype(int)
    
    # Mantenir la jornada com a string o netejar decimals si són numèrics
    if 'jornada' in df_all.columns:
        df_all['jornada'] = df_all['jornada'].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    if 'ddmmaa' in df_all.columns:
        df_all['ddmmaa'] = pd.to_datetime(df_all['ddmmaa'], errors='coerce')
        
    return df_all

try:
    df_all = carregar_dades()
except Exception as e:
    st.error(f"No s'ha pogut carregar el fitxer 'bitllespalou.xlsx': {e}")
    st.stop()

# --- FILTRES A LA BARRA LATERAL ---
st.sidebar.header("Filtres d'Anàlisi")

equips_disp = sorted(df_all['equip'].dropna().astype(str).str.strip().unique().tolist())
equip_defaut = 'PALOU' if 'PALOU' in equips_disp else equips_disp[0]
sel_equip = st.sidebar.selectbox("Selecciona Equip:", equips_disp, index=equips_disp.index(equip_defaut))

df_equip = df_all[df_all['equip'].astype(str).str.strip().str.upper() == sel_equip.upper()]
temporades = sorted(df_equip['temporada'].dropna().unique())
sel_temp = st.sidebar.selectbox("Selecciona Temporada:", temporades)

df_temp_filtered = df_equip[df_equip['temporada'] == sel_temp]

# Obtenir totes les jornades disponibles (incloses lletres com P, I, F, etc.)
if 'jornada' in df_temp_filtered.columns:
    jornades_disp = sorted(df_temp_filtered['jornada'].dropna().astype(str).unique().tolist())
else:
    jornades_disp = []

# Filtre múltiple de Jornada obert a qualsevol valor
sel_jornades = st.sidebar.multiselect(
    "Selecciona Jornada(s):", 
    options=jornades_disp, 
    default=jornades_disp
)

sub_df = df_temp_filtered[
    (df_temp_filtered['ordre'].isin([1, 2, 3, 4, 5])) & 
    (df_temp_filtered['jornada'].isin(sel_jornades))
].copy()

def es_valor_valid(val):
    if pd.isna(val):
        return False
    v_str = str(val).strip().lower().replace('.', ',')
    return v_str in ['cero', '0', '0,0', '0,2', '0,4']

if 'punts' in sub_df.columns:
    sub_df = sub_df[sub_df['punts'].apply(es_valor_valid)].copy()

if sub_df.empty:
    st.warning("No hi ha dades de titulars amb els criteris de selecció actuals.")
else:
    group_cols = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df.columns and not sub_df['ddmmaa'].isna().all() else ['jornada', 'np']
    
    def convertir_punts(val):
        v_str = str(val).strip().lower()
        if v_str == 'cero' or v_str == '':
            return 0.0
        try:
            return float(v_str.replace(',', '.'))
        except:
            return 0.0

    sub_df['punts_num'] = sub_df['punts'].apply(convertir_punts)

    if 'partit' in sub_df.columns:
        df_partits = sub_df.groupby(group_cols, as_index=False).agg({
            'punts_num': 'sum', 
            'partit': 'first'
        })
        df_partits['partit_str'] = df_partits['partit'].astype(str)
    else:
        df_partits = sub_df.groupby(group_cols, as_index=False).agg({
            'punts_num': 'sum'
        })
        df_partits['partit_str'] = "Partit " + df_partits['np'].astype(str)

    df_partits = df_partits.sort_values(by=group_cols, ascending=[True, True]).reset_index(drop=True)

    df_partits['p_real'] = df_partits['punts_num']
    df_partits['p_ideal'] = 2.0  
    
    df_partits['p_real_acum'] = df_partits['p_real'].cumsum()
    df_partits['p_ideal_acum'] = df_partits['p_ideal'].cumsum()

    eix_x_str = df_partits['partit_str'] + ' (P' + df_partits['np'].astype(str) + ')'
    x_vals = np.arange(len(df_partits))

    total_reals = df_partits['p_real_acum'].iloc[-1] if not df_partits.empty else 0
    total_ideals = df_partits['p_ideal_acum'].iloc[-1] if not df_partits.empty else 0
    eficiencia = (total_reals / total_ideals) * 100 if total_ideals > 0 else 0

    # --- VISUALITZACIÓ DE KPIs A STREAMLIT ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Suma Punts Reals Acumulats", f"{total_reals:.1f} pts")
    col2.metric("Suma Punts Màxims Possibles (Ideal)", f"{total_ideals:.1f} pts")
    col3.metric("Eficiència Global", f"{eficiencia:.1f}%")

    st.markdown("---")

    # --- CREACIÓ DE LA GRÀFICA AMB EIX ESQUERRE LIMITAT A 0, 1, 2 ---
    fig, ax1 = plt.subplots(figsize=(13, 6.5))

    color_esq = '#1E88E5'
    ax1.set_xlabel("Partit i Partida (np) [Ordre Cronològic]", fontsize=10)
    ax1.set_ylabel("Punts Partit (Eix Esquerre)", color=color_esq, fontsize=10, fontweight='bold')
    
    ax1.set_yticks([0, 1, 2])
    ax1.set_ylim(-0.2, 2.2)

    line1 = ax1.plot(x_vals, df_partits['p_real'], color=color_esq, marker='o', linewidth=2, 
                     label="Punts Reals (Partit a Partit)")
    ax1.tick_params(axis='y', labelcolor=color_esq)

    for i, txt in enumerate(df_partits['p_real']):
        ax1.annotate(f"{int(txt)}", 
                     (x_vals[i], df_partits['p_real'][i]), 
                     textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=color_esq)

    ax2 = ax1.twinx()  
    color_dret_real = '#2E7D32'
    color_dret_ideal = '#E53935'
    ax2.set_ylabel("Punts Acumulats (Eix Dret)", color=color_dret_real, fontsize=10, fontweight='bold')

    line2 = ax2.plot(x_vals, df_partits['p_real_acum'], color=color_dret_real, marker='s', linewidth=2.5, 
                     linestyle='-', label="Punts Reals Acumulats")
    line3 = ax2.plot(x_vals, df_partits['p_ideal_acum'], color=color_dret_ideal, marker='^', linewidth=2, 
                     linestyle='--', label="Escenari Ideal Acumulat (Màxim)")
    
    ax2.tick_params(axis='y', labelcolor=color_dret_real)

    ax1.set_xticks(x_vals)
    ax1.set_xticklabels(eix_x_str, rotation=45, ha='right')

    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', bbox_to_anchor=(0.02, 0.90))

    text_kpis = f"Punts Reals: {total_reals:.1f} pts   |   Punts Ideals: {total_ideals:.1f} pts   |   Eficiència: {eficiencia:.1f}%"
    fig.suptitle(text_kpis, fontsize=12, fontweight='bold', color='#1E88E5', y=0.97)

    ax1.grid(True, linestyle='--', alpha=0.4)
    fig.tight_layout(rect=[0, 0, 1, 0.94])

    st.pyplot(fig)

    # Botó de descàrrega directa per a WhatsApp
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    
    st.download_button(
        label="📥 Descarregar gràfica amb KPIs per WhatsApp",
        data=buf,
        file_name=f"doble_eix_punts_{sel_equip}_{sel_temp}.png",
        mime="image/png"
    )