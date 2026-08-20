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

def generar_grafico_radar_gps(df_gps_filtrado_jugador, df_gps_global_equipo, jugador_seleccionado, posicion_jugador):
    """
    1. Calcula las medias del jugador usando los datos filtrados.
    2. Calcula las medias del GRUPO DE POSICIÓN usando todo el histórico del equipo 
       para ese mismo contexto, sin filtrar por jugador.
    """
    df_jug_valido = df_gps_filtrado_jugador[df_gps_filtrado_jugador['DIS'] > 0].copy()
    if df_jug_valido.empty:
        return None

    for col in ['DIS', 'DIS AI', 'ACC', 'Nº SPR']:
        if f'{col}/min' not in df_jug_valido.columns:
            df_jug_valido[f'{col}/min'] = np.where(df_jug_valido['MIN'] > 0, df_jug_valido[col] / df_jug_valido['MIN'], 0)

    df_posicion = df_gps_global_equipo[df_gps_global_equipo['DIS'] > 0].copy()
    for col in ['DIS', 'DIS AI', 'ACC', 'Nº SPR']:
        if f'{col}/min' not in df_posicion.columns:
            df_posicion[f'{col}/min'] = np.where(df_posicion['MIN'] > 0, df_posicion[col] / df_posicion['MIN'], 0)

    if df_posicion.empty:
        return None

    medias_pos = {
        'ACC/min': df_posicion['ACC/min'].mean(),
        'VMAX': df_posicion['VMAX'].mean(),
        'V_Media': (df_posicion['DIS'].sum() / df_posicion['MIN'].sum()) * 60 if df_posicion['MIN'].sum() > 0 else 0,
        'DIS/min': df_posicion['DIS/min'].mean(),
        'Nº SPR/min': df_posicion['Nº SPR/min'].mean(),
        'DIS AI/min': df_posicion['DIS AI/min'].mean()
    }

    medias_jug = {
        'ACC/min': df_jug_valido['ACC/min'].mean(),
        'VMAX': df_jug_valido['VMAX'].mean(),
        'V_Media': (df_jug_valido['DIS'].sum() / df_jug_valido['MIN'].sum()) * 60 if df_jug_valido['MIN'].sum() > 0 else 0,
        'DIS/min': df_jug_valido['DIS/min'].mean(),
        'Nº SPR/min': df_jug_valido['Nº SPR/min'].mean(),
        'DIS AI/min': df_jug_valido['DIS AI/min'].mean()
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
    
    valores_jugador = []
    valores_referencia = [100, 100, 100, 100, 100, 100]

    for clave in claves:
        m_pos = medias_pos[clave]
        m_jug = medias_jug[clave]
        
        if m_pos > 0:
            porcentaje = (m_jug / m_pos) * 100
        else:
            porcentaje = 100
        valores_jugador.append(round(porcentaje, 1))

    categorias_radar = categorias + [categorias[0]]
    valores_jug_radar = valores_jugador + [valores_jugador[0]]
    valores_ref_radar = valores_referencia + [valores_referencia[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=valores_ref_radar,
        theta=categorias_radar,
        fill='toself',
        name=f'Media Posición ({posicion_jugador})',
        line=dict(color='rgba(150, 150, 150, 0.8)', width=2),
        fillcolor='rgba(200, 200, 200, 0.2)'
    ))

    fig.add_trace(go.Scatterpolar(
        r=valores_jug_radar,
        theta=categorias_radar,
        fill='toself',
        name=jugador_seleccionado,
        line=dict(color='#00b4d8', width=3),
        fillcolor='rgba(0, 180, 216, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(150, max(valores_jugador) + 20)]
            )
        ),
        title=f"<b>Perfil Físico: {jugador_seleccionado} vs Media de {posicion_jugador}</b>",
        showlegend=True,
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

# Mapa dinámico de posiciones específicas asignadas en la plantilla
dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", p.get("POS", "")) for p in st.session_state.get("plantilla", [])}

datos_gps = []
for s in st.session_state.sesiones:
    if s.get("informe_generado"):
        es_partido = "Partido" in s["tipo"]
        tipo_str = "Partido" if es_partido else "Entrenamiento"
        md_str = s["descripcion"]
        
        disp_s = s.get("disponibilidad", {})
        disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}

        nombre_ev = s.get("nombre_dinamico", s["tipo"])
        subtitulo = s.get("subtitulo_dinamico", "")
        nombre_sesion_completo = f"{s['fecha']} | {nombre_ev}"
        if subtitulo:
            nombre_sesion_completo += f" ({subtitulo})"
        
        for d in s["datos_informe"]:
            jug_nombre = d["JUGADOR"]
            est_jug = disp_s_clean.get(limpiar_nombre(jug_nombre), "Disponible")
            
            if est_jug in ["Disponible", "Titular", "Suplente"] and float(d.get("DIS", 0)) > 0:
                min_val = float(d.get("MIN_GPS", d.get("MIN", 0)))
                if min_val == 0: min_val = 1 
                
                num_sem = obtener_numero_semana(s["fecha"])
                id_micro = mapa_micros.get(num_sem, num_sem)
                pos_esp_val = dict_pos_esp.get(limpiar_nombre(jug_nombre), d.get("POS", ""))
                
                datos_gps.append({
                    "FECHA": s["fecha"],
                    "TIPO": tipo_str,
                    "MD": md_str,
                    "Microciclo": f"Microciclo {id_micro}",
                    "Nombre_Sesion": nombre_sesion_completo,
                    "JUGADOR": d["JUGADOR"],
                    "POS": d.get("POS", ""),
                    "POS_ESP": pos_esp_val,
                    "MIN": min_val,
                    "DIS": float(d.get("DIS", 0)),
                    "DIS AI": float(d.get("HID >21", d.get("DIS AI", 0))),
                    "Nº SPR": float(d.get("SPR >24", d.get("Nº SPR", 0))),
                    "ACC": float(d.get("ACC >3", d.get("ACC", 0))),
                    "DCC": float(d.get("DCC >3", d.get("DCC", 0))),
                    "VMAX": float(d.get("V_Max", d.get("VMAX", 0))),
                    "Z1": float(d.get("Z1", 0)),
                    "Z2": float(d.get("Z2", 0)),
                    "Z3": float(d.get("Z3", 0)),
                    "Z4": float(d.get("Z4", 0)),
                    "Z5": float(d.get("Z5", 0)),
                    "Z6": float(d.get("Z6", 0))
                })
                
