import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
st.title("Estadístiques Bitlles Palou — Suma Total Titulars i Resultats")

@st.cache_data
def carregar_dades():
    excel_filename = "bitllespalou.xlsx"
    xls = pd.ExcelFile(excel_filename)
    df_list = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    df_all = pd.concat(df_list, ignore_index=True)
    
    # Neteja general de columnes numèriques i text
    df_all['equip_str'] = df_all['equip'].astype(str).str.strip().str.upper()
    df_all['total'] = pd.to_numeric(df_all['total'], errors='coerce')
    df_all['punts'] = pd.to_numeric(df_all['punts'], errors='coerce').fillna(0)
    df_all['temporada'] = df_all['temporada'].astype(str)
    df_all['ordre'] = pd.to_numeric(df_all['ordre'], errors='coerce')
    df_all['np'] = pd.to_numeric(df_all['np'], errors='coerce').fillna(1).astype(int)
    
    if 'jornada' in df_all.columns:
        df_all['jornada'] = pd.to_numeric(df_all['jornada'], errors='coerce')
    
    if 'ddmmaa' in df_all.columns:
        df_all['ddmmaa'] = pd.to_datetime(df_all['ddmmaa'], errors='coerce')
        
    return df_all

try:
    df_all = carregar_dades()
except Exception as e:
    st.error(f"No s'ha pogut carregar el fitxer 'bitllespalou.xlsx': {e}")
    st.stop()

# --- FILTRES A LA BARRA LATERAL ---
st.sidebar.header("Filtres")

# 1. Filtre de Temporada
temporades = sorted(df_all['temporada'].dropna().unique())
sel_temp = st.sidebar.selectbox("Selecciona Temporada:", temporades)

# Obtenir les jornades disponibles per a la temporada seleccionada
df_temp_filtered = df_all[df_all['temporada'] == sel_temp]
jornades_disp = sorted(df_temp_filtered['jornada'].dropna().unique()) if 'jornada' in df_temp_filtered.columns else []

# 2. Filtre múltiple de Jornada
sel_jornades = st.sidebar.multiselect(
    "Selecciona Jornada(s):", 
    options=jornades_disp, 
    default=jornades_disp
)

# Filtrar dades de la temporada i jornades per a ordres titulars (1, 2, 3, 4, 5)
sub_df_all = df_temp_filtered[
    (df_temp_filtered['ordre'].isin([1, 2, 3, 4, 5])) & 
    (df_temp_filtered['jornada'].isin(sel_jornades))
].copy()

if sub_df_all.empty:
    st.info("No hi ha dades per a la selecció actual de temporada i jornades.")
