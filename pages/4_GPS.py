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

def generar_grafico_radar_gps(df_target, df_ref, label_target, label_ref):
    """ Radar para Perfil de Rendimiento (Objetivo vs 100% de Referencia) """
    df_t_val = df_target[df_target['DIS'] > 0].copy()
    df_r_val = df_ref[df_ref['DIS'] > 0].copy()
    
    if df_t_val.empty or df_r_val.empty: return None

    for df in [df_t_val, df_r_val]:
        for col in ['DIS', 'DIS AI', 'ACC', 'Nº SPR']:
            if f'{col}/min' not in df.columns:
                df[f'{col}/min'] = np.where(df['MIN'] > 0, df[col] / df['MIN'], 0)

    medias_ref = {
        'ACC/min': df_r_val['ACC/min'].mean(),
        'VMAX': df_r_val['VMAX'].mean(),
        'V_Media': (df_r_val['DIS'].sum() / df_r_val['MIN'].sum()) * 60 if df_r_val['MIN'].sum() > 0 else 0,
        'DIS/min': df_r_val['DIS/min'].mean(),
        'Nº SPR/min': df_r_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_r_val['DIS AI/min'].mean()
    }

    medias_target = {
        'ACC/min': df_t_val['ACC/min'].mean(),
        'VMAX': df_t_val['VMAX'].mean(),
        'V_Media': (df_t_val['DIS'].sum() / df_t_val['MIN'].sum()) * 60 if df_t_val['MIN'].sum() > 0 else 0,
        'DIS/min': df_t_val['DIS/min'].mean(),
        'Nº SPR/min': df_t_val['Nº SPR/min'].mean(),
        'DIS AI/min': df_t_val['DIS AI/min'].mean()
    }

    categorias = ['Aceleraciones (>3)/min', 'Velocidad Máxima', 'Velocidad Media', 'Distancia/min', 'Sprints/min', 'HSR (>21)/min']
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min']
    
    valores_target = []
    valores_referencia = [100] * 6

    for clave in claves:
        m_ref, m_tar = medias_ref[clave], medias_target[clave]
        porcentaje = (m_tar / m_ref) * 100 if m_ref > 0 else 100
        valores_target.append(round(porcentaje, 1))

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores_referencia + [valores_referencia[0]], theta=categorias + [categorias[0]],
        fill='toself', name=label_ref, line=dict(color='rgba(150, 150, 150, 0.8)', width=2), fillcolor='rgba(200, 200, 200, 0.2)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=valores_target + [valores_target[0]], theta=categorias + [categorias[0]],
        fill='toself', name=label_target, line=dict(color='#00b4d8', width=3), fillcolor='rgba(0, 180, 216, 0.3)'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max(150, max(valores_target) + 20)])),
        title=f"<b>Perfil Radar: {label_target} vs {label_ref}</b>",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    return fig

def generar_radar_comparador(dict_medias, usar_C):
    """ 
    Radar para Comparador Múltiple (A vs B vs C)
    Normaliza cada métrica al valor máximo de los perfiles seleccionados (Máx = 100%)
    """
    categorias = ['Aceleraciones (>3)/min', 'Velocidad Máxima', 'Velocidad Media', 'Distancia/min', 'Sprints/min', 'HSR (>21)/min']
    claves = ['ACC/min', 'VMAX', 'V_Media', 'DIS/min', 'Nº SPR/min', 'DIS AI/min']
    
    # Preparar datos
    datos_graf = {'A': [], 'B': [], 'C': []}
    
    for clave in claves:
        val_A = dict_medias['A'].get(clave, 0)
        val_B = dict_medias['B'].get(clave, 0)
        val_C = dict_medias['C'].get(clave, 0) if usar_C else 0
        
        # Encontrar el máximo para esta métrica
        max_val = max(val_A, val_B, val_C) if usar_C else max(val_A, val_B)
        
        # Calcular porcentajes respecto al máximo
        if max_val > 0:
            datos_graf['A'].append((val_A / max_val) * 100)
            datos_graf['B'].append((val_B / max_val) * 100)
            if usar_C: datos_graf['C'].append((val_C / max_val) * 100)
        else:
            datos_graf['A'].append(0)
            datos_graf['B'].append(0)
            if usar_C: datos_graf['C'].append(0)

    fig = go.Figure()

    # Perfil A (Azul)
    fig.add_trace(go.Scatterpolar(
        r=datos_graf['A'] + [datos_graf['A'][0]], theta=categorias + [categorias[0]],
        fill='toself', name=dict_medias['A_label'], line=dict(color='#00b4d8', width=2), fillcolor='rgba(0, 180, 216, 0.2)'
    ))
    
    # Perfil B (Rojo)
    fig.add_trace(go.Scatterpolar(
        r=datos_graf['B'] + [datos_graf['B'][0]], theta=categorias + [categorias[0]],
        fill='toself', name=dict_medias['B_label'], line=dict(color='#ff4b4b', width=2), fillcolor='rgba(255, 75, 75, 0.2)'
    ))

    # Perfil C (Verde)
    if usar_C:
        fig.add_trace(go.Scatterpolar(
            r=datos_graf['C'] + [datos_graf['C'][0]], theta=categorias + [categorias[0]],
            fill='toself', name=dict_medias['C_label'], line=dict(color='#28a745', width=2), fillcolor='rgba(40, 167, 69, 0.2)'
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 110])),
        title="<b>Comparativa Multidimensional (Valores relativos al Máximo)</b>",
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

dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", p.get("POS", "")) for p in st.session_state.get("plantilla", [])}

datos_gps = []
for s in st.session_state.sesiones:
    if s.get("informe_generado"):
        es_partido = "Partido" in s["tipo"]
        tipo_str = "Partido" if es_partido else "Entrenamiento"
        
        disp_s_clean = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
        nombre_ses_completo = f"{s['fecha']} | {s.get('nombre_dinamico', s['tipo'])}"
        if s.get("subtitulo_dinamico"): nombre_ses_completo += f" ({s['subtitulo_dinamico']})"
        
        for d in s["datos_informe"]:
            jug_nombre = d["JUGADOR"]
            if disp_s_clean.get(limpiar_nombre(jug_nombre), "Disponible") in ["Disponible", "Titular", "Suplente"] and float(d.get("DIS", 0)) > 0:
                min_val = max(float(d.get("MIN_GPS", d.get("MIN", 1))), 1)
                id_micro = mapa_micros.get(obtener_numero_semana(s["fecha"]), obtener_numero_semana(s["fecha"]))
                
                datos_gps.append({
                    "FECHA": s["fecha"],
                    "TIPO": tipo_str,
                    "MD": s["descripcion"],
                    "Microciclo": f"Microciclo {id_micro}",
                    "Nombre_Sesion": nombre_ses_completo,
                    "JUGADOR": d["JUGADOR"],
                    "POS": d.get("POS", ""),
                    "POS_ESP": dict_pos_esp.get(limpiar_nombre(jug_nombre), d.get("POS", "")),
                    "MIN": min_val,
                    "DIS": float(d.get("DIS", 0)),
                    "DIS AI": float(d.get("HID >21", d.get("DIS AI", 0))),
                    "Nº SPR": float(d.get("SPR >24", d.get("Nº SPR", 0))),
                    "ACC": float(d.get("ACC >3", d.get("ACC", 0))),
                    "DCC": float(d.get("DCC >3", d.get("DCC", 0))),
                    "VMAX": float(d.get("V_Max", d.get("VMAX", 0))),
                    "Z1": float(d.get("Z1", 0)), "Z2": float(d.get("Z2", 0)), "Z3": float(d.get("Z3", 0)),
                    "Z4": float(d.get("Z4", 0)), "Z5": float(d.get("Z5", 0)), "Z6": float(d.get("Z6", 0))
                })
                
df_gps = pd.DataFrame(datos_gps)

tab_gps_perf, tab_gps_comp = st.tabs(["📈 Perfil de Rendimiento", "⚖️ Comparador"])

if df_gps.empty:
    st.info("No hay datos de GPS registrados todavía. Procesa datos en alguna sesión para visualizarlos aquí.")
