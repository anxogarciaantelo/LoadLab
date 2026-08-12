import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections].Counter

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

datos_gps = []
for s in st.session_state.sesiones:
    if s.get("informe_generado"):
        es_partido = "Partido" in s["tipo"]
        tipo_str = "Partido" if es_partido else "Entrenamiento"
        md_str = s["descripcion"]
        
        disp_s = s.get("disponibilidad", {})
        disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
        
        for d in s["datos_informe"]:
            jug_nombre = d["JUGADOR"]
            est_jug = disp_s_clean.get(limpiar_nombre(jug_nombre), "Disponible")
            
            # FILTRO DE EXCLUSIÓN PARA GPS GLOBAL: Solo jugadores válidos y con distancia > 0
            if est_jug in ["Disponible", "Titular", "Suplente"] and float(d.get("DIS", 0)) > 0:
                min_val = float(d.get("MIN_GPS", d.get("MIN", 0)))
                if min_val == 0: min_val = 1 
                
                num_sem = obtener_numero_semana(s["fecha"])
                id_micro = mapa_micros.get(num_sem, num_sem)
                
                datos_gps.append({
                    "FECHA": s["fecha"],
                    "TIPO": tipo_str,
                    "MD": md_str,
                    "Microciclo": f"Microciclo {id_micro}",
                    "Nombre_Sesion": f"{s['fecha']} | {s.get('nombre_dinamico', s['tipo'])}",
                    "JUGADOR": d["JUGADOR"],
                    "POS": d.get("POS", ""),
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
    lista_mds = ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"]

    def aplicar_filtros_gps(df, target_tipo, target_md, target_nivel, target_jug, target_pos, target_tiempo="Histórico Completo", target_sel_tiempo="TODOS"):
        res = df.copy()
        
        if target_tiempo == "Microciclo Concreto" and target_sel_tiempo != "TODOS":
            res = res[res['Microciclo'] == target_sel_tiempo]
        elif target_tiempo == "Sesión Concreta" and target_sel_tiempo != "TODOS":
            res = res[res['Nombre_Sesion'] == target_sel_tiempo]
            
        if target_tipo != "TODOS":
            res = res[res['TIPO'] == target_tipo]
            if target_tipo == "Entrenamiento" and target_md != "TODOS":
                res = res[res['MD'] == target_md]
        if target_nivel == "Jugador":
            if target_jug != "TODOS": res = res[res['JUGADOR'] == target_jug]
        elif target_nivel == "Posición":
            res = res[res['POS'] == target_pos]
        return res

    with tab_gps_perf:
        st.markdown("#### 🔍 Filtros de Rendimiento")
        
        c_t1, c_t2 = st.columns(2)
        f_tiempo = c_t1.selectbox("Filtro Temporal:", ["Histórico Completo", "Microciclo Concreto", "Sesión Concreta"], key="p_tiempo")
        f_sel_tiempo = "TODOS"
        
        if f_tiempo == "Microciclo Concreto":
            lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]))
            f_sel_tiempo = c_t2.selectbox("Seleccionar Microciclo:", lista_micros, key="p_sel_micro")
        elif f_tiempo == "Sesión Concreta":
            lista_sesiones = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
            f_sel_tiempo = c_t2.selectbox("Seleccionar Sesión:", lista_sesiones, key="p_sel_ses")

        c1, c2, c3, c4 = st.columns(4)
        f_tipo = c1.selectbox("Sesión:", ["TODOS", "Entrenamiento", "Partido"], key="p_tipo")
        f_md = "TODOS"
        if f_tipo == "Entrenamiento": f_md = c2.selectbox("Match Day:", lista_mds, key="p_md")
        
        f_nivel = c3.radio("Analizar por:", ["Equipo Completo", "Posición", "Jugador"], key="p_niv")
        f_jug, f_pos = "TODOS", "DEF"
        if f_nivel == "Jugador": f_jug = c4.selectbox("Seleccionar Jugador:", ["TODOS"] + lista_jugs, key="p_jug")
        elif f_nivel == "Posición": f_pos = c4.selectbox("Seleccionar Posición:", lista_pos, key="p_pos")

        df_perfil = aplicar_filtros_gps(df_gps, f_tipo, f_md, f_nivel, f_jug, f_pos, f_tiempo, f_sel_tiempo)

        if df_perfil.empty:
            st.warning("No hay datos para esta combinación de filtros.")
        else:
            kpis = df_perfil[['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].mean()
            kpis_rel = df_perfil[['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']].mean()

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
            a_tipo = st.selectbox("Sesión (A):", ["TODOS", "Entrenamiento", "Partido"], key="c_a_tipo")
            a_md = "TODOS"
            if a_tipo == "Entrenamiento": a_md = st.selectbox("MD (A):", lista_mds, key="c_a_md")
            a_nivel = st.radio("Filtro (A):", ["Jugador", "Posición", "Equipo Completo"], key="c_a_niv")
            a_jug, a_pos = "TODOS", "DEF"
            if a_nivel == "Jugador": a_jug = st.selectbox("Jugador (A):", lista_jugs, key="c_a_jug")
            elif a_nivel == "Posición": a_pos = st.selectbox("Posición (A):", lista_pos, key="c_a_pos")
        
        with colB:
            st.markdown("##### 🔴 Perfil B")
            b_tipo = st.selectbox("Sesión (B):", ["TODOS", "Entrenamiento", "Partido"], key="c_b_tipo")
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
                c_tipo = st.selectbox("Sesión (C):", ["TODOS", "Entrenamiento", "Partido"], key="c_c_tipo")
                c_md = "TODOS"
                if c_tipo == "Entrenamiento": c_md = st.selectbox("MD (C):", lista_mds, key="c_c_md")
                c_nivel = st.radio("Filtro (C):", ["Jugador", "Posición", "Equipo Completo"], key="c_c_niv")
                c_jug, c_pos = "TODOS", "ATA"
                if c_nivel == "Jugador": c_jug = st.selectbox("Jugador (C):", lista_jugs, key="c_c_jug")
                elif c_nivel == "Posición": c_pos = st.selectbox("Posición (C):", lista_pos, key="c_c_pos")
            else:
                c_tipo, c_md, c_nivel, c_jug, c_pos = "TODOS", "TODOS", "Equipo Completo", "TODOS", "ATA"

        df_A = aplicar_filtros_gps(df_gps, a_tipo, a_md, a_nivel, a_jug, a_pos)
        df_B = aplicar_filtros_gps(df_gps, b_tipo, b_md, b_nivel, b_jug, b_pos)
        df_C = aplicar_filtros_gps(df_gps, c_tipo, c_md, c_nivel, c_jug, c_pos) if usar_C else pd.DataFrame()

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