else:
    group_cols = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df_all.columns and not sub_df_all['ddmmaa'].isna().all() else ['jornada', 'np']
    
    # Separar Palou i l'altre equip
    sub_palou = sub_df_all[sub_df_all['equip_str'] == 'PALOU']
    sub_rival = sub_df_all[sub_df_all['equip_str'] != 'PALOU']

    # Suma de Palou
    if 'partit' in sub_palou.columns:
        df_suma_palou = sub_palou.groupby(group_cols, as_index=False).agg({
            'total': 'sum', 
            'punts': 'sum', 
            'partit': 'first'
        })
        df_suma_palou['partit_str'] = df_suma_palou['partit'].astype(str)
    else:
        df_suma_palou = sub_palou.groupby(group_cols, as_index=False).agg({
            'total': 'sum',
            'punts': 'sum'
        })
        df_suma_palou['partit_str'] = "Partit " + df_suma_palou['np'].astype(str)

    # Suma de l'altre equip (rival)
    df_suma_rival = sub_rival.groupby(group_cols, as_index=False).agg({
        'total': 'sum'
    }).rename(columns={'total': 'total_rival'})

    # Fusionar les dades de Palou i del rival
    df_suma = pd.merge(df_suma_palou, df_suma_rival, on=group_cols, how='left')
    df_suma['total_rival'] = df_suma['total_rival'].fillna(0)

    # Ordenació cronològica estricta ascendent
    df_suma = df_suma.sort_values(by=group_cols, ascending=[True, True]).reset_index(drop=True)

    # --- CÀLCULS DE PUNTS ACUMULATS, % I MITJANA ACUMULADA ---
    df_suma['acumulat_punts'] = df_suma['punts'].cumsum()
    max_punts_possibles = (df_suma.index + 1) * 2
    df_suma['pct_punts_acumulats'] = (df_suma['acumulat_punts'] / max_punts_possibles) * 100
    
    # Càlcul de la mitjana acumulada de bolos de Palou
    df_suma['mitjana_acumulada_palou'] = df_suma['total'].expanding().mean()

    eix_x_str = df_suma['partit_str'] + ' (P' + df_suma['np'].astype(str) + ')'
    eix_y_palou = df_suma['total'].values
    eix_y_rival = df_suma['total_rival'].values
    eix_punts = df_suma['punts'].values
    eix_acumulat = df_suma['acumulat_punts'].values
    eix_pct = df_suma['pct_punts_acumulats'].values
    eix_mitjana_acum = df_suma['mitjana_acumulada_palou'].values
    x_vals = np.arange(len(df_suma))

    # Obtenir l'últim valor de la mitjana acumulada
    ultima_mitjana_palou = eix_mitjana_acum[-1] if len(eix_mitjana_acum) > 0 else 0.0

    # Taula resum amb les columnes
    st.subheader("Resum Suma Titulars (Ordres 1-5) — Temporada: " + str(sel_temp))
    df_taula_resum = pd.DataFrame({
        'Partit / Partida': eix_x_str,
        'Suma Total Titulars (Palou)': eix_y_palou,
        'Suma Total Titulars (Rival)': eix_y_rival,
        'Suma Punts Partit': eix_punts,
        'Acumulat Punts': eix_acumulat,
        '% Punts Acumulats': eix_pct.round(2).astype(str) + '%',
        'Mitjana Acumulada Palou': eix_mitjana_acum.round(2)
    })
    st.dataframe(df_taula_resum, use_container_width=True, hide_index=True)

    # --- GENERAR LA GRÀFICA DE DOBLE EIX ---
    fig, ax1 = plt.subplots(figsize=(13, 6))
    
    width = 0.38  # Ample de les barres

    # Mapa de colors per a les barres de Palou segons resultat (2 = verd, 1 = blau, 0 = vermell)
    colors_map = {2: '#2E7D32', 1: '#1E88E5', 0: '#D32F2F'}
    colors_palou = [colors_map.get(int(p), '#1E88E5') for p in eix_punts]

    # Eix Esquerre: Barres de Palou i Rival (Punts de boles)
    rects1 = ax1.bar(x_vals - width/2, eix_y_palou, width, color=colors_palou, alpha=0.85, label='Palou (Bolos)')
    rects2 = ax1.bar(x_vals + width/2, eix_y_rival, width, color='#FF7043', alpha=0.85, label='Rival (Bolos)')

    # Etiquetes numèriques damunt de les barres de Palou
    for rect in rects1:
        height = rect.get_height()
        if height > 0:
            ax1.annotate(f"{int(height)}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Etiquetes numèriques damunt de les barres del Rival
    for rect in rects2:
        height = rect.get_height()
        if height > 0:
            ax1.annotate(f"{int(height)}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8, fontweight='bold', color='#D84315')

    # 1. Línia horitzontal d'Objectiu = 355 punts (Eix Esquerre)
    ax1.axhline(355, color='#D32F2F', linestyle='--', linewidth=1.5, label='Objectiu = 355 pts', zorder=3)

    # 2. Línia de la Mitjana Acumulada de Palou (Eix Esquerre)
    ax1.plot(x_vals, eix_mitjana_acum, color='#0288D1', linestyle='-.', linewidth=2, marker='o', markersize=4, label=f"Mitja Acum {ultima_mitjana_palou:.2f}", zorder=4)

    # Fixar el valor mínim de l'eix esquerre a 200
    ax1.set_ylim(bottom=200)

    ax1.set_xlabel("Partit i Partida (np) [Ordre Cronològic]", fontsize=10)
    ax1.set_ylabel("Punts Totals / Bolos (Suma Titulars)", fontsize=10, color='#1F2937')
    ax1.grid(True, linestyle='--', alpha=0.4, axis='y')

    # Eix Dret: Línia / marcadors per als Punts Acumulats de la Classificació
    ax2 = ax1.twinx()
    line_acum = ax2.plot(x_vals, eix_acumulat, color='#6A1B9A', marker='D', linewidth=2, markersize=6, label='Punts Acumulats', zorder=5)
    
    # Etiquetes numèriques als punts acumulats de l'eix dret
    for i in range(len(x_vals)):
        ax2.annotate(f"{int(eix_acumulat[i])} ({eix_pct[i]:.1f}%)", 
                     (x_vals[i], eix_acumulat[i]),
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=8, fontweight='bold', color='#6A1B9A', zorder=6)

    ax2.set_ylabel("Punts Acumulats (Classificació)", fontsize=10, color='#6A1B9A')
    ax2.tick_params(axis='y', labelcolor='#6A1B9A')
    
    # Limitar l'eix dret de manera neta
    max_poss_final = len(df_suma) * 2
    ax2.set_ylim(0, max_poss_final * 1.15)

    # Configuració d'eixos X
    ax1.set_xticks(x_vals)
    ax1.set_xticklabels(eix_x_str, rotation=45, ha='right')

    ax1.set_title("Evolució Titulars (Palou vs Rival) i Punts Acumulats — Temporada: " + str(sel_temp), fontsize=12, fontweight='bold')
    
    # Combinar llegendes de tots dos eixos
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E7D32', alpha=0.85, label='Palou Guanyat (2 pts)'),
        Patch(facecolor='#1E88E5', alpha=0.85, label='Palou Empatat (1 pt)'),
        Patch(facecolor='#D32F2F', alpha=0.85, label='Palou Perdut (0 pts)'),
        Patch(facecolor='#FF7043', alpha=0.85, label='Suma Rival (Bolos)'),
        plt.Line2D([0], [0], color='#D32F2F', linestyle='--', lw=1.5, label='Objectiu = 355 pts'),
        plt.Line2D([0], [0], color='#0288D1', linestyle='-.', lw=2, marker='o', label=f"Mitja Acum {ultima_mitjana_palou:.2f}"),
        plt.Line2D([0], [0], color='#6A1B9A', marker='D', lw=2, label='Punts Acumulats i %')
    ]
    ax1.legend(handles=legend_elements, title="Llegenda", bbox_to_anchor=(1.15, 1), loc='upper left')
    
    plt.tight_layout()

    st.pyplot(fig)

    # Botó de descàrrega directa per a WhatsApp
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    
    st.download_button(
        label="📥 Descarregar gràfica per WhatsApp",
        data=buf,
        file_name="suma_titulars_punts_acumulats_palou.png",
        mime="image/png"
    )
