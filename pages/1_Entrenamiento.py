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

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("Por favor, inicia sesión y selecciona un equipo primero.")
    st.stop()

sesiones_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
conteo_entrenos = 0
conteo_amistosos = 0
conteo_liga = 0
conteo_copa = 0

for s in sesiones_crono:
    if s["tipo"] == "Entrenamiento":
        conteo_entrenos += 1
        s["nombre_dinamico"] = f"Sesión {conteo_entrenos}"
        s["subtitulo_dinamico"] = s.get("descripcion", "")
    elif s["tipo"] == "Partido Amistoso":
        conteo_amistosos += 1
        s["nombre_dinamico"] = f"Partido Amistoso {conteo_amistosos}"
        s["subtitulo_dinamico"] = f"vs {s.get('rival', 'Rival')}"
    elif s["tipo"] == "Partido Oficial":
        comp = s.get("competicion", "Liga")
        if comp == "Liga":
            conteo_liga += 1
            s["nombre_dinamico"] = f"Jornada {conteo_liga}"
        elif comp == "Copa":
            conteo_copa += 1
            s["nombre_dinamico"] = f"Ronda {conteo_copa}"
        s["subtitulo_dinamico"] = f"vs {s.get('rival', 'Rival')}"
 
    st.subheader("📅 Entrenamiento")
    
    tab_cal, tab_temp, tab_micro, tab_ses = st.tabs(["🗓️ Calendario", "🏆 Temporada", "🔄 Microciclos", "📋 Sesiones"])
    
    with tab_cal:
        c_dia1, c_dia2 = st.columns([1, 2])
        with c_dia1:
            # Diccionarios para traducir los meses y días del selector al castellano
            meses_trad = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
            dias_trad = {0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"}
            
            dia_clicado = st.date_input("Selecciona un día del calendario:", date.today())
            
            # Formateamos la fecha seleccionada a Día-Mes-Año en texto para los mensajes
            fecha_formateada = dia_clicado.strftime("%d-%m-%Y")
            
            sesiones_en_fecha = [s for s in st.session_state.sesiones if s["fecha"] == str(dia_clicado)]
            if sesiones_en_fecha: 
                st.success(f"¡Hay sesión programada para el {fecha_formateada}!")
            else:
                st.warning(f"No hay registros para el {fecha_formateada}.")
                with st.expander("➕ Generar Sesión"):
                    tipo_nuevo = st.selectbox("Tipo de Evento:", ["Entrenamiento", "Partido Oficial", "Partido Amistoso"])
                    
                    desc_nuevo = ""
                    comp_nuevo = ""
                    rival_nuevo = ""
                    
                    if tipo_nuevo == "Entrenamiento":
                        desc_nuevo = st.selectbox("Match Day:", ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"])
                    elif tipo_nuevo == "Partido Oficial":
                        comp_nuevo = st.selectbox("Competición:", ["Liga", "Copa"])
                        rival_nuevo = st.text_input("Rival:")
                    elif tipo_nuevo == "Partido Amistoso":
                        rival_nuevo = st.text_input("Rival:")
                        
                    if st.button("Guardar Sesión"):
                        st.session_state.sesiones.append({
                            "fecha": str(dia_clicado), 
                            "tipo": tipo_nuevo, 
                            "descripcion": desc_nuevo,
                            "competicion": comp_nuevo,
                            "rival": rival_nuevo,
                            "disponibilidad": {},
                            "informe_generado": False, 
                            "datos_informe": []
                        })
                        guardar_datos()
                        st.success("¡Evento creado en el calendario!")
                        st.rerun()
        with c_dia2:
            if st.session_state.sesiones:
                df_s = pd.DataFrame(st.session_state.sesiones).sort_values("fecha", ascending=False)
                df_s["Sesión"] = df_s.apply(lambda row: row.get("nombre_dinamico", row["tipo"]), axis=1)
                df_s["MD / Rival"] = df_s.apply(lambda row: row.get("subtitulo_dinamico", row.get("descripcion", "")), axis=1)
                df_s["Fecha"] = df_s["fecha"]
                mostrar_tabla_moderna(df_s[["Fecha", "Sesión", "MD / Rival"]].style.hide(axis="index"))

        # --- IMPORTADOR MASIVO DE HISTÓRICO ---
        st.markdown("---")
        with st.expander("📥 Importar Histórico Masivo (Excel de Temporada)"):
            st.caption("Sube tu archivo Excel con todo el histórico. El sistema creará o actualizará las sesiones automáticamente y añadirá a los jugadores nuevos si no existen.")
            archivo_historico = st.file_uploader("Sube el Excel de histórico:", type=["xlsx"])
            if st.button("🚀 Procesar Histórico Masivo") and archivo_historico is not None:
                try:
                    df_hist = pd.read_excel(archivo_historico)
                    df_hist_valid = df_hist[df_hist['JUGADOR'] != 0].copy()
                    df_hist_valid['FECHA_STR'] = pd.to_datetime(df_hist_valid['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                    df_hist_valid = df_hist_valid.dropna(subset=['FECHA_STR'])
                    
                    sesiones_creadas_count = 0
                    for fecha_str, grupo in df_hist_valid.groupby('FECHA_STR'):
                        sesion_obj = next((s for s in st.session_state.sesiones if s["fecha"] == fecha_str), None)
                        if not sesion_obj:
                            sesion_obj = {
                                "fecha": fecha_str,
                                "tipo": "Entrenamiento",
                                "descripcion": "TD",
                                "competicion": "",
                                "rival": "",
                                "disponibilidad": {},
                                "informe_generado": True,
                                "datos_informe": []
                            }
                            st.session_state.sesiones.append(sesion_obj)
                            sesiones_creadas_count += 1
                        else:
                            sesion_obj["informe_generado"] = True
                            
                        registros_sesion = []
                        for idx, row in grupo.iterrows():
                            jug_nombre = str(row['JUGADOR']).strip()
                            if pd.isna(row['JUGADOR']) or jug_nombre == "" or jug_nombre == "nan": continue
                            
                            match_p = next((p for p in st.session_state.plantilla if limpiar_nombre(p['JUGADOR']) == limpiar_nombre(jug_nombre)), None)
                            if not match_p:
                                st.session_state.plantilla.append({
                                    "JUGADOR": jug_nombre,
                                    "POS": "DEF",
                                    "edad": 20,
                                    "pos_1": "Central",
                                    "pos_2": "Ninguna",
                                    "dorsal": 99,
                                    "altura": 180,
                                    "lateralidad": "Diestro",
                                    "foto": None
                                })
                                
                            fatiga = get_col(row, ['FATIGA', 'Fatiga'])
                            sueño = get_col(row, ['SUEÑO', 'Sueño', 'SUENO'])
                            dolor = get_col(row, ['DOLOR', 'Dolor'])
                            estres = get_col(row, ['ESTRÉS', 'Estrés', 'ESTRES'])
                            humor = get_col(row, ['HUMOR', 'Humor'])
                            well_sum = fatiga + sueño + dolor + estres + humor
                            
                            min_sesion = get_col(row, ['MINUTOS SESIÓN', 'MINUTOS SESION', 'Minutos Sesión'])
                            min_gps = get_col(row, ['MINUTOS GPS', 'Time Played', 'Minutos GPS'])
                            rpe = get_col(row, ['RPE'])
                            
                            dis = get_col(row, ['DISTANCIA', 'Distance (km)'])
                            
                            # Si el jugador no llevó GPS (distancia = 0) o min gps = 0, se anulan sus métricas de GPS
                            if min_gps > 0 and dis > 0:
                                dis_ai_21 = get_col(row, ['DISTANCIA AI >21', 'HID distance (> 21.00 km/h)'])
                                dis_ai_24 = get_col(row, ['DISTANCIA AI >24', 'HID distance (> 24.00 km/h)'])
                                spr_24 = get_col(row, ['SPRINTS >24', '# of Sprints (> 24.00 km/h)'])
                                spr_27 = get_col(row, ['SPRINTS >27'])
                                v_med = get_col(row, ['V.MEDIA', 'V. MEDIA', 'Avg Speed (km/h)'])
                                v_max = get_col(row, ['V. MÁXIMA', 'Max Speed (km/h)'])
                                acc_max = get_col(row, ['ACC. MÁXIMA'])
                                acc_2 = get_col(row, ['ACC >2 m/s', '# of Accelerations (> 2.00 m/s²)'])
                                acc_3 = get_col(row, ['ACC >3 m/s', '# of Accelerations (> 3.00 m/s²)'])
                                acc_4 = get_col(row, ['ACC >4 m/s', '# of Accelerations (> 4.00 m/s²)'])
                                dcc_2 = get_col(row, ['DCC >2 m/s', '# of Decelerations (> 2.00 m/s²)'])
                                dcc_3 = get_col(row, ['DCC >3 m/s', '# of Decelerations (> 3.00 m/s²)'])
                                dcc_4 = get_col(row, ['DCC >4 m/s', '# of Decelerations (> 4.00 m/s²)'])
                                r_0_7 = get_col(row, ['DISTANCIA 0-7 KM/H', 'Distance Speed Range (0 - 7 km)'])
                                r_7_14 = get_col(row, ['DISTANCIA 7-14 KM/H', 'Distance Speed Range (7 - 14 km)'])
                                r_14_21 = get_col(row, ['DISTANCIA 14-21 KM/H', 'Distance Speed Range (14 - 21 km)'])
                                r_21_24 = get_col(row, ['DISTANCIA 21-24 KM/H', 'Distance Speed Range (21 - 24 km)'])
                                r_24_27 = get_col(row, ['DISTANCIA 24-27 KM/H', 'Distance Speed Range (24 - 27 km)'])
                                r_27_30 = get_col(row, ['DISTANCIA 27-30 KM/H', 'Distance Speed Range (27 - 30 km)'])
                                r_30 = get_col(row, ['DISTANCIA >30 KM/H', 'Distance Speed Range (30 - 45 km)'])
                            else:
                                dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_27 = v_med = v_max = acc_max = acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = r_30 = 0.0
                                min_gps = 0.0

                            rec = {
                                "JUGADOR": jug_nombre,
                                "POS": next((p['POS'] for p in st.session_state.plantilla if limpiar_nombre(p['JUGADOR']) == limpiar_nombre(jug_nombre)), "DEF"),
                                "TQR": get_col(row, ['TQR']),
                                "WELLNESS": well_sum,
                                "W_Humor": humor, "W_Sueño": sueño, "W_Fatiga": fatiga, "W_Dolor": dolor, "W_Estres": estres,
                                "RPE": rpe,
                                "MIN": min_sesion,
                                "MIN_GPS": min_gps,
                                "CARGA": min_sesion * rpe,
                                
                                # Formato Standard (Para Dashboards Globales)
                                "DIS": dis,
                                "DIS AI": dis_ai_21,
                                "Nº SPR": spr_24,
                                "ACC": acc_3,
                                "DCC": dcc_3,
                                "VMAX": v_max,
                                "Z1": r_0_7 + r_7_14,
                                "Z2": r_14_21,
                                "Z3": r_21_24,
                                "Z4": r_24_27,
                                "Z5": r_27_30,
                                "Z6": r_30,
                                
                                # Formato Extendido Exacto (Para la Tabla de Carga Manual y Mapeo Estricto)
                                "HID >21": dis_ai_21,
                                "HID >24": dis_ai_24,
                                "SPR >24": spr_24,
                                "SPR >27": spr_27,
                                "V_Med": v_med,
                                "V_Max": v_max,
                                "ACC_Max": acc_max,
                                "ACC >2": acc_2,
                                "ACC >3": acc_3,
                                "ACC >4": acc_4,
                                "DCC >2": dcc_2,
                                "DCC >3": dcc_3,
                                "DCC >4": dcc_4,
                                "R_0_7": r_0_7,
                                "R_7_14": r_7_14,
                                "R_14_21": r_14_21,
                                "R_21_24": r_21_24,
                                "R_24_27": r_24_27,
                                "R_27_30": r_27_30,
                                "R_30_45": r_30
                            }
                            registros_sesion.append(rec)
                            
                        sesion_obj["datos_informe"] = registros_sesion
                        
                    guardar_datos()
                    st.success(f"✅ ¡Histórico importado correctamente! Se procesaron {len(df_hist_valid)} registros en total.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo histórico: {e}")

    with tab_temp:
        st.markdown("### 🏆 Evolución de la Temporada")
        if not st.session_state.sesiones:
            st.info("No hay datos suficientes para generar el informe de temporada.")
        else:
            lista_micro = []
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    num_sem = obtener_numero_semana(s["fecha"])
                    _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
                    lista_micro.append({"num_semana": num_sem, "lunes_dt": lunes})
            
            if not lista_micro:
                st.warning("Debes procesar datos en las sesiones para ver la evolución de la temporada.")
            else:
                df_m = pd.DataFrame(lista_micro).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
                
                kpis_temporada = []
                for i, row in df_m.iterrows():
                    num_sem = row["num_semana"]
                    nombre_micro = f"Microciclo {i+1}"
                    ses_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem and s.get("informe_generado", False)]
                    datos_acum = []
                    for s in ses_sem:
                        disp_s = s.get("disponibilidad", {})
                        disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                        
                        for d in s["datos_informe"]:
                            jug_name = d["JUGADOR"]
                            est_jug = disp_s_clean.get(limpiar_nombre(jug_name), "Disponible")
                            
                            # EXCLUSIÓN PARA MEDIAS DE CARGA INTERNA: Ni lesionados, ni readaptación, ni no disponibles
                            if est_jug in ["Disponible", "Titular", "Suplente"]:
                                datos_acum.append({
                                    "JUGADOR": jug_name, "DIA": s["fecha"],
                                    "TQR": safe_float(d.get("TQR")), "WELLNESS": safe_float(d.get("WELLNESS")),
                                    "RPE": safe_float(d.get("RPE")), "MIN": safe_float(d.get("MIN")),
                                    "CARGA": safe_float(d.get("CARGA")), "DIS": safe_float(d.get("DIS")),
                                    "DIS AI": safe_float(d.get("HID >21", d.get("DIS AI", 0))), 
                                    "Nº SPR": safe_float(d.get("SPR >24", d.get("Nº SPR", 0))),
                                    "ACC": safe_float(d.get("ACC >3", d.get("ACC", 0))), 
                                    "DCC": safe_float(d.get("DCC >3", d.get("DCC", 0)))
                                })
                    df_sem = pd.DataFrame(datos_acum)
                    if not df_sem.empty:
                        # Reemplazar 0 por NaN en encuestas para que los no-rellenados no bajen la media
                        df_sem['TQR'] = df_sem['TQR'].replace(0, np.nan)
                        df_sem['WELLNESS'] = df_sem['WELLNESS'].replace(0, np.nan)
                        df_sem['RPE'] = df_sem['RPE'].replace(0, np.nan)
                        
                        df_jug_sum_int = df_sem.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
                        
                        # PARA GPS: SOLO LOS QUE TIENEN DISTANCIA > 0
                        df_sem_gps = df_sem[df_sem['DIS'] > 0]
                        if not df_sem_gps.empty:
                            df_jug_sum_ext = df_sem_gps.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].sum().reset_index()
                        else:
                            df_jug_sum_ext = pd.DataFrame(columns=['JUGADOR', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                            
                        df_no_ceros = df_sem.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                        df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE']].mean().reset_index().fillna(0)
                        
                        kpis_temporada.append({
                            "ID": i+1,
                            "Microciclo": nombre_micro,
                            "Wellness": df_jug_mean['WELLNESS'].mean(),
                            "TQR": df_jug_mean['TQR'].mean(),
                            "RPE": df_jug_mean['RPE'].mean(),
                            "Minutos": df_jug_sum_int['MIN'].mean() if not df_jug_sum_int.empty else 0,
                            "Carga (UA)": df_jug_sum_int['CARGA'].mean() if not df_jug_sum_int.empty else 0,
                            "DIS (km)": df_jug_sum_ext['DIS'].mean() if not df_jug_sum_ext.empty else 0,
                            "DIS AI (m)": df_jug_sum_ext['DIS AI'].mean() if not df_jug_sum_ext.empty else 0,
                            "Nº Sprints": df_jug_sum_ext['Nº SPR'].mean() if not df_jug_sum_ext.empty else 0,
                            "ACC": df_jug_sum_ext['ACC'].mean() if not df_jug_sum_ext.empty else 0,
                            "DCC": df_jug_sum_ext['DCC'].mean() if not df_jug_sum_ext.empty else 0
                        })
                
                if not kpis_temporada:
                    st.warning("No hay suficientes datos de jugadores disponibles (sin contar lesiones/readaptación/no disponibles) para generar la temporada.")
                else:
                    df_temporada = pd.DataFrame(kpis_temporada)
                    
                    st.markdown("#### 🎯 Promedios")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Wellness", f"{df_temporada['Wellness'].mean():.1f}")
                    c2.metric("TQR", f"{df_temporada['TQR'].mean():.1f}")
                    c3.metric("RPE", f"{df_temporada['RPE'].mean():.1f}")
                    c4.metric("Minutos", f"{df_temporada['Minutos'].mean():.1f}")
                    c5.metric("Carga media (UA)", f"{df_temporada['Carga (UA)'].mean():.0f}")
                    
                    c6, c7, c8, c9, c10 = st.columns(5)
                    c6.metric("Distancia (km)", f"{df_temporada['DIS (km)'].mean():.2f}")
                    c7.metric("HSR (>21 km/h)", f"{df_temporada['DIS AI (m)'].mean():.2f}")
                    c8.metric("N.º Sprints (>24 km/h)", f"{df_temporada['Nº Sprints'].mean():.1f}")
                    c9.metric("ACC (>3 m/s²)", f"{df_temporada['ACC'].mean():.1f}")
                    c10.metric("DCC (>3 m/s²)", f"{df_temporada['DCC'].mean():.1f}")
                    
                    st.markdown("---")
                    st.markdown("#### 📋 Resumen por Microciclo")
                    cols_order = ["Microciclo", "Wellness", "TQR", "RPE", "Minutos", "Carga (UA)", "DIS (km)", "DIS AI (m)", "Nº Sprints", "ACC", "DCC"]
                    mostrar_tabla_moderna(df_temporada[cols_order].sort_values("Microciclo", ascending=False).style.hide(axis="index").format(precision=1))

                    st.markdown("---")
                    st.markdown("#### 🧠 Bienestar")
                    cg_b1, cg_b2 = st.columns(2)
                    with cg_b1:
                        fig_tqr = px.bar(
                            df_temporada, x='Microciclo', y='TQR', 
                            color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10],
                            title="Evolución TQR"
                        )
                        fig_tqr.update_yaxes(range=[1, 10])
                        st.plotly_chart(fig_tqr, use_container_width=True, key="temp_tqr_bar")
                    with cg_b2:
                        # Extraer los componentes de wellness directamente del DataFrame de temporada o recalculando con los datos filtrados válidos del microciclo
                        datos_w_temp = []
                        for i, row in df_temporada.iterrows():
                            m_id = row["Microciclo"]
                            num_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == row.get("num_semana", obtener_numero_semana(st.session_state.sesiones[0]["fecha"]))] # fallback seguro
                            # Buscamos las sesiones de esta semana directamente por el número de semana guardado en el bucle principal de temporada
                            num_sem_val = None
                            # Recuperamos el num_semana correcto de df_m original
                            for m_item in lista_micro:
                                # Relacionamos por índice o nombre
                                pass
                            
                            # Forma más directa y robusta usando las fechas del microciclo acumuladas:
                            ses_sem = [s for s in st.session_state.sesiones if f"Microciclo {i+1}" == m_id and s.get("informe_generado", False)]
                            # Si no coincide exactamente por el texto, filtramos por el número de semana de df_m correspondiente a este índice i:
                            num_sem_real = df_m.iloc[i]["num_semana"]
                            ses_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem_real and s.get("informe_generado", False)]
                            
                            f, s_lista, d_lista, e, h = [], [], [], [], []
                            for ses in ses_sem:
                                disp_s = ses.get("disponibilidad", {})
                                disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                                for d_jug in ses["datos_informe"]:
                                    jug_name = d_jug["JUGADOR"]
                                    est_jug = disp_s_clean.get(limpiar_nombre(jug_name), "Disponible")
                                    # Mismo filtro estricto de exclusión que en las tablas y métricas
                                    if est_jug in ["Disponible", "Titular", "Suplente"] and safe_float(d_jug.get("WELLNESS")) > 0:
                                        f.append(safe_float(d_jug.get("W_Fatiga")))
                                        s_lista.append(safe_float(d_jug.get("W_Sueño")))
                                        d_lista.append(safe_float(d_jug.get("W_Dolor")))
                                        e.append(safe_float(d_jug.get("W_Estres")))
                                        h.append(safe_float(d_jug.get("W_Humor")))
                            
                            datos_w_temp.append({
                                "Microciclo": m_id, 
                                "Fatiga": np.mean(f) if f else 0, 
                                "Sueño": np.mean(s_lista) if s_lista else 0, 
                                "Dolor": np.mean(d_lista) if d_lista else 0, 
                                "Estrés": np.mean(e) if e else 0, 
                                "Humor": np.mean(h) if h else 0
                            })
                        
                        df_well_temp = pd.DataFrame(datos_w_temp)
                        
                        fig_well = px.bar(
                            df_well_temp, x='Microciclo', y=['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor'],
                            title="Evolución Wellness por Componentes", color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={'value': 'Puntos', 'variable': 'Factor', 'Microciclo': ''}
                        )
                        fig_well.update_layout(barmode='stack', yaxis_range=[5, 35])
                        fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                        fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                        st.plotly_chart(fig_well, use_container_width=True, key="temp_well_bar")

                    st.markdown("---")
                    st.markdown("#### 🔥 Carga Interna")
                    cg_i1, cg_i2, cg_i3 = st.columns(3)
                    with cg_i1:
                        fig_min = px.bar(df_temporada, x='Microciclo', y='Minutos', title="Evolución Minutos de Sesión", color_discrete_sequence=["#00b4d8"])
                        st.plotly_chart(fig_min, use_container_width=True, key="temp_min_bar")
                    with cg_i2:
                        fig_rpe = px.bar(
                            df_temporada, x='Microciclo', y='RPE', 
                            color='RPE', color_continuous_scale="Reds", range_color=[0, 10],
                            title="Evolución RPE"
                        )
                        fig_rpe.update_yaxes(range=[1, 10])
                        st.plotly_chart(fig_rpe, use_container_width=True, key="temp_rpe_bar")
                    with cg_i3:
                        min_c_temp = df_temporada['Carga (UA)'].min() * 0.9 if not df_temporada.empty else 0.0
                        max_c_temp = df_temporada['Carga (UA)'].max() * 1.1 if not df_temporada.empty else 1000.0

                        fig_carga = px.bar(
                            df_temporada, x='Microciclo', y='Carga (UA)', 
                            color='Carga (UA)', color_continuous_scale="Reds", 
                            range_color=[min_c_temp, max_c_temp],
                            title="Evolución Carga (Aguda)"
                        )
                        fig_carga.update_yaxes(range=[min_c_temp, max_c_temp])
                        st.plotly_chart(fig_carga, use_container_width=True, key="temp_carga_bar")

    with tab_micro:
        if not st.session_state.sesiones:
            st.info("Genera sesiones en el calendario para calcular los microciclos automáticamente.")
        else:
            lista_micro = []
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    num_sem = obtener_numero_semana(s["fecha"])
                    _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
                    lista_micro.append({"num_semana": num_sem, "ini": lunes.strftime("%d/%m"), "fin": domingo.strftime("%d/%m"), "lunes_dt": lunes, "domingo_dt": domingo})
            
            if not lista_micro:
                st.warning("Debes cargar y procesar datos en al menos una sesión para poder generar informes semanales.")
            else:
                df_m = pd.DataFrame(lista_micro).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
                
                for idx_real, row in df_m.sort_values(by="lunes_dt", ascending=False).iterrows():
                    num_sem = row["num_semana"]
                    nombre_etiqueta = f"📦 Microciclo {idx_real + 1} | Semana del {row['ini']} al {row['fin']}"
                    
                    with st.expander(nombre_etiqueta, expanded=False):
                        sesiones_semana = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem and s.get("informe_generado", False)]
                        rol_semanal = {j["JUGADOR"]: "Sin Partido" for j in st.session_state.plantilla}
                        hubo_partido = False
                        for s in sesiones_semana:
                            if "Partido" in s['tipo']:
                                hubo_partido = True
                                disp = s.get("disponibilidad", {})
                                disp_clean = {limpiar_nombre(k): v for k, v in disp.items()}
                                for j in st.session_state.plantilla:
                                    if disp_clean.get(limpiar_nombre(j["JUGADOR"]), "") == "Titular":
                                        rol_semanal[j["JUGADOR"]] = "Titular"
                        if hubo_partido:
                            for k in rol_semanal.keys():
                                if rol_semanal[k] == "Sin Partido": rol_semanal[k] = "Suplente"

                        datos_7_dias = []
                        for offset in range(7):
                            dia_actual = row["lunes_dt"] + timedelta(days=offset)
                            fecha_str = dia_actual.strftime("%Y-%m-%d")
                            dia_semana_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][offset]
                            sesion_dia = next((s for s in sesiones_semana if s["fecha"] == fecha_str), None)
                            
                            for j in st.session_state.plantilla:
                                jugador = j["JUGADOR"]
                                if sesion_dia:
                                    disp_s = sesion_dia.get("disponibilidad", {})
                                    disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                                    est_jug = disp_s_clean.get(limpiar_nombre(jugador), "Disponible")
                                    d_jug = next((d for d in sesion_dia["datos_informe"] if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jugador)), None)
                                    
                                    if d_jug:
                                        datos_7_dias.append({
                                            "JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador],
                                            "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": est_jug,
                                            "TQR": safe_float(d_jug.get("TQR")), "WELLNESS": safe_float(d_jug.get("WELLNESS")),
                                            "RPE": safe_float(d_jug.get("RPE")), "MIN": safe_float(d_jug.get("MIN")),
                                            "CARGA": safe_float(d_jug.get("CARGA")),
                                            "DIS": safe_float(d_jug.get("DIS")),
                                            "DIS AI": safe_float(d_jug.get("HID >21", d_jug.get("DIS AI", 0))),
                                            "Nº SPR": safe_float(d_jug.get("SPR >24", d_jug.get("Nº SPR", 0))),
                                            "ACC": safe_float(d_jug.get("ACC >3", d_jug.get("ACC", 0))),
                                            "DCC": safe_float(d_jug.get("DCC >3", d_jug.get("DCC", 0))),
                                            "VMAX": safe_float(d_jug.get("V_Max", d_jug.get("VMAX", 0))), 
                                            "ENTRENO": 1 # Anclaje clave para promediar solo a los que entrenaron
                                        })
                                    else:
                                        # Si no está en datos_informe, no promediará
                                        datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": est_jug, "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})
                                else:
                                    datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": "Sin Sesión", "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})

                        df_semana = pd.DataFrame(datos_7_dias)

                        col_f1, col_f2 = st.columns(2)
                        with col_f1: pos_filtro = st.radio("Filtrar Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"fw_p_{num_sem}")
                        with col_f2: rol_filtro = st.radio("Filtrar Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"fw_r_{num_sem}")
                        
                        df_filtrado = df_semana.copy()
                        if pos_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["POS"] == pos_filtro]
                        if rol_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["ROL"] == rol_filtro]

                        if df_filtrado.empty:
                            st.warning("No hay jugadores que coincidan con estos filtros en esta semana.")
                        else:
                            # FILTRO EXCLUSIÓN DIARIO PARA MEDIAS DEL EQUIPO (Sincronizado con el Informe)
                            df_disp = df_filtrado[(df_filtrado['ESTADO'].isin(["Disponible", "Titular", "Suplente"])) & (df_filtrado['ENTRENO'] == 1)].copy()
                            
                            df_disp['TQR'] = df_disp['TQR'].replace(0, np.nan)
                            df_disp['WELLNESS'] = df_disp['WELLNESS'].replace(0, np.nan)
                            df_disp['RPE'] = df_disp['RPE'].replace(0, np.nan)
                            
                            if not df_disp.empty:
                                df_diario_int = df_disp.groupby('DIA', sort=False)[['WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA']].mean().reset_index()
                                df_disp_gps = df_disp[df_disp['DIS'] > 0]
                                if not df_disp_gps.empty:
                                    df_diario_ext = df_disp_gps.groupby('DIA', sort=False)[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].mean().reset_index()
                                else:
                                    df_diario_ext = pd.DataFrame(columns=['DIA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                                
                                df_diario = pd.merge(df_diario_int, df_diario_ext, on='DIA', how='left').fillna(0)
                            else:
                                df_diario = pd.DataFrame(columns=['DIA', 'WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])

                            orden_dias = {"Lunes":1, "Martes":2, "Miércoles":3, "Jueves":4, "Viernes":5, "Sábado":6, "Domingo":7}
                            df_diario["Orden"] = df_diario["DIA"].map(orden_dias)
                            df_diario = df_diario.sort_values("Orden").drop(columns=["Orden"])

                            st.markdown("#### 🎯 Resumen del Microciclo")
                            c1, c2, c3, c4, c5 = st.columns(5)
                            c1.metric("Wellness medio", f"{df_diario['WELLNESS'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c2.metric("TQR medio", f"{df_diario['TQR'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c3.metric("RPE medio", f"{df_diario['RPE'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c4.metric("Minutos totales", f"{df_diario['MIN'].sum():.1f}" if not df_diario.empty else "0")
                            c5.metric("Carga total (UA)", f"{df_diario['CARGA'].sum():.0f}" if not df_diario.empty else "0")
                            
                            c6, c7, c8, c9, c10 = st.columns(5)
                            c6.metric("Distancia total", f"{df_diario['DIS'].sum():.2f}" if not df_diario.empty else "0")
                            c7.metric("HSR total (>21 km/h)", f"{df_diario['DIS AI'].sum():.2f}" if not df_diario.empty else "0")
                            c8.metric("Sprints totales (>24 km/h)", f"{df_diario['Nº SPR'].sum():.1f}" if not df_diario.empty else "0")
                            c9.metric("ACC totales (>3 m/s²)", f"{df_diario['ACC'].sum():.1f}" if not df_diario.empty else "0")
                            c10.metric("DCC totales (>3 m/s²)", f"{df_diario['DCC'].sum():.1f}" if not df_diario.empty else "0")

                            st.markdown("---")
                            st.markdown("#### 📋 Resumen por Día")
                            if not df_diario.empty:
                                mostrar_tabla_moderna(df_diario.style.hide(axis="index").format(precision=2))

                            st.markdown("---")
                            st.markdown("#### 🧠 Bienestar")
                            cg_b1, cg_b2 = st.columns(2)
                            with cg_b1:
                                df_tqr_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                fig_tqr = px.bar(
                                    df_tqr_plot, x='DIA', y='TQR', 
                                    color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10],
                                    title="Calidad de Recuperación (TQR)"
                                )
                                fig_tqr.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_tqr.update_yaxes(range=[1, 10])
                                st.plotly_chart(fig_tqr, use_container_width=True, key=f"micro_tqr_{num_sem}_{idx_real}")
                            with cg_b2:
                                datos_w = []
                                for offset in range(7):
                                    dia_n = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][offset]
                                    f_str = (row["lunes_dt"] + timedelta(days=offset)).strftime("%Y-%m-%d")
                                    ses = next((s for s in sesiones_semana if s["fecha"] == f_str), None)
                                    
                                    f_val = s_val = d_val = e_val = h_val = 0.0
                                    if ses and ses.get("datos_informe"):
                                        j_validos = df_disp[df_disp['DIA'] == dia_n]['JUGADOR'].tolist()
                                        d_validos = [d for d in ses["datos_informe"] if d["JUGADOR"] in j_validos and safe_float(d.get("WELLNESS")) > 0]
                                        
                                        if d_validos:
                                            f_val = np.mean([safe_float(d.get("W_Fatiga")) for d in d_validos])
                                            s_val = np.mean([safe_float(d.get("W_Sueño")) for d in d_validos])
                                            d_val = np.mean([safe_float(d.get("W_Dolor")) for d in d_validos])
                                            e_val = np.mean([safe_float(d.get("W_Estres")) for d in d_validos])
                                            h_val = np.mean([safe_float(d.get("W_Humor")) for d in d_validos])
                                            
                                    datos_w.append({"DIA": dia_n, "Fatiga": f_val, "Sueño": s_val, "Dolor": d_val, "Estrés": e_val, "Humor": h_val})
                                
                                fig_well = px.bar(
                                    pd.DataFrame(datos_w), x='DIA', y=['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor'], 
                                    title="Evolución Wellness Diario", color_discrete_sequence=px.colors.qualitative.Set2,
                                    labels={'value': 'Puntos', 'variable': 'Factor', 'DIA': ''}
                                )
                                fig_well.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_well.update_yaxes(range=[5, 35])
                                fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                                fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                                fig_well.update_traces(hovertemplate="%{variable}: %{y:.1f} pts")
                                fig_well.update_layout(barmode='stack', legend_title_text='Factores', hovermode="x unified")
                                st.plotly_chart(fig_well, use_container_width=True, key=f"micro_well_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 🔥 Carga Interna")
                            cg_i1, cg_i2, cg_i3 = st.columns(3)
                            with cg_i1:
                                fig_min = px.bar(df_diario, x='DIA', y='MIN', title="Evolución Minutos")
                                st.plotly_chart(fig_min, use_container_width=True, key=f"micro_min_{num_sem}")
                            with cg_i2:
                                df_rpe_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                fig_rpe = px.bar(df_rpe_plot, x='DIA', y='RPE', title="Evolución RPE", color='RPE', color_continuous_scale="Reds", range_color=[0, 10])
                                fig_rpe.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_rpe.update_yaxes(range=[1, 10])
                                st.plotly_chart(fig_rpe, use_container_width=True, key=f"micro_rpe_{num_sem}_{idx_real}")
                            with cg_i3:
                                df_carga_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                
                                min_c_temp = 0.0
                                max_c_temp = 1000.0
                                todas_cargas_temp = []
                                for s_t in st.session_state.sesiones:
                                    if s_t.get("informe_generado", False) and s_t.get("datos_informe"):
                                        for d in s_t["datos_informe"]:
                                            val_c = safe_float(d.get("CARGA"))
                                            if val_c > 0:
                                                todas_cargas_temp.append(val_c)
                                                
                                if todas_cargas_temp:
                                    min_c_temp = min(todas_cargas_temp)
                                    max_c_temp = max(todas_cargas_temp) * 1.1

                                fig_carga = px.bar(
                                    df_carga_plot, x='DIA', y='CARGA', 
                                    color='CARGA', color_continuous_scale="Reds", 
                                    range_color=[min_c_temp, max_c_temp],
                                    title="Evolución Carga"
                                )
                                fig_carga.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_carga.update_yaxes(range=[0, max_c_temp])
                                
                                media_equipo_semana = df_diario['CARGA'].mean()
                                if media_equipo_semana > 0:
                                    fig_carga.add_hline(
                                        y=media_equipo_semana, 
                                        line_dash="dot", 
                                        line_color="gray", 
                                        annotation_text=f"Media Semana: {media_equipo_semana:.0f} UA", 
                                        annotation_position="top right"
                                    )
                                    
                                st.plotly_chart(fig_carga, use_container_width=True, key=f"micro_carga_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 🏃‍♂️ Carga Externa (Solo datos GPS > 0m)")
                            
                            df_diario_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index().fillna(0)
                            
                            cg_e1, cg_e2, cg_e3 = st.columns(3)
                            with cg_e1:
                                fig_accdcc = go.Figure()
                                fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['ACC'], mode='lines+markers', name='ACC (>3)', line=dict(color='blue')))
                                fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['DCC'], mode='lines+markers', name='DCC (>3)', line=dict(color='red')))
                                fig_accdcc.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_accdcc.update_layout(title="Evolución ACC vs DCC")
                                st.plotly_chart(fig_accdcc, use_container_width=True, key=f"micro_accdcc_{num_sem}_{idx_real}")
                            with cg_e2:
                                fig_dis = px.bar(df_diario_plot, x='DIA', y='DIS', title="Evolución DIS (km)", color_discrete_sequence=['#00b4d8'])
                                fig_dis.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                st.plotly_chart(fig_dis, use_container_width=True, key=f"micro_dis_{num_sem}_{idx_real}")
                            with cg_e3:
                                fig_disai = px.bar(df_diario_plot, x='DIA', y='DIS AI', title="Evolución HSR (>21 km/h)", color_discrete_sequence=['#f50057'])
                                fig_disai.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                st.plotly_chart(fig_disai, use_container_width=True, key=f"micro_disai_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 👤 Resumen Semanal por Jugador")
                            # El resumen de jugador suma todas sus sesiones, aunque un día estuviera lesionado, sus datos de ese día serán 0.
                            df_jug_sum_int = df_filtrado.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
                            df_filtrado_gps = df_filtrado[df_filtrado['DIS'] > 0]
                            df_jug_sum_ext = df_filtrado_gps.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].sum().reset_index() if not df_filtrado_gps.empty else pd.DataFrame(columns=['JUGADOR', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                            
                            df_jug_sum = pd.merge(df_jug_sum_int, df_jug_sum_ext, on='JUGADOR', how='left').fillna(0)
                            
                            df_no_ceros = df_filtrado.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                            df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE']].mean().reset_index().fillna(0)
                            df_indiv = df_jug_sum.merge(df_jug_mean, on='JUGADOR')
                            
                            df_info_extra = df_filtrado[['JUGADOR', 'POS', 'ROL']].drop_duplicates()
                            df_indiv = df_indiv.merge(df_info_extra, on='JUGADOR')
                            cols_ordenadas = ['JUGADOR', 'POS', 'ROL', 'MIN', 'TQR', 'WELLNESS', 'RPE', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
                            df_indiv = df_indiv[cols_ordenadas]
                            mostrar_tabla_moderna(df_indiv.style.hide(axis="index").format(precision=2)) # <--- CORREGIDO A df_indiv
                            
                            # --- PEGAR A CONTINUACIÓN ---
                            kpis_micro = {
                                "Wellness": df_diario['WELLNESS'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "TQR": df_diario['TQR'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "RPE": df_diario['RPE'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "Minutos": df_diario['MIN'].sum() if not df_diario.empty else 0,
                                "Carga": df_diario['CARGA'].sum() if not df_diario.empty else 0,
                                "DIS": df_diario['DIS'].sum() if not df_diario.empty else 0,
                                "HSR": df_diario['DIS AI'].sum() if not df_diario.empty else 0,
                                "SPR": df_diario['Nº SPR'].sum() if not df_diario.empty else 0,
                                "ACC": df_diario['ACC'].sum() if not df_diario.empty else 0,
                                "DCC": df_diario['DCC'].sum() if not df_diario.empty else 0
                            }

                            diccionario_figuras_micro = {
                                "TQR": fig_tqr,
                                "Wellness": fig_well,
                                "Minutos": fig_min,
                                "RPE": fig_rpe,
                                "Carga": fig_carga,
                                "ACC_DCC": fig_accdcc,
                                "DIS": fig_dis,
                                "DIS_AI": fig_disai
                            }

                        st.markdown("---")
                        pdf_key = f"pdf_listo_{num_sem}_{idx_real}"

                        if pdf_key not in st.session_state:
                            if st.button("⚙️ Generar PDF del Microciclo", key=f"btn_prepara_pdf_{num_sem}_{idx_real}"):
                                with st.spinner("Procesando gráficos y PDF (esto puede tardar unos segundos)..."):
                                    st.session_state[pdf_key] = generar_pdf_microciclo(nombre_etiqueta, df_diario, df_indiv, kpis_micro, diccionario_figuras_micro)
                                st.rerun()
                        else:
                            col_pdf1, col_pdf2 = st.columns(2)
                            with col_pdf1:
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=st.session_state[pdf_key],
                                    file_name=f"Microciclo_Semana_{num_sem}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_descarga_pdf_{num_sem}_{idx_real}"
                                )
                            with col_pdf2:
                                if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_{num_sem}_{idx_real}"):
                                    del st.session_state[pdf_key]
                                    st.rerun()

    with tab_ses:
        if not st.session_state.sesiones:
            st.info("Aún no has generado ninguna sesión.")
        
        sesiones_ordenadas = sorted(st.session_state.sesiones, key=lambda x: x["fecha"], reverse=True)
            
        for idx_visual, sesion in enumerate(sesiones_ordenadas):
            idx_real = st.session_state.sesiones.index(sesion)
            es_partido = "Partido" in sesion['tipo']
            nombre_ev = sesion.get("nombre_dinamico", sesion["tipo"])
            detalle_ev = sesion.get("subtitulo_dinamico", sesion.get("descripcion", ""))
            
            with st.container():
                col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
                fecha_formateada = datetime.strptime(sesion['fecha'], "%Y-%m-%d").strftime("%d-%m-%Y")
                col_s1.write(f"📅 **{fecha_formateada}**")
                col_s2.write(f"⚽ **{nombre_ev}**\n\n<small>{detalle_ev}</small>", unsafe_allow_html=True)
                
                if col_s3.button("🏥 Disponibilidad", key=f"btn_disp_{idx_real}"):
                    st.session_state[f"mostrar_disp_{idx_real}"] = not st.session_state.get(f"mostrar_disp_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False
                
                if col_s4.button("📊 Informe", key=f"btn_inf_{idx_real}"):
                    st.session_state[f"mostrar_informe_{idx_real}"] = not st.session_state.get(f"mostrar_informe_{idx_real}", False)
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False
                    
                if col_s5.button("📂 Cargar Datos", key=f"btn_datos_{idx_real}"):
                    st.session_state[f"mostrar_datos_{idx_real}"] = not st.session_state.get(f"mostrar_datos_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False

                if col_s6.button("🚑 Lesión", key=f"btn_lesion_{idx_real}"):
                    st.session_state[f"mostrar_lesion_{idx_real}"] = not st.session_state.get(f"mostrar_lesion_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
            
            if st.session_state.get(f"mostrar_disp_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 🏥 CONTROL DE DISPONIBILIDAD | {sesion['fecha']}")
                if es_partido:
                    opciones_disp = ["Titular", "Suplente", "No convocado", "Lesionado", "Enfermo", "Selección", "No disponible"]
                    default_disp = "Titular"
                else:
                    opciones_disp = ["Disponible", "Lesionado", "Readaptación", "Enfermo", "Falta", "Selección", "No disponible"]
                    default_disp = "Disponible"
                
                disp_dict = sesion.get("disponibilidad", {})
                disp_dict_clean = {limpiar_nombre(k): v for k, v in disp_dict.items()}
                
                conteos = Counter([disp_dict_clean.get(limpiar_nombre(j["JUGADOR"]), default_disp) for j in st.session_state.plantilla])
                cols_metricas = st.columns(len(opciones_disp))
                for i, opc in enumerate(opciones_disp): cols_metricas[i].metric(opc, conteos.get(opc, 0))
                
                with st.form(key=f"form_disp_{idx_real}"):
                    for i in range(0, len(st.session_state.plantilla), 2):
                        col_d1, col_d2 = st.columns(2)
                        jugador1 = st.session_state.plantilla[i]["JUGADOR"]
                        estado1 = disp_dict_clean.get(limpiar_nombre(jugador1), default_disp)
                        if estado1 not in opciones_disp: estado1 = opciones_disp[0]
                        nuevo1 = col_d1.selectbox(f"👤 {jugador1}", opciones_disp, index=opciones_disp.index(estado1), key=f"sel1_{idx_real}_{jugador1}")
                        if "disponibilidad" not in st.session_state.sesiones[idx_real]: st.session_state.sesiones[idx_real]["disponibilidad"] = {}
                        st.session_state.sesiones[idx_real]["disponibilidad"][jugador1] = nuevo1
                        
                        if i + 1 < len(st.session_state.plantilla):
                            jugador2 = st.session_state.plantilla[i+1]["JUGADOR"]
                            estado2 = disp_dict_clean.get(limpiar_nombre(jugador2), default_disp)
                            if estado2 not in opciones_disp: estado2 = opciones_disp[0]
                            nuevo2 = col_d2.selectbox(f"👤 {jugador2}", opciones_disp, index=opciones_disp.index(estado2), key=f"sel2_{idx_real}_{jugador2}")
                            st.session_state.sesiones[idx_real]["disponibilidad"][jugador2] = nuevo2
                    if st.form_submit_button("💾 Guardar Cambios"):
                        guardar_datos()
                        st.success("Disponibilidad guardada.")
                        st.rerun()
                st.markdown("---")

            if st.session_state.get(f"mostrar_informe_{idx_real}", False):
                st.markdown("---")
                if sesion.get("informe_generado", False) and sesion.get("datos_informe"):
                    df_informe = pd.DataFrame(sesion["datos_informe"])
                    
                    # --- 1. FORZAR CONVERSIÓN NUMÉRICA ESTRICTA ---
                    cols_metricas = [
                        'TQR', 'WELLNESS', 'W_Humor', 'W_Sueño', 'W_Fatiga', 'W_Dolor', 'W_Estres', 
                        'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX',
                        'HID >21', 'SPR >24', 'ACC >3', 'DCC >3', 'V_Max'
                    ]
                    for c in cols_metricas:
                        if c in df_informe.columns:
                            df_informe[c] = pd.to_numeric(df_informe[c], errors='coerce').fillna(0.0)
                    # ---------------------------------------------
                    
                    # MAPEO ESTRICTO PARA EL INFORME: Que use los nombres de las columnas detalladas si existen
                    if 'HID >21' in df_informe.columns: df_informe['DIS AI'] = df_informe['HID >21']
                    if 'SPR >24' in df_informe.columns: df_informe['Nº SPR'] = df_informe['SPR >24']
                    if 'ACC >3' in df_informe.columns:  df_informe['ACC'] = df_informe['ACC >3']
                    if 'DCC >3' in df_informe.columns:  df_informe['DCC'] = df_informe['DCC >3']
                    if 'V_Max' in df_informe.columns:   df_informe['VMAX'] = df_informe['V_Max']
                    
                    disp_dict = sesion.get("disponibilidad", {})
                    disp_dict_clean = {limpiar_nombre(k): v for k, v in disp_dict.items()}
                    default_disp = "Titular" if es_partido else "Disponible"
                    
                    df_informe['ESTADO'] = df_informe['JUGADOR'].map(lambda j: disp_dict_clean.get(limpiar_nombre(j), default_disp))

                    dic_ewma = calcular_ewma_historico(st.session_state.sesiones, sesion["fecha"])
                    df_informe['EWMA AGUDA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA AGUDA', 0))
                    df_informe['EWMA CRÓNICA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA CRÓNICA', 0))
                    df_informe['RATIO A/C'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C', 0))

                    col_filt1, col_filt2 = st.columns(2)
                    with col_filt1:
                        filtro_pos = st.radio("Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"rp_{idx_real}")
                        if filtro_pos != "TODOS": df_informe = df_informe[df_informe["POS"] == filtro_pos]
                    if es_partido:
                        with col_filt2:
                            filtro_rol = st.radio("Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"rr_{idx_real}")
                            if filtro_rol != "TODOS": df_informe = df_informe[df_informe["ESTADO"] == filtro_rol]

                    # FILTRO ESTRICTO DE MEDIAS PARA EL EQUIPO (Sin Porteros)
                    estados_validos_medias = ["Disponible", "Titular", "Suplente"]
                    df_para_medias = df_informe[(df_informe['ESTADO'].isin(estados_validos_medias)) & (df_informe['POS'] != "POR")].copy()
                    
                    df_para_medias['TQR'] = df_para_medias['TQR'].replace(0, np.nan)
                    df_para_medias['WELLNESS'] = df_para_medias['WELLNESS'].replace(0, np.nan)
                    df_para_medias['RPE'] = df_para_medias['RPE'].replace(0, np.nan)
                    
                    # FILTRO ESTRICTO DE MEDIAS GPS (Solo si tienen distancia > 0)
                    df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0].copy()
                    
                    # TABLAS Y GRÁFICOS MOSTRARÁN A TODOS LOS JUGADORES
                    df_graficos = df_informe[df_informe['JUGADOR'] != ""].copy()
                    fig_well = fig_tqr = fig2 = fig3 = fig5 = fig4 = None

                    if not df_informe.empty:
                        # --- 2. CÁLCULO SEGURO DE MEDIAS GLOBALES ---
                        tqr_m = df_para_medias['TQR'].mean()
                        tqr_m = tqr_m if pd.notna(tqr_m) else 0.0
                        
                        well_m = df_para_medias['WELLNESS'].mean()
                        well_m = well_m if pd.notna(well_m) else 0.0
                        
                        rpe_m = df_para_medias['RPE'].mean()
                        rpe_m = rpe_m if pd.notna(rpe_m) else 0.0
                        
                        carga_m = df_para_medias['CARGA'].mean()
                        carga_m = carga_m if pd.notna(carga_m) else 0.0
                        
                        min_m = df_para_medias['MIN'].mean()
                        min_m = min_m if pd.notna(min_m) else 0.0

                        # --- KPIs GLOBALES SUPERIORES DE LA SESIÓN ---
                        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                        kpi1.metric("TQR Medio (Recuperación)", f"{tqr_m:.1f} / 10")
                        kpi2.metric("Wellness Medio (Fatiga)", f"{well_m:.1f} pts")
                        kpi3.metric("RPE Medio (Esfuerzo)", f"{rpe_m:.1f} / 10")
                        kpi4.metric("Carga Media Sesión", f"{carga_m:.0f} UA")

                        st.markdown("---")

                        # --- SECCIÓN 1: BIENESTAR Y RECUPERACIÓN ---
                        st.markdown("#### 🧠 1. Bienestar y Recuperación")
                        cg1, cg2 = st.columns(2)
                        
                        with cg1:
                            if df_graficos['WELLNESS'].sum() > 0:
                                df_well = df_graficos[df_graficos['WELLNESS'] > 0].sort_values('WELLNESS', ascending=False).copy()
                                nombres_limpios = {
                                    'W_Sueño': 'Sueño', 
                                    'W_Fatiga': 'Fatiga', 
                                    'W_Dolor': 'Dolor', 
                                    'W_Estres': 'Estrés', 
                                    'W_Humor': 'Humor'
                                }
                                df_well = df_well.rename(columns=nombres_limpios)
                                cols_wellness = list(nombres_limpios.values())
                                
                                fig_well = px.bar(
                                    df_well,
                                    x='JUGADOR',
                                    y=cols_wellness,
                                    title="<b>Desglose de Wellness por Componentes</b>",
                                    labels={'value': 'Puntos', 'variable': '', 'JUGADOR': ''},
                                    color_discrete_sequence=px.colors.qualitative.Set2
                                )

                                fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                                fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                                
                                # MODIFICACIÓN: Fijar el eje Y de 5 a 35 obligatoriamente
                                fig_well.update_yaxes(range=[5, 35])
                                
                                fig_well.update_traces(hovertemplate="%{y}")
                                fig_well.update_layout(
                                    barmode='stack',
                                    xaxis_tickangle=-45,
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    margin=dict(t=40, b=120, l=40, r=40),
                                    legend_title_text='Factores',
                                    hovermode="x unified"
                                )
                                st.plotly_chart(fig_well, use_container_width=True, key=f"ses_well_detalle_grafico_{idx_real}")
                        
                        with cg2:
                            if df_graficos['TQR'].sum() > 0:
                                df_tqr = df_graficos[df_graficos['TQR'] > 0].sort_values('TQR')
                                fig_tqr = px.bar(
                                    df_tqr, x='JUGADOR', y='TQR', 
                                    color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], 
                                    title="Calidad de Recuperación (TQR)"
                                )
                                # AÑADIDO: Fijamos el eje Y de 1 a 10 estrictamente
                                fig_tqr.update_yaxes(range=[1, 10])
                                st.plotly_chart(fig_tqr, use_container_width=True, key=f"ses_tqr_grafico_{idx_real}")
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN 2: CARGA INTERNA ---
                        st.markdown("#### 🔥 2. Carga Interna")
                        ci1, ci2, ci3 = st.columns(3)
                        ci1.metric("Minutos Sesión (Media)", f"{min_m:.1f}")
                        ci2.metric("RPE Medio", f"{rpe_m:.1f}")
                        ci3.metric("Carga Media (UA)", f"{carga_m:.0f}")
                        
                        cols_ver_ci = ['JUGADOR', 'POS', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']
                        
                        estilo_ci = (df_informe[cols_ver_ci].style
                                     .hide(axis="index")
                                     .format(precision=2)
                                     .background_gradient(subset=['RPE'], cmap='Reds', vmin=0, vmax=10)
                                     .map(lambda x: f"background-color: {color_ratio_ac(x)}; color: black;" if isinstance(x, (int, float)) else "", subset=['RATIO A/C'])
                                     .set_table_attributes('class="modern-table"')
                                    )
                        
                        css_personalizado = "<style>.modern-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); background-color: white; margin-bottom: 20px; } .modern-table thead tr { background-color: #000000; color: #ffffff; } .modern-table th { padding: 12px 15px; font-weight: bold; text-align: center !important; border-bottom: 2px solid #333333; } .modern-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #eeeeee; } .modern-table tbody tr:hover td { filter: brightness(0.95); }</style>"
                        
                        st.markdown(css_personalizado + estilo_ci.to_html(), unsafe_allow_html=True)
                        
                        cg3, cg4 = st.columns(2)
                        with cg3:
                            if df_graficos['CARGA'].sum() > 0:
                                df_ci = df_graficos[df_graficos['CARGA'] > 0].sort_values('CARGA', ascending=False)
                                fig2 = px.bar(
                                    df_ci, x='JUGADOR', y='CARGA', 
                                    color='RPE', color_continuous_scale="Reds", 
                                    range_color=[0, 10], title="Carga de Sesión (Min * RPE)"
                                )
                                if not df_para_medias.empty:
                                    media_equipo = df_para_medias['CARGA'].mean()
                                    fig2.add_hline(
                                        y=media_equipo, 
                                        line_dash="dot", 
                                        line_color="gray", 
                                        annotation_text=f"Media Equipo: {media_equipo:.0f} UA", 
                                        annotation_position="top right"
                                    )
                                st.plotly_chart(fig2, use_container_width=True, key=f"ses_carga_grafico_{idx_real}")
                        with cg4:
                            if df_graficos['RATIO A/C'].sum() > 0:
                                df_ac = df_graficos[df_graficos['RATIO A/C'] > 0].sort_values('RATIO A/C', ascending=False).copy()
                                df_ac['Color_AC'] = df_ac['RATIO A/C'].apply(color_ratio_ac)
                                fig3 = go.Figure(data=[go.Bar(
                                    x=df_ac['JUGADOR'], 
                                    y=df_ac['RATIO A/C'], 
                                    marker_color=df_ac['Color_AC'], 
                                    text=df_ac['RATIO A/C'].round(2), 
                                    textposition='auto'
                                )])
                                fig3.update_layout(title="Riesgo de Lesión (Ratio A/C)")
                                fig3.add_hline(y=1.4, line_dash="dash", line_color="#ff4b4b")
                                st.plotly_chart(fig3, use_container_width=True, key=f"ses_ac_grafico_{idx_real}")
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN 3: CARGA EXTERNA ---
                        st.markdown("#### 🏃‍♂️ 3. Carga Externa (GPS) - Solo jugadores con GPS > 0m")
                        
                        dis_m = df_para_medias_gps['DIS'].mean()
                        dis_m = dis_m if pd.notna(dis_m) else 0.0
                        
                        hsr_m = df_para_medias_gps['DIS AI'].mean()
                        hsr_m = hsr_m if pd.notna(hsr_m) else 0.0
                        
                        spr_m = df_para_medias_gps['Nº SPR'].mean()
                        spr_m = spr_m if pd.notna(spr_m) else 0.0
                        
                        acc_m = df_para_medias_gps['ACC'].mean()
                        acc_m = acc_m if pd.notna(acc_m) else 0.0
                        
                        dcc_m = df_para_medias_gps['DCC'].mean()
                        dcc_m = dcc_m if pd.notna(dcc_m) else 0.0
                        
                        ce1, ce2, ce3, ce4, ce5 = st.columns(5)
                        ce1.metric("Distancia (km)", f"{dis_m:.2f}")
                        ce2.metric("HSR (>21 km/h)", f"{hsr_m:.2f}")
                        ce3.metric("Nº SPRINTS (>24 km/h)", f"{spr_m:.1f}")
                        ce4.metric("ACC (>3 m/s²)", f"{acc_m:.0f}")
                        ce5.metric("DCC (>3 m/s²)", f"{dcc_m:.0f}")
                        
                        if 'HID >21' not in df_informe.columns:
                            df_informe['HID >21'] = df_informe.get('DIS AI', 0.0)
                        
                        cols_ver_ce = ['JUGADOR', 'POS', 'ESTADO', 'DIS', 'HID >21', 'Nº SPR', 'ACC', 'DCC', 'VMAX']
                        
                        # AÑADIDO: Filtramos el DataFrame para quedarnos solo con los jugadores que llevaron GPS (Distancia > 0)
                        df_tabla_ce = df_informe[df_informe['DIS'] > 0]
                        mostrar_tabla_moderna(df_tabla_ce[cols_ver_ce].style.hide(axis="index").format(precision=2))
                        
                        cg5, cg6 = st.columns(2)
                        with cg5:
                            if df_graficos['DIS'].sum() > 0:
                                df_gps_sesion = df_graficos[df_graficos['DIS'] > 0].copy()
                                fig5 = px.scatter(
                                    df_gps_sesion, 
                                    x='DIS', 
                                    y='DIS AI', 
                                    color='POS', 
                                    hover_name='JUGADOR', 
                                    text='JUGADOR', 
                                    title="Volumen vs Intensidad",
                                    color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"}
                                )
                                fig5.update_traces(
                                    textposition='top center', 
                                    marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey'))
                                )
                                media_vol = df_gps_sesion['DIS'].mean()
                                media_int = df_gps_sesion['DIS AI'].mean()
                                fig5.add_vline(x=media_vol, line_dash="dot", line_color="gray", opacity=0.6)
                                fig5.add_hline(y=media_int, line_dash="dot", line_color="gray", opacity=0.6)
                                st.plotly_chart(fig5, use_container_width=True, key=f"ses_hsr_grafico_{idx_real}")
                        with cg6:
                            if df_graficos['ACC'].sum() > 0 or df_graficos['DCC'].sum() > 0:
                                df_accdcc = df_graficos[df_graficos['DIS'] > 0]
                                max_val = max(df_accdcc['ACC'].max(), df_accdcc['DCC'].max()) * 1.1 if not df_accdcc.empty else 10
                                fig4 = px.scatter(
                                    df_accdcc, x='DCC', y='ACC', color='POS', 
                                    hover_name='JUGADOR', 
                                    text='JUGADOR', # <--- AÑADIDO: Muestra el nombre en el punto
                                    title="ACC vs DCC",
                                    color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"}
                                )
                                fig4.update_traces(
                                    textposition='top center', # <--- AÑADIDO: Coloca el texto arriba del punto
                                    marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')) # Añadimos el borde oscuro para igualarlo al otro gráfico
                                )
                                fig4.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", dash="dot"))
                                fig4.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1))
                                st.plotly_chart(fig4, use_container_width=True, key=f"ses_accdcc_grafico_{idx_real}")
                        st.markdown("---")
                        st.markdown("#### ⚠️ Alertas de Riesgo lesivo alto")
                    
                        media_carga = df_para_medias['CARGA'].mean() if not df_para_medias.empty else 0
                        std_carga = df_para_medias['CARGA'].std(ddof=0) if not df_para_medias.empty else 0
                        umbral_carga = media_carga + (2.0 * std_carga) if std_carga > 0 else media_carga * 1.4

                        alertas_jugadores = {}
                        activos = df_informe[df_informe['ESTADO'].isin(["Disponible", "Titular", "Suplente"])]

                        for idx_row, row in activos.iterrows():
                            jug = row['JUGADOR']
                            alertas_jugadores[jug] = {'recuperacion': [], 'carga': [], 'total': 0}
                            
                            tqr = safe_float(row.get('TQR'))
                            well = safe_float(row.get('WELLNESS'))
                            
                            if tqr > 0:
                                if tqr <= 3:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 Recuperación Crítica ({tqr:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif tqr == 4:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🟡 Recuperación Moderada ({tqr:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                    
                            if well > 0:
                                if well >= 24:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 Wellness Crítico ({well:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif 18 <= well <= 23:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🟡 Wellness Moderado ({well:.1f})")
                                    alertas_jugadores[jug]['total'] += 1

                            ratio_ac = safe_float(row.get('RATIO A/C'))
                            carga_aguda = safe_float(row.get('EWMA AGUDA'))
                            carga_sesion = safe_float(row.get('CARGA'))
                            
                            if carga_aguda > 1000:
                                if ratio_ac >= 1.5:
                                    alertas_jugadores[jug]['carga'].append(f"🔴 Ratio A/C en riesgo alto ({ratio_ac:.2f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif 1.35 <= ratio_ac < 1.5:
                                    alertas_jugadores[jug]['carga'].append(f"🟡 Ratio A/C en riesgo moderado ({ratio_ac:.2f})")
                                    alertas_jugadores[jug]['total'] += 1
                                    
                            if media_carga > 0 and carga_sesion > umbral_carga:
                                alertas_jugadores[jug]['carga'].append(f"🟠 Carga Anormal ({carga_sesion:.0f} UA vs Media {media_carga:.0f} UA)")
                                alertas_jugadores[jug]['total'] += 1
                                
                            monot = calcular_monotonia_7d(st.session_state.sesiones, jug, sesion['fecha'])
                            strain = carga_aguda * monot
                            if monot > 2.0 and strain > 4000:
                                alertas_jugadores[jug]['carga'].append(f"🟡 Riesgo por monotonía y fatiga acumulada (Monotonía {monot:.2f}, Strain {strain:.0f})")
                                alertas_jugadores[jug]['total'] += 1
                                
                        alertas_multi = []
                        alertas_rec = []
                        alertas_car = []
                        
                        for jug, data in alertas_jugadores.items():
                            if data['total'] >= 2:
                                alertas_multi.append(f"**{jug}** ({data['total']} alertas): " + " | ".join(data['recuperacion'] + data['carga']))
                            elif data['total'] == 1:
                                if data['recuperacion']: alertas_rec.append(f"**{jug}**: {data['recuperacion'][0]}")
                                if data['carga']: alertas_car.append(f"**{jug}**: {data['carga'][0]}")

                        if not alertas_multi and not alertas_rec and not alertas_car:
                            st.success("✅ Todos los marcadores de fatiga y riesgo del equipo están dentro de los parámetros normales.")
                        else:
                            if alertas_multi:
                                st.error("🚨 **RIESGO MULTIFACTORIAL (2 o más alertas simultáneas)**")
                                for al in alertas_multi: st.write(f"- {al}")
                                st.markdown("---")
                                
                            c_al1, c_al2 = st.columns(2)
                            with c_al1:
                                st.markdown("#### 🧠 Recuperación")
                                if alertas_rec:
                                    for al in alertas_rec: st.warning(al)
                                else:
                                    st.info("✅ Sin alertas individuales.")
                                    
                            with c_al2:
                                st.markdown("#### 🔥 Carga")
                                if alertas_car:
                                    for al in alertas_car: st.warning(al)
                                else:
                                    st.info("✅ Sin alertas individuales.")
                        
                        dict_figs = {
                            "Desglose de Wellness": fig_well,
                            "Calidad de Recuperación (TQR)": fig_tqr,
                            "Carga de Sesión": fig2,
                            "Riesgo de Lesión (Ratio A/C)": fig3,
                            "Volumen vs Intensidad": fig5,
                            "ACC vs DCC": fig4
                        }
                        
                        st.markdown("---")
                        pdf_key = f"pdf_sesion_listo_{idx_real}"
                        
                        if pdf_key not in st.session_state:
                            if st.button("⚙️ Generar PDF de la Sesión", key=f"btn_prepara_pdf_ses_{idx_real}"):
                                with st.spinner("Procesando gráficos y PDF (esto puede tardar unos segundos)..."):
                                    st.session_state[pdf_key] = generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, dict_figs)
                                st.rerun()
                        else:
                            col_pdf1, col_pdf2 = st.columns(2)
                            with col_pdf1:
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=st.session_state[pdf_key],
                                    file_name=f"Sesion_{sesion['fecha']}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_descarga_pdf_ses_{idx_real}"
                                )
                            with col_pdf2:
                                if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_ses_{idx_real}"):
                                    del st.session_state[pdf_key]
                                    st.rerun()                                                          
                    else:
                        st.warning("No hay datos que coincidan con los filtros seleccionados.")
                st.markdown("---")
            
            # --- NUEVA CONDICIÓN AÑADIDA AQUÍ ---
            if st.session_state.get(f"mostrar_datos_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 📂 CARGA DE DATOS DE LA SESIÓN | {sesion['fecha']}")
                # --- NUEVO: MOSTRADOR DE MENSAJES DE SINCRONIZACIÓN ---
                if f'msg_sync_{idx_real}' in st.session_state:
                    for msg in st.session_state[f'msg_sync_{idx_real}']:
                        if "✅" in msg: st.success(msg)
                        elif "⚠️" in msg: st.warning(msg)
                        elif "❓" in msg: st.info(msg)
                    del st.session_state[f'msg_sync_{idx_real}']
                # ------------------------------------------------------
                with st.expander("✍️ Introducción o Edición Manual de Datos", expanded=not sesion.get("informe_generado", False)):
                    st.caption("Introduce Wellness (1-7), Minutos de Sesión, Minutos de GPS, RPE y métricas detalladas.")
                    
                    if sesion.get("datos_informe"):
                        df_manual_base = pd.DataFrame(sesion["datos_informe"])
                    else:
                        rows = []
                        for p in st.session_state.plantilla:
                            rows.append({
                                "JUGADOR": p["JUGADOR"],
                                "POS": p["POS"],
                                "TQR": 0.0,
                                "W_Humor": 0.0,
                                "W_Sueño": 0.0,
                                "W_Fatiga": 0.0,
                                "W_Dolor": 0.0,
                                "W_Estres": 0.0,
                                "RPE": 0.0,
                                "MIN": 0.0,
                                "MIN_GPS": 0.0,
                                "DIS": 0.0,
                                "HID >21": 0.0,
                                "HID >24": 0.0,
                                "SPR >24": 0.0,
                                "SPR >27": 0.0,
                                "V_Med": 0.0,
                                "V_Max": 0.0,
                                "ACC_Max": 0.0,
                                "ACC >2": 0.0,
                                "ACC >3": 0.0,
                                "ACC >4": 0.0,
                                "DCC >2": 0.0,
                                "DCC >3": 0.0,
                                "DCC >4": 0.0,
                                "R_0_7": 0.0,
                                "R_7_14": 0.0,
                                "R_14_21": 0.0,
                                "R_21_24": 0.0,
                                "R_24_27": 0.0,
                                "R_27_30": 0.0,
                                "R_30_45": 0.0
                            })
                        df_manual_base = pd.DataFrame(rows)
                        
                    if "V_Max" not in df_manual_base.columns: df_manual_base["V_Max"] = df_manual_base.get("VMAX", 0.0)
                    if "HID >21" not in df_manual_base.columns: df_manual_base["HID >21"] = df_manual_base.get("DIS AI", 0.0)
                    if "SPR >24" not in df_manual_base.columns: df_manual_base["SPR >24"] = df_manual_base.get("Nº SPR", 0.0)
                    if "ACC >3" not in df_manual_base.columns: df_manual_base["ACC >3"] = df_manual_base.get("ACC", 0.0)
                    if "DCC >3" not in df_manual_base.columns: df_manual_base["DCC >3"] = df_manual_base.get("DCC", 0.0)

                    cols_to_show = [
                        "JUGADOR", "POS", "TQR", 
                        "W_Humor", "W_Sueño", "W_Fatiga", "W_Dolor", "W_Estres", 
                        "RPE", "MIN", "MIN_GPS", "DIS", 
                        "HID >21", "HID >24", "SPR >24", "SPR >27", "V_Med", "V_Max", "ACC_Max",
                        "ACC >2", "ACC >3", "ACC >4", "DCC >2", "DCC >3", "DCC >4",
                        "R_0_7", "R_7_14", "R_14_21", "R_21_24", "R_24_27", "R_27_30", "R_30_45"
                    ]
                    for c in cols_to_show:
                        if c not in df_manual_base.columns:
                            df_manual_base[c] = 0.0
                            
                    edited_df = st.data_editor(
                        df_manual_base[cols_to_show],
                        key=f"editor_manual_{idx_real}",
                        use_container_width=True,
                        hide_index=True,
                        disabled=["JUGADOR", "POS"]
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar Datos Manuales", key=f"btn_save_manual_{idx_real}"):
                            full_records = []
                            for idx_row, row in edited_df.iterrows():
                                suma_well = safe_float(row["W_Humor"]) + safe_float(row["W_Sueño"]) + safe_float(row["W_Fatiga"]) + safe_float(row["W_Dolor"]) + safe_float(row["W_Estres"])
                                min_ses = safe_float(row["MIN"])
                                min_gps_val = safe_float(row["MIN_GPS"])
                                
                                if min_gps_val > 0 and safe_float(row["DIS"]) > 0:
                                    dis = safe_float(row["DIS"])
                                    dis_ai_21 = safe_float(row["HID >21"])
                                    dis_ai_24 = safe_float(row["HID >24"])
                                    spr_24 = safe_float(row["SPR >24"])
                                    spr_27 = safe_float(row["SPR >27"])
                                    v_med = safe_float(row["V_Med"])
                                    v_max = safe_float(row["V_Max"])
                                    acc_max = safe_float(row["ACC_Max"])
                                    acc_2 = safe_float(row["ACC >2"])
                                    acc_3 = safe_float(row["ACC >3"])
                                    acc_4 = safe_float(row["ACC >4"])
                                    dcc_2 = safe_float(row["DCC >2"])
                                    dcc_3 = safe_float(row["DCC >3"])
                                    dcc_4 = safe_float(row["DCC >4"])
                                    r_0_7 = safe_float(row["R_0_7"])
                                    r_7_14 = safe_float(row["R_7_14"])
                                    r_14_21 = safe_float(row["R_14_21"])
                                    r_21_24 = safe_float(row["R_21_24"])
                                    r_24_27 = safe_float(row["R_24_27"])
                                    r_27_30 = safe_float(row["R_27_30"])
                                    r_30_45 = safe_float(row["R_30_45"])
                                else:
                                    dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_27 = v_med = v_max = acc_max = acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = r_30_45 = 0.0

                                rec = {
                                    "JUGADOR": row["JUGADOR"],
                                    "POS": row["POS"],
                                    "TQR": safe_float(row["TQR"]),
                                    "WELLNESS": suma_well,
                                    "W_Humor": safe_float(row["W_Humor"]),
                                    "W_Sueño": safe_float(row["W_Sueño"]),
                                    "W_Fatiga": safe_float(row["W_Fatiga"]),
                                    "W_Dolor": safe_float(row["W_Dolor"]),
                                    "W_Estres": safe_float(row["W_Estres"]),
                                    "RPE": safe_float(row["RPE"]),
                                    "MIN": min_ses,
                                    "MIN_GPS": min_gps_val,
                                    "CARGA": min_ses * safe_float(row["RPE"]),
                                    
                                    "DIS": dis,
                                    "DIS AI": dis_ai_21,
                                    "Nº SPR": spr_24,
                                    "ACC": acc_3,
                                    "DCC": dcc_3,
                                    "VMAX": v_max,
                                    "Z1": r_0_7 + r_7_14,
                                    "Z2": r_14_21,
                                    "Z3": r_21_24,
                                    "Z4": r_24_27,
                                    "Z5": r_27_30,
                                    "Z6": r_30_45,
                                    
                                    "HID >21": dis_ai_21,
                                    "HID >24": dis_ai_24,
                                    "SPR >24": spr_24,
                                    "SPR >27": spr_27,
                                    "V_Med": v_med,
                                    "V_Max": v_max,
                                    "ACC_Max": acc_max,
                                    "ACC >2": acc_2,
                                    "ACC >3": acc_3,
                                    "ACC >4": acc_4,
                                    "DCC >2": dcc_2,
                                    "DCC >3": dcc_3,
                                    "DCC >4": dcc_4,
                                    "R_0_7": r_0_7,
                                    "R_7_14": r_7_14,
                                    "R_14_21": r_14_21,
                                    "R_21_24": r_21_24,
                                    "R_24_27": r_24_27,
                                    "R_27_30": r_27_30,
                                    "R_30_45": r_30_45
                                }
                                full_records.append(rec)
                                
                            st.session_state.sesiones[idx_real]['datos_informe'] = full_records
                            st.session_state.sesiones[idx_real]['informe_generado'] = True
                            guardar_datos()
                            st.success("✅ ¡Datos manuales guardados correctamente!")
                            st.rerun()

                    with col_btn2:
                        if st.button("🗑️ Borrar Datos de la Sesión", key=f"btn_del_session_{idx_real}"):
                            st.session_state.sesiones[idx_real]['datos_informe'] = []
                            st.session_state.sesiones[idx_real]['informe_generado'] = False
                            guardar_datos()
                            st.success("✅ Datos de la sesión borrados correctamente.")
                            st.rerun()

                with st.expander("📁 Importar desde Archivos Excel (Wellness, RPE, GPS)"):
                    st.caption("Sube tus archivos. El sistema integrará a toda la plantilla cruzando Wellness, RPE y los GPS disponibles.")
                    col_up1, col_up2, col_up3 = st.columns(3)
                    with col_up1: archivo_well = st.file_uploader("1. Bienestar (Wellness):", type=["xlsx"], key=f"up_well_{idx_real}")
                    with col_up2: archivo_rpe = st.file_uploader("2. Carga Interna (RPE):", type=["xlsx"], key=f"up_rpe_{idx_real}")
                    with col_up3: archivo_gps = st.file_uploader("3. Carga Externa (GPS):", type=["xlsx"], key=f"up_gps_{idx_real}")
                    
                    if st.button("⚙️ Procesar y Sincronizar Archivos", key=f"btn_proc_{idx_real}"):
                        try:
                            import difflib
                            
                            df_w_up = pd.read_excel(archivo_well) if archivo_well else pd.DataFrame()
                            df_r_up = pd.read_excel(archivo_rpe) if archivo_rpe else pd.DataFrame()
                            df_g_up = pd.read_excel(archivo_gps) if archivo_gps else pd.DataFrame()
                            
                            fecha_sesion_str = pd.to_datetime(sesion['fecha']).strftime('%Y-%m-%d')
                            
                            def filtrar_fecha(df):
                                if df.empty: return df
                                col_f = next((c for c in df.columns if 'marca temporal' in str(c).lower() or 'activity date' in str(c).lower()), None)
                                if col_f:
                                    df['FECHA_TEMP'] = pd.to_datetime(df[col_f], errors='coerce').dt.strftime('%Y-%m-%d')
                                    return df[df['FECHA_TEMP'] == fecha_sesion_str].drop(columns=['FECHA_TEMP'])
                                return df

                            df_w_up = filtrar_fecha(df_w_up)
                            df_r_up = filtrar_fecha(df_r_up)
                            df_g_up = filtrar_fecha(df_g_up)

                            nombres_plantilla = [p['JUGADOR'] for p in st.session_state.plantilla]
                            no_encontrados_en_app = set()
                            
                            def emparejar_nombre(nombre_excel):
                                if pd.isna(nombre_excel): return None
                                n_ex = limpiar_nombre(nombre_excel)
                                for n_app in nombres_plantilla:
                                    if n_ex == limpiar_nombre(n_app): return n_app
                                for n_app in nombres_plantilla:
                                    n_app_cl = limpiar_nombre(n_app)
                                    if n_ex in n_app_cl or n_app_cl in n_ex: return n_app
                                matches = difflib.get_close_matches(n_ex, [limpiar_nombre(n) for n in nombres_plantilla], n=1, cutoff=0.7)
                                if matches:
                                    for n_app in nombres_plantilla:
                                        if limpiar_nombre(n_app) == matches[0]: return n_app
                                return None

                            faltan_w = []
                            if not df_w_up.empty and 'Nombre' in df_w_up.columns:
                                df_w_up['JUGADOR_MATCH'] = df_w_up['Nombre'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_w_up[df_w_up['JUGADOR_MATCH'].isna()]['Nombre'].dropna().tolist())
                                df_w_up = df_w_up.dropna(subset=['JUGADOR_MATCH'])
                                faltan_w = [n for n in nombres_plantilla if n not in df_w_up['JUGADOR_MATCH'].tolist()]
                            elif archivo_well: faltan_w = nombres_plantilla.copy()

                            faltan_r = []
                            if not df_r_up.empty and 'Nombre' in df_r_up.columns:
                                df_r_up['JUGADOR_MATCH'] = df_r_up['Nombre'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_r_up[df_r_up['JUGADOR_MATCH'].isna()]['Nombre'].dropna().tolist())
                                df_r_up = df_r_up.dropna(subset=['JUGADOR_MATCH'])
                                faltan_r = [n for n in nombres_plantilla if n not in df_r_up['JUGADOR_MATCH'].tolist()]
                            elif archivo_rpe: faltan_r = nombres_plantilla.copy()

                            if not df_g_up.empty and 'Player Name' in df_g_up.columns:
                                df_g_up['JUGADOR_MATCH'] = df_g_up['Player Name'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_g_up[df_g_up['JUGADOR_MATCH'].isna()]['Player Name'].dropna().tolist())
                                df_g_up = df_g_up.dropna(subset=['JUGADOR_MATCH'])

                            # 1. RECUPERAR DATOS EXISTENTES PARA NO SOBREESCRIBIRLOS
                            datos_actuales = {d["JUGADOR"]: d for d in sesion.get("datos_informe", [])}
                            
                            registros_sesion = []
                            for nombre_final in sorted(nombres_plantilla):
                                match_p = next((p for p in st.session_state.plantilla if p['JUGADOR'] == nombre_final), None)
                                pos_jug = match_p['POS'] if match_p else "DEF"

                                # 2. OBTENER REGISTRO PREVIO O CREAR UNO NUEVO A CERO
                                reg = datos_actuales.get(nombre_final, {
                                    "JUGADOR": nombre_final, "POS": pos_jug,
                                    "TQR": 0.0, "WELLNESS": 0.0,
                                    "W_Humor": 0.0, "W_Sueño": 0.0, "W_Fatiga": 0.0, "W_Dolor": 0.0, "W_Estres": 0.0,
                                    "RPE": 0.0, "MIN": 0.0, "MIN_GPS": 0.0, "CARGA": 0.0,
                                    "DIS": 0.0, "DIS AI": 0.0, "Nº SPR": 0.0, "ACC": 0.0, "DCC": 0.0, "VMAX": 0.0,
                                    "Z1": 0.0, "Z2": 0.0, "Z3": 0.0, "Z4": 0.0, "Z5": 0.0, "Z6": 0.0,
                                    "HID >21": 0.0, "HID >24": 0.0, "SPR >24": 0.0, "SPR >27": 0.0,
                                    "V_Med": 0.0, "V_Max": 0.0, "ACC_Max": 0.0, "ACC >2": 0.0, "ACC >3": 0.0, "ACC >4": 0.0,
                                    "DCC >2": 0.0, "DCC >3": 0.0, "DCC >4": 0.0, "R_0_7": 0.0, "R_7_14": 0.0,
                                    "R_14_21": 0.0, "R_21_24": 0.0, "R_24_27": 0.0, "R_27_30": 0.0, "R_30_45": 0.0
                                })

                                # 3. ACTUALIZAR SÓLO LOS MÓDULOS QUE SE HAYAN SUBIDO EN ESTA TANDA
                                
                                # --- RPE ---
                                if not df_r_up.empty:
                                    match_r = df_r_up[df_r_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_r.empty: 
                                        reg["RPE"] = safe_float(match_r.iloc[0].get('Índice de Esfuerzo Percibido', 0))
                                        # Si sube RPE y el tiempo de sesión está vacío, asumimos 90 mins por defecto
                                        if reg["MIN"] == 0: reg["MIN"] = 90.0

                                # --- WELLNESS ---
                                if not df_w_up.empty:
                                    match_w = df_w_up[df_w_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_w.empty:
                                        r_w = match_w.iloc[0]
                                        reg["TQR"] = safe_float(r_w.get('Índice de Calidad de Recuperación', 0))
                                        reg["W_Fatiga"] = safe_float(r_w.get('Fatiga:', 0))
                                        reg["W_Sueño"] = safe_float(r_w.get('Calidad del sueño:', 0))
                                        reg["W_Dolor"] = safe_float(r_w.get('Dolor muscular:', 0))
                                        reg["W_Estres"] = safe_float(r_w.get('Nivel de estrés:', 0))
                                        reg["W_Humor"] = safe_float(r_w.get('Humor:', 0))
                                        reg["WELLNESS"] = reg["W_Fatiga"] + reg["W_Sueño"] + reg["W_Dolor"] + reg["W_Estres"] + reg["W_Humor"]

                                # --- GPS ---
                                if not df_g_up.empty:
                                    match_g = df_g_up[df_g_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_g.empty:
                                        row_g = match_g.iloc[0]
                                        dis = safe_float(row_g.get('Distance (km)', 0))
                                        if dis > 0:
                                            min_gps_excel = extraer_minutos(str(row_g.get('Time Played', '0')))
                                            reg["MIN_GPS"] = min_gps_excel if min_gps_excel > 0 else 90.0
                                            reg["MIN"] = reg["MIN_GPS"] # El GPS manda sobre el tiempo global de sesión
                                            
                                            reg["DIS"] = dis
                                            reg["HID >21"] = safe_float(row_g.get('HID distance (> 21.00 km/h)', 0))
                                            reg["DIS AI"] = reg["HID >21"]
                                            reg["HID >24"] = safe_float(row_g.get('HID distance (> 24.00 km/h)', 0))
                                            
                                            reg["SPR >24"] = safe_float(row_g.get('# of Sprints (> 24.00 km/h)', 0))
                                            reg["Nº SPR"] = reg["SPR >24"]
                                            reg["SPR >27"] = safe_float(row_g.get('# of Sprints (> 30.00 km/h)', 0))
                                            
                                            reg["V_Med"] = safe_float(row_g.get('Avg Speed (km/h)', 0))
                                            reg["VMAX"] = safe_float(row_g.get('Max Speed (km/h)', 0))
                                            reg["V_Max"] = reg["VMAX"]
                                            
                                            reg["ACC >2"] = safe_float(row_g.get('# of Accelerations (> 2.00 m/s²)', 0))
                                            reg["ACC >3"] = safe_float(row_g.get('# of Accelerations (> 3.00 m/s²)', 0))
                                            reg["ACC"] = reg["ACC >3"]
                                            reg["ACC >4"] = safe_float(row_g.get('# of Accelerations (> 4.00 m/s²)', 0))
                                            
                                            reg["DCC >2"] = safe_float(row_g.get('# of Decelerations (> 2.00 m/s²)', 0))
                                            reg["DCC >3"] = safe_float(row_g.get('# of Decelerations (> 3.00 m/s²)', 0))
                                            reg["DCC"] = reg["DCC >3"]
                                            reg["DCC >4"] = safe_float(row_g.get('# of Decelerations (> 4.00 m/s²)', 0))
                                            
                                            reg["R_0_7"] = safe_float(row_g.get('Distance Speed Range (0 - 7 km)', 0))
                                            reg["R_7_14"] = safe_float(row_g.get('Distance Speed Range (7 - 14 km)', 0))
                                            reg["R_14_21"] = safe_float(row_g.get('Distance Speed Range (14 - 21 km)', 0))
                                            reg["R_21_24"] = safe_float(row_g.get('Distance Speed Range (21 - 24 km)', 0))
                                            reg["R_24_27"] = safe_float(row_g.get('Distance Speed Range (24 - 27 km)', 0))
                                            reg["R_27_30"] = safe_float(row_g.get('Distance Speed Range (27 - 30 km)', 0))
                                            reg["R_30_45"] = safe_float(row_g.get('# of Sprints (> 30.00 km/h)', 0)) 
                                            
                                            reg["Z1"] = reg["R_0_7"] + reg["R_7_14"]
                                            reg["Z2"] = reg["R_14_21"]
                                            reg["Z3"] = reg["R_21_24"]
                                            reg["Z4"] = reg["R_24_27"]
                                            reg["Z5"] = reg["R_27_30"]

                                # 4. RECALCULAR CARGA FINAL SEGÚN LAS ACTUALIZACIONES
                                reg["CARGA"] = reg["MIN"] * reg["RPE"]
                                
                                registros_sesion.append(reg)
                                
                            st.session_state.sesiones[idx_real]['datos_informe'] = registros_sesion
                            st.session_state.sesiones[idx_real]['informe_generado'] = True
                            guardar_datos()
                            
                            msgs = [f"✅ Sincronización completada. Se generó la tabla con los {len(nombres_plantilla)} jugadores de tu plantilla."]
                            if archivo_well and faltan_w: msgs.append(f"⚠️ **Faltan en Wellness:** {', '.join(faltan_w)}")
                            if archivo_rpe and faltan_r: msgs.append(f"⚠️ **Faltan en RPE:** {', '.join(faltan_r)}")
                            if no_encontrados_en_app: msgs.append(f"❓ **Están en Excel pero NO en tu App:** {', '.join(no_encontrados_en_app)}")
                            st.session_state[f'msg_sync_{idx_real}'] = msgs
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al procesar: {e}")
                            st.error(f"Error al procesar y sincronizar los archivos: {e}")

            if st.session_state.get(f"mostrar_lesion_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 🚑 PARTE MÉDICO | {sesion['fecha']}")
                st.caption("Registra aquí una incidencia ocurrida durante esta sesión.")
                
                if not st.session_state.plantilla:
                    st.warning("No hay jugadores en la plantilla para registrar lesiones.")
                else:
                    with st.form(key=f"form_lesion_{idx_real}"):
                        nombres_plantilla = [j["JUGADOR"] for j in st.session_state.plantilla]
                        
                        c_L1, c_L2 = st.columns(2)
                        les_jugador = c_L1.selectbox("Jugador Afectado:", nombres_plantilla)
                        les_tipo = c_L2.selectbox("Tipo de Lesión:", ["Muscular", "Tendinosa", "Artículo-ligamentosa", "Fractura", "Otra"])
                        
                        c_L3, c_L4 = st.columns(2)
                        les_zona = c_L3.selectbox("Zona Afectada:", ["Pie", "Tobillo", "Pierna", "Rodilla", "Muslo", "Cadera - Ingles", "Extremidades Superiores", "Tronco", "Cabeza"])
                        
                        zonas_bilaterales = ["Pie", "Tobillo", "Pierna", "Rodilla", "Muslo", "Cadera - Ingles", "Extremidades Superiores"]
                        if les_zona in zonas_bilaterales:
                            les_lado = c_L4.selectbox("Lado:", ["Derecha", "Izquierda"])
                        else:
                            les_lado = "N/A"
                            c_L4.write("") 
                            
                        c_L5, c_L6, c_L7 = st.columns(3)
                        les_lat = c_L5.selectbox("Lateralidad de la lesión:", ["Dominante", "No dominante", "Sin lateralidad"])
                        les_contacto = c_L6.radio("¿Hubo contacto?", ["Sí", "No"], horizontal=True)
                        les_cesped = c_L7.radio("Superficie:", ["Natural", "Artificial"], horizontal=True)
                        
                        c_L8, c_L9 = st.columns([1, 3])
                        les_recidiva = c_L8.radio("¿Es Recidiva?", ["No", "Sí"], horizontal=True)
                        les_comentarios = c_L9.text_input("Comentarios / Mecanismo lesional:")
                        
                        if st.form_submit_button("💾 Registrar Lesión"):
                            nueva_lesion = {
                                "id_sesion": sesion["fecha"],
                                "tipo_sesion": "Partido" if es_partido else "Entrenamiento",
                                "jugador": les_jugador,
                                "tipo": les_tipo,
                                "zona": les_zona,
                                "lado": les_lado,
                                "lateralidad": les_lat,
                                "contacto": les_contacto,
                                "cesped": les_cesped,
                                "recidiva": les_recidiva,
                                "comentarios": les_comentarios,
                                "dias_baja": None,
                                "estado": "Activa",
                                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            st.session_state.lesiones.append(nueva_lesion)
                            guardar_datos()
                            st.success(f"¡Parte médico de {les_jugador} guardado correctamente!")
                            st.rerun()
                st.markdown("---")

