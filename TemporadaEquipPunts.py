import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide")
st.title("Estadístiques Bitlles Palou — Quadre de Comandament Integral")

@st.cache_data
def carregar_dades():
    excel_filename = "bitllespalou.xlsx"
    xls = pd.ExcelFile(excel_filename)
    df_list = [pd.read_excel(xls, sheet_name=sheet) for sheet in xls.sheet_names]
    df_all = pd.concat(df_list, ignore_index=True)
    
    df_all['total'] = pd.to_numeric(df_all['total'], errors='coerce')
    df_all['temporada'] = df_all['temporada'].astype(str)
    df_all['ordre'] = pd.to_numeric(df_all['ordre'], errors='coerce')
    df_all['np'] = pd.to_numeric(df_all['np'], errors='coerce').fillna(1).astype(int)
    
    if 'jornada' in df_all.columns:
        df_all['jornada'] = pd.to_numeric(df_all['jornada'], errors='coerce')
    
    if 'ddmmaa' in df_all.columns:
        df_all['ddmmaa'] = pd.to_datetime(df_all['ddmmaa'], errors='coerce')
        
    # --- FILTRE GLOBAL DE PUNTS (0, 0.2, 0.4 / 0,2 / 0,4) ---
    def es_valor_valid_global(val):
        if pd.isna(val):
            return False
        v_str = str(val).strip().lower().replace('.', ',')
        return v_str in ['cero', '0', '0,0', '0,2', '0,4']

    if 'punts' in df_all.columns:
        df_all = df_all[df_all['punts'].apply(es_valor_valid_global)].copy()
        
        def convertir_punts(val):
            v_str = str(val).strip().lower()
            if v_str == 'cero' or v_str == '':
                return 0.0
            try:
                return float(v_str.replace(',', '.'))
            except:
                return 0.0
                
        df_all['punts_num'] = df_all['punts'].apply(convertir_punts)
    else:
        df_all['punts_num'] = 0.0

    return df_all

try:
    df_all = carregar_dades()
except Exception as e:
    st.error(f"No s'ha pogut carregar el fitxer 'bitllespalou.xlsx': {e}")
    st.stop()

# --- CREAR LES 3 PESTANYES ---
tab1, tab2, tab3 = st.tabs([
    "📊 Suma Titulars i Resultats", 
    "📈 Doble Eix Y (Reals vs Acumulats)", 
    "👥 Evolució per Ordre i Jugadors"
])

