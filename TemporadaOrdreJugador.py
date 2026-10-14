import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
st.title("Estadístiques Bitlles Palou — Taula i Gràfiques Interactives")

@st.cache_data
def carregar_dades():
    excel_filename = "bitllespalou.xlsx"
    xls = pd.ExcelFile(excel_filename)
    df_list = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    df_all = pd.concat(df_list, ignore_index=True)
    
    palou_df = df_all[df_all['equip'].astype(str).str.strip().str.upper() == 'PALOU'].copy()
    palou_df['total'] = pd.to_numeric(palou_df['total'], errors='coerce')
    palou_df['temporada'] = palou_df['temporada'].astype(str)
    palou_df['ordre'] = pd.to_numeric(palou_df['ordre'], errors='coerce')
    palou_df['np'] = pd.to_numeric(palou_df['np'], errors='coerce').fillna(1).astype(int)
    
    if 'ddmmaa' in palou_df.columns:
        palou_df['ddmmaa'] = pd.to_datetime(palou_df['ddmmaa'], errors='coerce')
        
    return palou_df

try:
    palou_df = carregar_dades()
except Exception as e:
    st.error(f"No s'ha pogut carregar el fitxer 'bitllespalou.xlsx': {e}")
    st.stop()

# Taula dinàmica resum
pivot_df = pd.pivot_table(palou_df, values='total', index='ordre', columns='temporada', aggfunc='mean').round(2)
st.subheader("Taula Dinàmica: Mitjana de Punts (Ordre vs Temporada)")
st.dataframe(pivot_df, use_container_width=True)

st.sidebar.header("Filtres")
temporades = sorted(palou_df['temporada'].dropna().unique())
sel_temp = st.sidebar.selectbox("Selecciona Temporada:", temporades)

ordres_disp = sorted(palou_df['ordre'].dropna().unique())
sel_ordres = st.sidebar.multiselect("Selecciona Ordre(s):", ordres_disp, default=[ordres_disp[0]] if ordres_disp else [])

sub_df_temp = palou_df[(palou_df['temporada'] == sel_temp) & (palou_df['ordre'].isin(sel_ordres))]
jugadors_disp = ['Tots'] + sorted(sub_df_temp['jugador'].dropna().astype(str).unique().tolist())
sel_jugador = st.sidebar.selectbox("Selecciona Jugador:", jugadors_disp)

if not sel_ordres:
    st.warning("Selecciona almenys un ordre a la barra lateral.")