df_gps = pd.DataFrame(datos_gps)

tab_gps_perf, tab_gps_comp = st.tabs(["📈 Perfil de Rendimiento", "⚖️ Comparador"])

if df_gps.empty:
    st.info("No hay datos de GPS registrados todavía. Procesa datos en alguna sesión para visualizarlos aquí.")
else:
    cols_dinamicas = ['DIS', 'DIS AI', 'ACC', 'DCC', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
    for c in cols_dinamicas:
        df_gps[f'{c}/min'] = np.where(df_gps['MIN'] > 0, df_gps[c] / df_gps['MIN'], 0)

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
            res = res[res['TIPO'] == target_tipo]
            if target_tipo == "Entrenamiento" and target_md != "TODOS":
                res = res[res['MD'] == target_md]

        if target_sel_sesion != "TODOS":
            res = res[res['Nombre_Sesion'] == target_sel_sesion]

        if target_nivel == "Por jugador":
            if target_jug != "TODOS": res = res[res['JUGADOR'] == target_jug]
        elif target_nivel == "Por posición general":
            res = res[res['POS'] == target_pos]
        elif target_nivel == "Por posición específica":
            res = res[res['POS_ESP'] == target_pos_esp]

        return res

    with tab_gps_perf:
        st.markdown("#### 🔍 Filtros de Rendimiento")
        
        # --- FILTROS SUPERIORES EN CASILLAS Y DROPDOWN CONTEXTUAL ---
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
                ["Todas", "Entrenamiento", "Partido"], 
                key="p_tipo"
            )

        f_sel_micro = "TODOS"
        f_sel_sesion = "TODOS"
        f_md = "TODOS"

        with c_f3:
            # Selector de Microciclos
            if f_tiempo == "Promedio de microciclo":
                lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]) if len(x.split()) > 1 and x.split()[1].isdigit() else 0)
                f_sel_micro = st.selectbox("Seleccionar microciclo:", lista_micros, key="p_sel_micro")
            
            # Selector condicional según entrenamiento, partido o sesión general
            if f_tipo == "Entrenamiento":
                lista_entrenos = sorted(df_gps[df_gps['TIPO'] == 'Entrenamiento']['Nombre_Sesion'].unique(), reverse=True)
                if lista_entrenos:
                    if f_tiempo == "Sesión":
                        f_sel_sesion = st.selectbox("Seleccionar entrenamiento:", lista_entrenos, key="p_sel_entreno")
                    else:
                        f_sel_sesion = st.selectbox("Seleccionar entrenamiento (Opcional):", ["TODOS"] + lista_entrenos, key="p_sel_entreno")
                else:
                    st.info("No hay entrenamientos registrados.")
                    
            elif f_tipo == "Partido":
                lista_partidos = sorted(df_gps[df_gps['TIPO'] == 'Partido']['Nombre_Sesion'].unique(), reverse=True)
                if lista_partidos:
                    if f_tiempo == "Sesión":
                        f_sel_sesion = st.selectbox("Seleccionar partido:", lista_partidos, key="p_sel_partido")
                    else:
                        f_sel_sesion = st.selectbox("Seleccionar partido (Opcional):", ["TODOS"] + lista_partidos, key="p_sel_partido")
                else:
                    st.info("No hay partidos registrados.")

            elif f_tiempo == "Sesión" and f_tipo == "Todas":
                lista_todas_ses = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                f_sel_sesion = st.selectbox("Seleccionar sesión:", lista_todas_ses, key="p_sel_ses_todas")

        st.markdown("---")

        # --- FILTRO INFERIOR POR NIVEL (CASILLAS HORIZONTALES) ---
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
            kpis = df_perfil[['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].mean()
            kpis_rel = df_perfil[['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']].mean()

            if f_nivel == "Por jugador" and f_jug != "TODOS":
                jugador_info = next((p for p in st.session_state.plantilla if p['JUGADOR'] == f_jug), None)
                pos_exacta = jugador_info.get('pos_1', 'Desconocida') if jugador_info else 'Desconocida'
                
                jugadores_misma_pos = [p['JUGADOR'] for p in st.session_state.plantilla if p.get('pos_1') == pos_exacta]
                
                df_contexto_posicion = df_gps[df_gps['JUGADOR'].isin(jugadores_misma_pos)].copy()
                if f_tipo != "Todas":
                    df_contexto_posicion = df_contexto_posicion[df_contexto_posicion['TIPO'] == f_tipo]
                    
                st.markdown("---")
                st.markdown(f"#### 🕸️ Perfil Radar de Rendimiento: {f_jug}")
                
                fig_radar = generar_grafico_radar_gps(df_perfil, df_contexto_posicion, f_jug, pos_exacta)
                
                if fig_radar:
                    st.plotly_chart(fig_radar, use_container_width=True)
                else:
                    st.info("No hay suficientes datos GPS para generar el radar con estos filtros.")

            st.markdown("---")
            st.markdown("#### 🚀 Promedios Absolutos (Totales)")
            kp1, kp2, kp3, kp4, kp5, kp6, kp7 = st.columns(7)
            kp1.metric("Minutos GPS", f"{kpis['MIN']:.1f}")
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

    with tab_gps_comp:
        st.markdown("#### ⚖️ Comparador (A vs B vs C)")
        
        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown("##### 🔵 Perfil A")
            a_tipo = st.selectbox("Sesión (A):", ["Todas", "Entrenamiento", "Partido"], key="c_a_tipo")
            a_md = "TODOS"
            if a_tipo == "Entrenamiento": a_md = st.selectbox("MD (A):", lista_mds, key="c_a_md")
            a_nivel = st.radio("Filtro (A):", ["Jugador", "Posición", "Equipo Completo"], key="c_a_niv")
            a_jug, a_pos = "TODOS", "DEF"
            if a_nivel == "Jugador": a_jug = st.selectbox("Jugador (A):", lista_jugs, key="c_a_jug")
            elif a_nivel == "Posición": a_pos = st.selectbox("Posición (A):", lista_pos, key="c_a_pos")
        
        with colB:
            st.markdown("##### 🔴 Perfil B")
            b_tipo = st.selectbox("Sesión (B):", ["Todas", "Entrenamiento", "Partido"], key="c_b_tipo")
            b_md = "TODOS"
            if b_tipo == "Entrenamiento": b_md = st.selectbox("MD (B):", lista_mds, key="c_b_md")
            b_nivel = st.radio("Filtro (B):", ["Jugador", "Posición", "Equipo Completo"], key="c_b_niv")
            b_jug, b_pos = "TODOS", "MED"
            if b_nivel == "Jugador": b_jug = st.selectbox("Jugador (B):", lista_jugs, key="c_b_jug")
            elif b_nivel == "Posición": b_pos = st.selectbox("Posición (B):", lista_pos, key="c_b_pos")

        with colC:
            st.markdown("##### 🟢 Perfil C (Opcional)")
            usar_C = st.checkbox("Activar Perfil C")
            if usar_C:
                c_tipo = st.selectbox("Sesión (C):", ["Todas", "Entrenamiento", "Partido"], key="c_c_tipo")
                c_md = "TODOS"
                if c_tipo == "Entrenamiento": c_md = st.selectbox("MD (C):", lista_mds, key="c_c_md")
                c_nivel = st.radio("Filtro (C):", ["Jugador", "Posición", "Equipo Completo"], key="c_c_niv")
                c_jug, c_pos = "TODOS", "ATA"
                if c_nivel == "Jugador": c_jug = st.selectbox("Jugador (C):", lista_jugs, key="c_c_jug")
                elif c_nivel == "Posición": c_pos = st.selectbox("Posición (C):", lista_pos, key="c_c_pos")
            else:
                c_tipo, c_md, c_nivel, c_jug, c_pos = "Todas", "TODOS", "Equipo Completo", "TODOS", "ATA"

        df_A = aplicar_filtros_gps(df_gps, target_tipo=a_tipo, target_md=a_md, target_nivel=a_nivel, target_jug=a_jug, target_pos=a_pos)
        df_B = aplicar_filtros_gps(df_gps, target_tipo=b_tipo, target_md=b_md, target_nivel=b_nivel, target_jug=b_jug, target_pos=b_pos)
        df_C = aplicar_filtros_gps(df_gps, target_tipo=c_tipo, target_md=c_md, target_nivel=c_nivel, target_jug=c_jug, target_pos=c_pos) if usar_C else pd.DataFrame()

        if df_A.empty or df_B.empty or (usar_C and df_C.empty):
            st.warning("⚠️ Uno de los perfiles activos no tiene datos. Revisa los filtros.")
        else:
            st.markdown("---")
            modo_comp = st.radio("¿Qué tipo de métricas quieres comparar?", ["Absolutas (Totales)", "Relativas (Por Minuto)"], horizontal=True)
            
            if modo_comp == "Absolutas (Totales)":
                metrics_to_compare = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
            else:
                metrics_to_compare = ['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min', 'Z1/min', 'Z2/min', 'Z3/min', 'Z4/min', 'Z5/min', 'Z6/min']

            mean_A = df_A[metrics_to_compare].mean()
            mean_B = df_B[metrics_to_compare].mean()
            mean_C = df_C[metrics_to_compare].mean() if usar_C else None

            comp_data = []
            for m in metrics_to_compare:
                valA = mean_A[m] if not pd.isna(mean_A[m]) else 0
                valB = mean_B[m] if not pd.isna(mean_B[m]) else 0
                valC = mean_C[m] if usar_C and not pd.isna(mean_C[m]) else 0
                
                if 'DIS/min' in m or 'DIS AI/min' in m:
                    valA, valB, valC = valA * 1000, valB * 1000, valC * 1000

                diff_str_B = f"{(((valB - valA) / valA) * 100):+.1f}%" if valA > 0 else "N/A"
                diff_str_C = f"{(((valC - valA) / valA) * 100):+.1f}%" if usar_C and valA > 0 else "N/A"
                    
                fila = {
                    "Métrica": m.replace("/min", " (m/min)" if "DIS" in m else " / min"),
                    "A": round(valA, 2),
                    "B": round(valB, 2),
                    "Dif. B vs A": diff_str_B
                }
                if usar_C:
                    fila["C"] = round(valC, 2)
                    fila["Dif. C vs A"] = diff_str_C
                    
                comp_data.append(fila)
                
            st.markdown("#### 📊 Tabla de Comparación Triple")
            columnas_estilo = ["Dif. B vs A", "Dif. C vs A"] if usar_C else ["Dif. B vs A"]
            mostrar_tabla_moderna(pd.DataFrame(comp_data).style.hide(axis="index").map(lambda x: "color: #28a745" if "+" in str(x) else ("color: #ff4b4b" if "-" in str(x) else ""), subset=columnas_estilo))