# ==========================================
# PESTANYA 1: Suma Total Titulars i Resultats
# ==========================================
with tab1:
    st.header("Suma Total Titulars (Ordres 1-5) i Resultats")
    
    palou_df_1 = df_all[df_all['equip'].astype(str).str.strip().str.upper() == 'PALOU'].copy()
    temporades_1 = sorted(palou_df_1['temporada'].dropna().unique())
    sel_temp_1 = st.selectbox("Selecciona Temporada (Vista 1):", temporades_1, key="t1")
    
    df_temp_filtered_1 = palou_df_1[palou_df_1['temporada'] == sel_temp_1]
    jornades_disp_1 = sorted(df_temp_filtered_1['jornada'].dropna().unique()) if 'jornada' in df_temp_filtered_1.columns else []
    
    sel_jornades_1 = st.multiselect("Selecciona Jornada(s) (Vista 1):", options=jornades_disp_1, default=jornades_disp_1, key="j1")
    
    sub_df_1 = df_temp_filtered_1[
        (df_temp_filtered_1['ordre'].isin([1, 2, 3, 4, 5])) & 
        (df_temp_filtered_1['jornada'].isin(sel_jornades_1))
    ].copy()
    
    if sub_df_1.empty:
        st.info("No hi ha dades per a la selecció actual.")
    else:
        group_cols_1 = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df_1.columns and not sub_df_1['ddmmaa'].isna().all() else ['jornada', 'np']
        
        if 'partit' in sub_df_1.columns:
            df_suma = sub_df_1.groupby(group_cols_1, as_index=False).agg({'total': 'sum', 'punts_num': 'sum', 'partit': 'first'})
            df_suma['partit_str'] = df_suma['partit'].astype(str)
        else:
            df_suma = sub_df_1.groupby(group_cols_1, as_index=False).agg({'total': 'sum', 'punts_num': 'sum'})
            df_suma['partit_str'] = "Partit " + df_suma['np'].astype(str)

        df_suma = df_suma.sort_values(by=group_cols_1, ascending=[True, True])
        eix_x_str_1 = df_suma['partit_str'] + ' (P' + df_suma['np'].astype(str) + ')'
        eix_y_1 = df_suma['total'].values
        eix_punts_1 = df_suma['punts_num'].values
        x_vals_1 = np.arange(len(df_suma))

        st.subheader(f"Resum Suma Titulars — Temporada: {sel_temp_1}")
        df_taula_resum = pd.DataFrame({
            'Partit / Partida': eix_x_str_1,
            'Suma Total Titulars': eix_y_1,
            'Suma Punts Partit': eix_punts_1
        })
        st.dataframe(df_taula_resum, use_container_width=True, hide_index=True)

        fig1, ax1 = plt.subplots(figsize=(13, 6))
        ax1.plot(x_vals_1, eix_y_1, linestyle='-', linewidth=1.5, color='#B0BEC5', alpha=0.7, zorder=1)

        colors_map = {2: '#2E7D32', 1: '#1E88E5', 0: '#D32F2F'}
        labels_map = {2: 'Guanyat (2 pts)', 1: 'Empatat (1 pt)', 0: 'Perdut (0 pts)'}
        
        for i in range(len(x_vals_1)):
            p_val = eix_punts_1[i]
            color_actual = colors_map.get(int(p_val), '#1E88E5')
            ax1.plot(x_vals_1[i], eix_y_1[i], marker='o', markersize=8, color=color_actual, zorder=3)
            ax1.annotate(f"{int(eix_y_1[i])}", (x_vals_1[i], eix_y_1[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, fontweight='bold', color=color_actual, zorder=4)

        for p_val, col in colors_map.items():
            if p_val in eix_punts_1:
                ax1.plot([], [], marker='o', color=col, markersize=8, linestyle='None', label=labels_map[p_val])

        mitjana_equip = eix_y_1.mean()
        ax1.axhline(mitjana_equip, color='gray', linestyle=':', linewidth=1.5, label=f"Mitjana Global: {mitjana_equip:.2f}", zorder=2)

        if len(eix_y_1) > 1:
            z1 = np.polyfit(x_vals_1, eix_y_1, 1)
            p1 = np.poly1d(z1)
            ax1.plot(x_vals_1, p1(x_vals_1), color='orange', linestyle='--', linewidth=1.5, alpha=0.8, label="Tendència Lineal", zorder=2)

        ax1.set_xticks(x_vals_1)
        ax1.set_xticklabels(eix_x_str_1, rotation=45, ha='right')
        ax1.set_title(f"Evolució Suma Punts Titulars i Resultats — Temporada: {sel_temp_1}", fontsize=12, fontweight='bold')
        ax1.set_xlabel("Partit i Partida (np) [Ordre Cronològic]", fontsize=10)
        ax1.set_ylabel("Punts Totals", fontsize=10)
        ax1.legend(title="Llegenda", bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()

        st.pyplot(fig1)

        buf1 = io.BytesIO()
        fig1.savefig(buf1, format="png", dpi=300, bbox_inches='tight')
        buf1.seek(0)
        st.download_button(
            label="📥 Descarregar gràfica 1 per WhatsApp",
            data=buf1,
            file_name="suma_titulars_resultats_palou.png",
            mime="image/png",
            key="dl1"
        )

# ==========================================
# PESTANYA 2: Doble Eix Y (Reals vs Acumulats)
# ==========================================
with tab2:
    st.header("Evolució Doble Eix Y (Punts Partit vs. Acumulats)")
    
    equips_disp = sorted(df_all['equip'].astype(str).str.strip().unique().tolist())
    equip_defaut = 'PALOU' if 'PALOU' in equips_disp else equips_disp[0]
    sel_equip_2 = st.selectbox("Selecciona Equip (Vista 2):", equips_disp, index=equips_disp.index(equip_defaut), key="eq2")
    
    df_equip_2 = df_all[df_all['equip'].astype(str).str.strip().str.upper() == sel_equip_2.upper()]
    temporades_2 = sorted(df_equip_2['temporada'].dropna().unique())
    sel_temp_2 = st.selectbox("Selecciona Temporada (Vista 2):", temporades_2, key="t2")
    
    df_temp_filtered_2 = df_equip_2[df_equip_2['temporada'] == sel_temp_2]
    jornades_disp_2 = sorted(df_temp_filtered_2['jornada'].dropna().unique()) if 'jornada' in df_temp_filtered_2.columns else []
    
    sel_jornades_2 = st.multiselect("Selecciona Jornada(s) (Vista 2):", options=jornades_disp_2, default=jornades_disp_2, key="j2")
    
    sub_df_2 = df_temp_filtered_2[
        (df_temp_filtered_2['ordre'].isin([1, 2, 3, 4, 5])) & 
        (df_temp_filtered_2['jornada'].isin(sel_jornades_2))
    ].copy()

    if sub_df_2.empty:
        st.warning("No hi ha dades de titulars amb els criteris seleccionats.")
    else:
        group_cols_2 = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df_2.columns and not sub_df_2['ddmmaa'].isna().all() else ['jornada', 'np']
        
        if 'partit' in sub_df_2.columns:
            df_partits = sub_df_2.groupby(group_cols_2, as_index=False).agg({'punts_num': 'sum', 'partit': 'first'})
            df_partits['partit_str'] = df_partits['partit'].astype(str)
        else:
            df_partits = sub_df_2.groupby(group_cols_2, as_index=False).agg({'punts_num': 'sum'})
            df_partits['partit_str'] = "Partit " + df_partits['np'].astype(str)

        df_partits = df_partits.sort_values(by=group_cols_2, ascending=[True, True]).reset_index(drop=True)
        df_partits['p_real'] = df_partits['punts_num']
        df_partits['p_ideal'] = 2.0  
        df_partits['p_real_acum'] = df_partits['p_real'].cumsum()
        df_partits['p_ideal_acum'] = df_partits['p_ideal'].cumsum()

        eix_x_str_2 = df_partits['partit_str'] + ' (P' + df_partits['np'].astype(str) + ')'
        x_vals_2 = np.arange(len(df_partits))

        total_reals = df_partits['p_real_acum'].iloc[-1] if not df_partits.empty else 0
        total_ideals = df_partits['p_ideal_acum'].iloc[-1] if not df_partits.empty else 0
        eficiencia = (total_reals / total_ideals) * 100 if total_ideals > 0 else 0

        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        col_kpi1.metric("Suma Punts Reals Acumulats", f"{total_reals:.1f} pts")
        col_kpi2.metric("Suma Punts Màxims (Ideal)", f"{total_ideals:.1f} pts")
        col_kpi3.metric("Eficiència Global", f"{eficiencia:.1f}%")
        st.markdown("---")

        fig2, ax2_1 = plt.subplots(figsize=(13, 6.5))
        color_esq = '#1E88E5'
        ax2_1.set_xlabel("Partit i Partida (np) [Ordre Cronològic]", fontsize=10)
        ax2_1.set_ylabel("Punts Partit (Eix Esquerre)", color=color_esq, fontsize=10, fontweight='bold')
        ax2_1.set_yticks([0, 1, 2])
        ax2_1.set_ylim(-0.2, 2.2)

        line1 = ax2_1.plot(x_vals_2, df_partits['p_real'], color=color_esq, marker='o', linewidth=2, label="Punts Reals (Partit)")
        ax2_1.tick_params(axis='y', labelcolor=color_esq)

        for i, txt in enumerate(df_partits['p_real']):
            ax2_1.annotate(f"{int(txt)}", (x_vals_2[i], df_partits['p_real'][i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=color_esq)

        ax2_2 = ax2_1.twinx()  
        color_dret_real = '#2E7D32'
        color_dret_ideal = '#E53935'
        ax2_2.set_ylabel("Punts Acumulats (Eix Dret)", color=color_dret_real, fontsize=10, fontweight='bold')

        line2 = ax2_2.plot(x_vals_2, df_partits['p_real_acum'], color=color_dret_real, marker='s', linewidth=2.5, label="Punts Reals Acumulats")
        line3 = ax2_2.plot(x_vals_2, df_partits['p_ideal_acum'], color=color_dret_ideal, marker='^', linewidth=2, linestyle='--', label="Escenari Ideal Acumulat")
        ax2_2.tick_params(axis='y', labelcolor=color_dret_real)

        ax2_1.set_xticks(x_vals_2)
        ax2_1.set_xticklabels(eix_x_str_2, rotation=45, ha='right')

        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax2_1.legend(lines, labels, loc='upper left', bbox_to_anchor=(0.02, 0.90))

        text_kpis = f"Punts Reals: {total_reals:.1f} pts   |   Punts Ideals: {total_ideals:.1f} pts   |   Eficiència: {eficiencia:.1f}%"
        fig2.suptitle(text_kpis, fontsize=12, fontweight='bold', color='#1E88E5', y=0.97)

        ax2_1.grid(True, linestyle='--', alpha=0.4)
        fig2.tight_layout(rect=[0, 0, 1, 0.94])

        st.pyplot(fig2)

        buf2 = io.BytesIO()
        fig2.savefig(buf2, format="png", dpi=300, bbox_inches='tight')
        buf2.seek(0)
        st.download_button(
            label="📥 Descarregar gràfica 2 per WhatsApp",
            data=buf2,
            file_name=f"doble_eix_punts_{sel_equip_2}_{sel_temp_2}.png",
            mime="image/png",
            key="dl2"
        )

# ==========================================
# PESTANYA 3: Evolució per Ordre i Jugadors
# ==========================================
with tab3:
    st.header("Evolució per Ordre i Jugadors")
    
    palou_df_3 = df_all[df_all['equip'].astype(str).str.strip().str.upper() == 'PALOU'].copy()
    pivot_df = pd.pivot_table(palou_df_3, values='total', index='ordre', columns='temporada', aggfunc='mean').round(2)
    st.subheader("Taula Dinàmica: Mitjana de Punts (Ordre vs Temporada)")
    st.dataframe(pivot_df, use_container_width=True)

    temporades_3 = sorted(palou_df_3['temporada'].dropna().unique())
    sel_temp_3 = st.selectbox("Selecciona Temporada (Vista 3):", temporades_3, key="t3")

    ordres_disp = sorted(palou_df_3['ordre'].dropna().unique())
    sel_ordres = st.multiselect("Selecciona Ordre(s):", ordres_disp, default=[ordres_disp[0]] if ordres_disp else [], key="ord3")

    sub_df_temp_3 = palou_df_3[(palou_df_3['temporada'] == sel_temp_3) & (palou_df_3['ordre'].isin(sel_ordres))]
    jugadors_disp = ['Tots'] + sorted(sub_df_temp_3['jugador'].dropna().astype(str).unique().tolist())
    sel_jugador = st.selectbox("Selecciona Jugador:", jugadors_disp, key="jug3")

    if not sel_ordres:
        st.warning("Selecciona almenys un ordre.")
    else:
        sub_df_3 = sub_df_temp_3.copy()
        sub_df_per_mitjana = sub_df_3.copy()
        if sel_jugador != 'Tots':
            sub_df_per_mitjana = sub_df_per_mitjana[sub_df_per_mitjana['jugador'].astype(str) == sel_jugador]
        mitjanes_ordres = sub_df_per_mitjana.groupby('ordre')['total'].mean()

        if sel_jugador != 'Tots':
            sub_df_3 = sub_df_3[sub_df_3['jugador'].astype(str) == sel_jugador]

        if sub_df_3.empty:
            st.info("No hi ha dades per a aquesta selecció.")
        else:
            sort_cols_3 = ['ddmmaa', 'np'] if 'ddmmaa' in sub_df_3.columns and not sub_df_3['ddmmaa'].isna().all() else ['jornada', 'np']
            sub_df_3 = sub_df_3.sort_values(by=sort_cols_3, ascending=[True, True])

            fig3, ax3 = plt.subplots(figsize=(13, 6))
            colors_disponibles = plt.cm.tab10(np.linspace(0, 1, len(sel_ordres)))
            estils_linia = ['-', '--', '-.', ':', (0, (3, 1, 1, 1))]
            
            ordre_color_map = {ordre: colors_disponibles[i] for i, ordre in enumerate(sel_ordres)}
            ordre_estil_map = {ordre: estils_linia[i % len(estils_linia)] for i, ordre in enumerate(sel_ordres)}
            
            jugadors = sub_df_3['jugador'].dropna().unique()
            
            for jugador in jugadors:
                df_jugador = sub_df_3[sub_df_3['jugador'] == jugador].dropna(subset=['total'])
                if df_jugador.empty:
                    continue
                
                if 'ddmmaa' in df_jugador.columns and not df_jugador['ddmmaa'].isna().all():
                    eix_x_str_3 = df_jugador['ddmmaa'].dt.strftime('%d/%m/%Y') + ' (P' + df_jugador['np'].astype(str) + ')'
                else:
                    eix_x_str_3 = 'Jor. ' + df_jugador['jornada'].astype(str) + ' (P' + df_jugador['np'].astype(str) + ')'
                
                eix_y_3 = df_jugador['total'].values
                ordres_jugador = df_jugador['ordre'].values
                x_vals_3 = np.arange(len(df_jugador))
                
                if sel_jugador == 'Tots':
                    col_def = ordre_color_map.get(ordres_jugador[0], '#1E88E5')
                    estil_def = ordre_estil_map.get(ordres_jugador[0], '-')
                    ax3.plot(x_vals_3, eix_y_3, marker='o', linestyle=estil_def, linewidth=2, markersize=6, color=col_def, label=str(jugador))
                    for i, txt in enumerate(eix_y_3):
                        ax3.annotate(f"{int(txt)}", (x_vals_3[i], eix_y_3[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=col_def)
                else:
                    for i in range(len(df_jugador)):
                        ordre_actual = ordres_jugador[i]
                        col_actual = ordre_color_map.get(ordre_actual, '#1E88E5')
                        ax3.plot(x_vals_3[i], eix_y_3[i], marker='o', markersize=6, color=col_actual)
                        ax3.annotate(f"{int(eix_y_3[i])}", (x_vals_3[i], eix_y_3[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=8, fontweight='bold', color=col_actual)
                        
                        if i < len(df_jugador) - 1:
                            ordre_seg = ordres_jugador[i+1]
                            col_seg = ordre_color_map.get(ordre_seg, col_actual)
                            estil_seg = ordre_estil_map.get(ordre_seg, '-')
                            ax3.plot([x_vals_3[i], x_vals_3[i+1]], [eix_y_3[i], eix_y_3[i+1]], linestyle=estil_seg, linewidth=2.5, color=col_seg)

                    mitjana_jugador = eix_y_3.mean()
                    ax3.axhline(mitjana_jugador, color='gray', linestyle=':', linewidth=1.5, label=f"Mitjana Global: {mitjana_jugador:.2f}")

            for ordre, color in ordre_color_map.items():
                estil = ordre_estil_map.get(ordre, '-')
                mitjana_val = mitjanes_ordres.get(ordre, np.nan)
                etiqueta_ordre = f"Ordre {ordre} (Mitjana: {mitjana_val:.2f})" if not np.isnan(mitjana_val) else f"Ordre {ordre}"
                ax3.plot([], [], marker='o', color=color, linestyle=estil, linewidth=2, label=etiqueta_ordre)

            ax3.set_xticks(x_vals_3)
            ax3.set_xticklabels(eix_x_str_3, rotation=45, ha='right')

            ordres_str = ", ".join(map(str, sel_ordres))
            ax3.set_title(f"Evolució Temporal — Temporada: {sel_temp_3} | Ordre(s): {ordres_str} | Jugador: {sel_jugador}", fontsize=12, fontweight='bold')
            ax3.set_xlabel("Data i Partida", fontsize=10)
            ax3.set_ylabel("Punts (Total)", fontsize=10)
            ax3.legend(title="Llegenda", bbox_to_anchor=(1.05, 1), loc='upper left')
            ax3.grid(True, linestyle='--', alpha=0.6)
            plt.tight_layout()

            st.pyplot(fig3)

            buf3 = io.BytesIO()
            fig3.savefig(buf3, format="png", dpi=300, bbox_inches='tight')
            buf3.seek(0)
            st.download_button(
                label="📥 Descarregar gràfica 3 per WhatsApp",
                data=buf3,
                file_name="evolucio_jugadors_palou.png",
                mime="image/png",
                key="dl3"
            )