else:
    sub_df = sub_df_temp.copy()
    
    # Calcular mitjanes per ordre per a la llegenda
    sub_df_per_mitjana = sub_df.copy()
    if sel_jugador != 'Tots':
        sub_df_per_mitjana = sub_df_per_mitjana[sub_df_per_mitjana['jugador'].astype(str) == sel_jugador]
    mitjanes_ordres = sub_df_per_mitjana.groupby('ordre')['total'].mean()

    if sel_jugador != 'Tots':
        sub_df = sub_df[sub_df['jugador'].astype(str) == sel_jugador]

    if sub_df.empty:
        st.info("No hi ha dades per a la selecció actual.")
    else:
        # Ordenació cronològica estricta ascendent
        sort_cols = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df.columns and not sub_df['ddmmaa'].isna().all() else ['jornada', 'np']
        sub_df = sub_df.sort_values(by=sort_cols, ascending=[True, True])

        fig, ax = plt.subplots(figsize=(13, 6))
        
        colors_disponibles = plt.cm.tab10(np.linspace(0, 1, len(sel_ordres)))
        estils_linia = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
        
        ordre_color_map = {ordre: colors_disponibles[i] for i, ordre in enumerate(sel_ordres)}
        ordre_estil_map = {ordre: estils_linia[i % len(estils_linia)] for i, ordre in enumerate(sel_ordres)}
        
        jugadors = sub_df['jugador'].dropna().unique()
        
        for jugador in jugadors:
            df_jugador = sub_df[sub_df['jugador'] == jugador].dropna(subset=['total'])
            
            if df_jugador.empty:
                continue
            
            if 'ddmmaa' in df_jugador.columns and not df_jugador['ddmmaa'].isna().all():
                eix_x_str = df_jugador['ddmmaa'].dt.strftime('%d/%m/%Y') + ' (P' + df_jugador['np'].astype(str) + ')'
            else:
                eix_x_str = 'Jor. ' + df_jugador['jornada'].astype(str) + ' (P' + df_jugador['np'].astype(str) + ')'
            
            eix_y = df_jugador['total'].values
            ordres_jugador = df_jugador['ordre'].values
            x_vals = np.arange(len(df_jugador))
            
            if sel_jugador == 'Tots':
                col_def = ordre_color_map.get(ordres_jugador[0], '#1E88E5')
                estil_def = ordre_estil_map.get(ordres_jugador[0], '-')
                ax.plot(x_vals, eix_y, marker='o', linestyle=estil_def, linewidth=2, markersize=6, 
                         color=col_def, label=str(jugador))
                for i, txt in enumerate(eix_y):
                    ax.annotate(f"{int(txt)}", (x_vals[i], eix_y[i]), 
                                 textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=col_def)
            else:
                for i in range(len(df_jugador)):
                    ordre_actual = ordres_jugador[i]
                    col_actual = ordre_color_map.get(ordre_actual, '#1E88E5')
                    
                    ax.plot(x_vals[i], eix_y[i], marker='o', markersize=6, color=col_actual)
                    ax.annotate(f"{int(eix_y[i])}", (x_vals[i], eix_y[i]), 
                                 textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=col_actual)
                    
                    if i < len(df_jugador) - 1:
                        ordre_seg = ordres_jugador[i+1]
                        col_seg = ordre_color_map.get(ordre_seg, col_actual)
                        estil_seg = ordre_estil_map.get(ordre_seg, '-')
                        ax.plot([x_vals[i], x_vals[i+1]], [eix_y[i], eix_y[i+1]], linestyle=estil_seg, linewidth=2.5, color=col_seg)

                mitjana_jugador = eix_y.mean()
                ax.axhline(mitjana_jugador, color='gray', linestyle=':', linewidth=1.5, 
                            label=f"Mitjana Global: {mitjana_jugador:.2f}")

                if len(eix_y) > 1:
                    z = np.polyfit(x_vals, eix_y, 1)
                    p = np.poly1d(z)
                    ax.plot(x_vals, p(x_vals), color='black', linestyle='-', linewidth=1, alpha=0.7, 
                             label="Tendència Lineal Global")

            ax.set_xticks(x_vals)
            ax.set_xticklabels(eix_x_str, rotation=45, ha='right')

        for ordre, color in ordre_color_map.items():
            estil = ordre_estil_map.get(ordre, '-')
            mitjana_val = mitjanes_ordres.get(ordre, np.nan)
            etiqueta_ordre = f"Ordre {ordre} (Mitjana: {mitjana_val:.2f})" if not np.isnan(mitjana_val) else f"Ordre {ordre}"
            ax.plot([], [], marker='o', color=color, linestyle=estil, linewidth=2, label=etiqueta_ordre)

        ordres_str = ", ".join(map(str, sel_ordres))
        ax.set_title(f"Evolució Temporal Cronològica — Temporada: {sel_temp} | Ordre(s): {ordres_str} | Jugador: {sel_jugador}", fontsize=12, fontweight='bold')
        ax.set_xlabel("Data i Partida (np) [Ordre Cronològic]", fontsize=10)
        ax.set_ylabel("Punts (Total)", fontsize=10)
        ax.legend(title="Llegenda", bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        st.pyplot(fig)

        # Botó de descàrrega directa per a WhatsApp
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
        buf.seek(0)
        
        st.download_button(
            label="📥 Descarregar gràfica per WhatsApp",
            data=buf,
            file_name="grafica_bitlles_palou.png",
            mime="image/png"
        )