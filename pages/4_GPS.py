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
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    if st.button("Ir al Login principal"):
        st.session_state.clear()
        st.rerun()
    st.stop()

aplicar_color_sidebar()

def generar_grafico_radar_gps(df_target, df_ref, label_target, label_ref):
    """
    Genera un gráfico de radar universal:
    - df_target: Datos del grupo/jugador/sesión a evaluar (Línea Azul)
    - df_ref: Datos de referencia/comparación (Sombra Gris - 100%)
    """
    df_t_val = df_target[df_target['DIS'] > 0].copy()
    df_r_val = df_ref[df_ref['DIS'] > 0].copy()
    
    if df_t_val.empty or df_r_val.empty:
        return None

    for df in [df_t_val, df_r_val]:
        min_efectivo_radar = np.where(df['MIN_GPS'] > 0, df['MIN_GPS'], df['MIN'])
        for col in ['DIS', 'DIS AI', 'ACC', 'Nº SPR']:
            if f'{col}/min' not in df.columns:
                df[f'{col}/min'] = np.where(min_efectivo_radar > 0, df[col] / min_efectivo_radar, 0)
    
    # Corrección de la Velocidad Media para usar el tiempo de GPS real
    min_ref_sum = np.where(df_r_val['MIN_GPS'] > 0, df_r_val['MIN_GPS'], df_r_val['MIN']).sum()
    min_tar_sum = np.where(df_t_val['MIN_GPS'] > 0, df_t_val['MIN_GPS'], df_t_val['MIN']).sum()
    
    medias_ref = {
        'ACC/min': df_r_val['ACC/min'].mean(),
        'VMAX': df_r_val['VMAX'].mean(),
        'V_Media': (df_r_val['DIS'].sum() / min_ref_sum) * 60 if min_ref_sum > 0 else 0,
        'DIS/min': df_r_val['DIS/min'].mean(),
        'Nº SPR/min': df_r_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_r_val['DIS AI/min'].mean()
    }
    
    medias_target = {
        'ACC/min': df_t_val['ACC/min'].mean(),
        'VMAX': df_t_val['VMAX'].mean(),
        'V_Media': (df_t_val['DIS'].sum() / min_tar_sum) * 60 if min_tar_sum > 0 else 0,
        'DIS/min': df_t_val['DIS/min'].mean(),
        'Nº SPR/min': df_t_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_t_val['DIS AI/min'].mean()
    }

    categorias = [
        'Aceleraciones (>3)/min', 
        'Velocidad Máxima (Pico)', 
        'Velocidad Media', 
        'Distancia/min', 
        'Sprints/min', 
        'HSR (>21)/min'
    ]
    
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min']
    
    valores_target = []
    valores_referencia = [100] * 6

    for clave in claves:
        m_ref = medias_ref[clave]
        m_tar = medias_target[clave]
        
        if m_ref > 0:
            porcentaje = (m_tar / m_ref) * 100
        else:
            porcentaje = 100
        valores_target.append(round(porcentaje, 1))

    categorias_radar = categorias + [categorias[0]]
    valores_target_radar = valores_target + [valores_target[0]]
    valores_ref_radar = valores_referencia + [valores_referencia[0]]

    fig = go.Figure()

    # Trazado de referencia (Gris)
    fig.add_trace(go.Scatterpolar(
        r=valores_ref_radar,
        theta=categorias_radar,
        fill='toself',
        name=label_ref,
        line=dict(color='rgba(150, 150, 150, 0.8)', width=2),
        fillcolor='rgba(200, 200, 200, 0.2)'
    ))

    # Trazado del objetivo (Azul)
    fig.add_trace(go.Scatterpolar(
        r=valores_target_radar,
        theta=categorias_radar,
        fill='toself',
        name=label_target,
        line=dict(color='#00b4d8', width=3),
        fillcolor='rgba(0, 180, 216, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(150, max(valores_target) + 20)]
            )
        ),
        title=f"<b>Perfil Radar: {label_target} vs {label_ref}</b>",
        showlegend=True,
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig
def generar_radar_comparador(dict_medias, usar_C):
    """ 
    Radar para Comparador Múltiple (A vs B vs C).
    Normaliza cada métrica al valor máximo de los perfiles seleccionados (Máx = 100%).
    """
    categorias = ['Aceleraciones (>3)/min', 'Velocidad Máxima', 'Velocidad Media', 'Distancia/min', 'Sprints/min', 'HSR (>21)/min']
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min']
    
    datos_graf = {'A': [], 'B': [], 'C': []}
    
    for clave in claves:
        val_A = dict_medias['A'].get(clave, 0)
        val_B = dict_medias['B'].get(clave, 0)
        val_C = dict_medias['C'].get(clave, 0) if usar_C else 0
        
        # Encontrar el valor máximo entre los perfiles activos para escalar a 100%
        max_val = max(val_A, val_B, val_C) if usar_C else max(val_A, val_B)
        
        if max_val > 0:
            datos_graf['A'].append((val_A / max_val) * 100)
            datos_graf['B'].append((val_B / max_val) * 100)
            if usar_C:
                datos_graf['C'].append((val_C / max_val) * 100)
        else:
            datos_graf['A'].append(0)
            datos_graf['B'].append(0)
            if usar_C:
                datos_graf['C'].append(0)

    fig = go.Figure()

    # Perfil A (Azul)
    fig.add_trace(go.Scatterpolar(
        r=datos_graf['A'] + [datos_graf['A'][0]], 
        theta=categorias + [categorias[0]],
        fill='toself', 
        name=dict_medias['A_label'], 
        line=dict(color='#00b4d8', width=2), 
        fillcolor='rgba(0, 180, 216, 0.2)'
    ))
    
    # Perfil B (Rojo)
    fig.add_trace(go.Scatterpolar(
        r=datos_graf['B'] + [datos_graf['B'][0]], 
        theta=categorias + [categorias[0]],
        fill='toself', 
        name=dict_medias['B_label'], 
        line=dict(color='#ff4b4b', width=2), 
        fillcolor='rgba(255, 75, 75, 0.2)'
    ))

    # Perfil C (Verde)
    if usar_C:
        fig.add_trace(go.Scatterpolar(
            r=datos_graf['C'] + [datos_graf['C'][0]], 
            theta=categorias + [categorias[0]],
            fill='toself', 
            name=dict_medias['C_label'], 
            line=dict(color='#28a745', width=2), 
            fillcolor='rgba(40, 167, 69, 0.2)'
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 110])),
        title="<b>Comparativa Multidimensional (100% = Valor Máximo Relativo)</b>",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

