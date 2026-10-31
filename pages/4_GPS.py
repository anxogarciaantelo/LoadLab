import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# Importar nuestras herramientas y base de datos compartida
from utils.math_helpers import *
from utils.pdf_generator import *
from database.db_manager import *

# --- COMPROBACIÓN DE SEGURIDAD Y SESIÓN ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning(":material/warning: La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    if st.button("Ir al Login principal"):
        st.session_state.clear()
        st.rerun()
    st.stop()

aplicar_color_sidebar()

def generar_grafico_radar_gps(df_target, df_ref, label_target, label_ref):
    df_t_val = df_target[df_target['DIS'] > 0].copy()
    df_r_val = df_ref[df_ref['DIS'] > 0].copy()
    
    if df_t_val.empty or df_r_val.empty: return None

    for df in [df_t_val, df_r_val]:
            min_efectivo_radar = np.where(df['MIN_GPS'] > 0, df['MIN_GPS'], df['MIN'])
            for col in ['DIS', 'DIS AI', 'ACC', 'Nº SPR']:
                if f'{col}/min' not in df.columns:
                    multiplicador = 1000.0 if col == 'DIS' else 1.0
                    df[f'{col}/min'] = np.where(min_efectivo_radar > 0, (df[col] * multiplicador) / min_efectivo_radar, 0)
    
    min_ref_sum = np.where(df_r_val['MIN_GPS'] > 0, df_r_val['MIN_GPS'], df_r_val['MIN']).sum()
    min_tar_sum = np.where(df_t_val['MIN_GPS'] > 0, df_t_val['MIN_GPS'], df_t_val['MIN']).sum()
    
    medias_ref = {
        'ACC/min': df_r_val['ACC/min'].mean(), 'VMAX': df_r_val['VMAX'].mean(),
        'V_Media': (df_r_val['DIS'].sum() / min_ref_sum) * 60 if min_ref_sum > 0 else 0,
        'DIS/min': df_r_val['DIS/min'].mean(), 'Nº SPR/min': df_r_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_r_val['DIS AI/min'].mean(), '% VMAX': df_r_val['% VMAX'].mean()
    }
    
    medias_target = {
        'ACC/min': df_t_val['ACC/min'].mean(), 'VMAX': df_t_val['VMAX'].mean(),
        'V_Media': (df_t_val['DIS'].sum() / min_tar_sum) * 60 if min_tar_sum > 0 else 0,
        'DIS/min': df_t_val['DIS/min'].mean(), 'Nº SPR/min': df_t_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_t_val['DIS AI/min'].mean(), '% VMAX': df_t_val['% VMAX'].mean()
    }

    categorias = ['Aceleraciones (>3)/min', 'Velocidad Máxima (Pico)', 'Velocidad Media', 'Distancia/min', 'Sprints/min', 'HSR (>21)/min', '% V. Máx']
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min', '% VMAX']
    
    valores_target = []
    valores_referencia = [100] * 7

    for clave in claves:
        m_ref = medias_ref[clave]
        m_tar = medias_target[clave]
        porcentaje = (m_tar / m_ref) * 100 if m_ref > 0 else 100
        valores_target.append(round(porcentaje, 1))

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=valores_referencia + [valores_referencia[0]], theta=categorias + [categorias[0]], fill='toself', name=label_ref, line=dict(color='rgba(150, 150, 150, 0.8)', width=2), fillcolor='rgba(200, 200, 200, 0.2)'))
    fig.add_trace(go.Scatterpolar(r=valores_target + [valores_target[0]], theta=categorias + [categorias[0]], fill='toself', name=label_target, line=dict(color='#00b4d8', width=3), fillcolor='rgba(0, 180, 216, 0.3)'))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(150, max(valores_target) + 20)], gridcolor="#1c1f26", linecolor="#1c1f26"), bgcolor="rgba(0,0,0,0)", angularaxis=dict(gridcolor="#1c1f26", linecolor="#1c1f26")), title=f"<b>Perfil Radar: {label_target} vs {label_ref}</b>", showlegend=True, margin=dict(l=40, r=40, t=40, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
    return fig

def generar_radar_comparador(dict_medias, usar_C):
    categorias = ['Aceleraciones (>3)/min', 'Velocidad Máxima', 'Velocidad Media', 'Distancia/min', 'Sprints/min', 'HSR (>21)/min', '% V. Máx']
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min', '% VMAX']
    datos_graf = {'A': [], 'B': [], 'C': []}
    
    for clave in claves:
        val_A = dict_medias['A'].get(clave, 0)
        val_B = dict_medias['B'].get(clave, 0)
        val_C = dict_medias['C'].get(clave, 0) if usar_C else 0
        max_val = max(val_A, val_B, val_C) if usar_C else max(val_A, val_B)
        
        datos_graf['A'].append((val_A / max_val) * 100 if max_val > 0 else 0)
        datos_graf['B'].append((val_B / max_val) * 100 if max_val > 0 else 0)
        if usar_C: datos_graf['C'].append((val_C / max_val) * 100 if max_val > 0 else 0)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=datos_graf['A'] + [datos_graf['A'][0]], theta=categorias + [categorias[0]], fill='toself', name=dict_medias['A_label'], line=dict(color='#00b4d8', width=2), fillcolor='rgba(0, 180, 216, 0.2)'))
    fig.add_trace(go.Scatterpolar(r=datos_graf['B'] + [datos_graf['B'][0]], theta=categorias + [categorias[0]], fill='toself', name=dict_medias['B_label'], line=dict(color='#ff4b4b', width=2), fillcolor='rgba(255, 75, 75, 0.2)'))
    if usar_C: fig.add_trace(go.Scatterpolar(r=datos_graf['C'] + [datos_graf['C'][0]], theta=categorias + [categorias[0]], fill='toself', name=dict_medias['C_label'], line=dict(color='#28a745', width=2), fillcolor='rgba(40, 167, 69, 0.2)'))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 110], gridcolor="#1c1f26", linecolor="#1c1f26"), bgcolor="rgba(0,0,0,0)", angularaxis=dict(gridcolor="#1c1f26", linecolor="#1c1f26")), title="<b>Comparativa Multidimensional (100% = Valor Máximo)</b>", margin=dict(l=40, r=40, t=40, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#f8fafc'))
    return fig

st.subheader(":material/satellite_alt: GPS")

lista_micro_map = []
for s in st.session_state.sesiones:
    if s.get("informe_generado"):
        num_sem = obtener_numero_semana(s["fecha"])
        _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
        lista_micro_map.append({"num_semana": num_sem, "lunes_dt": lunes})
        
mapa_micros = {}
if lista_micro_map:
    df_m_map = pd.DataFrame(lista_micro_map).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
    mapa_micros = {row["num_semana"]: i + 1 for i, row in df_m_map.iterrows()}

# Mapa dinámico de posiciones específicas
dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", p.get("POS", "")) for p in st.session_state.get("plantilla", [])}

# --- NUEVO MOTOR OPTIMIZADO ---
if "df_master_informes" in st.session_state and not st.session_state.df_master_informes.empty:
    # 1. Copiamos el master de la RAM
    df_gps = st.session_state.df_master_informes.copy()
    
    # 2. Nos quedamos solo con los que llevaron GPS (Distancia > 0)
    if 'GPS_VIRTUAL' not in df_gps.columns:
        df_gps['GPS_VIRTUAL'] = False
    # Filtro Crítico: Excluir los datos imputados virtualmente para no contaminar perfiles
    df_gps = df_gps[(df_gps['DIS'] > 0) & (df_gps['GPS_VIRTUAL'] != True)]
    
    # 3. Recreamos las columnas específicas que necesita esta vista (Microciclo, Nombre Sesión, POS_ESP)
    df_gps['Microciclo'] = df_gps['FECHA'].apply(lambda f: f"Microciclo {mapa_micros.get(obtener_numero_semana(f), obtener_numero_semana(f))}")
    
    # Creamos un string para el rival (solo si existe, añadimos "vs Rival")
    if 'RIVAL' not in df_gps.columns: df_gps['RIVAL'] = ""
    df_gps['Rival_Str'] = np.where(df_gps['RIVAL'].astype(str).str.strip() != "", " vs " + df_gps['RIVAL'].astype(str), "")
    
    # Construimos el nombre final: Fecha | Tipo vs Rival (MD)
    df_gps['Nombre_Sesion'] = df_gps['FECHA'] + " | " + df_gps['TIPO_SESION'] + df_gps['Rival_Str'] + " (" + df_gps['MD'] + ")"
    
    # Diccionarios rápidos para cruzar las posiciones específicas
    dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", p.get("POS", "")) for p in st.session_state.get("plantilla", [])}
    df_gps['POS_ESP'] = df_gps['JUGADOR'].apply(lambda x: dict_pos_esp.get(limpiar_nombre(x), "Desconocida"))
    
    # Renombrar para compatibilidad con el resto del código de GPS
    df_gps = df_gps.rename(columns={"TIPO_SESION": "TIPO"})
else:
    df_gps = pd.DataFrame()

tab_gps_perf, tab_gps_comp, tab_gps_inf = st.tabs([
    ":material/insights: Perfil de Rendimiento", 
    ":material/balance: Comparador",
    ":material/picture_as_pdf: Informe Individual"
])

if df_gps.empty:
    st.info(":material/info: No hay datos de GPS registrados todavía. Procesa datos en alguna sesión para visualizarlos aquí.")
else:
    cols_dinamicas = ['DIS', 'DIS AI', 'ACC', 'DCC', 'Nº SPR', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
    for c in cols_dinamicas:
        min_efectivo = np.where(df_gps['MIN_GPS'] > 0, df_gps['MIN_GPS'], df_gps['MIN'])
        multiplicador = 1000.0 if c == 'DIS' else 1.0
        df_gps[f'{c}/min'] = np.where(min_efectivo > 0, (df_gps[c] * multiplicador) / min_efectivo, 0)

    # --- NUEVO CÁLCULO DE % VMAX HISTÓRICA ---
    # Cogemos el máximo histórico de VMAX aislando los datos imputados (virtuales)
    df_master_real = st.session_state.df_master_informes.copy()
    if 'GPS_VIRTUAL' in df_master_real.columns:
        df_master_real = df_master_real[df_master_real['GPS_VIRTUAL'] != True]
        
    vmax_historica = df_master_real.groupby('JUGADOR')['VMAX'].max().to_dict()
    df_gps['VMAX_HIST'] = df_gps['JUGADOR'].map(vmax_historica).fillna(0)
    df_gps['% VMAX'] = np.where(df_gps['VMAX_HIST'] > 0, (df_gps['VMAX'] / df_gps['VMAX_HIST']) * 100, 0.0)
    # ------------------------------------------

    lista_jugs = sorted(df_gps['JUGADOR'].unique())
    lista_pos = ["POR", "DEF", "MED", "ATA"]
    lista_pos_esp = ["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"]
    lista_mds = ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD", "Post-Partido"]

    def aplicar_filtros_gps(df, target_tipo="Todas", target_md="TODOS", target_nivel="Equipo completo", target_jug="TODOS", target_pos="DEF", target_tiempo="Promedio total", target_sel_micro="TODOS", target_sel_sesion="TODOS", target_pos_esp="Central"):
        # --- ESCUDO ANTI-DATOS VIRTUALES ---
        # Aniquila cualquier registro imputado antes de evaluar al jugador
        if 'GPS_VIRTUAL' in df.columns:
            df = df[df['GPS_VIRTUAL'] != True]
            
        res = df.copy()
        
        if target_tiempo == "Promedio de microciclo" and target_sel_micro != "TODOS":
            res = res[res['Microciclo'] == target_sel_micro]
        elif target_tiempo == "Sesión" and target_sel_sesion != "TODOS":
            res = res[res['Nombre_Sesion'] == target_sel_sesion]
            
        if target_tipo != "Todas":
            res = res[res['TIPO'] == target_tipo]
            if target_tipo == "Entrenamiento" and target_md != "TODOS":
                res = res[res['MD'] == target_md]

        # --- Filtrar por disponibilidad salvo si es jugador concreto ---
        if target_nivel == "Por jugador":
            if target_jug != "TODOS": 
                res = res[res['JUGADOR'] == target_jug]
        else:
            # Excluimos a los no disponibles para que no hundan la media del grupo
            res = res[res['ESTADO'].isin(["Disponible", "Titular", "Suplente"])]
            
            if target_nivel == "Por posición general":
                res = res[res['POS'] == target_pos]
            elif target_nivel == "Por posición específica":
                res = res[res['POS_ESP'] == target_pos_esp]

        return res

    with tab_gps_perf:
        # --- FILTROS PLEGABLES DE UNA SOLA FILA ---
        with st.expander(":material/filter_list: FILTROS DE RENDIMIENTO", expanded=True):
            # Usamos 6 columnas compactas para una lectura de izquierda a derecha
            c_f1, c_f2, c_f3, c_f4, c_f5, c_f6 = st.columns(6)
            
            with c_f1: f_tiempo = st.selectbox("1. Periodo:", ["Promedio total", "Promedio de microciclo", "Sesión"], key="p_tiempo")
            with c_f2: f_tipo = st.selectbox("2. Evento:", ["Todas", "Entrenamiento", "Partido Oficial", "Partido Amistoso"], key="p_tipo")
            
            f_sel_micro, f_sel_sesion, f_md = "TODOS", "TODOS", "TODOS"
            
            with c_f3:
                if f_tiempo == "Promedio de microciclo":
                    lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
                    f_sel_micro = st.selectbox("3. Microciclo:", lista_micros, key="p_sel_micro")
                elif f_tipo == "Entrenamiento":
                    f_md = st.selectbox("3. Match Day:", lista_mds, key="p_md")
                elif f_tiempo == "Sesión" and f_tipo in ["Partido Oficial", "Partido Amistoso"]:
                    lista_partidos = sorted(df_gps[df_gps['TIPO'] == f_tipo]['Nombre_Sesion'].unique(), reverse=True)
                    f_sel_sesion = st.selectbox("3. Partido:", lista_partidos if lista_partidos else ["Sin datos"], key="p_sel_partido")
                elif f_tiempo == "Sesión" and f_tipo == "Todas":
                    lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                    f_sel_sesion = st.selectbox("3. Sesión:", lista_todas_ses if lista_todas_ses else ["Sin datos"], key="p_sel_ses_todas")
                else:
                    st.selectbox("3. Filtro extra:", [" "], disabled=True)

            with c_f4:
                if f_tiempo == "Sesión" and f_tipo == "Entrenamiento":
                    df_filtrado_md = df_gps[df_gps['TIPO'] == 'Entrenamiento']
                    if f_md != "TODOS": df_filtrado_md = df_filtrado_md[df_filtrado_md['MD'] == f_md]
                    lista_entrenos = sorted(df_filtrado_md['Nombre_Sesion'].unique(), reverse=True)
                    f_sel_sesion = st.selectbox("4. Sesión Exacta:", lista_entrenos if lista_entrenos else ["Sin datos"], key="p_sel_entreno")
                else:
                    st.selectbox("4. Sesión Exacta:", [" "], disabled=True)
            
            with c_f5:
                f_nivel = st.selectbox("5. Agrupar por:", ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], key="p_niv")

            f_jug, f_pos, f_pos_esp = "TODOS", "DEF", "Central"
            with c_f6:
                if f_nivel == "Por posición general":
                    f_pos = st.selectbox("6. Selección:", lista_pos, key="p_pos")
                elif f_nivel == "Por posición específica":
                    f_pos_esp = st.selectbox("6. Selección:", lista_pos_esp, key="p_pos_esp")
                elif f_nivel == "Por jugador":
                    f_jug = st.selectbox("6. Selección:", ["TODOS"] + lista_jugs, key="p_jug")
                else:
                    st.selectbox("6. Selección:", [" "], disabled=True)

        # Aplicar filtros a la selección principal
        df_perfil = aplicar_filtros_gps(
            df_gps, 
            target_tipo=f_tipo, 
            target_md=f_md, 
            target_nivel=f_nivel, 
            target_jug=f_jug, 
            target_pos=f_pos, 
            target_tiempo=f_tiempo, 
            target_sel_micro=f_sel_micro, 
            target_sel_sesion=f_sel_sesion, 
            target_pos_esp=f_pos_esp
        )

        if df_perfil.empty:
            st.warning(":material/warning: No hay datos para esta combinación de filtros.")
        else:
            # --- CONSTRUCCIÓN DINÁMICA DEL RADAR COMPARATIVO ---
            mostrar_radar = True
            df_radar_target = pd.DataFrame()
            df_radar_ref = pd.DataFrame()
            label_radar_target = ""
            label_radar_ref = ""

            if f_nivel == "Por jugador" and f_jug != "TODOS":
                # Caso Jugador (Mantiene lógica previa)
                jugador_info = next((p for p in st.session_state.plantilla if p['JUGADOR'] == f_jug), None)
                pos_exacta = jugador_info.get('pos_1', 'Desconocida') if jugador_info else 'Desconocida'
                jugadores_misma_pos = [p['JUGADOR'] for p in st.session_state.plantilla if p.get('pos_1') == pos_exacta]
                
                df_radar_target = df_perfil
                # Filtramos la referencia de su posición para que sea real (Solo Disponibles)
                df_radar_ref = df_gps[(df_gps['JUGADOR'].isin(jugadores_misma_pos)) & (df_gps['ESTADO'].isin(["Disponible", "Titular", "Suplente"]))].copy()
                if f_tipo != "Todas":
                    df_radar_ref = df_radar_ref[df_radar_ref['TIPO'] == f_tipo]
                
                label_radar_target = f_jug
                label_radar_ref = f"Media Posición ({pos_exacta})"

            elif f_tiempo == "Promedio total":
                if f_nivel == "Equipo completo":
                    mostrar_radar = False
                else:
                    df_radar_target = df_perfil
                    # Filtramos la base para que la referencia excluya a los no disponibles
                    df_base = df_gps[df_gps['ESTADO'].isin(["Disponible", "Titular", "Suplente"])].copy()
                    if f_tipo != "Todas":
                        df_base = df_base[df_base['TIPO'] == f_tipo]
                        
                    if f_nivel == "Por posición general":
                        df_radar_ref = df_base[df_base['POS'] != f_pos]
                        label_radar_target = f"Posición {f_pos}"
                        label_radar_ref = f"Resto del Equipo (excl. {f_pos})"
                    elif f_nivel == "Por posición específica":
                        df_radar_ref = df_base[df_base['POS_ESP'] != f_pos_esp]
                        label_radar_target = f"Posición {f_pos_esp}"
                        label_radar_ref = f"Resto del Equipo (excl. {f_pos_esp})"

            elif f_tiempo == "Promedio de microciclo":
                df_radar_target = df_perfil
                # Filtramos la base de referencia
                df_base_nivel = df_gps[df_gps['ESTADO'].isin(["Disponible", "Titular", "Suplente"])].copy()
                if f_tipo != "Todas":
                    df_base_nivel = df_base_nivel[df_base_nivel['TIPO'] == f_tipo]
                    
                if f_nivel == "Por posición general":
                    df_base_nivel = df_base_nivel[df_base_nivel['POS'] == f_pos]
                    lbl_scope = f"Posición {f_pos}"
                elif f_nivel == "Por posición específica":
                    df_base_nivel = df_base_nivel[df_base_nivel['POS_ESP'] == f_pos_esp]
                    lbl_scope = f"Posición {f_pos_esp}"
                else:
                    lbl_scope = "Equipo Completo"
                    
                df_radar_ref = df_base_nivel[df_base_nivel['Microciclo'] != f_sel_micro]
                label_radar_target = f"{lbl_scope} ({f_sel_micro})"
                label_radar_ref = f"{lbl_scope} (Resto de Microciclos)"

            elif f_tiempo == "Sesión":
                df_radar_target = df_perfil
                df_sesion_sel = df_gps[df_gps['Nombre_Sesion'] == f_sel_sesion]
                
                if not df_sesion_sel.empty:
                    md_sesion_sel = df_sesion_sel.iloc[0]['MD']
                    tipo_sesion_sel = df_sesion_sel.iloc[0]['TIPO']
                    
                    # Filtramos la base de referencia
                    df_base_nivel = df_gps[df_gps['ESTADO'].isin(["Disponible", "Titular", "Suplente"])].copy()
                    
                    if tipo_sesion_sel == "Entrenamiento":
                        df_base_nivel = df_base_nivel[(df_base_nivel['TIPO'] == "Entrenamiento") & (df_base_nivel['MD'] == md_sesion_sel)]
                        criterio_str = f"{md_sesion_sel}"
                    else:
                        df_base_nivel = df_base_nivel[df_base_nivel['TIPO'] == tipo_sesion_sel]
                        criterio_str = f"{tipo_sesion_sel}s"

                    if f_nivel == "Por posición general":
                        df_base_nivel = df_base_nivel[df_base_nivel['POS'] == f_pos]
                        lbl_scope = f"Posición {f_pos}"
                    elif f_nivel == "Por posición específica":
                        df_base_nivel = df_base_nivel[df_base_nivel['POS_ESP'] == f_pos_esp]
                        lbl_scope = f"Posición {f_pos_esp}"
                    else:
                        lbl_scope = "Equipo Completo"

                    df_radar_ref = df_base_nivel[df_base_nivel['Nombre_Sesion'] != f_sel_sesion]
                    label_radar_target = f"{lbl_scope} (Sesión Actual)"
                    label_radar_ref = f"{lbl_scope} (Resto de {criterio_str})"
                else:
                    mostrar_radar = False

            # Mostrar Radar si corresponde
            if mostrar_radar and not df_radar_target.empty and not df_radar_ref.empty:
                fig_radar = generar_grafico_radar_gps(df_radar_target, df_radar_ref, label_radar_target, label_radar_ref)
                if fig_radar:
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.info(":material/info: No hay suficientes datos GPS para generar la comparación radar.")

            # --- REDISEÑO ÉLITE: TARJETAS KPI Y HEATMAP ---
            df_perfil['m/min'] = np.where(df_perfil['MIN_GPS'] > 0, (df_perfil['DIS'] * 1000) / df_perfil['MIN_GPS'], 0)
            df_perfil['HSR/min'] = np.where(df_perfil['MIN_GPS'] > 0, df_perfil['DIS AI'] / df_perfil['MIN_GPS'], 0)
            df_perfil['SPR/min'] = np.where(df_perfil['MIN_GPS'] > 0, df_perfil['Nº SPR'] / df_perfil['MIN_GPS'], 0)
            df_perfil['ACC/min'] = np.where(df_perfil['MIN_GPS'] > 0, df_perfil['ACC'] / df_perfil['MIN_GPS'], 0)
            df_perfil['DCC/min'] = np.where(df_perfil['MIN_GPS'] > 0, df_perfil['DCC'] / df_perfil['MIN_GPS'], 0)

            kpis_abs = df_perfil[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', '% VMAX']].mean()
            kpis_rel = df_perfil[['m/min', 'HSR/min', 'SPR/min', 'ACC/min', 'DCC/min']].mean()

            def kpi_gps_card(titulo, val_abs, lbl_abs, val_rel, lbl_rel, color="#C5A059"):
                return f"""
                <div style="background: #111318; border: 1px solid #1c1f26; border-top: 3px solid {color}; border-radius: 10px; padding: 15px; display: flex; flex-direction: column; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                    <span style="color: #94a3b8; font-size: 0.85rem; font-weight: 800; text-transform: uppercase; margin-bottom: 5px;">{titulo}</span>
                    <span style="color: #f8fafc; font-size: 1.8rem; font-weight: 800; line-height: 1;">{val_abs} <span style="font-size: 0.9rem; color: #94a3b8;">{lbl_abs}</span></span>
                    <div style="margin-top: auto; padding-top: 10px; border-top: 1px solid #1c1f26; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #cbd5e1; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">Densidad</span>
                        <span style="color: {color}; font-size: 0.95rem; font-weight: 800;">{val_rel} <span style="font-size: 0.75rem;">{lbl_rel}</span></span>
                    </div>
                </div>
                """

            st.markdown("---")
            st.markdown("#### :material/track_changes: Rendimiento Físico Medio (Absoluto vs Relativo)")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1: st.markdown(kpi_gps_card("Distancia", f"{kpis_abs['DIS']:.2f}", "km", f"{kpis_rel['m/min']:.1f}", "m/min", "#C5A059"), unsafe_allow_html=True)
            with c2: st.markdown(kpi_gps_card("HSR (>21)", f"{kpis_abs['DIS AI']:.0f}", "m", f"{kpis_rel['HSR/min']:.2f}", "m/min", "#f59e0b"), unsafe_allow_html=True)
            with c3: st.markdown(kpi_gps_card("Sprints", f"{kpis_abs['Nº SPR']:.1f}", "nº", f"{kpis_rel['SPR/min']:.2f}", "n/min", "#ef4444"), unsafe_allow_html=True)
            with c4: st.markdown(kpi_gps_card("ACC (>3)", f"{kpis_abs['ACC']:.0f}", "nº", f"{kpis_rel['ACC/min']:.2f}", "n/min", "#10b981"), unsafe_allow_html=True)
            with c5: st.markdown(kpi_gps_card("DCC (>3)", f"{kpis_abs['DCC']:.0f}", "nº", f"{kpis_rel['DCC/min']:.2f}", "n/min", "#8b5cf6"), unsafe_allow_html=True)
            with c6: 
                st.markdown(f"""
                <div style="background: #111318; border: 1px solid #1c1f26; border-top: 3px solid #ec4899; border-radius: 10px; padding: 15px; display: flex; flex-direction: column; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                    <span style="color: #94a3b8; font-size: 0.85rem; font-weight: 800; text-transform: uppercase; margin-bottom: 5px;">Velocidad Máx</span>
                    <span style="color: #f8fafc; font-size: 1.8rem; font-weight: 800; line-height: 1;">{kpis_abs['VMAX']:.1f} <span style="font-size: 0.9rem; color: #94a3b8;">km/h</span></span>
                    <div style="margin-top: auto; padding-top: 10px; border-top: 1px solid #1c1f26; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #cbd5e1; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">% Histórico</span>
                        <span style="color: #ec4899; font-size: 0.95rem; font-weight: 800;">{kpis_abs['% VMAX']:.1f} <span style="font-size: 0.75rem;">%</span></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### :material/grid_on: Análisis Detallado (Heatmap de Intensidad)")
            
            df_tabla = df_perfil.groupby(['JUGADOR', 'POS']).agg({
                'MIN_GPS': 'mean', 'DIS': 'mean', 'm/min': 'mean', 'DIS AI': 'mean',
                'Nº SPR': 'mean', 'ACC': 'mean', 'DCC': 'mean', 'VMAX': 'max', '% VMAX': 'max'
            }).reset_index()
            
            df_tabla['DCC:ACC'] = (df_tabla['DCC'] / df_tabla['ACC'].replace(0, np.nan)).fillna(0)
            
            css_dark_table = "<style>.modern-dark-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); background-color: #111318; color: #f8fafc; margin-bottom: 20px; } .modern-dark-table thead tr { background-color: #0b0e14; color: #C5A059; } .modern-dark-table th { padding: 12px 15px; font-weight: 800; text-transform: uppercase; font-size: 0.8rem; text-align: center !important; border-bottom: 2px solid #1c1f26; } .modern-dark-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #1c1f26; font-weight: 700; font-size: 0.95rem; } .modern-dark-table tbody tr:hover td { filter: brightness(1.2); } .alerta-excentrica { color: #ef4444; font-weight: 900; }</style>"
            
            cols_tabla = ['JUGADOR', 'POS', 'MIN_GPS', 'DIS', 'm/min', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'DCC:ACC', 'VMAX', '% VMAX']
            
            estilo_gps = (df_tabla[cols_tabla].style
                .hide(axis="index")
                .format({"MIN_GPS": "{:.0f}'", "DIS": "{:.2f}", "m/min": "{:.1f}", "DIS AI": "{:.0f}", "Nº SPR": "{:.1f}", "ACC": "{:.0f}", "DCC": "{:.0f}", "DCC:ACC": "{:.2f}", "VMAX": "{:.1f}", "% VMAX": "{:.1f}"})
                .background_gradient(subset=['DIS', 'm/min'], cmap='Blues', text_color_threshold=0.6)
                .background_gradient(subset=['DIS AI'], cmap='YlOrBr', text_color_threshold=0.6)
                .background_gradient(subset=['Nº SPR'], cmap='Reds', text_color_threshold=0.6)
                .background_gradient(subset=['ACC'], cmap='Greens', text_color_threshold=0.6)
                .background_gradient(subset=['DCC'], cmap='Purples', text_color_threshold=0.6)
                .background_gradient(subset=['DCC:ACC'], cmap='Oranges', text_color_threshold=0.6)
                .background_gradient(subset=['VMAX', '% VMAX'], cmap='RdPu', text_color_threshold=0.6)
                .map(lambda x: "color: #ef4444; font-weight: 900;" if isinstance(x, (int, float)) and x > 1.3 else "", subset=['DCC:ACC'])
                .set_table_attributes('class="modern-dark-table"')
            )
            
            st.markdown(css_dark_table + estilo_gps.to_html(), unsafe_allow_html=True)

    # ==========================================
    # PESTAÑA 2: COMPARADOR (FILTROS PLEGABLES)
    # ==========================================
    with tab_gps_comp:
        # --- DESPLEGABLE CON LOS FILTROS DE LOS PERFILES ---
        with st.expander(":material/tune: Configurar Perfiles a Comparar", expanded=False):
            
            def render_columna_filtro_comparador(prefijo, titulo, color_hex):
                st.markdown(f"**<span style='color:{color_hex}'>■</span> {titulo}**", unsafe_allow_html=True)
                
                t_tiempo = st.selectbox("1. Periodo:", ["Promedio total", "Promedio de microciclo", "Sesión"], key=f"c_{prefijo}_tiempo")
                t_tipo = st.selectbox("2. Evento:", ["Todas", "Entrenamiento", "Partido Oficial", "Partido Amistoso"], key=f"c_{prefijo}_tipo")
                
                t_sel_micro, t_sel_sesion, t_md = "TODOS", "TODOS", "TODOS"
                
                if t_tiempo == "Promedio de microciclo":
                    lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
                    t_sel_micro = st.selectbox("3. Microciclo:", lista_micros, key=f"c_{prefijo}_micro")
                
                if t_tipo == "Entrenamiento":
                    t_md = st.selectbox("Match Day (MD):", lista_mds, key=f"c_{prefijo}_md")
                    if t_tiempo == "Sesión":
                        df_filtrado_md = df_gps[df_gps['TIPO'] == 'Entrenamiento']
                        if t_md != "TODOS": df_filtrado_md = df_filtrado_md[df_filtrado_md['MD'] == t_md]
                        lista_entrenos = sorted(df_filtrado_md['Nombre_Sesion'].unique(), reverse=True)
                        t_sel_sesion = st.selectbox("Sesión exacta:", lista_entrenos if lista_entrenos else ["Sin datos"], key=f"c_{prefijo}_entreno")
                elif t_tiempo == "Sesión":
                    if t_tipo in ["Partido Oficial", "Partido Amistoso"]:
                        lista_partidos = sorted(df_gps[df_gps['TIPO'] == t_tipo]['Nombre_Sesion'].unique(), reverse=True)
                        t_sel_sesion = st.selectbox("Sesión exacta:", lista_partidos if lista_partidos else ["Sin datos"], key=f"c_{prefijo}_partido")
                    else:
                        lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                        t_sel_sesion = st.selectbox("Sesión exacta:", lista_todas_ses if lista_todas_ses else ["Sin datos"], key=f"c_{prefijo}_ses_todas")

                t_nivel = st.selectbox("Agrupar por:", ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], key=f"c_{prefijo}_niv")
                t_jug, t_pos, t_pos_esp = "TODOS", "DEF", "Central"
                
                if t_nivel == "Por posición general":
                    t_pos = st.selectbox("Selección:", lista_pos, key=f"c_{prefijo}_pos")
                elif t_nivel == "Por posición específica":
                    t_pos_esp = st.selectbox("Selección:", lista_pos_esp, key=f"c_{prefijo}_pos_esp")
                elif t_nivel == "Por jugador":
                    t_jug = st.selectbox("Selección:", ["TODOS"] + lista_jugs, key=f"c_{prefijo}_jug")
                
                lbl_nivel = t_jug if t_nivel == "Por jugador" else (t_pos if t_nivel == "Por posición general" else (t_pos_esp if t_nivel == "Por posición específica" else "Equipo"))
                lbl_ctx = t_sel_micro if t_tiempo == "Promedio de microciclo" else (t_sel_sesion if t_tiempo == "Sesión" else (t_md if t_tipo == "Entrenamiento" and t_md != "TODOS" else ("Entrenos" if t_tipo == "Entrenamiento" else ("Partidos" if "Partido" in t_tipo else "Total"))))
                label_final = f"{lbl_nivel} ({lbl_ctx})"

                df_res = aplicar_filtros_gps(
                    df_gps, 
                    target_tiempo=t_tiempo, 
                    target_tipo=t_tipo, 
                    target_md=t_md,
                    target_sel_micro=t_sel_micro, 
                    target_sel_sesion=t_sel_sesion, 
                    target_nivel=t_nivel, 
                    target_pos=t_pos, 
                    target_pos_esp=t_pos_esp, 
                    target_jug=t_jug
                )

                return df_res, label_final

            # Cuadrícula de 3 columnas dentro del expander
            colA, colB, colC = st.columns(3)
            with colA: 
                df_A, lbl_A = render_columna_filtro_comparador("A", "Perfil A", "#00b4d8")
            with colB: 
                df_B, lbl_B = render_columna_filtro_comparador("B", "Perfil B", "#ff4b4b")
            with colC:
                usar_C = st.checkbox("Activar Perfil C", value=False)
                if usar_C:
                    df_C, lbl_C = render_columna_filtro_comparador("C", "Perfil C", "#28a745")
                else:
                    df_C, lbl_C = pd.DataFrame(), ""

        # --- CONTENIDO VISUAL EN PANTALLA PRINCIPAL (FUERA DEL EXPANDER) ---
        if df_A.empty or df_B.empty or (usar_C and df_C.empty):
            st.warning(":material/warning: Uno de los perfiles activos no tiene datos para los filtros seleccionados.")
        else:
            # 1. CÁLCULO DE MEDIAS PARA EL RADAR MULTI-PERFIL
            metrics_radar = ['ACC/min', 'VMAX', 'DIS/min', 'Nº SPR/min', 'DIS AI/min', 'MIN', 'DIS', '% VMAX']
            mean_A = df_A[metrics_radar].mean().to_dict()
            mean_B = df_B[metrics_radar].mean().to_dict()
            mean_C = df_C[metrics_radar].mean().to_dict() if usar_C else {}
            
            def calc_vmedia(df): return (df['DIS'].sum() / df['MIN'].sum()) * 60 if df['MIN'].sum() > 0 else 0

            mean_A['V_Media'] = calc_vmedia(df_A)
            mean_B['V_Media'] = calc_vmedia(df_B)
            if usar_C: mean_C['V_Media'] = calc_vmedia(df_C)

            dict_medias_radar = {'A': mean_A, 'A_label': lbl_A, 'B': mean_B, 'B_label': lbl_B, 'C': mean_C, 'C_label': lbl_C}

            # 2. MOSTRAR RADAR
            st.markdown("#### :material/radar: Radar Comparativo")
            fig_comp = generar_radar_comparador(dict_medias_radar, usar_C)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.markdown("---")

            # 3. MOSTRAR TABLA COMPARATIVA
            st.markdown("#### :material/table_chart: Análisis Analítico Avanzado")
            st.caption("Analiza las diferencias porcentuales entre perfiles. Los datos absolutos y relativos se formatean a 2 decimales exactos para garantizar precisión.")
            modo_comp = st.radio("¿Qué tipo de métricas quieres comparar en la tabla?", ["Absolutas (Totales)", "Relativas (Por Minuto)"], horizontal=True)
            
            # Asegurar cálculos de densidades en los dataframes de comparación
            for df_x in [df_A, df_B] + ([df_C] if usar_C else []):
                if not df_x.empty:
                    min_ef_x = np.where(df_x['MIN_GPS'] > 0, df_x['MIN_GPS'], df_x['MIN'])
                    df_x['DIS/min'] = np.where(min_ef_x > 0, (df_x['DIS'] * 1000) / min_ef_x, 0)
                    df_x['DIS AI/min'] = np.where(min_ef_x > 0, df_x['DIS AI'] / min_ef_x, 0)
                    df_x['SPR/min'] = np.where(min_ef_x > 0, df_x['Nº SPR'] / min_ef_x, 0)
                    df_x['ACC/min'] = np.where(min_ef_x > 0, df_x['ACC'] / min_ef_x, 0)
                    df_x['DCC/min'] = np.where(min_ef_x > 0, df_x['DCC'] / min_ef_x, 0)
                    df_x['DCC:ACC'] = (df_x['DCC'] / df_x['ACC'].replace(0, np.nan)).fillna(0)
            
            if modo_comp == "Absolutas (Totales)":
                metrics_to_compare = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'DCC:ACC', 'VMAX', '% VMAX']
                nombres_met = {'MIN': 'Minutos', 'DIS': 'Volumen (km)', 'DIS AI': 'HSR (>21) (m)', 'Nº SPR': 'Sprints (>24)', 'ACC': 'Aceleraciones', 'DCC': 'Deceleraciones', 'DCC:ACC': 'Ratio DCC:ACC', 'VMAX': 'V. Máxima (km/h)', '% VMAX': '% V. Máx'}
            else:
                metrics_to_compare = ['DIS/min', 'DIS AI/min', 'SPR/min', 'ACC/min', 'DCC/min', 'DCC:ACC']
                nombres_met = {'DIS/min': 'Densidad Vol. (m/min)', 'DIS AI/min': 'Densidad HSR (m/min)', 'SPR/min': 'Sprints / min', 'ACC/min': 'ACC / min', 'DCC/min': 'DCC / min', 'DCC:ACC': 'Ratio DCC:ACC'}

            mean_t_A = df_A[metrics_to_compare].mean()
            mean_t_B = df_B[metrics_to_compare].mean()
            mean_t_C = df_C[metrics_to_compare].mean() if usar_C else None

            comp_data = []
            for m in metrics_to_compare:
                valA = mean_t_A[m] if not pd.isna(mean_t_A[m]) else 0
                valB = mean_t_B[m] if not pd.isna(mean_t_B[m]) else 0
                valC = mean_t_C[m] if usar_C and not pd.isna(mean_t_C[m]) else 0

                dif_pct_B = ((valB - valA) / valA * 100) if valA > 0 else 0
                dif_pct_C = ((valC - valA) / valA * 100) if usar_C and valA > 0 else 0
                
                def format_trend(pct):
                    if pct > 2: return f"▲ +{pct:.2f}%"
                    elif pct < -2: return f"▼ {pct:.2f}%"
                    else: return f"▬ {pct:+.2f}%"

                # Truncamos los títulos para que no deformen la tabla
                lbl_A_short = (lbl_A[:30] + '..') if len(lbl_A) > 30 else lbl_A
                lbl_B_short = (lbl_B[:30] + '..') if len(lbl_B) > 30 else lbl_B
                
                fila = {
                    "MÉTRICA": nombres_met.get(m, m),
                    f"A: {lbl_A_short}": valA,
                    f"B: {lbl_B_short}": valB,
                    "EVOLUCIÓN (B vs A)": format_trend(dif_pct_B)
                }
                if usar_C:
                    lbl_C_short = (lbl_C[:30] + '..') if len(lbl_C) > 30 else lbl_C
                    fila[f"C: {lbl_C_short}"] = valC
                    fila["EVOLUCIÓN (C vs A)"] = format_trend(dif_pct_C)
                    
                comp_data.append(fila)
                
            df_comp_final = pd.DataFrame(comp_data)
            
            columnas_estilo = ["EVOLUCIÓN (B vs A)", "EVOLUCIÓN (C vs A)"] if usar_C else ["EVOLUCIÓN (B vs A)"]
            
            fmt_dict = {}
            for col in df_comp_final.columns:
                if col.startswith("A:") or col.startswith("B:") or col.startswith("C:"):
                    fmt_dict[col] = "{:.2f}"
            
            estilo_comp = (df_comp_final.style
                .hide(axis="index")
                .format(fmt_dict)
                .map(lambda x: "color: #10b981; font-weight: 800;" if "▲" in str(x) else ("color: #ef4444; font-weight: 800;" if "▼" in str(x) else "color: #94a3b8; font-weight: 800;"), subset=columnas_estilo)
                .set_table_attributes('class="modern-dark-table"')
            )
            
            css_dark_table = "<style>.modern-dark-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4); background-color: #111318; color: #f8fafc; margin-bottom: 20px; } .modern-dark-table thead tr { background-color: #0b0e14; color: #C5A059; } .modern-dark-table th { padding: 12px 15px; font-weight: 800; text-transform: uppercase; font-size: 0.8rem; text-align: center !important; border-bottom: 2px solid #1c1f26; } .modern-dark-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #1c1f26; font-weight: 700; font-size: 0.95rem; } .modern-dark-table tbody tr:hover td { filter: brightness(1.2); } </style>"
            
            st.markdown(css_dark_table + estilo_comp.to_html(), unsafe_allow_html=True)
# ==========================================
    # PESTAÑA 3: INFORME INDIVIDUAL
    # ==========================================
    with tab_gps_inf:
        st.markdown("#### :material/picture_as_pdf: Generador de Informe GPS Individual")
        st.caption("Selecciona una sesión y un jugador para generar un informe en PDF detallado y enfocado exclusivamente en su rendimiento. Se aislará su métrica frente a los promedios posicionales.")
        
        col_s1, col_s2 = st.columns(2)
        lista_sesiones = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
        sesion_sel = col_s1.selectbox("1. Selecciona la Sesión:", ["Selecciona..."] + lista_sesiones, key="inf_ses")
        
        if sesion_sel != "Selecciona...":
            df_ses = df_gps[df_gps['Nombre_Sesion'] == sesion_sel].copy()
            jugadores_ses = sorted(df_ses['JUGADOR'].unique())
            jug_sel = col_s2.selectbox("2. Selecciona el Jugador:", ["Selecciona..."] + jugadores_ses, key="inf_jug")
            
            if jug_sel != "Selecciona...":
                st.markdown("---")
                
                # Densidades previas
                for df_calc in [df_ses]:
                    min_ef = np.where(df_calc['MIN_GPS'] > 0, df_calc['MIN_GPS'], df_calc['MIN'])
                    df_calc['m/min'] = np.where(min_ef > 0, (df_calc['DIS'] * 1000) / min_ef, 0)
                    df_calc['HSR/min'] = np.where(min_ef > 0, df_calc['DIS AI'] / min_ef, 0)
                    df_calc['SPR/min'] = np.where(min_ef > 0, df_calc['Nº SPR'] / min_ef, 0)
                    df_calc['ACC/min'] = np.where(min_ef > 0, df_calc['ACC'] / min_ef, 0)
                    df_calc['DCC/min'] = np.where(min_ef > 0, df_calc['DCC'] / min_ef, 0)
                    df_calc['Mec/min'] = np.where(min_ef > 0, (df_calc['ACC'] + df_calc['DCC']) / min_ef, 0)

                df_jug = df_ses[df_ses['JUGADOR'] == jug_sel].copy()
                pos_jug = df_jug.iloc[0]['POS_ESP'] if 'POS_ESP' in df_jug.columns else "Desconocida"
                
                df_ref_pos = df_ses[(df_ses['POS_ESP'] == pos_jug) & (df_ses['JUGADOR'] != jug_sel) & (df_ses['ESTADO'].isin(["Disponible", "Titular", "Suplente"]))]
                if df_ref_pos.empty:
                    df_ref_pos = df_ses[df_ses['POS_ESP'] == pos_jug]
                
                # Radar (Jugador vs Posición)
                fig_radar = generar_grafico_radar_gps(df_jug, df_ref_pos, jug_sel, f"Media ({pos_jug})")
                
                # Referencias 100% (para bandas objetivo)
                df_partidos = st.session_state.df_master_informes[(st.session_state.df_master_informes['TIPO_SESION'].str.contains("Partido", na=False)) & (st.session_state.df_master_informes['DIS'] > 0)].copy()
                if not df_partidos.empty:
                    df_partidos['MIN_REAL'] = np.where(df_partidos.get('MIN_GPS', df_partidos['MIN']) > 0, df_partidos.get('MIN_GPS', df_partidos['MIN']), df_partidos['MIN'])
                    min_tot = df_partidos['MIN_REAL'].sum()
                    dis_100_eq = (df_partidos['DIS'].sum() / min_tot) * 90 if min_tot > 0 else 10.0
                    hsr_100_eq = (df_partidos['DIS AI'].sum() / min_tot) * 90 if min_tot > 0 else 600.0
                    acc_100_eq = (df_partidos['ACC'].sum() / min_tot) * 90 if min_tot > 0 else 40.0
                    dcc_100_eq = (df_partidos['DCC'].sum() / min_tot) * 90 if min_tot > 0 else 40.0
                else:
                    dis_100_eq, hsr_100_eq, acc_100_eq, dcc_100_eq = 10.0, 600.0, 40.0, 40.0

                es_entreno = df_jug.iloc[0]['TIPO'] == "Entrenamiento"
                md_ses = df_jug.iloc[0]['MD']
                
                # 1. Scatter Vol vs Int
                fig_vi = px.scatter(df_jug, x='DIS', y='DIS AI', text='JUGADOR', title=f"Volumen vs Intensidad ({md_ses})")
                fig_vi.update_traces(marker=dict(size=16, color="#10b981", line=dict(width=2, color="DarkSlateGrey")), textposition='top center')
                
                x1_v, y1_v = 0, 0
                if es_entreno:
                    zonas_pt = {
                        "MD-5": {"DIS": [0.15, 0.45], "HSR": [0.00, 0.20], "ACC": [0.10, 0.40], "DCC": [0.10, 0.40]},
                        "MD-4": {"DIS": [0.40, 0.70], "HSR": [0.10, 0.40], "ACC": [0.70, 1.30], "DCC": [0.70, 1.30]},
                        "MD-3": {"DIS": [0.60, 0.90], "HSR": [0.50, 0.95], "ACC": [0.40, 0.75], "DCC": [0.40, 0.75]},
                        "MD-2": {"DIS": [0.30, 0.55], "HSR": [0.15, 0.45], "ACC": [0.25, 0.55], "DCC": [0.25, 0.55]},
                        "MD-1": {"DIS": [0.15, 0.35], "HSR": [0.00, 0.15], "ACC": [0.10, 0.30], "DCC": [0.10, 0.30]},
                        "MD+1": {"DIS": [0.15, 0.45], "HSR": [0.00, 0.20], "ACC": [0.10, 0.40], "DCC": [0.10, 0.40]},
                        "MD+2": {"DIS": [0.30, 0.60], "HSR": [0.10, 0.35], "ACC": [0.25, 0.60], "DCC": [0.25, 0.60]},
                        "TD":   {"DIS": [0.45, 0.85], "HSR": [0.25, 0.75], "ACC": [0.45, 0.85], "DCC": [0.45, 0.85]},
                        "Post-Partido": {"DIS": [0.30, 0.60], "HSR": [0.40, 0.80], "ACC": [0.50, 0.90], "DCC": [0.50, 0.90]}
                    }
                    z_obj = zonas_pt.get(md_ses, zonas_pt["TD"])
                    x0_v, x1_v = z_obj["DIS"][0]*dis_100_eq, z_obj["DIS"][1]*dis_100_eq
                    y0_v, y1_v = z_obj["HSR"][0]*hsr_100_eq, z_obj["HSR"][1]*hsr_100_eq
                    fig_vi.add_shape(type="rect", x0=x0_v, x1=x1_v, y0=y0_v, y1=y1_v, fillcolor="green", opacity=0.15, line_color="green", layer="below")
                
                fig_vi.update_layout(
                    xaxis=dict(range=[0, max(x1_v*1.2, df_jug['DIS'].max()*1.2)]),
                    yaxis=dict(range=[0, max(y1_v*1.2, df_jug['DIS AI'].max()*1.2)]),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                )

                # 2. Scatter ACC vs DCC
                fig_mec = px.scatter(df_jug, x='DCC', y='ACC', text='JUGADOR', title=f"Tensión Mecánica ({md_ses})")
                fig_mec.update_traces(marker=dict(size=16, color="#ef4444", line=dict(width=2, color="DarkSlateGrey")), textposition='top center')
                
                x1_m, y1_m = 0, 0
                if es_entreno:
                    x0_m, x1_m = z_obj["DCC"][0]*dcc_100_eq, z_obj["DCC"][1]*dcc_100_eq
                    y0_m, y1_m = z_obj["ACC"][0]*acc_100_eq, z_obj["ACC"][1]*acc_100_eq
                    fig_mec.add_shape(type="rect", x0=x0_m, x1=x1_m, y0=y0_m, y1=y1_m, fillcolor="green", opacity=0.15, line_color="green", layer="below")
                    
                fig_mec.update_layout(
                    xaxis=dict(range=[0, max(x1_m*1.2, df_jug['DCC'].max()*1.2)]),
                    yaxis=dict(range=[0, max(y1_m*1.2, df_jug['ACC'].max()*1.2)]),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                )

                # 3. Densidades
                fig_den1 = px.scatter(df_jug, x='m/min', y='HSR/min', text='JUGADOR', title="Densidad: Volumen vs Intensidad", size='VMAX')
                fig_den1.update_traces(marker=dict(color="#0ea5e9", line=dict(width=2, color="DarkSlateGrey")), textposition='top center')
                fig_den1.update_layout(xaxis=dict(range=[0, df_jug['m/min'].max()*1.5]), yaxis=dict(range=[0, df_jug['HSR/min'].max()*1.5]), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                
                fig_den2 = px.scatter(df_jug, x='m/min', y='Mec/min', text='JUGADOR', title="Densidad: Volumen vs Tensión Mecánica")
                fig_den2.update_traces(marker=dict(size=16, color="#8b5cf6", line=dict(width=2, color="DarkSlateGrey")), textposition='top center')
                fig_den2.update_layout(xaxis=dict(range=[0, df_jug['m/min'].max()*1.5]), yaxis=dict(range=[0, df_jug['Mec/min'].max()*1.5]), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

                # Dicc. KPIs (Aseguramos la integridad de los datos para FPDF)
                kpis_abs = {
                    "DIS": df_jug.iloc[0]['DIS'], "DIS AI": df_jug.iloc[0]['DIS AI'],
                    "Nº SPR": df_jug.iloc[0]['Nº SPR'], "ACC": df_jug.iloc[0]['ACC'],
                    "DCC": df_jug.iloc[0]['DCC'], "VMAX": df_jug.iloc[0]['VMAX'], "% VMAX": df_jug.iloc[0]['% VMAX']
                }
                kpis_rel = {
                    "m/min": df_jug.iloc[0]['m/min'], "HSR/min": df_jug.iloc[0]['HSR/min'],
                    "SPR/min": df_jug.iloc[0]['SPR/min'], "ACC/min": df_jug.iloc[0]['ACC/min'], "DCC/min": df_jug.iloc[0]['DCC/min']
                }
                
                pdf_key = f"pdf_gps_ind_{jug_sel}_{sesion_sel}"
                
                if pdf_key not in st.session_state:
                    if st.button(":material/picture_as_pdf: Generar Informe en PDF", use_container_width=True, type="primary"):
                        with st.spinner("Compilando gráficos y generando informe..."):
                            import tempfile
                            
                            def render_plot_for_pdf(fig):
                                if not fig: return None
                                # Acomodamos fondo, márgenes y color de ejes para el PDF en blanco
                                fig.update_layout(
                                    paper_bgcolor="white", 
                                    plot_bgcolor="white", 
                                    font=dict(color="black"), 
                                    title_font=dict(color="black"),
                                    xaxis=dict(tickfont=dict(color="black"), title_font=dict(color="black"), gridcolor="#e2e8f0"),
                                    yaxis=dict(tickfont=dict(color="black"), title_font=dict(color="black"), gridcolor="#e2e8f0")
                                )
                                # Adaptación específica para el gráfico de radar
                                if hasattr(fig.layout, 'polar'):
                                    fig.update_layout(polar=dict(angularaxis=dict(tickfont=dict(color="black")), radialaxis=dict(tickfont=dict(color="black"))))
                                    
                                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                                tmp.close()
                                fig.write_image(tmp.name, engine="kaleido", width=800, height=530, format="jpg")
                                return tmp.name
                                
                            img_paths = {
                                "radar": render_plot_for_pdf(fig_radar),
                                "vol_int": render_plot_for_pdf(fig_vi),
                                "tension": render_plot_for_pdf(fig_mec),
                                "den_vol_int": render_plot_for_pdf(fig_den1),
                                "den_tension": render_plot_for_pdf(fig_den2)
                            }
                            
                            jug_datos = next((p for p in st.session_state.plantilla if p["JUGADOR"] == jug_sel), None)
                            foto_b64 = jug_datos.get("foto") if jug_datos else None
                            
                            from utils.pdf_generator import generar_pdf_gps_individual
                            pdf_bytes = generar_pdf_gps_individual(
                                jug_sel, sesion_sel, kpis_abs, kpis_rel, img_paths,
                                st.session_state.get('escudo_equipo'), foto_b64, pos_jug
                            )
                            st.session_state[pdf_key] = pdf_bytes
                            st.rerun()
                else:
                    c_down1, c_down2 = st.columns(2)
                    with c_down1:
                        st.download_button(
                            label=":material/download: Descargar PDF",
                            data=st.session_state[pdf_key],
                            file_name=f"GPS_{jug_sel}_{sesion_sel}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    with c_down2:
                        if st.button(":material/delete: Descartar PDF", use_container_width=True):
                            del st.session_state[pdf_key]
                            st.rerun()
