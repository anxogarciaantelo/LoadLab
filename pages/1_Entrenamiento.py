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

tab_cal, tab_temp, tab_micro, tab_ses, tab_add = st.tabs(["🗓️ Calendario", "🏆 Temporada", "🔄 Microciclos", "📋 Sesiones", "➕ Añadir Sesión"])

with tab_cal:
    # 1. ESTADO DE NAVEGACIÓN DEL CALENDARIO
    if 'cal_offset' not in st.session_state:
        st.session_state.cal_offset = 0

    import calendar
    hoy = date.today()
    mes_actual = hoy.month - 1 + st.session_state.cal_offset
    year = hoy.year + mes_actual // 12
    month = mes_actual % 12 + 1
    
    meses_nombres = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    # Botones de navegación del mes
    c_nav1, c_nav2, c_nav3 = st.columns([1, 3, 1])
    if c_nav1.button("◀ Mes Anterior", use_container_width=True):
        st.session_state.cal_offset -= 1
        st.rerun()
    with c_nav2:
        st.markdown(f"<h3 style='text-align: center; color: #f8fafc; margin-top: 0; margin-bottom: 10px; text-transform: uppercase; font-weight: 800; letter-spacing: 1px;'>🗓️ {meses_nombres[month]} {year}</h3>", unsafe_allow_html=True)
    if c_nav3.button("Mes Siguiente ▶", use_container_width=True):
        st.session_state.cal_offset += 1
        st.rerun()
    
    # Renderizado de la cuadrícula
    st.markdown("""
        <div style='background-color: #1e293b; border: 1px solid #334155; border-top: 3px solid #3b82f6; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
    """, unsafe_allow_html=True)
    
    cal = calendar.monthcalendar(year, month)
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    html_cal = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; text-align: center;'>"
    
    for d in dias_semana:
        html_cal += f"<div style='background-color: #0f172a; color: #94a3b8; padding: 12px 5px; font-weight: 800; font-size: 0.9rem; border-radius: 8px; border: 1px solid #334155;'>{d}</div>"
        
    hoy_str = str(date.today())
    
    for week in cal:
        for day in week:
            if day == 0:
                html_cal += "<div style='padding: 10px; background-color: transparent;'></div>"
            else:
                fecha_str = f"{year}-{month:02d}-{day:02d}"
                es_hoy = "border: 2px solid #3b82f6;" if fecha_str == hoy_str else "border: 1px solid #334155;"
                bg_color = "#0f172a" if fecha_str == hoy_str else "#1e293b"
                
                sesiones_dia = [s for s in st.session_state.sesiones if s["fecha"] == fecha_str]
                contenido_extra = ""
                
                if sesiones_dia:
                    for s in sesiones_dia:
                        nom = s.get("nombre_dinamico", s.get("tipo", ""))
                        if "Partido" in s.get("tipo", ""):
                            color_badge = "#dc2626" 
                            sub = s.get('rival', 'Rival')
                        else:
                            color_badge = "#10b981" 
                            sub = s.get('descripcion', 'TD')
                            
                        contenido_extra += f"<div style='background-color: {color_badge}; color: white; font-size: 0.8rem; font-weight: 800; padding: 8px 6px; border-radius: 6px; margin-top: 6px; width: 100%; box-sizing: border-box; word-wrap: break-word; line-height: 1.2; box-shadow: 0 2px 4px rgba(0,0,0,0.2);' title='{nom} | {sub}'>{nom}<br><span style='font-size: 0.7rem; font-weight: 600;'>{sub}</span></div>"
                
                html_cal += f"<div style='background-color: {bg_color}; {es_hoy} padding: 10px 5px; border-radius: 8px; min-height: 110px; display: flex; flex-direction: column; align-items: center; transition: transform 0.2s ease;' onmouseover=\"this.style.transform='scale(1.03)'\" onmouseout=\"this.style.transform='scale(1)'\"><span style='color: #f8fafc; font-weight: 800; font-size: 1.2rem; margin-bottom: 4px;'>{day}</span>{contenido_extra}</div>"
                
    html_cal += "</div></div>"
    st.markdown(html_cal, unsafe_allow_html=True)

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
                
                fechas_semana = [s["fecha"] for s in ses_sem]
                df_master = st.session_state.df_master_informes
                
                df_sem = df_master[
                    (df_master['FECHA'].isin(fechas_semana)) & 
                    (df_master['ESTADO'].isin(["Disponible", "Titular", "Suplente"]))
                ].copy()
                
                if 'HID >21' in df_sem.columns: df_sem['DIS AI'] = df_sem['HID >21']
                if 'SPR >24' in df_sem.columns: df_sem['Nº SPR'] = df_sem['SPR >24']
                if 'ACC >3' in df_sem.columns: df_sem['ACC'] = df_sem['ACC >3']
                if 'DCC >3' in df_sem.columns: df_sem['DCC'] = df_sem['DCC >3']
                
                if not df_sem.empty:
                    df_sem['TQR'] = df_sem['TQR'].replace(0, np.nan)
                    df_sem['WELLNESS'] = df_sem['WELLNESS'].replace(0, np.nan)
                    df_sem['RPE'] = df_sem['RPE'].replace(0, np.nan)
                    
                    df_jug_sum_int = df_sem.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
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
                        "Carga": df_jug_sum_int['CARGA'].mean() if not df_jug_sum_int.empty else 0,
                        "DIS": df_jug_sum_ext['DIS'].mean() if not df_jug_sum_ext.empty else 0,
                        "HSR": df_jug_sum_ext['DIS AI'].mean() if not df_jug_sum_ext.empty else 0,
                        "Sprints": df_jug_sum_ext['Nº SPR'].mean() if not df_jug_sum_ext.empty else 0,
                        "ACC": df_jug_sum_ext['ACC'].mean() if not df_jug_sum_ext.empty else 0,
                        "DCC": df_jug_sum_ext['DCC'].mean() if not df_jug_sum_ext.empty else 0
                    })
            
            if not kpis_temporada:
                st.warning("No hay suficientes datos válidos para generar la temporada.")
            else:
                # 1. ORDENACIÓN NUMÉRICA ABSOLUTA PARA EVITAR FALLOS DE STRING (Micro 10 antes que 2)
                df_temporada = pd.DataFrame(kpis_temporada).sort_values("ID", ascending=True).reset_index(drop=True)
                
                # --- CÁLCULO DE MEDIAS Y TENDENCIAS (Actual vs Media Temporada) ---
                ultimo_m = df_temporada.iloc[-1]
                medias_temp = df_temporada.mean(numeric_only=True)
                
                def calc_tendencia_temporada(col):
                    media = medias_temp[col]
                    actual = ultimo_m[col]
                    
                    if media == 0: 
                        return {'valor': 0, 'inverso': False, 'texto': 'esta semana'}
                    
                    # Corrección científica: En Wellness (5-35), la fatiga real empieza en 5.
                    if col == 'Wellness' and media > 5:
                        diff_pct = ((actual - media) / (media - 5)) * 100
                    else:
                        diff_pct = ((actual - media) / media) * 100
                    
                    if col == 'Wellness':
                        texto = "peor esta semana" if diff_pct > 0 else "mejor esta semana"
                        inverso = True
                    elif col == 'TQR':
                        texto = "mejor esta semana" if diff_pct > 0 else "peor esta semana"
                        inverso = False
                    else:
                        texto = "más esta semana" if diff_pct > 0 else "menos esta semana"
                        inverso = False  # RPE ahora es directo: más = verde, menos = rojo
                        
                    return {'valor': diff_pct, 'inverso': inverso, 'texto': texto}
                
                # --- KPIs COMPACTOS EN UNA SOLA FILA ---
                st.markdown(f"#### 🎯 Promedios de la Temporada (Tendencia vs {ultimo_m['Microciclo']})")
                cols_kpi = st.columns(10)
                
                from utils.math_helpers import render_kpi_elite
                with cols_kpi[0]: render_kpi_elite("Wellness", f"{medias_temp['Wellness']:.1f}", tendencia=calc_tendencia_temporada('Wellness'))
                with cols_kpi[1]: render_kpi_elite("TQR", f"{medias_temp['TQR']:.1f}", tendencia=calc_tendencia_temporada('TQR'))
                with cols_kpi[2]: render_kpi_elite("RPE", f"{medias_temp['RPE']:.1f}", tendencia=calc_tendencia_temporada('RPE'))
                with cols_kpi[3]: render_kpi_elite("Minutos", f"{medias_temp['Minutos']:.0f}", tendencia=calc_tendencia_temporada('Minutos'))
                with cols_kpi[4]: render_kpi_elite("Carga", f"{medias_temp['Carga']:.0f}", tendencia=calc_tendencia_temporada('Carga'))
                with cols_kpi[5]: render_kpi_elite("DIS (km)", f"{medias_temp['DIS']:.1f}", tendencia=calc_tendencia_temporada('DIS'))
                with cols_kpi[6]: render_kpi_elite("HSR (m)", f"{medias_temp['HSR']:.0f}", tendencia=calc_tendencia_temporada('HSR'))
                with cols_kpi[7]: render_kpi_elite("Sprints", f"{medias_temp['Sprints']:.1f}", tendencia=calc_tendencia_temporada('Sprints'))
                with cols_kpi[8]: render_kpi_elite("ACC", f"{medias_temp['ACC']:.0f}", tendencia=calc_tendencia_temporada('ACC'))
                with cols_kpi[9]: render_kpi_elite("DCC", f"{medias_temp['DCC']:.0f}", tendencia=calc_tendencia_temporada('DCC'))
                
                st.markdown("---")
                
                # --- GRÁFICOS SUPERIORES Y MEJORADOS ---
                st.markdown("#### 📈 Evolución Gráfica de la Temporada")
                cg1, cg2 = st.columns(2)
                
                with cg1:
                    fig_well_tqr = go.Figure()
                    fig_well_tqr.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada['Wellness'], name="Fatiga/Dolor (Wellness)", marker_color="rgba(239, 68, 68, 0.7)", yaxis="y1"))
                    fig_well_tqr.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['TQR'], name="Recuperación (TQR)", mode="lines+markers", line=dict(color="#10b981", width=3), marker=dict(size=8), yaxis="y2"))
                    fig_well_tqr.update_layout(
                        title="Recuperación vs Fatiga",
                        yaxis=dict(title="Puntos Wellness", range=[0, 35]),
                        yaxis2=dict(title="TQR", overlaying="y", side="right", range=[0, 10]),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_well_tqr, use_container_width=True)
                    
                with cg2:
                    fig_carga = go.Figure()
                    fig_carga.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada['Carga'], name="Carga (UA)", marker_color="#3b82f6"))
                    media_carga = df_temporada['Carga'].mean()
                    fig_carga.add_hline(y=media_carga, line_dash="dash", line_color="#f59e0b", annotation_text=f"Media Acumulada: {media_carga:.0f} UA")
                    fig_carga.update_layout(title="Carga Interna Acumulada", yaxis_title="Unidades Arbitrarias")
                    st.plotly_chart(fig_carga, use_container_width=True)
                    
                cg3, cg4 = st.columns(2)
                with cg3:
                    fig_ext = go.Figure()
                    fig_ext.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada['DIS'], name="Volumen (km)", marker_color="rgba(59, 130, 246, 0.6)", yaxis="y1"))
                    fig_ext.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['HSR'], name="HSR (>21km/h)", mode="lines+markers", line=dict(color="#f59e0b", width=3), yaxis="y2"))
                    fig_ext.update_layout(
                        title="Volumen vs Alta Intensidad",
                        yaxis=dict(title="Distancia (km)"),
                        yaxis2=dict(title="HSR (m)", overlaying="y", side="right"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_ext, use_container_width=True)
                    
                with cg4:
                    fig_mec = go.Figure()
                    fig_mec.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['ACC'], name="Aceleraciones", mode="lines+markers", line=dict(color="#10b981", width=2)))
                    fig_mec.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['DCC'], name="Deceleraciones", mode="lines+markers", line=dict(color="#ef4444", width=2)))
                    fig_mec.update_layout(title="Carga Mecánica (ACC vs DCC)", yaxis_title="Cantidad (>3 m/s²)")
                    st.plotly_chart(fig_mec, use_container_width=True)

                st.markdown("---")
                
                # --- TABLA INTERACTIVA (FILTRABLE Y ORDENABLE) ---
                st.markdown("#### 📋 Base de Datos de Microciclos")
                st.caption("Puedes clickar en el nombre de cualquier columna para ordenar los datos de mayor a menor, o usar la lupa para buscar.")
                
                # Ordenamos el DataFrame de más reciente a más antiguo (por ID) pero ocultamos la columna técnica ID
                df_temporada_show = df_temporada.sort_values("ID", ascending=False).drop(columns=["ID"])
                
                # Usamos st.dataframe para habilitar la funcionalidad de filtrado y ordenación nativa de Streamlit
                st.dataframe(
                    df_temporada_show.style.format(precision=1),
                    use_container_width=True,
                    hide_index=True
                )

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
            # 1. PREPARACIÓN DEL SELECTOR (Sustituye a la lista interminable de Expanders)
            df_m = pd.DataFrame(lista_micro).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
            df_m['Micro_Num'] = df_m.index + 1
            df_m_desc = df_m.sort_values("lunes_dt", ascending=False)
            
            dict_micros = {}
            for _, r_m in df_m_desc.iterrows():
                etiqueta = f"📦 Microciclo {r_m['Micro_Num']} | Semana del {r_m['ini']} al {r_m['fin']}"
                dict_micros[etiqueta] = r_m
            
            st.markdown("### 🔄 Análisis de Microciclos")
            
            # Selector y Filtros en la misma línea
            c_sel1, c_sel2 = st.columns([1, 2])
            micro_seleccionado = c_sel1.selectbox("Selecciona un Microciclo para analizar:", list(dict_micros.keys()))
            
            # 2. EXTRACCIÓN DE LA FILA SELECCIONADA (Sustituye al bucle for row in df_m.iterrows())
            row = dict_micros[micro_seleccionado]
            num_sem = row["num_semana"]
            idx_real = row["Micro_Num"] - 1 
            nombre_etiqueta = micro_seleccionado
            
            # --- AQUÍ EMPIEZA TU LÓGICA MATEMÁTICA EXACTA ORIGINAL ---
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
                                "CARGA": safe_float(d_jug.get("CARGA")), "DIS": safe_float(d_jug.get("DIS")),
                                "DIS AI": safe_float(d_jug.get("HID >21", d_jug.get("DIS AI", 0))),
                                "Nº SPR": safe_float(d_jug.get("SPR >24", d_jug.get("Nº SPR", 0))),
                                "ACC": safe_float(d_jug.get("ACC >3", d_jug.get("ACC", 0))),
                                "DCC": safe_float(d_jug.get("DCC >3", d_jug.get("DCC", 0))),
                                "VMAX": safe_float(d_jug.get("V_Max", d_jug.get("VMAX", 0))), "ENTRENO": 1 
                            })
                        else:
                            datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": est_jug, "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})
                    else:
                        datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": "Sin Sesión", "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})

            df_semana = pd.DataFrame(datos_7_dias)

            with c_sel2:
                col_f1, col_f2 = st.columns(2)
                with col_f1: pos_filtro = st.radio("Filtrar Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"fw_p_{num_sem}")
                with col_f2: rol_filtro = st.radio("Filtrar Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"fw_r_{num_sem}")
            
            df_filtrado = df_semana.copy()
            if pos_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["POS"] == pos_filtro]
            if rol_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["ROL"] == rol_filtro]

            if df_filtrado.empty:
                st.warning("No hay jugadores que coincidan con estos filtros en esta semana.")
            else:
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

                st.markdown("---")
                
                # --- NUEVOS KPIS DE DISEÑO ÉLITE EN UNA FILA ---
                st.markdown(f"#### 🎯 Resumen Acumulado del Microciclo")
                cols_kpi = st.columns(10)
                from utils.math_helpers import render_kpi_elite
                
                with cols_kpi[0]: render_kpi_elite("Wellness", f"{df_diario['WELLNESS'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                with cols_kpi[1]: render_kpi_elite("TQR", f"{df_diario['TQR'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                with cols_kpi[2]: render_kpi_elite("RPE", f"{df_diario['RPE'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                with cols_kpi[3]: render_kpi_elite("Minutos", f"{df_diario['MIN'].sum():.0f}" if not df_diario.empty else "0")
                with cols_kpi[4]: render_kpi_elite("Carga", f"{df_diario['CARGA'].sum():.0f}" if not df_diario.empty else "0")
                with cols_kpi[5]: render_kpi_elite("DIS (km)", f"{df_diario['DIS'].sum():.1f}" if not df_diario.empty else "0")
                with cols_kpi[6]: render_kpi_elite("HSR (m)", f"{df_diario['DIS AI'].sum():.0f}" if not df_diario.empty else "0")
                with cols_kpi[7]: render_kpi_elite("Sprints", f"{df_diario['Nº SPR'].sum():.1f}" if not df_diario.empty else "0")
                with cols_kpi[8]: render_kpi_elite("ACC", f"{df_diario['ACC'].sum():.0f}" if not df_diario.empty else "0")
                with cols_kpi[9]: render_kpi_elite("DCC", f"{df_diario['DCC'].sum():.0f}" if not df_diario.empty else "0")

                st.markdown("---")
                st.markdown("#### 📋 Resumen por Día")
                if not df_diario.empty:
                    mostrar_tabla_moderna(df_diario.style.hide(axis="index").format(precision=2))

                st.markdown("---")
                st.markdown("#### 🧠 Bienestar")
                cg_b1, cg_b2 = st.columns(2)
                with cg_b1:
                    df_tqr_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                    fig_tqr = px.bar(df_tqr_plot, x='DIA', y='TQR', color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], title="Calidad de Recuperación (TQR)")
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
                    
                    fig_well = go.Figure()
                    colores_w = px.colors.qualitative.Set2
                    factores = ['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor']
                    df_w_plot = pd.DataFrame(datos_w)
                    
                    for i, factor in enumerate(factores):
                        fig_well.add_trace(go.Bar(x=df_w_plot['DIA'], y=df_w_plot[factor], name=factor, marker_color=colores_w[i]))
                    
                    fig_well.update_layout(title="Evolución Wellness Diario", barmode='stack', yaxis_title="Puntos", legend_title_text="Factor", yaxis_range=[0, 35], hovermode="x unified")
                    fig_well.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                    fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                    st.plotly_chart(fig_well, use_container_width=True, key=f"micro_well_{num_sem}_{idx_real}")

                st.markdown("---")
                st.markdown("#### 🔥 Carga Interna")
                cg_i1, cg_i2, cg_i3 = st.columns(3)
                with cg_i1:
                    fig_min = px.bar(df_diario, x='DIA', y='MIN', title="Evolución Minutos")
                    st.plotly_chart(fig_min, use_container_width=True, key=f"micro_min_{num_sem}_{idx_real}")
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
                
                st.dataframe(df_indiv.style.format(precision=1), use_container_width=True, hide_index=True)
                
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
                    "TQR": fig_tqr, "Wellness": fig_well, "Minutos": fig_min, "RPE": fig_rpe, 
                    "Carga": fig_carga, "ACC_DCC": fig_accdcc, "DIS": fig_dis, "DIS_AI": fig_disai
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
                            file_name=f"Microciclo_{num_sem}.pdf",
                            mime="application/pdf",
                            key=f"btn_descarga_pdf_{num_sem}_{idx_real}"
                        )
                    with col_pdf2:
                        if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_{num_sem}_{idx_real}"):
                            del st.session_state[pdf_key]
                            st.rerun()

with tab_ses:
    # --- CSS ESPECÍFICO PARA BOTONES DE SESIÓN ---
    st.markdown("""
    <style>
    div[data-testid="column"]:has(.sesion-toolbar-hook) div[data-testid="stHorizontalBlock"] button {
        min-height: 42px !important; /* Altura aumentada para evitar recortes */
        padding: 0 !important;
        border-radius: 6px !important;
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="column"]:has(.sesion-toolbar-hook) div[data-testid="stHorizontalBlock"] button:hover {
        border-color: #3b82f6 !important;
        transform: translateY(-2px);
    }
    /* Forzamos píxeles absolutos (px) para ignorar el escalado global del 90% */
    div[data-testid="column"]:has(.sesion-toolbar-hook) div[data-testid="stHorizontalBlock"] button p,
    div[data-testid="column"]:has(.sesion-toolbar-hook) div[data-testid="stHorizontalBlock"] button span {
        font-size: 22px !important; 
        line-height: 1 !important;
        margin: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.sesiones:
        render_estado_vacio(
            icono="📅", 
            titulo="Sin sesiones registradas", 
            descripcion="Aún no has planificado ningún entrenamiento o partido. LoadLab necesita este calendario para mapear la fatiga del equipo.",
            accion_sugerida="Ve a la pestaña '➕ Añadir Sesión' para generar tu primer evento."
        )
    else:
        # 1. Agrupar sesiones por microciclo y mapear numeración relativa
        micros_dict = {}
        semanas_unicas = set()
        for s in st.session_state.sesiones:
            num_sem = obtener_numero_semana(s["fecha"])
            semanas_unicas.add(num_sem)
            if num_sem not in micros_dict:
                micros_dict[num_sem] = []
            micros_dict[num_sem].append(s)
            
        # Creamos el mapa ordenando cronológicamente las semanas
        mapa_micros = {num_sem: i + 1 for i, num_sem in enumerate(sorted(list(semanas_unicas)))}
        micros_sorted = sorted(micros_dict.keys(), reverse=True)
        
        # Gestión de estado de la vista activa para ultra-rendimiento (Solo carga 1 panel a la vez)
        if "ses_activa_idx" not in st.session_state:
            st.session_state.ses_activa_idx = None
        if "ses_activa_view" not in st.session_state:
            st.session_state.ses_activa_view = None

        # Renderizar microciclos
        for num_sem in micros_sorted:
            sesiones_sem = sorted(micros_dict[num_sem], key=lambda x: x["fecha"])
            _, _, lunes, domingo = obtener_rango_fechas_semana(sesiones_sem[0]["fecha"])
            
            micro_relativo = mapa_micros[num_sem]
            
            st.markdown(f"""
            <div style='background-color: #1e293b; padding: 12px 18px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-top: 25px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);'>
                <h4 style='margin: 0; color: #f8fafc; font-weight: 800; text-transform: uppercase;'>📦 MICROCICLO {micro_relativo} 
                <span style='font-size: 0.95rem; color: #94a3b8; font-weight: 700;'>(Semana {lunes.strftime('%d/%m')} al {domingo.strftime('%d/%m')})</span></h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Cuadrícula horizontal para las sesiones (Máximo 7 columnas por fila)
            cols = st.columns(7)
            for i, sesion in enumerate(sesiones_sem):
                col_idx = i % 7
                idx_real = st.session_state.sesiones.index(sesion)
                es_partido = "Partido" in sesion['tipo']
                color_borde = "#dc2626" if es_partido else "#10b981"
                
                f_dt = datetime.strptime(sesion["fecha"], "%Y-%m-%d")
                dia_semana = ["L", "M", "X", "J", "V", "S", "D"][f_dt.weekday()]
                f_str = f"{dia_semana} {f_dt.strftime('%d/%m')}"
                
                nom_dyn = sesion.get("nombre_dinamico", sesion["tipo"])
                if es_partido: sub = sesion.get('rival', 'Rival')
                else: sub = sesion.get('descripcion', 'TD')
                
                with cols[col_idx]:
                    st.markdown(f"""
                    <div class="sesion-toolbar-hook" style='background-color: #0f172a; border: 1px solid #334155; border-top: 3px solid {color_borde}; border-radius: 8px; padding: 10px 5px; text-align: center; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); height: 70px; display: flex; flex-direction: column; justify-content: center;'>
                        <strong style='color: #f8fafc; font-size: 0.95rem;'>{f_str}</strong>
                        <span style='color: #94a3b8; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{sub}'>{sub}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Botones de herramientas compactos en la propia tarjeta con lógica TOGGLE
                    b_cols = st.columns(5)
                    
                    def toggle_view(target_idx, target_view):
                        if st.session_state.ses_activa_idx == target_idx and st.session_state.ses_activa_view == target_view:
                            st.session_state.ses_activa_idx = None
                            st.session_state.ses_activa_view = None
                        else:
                            st.session_state.ses_activa_idx = target_idx
                            st.session_state.ses_activa_view = target_view
                            
                    if b_cols[0].button("🏥", key=f"bd_{idx_real}", help="Disponibilidad"):
                        toggle_view(idx_real, "disp"); st.rerun()
                    if b_cols[1].button("📊", key=f"bi_{idx_real}", help="Informe"):
                        toggle_view(idx_real, "inf"); st.rerun()
                    if b_cols[2].button("📂", key=f"bc_{idx_real}", help="Cargar Datos"):
                        toggle_view(idx_real, "datos"); st.rerun()
                    if b_cols[3].button("🚑", key=f"bl_{idx_real}", help="Lesión"):
                        toggle_view(idx_real, "les"); st.rerun()
                    if es_partido:
                        if b_cols[4].button("⚡", key=f"bs_{idx_real}", help="Stats Partido"):
                            toggle_view(idx_real, "stats"); st.rerun()
                    else:
                        b_cols[4].write("")
            
            # --- PANEL ACTIVO PARA ESTE MICROCICLO ---
            active_idx = st.session_state.ses_activa_idx
            active_view = st.session_state.ses_activa_view
            
            if active_idx is not None and active_view is not None:
                if active_idx in [st.session_state.sesiones.index(s) for s in sesiones_sem]:
                    sesion = st.session_state.sesiones[active_idx]
                    idx_real = active_idx
                    es_partido = "Partido" in sesion['tipo']
                    
                    st.markdown("---")
                    
                    # ---------------------------------------------------------
                    # HERRAMIENTA 1: DISPONIBILIDAD (MULTIFILTRO OPTIMIZADO)
                    # ---------------------------------------------------------
                    if active_view == "disp":
                        st.markdown(f"#### 🏥 CONTROL DE DISPONIBILIDAD | {sesion['fecha']}")
                        if es_partido:
                            opciones_disp = ["Suplente", "No convocado", "Lesionado", "Enfermo", "Selección", "No disponible"]
                            default_disp = "Titular"
                        else:
                            opciones_disp = ["Lesionado", "Readaptación", "Enfermo", "Falta", "Selección", "No disponible"]
                            default_disp = "Disponible"
                        
                        disp_dict_clean = {limpiar_nombre(k): v for k, v in sesion.get("disponibilidad", {}).items()}
                        jugs_plantilla = [p["JUGADOR"] for p in st.session_state.plantilla]
                        
                        # --- RENDERIZAR KPIs EN UNA SOLA FILA ---
                        todas_opciones = [default_disp] + opciones_disp
                        conteos = Counter([disp_dict_clean.get(limpiar_nombre(j), default_disp) for j in jugs_plantilla])
                        
                        cols_m = st.columns(len(todas_opciones))
                        for i, opc in enumerate(todas_opciones):
                            cols_m[i].metric(opc, conteos.get(opc, 0))
                        st.markdown("---")
                        
                        jugadores_por_estado = {est: [] for est in opciones_disp}
                        for j in jugs_plantilla:
                            est = disp_dict_clean.get(limpiar_nombre(j), default_disp)
                            if est in opciones_disp:
                                jugadores_por_estado[est].append(j)

                        st.info(f"💡 Por defecto, todos los jugadores de la plantilla que no añadas abajo se marcarán automáticamente como **{default_disp}**.")
                        
                        with st.form(key=f"form_disp_{idx_real}"):
                            selecciones = {}
                            
                            # RENDERIZAR SELECTORES EN UNA SOLA FILA HORIZONTAL
                            cols_disp = st.columns(len(opciones_disp))
                            for i, est in enumerate(opciones_disp):
                                with cols_disp[i]:
                                    selecciones[est] = st.multiselect(f"{est}", jugs_plantilla, default=jugadores_por_estado[est])
                                    
                            if st.form_submit_button("💾 Guardar Disponibilidad", type="primary", use_container_width=True):
                                disp_final = {}
                                for j in jugs_plantilla:
                                    asignado = False
                                    for est, lista_jugs in selecciones.items():
                                        if j in lista_jugs:
                                            disp_final[j] = est
                                            asignado = True
                                            break
                                    if not asignado:
                                        disp_final[j] = default_disp
                                        
                                st.session_state.sesiones[idx_real]["disponibilidad"] = disp_final
                                guardar_datos(modulo="sesiones")
                                st.success("Disponibilidad guardada correctamente.")
                                st.rerun()

                    # ---------------------------------------------------------
                    # HERRAMIENTA 2: INFORME MAESTRO
                    # ---------------------------------------------------------
                    elif active_view == "inf":
                        if sesion.get("informe_generado", False) and sesion.get("datos_informe"):
                            df_informe = pd.DataFrame(sesion["datos_informe"])
                            cols_metricas = ['TQR', 'WELLNESS', 'W_Humor', 'W_Sueño', 'W_Fatiga', 'W_Dolor', 'W_Estres', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'HID >21', 'SPR >24', 'ACC >3', 'DCC >3', 'V_Max']
                            for c in cols_metricas:
                                if c in df_informe.columns: df_informe[c] = pd.to_numeric(df_informe[c], errors='coerce').fillna(0.0)
                            
                            if 'HID >21' in df_informe.columns: df_informe['DIS AI'] = df_informe['HID >21']
                            if 'SPR >24' in df_informe.columns: df_informe['Nº SPR'] = df_informe['SPR >24']
                            if 'ACC >3' in df_informe.columns:  df_informe['ACC'] = df_informe['ACC >3']
                            if 'DCC >3' in df_informe.columns:  df_informe['DCC'] = df_informe['DCC >3']
                            if 'V_Max' in df_informe.columns:   df_informe['VMAX'] = df_informe['V_Max']
                            
                            disp_dict = sesion.get("disponibilidad", {})
                            disp_dict_clean = {limpiar_nombre(k): v for k, v in disp_dict.items()}
                            default_disp = "Titular" if es_partido else "Disponible"
                            df_informe['ESTADO'] = df_informe['JUGADOR'].map(lambda j: disp_dict_clean.get(limpiar_nombre(j), default_disp))

                            df_master_sesion = st.session_state.df_master_informes[st.session_state.df_master_informes['FECHA'] == sesion["fecha"]]
                            df_master_sesion = df_master_sesion.drop_duplicates(subset=['JUGADOR'], keep='last')
                            dic_ewma = df_master_sesion.set_index('JUGADOR')[['EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']].to_dict('index')
                            
                            df_informe['EWMA AGUDA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA AGUDA', 0.0))
                            df_informe['EWMA CRÓNICA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA CRÓNICA', 0.0))
                            df_informe['RATIO A/C'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C', 0.0))

                            col_filt1, col_filt2 = st.columns(2)
                            with col_filt1:
                                filtro_pos = st.radio("Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"rp_{idx_real}")
                                if filtro_pos != "TODOS": df_informe = df_informe[df_informe["POS"] == filtro_pos]
                            if es_partido:
                                with col_filt2:
                                    filtro_rol = st.radio("Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"rr_{idx_real}")
                                    if filtro_rol != "TODOS": df_informe = df_informe[df_informe["ESTADO"] == filtro_rol]

                            estados_validos_medias = ["Disponible", "Titular", "Suplente"]
                            df_para_medias = df_informe[(df_informe['ESTADO'].isin(estados_validos_medias)) & (df_informe['POS'] != "POR")].copy()
                            df_para_medias['TQR'] = df_para_medias['TQR'].replace(0, np.nan)
                            df_para_medias['WELLNESS'] = df_para_medias['WELLNESS'].replace(0, np.nan)
                            df_para_medias['RPE'] = df_para_medias['RPE'].replace(0, np.nan)
                            df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0].copy()
                            
                            df_graficos = df_informe[df_informe['JUGADOR'] != ""].copy()
                            fig_well = fig_tqr = fig2 = fig3 = fig5 = fig4 = None

                            if not df_informe.empty:
                                # --- 1. CÁLCULO DE % V. MÁX HISTÓRICA ---
                                df_master_hist = st.session_state.df_master_informes[st.session_state.df_master_informes['FECHA'] <= sesion["fecha"]]
                                vmax_historica = df_master_hist.groupby('JUGADOR')['VMAX'].max().to_dict()
                                df_informe['VMAX_HIST'] = df_informe['JUGADOR'].map(lambda j: vmax_historica.get(j, 0.0))
                                df_informe['% VMAX'] = np.where(df_informe['VMAX_HIST'] > 0, (df_informe['VMAX'] / df_informe['VMAX_HIST']) * 100, 0.0)

                                # Re-filtrar con la nueva columna añadida
                                df_para_medias = df_informe[(df_informe['ESTADO'].isin(["Disponible", "Titular", "Suplente"])) & (df_informe['POS'] != "POR")].copy()
                                df_para_medias['TQR'] = df_para_medias['TQR'].replace(0, np.nan)
                                df_para_medias['WELLNESS'] = df_para_medias['WELLNESS'].replace(0, np.nan)
                                df_para_medias['RPE'] = df_para_medias['RPE'].replace(0, np.nan)
                                df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0].copy()
                                df_graficos = df_informe[df_informe['JUGADOR'] != ""].copy()

                                # --- 2. CÁLCULO DE ALERTAS (MOVIDO ARRIBA) ---
                                media_carga = df_para_medias['CARGA'].mean() if not df_para_medias.empty else 0
                                std_carga = df_para_medias['CARGA'].std(ddof=0) if not df_para_medias.empty else 0
                                umbral_carga = media_carga + (2.0 * std_carga) if std_carga > 0 else media_carga * 1.4

                                alertas_jugadores = {}
                                activos = df_informe[df_informe['ESTADO'].isin(["Disponible", "Titular", "Suplente"])]

                                for _, row in activos.iterrows():
                                    jug = row['JUGADOR']
                                    alertas_jugadores[jug] = {'recuperacion': [], 'carga': [], 'total': 0}
                                    tqr, well = safe_float(row.get('TQR')), safe_float(row.get('WELLNESS'))
                                    
                                    if tqr > 0:
                                        if tqr <= 3: alertas_jugadores[jug]['recuperacion'].append(f"🔴 Recuperación Crítica ({tqr:.1f})"); alertas_jugadores[jug]['total'] += 1
                                        elif tqr == 4: alertas_jugadores[jug]['recuperacion'].append(f"🟡 Recuperación Moderada ({tqr:.1f})"); alertas_jugadores[jug]['total'] += 1
                                    if well > 0:
                                        if well >= 24: alertas_jugadores[jug]['recuperacion'].append(f"🔴 Wellness Crítico ({well:.1f})"); alertas_jugadores[jug]['total'] += 1
                                        elif 18 <= well <= 23: alertas_jugadores[jug]['recuperacion'].append(f"🟡 Wellness Moderado ({well:.1f})"); alertas_jugadores[jug]['total'] += 1

                                    ratio_ac, carga_aguda, carga_sesion = safe_float(row.get('RATIO A/C')), safe_float(row.get('EWMA AGUDA')), safe_float(row.get('CARGA'))
                                    
                                    if carga_aguda > 1000:
                                        if ratio_ac >= 1.5: alertas_jugadores[jug]['carga'].append(f"🔴 Ratio A/C en riesgo alto ({ratio_ac:.2f})"); alertas_jugadores[jug]['total'] += 1
                                        elif 1.35 <= ratio_ac < 1.5: alertas_jugadores[jug]['carga'].append(f"🟡 Ratio A/C en riesgo moderado ({ratio_ac:.2f})"); alertas_jugadores[jug]['total'] += 1
                                    if media_carga > 0 and carga_sesion > umbral_carga:
                                        alertas_jugadores[jug]['carga'].append(f"🟠 Carga Anormal ({carga_sesion:.0f} UA vs Media {media_carga:.0f} UA)"); alertas_jugadores[jug]['total'] += 1
                                        
                                    monot = calcular_monotonia_7d(st.session_state.sesiones, jug, sesion['fecha'])
                                    strain = carga_aguda * monot
                                    if monot > 2.0 and strain > 4000:
                                        alertas_jugadores[jug]['carga'].append(f"🟡 Riesgo por monotonía y fatiga (Strain {strain:.0f})"); alertas_jugadores[jug]['total'] += 1
                                        
                                alertas_multi, alertas_rec, alertas_car = [], [], []
                                for jug, data in alertas_jugadores.items():
                                    if data['total'] >= 2: alertas_multi.append(f"**{jug}**: " + " | ".join(data['recuperacion'] + data['carga']))
                                    elif data['total'] == 1:
                                        if data['recuperacion']: alertas_rec.append(f"**{jug}**: {data['recuperacion'][0]}")
                                        if data['carga']: alertas_car.append(f"**{jug}**: {data['carga'][0]}")

                                # --- 3. RENDERIZADO DE KPIs GLOBALES EN UNA SOLA FILA ---
                                tqr_m = df_para_medias['TQR'].mean() if pd.notna(df_para_medias['TQR'].mean()) else 0.0
                                well_m = df_para_medias['WELLNESS'].mean() if pd.notna(df_para_medias['WELLNESS'].mean()) else 0.0
                                rpe_m = df_para_medias['RPE'].mean() if pd.notna(df_para_medias['RPE'].mean()) else 0.0
                                carga_m = df_para_medias['CARGA'].mean() if pd.notna(df_para_medias['CARGA'].mean()) else 0.0
                                min_m = df_para_medias['MIN'].mean() if pd.notna(df_para_medias['MIN'].mean()) else 0.0
                                
                                dis_m = df_para_medias_gps['DIS'].mean() if pd.notna(df_para_medias_gps['DIS'].mean()) else 0.0
                                hsr_m = df_para_medias_gps['DIS AI'].mean() if pd.notna(df_para_medias_gps['DIS AI'].mean()) else 0.0
                                spr_m = df_para_medias_gps['Nº SPR'].mean() if pd.notna(df_para_medias_gps['Nº SPR'].mean()) else 0.0
                                acc_m = df_para_medias_gps['ACC'].mean() if pd.notna(df_para_medias_gps['ACC'].mean()) else 0.0
                                dcc_m = df_para_medias_gps['DCC'].mean() if pd.notna(df_para_medias_gps['DCC'].mean()) else 0.0
                                pct_vmax_m = df_para_medias_gps['% VMAX'].mean() if pd.notna(df_para_medias_gps['% VMAX'].mean()) else 0.0

                                # Estructuras HTML Forzadas para igualar el CSS de style.css
                                def html_tarjeta_doble(color, val1, val2, lbl1, lbl2):
                                    return f"""
                                    <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid {color}; border-radius: 8px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); display: flex; flex-direction: row; align-items: stretch; margin-bottom: 10px; height: 85px;">
                                        <div style='flex: 1; padding-right: 8px; border-right: 1px solid #334155; display: flex; flex-direction: column;'>
                                            <span style='font-size: 0.85rem; color: #f8fafc; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; text-align: left; line-height: 1.1;'>{lbl1}</span>
                                            <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc; text-align: center; margin-top: auto;'>{val1}</span>
                                        </div>
                                        <div style='flex: 1; padding-left: 8px; display: flex; flex-direction: column;'>
                                            <span style='font-size: 0.85rem; color: #f8fafc; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; text-align: left; line-height: 1.1;'>{lbl2}</span>
                                            <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc; text-align: center; margin-top: auto;'>{val2}</span>
                                        </div>
                                    </div>
                                    """
                                    
                                def html_tarjeta_simple(color, val, lbl):
                                    return f"""
                                    <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid {color}; border-radius: 8px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); display: flex; flex-direction: column; margin-bottom: 10px; height: 85px;">
                                        <span style='font-size: 0.85rem; color: #f8fafc; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; text-align: left; line-height: 1.1;'>{lbl}</span>
                                        <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc; text-align: center; margin-top: auto;'>{val}</span>
                                    </div>
                                    """

                                # Dividimos el espacio horizontal en proporciones 1:2:3 (6 tarjetas en total)
                                col_w, col_i, col_e = st.columns([1, 2, 3])
                                
                                with col_w:
                                    st.markdown("<h5 style='color: #f8fafc; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; margin-top: 0;'>🧠 Bienestar</h5>", unsafe_allow_html=True)
                                    st.markdown(html_tarjeta_doble("#10b981", f"{tqr_m:.1f}", f"{well_m:.1f}", "TQR", "Wellness"), unsafe_allow_html=True)
                                    
                                with col_i:
                                    st.markdown("<h5 style='color: #f8fafc; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; margin-top: 0;'>🔥 Carga Interna</h5>", unsafe_allow_html=True)
                                    # Anidamos columnas internamente para que queden en la misma línea
                                    c_i1, c_i2 = st.columns(2)
                                    with c_i1:
                                        st.markdown(html_tarjeta_doble("#f59e0b", f"{min_m:.0f}'", f"{rpe_m:.1f}", "Minutos", "RPE"), unsafe_allow_html=True)
                                    with c_i2:
                                        st.markdown(html_tarjeta_simple("#f59e0b", f"{carga_m:.0f} UA", "Carga Interna"), unsafe_allow_html=True)
                                        
                                with col_e:
                                    st.markdown("<h5 style='color: #f8fafc; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; margin-top: 0;'>🏃‍♂️ Carga Externa</h5>", unsafe_allow_html=True)
                                    c_e1, c_e2, c_e3 = st.columns(3)
                                    with c_e1:
                                        st.markdown(html_tarjeta_doble("#3b82f6", f"{dis_m:.2f} km", f"{hsr_m:.0f} m", "Distancia", "HSR (>21)"), unsafe_allow_html=True)
                                    with c_e2:
                                        st.markdown(html_tarjeta_doble("#3b82f6", f"{spr_m:.1f}", f"{pct_vmax_m:.1f} %", "Sprints", "% V. Máx"), unsafe_allow_html=True)
                                    with c_e3:
                                        st.markdown(html_tarjeta_doble("#3b82f6", f"{acc_m:.0f}", f"{dcc_m:.0f}", "ACC (>3)", "DCC (>3)"), unsafe_allow_html=True)

                                st.markdown("---")
                                
                                # --- 4. ALERTAS DE RIESGO MOVIDAS ARRIBA (EN 3 COLUMNAS) ---
                                st.markdown("#### ⚠️ Alertas de Rendimiento y Riesgo Lesivo")
                                if not alertas_multi and not alertas_rec and not alertas_car:
                                    st.success("✅ Todos los marcadores de fatiga y riesgo del equipo están dentro de los parámetros normales.")
                                else:
                                    c_al_rec, c_al_car, c_al_mul = st.columns(3)
                                    with c_al_rec:
                                        st.markdown("##### 🧠 Recuperación")
                                        if alertas_rec:
                                            for al in alertas_rec: st.warning(al)
                                        else: st.info("✅ Sin alertas.")
                                    with c_al_car:
                                        st.markdown("##### 🔥 Carga")
                                        if alertas_car:
                                            for al in alertas_car: st.warning(al)
                                        else: st.info("✅ Sin alertas.")
                                    with c_al_mul:
                                        st.markdown("##### 🚨 Riesgo Multifactorial")
                                        if alertas_multi:
                                            for al in alertas_multi: st.error(al)
                                        else: st.success("✅ Sin alertas críticas.")

                                st.markdown("---")

                                # --- 5. GRÁFICOS DE BIENESTAR ---
                                st.markdown("#### 🧠 1. Bienestar y Recuperación")
                                cg1, cg2 = st.columns(2)
                                with cg1:
                                    if df_graficos['WELLNESS'].sum() > 0:
                                        df_well = df_graficos[df_graficos['WELLNESS'] > 0].sort_values('WELLNESS', ascending=False).copy()
                                        nombres_limpios = {'W_Sueño': 'Sueño', 'W_Fatiga': 'Fatiga', 'W_Dolor': 'Dolor', 'W_Estres': 'Estrés', 'W_Humor': 'Humor'}
                                        df_well = df_well.rename(columns=nombres_limpios)
                                        fig_well = go.Figure()
                                        for i, factor in enumerate(list(nombres_limpios.values())):
                                            fig_well.add_trace(go.Bar(x=df_well['JUGADOR'], y=df_well[factor], name=factor, marker_color=px.colors.qualitative.Set2[i]))
                                        fig_well.update_layout(title="<b>Desglose de Wellness</b>", barmode='stack', yaxis_title="Puntos", legend_title_text="Factores", yaxis_range=[0, 35], plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=120, l=40, r=40), hovermode="x unified")
                                        fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                                        fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                                        st.plotly_chart(fig_well, use_container_width=True, key=f"ses_w_{idx_real}")
                                with cg2:
                                    if df_graficos['TQR'].sum() > 0:
                                        df_tqr = df_graficos[df_graficos['TQR'] > 0].sort_values('TQR')
                                        fig_tqr = px.bar(df_tqr, x='JUGADOR', y='TQR', color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], title="Calidad de Recuperación (TQR)")
                                        fig_tqr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                        fig_tqr.update_yaxes(range=[1, 10])
                                        st.plotly_chart(fig_tqr, use_container_width=True, key=f"ses_t_{idx_real}")

                                st.markdown("---")

                                # --- 6. CARGA INTERNA (GRÁFICOS PRIMERO, TABLA DESPUÉS) ---
                                st.markdown("#### 🔥 2. Carga Interna")
                                
                                cg3, cg4 = st.columns(2)
                                with cg3:
                                    if df_graficos['CARGA'].sum() > 0:
                                        df_ci = df_graficos[df_graficos['CARGA'] > 0].sort_values('CARGA', ascending=False)
                                        fig2 = px.bar(df_ci, x='JUGADOR', y='CARGA', color='RPE', color_continuous_scale="Reds", range_color=[0, 10], title="Carga de Sesión (Min * RPE)")
                                        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                        if not df_para_medias.empty:
                                            fig2.add_hline(y=df_para_medias['CARGA'].mean(), line_dash="dot", line_color="gray", annotation_text=f"Media Equipo", annotation_position="top right")
                                        st.plotly_chart(fig2, use_container_width=True, key=f"ses_c_{idx_real}")
                                with cg4:
                                    if df_graficos['RATIO A/C'].sum() > 0:
                                        df_ac = df_graficos[df_graficos['RATIO A/C'] > 0].sort_values('RATIO A/C', ascending=False).copy()
                                        df_ac['Color_AC'] = df_ac['RATIO A/C'].apply(color_ratio_ac)
                                        fig3 = go.Figure(data=[go.Bar(x=df_ac['JUGADOR'], y=df_ac['RATIO A/C'], marker_color=df_ac['Color_AC'], text=df_ac['RATIO A/C'].round(2), textposition='auto')])
                                        fig3.update_layout(title="Riesgo de Lesión (Ratio A/C)")
                                        fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                        fig3.add_hline(y=1.4, line_dash="dash", line_color="#ff4b4b")
                                        st.plotly_chart(fig3, use_container_width=True, key=f"ses_ac_{idx_real}")
                                
                                cols_ver_ci = ['JUGADOR', 'POS', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']
                                estilo_ci = (df_informe[cols_ver_ci].style.hide(axis="index").format(precision=2).background_gradient(subset=['RPE'], cmap='Reds', vmin=0, vmax=10).map(lambda x: f"background-color: {color_ratio_ac(x)}; color: black;" if isinstance(x, (int, float)) else "", subset=['RATIO A/C']))
                                mostrar_tabla_moderna(estilo_ci)
                                
                                st.markdown("---")

                                # --- 7. CARGA EXTERNA (GRÁFICOS PRIMERO, TABLA DESPUÉS, CON % VMAX) ---
                                st.markdown("#### 🏃‍♂️ 3. Carga Externa (GPS)")
                                
                                cg5, cg6 = st.columns(2)
                                with cg5:
                                    if df_graficos['DIS'].sum() > 0:
                                        df_gps_sesion = df_graficos[df_graficos['DIS'] > 0].copy()
                                        fig5 = px.scatter(df_gps_sesion, x='DIS', y='DIS AI', color='POS', hover_name='JUGADOR', text='JUGADOR', title="Volumen vs Intensidad", color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"})
                                        fig5.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                        fig5.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                        fig5.add_vline(x=df_gps_sesion['DIS'].mean(), line_dash="dot", line_color="gray", opacity=0.6)
                                        fig5.add_hline(y=df_gps_sesion['DIS AI'].mean(), line_dash="dot", line_color="gray", opacity=0.6)
                                        st.plotly_chart(fig5, use_container_width=True, key=f"ses_h_{idx_real}")
                                with cg6:
                                    if df_graficos['ACC'].sum() > 0 or df_graficos['DCC'].sum() > 0:
                                        df_accdcc = df_graficos[df_graficos['DIS'] > 0]
                                        max_val = max(df_accdcc['ACC'].max(), df_accdcc['DCC'].max()) * 1.1 if not df_accdcc.empty else 10
                                        fig4 = px.scatter(df_accdcc, x='DCC', y='ACC', color='POS', hover_name='JUGADOR', text='JUGADOR', title="ACC vs DCC", color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"})
                                        fig4.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                        fig4.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", dash="dot"))
                                        fig4.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                        st.plotly_chart(fig4, use_container_width=True, key=f"ses_a_{idx_real}")
                                        
                                # AÑADIDO: '% VMAX' en la tabla de GPS
                                cols_ver_ce = ['JUGADOR', 'POS', 'ESTADO', 'DIS', 'HID >21', 'Nº SPR', 'ACC', 'DCC', 'VMAX', '% VMAX']
                                df_tabla_ce = df_informe[df_informe['DIS'] > 0]
                                mostrar_tabla_moderna(df_tabla_ce[cols_ver_ce].style.hide(axis="index").format(precision=2))
                                
                                st.markdown("---")
                                pdf_key = f"pdf_sesion_listo_{idx_real}"
                                if pdf_key not in st.session_state:
                                    if st.button("⚙️ Generar PDF de la Sesión", key=f"btn_prepara_pdf_ses_{idx_real}", type="primary", use_container_width=True):
                                        with st.spinner("Procesando gráficos y PDF..."):
                                            st.session_state[pdf_key] = generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, {"Desglose de Wellness": fig_well, "Calidad de Recuperación (TQR)": fig_tqr, "Carga de Sesión": fig2, "Riesgo de Lesión (Ratio A/C)": fig3, "Volumen vs Intensidad": fig5, "ACC vs DCC": fig4})
                                        st.rerun()
                                else:
                                    col_pdf1, col_pdf2 = st.columns(2)
                                    with col_pdf1: st.download_button("📥 Descargar PDF", data=st.session_state[pdf_key], file_name=f"Sesion_{sesion['fecha']}.pdf", mime="application/pdf", key=f"btn_descarga_pdf_ses_{idx_real}", use_container_width=True)
                                    with col_pdf2:
                                        if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_ses_{idx_real}", use_container_width=True): del st.session_state[pdf_key]; st.rerun()                                                          
                        else:
                            st.warning("El informe de esta sesión aún no ha sido procesado.")

                    # ---------------------------------------------------------
                    # HERRAMIENTA 3: CARGA DE DATOS (FORMULARIO OPTIMIZADO)
                    # ---------------------------------------------------------
                    elif active_view == "datos":
                        st.markdown(f"#### 📂 CARGA DE DATOS | {sesion['fecha']}")

                        # --- MOTOR DE IMPUTACIÓN DE GPS PARA JUGADORES SIN UNIDAD ---
                        def aplicar_imputacion_gps(registros, sesion_actual, es_partido_flag):
                            disp_dict = {limpiar_nombre(k): v for k, v in sesion_actual.get("disponibilidad", {}).items()}
                            default_estado = "Titular" if es_partido_flag else "Disponible"
                            
                            # 1. Analizamos a los que SÍ llevaron GPS para sacar los ratios
                            datos_validos = []
                            for reg in registros:
                                jug = reg["JUGADOR"]
                                pos = reg.get("POS", "DEF")
                                if reg.get("DIS", 0) > 0 and pos != "POR":
                                    p_match = next((p for p in st.session_state.plantilla if p["JUGADOR"] == jug), {})
                                    pos_esp = p_match.get("pos_1", pos)
                                    min_gps = safe_float(reg.get("MIN_GPS", reg.get("MIN", 0)))
                                    if min_gps > 0:
                                        datos_validos.append({
                                            "POS_ESP": pos_esp, "POS_GEN": pos,
                                            "DIS_pm": safe_float(reg.get("DIS")) / min_gps,
                                            "DIS_AI_pm": safe_float(reg.get("HID >21", reg.get("DIS AI", 0))) / min_gps,
                                            "SPR_pm": safe_float(reg.get("SPR >24", reg.get("Nº SPR", 0))) / min_gps,
                                            "ACC_pm": safe_float(reg.get("ACC >3", reg.get("ACC", 0))) / min_gps,
                                            "DCC_pm": safe_float(reg.get("DCC >3", reg.get("DCC", 0))) / min_gps,
                                            "VMAX": safe_float(reg.get("V_Max", reg.get("VMAX", 0)))
                                        })
                                        
                            if datos_validos:
                                df_val = pd.DataFrame(datos_validos)
                                medias_esp = df_val.groupby("POS_ESP").mean().to_dict('index')
                                medias_gen = df_val.groupby("POS_GEN").mean().to_dict('index')
                                medias_eq = df_val.mean().to_dict()
                                
                                # 2. Imputamos a los que no tienen GPS pero entrenaron
                                for reg in registros:
                                    jug = reg["JUGADOR"]
                                    pos = reg.get("POS", "DEF")
                                    estado = disp_dict.get(limpiar_nombre(jug), default_estado)
                                    
                                    elegible = estado in ["Disponible", "Titular", "Suplente"]
                                    min_jug = safe_float(reg.get("MIN", 0))
                                    
                                    # Condición: Elegible, de campo, con 0 distancia y que haya entrenado (MIN > 0)
                                    if elegible and pos != "POR" and safe_float(reg.get("DIS", 0)) == 0 and min_jug > 0:
                                        p_match = next((p for p in st.session_state.plantilla if p["JUGADOR"] == jug), {})
                                        pos_esp = p_match.get("pos_1", pos)
                                        
                                        # Escala de fallback: Misma posición específica -> Posición general -> Media de equipo
                                        ratios = medias_esp.get(pos_esp, medias_gen.get(pos, medias_eq))
                                        
                                        reg["MIN_GPS"] = min_jug
                                        reg["DIS"] = ratios["DIS_pm"] * min_jug
                                        reg["DIS AI"] = ratios["DIS_AI_pm"] * min_jug
                                        reg["HID >21"] = ratios["DIS_AI_pm"] * min_jug
                                        reg["Nº SPR"] = ratios["SPR_pm"] * min_jug
                                        reg["SPR >24"] = ratios["SPR_pm"] * min_jug
                                        reg["ACC"] = ratios["ACC_pm"] * min_jug
                                        reg["ACC >3"] = ratios["ACC_pm"] * min_jug
                                        reg["DCC"] = ratios["DCC_pm"] * min_jug
                                        reg["DCC >3"] = ratios["DCC_pm"] * min_jug
                                        reg["VMAX"] = ratios["VMAX"]
                                        reg["V_Max"] = ratios["VMAX"]
                            return registros
                        if f'msg_sync_{idx_real}' in st.session_state:
                            for msg in st.session_state[f'msg_sync_{idx_real}']:
                                if "✅" in msg: st.success(msg)
                                elif "⚠️" in msg: st.warning(msg)
                                elif "❓" in msg: st.info(msg)
                            del st.session_state[f'msg_sync_{idx_real}']

                        t_man, t_exc = st.tabs(["✍️ Edición Manual de Tabla", "📁 Importar desde Excel"])
                        
                        with t_man:
                            st.caption("Modifica la tabla a tu ritmo. Los cálculos internos y el guardado solo se ejecutarán cuando pulses el botón de abajo.")
                            if sesion.get("datos_informe"):
                                df_manual_base = pd.DataFrame(sesion["datos_informe"])
                            else:
                                rows = []
                                for p in st.session_state.plantilla:
                                    rows.append({"JUGADOR": p["JUGADOR"], "POS": p["POS"], "TQR": 0.0, "W_Humor": 0.0, "W_Sueño": 0.0, "W_Fatiga": 0.0, "W_Dolor": 0.0, "W_Estres": 0.0, "RPE": 0.0, "MIN": 0.0, "MIN_GPS": 0.0, "DIS": 0.0, "HID >21": 0.0, "HID >24": 0.0, "SPR >24": 0.0, "SPR >27": 0.0, "V_Med": 0.0, "V_Max": 0.0, "ACC_Max": 0.0, "ACC >2": 0.0, "ACC >3": 0.0, "ACC >4": 0.0, "DCC >2": 0.0, "DCC >3": 0.0, "DCC >4": 0.0, "R_0_7": 0.0, "R_7_14": 0.0, "R_14_21": 0.0, "R_21_24": 0.0, "R_24_27": 0.0, "R_27_30": 0.0, "R_30_45": 0.0})
                                df_manual_base = pd.DataFrame(rows)
                                
                            if "V_Max" not in df_manual_base.columns: df_manual_base["V_Max"] = df_manual_base.get("VMAX", 0.0)
                            if "HID >21" not in df_manual_base.columns: df_manual_base["HID >21"] = df_manual_base.get("DIS AI", 0.0)
                            if "SPR >24" not in df_manual_base.columns: df_manual_base["SPR >24"] = df_manual_base.get("Nº SPR", 0.0)
                            if "ACC >3" not in df_manual_base.columns: df_manual_base["ACC >3"] = df_manual_base.get("ACC", 0.0)
                            if "DCC >3" not in df_manual_base.columns: df_manual_base["DCC >3"] = df_manual_base.get("DCC", 0.0)

                            cols_to_show = ["JUGADOR", "POS", "TQR", "W_Humor", "W_Sueño", "W_Fatiga", "W_Dolor", "W_Estres", "RPE", "MIN", "MIN_GPS", "DIS", "HID >21", "HID >24", "SPR >24", "SPR >27", "V_Med", "V_Max", "ACC_Max", "ACC >2", "ACC >3", "ACC >4", "DCC >2", "DCC >3", "DCC >4", "R_0_7", "R_7_14", "R_14_21", "R_21_24", "R_24_27", "R_27_30", "R_30_45"]
                            for c in cols_to_show:
                                if c not in df_manual_base.columns: df_manual_base[c] = 0.0
                                    
                            with st.form(key=f"form_manual_{idx_real}"):
                                edited_df = st.data_editor(
                                    df_manual_base[cols_to_show],
                                    use_container_width=True,
                                    hide_index=True,
                                    disabled=["JUGADOR", "POS"]
                                )
                                
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    submit_manual = st.form_submit_button("💾 Guardar y Calcular Tabla", type="primary", use_container_width=True)
                                with col_btn2:
                                    del_manual = st.form_submit_button("🗑️ Vaciar Datos de Sesión", use_container_width=True)
                                    
                                if submit_manual:
                                    full_records = []
                                    for idx_row, row in edited_df.iterrows():
                                        suma_well = safe_float(row["W_Humor"]) + safe_float(row["W_Sueño"]) + safe_float(row["W_Fatiga"]) + safe_float(row["W_Dolor"]) + safe_float(row["W_Estres"])
                                        min_ses = safe_float(row["MIN"])
                                        min_gps_val = safe_float(row["MIN_GPS"])
                                        
                                        if min_gps_val > 0 and safe_float(row["DIS"]) > 0:
                                            dis = safe_float(row["DIS"]); dis_ai_21 = safe_float(row["HID >21"]); dis_ai_24 = safe_float(row["HID >24"]); spr_24 = safe_float(row["SPR >24"]); spr_27 = safe_float(row["SPR >27"]); v_med = safe_float(row["V_Med"]); v_max = safe_float(row["V_Max"]); acc_max = safe_float(row["ACC_Max"]); acc_2 = safe_float(row["ACC >2"]); acc_3 = safe_float(row["ACC >3"]); acc_4 = safe_float(row["ACC >4"]); dcc_2 = safe_float(row["DCC >2"]); dcc_3 = safe_float(row["DCC >3"]); dcc_4 = safe_float(row["DCC >4"]); r_0_7 = safe_float(row["R_0_7"]); r_7_14 = safe_float(row["R_7_14"]); r_14_21 = safe_float(row["R_14_21"]); r_21_24 = safe_float(row["R_21_24"]); r_24_27 = safe_float(row["R_24_27"]); r_27_30 = safe_float(row["R_27_30"]); r_30_45 = safe_float(row["R_30_45"])
                                        else:
                                            dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_27 = v_med = v_max = acc_max = acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = r_30_45 = 0.0

                                        ewma_actual = calcular_ewma_historico(st.session_state.sesiones, sesion["fecha"]).get(row["JUGADOR"], {})
                                        ewma_aguda = ewma_actual.get("EWMA AGUDA", min_ses * safe_float(row["RPE"]))
                                        ewma_cronica = ewma_actual.get("EWMA CRÓNICA", ewma_aguda)
                                        ratio_ac = ewma_actual.get("RATIO A/C", 1.0)
                                        
                                        full_records.append({
                                            # ... toda la lista de variables ...
                                        })
                                        
                                    # Imputar GPS automático antes de guardar
                                    full_records = aplicar_imputacion_gps(full_records, sesion, es_partido)
                                    
                                    st.session_state.sesiones[idx_real]['datos_informe'] = full_records
                                    st.session_state.sesiones[idx_real]['informe_generado'] = True
                                    guardar_datos(modulo="sesiones")
                                    st.success("✅ ¡Datos manuales calculados y guardados correctamente!")
                                    st.rerun()
                                    
                                elif del_manual:
                                    st.session_state.sesiones[idx_real]['datos_informe'] = []
                                    st.session_state.sesiones[idx_real]['informe_generado'] = False
                                    guardar_datos(modulo="sesiones")
                                    st.success("✅ Datos de la sesión borrados correctamente.")
                                    st.rerun()

                        with t_exc:
                            st.caption("Asegúrate de haber configurado el nombre de las columnas en la pestaña de Configuración.")
                            col_up1, col_up2, col_up3 = st.columns(3)
                            with col_up1: archivo_well = st.file_uploader("1. Wellness:", type=["xlsx"], key=f"up_w_{idx_real}")
                            with col_up2: archivo_rpe = st.file_uploader("2. RPE:", type=["xlsx"], key=f"up_r_{idx_real}")
                            with col_up3: archivo_gps = st.file_uploader("3. GPS:", type=["xlsx"], key=f"up_g_{idx_real}")
                            
                            if st.button("⚙️ Sincronizar Archivos", type="primary", use_container_width=True):
                                try:
                                    import difflib
                                    df_w_up = pd.read_excel(archivo_well) if archivo_well else pd.DataFrame()
                                    df_r_up = pd.read_excel(archivo_rpe) if archivo_rpe else pd.DataFrame()
                                    df_g_up = pd.read_excel(archivo_gps) if archivo_gps else pd.DataFrame()
                                    
                                    cfg_w = st.session_state.get("config_mapeo", {}).get("wellness", {})
                                    cfg_r = st.session_state.get("config_mapeo", {}).get("rpe", {})
                                    cfg_g = st.session_state.get("config_mapeo", {}).get("gps", {})
                                    
                                    errores_criticos = []
                                    if not df_w_up.empty:
                                        valido, err = validar_columnas_excel(df_w_up, "Wellness", [cfg_w.get("nombre", "Nombre"), cfg_w.get("fecha", "Marca temporal")])
                                        if not valido: errores_criticos.append(err)
                                    if not df_r_up.empty:
                                        valido, err = validar_columnas_excel(df_r_up, "RPE", [cfg_r.get("nombre", "Nombre"), cfg_r.get("fecha", "Marca temporal")])
                                        if not valido: errores_criticos.append(err)
                                    if not df_g_up.empty:
                                        valido, err = validar_columnas_excel(df_g_up, "GPS", [cfg_g.get("nombre", "Player Name"), cfg_g.get("fecha", "Activity Date"), cfg_g.get("dis", "Distance (km)")])
                                        if not valido: errores_criticos.append(err)
                                            
                                    if errores_criticos:
                                        for error_msg in errores_criticos: st.markdown(f"<div style='background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin-bottom: 10px; border-radius: 6px; color: #991b1b;'>{error_msg}</div>", unsafe_allow_html=True)
                                        st.stop() # Bloqueo crítico para impedir contaminación de datos
                                    else:
                                        fecha_sesion_str = pd.to_datetime(sesion['fecha']).strftime('%Y-%m-%d')
                                        def filtrar_fecha_dinamico(df, col_fecha_config):
                                            if df.empty: return df
                                            col_f = next((c for c in df.columns if str(c).strip().lower() == col_fecha_config.strip().lower()), None)
                                            if not col_f: col_f = next((c for c in df.columns if 'marca temporal' in str(c).lower() or 'activity date' in str(c).lower() or 'date' in str(c).lower() or 'fecha' in str(c).lower()), None)
                                            if col_f:
                                                df['FECHA_TEMP'] = pd.to_datetime(df[col_f], errors='coerce').dt.strftime('%Y-%m-%d')
                                                return df[df['FECHA_TEMP'] == fecha_sesion_str].drop(columns=['FECHA_TEMP'])
                                            return df

                                        df_w_up = filtrar_fecha_dinamico(df_w_up, cfg_w.get("fecha", "Marca temporal"))
                                        df_r_up = filtrar_fecha_dinamico(df_r_up, cfg_r.get("fecha", "Marca temporal"))
                                        df_g_up = filtrar_fecha_dinamico(df_g_up, cfg_g.get("fecha", "Activity Date"))

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
                                        col_w_nom = cfg_w.get("nombre", "Nombre")
                                        if not df_w_up.empty and col_w_nom in df_w_up.columns:
                                            df_w_up['JUGADOR_MATCH'] = df_w_up[col_w_nom].apply(emparejar_nombre)
                                            no_encontrados_en_app.update(df_w_up[df_w_up['JUGADOR_MATCH'].isna()][col_w_nom].dropna().tolist())
                                            df_w_up = df_w_up.dropna(subset=['JUGADOR_MATCH'])
                                            faltan_w = [n for n in nombres_plantilla if n not in df_w_up['JUGADOR_MATCH'].tolist()]
                                        elif archivo_well: faltan_w = nombres_plantilla.copy()

                                        faltan_r = []
                                        col_r_nom = cfg_r.get("nombre", "Nombre")
                                        if not df_r_up.empty and col_r_nom in df_r_up.columns:
                                            df_r_up['JUGADOR_MATCH'] = df_r_up[col_r_nom].apply(emparejar_nombre)
                                            no_encontrados_en_app.update(df_r_up[df_r_up['JUGADOR_MATCH'].isna()][col_r_nom].dropna().tolist())
                                            df_r_up = df_r_up.dropna(subset=['JUGADOR_MATCH'])
                                            faltan_r = [n for n in nombres_plantilla if n not in df_r_up['JUGADOR_MATCH'].tolist()]
                                        elif archivo_rpe: faltan_r = nombres_plantilla.copy()

                                        col_g_nom = cfg_g.get("nombre", "Player Name")
                                        if not df_g_up.empty and col_g_nom in df_g_up.columns:
                                            df_g_up['JUGADOR_MATCH'] = df_g_up[col_g_nom].apply(emparejar_nombre)
                                            no_encontrados_en_app.update(df_g_up[df_g_up['JUGADOR_MATCH'].isna()][col_g_nom].dropna().tolist())
                                            df_g_up = df_g_up.dropna(subset=['JUGADOR_MATCH'])

                                        datos_actuales = {d["JUGADOR"]: d for d in sesion.get("datos_informe", [])}
                                        registros_sesion = []
                                        for nombre_final in sorted(nombres_plantilla):
                                            match_p = next((p for p in st.session_state.plantilla if p['JUGADOR'] == nombre_final), None)
                                            pos_jug = match_p['POS'] if match_p else "DEF"

                                            reg = datos_actuales.get(nombre_final, {
                                                "JUGADOR": nombre_final, "POS": pos_jug, "TQR": 0.0, "WELLNESS": 0.0, "W_Humor": 0.0, "W_Sueño": 0.0, "W_Fatiga": 0.0, "W_Dolor": 0.0, "W_Estres": 0.0, "RPE": 0.0, "MIN": 0.0, "MIN_GPS": 0.0, "CARGA": 0.0, "EWMA AGUDA": 0.0, "EWMA CRÓNICA": 0.0, "RATIO A/C": 0.0, "DIS": 0.0, "DIS AI": 0.0, "Nº SPR": 0.0, "ACC": 0.0, "DCC": 0.0, "VMAX": 0.0, "Z1": 0.0, "Z2": 0.0, "Z3": 0.0, "Z4": 0.0, "Z5": 0.0, "Z6": 0.0, "HID >21": 0.0, "HID >24": 0.0, "SPR >24": 0.0, "SPR >27": 0.0, "V_Med": 0.0, "V_Max": 0.0, "ACC_Max": 0.0, "ACC >2": 0.0, "ACC >3": 0.0, "ACC >4": 0.0, "DCC >2": 0.0, "DCC >3": 0.0, "DCC >4": 0.0, "R_0_7": 0.0, "R_7_14": 0.0, "R_14_21": 0.0, "R_21_24": 0.0, "R_24_27": 0.0, "R_27_30": 0.0, "R_30_45": 0.0
                                            })

                                            if not df_r_up.empty and cfg_r:
                                                match_r = df_r_up[df_r_up['JUGADOR_MATCH'] == nombre_final]
                                                if not match_r.empty: 
                                                    reg["RPE"] = safe_float(match_r.iloc[0].get(cfg_r.get("rpe", "RPE"), 0))
                                                    if reg["MIN"] == 0: reg["MIN"] = 90.0

                                            if not df_w_up.empty and cfg_w:
                                                match_w = df_w_up[df_w_up['JUGADOR_MATCH'] == nombre_final]
                                                if not match_w.empty:
                                                    r_w = match_w.iloc[0]
                                                    reg["TQR"] = safe_float(r_w.get(cfg_w.get("tqr", "TQR"), 0))
                                                    reg["W_Fatiga"] = safe_float(r_w.get(cfg_w.get("fatiga", "W_Fatiga"), 0))
                                                    reg["W_Sueño"] = safe_float(r_w.get(cfg_w.get("sueno", "W_Sueño"), 0))
                                                    reg["W_Dolor"] = safe_float(r_w.get(cfg_w.get("dolor", "W_Dolor"), 0))
                                                    reg["W_Estres"] = safe_float(r_w.get(cfg_w.get("estres", "W_Estres"), 0))
                                                    reg["W_Humor"] = safe_float(r_w.get(cfg_w.get("humor", "W_Humor"), 0))
                                                    reg["WELLNESS"] = reg["W_Fatiga"] + reg["W_Sueño"] + reg["W_Dolor"] + reg["W_Estres"] + reg["W_Humor"]

                                            if not df_g_up.empty and cfg_g:
                                                match_g = df_g_up[df_g_up['JUGADOR_MATCH'] == nombre_final]
                                                if not match_g.empty:
                                                    row_g = match_g.iloc[0]
                                                    dis = safe_float(row_g.get(cfg_g.get("dis", "Distance (km)"), 0))
                                                    if dis > 0:
                                                        min_gps_excel = extraer_minutos(str(row_g.get(cfg_g.get("min_gps", "Time Played"), '0')))
                                                        reg["MIN_GPS"] = min_gps_excel if min_gps_excel > 0 else 90.0
                                                        reg["MIN"] = reg["MIN_GPS"]
                                                        reg["DIS"] = dis
                                                        reg["HID >21"] = safe_float(row_g.get(cfg_g.get("hid_21", ""), 0)) * 1000.0
                                                        reg["DIS AI"] = reg["HID >21"]
                                                        reg["HID >24"] = safe_float(row_g.get(cfg_g.get("hid_24", ""), 0)) * 1000.0
                                                        reg["SPR >24"] = safe_float(row_g.get(cfg_g.get("spr_24", ""), 0))
                                                        reg["Nº SPR"] = reg["SPR >24"]
                                                        reg["SPR >27"] = safe_float(row_g.get(cfg_g.get("spr_27", ""), 0))
                                                        reg["V_Med"] = safe_float(row_g.get(cfg_g.get("v_med", ""), 0))
                                                        reg["VMAX"] = safe_float(row_g.get(cfg_g.get("v_max", ""), 0))
                                                        reg["V_Max"] = reg["VMAX"]
                                                        reg["ACC >2"] = safe_float(row_g.get(cfg_g.get("acc_2", ""), 0))
                                                        reg["ACC >3"] = safe_float(row_g.get(cfg_g.get("acc_3", ""), 0))
                                                        reg["ACC"] = reg["ACC >3"]
                                                        reg["ACC >4"] = safe_float(row_g.get(cfg_g.get("acc_4", ""), 0))
                                                        reg["DCC >2"] = safe_float(row_g.get(cfg_g.get("dcc_2", ""), 0))
                                                        reg["DCC >3"] = safe_float(row_g.get(cfg_g.get("dcc_3", ""), 0))
                                                        reg["DCC"] = reg["DCC >3"]
                                                        reg["DCC >4"] = safe_float(row_g.get(cfg_g.get("dcc_4", ""), 0))
                                                        reg["R_0_7"] = safe_float(row_g.get(cfg_g.get("r_0_7", ""), 0)) * 1000.0
                                                        reg["R_7_14"] = safe_float(row_g.get(cfg_g.get("r_7_14", ""), 0)) * 1000.0
                                                        reg["R_14_21"] = safe_float(row_g.get(cfg_g.get("r_14_21", ""), 0)) * 1000.0
                                                        reg["R_21_24"] = safe_float(row_g.get(cfg_g.get("r_21_24", ""), 0)) * 1000.0
                                                        reg["R_24_27"] = safe_float(row_g.get(cfg_g.get("r_24_27", ""), 0)) * 1000.0
                                                        reg["R_27_30"] = safe_float(row_g.get(cfg_g.get("r_27_30", ""), 0)) * 1000.0
                                                        reg["R_30_45"] = safe_float(row_g.get(cfg_g.get("r_30_45", ""), 0)) * 1000.0 
                                                        reg["Z1"] = reg["R_0_7"] + reg["R_7_14"]
                                                        reg["Z2"] = reg["R_14_21"]
                                                        reg["Z3"] = reg["R_21_24"]
                                                        reg["Z4"] = reg["R_24_27"]
                                                        reg["Z5"] = reg["R_27_30"]
                                                        reg["Z6"] = reg["R_30_45"]

                                            reg["CARGA"] = reg["MIN"] * reg["RPE"]
                                            ewma_excel = calcular_ewma_historico(st.session_state.sesiones, sesion["fecha"]).get(nombre_final, {})
                                            reg["EWMA AGUDA"] = ewma_excel.get("EWMA AGUDA", reg["CARGA"])
                                            reg["EWMA CRÓNICA"] = ewma_excel.get("EWMA CRÓNICA", reg["CARGA"])
                                            reg["RATIO A/C"] = ewma_excel.get("RATIO A/C", 1.0)
                                            
                                            registros_sesion.append(reg)
                                            
                                        # Imputar GPS automático antes de guardar
                                        registros_sesion = aplicar_imputacion_gps(registros_sesion, sesion, es_partido)
                                        
                                        st.session_state.sesiones[idx_real]['datos_informe'] = registros_sesion
                                        st.session_state.sesiones[idx_real]['informe_generado'] = True
                                        guardar_datos(modulo="sesiones")
                                        
                                        msgs = [f"✅ Sincronización completada. Se generó la tabla con los {len(nombres_plantilla)} jugadores de tu plantilla."]
                                        if archivo_well and faltan_w: msgs.append(f"⚠️ **Faltan en Wellness:** {', '.join(faltan_w)}")
                                        if archivo_rpe and faltan_r: msgs.append(f"⚠️ **Faltan en RPE:** {', '.join(faltan_r)}")
                                        if no_encontrados_en_app: msgs.append(f"❓ **Están en Excel pero NO en tu App:** {', '.join(no_encontrados_en_app)}")
                                        st.session_state[f'msg_sync_{idx_real}'] = msgs
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Error al procesar: {e}")

                    # ---------------------------------------------------------
                    # HERRAMIENTA 4: LESIONES (FORMULARIO COMPRIMIDO)
                    # ---------------------------------------------------------
                    elif active_view == "les":
                        st.markdown(f"#### 🚑 PARTE MÉDICO | {sesion['fecha']}")
                        if not st.session_state.plantilla:
                            st.warning("No hay jugadores en la plantilla.")
                        else:
                            with st.form(key=f"form_lesion_{idx_real}"):
                                n_plan = [j["JUGADOR"] for j in st.session_state.plantilla]
                                
                                c1, c2, c3, c4 = st.columns(4)
                                les_jugador = c1.selectbox("Jugador Afectado:", n_plan)
                                les_tipo = c2.selectbox("Tipo de Lesión:", ["Muscular", "Tendinosa", "Artículo-ligamentosa", "Fractura", "Otra"])
                                les_zona = c3.selectbox("Zona Afectada:", ["Pie", "Tobillo", "Pierna", "Rodilla", "Muslo", "Cadera - Ingles", "Extremidades Superiores", "Tronco", "Cabeza"])
                                les_lado = c4.selectbox("Lado:", ["Derecha", "Izquierda", "N/A"])
                                
                                c5, c6, c7, c8 = st.columns([1.5, 1, 1, 1])
                                les_lat = c5.selectbox("Lateralidad:", ["Dominante", "No dominante", "Sin lateralidad"])
                                les_contacto = c6.radio("¿Contacto?", ["Sí", "No"], horizontal=True)
                                les_cesped = c7.radio("Superficie:", ["Natural", "Artificial"], horizontal=True)
                                les_recidiva = c8.radio("¿Recidiva?", ["No", "Sí"], horizontal=True)
                                
                                les_comentarios = st.text_input("Comentarios / Mecanismo:")
                                
                                if st.form_submit_button("💾 Registrar Lesión", type="primary"):
                                    nueva_lesion = {"id_sesion": sesion["fecha"], "tipo_sesion": "Partido" if es_partido else "Entrenamiento", "jugador": les_jugador, "tipo": les_tipo, "zona": les_zona, "lado": les_lado, "lateralidad": les_lat, "contacto": les_contacto, "cesped": les_cesped, "recidiva": les_recidiva, "comentarios": les_comentarios, "dias_baja": None, "estado": "Activa", "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                                    st.session_state.lesiones.append(nueva_lesion)
                                    guardar_datos(modulo="lesiones")
                                    st.success(f"¡Parte médico de {les_jugador} guardado!")
                                    st.rerun()

                    # ---------------------------------------------------------
                    # HERRAMIENTA 5: ESTADÍSTICAS DEL PARTIDO
                    # ---------------------------------------------------------
                    elif active_view == "stats" and es_partido:
                        st.markdown(f"#### ⚡ ESTADÍSTICAS DE PARTIDO | vs {sesion.get('rival', 'Rival')} ({sesion['fecha']})")
                        col_g1, col_g2 = st.columns(2)
                        condicion_actual = sesion.get("condicion", "Casa")
                        nueva_condicion = col_g1.selectbox("Condición:", ["Casa", "Fuera"], index=["Casa", "Fuera"].index(condicion_actual), key=f"cond_{idx_real}")
                        goles_f_actual = sesion.get("goles_favor", 0)
                        nuevo_gf = col_g2.number_input("Goles Anotados (Favor del Equipo):", min_value=0, value=int(goles_f_actual or 0), key=f"gf_{idx_real}")
                        
                        sesion["condicion"] = nueva_condicion
                        sesion["goles_favor"] = nuevo_gf

                        st.markdown("##### 📋 Rendimiento de Jugadores Convocados")
                        disp_s = sesion.get("disponibilidad", {})
                        disp_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                        jugadores_convocados = []
                        for p in st.session_state.plantilla:
                            rol = disp_clean.get(limpiar_nombre(p["JUGADOR"]), "No convocado")
                            if rol in ["Titular", "Suplente"]:
                                jugadores_convocados.append({
                                    "JUGADOR": p["JUGADOR"], "POS": p["POS"], "Rol": rol,
                                    **sesion.get("estadisticas_partido", {}).get(p["JUGADOR"], {"Minutos": 90 if rol == "Titular" else 0, "Goles": 0, "Goles Encajados": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0})
                                })
                        
                        invitados_guardados = sesion.get("estadisticas_invitados", [])
                        for inv in invitados_guardados:
                            jugadores_convocados.append({"JUGADOR": inv["JUGADOR"], "POS": inv["POS"], "Rol": inv["Rol"], "Minutos": inv["Minutos"], "Goles": inv["Goles"], "Goles Encajados": inv["Goles Encajados"], "Asistencias": inv["Asistencias"], "Amarillas": inv["Amarillas"], "Rojas": inv["Rojas"]})

                        with st.expander("➕ Añadir jugador del filial / juvenil / invitado"):
                            c_inv1, c_inv2, c_inv3, c_inv4 = st.columns([2, 1, 1, 1])
                            nombre_invitado = c_inv1.text_input("Nombre del Jugador Invitado:", key=f"nombre_inv_{idx_real}")
                            pos_invitado = c_inv2.selectbox("Posición:", ["POR", "DEF", "MED", "ATA"], key=f"pos_inv_{idx_real}")
                            rol_invitado = c_inv3.selectbox("Rol:", ["Suplente", "Titular"], key=f"rol_inv_{idx_real}")
                            min_invitado = c_inv4.number_input("Minutos:", min_value=0, max_value=120, value=45, key=f"min_inv_{idx_real}")
                            if st.button("➕ Incluir en la tabla del partido", key=f"btn_add_inv_{idx_real}"):
                                if nombre_invitado.strip():
                                    if "estadisticas_invitados" not in sesion: sesion["estadisticas_invitados"] = []
                                    sesion["estadisticas_invitados"].append({"JUGADOR": nombre_invitado.strip() + " (Cantera)", "POS": pos_invitado, "Rol": rol_invitado, "Minutos": min_invitado, "Goles": 0, "Goles Encajados": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0})
                                    guardar_datos(modulo="sesiones")
                                    st.success(f"✅ {nombre_invitado} añadido al partido.")
                                    st.rerun()
                                else: st.warning("Escribe un nombre válido.")

                        if not jugadores_convocados:
                            st.warning("⚠️ No hay jugadores convocados. Configura la disponibilidad o añade un jugador invitado arriba.")
                        else:
                            df_stats_base = pd.DataFrame(jugadores_convocados)
                            cols_orden_stats = ["JUGADOR", "POS", "Rol", "Minutos", "Goles", "Goles Encajados", "Asistencias", "Amarillas", "Rojas"]
                            for c in cols_orden_stats:
                                if c not in df_stats_base.columns: df_stats_base[c] = 0
                            
                            with st.form(f"form_stats_{idx_real}"):
                                edited_stats = st.data_editor(df_stats_base[cols_orden_stats], use_container_width=True, hide_index=True, disabled=["JUGADOR", "POS", "Rol"])
                                if st.form_submit_button("💾 Guardar Estadísticas de Partido", type="primary"):
                                    stats_dict, invitados_actualizados, goles_contra_totales = {}, [], 0
                                    nombres_plantilla_oficial = [p["JUGADOR"] for p in st.session_state.plantilla]
                                    for _, r in edited_stats.iterrows():
                                        j_nom = r["JUGADOR"]
                                        g_e = int(safe_float(r["Goles Encajados"]))
                                        goles_contra_totales += g_e
                                        d_jug = {"Minutos": safe_float(r["Minutos"]), "Goles": int(safe_float(r["Goles"])), "Goles Encajados": g_e, "Asistencias": int(safe_float(r["Asistencias"])), "Amarillas": int(safe_float(r["Amarillas"])), "Rojas": int(safe_float(r["Rojas"]))}
                                        if j_nom in nombres_plantilla_oficial: stats_dict[j_nom] = d_jug
                                        else: invitados_actualizados.append({"JUGADOR": j_nom, "POS": r["POS"], "Rol": r["Rol"], **d_jug})
                                    sesion["estadisticas_partido"] = stats_dict
                                    sesion["estadisticas_invitados"] = invitados_actualizados
                                    sesion["goles_contra"] = goles_contra_totales
                                    guardar_datos(modulo="sesiones")
                                    st.success(f"✅ ¡Estadísticas guardadas con éxito! (Goles en contra totales: {goles_contra_totales})")
                                    st.rerun()
with tab_add:
    st.markdown("### ➕ Planificación de Sesiones")
    st.caption("Selecciona la fecha e introduce los datos del evento para registrarlo en el calendario.")
    
    col_add1, col_add2, col_add3 = st.columns([1, 2, 1])
    
    with col_add2:
        with st.container(border=True):
            st.markdown("#### 📅 1. Fecha del Evento")
            dia_clicado = st.date_input("Selecciona una fecha:", date.today())
            fecha_formateada = dia_clicado.strftime("%d-%m-%Y")
            
            sesiones_en_fecha = [s for s in st.session_state.sesiones if s["fecha"] == str(dia_clicado)]
            if sesiones_en_fecha: 
                st.info(f"ℹ️ Ya hay {len(sesiones_en_fecha)} evento(s) el {fecha_formateada}.")
            else:
                st.success(f"✅ Día libre el {fecha_formateada}. Listo para programar.")
                
        with st.container(border=True):
            st.markdown("#### ⚙️ 2. Detalles de la Sesión")
            tipo_nuevo = st.selectbox("Tipo de Evento:", ["Entrenamiento", "Partido Oficial", "Partido Amistoso"])
            
            desc_nuevo = ""
            comp_nuevo = ""
            rival_nuevo = ""
            condicion_nuevo = "Casa"
            ciudad_manual_nuevo = ""
            
            if tipo_nuevo == "Entrenamiento":
                desc_nuevo = st.selectbox("Match Day:", ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"])
            else:
                if tipo_nuevo == "Partido Oficial":
                    comp_nuevo = st.selectbox("Competición:", ["Liga", "Copa"])
                
                col_r1, col_r2 = st.columns(2)
                rival_nuevo = col_r1.text_input("Rival:")
                condicion_nuevo = col_r2.radio("Condición:", ["Casa", "Fuera"], horizontal=True)
                
                if condicion_nuevo == "Fuera":
                    rivales_db = st.session_state.get("rivales_guardados", {})
                    if rival_nuevo and rival_nuevo not in rivales_db:
                        st.info("ℹ️ Rival no guardado en la BBDD.")
                        ciudad_manual_nuevo = st.text_input("Ciudad (Necesario para clima autom.):")
                
            if st.button("💾 Guardar Sesión", use_container_width=True, type="primary"):
                ciudad_objetivo = st.session_state.get("ubicacion_local", "")
                
                if tipo_nuevo != "Entrenamiento" and condicion_nuevo == "Fuera":
                    rival_info = st.session_state.get("rivales_guardados", {}).get(rival_nuevo, {})
                    if isinstance(rival_info, dict) and rival_info.get("ciudad"):
                        ciudad_objetivo = rival_info.get("ciudad")
                    elif ciudad_manual_nuevo:
                        ciudad_objetivo = ciudad_manual_nuevo
                
                clima_data = None
                if ciudad_objetivo:
                    with st.spinner(f"Sincronizando clima para {ciudad_objetivo}..."):
                        from utils.math_helpers import obtener_clima
                        clima_data = obtener_clima(ciudad_objetivo, str(dia_clicado))

                st.session_state.sesiones.append({
                    "fecha": str(dia_clicado), 
                    "tipo": tipo_nuevo, 
                    "descripcion": desc_nuevo,
                    "competicion": comp_nuevo,
                    "rival": rival_nuevo,
                    "condicion": condicion_nuevo,
                    "ciudad_manual": ciudad_manual_nuevo,
                    "clima": clima_data,
                    "disponibilidad": {},
                    "informe_generado": False, 
                    "datos_informe": []
                })
                guardar_datos(modulo="sesiones")
                st.success("¡Evento creado en el calendario!")
                st.rerun()