else:
    for c in ['DIS', 'DIS AI', 'ACC', 'DCC', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']:
        df_gps[f'{c}/min'] = np.where(df_gps['MIN'] > 0, df_gps[c] / df_gps['MIN'], 0)

    lista_jugs = sorted(df_gps['JUGADOR'].unique())
    lista_pos = ["POR", "DEF", "MED", "ATA"]
    lista_pos_esp = ["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"]
    lista_mds = ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"]
    lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
    lista_entrenos = sorted(df_gps[df_gps['TIPO'] == 'Entrenamiento']['Nombre_Sesion'].unique(), reverse=True)
    lista_partidos = sorted(df_gps[df_gps['TIPO'] == 'Partido']['Nombre_Sesion'].unique(), reverse=True)
    lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)

    def aplicar_filtros_gps(df, tiempo, tipo, sel_micro, sel_sesion, nivel, pos, pos_esp, jug):
        res = df.copy()
        if tiempo == "Promedio de microciclo" and sel_micro != "TODOS": res = res[res['Microciclo'] == sel_micro]
        elif tiempo == "Sesión" and sel_sesion != "TODOS": res = res[res['Nombre_Sesion'] == sel_sesion]
        
        if tipo != "Todas": res = res[res['TIPO'] == tipo]
        if sel_sesion != "TODOS": res = res[res['Nombre_Sesion'] == sel_sesion]

        if nivel == "Por jugador" and jug != "TODOS": res = res[res['JUGADOR'] == jug]
        elif nivel == "Por posición general": res = res[res['POS'] == pos]
        elif nivel == "Por posición específica": res = res[res['POS_ESP'] == pos_esp]
        return res

    # ==========================================
    # PESTAÑA 1: PERFIL DE RENDIMIENTO
    # ==========================================
    with tab_gps_perf:
        with st.expander("🔍 Filtros de Rendimiento", expanded=False):
            c_f1, c_f2, c_f3 = st.columns([1.2, 1.2, 1.6])
            
            with c_f1: f_tiempo = st.radio("Analizar:", ["Promedio total", "Promedio de microciclo", "Sesión"], key="p_tiempo")
            with c_f2: f_tipo = st.radio("Tipo de Sesión:", ["Todas", "Entrenamiento", "Partido"], key="p_tipo")

            f_sel_micro, f_sel_sesion = "TODOS", "TODOS"
            with c_f3:
                if f_tiempo == "Promedio de microciclo":
                    f_sel_micro = st.selectbox("Seleccionar microciclo:", lista_micros, key="p_sel_micro")
                elif f_tipo == "Entrenamiento":
                    f_sel_sesion = st.selectbox("Seleccionar entreno:", lista_entrenos if f_tiempo=="Sesión" else ["TODOS"]+lista_entrenos, key="p_sel_entreno")
                elif f_tipo == "Partido":
                    f_sel_sesion = st.selectbox("Seleccionar partido:", lista_partidos if f_tiempo=="Sesión" else ["TODOS"]+lista_partidos, key="p_sel_partido")
                elif f_tiempo == "Sesión" and f_tipo == "Todas":
                    f_sel_sesion = st.selectbox("Seleccionar sesión:", lista_todas_ses, key="p_sel_ses_todas")

            st.markdown("---")
            c_n1, c_n2 = st.columns([2.2, 1.2])
            with c_n1: f_nivel = st.radio("Analizar por:", ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], horizontal=True, key="p_niv")

            f_jug, f_pos, f_pos_esp = "TODOS", "DEF", "Central"
            with c_n2:
                if f_nivel == "Por posición general": f_pos = st.selectbox("Posición general:", lista_pos, key="p_pos")
                elif f_nivel == "Por posición específica": f_pos_esp = st.selectbox("Posición específica:", lista_pos_esp, key="p_pos_esp")
                elif f_nivel == "Por jugador": f_jug = st.selectbox("Jugador:", ["TODOS"] + lista_jugs, key="p_jug")

        df_perfil = aplicar_filtros_gps(df_gps, f_tiempo, f_tipo, f_sel_micro, f_sel_sesion, f_nivel, f_pos, f_pos_esp, f_jug)

        if df_perfil.empty:
            st.warning("No hay datos para esta combinación de filtros.")
        else:
            # Lógica dinámica del Radar del perfil
            mostrar_radar, df_radar_target, df_radar_ref, label_radar_target, label_radar_ref = True, pd.DataFrame(), pd.DataFrame(), "", ""

            if f_nivel == "Por jugador" and f_jug != "TODOS":
                pos_exacta = dict_pos_esp.get(f_jug, 'Desconocida')
                jugadores_misma_pos = [j for j, p in dict_pos_esp.items() if p == pos_exacta]
                df_radar_target = df_perfil
                df_radar_ref = df_gps[df_gps['JUGADOR'].isin(jugadores_misma_pos)]
                if f_tipo != "Todas": df_radar_ref = df_radar_ref[df_radar_ref['TIPO'] == f_tipo]
                label_radar_target, label_radar_ref = f_jug, f"Media Posición ({pos_exacta})"

            elif f_tiempo == "Promedio total":
                if f_nivel == "Equipo completo": mostrar_radar = False
                else:
                    df_radar_target = df_perfil
                    df_base = df_gps[df_gps['TIPO'] == f_tipo] if f_tipo != "Todas" else df_gps.copy()
                    if f_nivel == "Por posición general":
                        df_radar_ref = df_base[df_base['POS'] != f_pos]
                        label_radar_target, label_radar_ref = f"Posición {f_pos}", f"Resto del Equipo"
                    elif f_nivel == "Por posición específica":
                        df_radar_ref = df_base[df_base['POS_ESP'] != f_pos_esp]
                        label_radar_target, label_radar_ref = f"Posición {f_pos_esp}", f"Resto del Equipo"

            elif f_tiempo == "Promedio de microciclo":
                df_radar_target = df_perfil
                df_base = df_gps[df_gps['TIPO'] == f_tipo] if f_tipo != "Todas" else df_gps.copy()
                if f_nivel == "Por posición general": df_base = df_base[df_base['POS'] == f_pos]
                elif f_nivel == "Por posición específica": df_base = df_base[df_base['POS_ESP'] == f_pos_esp]
                
                df_radar_ref = df_base[df_base['Microciclo'] != f_sel_micro]
                lbl_scope = f_pos if f_nivel == "Por posición general" else (f_pos_esp if f_nivel == "Por posición específica" else "Equipo Completo")
                label_radar_target, label_radar_ref = f"{lbl_scope} ({f_sel_micro})", f"{lbl_scope} (Resto Micros)"

            elif f_tiempo == "Sesión":
                df_radar_target = df_perfil
                df_sesion_sel = df_gps[df_gps['Nombre_Sesion'] == f_sel_sesion]
                if not df_sesion_sel.empty:
                    tipo_ses = df_sesion_sel.iloc[0]['TIPO']
                    df_base = df_gps[(df_gps['TIPO'] == "Entrenamiento") & (df_gps['MD'] == df_sesion_sel.iloc[0]['MD'])] if tipo_ses == "Entrenamiento" else df_gps[df_gps['TIPO'] == "Partido"]
                    if f_nivel == "Por posición general": df_base = df_base[df_base['POS'] == f_pos]
                    elif f_nivel == "Por posición específica": df_base = df_base[df_base['POS_ESP'] == f_pos_esp]
                    
                    df_radar_ref = df_base[df_base['Nombre_Sesion'] != f_sel_sesion]
                    lbl_scope = f_pos if f_nivel == "Por posición general" else (f_pos_esp if f_nivel == "Por posición específica" else "Equipo Completo")
                    label_radar_target, label_radar_ref = f"{lbl_scope} (Actual)", f"{lbl_scope} (Referencia)"
                else: mostrar_radar = False

            if mostrar_radar and not df_radar_target.empty and not df_radar_ref.empty:
                fig_radar = generar_grafico_radar_gps(df_radar_target, df_radar_ref, label_radar_target, label_radar_ref)
                if fig_radar: st.plotly_chart(fig_radar, use_container_width=True)

            kpis = df_perfil[['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].mean()
            kpis_rel = df_perfil[['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']].mean()

            st.markdown("---")
            st.markdown("#### 🚀 Promedios Absolutos (Totales)")
            kp1, kp2, kp3, kp4, kp5, kp6, kp7 = st.columns(7)
            kp1.metric("Min", f"{kpis['MIN']:.1f}")
            kp2.metric("DIS (km)", f"{kpis['DIS']:.2f}")
            kp3.metric("HSR (m)", f"{kpis['DIS AI']:.1f}")
            kp4.metric("Sprints", f"{kpis['Nº SPR']:.1f}")
            kp5.metric("ACC", f"{kpis['ACC']:.1f}")
            kp6.metric("DCC", f"{kpis['DCC']:.1f}")
            kp7.metric("V.Max", f"{kpis['VMAX']:.1f}")

    # ==========================================
    # PESTAÑA 2: COMPARADOR (AHORA CON FILTROS COMPLETOS Y RADAR MULTIPLE)
    # ==========================================
    with tab_gps_comp:
        st.markdown("#### ⚖️ Configurar Perfiles a Comparar")
        
        # Helper para generar las columnas de filtros compactas
        def render_columna_filtro_comparador(prefijo, titulo, color_hex):
            st.markdown(f"**<span style='color:{color_hex}'>■</span> {titulo}**", unsafe_allow_html=True)
            t_tiempo = st.selectbox("Analizar:", ["Promedio total", "Promedio de microciclo", "Sesión"], key=f"c_{prefijo}_tiempo")
            t_tipo = st.selectbox("Tipo:", ["Todas", "Entrenamiento", "Partido"], key=f"c_{prefijo}_tipo")
            
            t_sel_micro, t_sel_sesion = "TODOS", "TODOS"
            if t_tiempo == "Promedio de microciclo":
                t_sel_micro = st.selectbox("Microciclo:", lista_micros, key=f"c_{prefijo}_micro")
            elif t_tipo == "Entrenamiento":
                t_sel_sesion = st.selectbox("Entrenamiento:", lista_entrenos if t_tiempo=="Sesión" else ["TODOS"]+lista_entrenos, key=f"c_{prefijo}_entreno")
            elif t_tipo == "Partido":
                t_sel_sesion = st.selectbox("Partido:", lista_partidos if t_tiempo=="Sesión" else ["TODOS"]+lista_partidos, key=f"c_{prefijo}_partido")
            elif t_tiempo == "Sesión" and t_tipo == "Todas":
                t_sel_sesion = st.selectbox("Sesión:", lista_todas_ses, key=f"c_{prefijo}_ses_todas")

            t_nivel = st.selectbox("Analizar por:", ["Equipo completo", "Por posición general", "Por posición específica", "Por jugador"], key=f"c_{prefijo}_niv")
            t_jug, t_pos, t_pos_esp = "TODOS", "DEF", "Central"
            
            if t_nivel == "Por posición general": t_pos = st.selectbox("Posición Gen:", lista_pos, key=f"c_{prefijo}_pos")
            elif t_nivel == "Por posición específica": t_pos_esp = st.selectbox("Posición Esp:", lista_pos_esp, key=f"c_{prefijo}_pos_esp")
            elif t_nivel == "Por jugador": t_jug = st.selectbox("Jugador:", lista_jugs, key=f"c_{prefijo}_jug")
            
            # Generar una etiqueta dinámica para la leyenda
            lbl_nivel = t_jug if t_nivel == "Por jugador" else (t_pos if t_nivel == "Por posición general" else (t_pos_esp if t_nivel == "Por posición específica" else "Equipo"))
            lbl_ctx = t_sel_micro if t_tiempo == "Promedio de microciclo" else (t_sel_sesion if t_tiempo == "Sesión" else ("Entrenos" if t_tipo == "Entrenamiento" else ("Partidos" if t_tipo == "Partido" else "Total")))
            label_final = f"{lbl_nivel} ({lbl_ctx})"

            return aplicar_filtros_gps(df_gps, t_tiempo, t_tipo, t_sel_micro, t_sel_sesion, t_nivel, t_pos, t_pos_esp, t_jug), label_final

        colA, colB, colC = st.columns(3)
        with colA: df_A, lbl_A = render_columna_filtro_comparador("A", "Perfil A", "#00b4d8")
        with colB: df_B, lbl_B = render_columna_filtro_comparador("B", "Perfil B", "#ff4b4b")
        with colC:
            usar_C = st.checkbox("Activar Perfil C", value=False)
            if usar_C:
                df_C, lbl_C = render_columna_filtro_comparador("C", "Perfil C", "#28a745")
            else:
                df_C, lbl_C = pd.DataFrame(), ""

        if df_A.empty or df_B.empty or (usar_C and df_C.empty):
            st.warning("⚠️ Uno de los perfiles activos no tiene datos en el histórico. Revisa los filtros.")
        else:
            st.markdown("---")
            
            # Cálculo de medias
            metrics_radar = ['ACC/min', 'VMAX', 'DIS/min', 'Nº SPR/min', 'DIS AI/min', 'MIN', 'DIS']
            mean_A = df_A[metrics_radar].mean().to_dict()
            mean_B = df_B[metrics_radar].mean().to_dict()
            mean_C = df_C[metrics_radar].mean().to_dict() if usar_C else {}
            
            # Añadir Velocidad Media (Formula: (DIS / MIN) * 60)
            def calc_vmedia(df): return (df['DIS'].sum() / df['MIN'].sum()) * 60 if df['MIN'].sum() > 0 else 0
            mean_A['V_Media'] = calc_vmedia(df_A)
            mean_B['V_Media'] = calc_vmedia(df_B)
            if usar_C: mean_C['V_Media'] = calc_vmedia(df_C)

            dict_medias_radar = {
                'A': mean_A, 'A_label': lbl_A,
                'B': mean_B, 'B_label': lbl_B,
                'C': mean_C, 'C_label': lbl_C
            }

            # 1. Gráfico Radar Comparador
            st.markdown("#### 🕸️ Radar Comparativo")
            fig_comp = generar_radar_comparador(dict_medias_radar, usar_C)
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.markdown("---")

            # 2. Tabla Comparativa
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