st.subheader("📡 GPS")

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
    df_gps = df_gps[df_gps['DIS'] > 0]
    
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

tab_gps_perf, tab_gps_comp = st.tabs(["📈 Perfil de Rendimiento", "⚖️ Comparador"])

if df_gps.empty:
    st.info("No hay datos de GPS registrados todavía. Procesa datos en alguna sesión para visualizarlos aquí.")
else:
    cols_dinamicas = ['DIS', 'DIS AI', 'ACC', 'DCC', 'Nº SPR', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
    for c in cols_dinamicas:
        # Usamos MIN_GPS prioritariamente. Si por algún error de subida está a 0 pero hay distancia, usamos MIN como salvavidas antibloqueo.
        min_efectivo = np.where(df_gps['MIN_GPS'] > 0, df_gps['MIN_GPS'], df_gps['MIN'])
        df_gps[f'{c}/min'] = np.where(min_efectivo > 0, df_gps[c] / min_efectivo, 0)

    lista_jugs = sorted(df_gps['JUGADOR'].unique())
    lista_pos = ["POR", "DEF", "MED", "ATA"]
    lista_pos_esp = ["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"]
    lista_mds = ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"]

    def aplicar_filtros_gps(df, target_tipo="Todas", target_md="TODOS", target_nivel="Equipo completo", target_jug="TODOS", target_pos="DEF", target_tiempo="Promedio total", target_sel_micro="TODOS", target_sel_sesion="TODOS", target_pos_esp="Central"):
        res = df.copy()
        
        if target_tiempo == "Promedio de microciclo" and target_sel_micro != "TODOS":
            res = res[res['Microciclo'] == target_sel_micro]
        elif target_tiempo == "Sesión" and target_sel_sesion != "TODOS":
            res = res[res['Nombre_Sesion'] == target_sel_sesion]
            
        if target_tipo != "Todas":
            # Ahora busca la coincidencia exacta de la categoría elegida
            res = res[res['TIPO'] == target_tipo]
            if target_tipo == "Entrenamiento" and target_md != "TODOS":
                res = res[res['MD'] == target_md]

        if target_nivel == "Por jugador":
            if target_jug != "TODOS": res = res[res['JUGADOR'] == target_jug]
        elif target_nivel == "Por posición general":
            res = res[res['POS'] == target_pos]
        elif target_nivel == "Por posición específica":
            res = res[res['POS_ESP'] == target_pos_esp]

        return res

    with tab_gps_perf:
        # --- FILTROS PLEGABLES MEDIANTE EXPANDER ---
        with st.expander("🔍 Filtros de Rendimiento", expanded=False):
            c_f1, c_f2, c_f3 = st.columns([1.2, 1.2, 1.6])
            
            with c_f1:
                f_tiempo = st.radio(
                    "Analizar:", 
                    ["Promedio total", "Promedio de microciclo", "Sesión"], 
                    key="p_tiempo"
                )
                
            with c_f2:
                f_tipo = st.radio(
                    "Tipo de Sesión:", 
                    ["Todas", "Entrenamiento", "Partido Oficial", "Partido Amistoso"], 
                    key="p_tipo"
                )

            f_sel_micro = "TODOS"
            f_sel_sesion = "TODOS"
            f_md = "TODOS"

            with c_f3:
                if f_tiempo == "Promedio de microciclo":
                    lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
                    f_sel_micro = st.selectbox("Seleccionar microciclo:", lista_micros, key="p_sel_micro")
                
                if f_tipo == "Entrenamiento":
                    lista_entrenos = sorted(df_gps[df_gps['TIPO'] == 'Entrenamiento']['Nombre_Sesion'].unique(), reverse=True)
                    if lista_entrenos:
                        if f_tiempo == "Sesión":
                            f_sel_sesion = st.selectbox("Seleccionar entrenamiento:", lista_entrenos, key="p_sel_entreno")
                        else:
                            f_sel_sesion = st.selectbox("Seleccionar entrenamiento (Opcional):", ["TODOS"] + lista_entrenos, key="p_sel_entreno")
                    else:
                        st.info("No hay entrenamientos registrados.")
                        
                elif f_tipo in ["Partido Oficial", "Partido Amistoso"]:
                    lista_partidos = sorted(df_gps[df_gps['TIPO'] == f_tipo]['Nombre_Sesion'].unique(), reverse=True)
                    if lista_partidos:
                        if f_tiempo == "Sesión":
                            f_sel_sesion = st.selectbox(f"Seleccionar {f_tipo.lower()}:", lista_partidos, key="p_sel_partido")
                        else:
                            f_sel_sesion = st.selectbox(f"Seleccionar {f_tipo.lower()} (Opcional):", ["TODOS"] + lista_partidos, key="p_sel_partido")
                    else:
                        st.info(f"No hay registros de {f_tipo.lower()}.")

                elif f_tiempo == "Sesión" and f_tipo == "Todas":
                    lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                    f_sel_sesion = st.selectbox("Seleccionar sesión:", lista_todas_ses, key="p_sel_ses_todas")

            st.markdown("---")

            c_n1, c_n2 = st.columns([2.2, 1.2])
            
            with c_n1:
                f_nivel = st.radio(
                    "Analizar por:", 
                    ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], 
                    horizontal=True, 
                    key="p_niv"
                )

            f_jug = "TODOS"
            f_pos = "DEF"
            f_pos_esp = "Central"

            with c_n2:
                if f_nivel == "Por posición general":
                    f_pos = st.selectbox("Seleccionar posición general:", lista_pos, key="p_pos")
                elif f_nivel == "Por posición específica":
                    f_pos_esp = st.selectbox("Seleccionar posición específica:", lista_pos_esp, key="p_pos_esp")
                elif f_nivel == "Por jugador":
                    f_jug = st.selectbox("Seleccionar jugador:", ["TODOS"] + lista_jugs, key="p_jug")

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
            st.warning("No hay datos para esta combinación de filtros.")
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
                df_radar_ref = df_gps[df_gps['JUGADOR'].isin(jugadores_misma_pos)].copy()
                if f_tipo != "Todas":
                    df_radar_ref = df_radar_ref[df_radar_ref['TIPO'] == f_tipo]
                
                label_radar_target = f_jug
                label_radar_ref = f"Media Posición ({pos_exacta})"

            elif f_tiempo == "Promedio total":
                if f_nivel == "Equipo completo":
                    mostrar_radar = False
                else:
                    df_radar_target = df_perfil
                    df_base = df_gps.copy()
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
                df_base_nivel = df_gps.copy()
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
                    
                    df_base_nivel = df_gps.copy()
                    if tipo_sesion_sel == "Entrenamiento":
                        df_base_nivel = df_base_nivel[(df_base_nivel['TIPO'] == "Entrenamiento") & (df_base_nivel['MD'] == md_sesion_sel)]
                        criterio_str = f"{md_sesion_sel}"
                    else:
                        # La referencia será exactamente el mismo tipo de partido que estás analizando
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
                    st.info("No hay suficientes datos GPS para generar la comparación radar.")

            # --- METRICAS KPI Y TABLAS ---
            kpis = df_perfil[['MIN_GPS', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].mean()
            kpis_rel = df_perfil[['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']].mean()

            st.markdown("---")
            st.markdown("#### 🚀 Promedios Absolutos (Totales)")
            kp1, kp2, kp3, kp4, kp5, kp6, kp7 = st.columns(7)
            kp1.metric("Minutos GPS", f"{kpis['MIN_GPS']:.1f}")
            kp2.metric("Distancia (km)", f"{kpis['DIS']:.2f}")
            kp3.metric("HSR (m)", f"{kpis['DIS AI']:.1f}")
            kp4.metric("Sprints", f"{kpis['Nº SPR']:.1f}")
            kp5.metric("Aceleraciones", f"{kpis['ACC']:.1f}")
            kp6.metric("Deceleraciones", f"{kpis['DCC']:.1f}")
            kp7.metric("V. Max (km/h)", f"{kpis['VMAX']:.1f}")

            st.markdown("#### ⏱️ Promedios Relativos (Por Minuto de GPS)")
            kr1, kr2, kr3, kr4 = st.columns(4)
            kr1.metric("m / min", f"{(kpis_rel['DIS/min']*1000):.1f}")
            kr2.metric("HSR m / min", f"{(kpis_rel['DIS AI/min']*1000):.2f}")
            kr3.metric("ACC / min", f"{kpis_rel['ACC/min']:.2f}")
            kr4.metric("DCC / min", f"{kpis_rel['DCC/min']:.2f}")
            
            st.markdown("---")
            st.markdown("#### 🔬 Desglose Exhaustivo de Zonas de Velocidad")
            
            todas_kpis = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
            todas_kpis_rel = [f'{c}/min' for c in ['DIS', 'DIS AI', 'ACC', 'DCC', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']]
            
            medias_abs = df_perfil[todas_kpis].mean().round(2).to_dict()
            medias_rel = df_perfil[todas_kpis_rel].mean().round(3).to_dict()
            
            df_detallado = pd.DataFrame({
                "Variable": ["Minutos GPS", "Distancia Total", "HSR (>21km/h)", "Sprints", "ACC", "DCC", "V. Máxima", "Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5", "Zona 6"],
                "Promedio Acumulado": [
                    medias_abs['MIN'], medias_abs['DIS'], medias_abs['DIS AI'], medias_abs['Nº SPR'], 
                    medias_abs['ACC'], medias_abs['DCC'], medias_abs['VMAX'],
                    medias_abs['Z1'], medias_abs['Z2'], medias_abs['Z3'], medias_abs['Z4'], medias_abs['Z5'], medias_abs['Z6']
                ],
                "Promedio por Minuto": [
                    "-", medias_rel['DIS/min'], medias_rel['DIS AI/min'], "-", 
                    medias_rel['ACC/min'], medias_rel['DCC/min'], "-",
                    medias_rel['Z1/min'], medias_rel['Z2/min'], medias_rel['Z3/min'], 
                    medias_rel['Z4/min'], medias_rel['Z5/min'], medias_rel['Z6/min']
                ]
            })
            mostrar_tabla_moderna(df_detallado.style.hide(axis="index"))

    # ==========================================
    # PESTAÑA 2: COMPARADOR (FILTROS PLEGABLES)
    # ==========================================
    with tab_gps_comp:
        # --- DESPLEGABLE CON LOS FILTROS DE LOS PERFILES ---
        with st.expander("⚖️ Configurar Perfiles a Comparar", expanded=False):
            
            # Función auxiliar para renderizar los filtros de cada perfil en su columna
            def render_columna_filtro_comparador(prefijo, titulo, color_hex):
                st.markdown(f"**<span style='color:{color_hex}'>■</span> {titulo}**", unsafe_allow_html=True)
                
                t_tiempo = st.selectbox("Analizar:", ["Promedio total", "Promedio de microciclo", "Sesión"], key=f"c_{prefijo}_tiempo")
                t_tipo = st.selectbox("Tipo de Sesión:", ["Todas", "Entrenamiento", "Partido Oficial", "Partido Amistoso"], key=f"c_{prefijo}_tipo")
                
                t_sel_micro, t_sel_sesion = "TODOS", "TODOS"
                
                if t_tiempo == "Promedio de microciclo":
                    lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
                    t_sel_micro = st.selectbox("Microciclo:", lista_micros, key=f"c_{prefijo}_micro")
                elif t_tipo == "Entrenamiento":
                    lista_entrenos = sorted(df_gps[df_gps['TIPO'] == 'Entrenamiento']['Nombre_Sesion'].unique(), reverse=True)
                    t_sel_sesion = st.selectbox("Entrenamiento:", lista_entrenos if t_tiempo=="Sesión" else ["TODOS"]+lista_entrenos, key=f"c_{prefijo}_entreno")
                elif t_tipo in ["Partido Oficial", "Partido Amistoso"]:
                    lista_partidos = sorted(df_gps[df_gps['TIPO'] == t_tipo]['Nombre_Sesion'].unique(), reverse=True)
                    t_sel_sesion = st.selectbox(f"{t_tipo}:", lista_partidos if t_tiempo=="Sesión" else ["TODOS"]+lista_partidos, key=f"c_{prefijo}_partido")
                elif t_tiempo == "Sesión" and t_tipo == "Todas":
                    lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                    t_sel_sesion = st.selectbox("Sesión:", lista_todas_ses, key=f"c_{prefijo}_ses_todas")

                t_nivel = st.selectbox("Analizar por:", ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], key=f"c_{prefijo}_niv")
                t_jug, t_pos, t_pos_esp = "TODOS", "DEF", "Central"
                
                if t_nivel == "Por posición general":
                    t_pos = st.selectbox("Posición General:", lista_pos, key=f"c_{prefijo}_pos")
                elif t_nivel == "Por posición específica":
                    t_pos_esp = st.selectbox("Posición Específica:", lista_pos_esp, key=f"c_{prefijo}_pos_esp")
                elif t_nivel == "Por jugador":
                    t_jug = st.selectbox("Jugador:", ["TODOS"] + lista_jugs, key=f"c_{prefijo}_jug")
                
                # Etiqueta dinámica para la leyenda del radar y la tabla
                lbl_nivel = t_jug if t_nivel == "Por jugador" else (t_pos if t_nivel == "Por posición general" else (t_pos_esp if t_nivel == "Por posición específica" else "Equipo"))
                lbl_ctx = t_sel_micro if t_tiempo == "Promedio de microciclo" else (t_sel_sesion if t_tiempo == "Sesión" else ("Entrenos" if t_tipo == "Entrenamiento" else ("Partidos" if t_tipo == "Partido" else "Total")))
                label_final = f"{lbl_nivel} ({lbl_ctx})"

                df_res = aplicar_filtros_gps(
                    df_gps, 
                    target_tiempo=t_tiempo, 
                    target_tipo=t_tipo, 
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
            st.warning("⚠️ Uno de los perfiles activos no tiene datos para los filtros seleccionados.")
        else:
            # 1. CÁLCULO DE MEDIAS PARA EL RADAR MULTI-PERFIL
            metrics_radar = ['ACC/min', 'VMAX', 'DIS/min', 'Nº SPR/min', 'DIS AI/min', 'MIN', 'DIS']
            mean_A = df_A[metrics_radar].mean().to_dict()
            mean_B = df_B[metrics_radar].mean().to_dict()
            mean_C = df_C[metrics_radar].mean().to_dict() if usar_C else {}
            
            def calc_vmedia(df): 
                return (df['DIS'].sum() / df['MIN'].sum()) * 60 if df['MIN'].sum() > 0 else 0

            mean_A['V_Media'] = calc_vmedia(df_A)
            mean_B['V_Media'] = calc_vmedia(df_B)
            if usar_C: 
                mean_C['V_Media'] = calc_vmedia(df_C)

            dict_medias_radar = {
                'A': mean_A, 'A_label': lbl_A,
                'B': mean_B, 'B_label': lbl_B,
                'C': mean_C, 'C_label': lbl_C
            }

            # 2. MOSTRAR RADAR
            st.markdown("#### 🕸️ Radar Comparativo")
            fig_comp = generar_radar_comparador(dict_medias_radar, usar_C)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.markdown("---")

            # 3. MOSTRAR TABLA COMPARATIVA
            st.markdown("#### 📊 Tabla Analítica")
            modo_comp = st.radio("¿Qué tipo de métricas quieres comparar en la tabla?", ["Absolutas (Totales)", "Relativas (Por Minuto)"], horizontal=True)
            
            if modo_comp == "Absolutas (Totales)":
                metrics_to_compare = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']
            else:
                metrics_to_compare = ['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']

            mean_t_A = df_A[metrics_to_compare].mean()
            mean_t_B = df_B[metrics_to_compare].mean()
            mean_t_C = df_C[metrics_to_compare].mean() if usar_C else None

            comp_data = []
            for m in metrics_to_compare:
                valA = mean_t_A[m] if not pd.isna(mean_t_A[m]) else 0
                valB = mean_t_B[m] if not pd.isna(mean_t_B[m]) else 0
                valC = mean_t_C[m] if usar_C and not pd.isna(mean_t_C[m]) else 0
                
                if 'DIS/min' in m or 'DIS AI/min' in m:
                    valA, valB, valC = valA * 1000, valB * 1000, valC * 1000

                diff_str_B = f"{(((valB - valA) / valA) * 100):+.1f}%" if valA > 0 else "N/A"
                diff_str_C = f"{(((valC - valA) / valA) * 100):+.1f}%" if usar_C and valA > 0 else "N/A"
                    
                fila = {
                    "Métrica": m.replace("/min", " (m/min)" if "DIS" in m else " / min"),
                    f"A: {lbl_A}": round(valA, 2),
                    f"B: {lbl_B}": round(valB, 2),
                    "Dif. B vs A": diff_str_B
                }
                if usar_C:
                    fila[f"C: {lbl_C}"] = round(valC, 2)
                    fila["Dif. C vs A"] = diff_str_C
                    
                comp_data.append(fila)
                
            columnas_estilo = ["Dif. B vs A", "Dif. C vs A"] if usar_C else ["Dif. B vs A"]
            mostrar_tabla_moderna(pd.DataFrame(comp_data).style.hide(axis="index").map(lambda x: "color: #28a745" if "+" in str(x) else ("color: #ff4b4b" if "-" in str(x) else ""), subset=columnas_estilo))
