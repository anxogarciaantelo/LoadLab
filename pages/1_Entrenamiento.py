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
 
st.subheader(":material/calendar_month: Entrenamiento")

tab_cal, tab_temp, tab_micro, tab_ses, tab_add = st.tabs([
    ":material/calendar_view_month: Calendario", 
    ":material/emoji_events: Temporada", 
    ":material/sync: Microciclos", 
    ":material/list_alt: Sesiones", 
    ":material/add_circle: Añadir Sesión"
])

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
    if c_nav1.button(":material/chevron_left:", use_container_width=True):
        st.session_state.cal_offset -= 1
        st.rerun()
    with c_nav2:
        st.markdown(f"<h4 style='text-align: center; color: #f8fafc; margin-top: 0; margin-bottom: 10px; font-size: 1.15rem; text-transform: uppercase; font-weight: 800; letter-spacing: 1px;'>🗓️ {meses_nombres[month]} {year}</h4>", unsafe_allow_html=True)
    if c_nav3.button(":material/chevron_right:", use_container_width=True):
        st.session_state.cal_offset += 1
        st.rerun()
    
    cal = calendar.monthcalendar(year, month)
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    hoy_str = str(date.today())
    
    # --- CABECERAS DE LOS DÍAS (Limpias y reducidas) ---
    html_cal = "<div style='display: grid; grid-template-columns: 60px repeat(7, 1fr); gap: 8px; text-align: center; margin-bottom: 5px; align-items: end;'>"
    html_cal += "<div></div>" # Espacio vacío sobre la columna de microciclos
    for d in dias_semana:
        html_cal += f"<div style='color: #94a3b8; font-weight: 800; font-size: 0.8rem; text-transform: uppercase; padding-bottom: 6px; border-bottom: 2px solid #1c1f26;'>{d}</div>"
    html_cal += "</div>"
    
    # --- MAPA CRONOLÓGICO DE MICROCICLOS ---
    semanas_unicas_cal = set()
    for s in st.session_state.sesiones:
        semanas_unicas_cal.add(obtener_numero_semana(s["fecha"]))
    mapa_micros_cal = {n_sem: i + 1 for i, n_sem in enumerate(sorted(list(semanas_unicas_cal)))}
    
    # --- FILAS DE SEMANAS (Tarjetas horizontales largas) ---
    for week in cal:
        dia_sem = next((d for d in week if d != 0), None)
        num_sem = obtener_numero_semana(f"{year}-{month:02d}-{dia_sem:02d}") if dia_sem else 0
        micro_relativo = mapa_micros_cal.get(num_sem)
        
        # Tarjeta contenedora de la semana completa
        html_cal += "<div style='background-color: #111318; border: 1px solid #1c1f26; border-radius: 12px; padding: 10px; margin-bottom: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: grid; grid-template-columns: 60px repeat(7, 1fr); gap: 8px;'>"
        
        # Etiqueta del Microciclo (Píldora azul a la izquierda)
        if micro_relativo is not None:
            html_cal += f"<div style='background-color: transparent; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'><span style='font-size: 0.65rem; font-weight: 800; text-transform: uppercase; margin-bottom: 2px; opacity: 0.9;'>Micro</span><span style='font-size: 1.4rem; font-weight: 800; line-height: 1;'>{micro_relativo}</span></div>"
        else:
            html_cal += "<div></div>"

        # Cajas interiores para cada día de la semana
        for day in week:
            if day == 0:
                html_cal += "<div style='padding: 9px; background-color: transparent;'></div>"
            else:
                fecha_str = f"{year}-{month:02d}-{day:02d}"
                es_hoy = "border: 2px solid #C5A059;" if fecha_str == hoy_str else "border: 1px solid #111318;"
                bg_color = "#0b0e14" if fecha_str == hoy_str else "#0b1120"
                
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
                            
                        contenido_extra += f"<div style='background-color: {color_badge}; color: white; font-size: 0.8rem; font-weight: 800; padding: 6px; border-radius: 6px; margin-top: 6px; width: 100%; box-sizing: border-box; line-height: 1.2; box-shadow: 0 2px 4px rgba(0,0,0,0.2); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;' title='{nom} | {sub}'><span style='white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;'>{nom}</span><span style='font-size: 0.65rem; font-weight: 600; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;'>{sub}</span></div>"
                
                html_cal += f"<div style='background-color: {bg_color}; {es_hoy} padding: 10px 5px; border-radius: 8px; min-height: 107px; display: flex; flex-direction: column; align-items: center; transition: transform 0.2s ease;' onmouseover=\"this.style.transform='scale(1.03)'\" onmouseout=\"this.style.transform='scale(1)'\"><span style='color: #f8fafc; font-weight: 800; font-size: 1.15rem; margin-bottom: 4px;'>{day}</span>{contenido_extra}</div>"
        
        html_cal += "</div>" 
        
    st.markdown(html_cal, unsafe_allow_html=True)

with tab_temp:
    st.markdown("### Análisis de la Temporada")
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
                        
                    cols_w = ['W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor']
                    for c in cols_w:
                        if c not in df_sem.columns: df_sem[c] = 0.0
                        
                    df_no_ceros = df_sem.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                    df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE'] + cols_w].mean().reset_index().fillna(0)
                    
                    kpis_temporada.append({
                        "ID": i+1,
                        "Microciclo": nombre_micro,
                        "Wellness": df_jug_mean['WELLNESS'].mean(),
                        "TQR": df_jug_mean['TQR'].mean(),
                        "Fatiga": df_jug_mean['W_Fatiga'].mean(),
                        "Sueño": df_jug_mean['W_Sueño'].mean(),
                        "Dolor": df_jug_mean['W_Dolor'].mean(),
                        "Estrés": df_jug_mean['W_Estres'].mean(),
                        "Humor": df_jug_mean['W_Humor'].mean(),
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
                st.markdown(f"#### Promedios de la Temporada (Tendencia vs {ultimo_m['Microciclo']})")
                cols_kpi = st.columns(10)
                
                from utils.math_helpers import render_kpi_elite
                with cols_kpi[0]: render_kpi_elite("Wellness", f"{medias_temp['Wellness']:.1f}", tendencia=calc_tendencia_temporada('Wellness'))
                with cols_kpi[1]: render_kpi_elite("TQR", f"{medias_temp['TQR']:.1f}", tendencia=calc_tendencia_temporada('TQR'))
                with cols_kpi[2]: render_kpi_elite("RPE", f"{medias_temp['RPE']:.1f}", tendencia=calc_tendencia_temporada('RPE'))
                with cols_kpi[3]: render_kpi_elite("Minutos", f"{medias_temp['Minutos']:.0f}", tendencia=calc_tendencia_temporada('Minutos'))
                with cols_kpi[4]: render_kpi_elite("Carga", f"{medias_temp['Carga']:.0f}", tendencia=calc_tendencia_temporada('Carga'))
                with cols_kpi[5]: render_kpi_elite("DISTANCIA", f"{medias_temp['DIS']:.1f}", tendencia=calc_tendencia_temporada('DIS'))
                with cols_kpi[6]: render_kpi_elite("HSR", f"{medias_temp['HSR']:.0f}", tendencia=calc_tendencia_temporada('HSR'))
                with cols_kpi[7]: render_kpi_elite("Sprints", f"{medias_temp['Sprints']:.1f}", tendencia=calc_tendencia_temporada('Sprints'))
                with cols_kpi[8]: render_kpi_elite("ACC", f"{medias_temp['ACC']:.0f}", tendencia=calc_tendencia_temporada('ACC'))
                with cols_kpi[9]: render_kpi_elite("DCC", f"{medias_temp['DCC']:.0f}", tendencia=calc_tendencia_temporada('DCC'))
                
                st.markdown("---")
                
                # --- GRÁFICOS SUPERIORES Y MEJORADOS ---
                st.markdown("#### :material/psychology: Evolución de Bienestar y Recuperación")
                cg_b1, cg_b2 = st.columns(2)
                
                with cg_b1:
                    fig_tqr = px.bar(df_temporada, x='Microciclo', y='TQR', color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], title="Calidad de Recuperación (TQR)")
                    fig_tqr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_tqr.update_yaxes(range=[1, 10])
                    st.plotly_chart(fig_tqr, use_container_width=True)
                    
                with cg_b2:
                    fig_well = go.Figure()
                    colores_w = px.colors.qualitative.Set2
                    factores = ['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor']
                    for i, factor in enumerate(factores):
                        fig_well.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada[factor], name=factor, marker_color=colores_w[i]))
                    fig_well.update_layout(title="Evolución Wellness (Factores)", barmode='stack', yaxis_title="Puntos", yaxis_range=[0, 35], hovermode="x unified", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)")
                    fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)")
                    st.plotly_chart(fig_well, use_container_width=True)
                
                st.markdown("#### :material/local_fire_department: Carga Interna y Externa")
                cg1, cg2, cg3 = st.columns(3)
                with cg1:
                    fig_carga = go.Figure()
                    fig_carga.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada['Carga'], name="Carga (UA)", marker_color="#C5A059"))
                    media_carga = df_temporada['Carga'].mean()
                    fig_carga.add_hline(y=media_carga, line_dash="dash", line_color="#f59e0b", annotation_text=f"Media Acumulada: {media_carga:.0f} UA")
                    fig_carga.update_layout(title="Carga Interna", yaxis_title="UA", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_carga, use_container_width=True)
                with cg2:
                    fig_ext = go.Figure()
                    fig_ext.add_trace(go.Bar(x=df_temporada['Microciclo'], y=df_temporada['DIS'], name="Volumen (km)", marker_color="rgba(197, 160, 89, 0.6)", yaxis="y1"))
                    fig_ext.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['HSR'], name="HSR (>21km/h)", mode="lines+markers", line=dict(color="#f59e0b", width=3), yaxis="y2"))
                    fig_ext.update_layout(title="Volumen vs HSR", yaxis=dict(title="Distancia (km)"), yaxis2=dict(title="HSR (m)", overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_ext, use_container_width=True)
                with cg3:
                    fig_mec = go.Figure()
                    fig_mec.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['ACC'], name="Aceleraciones", mode="lines+markers", line=dict(color="#10b981", width=2)))
                    fig_mec.add_trace(go.Scatter(x=df_temporada['Microciclo'], y=df_temporada['DCC'], name="Deceleraciones", mode="lines+markers", line=dict(color="#ef4444", width=2)))
                    fig_mec.update_layout(title="Carga Mecánica", yaxis_title="Cantidad", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_mec, use_container_width=True)

                st.markdown("---")
                
                # --- TABLA INTERACTIVA (FILTRABLE Y ORDENABLE) ---
                st.markdown("#### :material/list_alt: Base de Datos de Microciclos")
                st.caption("Puedes clickar en el nombre de cualquier columna para ordenar los datos de mayor a menor, o usar la lupa para buscar.")
                
                df_temporada_show = df_temporada.sort_values("ID", ascending=False).drop(columns=["ID"])
                # Excluir las sub-columnas de Wellness para no saturar la vista
                cols_mostrar = [c for c in df_temporada_show.columns if c not in ['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor']]
                
                estilo_temp = (df_temporada_show[cols_mostrar].style.format(precision=1)
                    .background_gradient(subset=['Wellness'], cmap='Reds', vmin=5, vmax=35)
                    .background_gradient(subset=['TQR'], cmap='RdYlGn', vmin=1, vmax=10)
                    .background_gradient(subset=['RPE'], cmap='Reds', vmin=1, vmax=10)
                    .background_gradient(subset=['Minutos', 'Carga', 'DIS', 'HSR', 'Sprints', 'ACC', 'DCC'], cmap='Blues'))
                
                st.dataframe(estilo_temp, use_container_width=True, hide_index=True)

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
                etiqueta = f"Microciclo {r_m['Micro_Num']} | Semana del {r_m['ini']} al {r_m['fin']}"
                dict_micros[etiqueta] = r_m
            
            st.markdown("### :material/sync: Análisis de Microciclos")
            
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
                st.markdown(f"#### :material/track_changes: Resumen Acumulado del Microciclo")
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
                st.markdown("#### :material/list_alt: Resumen por Día")
                if not df_diario.empty:
                    estilo_diario = (df_diario.style.hide(axis="index").format(precision=2)
                        .background_gradient(subset=['WELLNESS'], cmap='Reds', vmin=5, vmax=35)
                        .background_gradient(subset=['TQR'], cmap='RdYlGn', vmin=1, vmax=10)
                        .background_gradient(subset=['RPE'], cmap='Reds', vmin=1, vmax=10)
                        .background_gradient(subset=['MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'], cmap='Blues'))
                    mostrar_tabla_moderna(estilo_diario)

                st.markdown("---")
                st.markdown("#### :material/psychology: Bienestar")
                cg_b1, cg_b2 = st.columns(2)
                with cg_b1:
                    df_tqr_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                    fig_tqr = px.bar(df_tqr_plot, x='DIA', y='TQR', color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], title="Calidad de Recuperación (TQR)")
                    fig_tqr.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_tqr.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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
                    
                    fig_well.update_layout(title="Evolución Wellness Diario", barmode='stack', yaxis_title="Puntos", legend_title_text="Factor", yaxis_range=[0, 35], hovermode="x unified", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_well.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                    fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                    st.plotly_chart(fig_well, use_container_width=True, key=f"micro_well_{num_sem}_{idx_real}")

                st.markdown("---")
                st.markdown("#### :material/local_fire_department: Carga Interna")
                cg_i1, cg_i2, cg_i3 = st.columns(3)
                with cg_i1:
                    fig_min = px.bar(df_diario, x='DIA', y='MIN', title="Evolución Minutos")
                    fig_min.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_min, use_container_width=True, key=f"micro_min_{num_sem}_{idx_real}")
                with cg_i2:
                    df_rpe_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                    fig_rpe = px.bar(df_rpe_plot, x='DIA', y='RPE', title="Evolución RPE", color='RPE', color_continuous_scale="Reds", range_color=[0, 10])
                    fig_rpe.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_rpe.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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
                    fig_carga.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
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
                st.markdown("#### :material/directions_run: Carga Externa (Solo datos GPS > 0m)")
                
                df_diario_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index().fillna(0)
                
                cg_e1, cg_e2, cg_e3 = st.columns(3)
                with cg_e1:
                    fig_accdcc = go.Figure()
                    fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['ACC'], mode='lines+markers', name='ACC (>3)', line=dict(color='blue')))
                    fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['DCC'], mode='lines+markers', name='DCC (>3)', line=dict(color='red')))
                    fig_accdcc.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_accdcc.update_layout(title="Evolución ACC vs DCC", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_accdcc, use_container_width=True, key=f"micro_accdcc_{num_sem}_{idx_real}")
                with cg_e2:
                    fig_dis = px.bar(df_diario_plot, x='DIA', y='DIS', title="Evolución DIS (km)", color_discrete_sequence=['#00b4d8'])
                    fig_dis.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_dis.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_dis, use_container_width=True, key=f"micro_dis_{num_sem}_{idx_real}")
                with cg_e3:
                    fig_disai = px.bar(df_diario_plot, x='DIA', y='DIS AI', title="Evolución HSR (>21 km/h)", color_discrete_sequence=['#f50057'])
                    fig_disai.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                    fig_disai.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_disai, use_container_width=True, key=f"micro_disai_{num_sem}_{idx_real}")

                st.markdown("---")
                st.markdown("#### :material/person: Resumen Semanal por Jugador")
                
                df_jug_sum_int = df_filtrado.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
                df_filtrado_gps = df_filtrado[df_filtrado['DIS'] > 0]
                df_jug_sum_ext = df_filtrado_gps.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].sum().reset_index() if not df_filtrado_gps.empty else pd.DataFrame(columns=['JUGADOR', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                
                df_jug_sum = pd.merge(df_jug_sum_int, df_jug_sum_ext, on='JUGADOR', how='left').fillna(0)
                
                # --- MÚLTIPLOS DE PARTIDO Y RATIO DCC/ACC ---
                df_historico_partidos = st.session_state.df_master_informes[(st.session_state.df_master_informes['TIPO_SESION'].str.contains("Partido", na=False)) & (st.session_state.df_master_informes['DIS'] > 0)].copy()
                medias_indiv_partido = {}
                if not df_historico_partidos.empty:
                    df_historico_partidos['MIN_REAL'] = np.where(df_historico_partidos.get('MIN_GPS', df_historico_partidos['MIN']) > 0, df_historico_partidos.get('MIN_GPS', df_historico_partidos['MIN']), df_historico_partidos['MIN'])
                    df_sum_indiv = df_historico_partidos.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'MIN_REAL']].sum()
                    for j_nom, j_row in df_sum_indiv.iterrows():
                        m_jug = j_row['MIN_REAL']
                        if m_jug > 0:
                            medias_indiv_partido[j_nom] = {
                                'DIS': (j_row['DIS'] / m_jug) * 90,
                                'HSR': (j_row['DIS AI'] / m_jug) * 90,
                                'MEC': ((j_row['ACC'] + j_row['DCC']) / m_jug) * 90
                            }

                def calc_xmatch(row, metrica_val, metrica_key):
                    ref = medias_indiv_partido.get(row['JUGADOR'], {}).get(metrica_key, 0)
                    return (metrica_val / ref) if ref > 0 else 0

                df_jug_sum['xPartido DIS'] = df_jug_sum.apply(lambda r: calc_xmatch(r, r['DIS'], 'DIS'), axis=1)
                df_jug_sum['xPartido HSR'] = df_jug_sum.apply(lambda r: calc_xmatch(r, r['DIS AI'], 'HSR'), axis=1)
                df_jug_sum['xPartido MEC'] = df_jug_sum.apply(lambda r: calc_xmatch(r, r['ACC'] + r['DCC'], 'MEC'), axis=1)
                df_jug_sum['DCC:ACC'] = np.where(df_jug_sum['ACC'] > 0, df_jug_sum['DCC'] / df_jug_sum['ACC'], 0)

                # --- VACUNA DE VELOCIDAD ---
                df_master_vac = st.session_state.df_master_informes
                vmax_hist_dict = df_master_vac.groupby('JUGADOR')['VMAX'].max().to_dict() if 'VMAX' in df_master_vac.columns else {}
                
                def dias_sin_vmax(jug):
                    if vmax_hist_dict.get(jug, 0) > 25.0:
                        df_picos = df_master_vac[(df_master_vac['JUGADOR'] == jug) & (df_master_vac['FECHA'] <= df_filtrado['FECHA'].max()) & (df_master_vac['VMAX'] >= vmax_hist_dict[jug] * 0.9)]
                        if not df_picos.empty:
                            ult_fecha = pd.to_datetime(df_picos['FECHA'].max()).date()
                            fecha_micro = pd.to_datetime(df_filtrado['FECHA'].max()).date()
                            return (fecha_micro - ult_fecha).days
                    return 0
                
                df_jug_sum['Días >90% VMax'] = df_jug_sum['JUGADOR'].apply(dias_sin_vmax)
                
                df_no_ceros = df_filtrado.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE']].mean().reset_index().fillna(0)
                df_indiv = df_jug_sum.merge(df_jug_mean, on='JUGADOR')
                
                df_info_extra = df_filtrado[['JUGADOR', 'POS', 'ROL']].drop_duplicates()
                df_indiv = df_indiv.merge(df_info_extra, on='JUGADOR')
                cols_ordenadas = ['JUGADOR', 'POS', 'ROL', 'MIN', 'WELLNESS', 'RPE', 'DIS', 'xPartido DIS', 'DIS AI', 'xPartido HSR', 'DCC:ACC', 'xPartido MEC', 'Días >90% VMax']
                df_indiv = df_indiv[cols_ordenadas]
                
                estilo_indiv = (df_indiv.style.format(precision=1)
                    .format({"xPartido DIS": "{:.1f}x", "xPartido HSR": "{:.1f}x", "xPartido MEC": "{:.1f}x", "DCC:ACC": "{:.2f}"})
                    .background_gradient(subset=['WELLNESS'], cmap='Reds', vmin=5, vmax=35)
                    .background_gradient(subset=['RPE'], cmap='Reds', vmin=1, vmax=10)
                    .background_gradient(subset=['MIN', 'DIS', 'DIS AI'], cmap='Blues')
                    .map(lambda x: "color: #ef4444; font-weight: bold;" if isinstance(x, (int, float)) and x > 1.3 else "", subset=['DCC:ACC'])
                    .map(lambda x: "background-color: #ef4444; color: white; font-weight: bold;" if isinstance(x, (int, float)) and x > 8 else "", subset=['Días >90% VMax']))
                
                st.dataframe(estilo_indiv, use_container_width=True, hide_index=True)
                
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
                    if st.button(":material/settings: Generar PDF del Microciclo", key=f"btn_prepara_pdf_{num_sem}_{idx_real}"):
                        with st.spinner("Procesando gráficos y PDF (esto puede tardar unos segundos)..."):
                            st.session_state[pdf_key] = generar_pdf_microciclo(nombre_etiqueta, df_diario, df_indiv, kpis_micro, diccionario_figuras_micro)
                        st.rerun()
                else:
                    col_pdf1, col_pdf2 = st.columns(2)
                    with col_pdf1:
                        st.download_button(
                            label=":material/download: Descargar PDF",
                            data=st.session_state[pdf_key],
                            file_name=f"Microciclo_{num_sem}.pdf",
                            mime="application/pdf",
                            key=f"btn_descarga_pdf_{num_sem}_{idx_real}"
                        )
                    with col_pdf2:
                        if st.button(":material/delete: Descartar PDF", key=f"btn_borrar_pdf_ses_{idx_real}", use_container_width=True):
                            del st.session_state[pdf_key]
                            st.rerun()

with tab_ses:
    # --- CSS ESPECÍFICO LIGERO PARA BOTONES ---
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] button {
        min-height: 48px !important;
        padding: 0 !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    div[data-testid="stHorizontalBlock"] button p {
        font-size: 1.5rem !important; 
        margin: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.sesiones:
        render_estado_vacio(
            icono=":material/calendar_month:", 
            titulo="Sin sesiones registradas", 
            descripcion="Aún no has planificado ningún entrenamiento o partido. LoadLab necesita este calendario para mapear la fatiga del equipo.",
            accion_sugerida="Ve a la pestaña ':material/add_circle: Añadir Sesión' para generar tu primer evento."
        )
    else:
        if "ses_activa_idx" not in st.session_state:
            st.session_state.ses_activa_idx = None
        if "ses_activa_view" not in st.session_state:
            st.session_state.ses_activa_view = None

        def toggle_view(target_idx, target_view):
            st.session_state.ses_activa_idx = target_idx
            st.session_state.ses_activa_view = target_view

        active_idx = st.session_state.ses_activa_idx
        active_view = st.session_state.ses_activa_view

        # =======================================================
        # VISTA 1: LISTADO DE MICROCICLOS Y SESIONES (CALENDARIO COMPRIMIDO)
        # =======================================================
        if active_idx is None:
            micros_dict = {}
            semanas_unicas = set()
            for s in st.session_state.sesiones:
                num_sem = obtener_numero_semana(s["fecha"])
                semanas_unicas.add(num_sem)
                if num_sem not in micros_dict:
                    micros_dict[num_sem] = []
                micros_dict[num_sem].append(s)
                
            mapa_micros = {num_sem: i + 1 for i, num_sem in enumerate(sorted(list(semanas_unicas)))}
            micros_sorted = sorted(micros_dict.keys(), reverse=True)

            # Agrupar en filas de 2 microciclos
            for i in range(0, len(micros_sorted), 2):
                micros_chunk = micros_sorted[i:i+2]
                cols_micro = st.columns(len(micros_chunk))
                
                for j, num_sem in enumerate(micros_chunk):
                    with cols_micro[j]:
                        sesiones_sem = sorted(micros_dict[num_sem], key=lambda x: x["fecha"], reverse=True)
                        _, _, lunes, domingo = obtener_rango_fechas_semana(sesiones_sem[0]["fecha"])
                        micro_relativo = mapa_micros[num_sem]
                        
                        # --- GENERADOR DEL MINI-CALENDARIO SEMANAL ---
                        html_mini_cal = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-top: 8px;'>"
                        letras_semana = ["L", "M", "X", "J", "V", "S", "D"]
                        for d_offset in range(7):
                            dia_actual = lunes + timedelta(days=d_offset)
                            dia_str = dia_actual.strftime("%Y-%m-%d")
                            ses_dia = next((s for s in sesiones_sem if s["fecha"] == dia_str), None)
                            
                            if ses_dia:
                                color_ind = "#dc2626" if "Partido" in ses_dia["tipo"] else "#10b981"
                                color_text = "#f8fafc"
                            else:
                                color_ind = "transparent"
                                color_text = "#475569"
                                
                            html_mini_cal += f"<div style='background-color: #0b0e14; border-radius: 4px; padding: 3px 0; border-bottom: 3px solid {color_ind}; display: flex; flex-direction: column; align-items: center;'><span style='color: #64748b; font-size: 0.55rem; font-weight: 800; line-height: 1;'>{letras_semana[d_offset]}</span><span style='color: {color_text}; font-size: 0.8rem; font-weight: 800; line-height: 1.2;'>{dia_actual.day}</span></div>"
                        html_mini_cal += "</div>"
                        
                        st.markdown(f"""
                        <div style='background-color: #111318; padding: 8px 12px; border-radius: 6px; border-top: 3px solid #C5A059; margin-top: 15px; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); text-align: center;'>
                            <h4 style='margin: 0; color: #f8fafc; font-weight: 800; font-size: 0.95rem; text-transform: uppercase;'> Micro {micro_relativo} <span style='font-size: 0.75rem; color: #94a3b8; font-weight: 700;'>({lunes.strftime('%d/%m')} - {domingo.strftime('%d/%m')})</span></h4>
                            {html_mini_cal}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        for sesion in sesiones_sem:
                            idx_real = st.session_state.sesiones.index(sesion)
                            es_partido = "Partido" in sesion['tipo']
                            color_borde = "#dc2626" if es_partido else "#10b981"
                            
                            f_dt = datetime.strptime(sesion["fecha"], "%Y-%m-%d")
                            f_str = f"{f_dt.strftime('%d/%m')}"
                            
                            nom_dyn = sesion.get("nombre_dinamico", "")
                            num = ''.join(filter(str.isdigit, nom_dyn))
                            
                            if es_partido: 
                                sub = sesion.get('rival', 'Rival')
                                prefix = "J" if "Jornada" in nom_dyn else ("R" if "Ronda" in nom_dyn else ("A" if "Amistoso" in nom_dyn else "P"))
                                tipo_str = f"{prefix}{num} - {f_str}"
                            else: 
                                sub = sesion.get('descripcion', 'TD')
                                tipo_str = f"S{num} - {f_str}"
                                
                            # 6 columnas estrictas para igualar anchuras en entrenos y partidos. 
                            # La tarjeta ocupa un ratio de 3.2 frente al 1 de los botones (ajuste milimétrico)
                            col_card, c_b1, c_b2, c_b3, c_b4, c_b5 = st.columns([3.2, 1, 1, 1, 1, 1])
                            
                            with col_card:
                                st.markdown(f"""
                                <div style='background-color: #0b0e14; border: 1px solid #1c1f26; border-left: 3px solid {color_borde}; border-radius: 6px; padding: 4px 8px; height: 48px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.15); margin-bottom: 8px;'>
                                    <strong style='color: #f8fafc; font-size: 0.9rem; line-height: 1;'>{tipo_str}</strong>
                                    <span style='color: #94a3b8; font-size: 0.7rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;'>{sub}</span>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            if c_b1.button(":material/local_hospital:", key=f"bd_{idx_real}", help="Disponibilidad", use_container_width=True): toggle_view(idx_real, "disp"); st.rerun()
                            if c_b2.button(":material/bar_chart:", key=f"bi_{idx_real}", help="Informe", use_container_width=True): toggle_view(idx_real, "inf"); st.rerun()
                            if c_b3.button(":material/folder_open:", key=f"bc_{idx_real}", help="Cargar Datos", use_container_width=True): toggle_view(idx_real, "datos"); st.rerun()
                            if c_b4.button(":material/emergency:", key=f"bl_{idx_real}", help="Lesión", use_container_width=True): toggle_view(idx_real, "les"); st.rerun()
                            if es_partido:
                                if c_b5.button(":material/bolt:", key=f"bs_{idx_real}", help="Stats Partido", use_container_width=True): toggle_view(idx_real, "stats"); st.rerun()

        # =======================================================
        # VISTA 2: PANTALLA COMPLETA PARA HERRAMIENTAS (ROUTER)
        # =======================================================
        else:
            sesion = st.session_state.sesiones[active_idx]
            idx_real = active_idx
            es_partido = "Partido" in sesion['tipo']
            
            # Barra superior de navegación nativa
            col_back, col_title = st.columns([1, 5])
            with col_back:
                if st.button(":material/arrow_back: Volver", use_container_width=True):
                    toggle_view(None, None)
                    st.rerun()
            with col_title:
                nom_h = sesion.get("nombre_dinamico", sesion["tipo"])
                sub_h = sesion.get('rival', 'Rival') if es_partido else sesion.get('descripcion', 'TD')
                st.markdown(f"<h4 style='margin-top: 5px; color: #f8fafc;'>Gestión: {nom_h} ({sub_h}) | {sesion['fecha']}</h4>", unsafe_allow_html=True)

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
                    opciones_disp = ["Recuperación Post-Partido", "Lesionado", "Readaptación", "Enfermo", "Falta", "Selección", "No disponible"]
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

                st.info(f":material/lightbulb: Por defecto, todos los jugadores de la plantilla que no añadas abajo se marcarán automáticamente como **{default_disp}**.")
                
                with st.form(key=f"form_disp_{idx_real}"):
                    selecciones = {}
                    
                    # RENDERIZAR SELECTORES EN UNA SOLA FILA HORIZONTAL
                    cols_disp = st.columns(len(opciones_disp))
                    for i, est in enumerate(opciones_disp):
                        with cols_disp[i]:
                            selecciones[est] = st.multiselect(f"{est}", jugs_plantilla, default=jugadores_por_estado[est])
                            
                    if st.form_submit_button(":material/save: Guardar Disponibilidad", type="primary", use_container_width=True):
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
                        
                        # NUEVO: Recalcular imputación al cambiar la disponibilidad
                        if st.session_state.sesiones[idx_real].get("informe_generado") and st.session_state.sesiones[idx_real].get("datos_informe"):
                            from utils.math_helpers import aplicar_imputacion_gps_global
                            st.session_state.sesiones[idx_real]["datos_informe"] = aplicar_imputacion_gps_global(st.session_state.sesiones[idx_real]["datos_informe"], st.session_state.sesiones[idx_real], st.session_state.plantilla)
                            
                        guardar_datos(modulo="sesiones")
                        st.success("Disponibilidad guardada y datos GPS re-imputados correctamente.")
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
                    cols_ewma = [c for c in ['EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C', 'RATIO A/C HSR', 'RATIO A/C ACC', 'EWMA AGUDA HSR'] if c in df_master_sesion.columns]
                    dic_ewma = df_master_sesion.set_index('JUGADOR')[cols_ewma].to_dict('index') if not df_master_sesion.empty else {}
                    
                    df_informe['EWMA AGUDA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA AGUDA', 0.0))
                    df_informe['EWMA CRÓNICA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA CRÓNICA', 0.0))
                    df_informe['RATIO A/C'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C', 1.0))
                    df_informe['RATIO A/C HSR'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C HSR', 1.0))
                    df_informe['RATIO A/C ACC'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C ACC', 1.0))

                    col_filt1, col_filt2 = st.columns([1, 2])
                    with col_filt1:
                        filtro_pos = st.multiselect("Posición:", ["POR", "DEF", "MED", "ATA"], default=["POR", "DEF", "MED", "ATA"], key=f"rp_{idx_real}")
                        if filtro_pos: df_informe = df_informe[df_informe["POS"].isin(filtro_pos)]
                    with col_filt2:
                        opcs_est = ["Titular", "Suplente", "No convocado", "Lesionado", "Enfermo", "Selección", "No disponible"] if es_partido else ["Disponible", "Recuperación Post-Partido", "Readaptación", "Lesionado", "Enfermo", "Falta", "Selección", "No disponible"]
                        def_est = ["Titular", "Suplente"] if es_partido else ["Disponible", "Recuperación Post-Partido"]
                        def_est = [e for e in def_est if e in opcs_est]
                        filtro_est = st.multiselect("Disponibilidad:", opcs_est, default=def_est, key=f"re_{idx_real}")
                        if filtro_est: df_informe = df_informe[df_informe["ESTADO"].isin(filtro_est)]

                    estados_validos_medias = ["Disponible", "Titular", "Suplente", "Recuperación Post-Partido", "Readaptación"]
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

                        dict_zscore = calcular_zscore_wellness(st.session_state.df_master_informes, sesion["fecha"])
                        dict_zscore_efi = calcular_zscores_eficiencia(st.session_state.df_master_informes, sesion["fecha"])
                        alertas_jugadores = {}
                        activos = df_informe[df_informe['ESTADO'].isin(["Disponible", "Titular", "Suplente"])]

                        for _, row in activos.iterrows():
                            jug = row['JUGADOR']
                            alertas_jugadores[jug] = {'recuperacion': [], 'carga': [], 'total': 0}
                            
                            tqr, well = safe_float(row.get('TQR')), safe_float(row.get('WELLNESS'))
                            w_dolor, w_fatiga = safe_float(row.get('W_Dolor')), safe_float(row.get('W_Fatiga'))
                            
                            st_j = dict_zscore.get(jug, {'media': 0, 'std': 1.0, 'dolor_media': 0, 'dolor_std': 0.5, 'fatiga_media': 0, 'fatiga_std': 0.5})
                            z_well = (well - st_j['media']) / st_j['std'] if st_j['std'] > 0 else 0
                            z_dolor = (w_dolor - st_j['dolor_media']) / st_j['dolor_std'] if st_j['dolor_std'] > 0 else 0
                            z_fatiga = (w_fatiga - st_j['fatiga_media']) / st_j['fatiga_std'] if st_j['fatiga_std'] > 0 else 0

                            # --- 1. ALERTAS DE READINESS CRUZADAS (Filtrado de Falsos Positivos) ---
                            
                            # A) Riesgo Estructural Directo (Daño Muscular aislado)
                            if w_dolor > 0 and z_dolor >= 1.5:
                                alertas_jugadores[jug]['recuperacion'].append(f"🔴 **Daño Muscular:** Dolor Anormal (Z: +{z_dolor:.1f})"); alertas_jugadores[jug]['total'] += 1
                            elif w_dolor > 0 and z_dolor >= 1.0:
                                alertas_jugadores[jug]['recuperacion'].append(f"🟡 **Sobrecarga Tisular:** Dolor elevado (Z: +{z_dolor:.1f})"); alertas_jugadores[jug]['total'] += 1
                                
                            # B) Fatiga Sistémica Integrada (Cruza TQR con Percepción Wellness)
                            if tqr > 0 and well > 0:
                                if tqr <= 3 and z_well >= 1.0:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 **Fatiga Sistémica:** TQR {tqr:.0f}/10 y Wellness Z: +{z_well:.1f}"); alertas_jugadores[jug]['total'] += 1
                                elif tqr <= 4 and z_fatiga >= 1.5:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 **Fatiga Muscular:** TQR {tqr:.0f}/10 y Fatiga Z: +{z_fatiga:.1f}"); alertas_jugadores[jug]['total'] += 1
                                elif (tqr <= 4 and z_well < 1.0) or (tqr > 4 and z_well >= 1.5):
                                    alertas_jugadores[jug]['recuperacion'].append(f"🟡 **Readiness Desajustado:** Discordancia TQR/Wellness"); alertas_jugadores[jug]['total'] += 1

                            # --- 2. ALERTAS DE CARGA Y RIESGO MECÁNICO ---
                            
                            ratio_ac = safe_float(row.get('RATIO A/C', 1.0))
                            carga_aguda = safe_float(row.get('EWMA AGUDA', 0.0))
                            ratio_hsr = safe_float(row.get('RATIO A/C HSR', 1.0))
                            ratio_acc = safe_float(row.get('RATIO A/C ACC', 1.0))
                            
                            # A) Carga Interna (Protegida por volumen mínimo para no saltar tras vacaciones)
                            if carga_aguda > 1500:
                                if ratio_ac >= 1.5:
                                    alertas_jugadores[jug]['carga'].append(f"🔴 **Spike Carga:** A/C {ratio_ac:.2f} ({carga_aguda:.0f} UA)"); alertas_jugadores[jug]['total'] += 1
                                elif ratio_ac <= 0.8:
                                    alertas_jugadores[jug]['carga'].append(f"🟡 **Desentrenamiento:** A/C {ratio_ac:.2f}"); alertas_jugadores[jug]['total'] += 1
                                    
                            # B) Carga Externa (Tejido conectivo y muscular)
                            if ratio_hsr >= 1.5:
                                alertas_jugadores[jug]['carga'].append(f"🔴 **Spike HSR:** A/C {ratio_hsr:.2f}"); alertas_jugadores[jug]['total'] += 1
                            if ratio_acc >= 1.5:
                                alertas_jugadores[jug]['carga'].append(f"🔴 **Spike Tensión (ACC):** A/C {ratio_acc:.2f}"); alertas_jugadores[jug]['total'] += 1

                            # --- CÁLCULO DE EFICIENCIA (AISLADO POR MD) ---
                            sesion_contexto = sesion.get('descripcion', 'TD') if not es_partido else "Partido"
                            df_hist_jug_md = df_master_hist[(df_master_hist['JUGADOR'] == jug) & (df_master_hist['FECHA'] < sesion["fecha"])].copy()
                            
                            if not es_partido:
                                df_hist_jug_md = df_hist_jug_md[(df_hist_jug_md['TIPO_SESION'] == "Entrenamiento") & (df_hist_jug_md['MD'] == sesion_contexto)]
                            else:
                                df_hist_jug_md = df_hist_jug_md[df_hist_jug_md['TIPO_SESION'].str.contains("Partido", na=False)]
                                
                            efi_cardio, efi_neuro = 0, 0
                            min_sesion = safe_float(row.get('MIN', 0.0))
                            dis_sesion = safe_float(row.get('DIS', 0.0))
                            rpe_sesion = safe_float(row.get('RPE', 0.0))
                            
                            if min_sesion > 0 and dis_sesion > 0:
                                m_min_actual = (dis_sesion * 1000) / min_sesion
                                mec_total_actual = safe_float(row.get('ACC', 0)) + safe_float(row.get('DCC', 0)) + safe_float(row.get('Nº SPR', 0))
                                
                                if m_min_actual > 0: efi_cardio = rpe_sesion / m_min_actual
                                if mec_total_actual > 0: efi_neuro = rpe_sesion / mec_total_actual
                                
                            if not df_hist_jug_md.empty and (efi_cardio > 0 or efi_neuro > 0):
                                df_hist_jug_md['m_min_h'] = np.where(df_hist_jug_md['MIN'] > 0, (df_hist_jug_md['DIS'] * 1000) / df_hist_jug_md['MIN'], 0)
                                df_hist_jug_md['mec_h'] = df_hist_jug_md['ACC'] + df_hist_jug_md['DCC'] + df_hist_jug_md['Nº SPR']
                                
                                df_c_val = df_hist_jug_md[(df_hist_jug_md['m_min_h'] > 0) & (df_hist_jug_md['RPE'] > 0)].copy()
                                df_n_val = df_hist_jug_md[(df_hist_jug_md['mec_h'] > 0) & (df_hist_jug_md['RPE'] > 0)].copy()
                                
                                if not df_c_val.empty: df_c_val['EFI_C'] = df_c_val['RPE'] / df_c_val['m_min_h']
                                if not df_n_val.empty: df_n_val['EFI_N'] = df_n_val['RPE'] / df_n_val['mec_h']

                                media_c = df_c_val['EFI_C'].mean() if not df_c_val.empty else 0
                                std_c = df_c_val['EFI_C'].std(ddof=0) if not df_c_val.empty else 0
                                std_c = std_c if std_c > 0 else (media_c * 0.1)

                                media_n = df_n_val['EFI_N'].mean() if not df_n_val.empty else 0
                                std_n = df_n_val['EFI_N'].std(ddof=0) if not df_n_val.empty else 0
                                std_n = std_n if std_n > 0 else (media_n * 0.1)
                                
                                z_cardio = (efi_cardio - media_c) / std_c if media_c > 0 and std_c > 0 else 0
                                z_neuro = (efi_neuro - media_n) / std_n if media_n > 0 and std_n > 0 else 0

                                cardio_mal, neuro_mal = (z_cardio >= 1.5), (z_neuro >= 1.5)
                                cardio_bien, neuro_bien = (z_cardio < 1.5), (z_neuro < 1.5)

                                if cardio_mal and neuro_mal:
                                    alertas_jugadores[jug]['carga'].append(f"🔴 **Fatiga Integral:** Coste Cardio Z:+{z_cardio:.1f} y Neuro Z:+{z_neuro:.1f}"); alertas_jugadores[jug]['total'] += 1
                                elif cardio_mal and not neuro_bien: 
                                    alertas_jugadores[jug]['carga'].append(f"🟡 **Coste Metabólico Elevado:** Z:+{z_cardio:.1f}"); alertas_jugadores[jug]['total'] += 1
                                elif neuro_mal and not cardio_bien: 
                                    alertas_jugadores[jug]['carga'].append(f"🟡 **Coste Neuromuscular Elevado:** Z:+{z_neuro:.1f}"); alertas_jugadores[jug]['total'] += 1
                                
                            # --- 3. MONOTONÍA Y BURNOUT PREVENTIVO ---
                            monot, strain = calcular_monotonia_7d(st.session_state.sesiones, jug, sesion['fecha'], devolver_strain=True)
                            if monot > 2.0 and strain > 4000:
                                alertas_jugadores[jug]['carga'].append(f"🔴 **Riesgo Burnout:** Monotonía {monot:.1f} (Strain: {strain:.0f} UA)"); alertas_jugadores[jug]['total'] += 1
                            
                            monot_hsr, strain_hsr = calcular_monotonia_7d(st.session_state.sesiones, jug, sesion['fecha'], metrica="DIS AI", devolver_strain=True)
                            if monot_hsr > 2.0 and strain_hsr > 1500:
                                alertas_jugadores[jug]['carga'].append(f"🔴 **Sobrecarga Mecánica:** Monotonía HSR {monot_hsr:.1f}"); alertas_jugadores[jug]['total'] += 1
                                
                        # --- AÑADE ESTO JUSTO AQUÍ (Alineado con el for _, row in activos.iterrows():) ---
                        alertas_multi, alertas_rec, alertas_car = [], [], []
                        for jug, data in alertas_jugadores.items():
                            if data['total'] >= 2: 
                                alertas_multi.append(f"**{jug}**: " + " | ".join(data['recuperacion'] + data['carga']))
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

                        efi_c_media = rpe_m / ((dis_m * 1000) / min_m) if min_m > 0 and dis_m > 0 else 0
                        efi_n_media = rpe_m / (acc_m + dcc_m + spr_m) if (acc_m + dcc_m + spr_m) > 0 else 0

                        # --- CÁLCULO DE LÍNEAS DE TENDENCIA (VS MISMO MD HISTÓRICO) ---
                        ses_md_tend = sesion.get('descripcion', 'TD') if not es_partido else "Partido"
                        
                        # Extraemos el histórico limpio excluyendo la sesión de hoy
                        df_hist_tend = df_master_hist[df_master_hist['FECHA'] < sesion["fecha"]].copy()
                        if not es_partido:
                            df_hist_tend = df_hist_tend[df_hist_tend['MD'] == ses_md_tend]
                        else:
                            df_hist_tend = df_hist_tend[df_hist_tend['TIPO_SESION'].str.contains("Partido", na=False)]
                        
                        hist_tqr_m = df_hist_tend['TQR'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_well_m = df_hist_tend['WELLNESS'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_rpe_m = df_hist_tend['RPE'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_carga_m = df_hist_tend['CARGA'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        
                        hist_efi_c = 0
                        hist_efi_n = 0
                        if not df_hist_tend.empty:
                            df_hist_tend['m_min_h'] = np.where(df_hist_tend['MIN'] > 0, (df_hist_tend['DIS'] * 1000) / df_hist_tend['MIN'], 0)
                            df_hist_tend['mec_h'] = df_hist_tend['ACC'] + df_hist_tend['DCC'] + df_hist_tend['Nº SPR']
                            
                            df_c_val = df_hist_tend[(df_hist_tend['m_min_h'] > 0) & (df_hist_tend['RPE'] > 0)]
                            df_n_val = df_hist_tend[(df_hist_tend['mec_h'] > 0) & (df_hist_tend['RPE'] > 0)]
                            
                            hist_efi_c = (df_c_val['RPE'] / df_c_val['m_min_h']).mean() if not df_c_val.empty else 0
                            hist_efi_n = (df_n_val['RPE'] / df_n_val['mec_h']).mean() if not df_n_val.empty else 0

                        def calc_tend_html(actual, historico, inverso=False):
                            if pd.isna(historico) or historico == 0: return ""
                            diff = ((actual - historico) / historico) * 100
                            if abs(diff) < 2: return "<span style='color: #94a3b8; font-size: 0.65rem; margin-left: 5px;'>▬ 0%</span>"
                            
                            if diff > 0:
                                color = "#ef4444" if inverso else "#10b981"
                                return f"<span style='color: {color}; font-size: 0.65rem; margin-left: 5px;' title='vs Media Histórica {ses_md_tend}'>▲ {abs(diff):.0f}%</span>"
                            else:
                                color = "#10b981" if inverso else "#ef4444"
                                return f"<span style='color: {color}; font-size: 0.65rem; margin-left: 5px;' title='vs Media Histórica {ses_md_tend}'>▼ {abs(diff):.0f}%</span>"

                        t_tqr = calc_tend_html(tqr_m, hist_tqr_m, inverso=False)
                        t_well = calc_tend_html(well_m, hist_well_m, inverso=True) # Más fatiga = Peor
                        t_rpe = calc_tend_html(rpe_m, hist_rpe_m, inverso=True)    # Más esfuerzo = Peor
                        t_carga = calc_tend_html(carga_m, hist_carga_m, inverso=True)
                        t_efic = calc_tend_html(efi_c_media, hist_efi_c, inverso=True) # Más coste = Peor
                        t_efin = calc_tend_html(efi_n_media, hist_efi_n, inverso=True)

                        # --- CÁLCULO DE REFERENCIAS HISTÓRICAS (MD) PARA TENDENCIAS ---
                        ses_md_tend = sesion.get('descripcion', 'TD') if not es_partido else "Partido"
                        df_hist_tend = st.session_state.df_master_informes[st.session_state.df_master_informes['FECHA'] < sesion["fecha"]].copy()
                        
                        if not es_partido:
                            df_hist_tend = df_hist_tend[(df_hist_tend['TIPO_SESION'] == "Entrenamiento") & (df_hist_tend['MD'] == ses_md_tend)]
                        else:
                            df_hist_tend = df_hist_tend[df_hist_tend['TIPO_SESION'].str.contains("Partido", na=False)]
                            
                        if 'filtro_est' in locals() and filtro_est:
                            df_hist_tend = df_hist_tend[df_hist_tend['ESTADO'].isin(filtro_est)]
                            
                        hist_tqr_m = df_hist_tend['TQR'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_well_m = df_hist_tend['WELLNESS'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_rpe_m = df_hist_tend['RPE'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        hist_carga_m = df_hist_tend['CARGA'].replace(0, np.nan).mean() if not df_hist_tend.empty else 0
                        
                        hist_readiness_m = 0
                        if hist_well_m > 0 and hist_tqr_m > 0:
                            hist_readiness_m = ((hist_tqr_m / 10) * 50) + (((35 - hist_well_m) / 30) * 50)
                            
                        hist_efi_c, hist_efi_n = 0, 0
                        if not df_hist_tend.empty:
                            df_hist_tend['m_min_h'] = np.where(df_hist_tend['MIN'] > 0, (df_hist_tend['DIS'] * 1000) / df_hist_tend['MIN'], 0)
                            df_hist_tend['mec_h'] = df_hist_tend['ACC'] + df_hist_tend['DCC'] + df_hist_tend['Nº SPR']
                            
                            df_c_val = df_hist_tend[(df_hist_tend['m_min_h'] > 0) & (df_hist_tend['RPE'] > 0)]
                            df_n_val = df_hist_tend[(df_hist_tend['mec_h'] > 0) & (df_hist_tend['RPE'] > 0)]
                            
                            hist_efi_c = (df_c_val['RPE'] / df_c_val['m_min_h']).mean() if not df_c_val.empty else 0
                            hist_efi_n = (df_n_val['RPE'] / df_n_val['mec_h']).mean() if not df_n_val.empty else 0

                        # --- CÁLCULO ACTUAL DE EFICIENCIAS Y READINESS ---
                        efi_c_media = rpe_m / ((dis_m * 1000) / min_m) if min_m > 0 and dis_m > 0 else 0
                        efi_n_media = rpe_m / (acc_m + dcc_m + spr_m) if (acc_m + dcc_m + spr_m) > 0 else 0
                        
                        readiness_m = 0
                        if well_m > 0 and tqr_m > 0:
                            readiness_m = ((tqr_m / 10) * 50) + (((35 - well_m) / 30) * 50)

                        # --- FUNCIÓN TENDENCIA HTML ---
                        def calc_tend_html(actual, historico, inverso=False):
                            if pd.isna(historico) or historico == 0: return "<span style='color: #94a3b8; font-size: 0.85rem;'>▬ N/A</span>"
                            diff = ((actual - historico) / historico) * 100
                            if abs(diff) < 2: return "<span style='color: #94a3b8; font-size: 0.85rem;'>▬ 0%</span>"
                            if diff > 0:
                                color = "#ef4444" if inverso else "#10b981"
                                return f"<span style='color: {color}; font-size: 0.85rem;'>▲ {abs(diff):.0f}%</span>"
                            else:
                                color = "#10b981" if inverso else "#ef4444"
                                return f"<span style='color: {color}; font-size: 0.85rem;'>▼ {abs(diff):.0f}%</span>"

                        t_readiness = calc_tend_html(readiness_m, hist_readiness_m, inverso=False)
                        t_carga = calc_tend_html(carga_m, hist_carga_m, inverso=True)
                        t_rpe = calc_tend_html(rpe_m, hist_rpe_m, inverso=True)
                        t_efic = calc_tend_html(efi_c_media, hist_efi_c, inverso=True)
                        t_efin = calc_tend_html(efi_n_media, hist_efi_n, inverso=True)

                        # --- ESTRUCTURAS HTML DE TARJETAS ---
                        def html_card_readiness(valor, tendencia_html):
                            color = "#10b981" if valor >= 75 else ("#f59e0b" if valor >= 60 else "#ef4444")
                            return f"""
                            <div style="background: #111318; border: 1px solid #1c1f26; border-top: 3px solid {color}; border-radius: 8px; padding: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 110px;">
                                <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 800; text-transform: uppercase; text-align: center; margin-bottom: 2px;">Readiness</span>
                                <div style="display: flex; justify-content: center; align-items: center; margin: 8px 0;">
                                    <svg viewBox="0 0 36 36" style="width: 65px; height: 65px;">
                                      <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#1c1f26" stroke-width="3" />
                                      <path stroke="{color}" stroke-dasharray="{valor}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke-width="3" stroke-linecap="round" />
                                      <text x="18" y="22.5" fill="{color}" font-size="12" font-weight="900" text-anchor="middle">{valor:.0f}</text>
                                    </svg>
                                </div>
                                <div style="text-align: center;">{tendencia_html}</div>
                            </div>
                            """

                        def html_card_basic(color, title, v1, l1, t1, v2, l2, t2):
                            return f"""
                            <div style="background: #111318; border: 1px solid #1c1f26; border-top: 3px solid {color}; border-radius: 8px; padding: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 110px;">
                                <span style="font-size: 0.9rem; color: #94a3b8; font-weight: 800; text-transform: uppercase; text-align: center; margin-bottom: 10px;">{title}</span>
                                <div style="display: flex; justify-content: space-around; align-items: center; flex: 1;">
                                    <div style="text-align: center;">
                                        <span style="font-size: 1.6rem; font-weight: 900; color: #f8fafc;">{v1}</span><br>
                                        <span style="font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase;">{l1}</span><br>
                                        <div style="margin-top: 4px;">{t1}</div>
                                    </div>
                                    <div style="width: 1px; height: 40px; background: #1c1f26;"></div>
                                    <div style="text-align: center;">
                                        <span style="font-size: 1.6rem; font-weight: 900; color: #f8fafc;">{v2}</span><br>
                                        <span style="font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase;">{l2}</span><br>
                                        <div style="margin-top: 4px;">{t2}</div>
                                    </div>
                                </div>
                            </div>
                            """

                        def html_card_triple(color, title, v1, l1, p1, v2, l2, p2, v3, l3, p3):
                            return f"""
                            <div style="background: #111318; border: 1px solid #1c1f26; border-top: 3px solid {color}; border-radius: 8px; padding: 10px 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); display: flex; flex-direction: column; justify-content: center; margin-bottom: 8px; min-height: 85px;">
                                <span style="font-size: 0.85rem; color: #94a3b8; font-weight: 800; text-transform: uppercase; margin-bottom: 6px;">{title}</span>
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div style='flex: 1; text-align: left;'>
                                        <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc;'>{v1} <span style='font-size:0.75em; color:#94a3b8;'>({p1:.0f}%)</span></span><br>
                                        <span style='font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase;'>{l1}</span>
                                    </div>
                                    <div style='width: 1px; height: 35px; background: #1c1f26; margin: 0 10px;'></div>
                                    <div style='flex: 1; text-align: center;'>
                                        <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc;'>{v2} <span style='font-size:0.75em; color:#94a3b8;'>({p2:.0f}%)</span></span><br>
                                        <span style='font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase;'>{l2}</span>
                                    </div>
                                    <div style='width: 1px; height: 35px; background: #1c1f26; margin: 0 10px;'></div>
                                    <div style='flex: 1; text-align: right;'>
                                        <span style='font-size: 1.4rem; font-weight: 800; color: #f8fafc;'>{v3} <span style='font-size:0.75em; color:#94a3b8;'>({p3:.0f}%)</span></span><br>
                                        <span style='font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase;'>{l3}</span>
                                    </div>
                                </div>
                            </div>
                            """

                        # --- REFERENCIAS 100% PARTIDO (VOLUMEN Y DENSIDAD) ---
                        df_historico_partidos = st.session_state.df_master_informes[(st.session_state.df_master_informes['TIPO_SESION'].str.contains("Partido", na=False)) & (st.session_state.df_master_informes['DIS'] > 0)].copy()
                        if not df_historico_partidos.empty:
                            df_historico_partidos['MIN_REAL'] = np.where(df_historico_partidos.get('MIN_GPS', df_historico_partidos['MIN']) > 0, df_historico_partidos.get('MIN_GPS', df_historico_partidos['MIN']), df_historico_partidos['MIN'])
                            min_totales_eq = df_historico_partidos['MIN_REAL'].sum()
                            
                            dis_100_eq = (df_historico_partidos['DIS'].sum() / min_totales_eq) * 90 if min_totales_eq > 0 else 10.0
                            hsr_100_eq = (df_historico_partidos['DIS AI'].sum() / min_totales_eq) * 90 if min_totales_eq > 0 else 600.0
                            acc_100_eq = (df_historico_partidos['ACC'].sum() / min_totales_eq) * 90 if min_totales_eq > 0 else 40.0
                            dcc_100_eq = (df_historico_partidos['DCC'].sum() / min_totales_eq) * 90 if min_totales_eq > 0 else 40.0
                            
                            df_sum_indiv = df_historico_partidos.groupby('JUGADOR')[['DIS', 'DIS AI', 'ACC', 'DCC', 'MIN_REAL']].sum()
                            medias_indiv_partido = {j_nom: {'DIS': (j_row['DIS']/j_row['MIN_REAL'])*90, 'DIS AI': (j_row['DIS AI']/j_row['MIN_REAL'])*90, 'ACC': (j_row['ACC']/j_row['MIN_REAL'])*90, 'DCC': (j_row['DCC']/j_row['MIN_REAL'])*90} for j_nom, j_row in df_sum_indiv.iterrows() if j_row['MIN_REAL'] > 0}
                        else:
                            dis_100_eq, hsr_100_eq, acc_100_eq, dcc_100_eq = 10.0, 600.0, 40.0, 40.0
                            medias_indiv_partido = {}

                        # Volúmenes
                        pct_dis_eq = (dis_m / dis_100_eq) * 100 if dis_100_eq > 0 else 0
                        pct_hsr_eq = (hsr_m / hsr_100_eq) * 100 if hsr_100_eq > 0 else 0
                        pct_acc_eq = ((acc_m + dcc_m) / (acc_100_eq + dcc_100_eq)) * 100 if (acc_100_eq + dcc_100_eq) > 0 else 0
                        
                        # Densidades (m/min o acc/min)
                        den_dis_100 = (dis_100_eq * 1000) / 90
                        den_hsr_100 = hsr_100_eq / 90
                        den_mec_100 = (acc_100_eq + dcc_100_eq) / 90
                        
                        den_dis_act = (dis_m * 1000) / min_m if min_m > 0 else 0
                        den_hsr_act = hsr_m / min_m if min_m > 0 else 0
                        den_mec_act = (acc_m + dcc_m) / min_m if min_m > 0 else 0
                        
                        pct_den_dis = (den_dis_act / den_dis_100) * 100 if den_dis_100 > 0 else 0
                        pct_den_hsr = (den_hsr_act / den_hsr_100) * 100 if den_hsr_100 > 0 else 0
                        pct_den_mec = (den_mec_act / den_mec_100) * 100 if den_mec_100 > 0 else 0

                        # --- RENDERIZADO GRID ---
                        col_r, col_c, col_co, col_e = st.columns([0.8, 1.2, 1.2, 2.5])
                        
                        with col_r:
                            st.markdown(html_card_readiness(readiness_m, t_readiness), unsafe_allow_html=True)
                            
                        with col_c:
                            st.markdown(html_card_basic("#f59e0b", "Carga Interna", f"{carga_m:.0f}", "Carga (UA)", t_carga, f"{rpe_m:.1f}", "RPE Medio", t_rpe), unsafe_allow_html=True)
                                
                        with col_co:
                            st.markdown(html_card_basic("#8b5cf6", "Eficiencia", f"{efi_c_media:.2f}", "Coste Cardio", t_efic, f"{efi_n_media:.2f}", "Coste Neuro", t_efin), unsafe_allow_html=True)
                            
                        with col_e:
                            st.markdown(html_card_triple("#C5A059", "Carga Externa: Volúmenes", f"{dis_m:.2f}k", "Distancia", pct_dis_eq, f"{hsr_m:.0f}m", "HSR (>21)", pct_hsr_eq, f"{(acc_m + dcc_m):.0f}", "ACC+DCC", pct_acc_eq), unsafe_allow_html=True)
                            st.markdown(html_card_triple("#0ea5e9", "Carga Externa: Densidades", f"{den_dis_act:.0f}", "m / min", pct_den_dis, f"{den_hsr_act:.1f}", "HSR / min", pct_den_hsr, f"{den_mec_act:.1f}", "MEC / min", pct_den_mec), unsafe_allow_html=True)
                        st.markdown("---")
                        
                        # --- 4. ALERTAS DE RIESGO MOVIDAS ARRIBA (EN 3 COLUMNAS) ---
                        st.markdown("#### :material/warning: Alertas de Rendimiento y Riesgo Lesivo")
                        if not alertas_multi and not alertas_rec and not alertas_car:
                            st.success(":material/check_circle: Todos los marcadores de fatiga y riesgo del equipo están dentro de los parámetros normales.")
                        else:
                            c_al_rec, c_al_car, c_al_mul = st.columns(3)
                            with c_al_rec:
                                st.markdown("##### :material/psychology: Recuperación")
                                if alertas_rec:
                                    for al in alertas_rec: st.warning(al)
                                else: st.info(":material/check_circle: Sin alertas.")
                            with c_al_car:
                                st.markdown("##### :material/local_fire_department: Carga")
                                if alertas_car:
                                    for al in alertas_car: st.warning(al)
                                else: st.info(":material/check_circle: Sin alertas.")
                            with c_al_mul:
                                st.markdown("##### :material/emergency: Riesgo Multifactorial")
                                if alertas_multi:
                                    for al in alertas_multi: st.error(al)
                                else: st.success(":material/check_circle: Sin alertas críticas.")

                        st.markdown("---")

                        # --- 5. GRÁFICOS DE BIENESTAR ---
                        st.markdown("#### :material/psychology: 1. Bienestar y Recuperación")
                        
                        # --- GRÁFICO PANORÁMICO DE READINESS INDIVIDUAL ---
                        if 'TQR' in df_graficos.columns and 'WELLNESS' in df_graficos.columns:
                            df_graficos['READINESS'] = np.where(
                                (df_graficos['TQR'] > 0) & (df_graficos['WELLNESS'] > 0),
                                ((df_graficos['TQR'] / 10) * 50) + (((35 - df_graficos['WELLNESS']) / 30) * 50),
                                0
                            )
                            if df_graficos['READINESS'].sum() > 0:
                                df_rd = df_graficos[df_graficos['READINESS'] > 0].sort_values('READINESS', ascending=False)
                                fig_rd = px.bar(
                                    df_rd, x='JUGADOR', y='READINESS', color='READINESS', 
                                    color_continuous_scale="RdYlGn", range_color=[0, 100], 
                                    title="<b>Índice de Readiness Individual</b> (TQR + Wellness)",
                                    text='READINESS'
                                )
                                fig_rd.update_traces(
                                    texttemplate='%{text:.0f}', textposition='outside', 
                                    marker_line_color='#1c1f26', marker_line_width=1
                                )
                                fig_rd.update_layout(
                                    height=250, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                                    margin=dict(t=40, b=20, l=40, r=40), coloraxis_showscale=False,
                                    xaxis_title="", yaxis_title="Puntos (0-100)",
                                    yaxis_range=[0, 115] # Espacio adicional para el texto superior
                                )
                                fig_rd.add_hline(y=75, line_dash="dot", line_color="#10b981", annotation_text="Óptimo (>75)", annotation_position="bottom right")
                                fig_rd.add_hline(y=60, line_dash="dash", line_color="#ef4444", annotation_text="Riesgo (<60)", annotation_position="top right")
                                st.plotly_chart(fig_rd, use_container_width=True, key=f"ses_rd_{idx_real}")

                        cg1, cg2 = st.columns(2)
                        with cg1:
                            if df_graficos['WELLNESS'].sum() > 0:
                                df_well = df_graficos[df_graficos['WELLNESS'] > 0].sort_values('WELLNESS', ascending=False).copy()
                                nombres_limpios = {'W_Sueño': 'Sueño', 'W_Fatiga': 'Fatiga', 'W_Dolor': 'Dolor', 'W_Estres': 'Estrés', 'W_Humor': 'Humor'}
                                df_well = df_well.rename(columns=nombres_limpios)
                                fig_well = go.Figure()
                                for i, factor in enumerate(list(nombres_limpios.values())):
                                    fig_well.add_trace(go.Bar(x=df_well['JUGADOR'], y=df_well[factor], name=factor, marker_color=px.colors.qualitative.Set2[i]))
                                fig_well.update_layout(title="<b>Desglose de Wellness</b>", barmode='stack', yaxis_title="Puntos", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, title=""), yaxis_range=[0, 35], plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=60, l=40, r=40), hovermode="x unified")
                                
                                umbrales_z = []
                                for jug_bar in df_well['JUGADOR']:
                                    st_j = dict_zscore.get(jug_bar, {'media': 0, 'std': 1.0})
                                    umbrales_z.append(st_j['media'] + (1.5 * st_j['std']) if st_j['media'] > 0 else 24)
                                    
                                fig_well.add_trace(go.Scatter(x=df_well['JUGADOR'], y=umbrales_z, mode='lines+markers', name='Límite Z-Score (+1.5)', line=dict(color='red', width=2, dash='dot'), marker=dict(symbol='diamond-open', size=8)))
                                
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
                        st.markdown("#### :material/local_fire_department: 2. Carga Interna")
                        
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
                                df_ac = df_graficos[df_graficos['RATIO A/C'] > 0].copy()
                                df_ac = df_ac.sort_values('RATIO A/C', ascending=False)
                                
                                z_data = df_ac[['RATIO A/C', 'RATIO A/C HSR', 'RATIO A/C ACC']].values
                                y_labels = df_ac['JUGADOR'].tolist()
                                x_labels = ['A/C INT', 'A/C HSR', 'A/C ACC']
                                
                                # Escala de colores estricta adaptada al Sweet Spot Model (0.8 - 1.3)
                                colorscale = [
                                    [0.0, "#C5A059"], [0.44, "#C5A059"],  # 0.0 a ~0.8 (Azul - Under-loading)
                                    [0.44, "#10b981"], [0.72, "#10b981"], # ~0.8 a ~1.3 (Verde - Sweet Spot)
                                    [0.72, "#f59e0b"], [0.83, "#f59e0b"], # ~1.3 a ~1.5 (Amarillo - Danger Zone)
                                    [0.83, "#ef4444"], [1.0, "#ef4444"]   # > 1.5 (Rojo - Riesgo Crítico)
                                ]
                                
                                fig3 = go.Figure(data=go.Heatmap(
                                    z=z_data, x=x_labels, y=y_labels,
                                    colorscale=colorscale, zmin=0.0, zmax=1.8,
                                    text=np.round(z_data, 2), texttemplate="%{text}",
                                    textfont={"color": "white", "weight": "bold", "size": 12},
                                    hoverongaps=False, showscale=False,
                                    xgap=2, ygap=2
                                ))
                                
                                fig3.update_layout(
                                    title="Riesgo Multidimensional (ACWR)", 
                                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                                    margin=dict(l=10, r=10, t=40, b=10), 
                                    yaxis={'autorange': 'reversed', 'tickfont': {'size': 11}},
                                    xaxis={'tickfont': {'size': 11}}
                                )
                                st.plotly_chart(fig3, use_container_width=True, key=f"ses_ac_{idx_real}")
                        
                        with st.expander(":material/list_alt: Ver Tabla Detallada de Carga Interna"):
                            cols_ver_ci = ['JUGADOR', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C', 'RATIO A/C HSR', 'RATIO A/C ACC']
                            df_tabla_riesgo = df_informe[cols_ver_ci].rename(columns={'RATIO A/C': 'A/C INT', 'RATIO A/C HSR': 'A/C HSR', 'RATIO A/C ACC': 'A/C ACC'})
                            
                            estilo_ci = (df_tabla_riesgo.style.hide(axis="index")
                                         .format({"MIN": "{:.0f}'", "RPE": "{:.0f}", "CARGA": "{:.0f}", "EWMA AGUDA": "{:.0f}", "EWMA CRÓNICA": "{:.0f}", "A/C INT": "{:.2f}", "A/C HSR": "{:.2f}", "A/C ACC": "{:.2f}"})
                                         .map(lambda x: f"background-color: {color_ratio_ac(x)}; color: black; font-weight: bold;" if isinstance(x, (int, float)) else "", subset=['A/C INT', 'A/C HSR', 'A/C ACC']))
                            mostrar_tabla_moderna(estilo_ci)
                        
                        st.markdown("---")

                        # --- 7. CARGA EXTERNA (GRÁFICOS PRIMERO, TABLA DESPUÉS, CON % VMAX) ---
                        st.markdown("#### :material/directions_run: 3. Carga Externa (GPS)")
                        
                        # --- HUELLA DACTILAR DE LA SESIÓN ---
                        if es_partido:
                            # Normalizamos el rendimiento global de ESTE partido a 90' para compararlo con justeza
                            min_efectivo_sesion = np.where(df_para_medias_gps.get('MIN_GPS', df_para_medias_gps['MIN']) > 0, df_para_medias_gps.get('MIN_GPS', df_para_medias_gps['MIN']), df_para_medias_gps['MIN'])
                            min_totales = min_efectivo_sesion.sum()
                            
                            if min_totales > 0:
                                vol_actual = (df_para_medias_gps['DIS'].sum() / min_totales) * 90 * 1000
                                int_actual = (df_para_medias_gps['DIS AI'].sum() / min_totales) * 90
                                ten_actual = ((df_para_medias_gps['ACC'].sum() + df_para_medias_gps['DCC'].sum()) / min_totales) * 90
                            else:
                                vol_actual, int_actual, ten_actual = 0, 0, 0
                        else:
                            # En entrenamientos usamos valores absolutos (la referencia también es absoluta)
                            vol_actual = dis_m * 1000
                            int_actual = hsr_m
                            ten_actual = acc_m + dcc_m
                        
                        df_historico = st.session_state.df_master_informes
                        # Exclusión estricta de porteros y de registros sin GPS real para no falsear medias
                        df_hist_campo = df_historico[(df_historico['POS'] != "POR") & (df_historico['DIS'] > 0)].copy()
                        
                        # REFERENCIA 1: PARTIDO (Normalizado a 90 minutos)
                        df_partidos = df_hist_campo[df_hist_campo['TIPO_SESION'].str.contains("Partido", na=False)]
                        if not df_partidos.empty:
                            min_efectivo_partido = np.where(df_partidos.get('MIN_GPS', df_partidos['MIN']) > 0, df_partidos.get('MIN_GPS', df_partidos['MIN']), df_partidos['MIN'])
                            # Extraemos la densidad global y proyectamos un "Partido Teórico de 90'"
                            v_ref_partido = (df_partidos['DIS'].sum() / min_efectivo_partido.sum()) * 90 * 1000
                            i_ref_partido = (df_partidos['DIS AI'].sum() / min_efectivo_partido.sum()) * 90
                            t_ref_partido = ((df_partidos['ACC'].sum() + df_partidos['DCC'].sum()) / min_efectivo_partido.sum()) * 90
                        else:
                            v_ref_partido, i_ref_partido, t_ref_partido = 10000, 600, 100
                            
                        # REFERENCIA 2: ENTRENAMIENTO MD (Promedio Absoluto de Disponibles)
                        ses_md = sesion.get('descripcion', 'TD')
                        df_md = df_hist_campo[(df_hist_campo['TIPO_SESION'] == "Entrenamiento") & (df_hist_campo['MD'] == ses_md) & (df_hist_campo['ESTADO'] == "Disponible")]
                        if not df_md.empty:
                            # Sin normalizar: buscamos el volumen físico real histórico de esta sesión
                            v_ref_md = df_md['DIS'].mean() * 1000
                            i_ref_md = df_md['DIS AI'].mean()
                            t_ref_md = df_md['ACC'].mean() + df_md['DCC'].mean()
                        else:
                            v_ref_md = vol_actual if vol_actual > 0 else 1
                            i_ref_md = int_actual if int_actual > 0 else 1
                            t_ref_md = ten_actual if ten_actual > 0 else 1
                            
                        c_hd1, c_hd2 = st.columns([1, 2.2])
                        with c_hd1:
                            st.markdown("##### :material/fingerprint: Huella Dactilar")
                            st.caption("Identifica de un vistazo la morfología de la carga y el enfoque físico-táctico de la sesión.")
                            tipo_ref = st.radio("Referencia (100%):", ["Orientación (vs Partido)", f"Cumplimiento (vs {ses_md})"], key=f"rad_ref_{idx_real}")
                            
                            v_ref = v_ref_partido if "Partido" in tipo_ref else v_ref_md
                            i_ref = i_ref_partido if "Partido" in tipo_ref else i_ref_md
                            t_ref = t_ref_partido if "Partido" in tipo_ref else t_ref_md
                            
                            v_ref = v_ref if v_ref > 0 else 1
                            i_ref = i_ref if i_ref > 0 else 1
                            t_ref = t_ref if t_ref > 0 else 1
                            
                            p_vol = (vol_actual / v_ref) * 100
                            p_int = (int_actual / i_ref) * 100
                            p_ten = (ten_actual / t_ref) * 100
                            
                            if p_ten > p_vol and p_ten > p_int: insight = ":material/local_fire_department: **Predominancia de Tensión:** Espacios reducidos y transiciones cortas."
                            elif p_vol >= p_ten and p_vol >= p_int: insight = ":material/directions_run: **Predominancia de Volumen:** Sesión extensiva y carga aeróbica."
                            else: insight = ":material/bolt: **Predominancia de Intensidad:** Alta velocidad y transiciones largas."
                                
                            st.info(insight)
                            
                        with c_hd2:
                            fig_hd = go.Figure()
                            cats = ['Volumen<br>(Distancia)', 'Intensidad<br>(HSR)', 'Tensión<br>(ACC+DCC)']
                            
                            # Línea base de referencia (100%)
                            fig_hd.add_trace(go.Scatterpolar(
                                r=[100, 100, 100, 100], theta=cats + [cats[0]], mode='lines', 
                                line=dict(color='#94a3b8', dash='dot', width=2), name='100% Ref.'
                            ))
                            # Polígono de la sesión
                            fig_hd.add_trace(go.Scatterpolar(
                                r=[p_vol, p_int, p_ten, p_vol], theta=cats + [cats[0]], fill='toself', 
                                name='Sesión', line=dict(color='#0ea5e9', width=3), fillcolor='rgba(14, 165, 233, 0.4)'
                            ))
                            
                            # Forzamos la transparencia de la telaraña (bgcolor) y adaptamos los colores de los ejes
                            fig_hd.update_layout(
                                polar=dict(
                                    bgcolor='rgba(0,0,0,0)', 
                                    radialaxis=dict(
                                        visible=True, range=[0, max(120, p_vol, p_int, p_ten)], 
                                        gridcolor="#1c1f26", linecolor="#1c1f26", tickfont=dict(color='#94a3b8')
                                    ),
                                    angularaxis=dict(
                                        gridcolor="#1c1f26", linecolor="#1c1f26", tickfont=dict(color='#f8fafc', size=11, weight='bold')
                                    )
                                ),
                                showlegend=True, 
                                paper_bgcolor='rgba(0,0,0,0)', 
                                plot_bgcolor='rgba(0,0,0,0)', 
                                font=dict(color='#f8fafc'), 
                                margin=dict(t=30, b=30, l=60, r=60), 
                                height=360
                            )
                            st.plotly_chart(fig_hd, use_container_width=True, key=f"hd_fig_{idx_real}")
                            
                        st.markdown("---")
                        
                        cg5, cg6 = st.columns(2)
                        
                        # --- MOTOR DE PERIODIZACIÓN TÁCTICA (ZONAS OBJETIVO AMPLIADAS) ---
                        # Se definen las bandas objetivo como porcentajes [Min, Max] respecto a la media del partido
                        zonas_pt = {
                            "MD-5": {"DIS": [0.15, 0.45], "HSR": [0.00, 0.20], "ACC": [0.10, 0.40], "DCC": [0.10, 0.40]},
                            "MD-4": {"DIS": [0.40, 0.70], "HSR": [0.10, 0.40], "ACC": [0.70, 1.30], "DCC": [0.70, 1.30]},
                            "MD-3": {"DIS": [0.60, 0.90], "HSR": [0.50, 0.95], "ACC": [0.40, 0.75], "DCC": [0.40, 0.75]},
                            "MD-2": {"DIS": [0.30, 0.55], "HSR": [0.15, 0.45], "ACC": [0.25, 0.55], "DCC": [0.25, 0.55]},
                            "MD-1": {"DIS": [0.15, 0.35], "HSR": [0.00, 0.15], "ACC": [0.10, 0.30], "DCC": [0.10, 0.30]},
                            "MD+1": {"DIS": [0.15, 0.45], "HSR": [0.00, 0.20], "ACC": [0.10, 0.40], "DCC": [0.10, 0.40]},
                            "MD+2": {"DIS": [0.30, 0.60], "HSR": [0.10, 0.35], "ACC": [0.25, 0.60], "DCC": [0.25, 0.60]},
                            "TD":   {"DIS": [0.45, 0.85], "HSR": [0.25, 0.75], "ACC": [0.45, 0.85], "DCC": [0.45, 0.85]}
                        }
                        
                        ses_md = sesion.get('descripcion', 'TD')
                        if es_partido: ses_md = "Partido" 
                        zona_obj = {"DIS": [0.75, 1.20], "HSR": [0.75, 1.20], "ACC": [0.75, 1.20], "DCC": [0.75, 1.20]} if es_partido else zonas_pt.get(ses_md, zonas_pt["TD"])
                        
                        with cg5:
                            if df_graficos['DIS'].sum() > 0:
                                df_gps_sesion = df_graficos[df_graficos['DIS'] > 0].copy()
                                
                                # Evaluar Cumplimiento Individual/Grupal (Verde, Amarillo, Rojo)
                                def eval_cump_vol_int(r):
                                    if es_partido:
                                        ref_d = medias_indiv_partido.get(r['JUGADOR'], {}).get('DIS', dis_100_eq)
                                        ref_h = medias_indiv_partido.get(r['JUGADOR'], {}).get('DIS AI', hsr_100_eq)
                                    else:
                                        ref_d, ref_h = dis_100_eq, hsr_100_eq
                                        
                                    ref_d = ref_d if ref_d > 0 else 10.0
                                    ref_h = ref_h if ref_h > 0 else 600.0
                                    
                                    val_h = r.get('DIS AI', r.get('HID >21', 0))
                                    d_ok = zona_obj["DIS"][0] * ref_d <= r['DIS'] <= zona_obj["DIS"][1] * ref_d
                                    h_ok = zona_obj["HSR"][0] * ref_h <= val_h <= zona_obj["HSR"][1] * ref_h
                                    
                                    if d_ok and h_ok: return "Óptimo (En Objetivo)"
                                    elif r['DIS'] > zona_obj["DIS"][1] * ref_d or val_h > zona_obj["HSR"][1] * ref_h: return "Excesivo"
                                    else: return "Deficiente"
                                
                                df_gps_sesion['DIS AI'] = df_gps_sesion.get('DIS AI', df_gps_sesion.get('HID >21', 0))
                                df_gps_sesion['Cumplimiento'] = df_gps_sesion.apply(eval_cump_vol_int, axis=1)
                                
                                tit_v = "Vol. vs Int. (Banda Obj. Individual)" if es_partido else f"Vol. vs Int. (Banda Obj: {ses_md})"
                                fig5 = px.scatter(df_gps_sesion, x='DIS', y='DIS AI', color='Cumplimiento', hover_name='JUGADOR', text='JUGADOR', title=tit_v, color_discrete_map={"Óptimo (En Objetivo)": "#10b981", "Excesivo": "#ef4444", "Deficiente": "#f59e0b"})
                                fig5.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                fig5.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                                
                                # La zona objetivo global solo se dibuja en entrenamientos (en partidos es individual para cada punto)
                                if not es_partido:
                                    fig5.add_shape(type="rect", x0=zona_obj["DIS"][0]*dis_100_eq, x1=zona_obj["DIS"][1]*dis_100_eq, y0=zona_obj["HSR"][0]*hsr_100_eq, y1=zona_obj["HSR"][1]*hsr_100_eq, fillcolor="green", opacity=0.15, line_width=2, line_color="green", layer="below")
                                    fig5.add_annotation(x=zona_obj["DIS"][1]*dis_100_eq, y=zona_obj["HSR"][1]*hsr_100_eq, text="ZONA OBJETIVO", showarrow=False, font=dict(color="green", size=10), xanchor="right", yanchor="bottom")
                                
                                st.plotly_chart(fig5, use_container_width=True, key=f"ses_h_{idx_real}")
                                
                        with cg6:
                            if df_graficos['ACC'].sum() > 0 or df_graficos['DCC'].sum() > 0:
                                df_accdcc = df_graficos[df_graficos['DIS'] > 0].copy()
                                
                                def eval_cump_ten(r):
                                    if es_partido:
                                        ref_a = medias_indiv_partido.get(r['JUGADOR'], {}).get('ACC', acc_100_eq)
                                        ref_d = medias_indiv_partido.get(r['JUGADOR'], {}).get('DCC', dcc_100_eq)
                                    else:
                                        ref_a, ref_d = acc_100_eq, dcc_100_eq
                                        
                                    ref_a = ref_a if ref_a > 0 else 40.0
                                    ref_d = ref_d if ref_d > 0 else 40.0
                                    
                                    a_ok = zona_obj["ACC"][0] * ref_a <= r['ACC'] <= zona_obj["ACC"][1] * ref_a
                                    d_ok = zona_obj["DCC"][0] * ref_d <= r['DCC'] <= zona_obj["DCC"][1] * ref_d
                                    if a_ok and d_ok: return "Óptimo (En Objetivo)"
                                    elif r['ACC'] > zona_obj["ACC"][1] * ref_a or r['DCC'] > zona_obj["DCC"][1] * ref_d: return "Excesivo"
                                    else: return "Deficiente"
                                    
                                df_accdcc['Cumplimiento'] = df_accdcc.apply(eval_cump_ten, axis=1)
                                
                                max_val = max(df_accdcc['ACC'].max(), df_accdcc['DCC'].max(), zona_obj["ACC"][1]*acc_100_eq*1.1) if not df_accdcc.empty else 10
                                tit_t = "Tensión Mecánica (Banda Obj. Individual)" if es_partido else f"Tensión Mecánica (Banda Obj: {ses_md})"
                                fig4 = px.scatter(df_accdcc, x='DCC', y='ACC', color='Cumplimiento', hover_name='JUGADOR', text='JUGADOR', title=tit_t, color_discrete_map={"Óptimo (En Objetivo)": "#10b981", "Excesivo": "#ef4444", "Deficiente": "#f59e0b"})
                                fig4.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                fig4.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", dash="dot"))
                                
                                if not es_partido:
                                    fig4.add_shape(type="rect", x0=zona_obj["DCC"][0]*dcc_100_eq, x1=zona_obj["DCC"][1]*dcc_100_eq, y0=zona_obj["ACC"][0]*acc_100_eq, y1=zona_obj["ACC"][1]*acc_100_eq, fillcolor="green", opacity=0.15, line_width=2, line_color="green", layer="below")
                                    fig4.add_annotation(x=zona_obj["DCC"][1]*dcc_100_eq, y=zona_obj["ACC"][1]*acc_100_eq, text="ZONA OBJETIVO", showarrow=False, font=dict(color="green", size=10), xanchor="right", yanchor="bottom")
                                
                                fig4.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                                st.plotly_chart(fig4, use_container_width=True, key=f"ses_a_{idx_real}")

                        # --- GRÁFICOS DE DENSIDAD CRUZADA (Volumen vs Intensidad) ---
                        df_den = df_graficos[df_graficos['DIS'] > 0].copy()
                        if not df_den.empty:
                            df_den['DIS AI'] = df_den.get('DIS AI', df_den.get('HID >21', 0))
                            df_den['m/min'] = np.where(df_den['MIN'] > 0, (df_den['DIS'] * 1000) / df_den['MIN'], 0)
                            df_den['HSR/min'] = np.where(df_den['MIN'] > 0, df_den['DIS AI'] / df_den['MIN'], 0)
                            df_den['Mec/min'] = np.where(df_den['MIN'] > 0, (df_den['ACC'] + df_den['DCC']) / df_den['MIN'], 0)
                            
                            cg7, cg8 = st.columns(2)
                            with cg7:
                                fig_den_v = px.scatter(df_den, x='m/min', y='HSR/min', color='POS', size='VMAX', hover_name='JUGADOR', text='JUGADOR', title="Densidad: Volumen vs Intensidad (Burbuja = VMax)", color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"})
                                fig_den_v.update_traces(textposition='top center', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                fig_den_v.update_xaxes(autorange=True)
                                fig_den_v.update_yaxes(autorange=True)
                                fig_den_v.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig_den_v, use_container_width=True, key=f"ses_den_v_{idx_real}")
                            with cg8:
                                fig_den_m = px.scatter(df_den, x='m/min', y='Mec/min', color='POS', hover_name='JUGADOR', text='JUGADOR', title="Densidad: Volumen vs Tensión Mecánica", color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"})
                                fig_den_m.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
                                fig_den_m.update_xaxes(autorange=True)
                                fig_den_m.update_yaxes(autorange=True)
                                fig_den_m.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                                st.plotly_chart(fig_den_m, use_container_width=True, key=f"ses_den_m_{idx_real}")

                        # --- TABLA DE CARGA EXTERNA (CON % RELATIVO INDIVIDUAL) ---
                        with st.expander(":material/list_alt: Ver Tabla Detallada de Carga Externa"):
                            df_tabla_ce = df_informe[df_informe['DIS'] > 0].copy()
                            df_tabla_ce['DIS AI'] = df_tabla_ce.get('DIS AI', df_tabla_ce.get('HID >21', 0))
                            
                            def calc_pct_match(row, metric):
                                val_partido = medias_indiv_partido.get(row['JUGADOR'], {}).get(metric, 0)
                                return (row[metric] / val_partido) * 100 if val_partido > 0 else 0
                                
                            df_tabla_ce['% DIS (Part)'] = df_tabla_ce.apply(lambda r: calc_pct_match(r, 'DIS'), axis=1)
                            df_tabla_ce['% HSR (Part)'] = df_tabla_ce.apply(lambda r: calc_pct_match(r, 'DIS AI'), axis=1)
                            df_tabla_ce['% ACC (Part)'] = df_tabla_ce.apply(lambda r: calc_pct_match(r, 'ACC'), axis=1)
                            df_tabla_ce['DCC:ACC'] = np.where(df_tabla_ce['ACC'] > 0, df_tabla_ce['DCC'] / df_tabla_ce['ACC'], 0)
                            
                            cols_ver_ce = ['JUGADOR', 'DIS', '% DIS (Part)', 'DIS AI', '% HSR (Part)', 'ACC', 'DCC', 'DCC:ACC', 'VMAX', '% VMAX']
                            mostrar_tabla_moderna(df_tabla_ce[cols_ver_ce].style.hide(axis="index")
                                                  .format({"DIS": "{:.2f}", "% DIS (Part)": "{:.2f}%", "DIS AI": "{:.0f}", "% HSR (Part)": "{:.2f}%", "ACC": "{:.0f}", "DCC": "{:.0f}", "DCC:ACC": "{:.2f}", "VMAX": "{:.2f}", "% VMAX": "{:.2f}%"})
                                                  .map(lambda x: "color: #ef4444; font-weight: bold;" if isinstance(x, (int, float)) and x > 1.3 else "", subset=['DCC:ACC']))
                        
                        # --- MÓDULO DE CARGA COMPENSATORIA (MD+1 / MD+2) ---
                        es_compensatoria = not es_partido and sesion.get('descripcion') in ['MD+1', 'MD+2']
                        
                        if es_partido or es_compensatoria:
                            st.markdown(f"#### :material/battery_charging_full: Carga Compensatoria {'(Seguimiento en Vivo)' if es_compensatoria else '(Recomendada 60 min)'}")
                            st.caption("Ajustado por posición específica (Titulares) y carga semanal acumulada en microciclo.")
                            
                            df_hist = st.session_state.df_master_informes.copy()
                            
                            if es_partido:
                                fecha_partido = sesion['fecha']
                            else:
                                df_hist_partidos = df_hist[(df_hist['TIPO_SESION'].str.contains("Partido", na=False)) & (df_hist['FECHA'] < sesion['fecha'])]
                                fecha_partido = df_hist_partidos['FECHA'].max() if not df_hist_partidos.empty else None
                                
                            if fecha_partido:
                                _, _, lunes_partido, _ = obtener_rango_fechas_semana(fecha_partido)
                                lunes_str = lunes_partido.strftime("%Y-%m-%d")
                                
                                df_partido_data = df_hist[df_hist['FECHA'] == fecha_partido].copy()
                                df_sem_data = df_hist[(df_hist['FECHA'] >= lunes_str) & (df_hist['FECHA'] < fecha_partido) & (df_hist['TIPO_SESION'] == 'Entrenamiento')].copy()
                                
                                if not df_partido_data.empty:
                                    df_partido_data['MIN_REAL'] = np.where(df_partido_data.get('MIN_GPS', df_partido_data['MIN']) > 0, df_partido_data.get('MIN_GPS', df_partido_data['MIN']), df_partido_data['MIN'])
                                    
                                    titulares_partido = df_partido_data[df_partido_data['ESTADO'] == 'Titular']
                                    suplentes_partido = df_partido_data[df_partido_data['ESTADO'].isin(['Suplente', 'No convocado'])]
                                    
                                    metricas_carga = ['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
                                    dict_pos_esp = {limpiar_nombre(p["JUGADOR"]): p.get("pos_1", p.get("POS", "DEF")) for p in st.session_state.plantilla}
                                    
                                    titulares_densidad = {}
                                    titulares_entreno = {}
                                    
                                    # 1. Extraer densidades y cargas previas de Titulares por posición
                                    for _, t in titulares_partido.iterrows():
                                        jug, m_real = t['JUGADOR'], t['MIN_REAL']
                                        pos_e = dict_pos_esp.get(limpiar_nombre(jug), 'DEF')
                                        
                                        if pos_e not in titulares_densidad: titulares_densidad[pos_e] = {m: [] for m in metricas_carga}
                                        if pos_e not in titulares_entreno: titulares_entreno[pos_e] = {m: [] for m in metricas_carga}
                                        
                                        if m_real > 0:
                                            for m in metricas_carga: titulares_densidad[pos_e][m].append(t.get(m, 0) / m_real)
                                            
                                        df_j_ent = df_sem_data[df_sem_data['JUGADOR'] == jug]
                                        for m in metricas_carga: titulares_entreno[pos_e][m].append(df_j_ent[m].sum() if not df_j_ent.empty else 0)
                                            
                                    for pos_e in titulares_densidad:
                                        for m in metricas_carga:
                                            titulares_densidad[pos_e][m] = np.mean(titulares_densidad[pos_e][m]) if titulares_densidad[pos_e][m] else 0.0
                                            titulares_entreno[pos_e][m] = np.mean(titulares_entreno[pos_e][m]) if titulares_entreno[pos_e][m] else 0.0
                                            
                                    fallback_densidad = {m: np.mean([v[m] for v in titulares_densidad.values()]) if titulares_densidad else 0 for m in metricas_carga}
                                    fallback_entreno = {m: np.mean([v[m] for v in titulares_entreno.values()]) if titulares_entreno else 0 for m in metricas_carga}
                                    
                                    # 2. Calcular déficit de los suplentes
                                    comp_data = []
                                    for _, sup in suplentes_partido.iterrows():
                                        jug = sup['JUGADOR']
                                        pos_e = dict_pos_esp.get(limpiar_nombre(jug), 'DEF')
                                        
                                        densidad_obj = titulares_densidad.get(pos_e, fallback_densidad)
                                        entreno_obj = titulares_entreno.get(pos_e, fallback_entreno)
                                        
                                        df_sup_ent = df_sem_data[df_sem_data['JUGADOR'] == jug]
                                        
                                        deficit = {}
                                        for m in metricas_carga:
                                            target_60m = densidad_obj[m] * 60
                                            total_target = entreno_obj[m] + target_60m
                                            total_actual = (df_sup_ent[m].sum() if not df_sup_ent.empty else 0) + sup.get(m, 0)
                                            deficit[m] = max(0, total_target - total_actual)
                                            
                                        if deficit['DIS'] > 0 or deficit['DIS AI'] > 0:
                                            if es_compensatoria:
                                                d_hoy = next((d for d in sesion['datos_informe'] if limpiar_nombre(d['JUGADOR']) == limpiar_nombre(jug)), {})
                                                if not d_hoy: continue # Si el suplente no entrenó en MD+1, lo saltamos
                                                
                                                m_hoy = safe_float(d_hoy.get('MIN_GPS', d_hoy.get('MIN', 0)))
                                                comp_data.append({
                                                    "JUGADOR": jug, "POS": pos_e,
                                                    "Obj_DIS": deficit['DIS'], "Hoy_DIS": safe_float(d_hoy.get('DIS', 0)),
                                                    "Obj_HSR": deficit['DIS AI'], "Hoy_HSR": safe_float(d_hoy.get('DIS AI', d_hoy.get('HID >21', 0))),
                                                    "Obj_SPR": deficit['Nº SPR'], "Hoy_SPR": safe_float(d_hoy.get('Nº SPR', d_hoy.get('SPR >24', 0))),
                                                    "Obj_MEC": deficit['ACC'] + deficit['DCC'], "Hoy_MEC": safe_float(d_hoy.get('ACC', 0)) + safe_float(d_hoy.get('DCC', 0)),
                                                    "MIN_Hoy": m_hoy,
                                                    "Den_Obj_DIS": densidad_obj['DIS'] * 1000, "Den_Hoy_DIS": (safe_float(d_hoy.get('DIS', 0))*1000)/m_hoy if m_hoy>0 else 0,
                                                    "Den_Obj_HSR": densidad_obj['DIS AI'], "Den_Hoy_HSR": safe_float(d_hoy.get('DIS AI', 0))/m_hoy if m_hoy>0 else 0
                                                })
                                            else:
                                                comp_data.append({
                                                    "JUGADOR": jug, "POS": pos_e,
                                                    "Déficit Volumen (km)": deficit['DIS'], "Déficit HSR (>21 km/h)": deficit['DIS AI'],
                                                    "Déficit Sprints (>24)": deficit['Nº SPR'], "Déficit Tensión (ACC+DCC)": deficit['ACC'] + deficit['DCC']
                                                })

                                    if comp_data:
                                        if es_partido:
                                            df_comp = pd.DataFrame(comp_data)
                                            mostrar_tabla_moderna(df_comp.style.hide(axis="index").format(precision=1))
                                        else:
                                            for c in comp_data:
                                                p_dis = min(100, (c['Hoy_DIS'] / c['Obj_DIS']) * 100) if c['Obj_DIS'] > 0 else 100
                                                p_hsr = min(100, (c['Hoy_HSR'] / c['Obj_HSR']) * 100) if c['Obj_HSR'] > 0 else 100
                                                p_mec = min(100, (c['Hoy_MEC'] / c['Obj_MEC']) * 100) if c['Obj_MEC'] > 0 else 100
                                                
                                                min_comp_v = (c['Hoy_DIS'] / (c['Den_Obj_DIS']/1000)) if c['Den_Obj_DIS'] > 0 else 0
                                                min_comp_i = (c['Hoy_HSR'] / c['Den_Obj_HSR']) if c['Den_Obj_HSR'] > 0 else 0
                                                min_comp_real = (min_comp_v + min_comp_i) / 2

                                                st.markdown(f"""
                                                <div style="background: #111318; border: 1px solid #1c1f26; border-left: 4px solid #C5A059; padding: 12px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
                                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                                        <strong style="color: #f8fafc; font-size: 1.1rem;">{c['JUGADOR']} <span style="font-size: 0.8rem; color: #94a3b8;">({c['POS']})</span></strong>
                                                        <span style="color: #10b981; font-weight: 800; font-size: 0.9rem;">Eq. Partido: ~{min_comp_real:.0f} min</span>
                                                    </div>
                                                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                                                        <div>
                                                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; font-weight: 800;">
                                                                <span>VOLUMEN ({c['Hoy_DIS']:.1f} / {c['Obj_DIS']:.1f} km)</span>
                                                                <span style="color: #0ea5e9;">{p_dis:.0f}%</span>
                                                            </div>
                                                            <div style="background: #1c1f26; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                                                                <div style="background: #0ea5e9; width: {p_dis}%; height: 100%;"></div>
                                                            </div>
                                                            <div style="font-size: 0.7rem; color: #64748b; font-weight: 600;">Densidad actual: {c['Den_Hoy_DIS']:.0f} m/m (Obj: {c['Den_Obj_DIS']:.0f})</div>
                                                        </div>
                                                        <div>
                                                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; font-weight: 800;">
                                                                <span>HSR ({c['Hoy_HSR']:.0f} / {c['Obj_HSR']:.0f} m)</span>
                                                                <span style="color: #f59e0b;">{p_hsr:.0f}%</span>
                                                            </div>
                                                            <div style="background: #1c1f26; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                                                                <div style="background: #f59e0b; width: {p_hsr}%; height: 100%;"></div>
                                                            </div>
                                                            <div style="font-size: 0.7rem; color: #64748b; font-weight: 600;">Densidad actual: {c['Den_Hoy_HSR']:.1f} m/m (Obj: {c['Den_Obj_HSR']:.1f})</div>
                                                        </div>
                                                        <div>
                                                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; font-weight: 800;">
                                                                <span>TENSIÓN ({c['Hoy_MEC']:.0f} / {c['Obj_MEC']:.0f} acc)</span>
                                                                <span style="color: #ef4444;">{p_mec:.0f}%</span>
                                                            </div>
                                                            <div style="background: #1c1f26; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 4px;">
                                                                <div style="background: #ef4444; width: {p_mec}%; height: 100%;"></div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                    else:
                                        st.success("Todos los suplentes igualaron la carga media de su posición.")
                            else:
                                st.info("No hay registros de un partido previo o titulares para calcular el déficit.")

            # ---------------------------------------------------------
            # HERRAMIENTA 3: CARGA DE DATOS (FORMULARIO OPTIMIZADO)
            # ---------------------------------------------------------
            elif active_view == "datos":
                st.markdown(f"#### :material/folder_open: CARGA DE DATOS | {sesion['fecha']}")
                if f'msg_sync_{idx_real}' in st.session_state:
                    for msg in st.session_state[f'msg_sync_{idx_real}']:
                        if ":material/check_circle:" in msg: st.success(msg)
                        elif ":material/warning:" in msg: st.warning(msg)
                        elif ":material/help:" in msg: st.info(msg)
                    del st.session_state[f'msg_sync_{idx_real}']

                t_man, t_exc = st.tabs([":material/edit_document: Edición Manual de Tabla", ":material/upload_file: Importar desde Excel"])
                
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
                            submit_manual = st.form_submit_button(":material/save: Guardar y Calcular Tabla", type="primary", use_container_width=True)
                        with col_btn2:
                            del_manual = st.form_submit_button(":material/delete: Vaciar Datos de Sesión", use_container_width=True)
                            
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
                                    "EWMA AGUDA": ewma_aguda,
                                    "EWMA CRÓNICA": ewma_cronica,
                                    "RATIO A/C": ratio_ac,
                                    "DIS": dis,
                                    "DIS AI": dis_ai_21,
                                    "Nº SPR": spr_24,
                                    "ACC": acc_3,
                                    "DCC": dcc_3,
                                    "VMAX": v_max,
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
                                    "R_30_45": r_30_45,
                                    "Z1": r_0_7 + r_7_14,
                                    "Z2": r_14_21,
                                    "Z3": r_21_24,
                                    "Z4": r_24_27,
                                    "Z5": r_27_30,
                                    "Z6": r_30_45
                                })
                                
                            # Imputar GPS automático antes de guardar
                            from utils.math_helpers import aplicar_imputacion_gps_global
                            full_records = aplicar_imputacion_gps_global(full_records, sesion, st.session_state.plantilla)
                            
                            st.session_state.sesiones[idx_real]['datos_informe'] = full_records # (o registros_sesion en el bloque Excel)
                            st.session_state.sesiones[idx_real]['informe_generado'] = True
                            
                            # NUEVO: Recalcular EWMA incluyendo la sesión actual recién guardada
                            ewma_post = calcular_ewma_historico(st.session_state.sesiones, sesion["fecha"])
                            for reg_item in st.session_state.sesiones[idx_real]['datos_informe']:
                                d_ewma = ewma_post.get(reg_item["JUGADOR"], {})
                                reg_item["EWMA AGUDA"] = d_ewma.get("EWMA AGUDA", reg_item["CARGA"])
                                reg_item["EWMA CRÓNICA"] = d_ewma.get("EWMA CRÓNICA", reg_item["CARGA"])
                                reg_item["RATIO A/C"] = d_ewma.get("RATIO A/C", 1.0)
                                
                            guardar_datos(modulo="sesiones")
                            st.success(":material/check_circle: Datos de la sesión borrados correctamente.")
                            st.rerun()

                with t_exc:
                    st.caption("Asegúrate de haber configurado el nombre de las columnas en la pestaña de Configuración.")
                    col_up1, col_up2, col_up3 = st.columns(3)
                    with col_up1: archivo_well = st.file_uploader("1. Wellness:", type=["xlsx"], key=f"up_w_{idx_real}")
                    with col_up2: archivo_rpe = st.file_uploader("2. RPE:", type=["xlsx"], key=f"up_r_{idx_real}")
                    with col_up3: archivo_gps = st.file_uploader("3. GPS:", type=["xlsx"], key=f"up_g_{idx_real}")
                    
                    if st.button(":material/settings: Sincronizar Archivos", type="primary", use_container_width=True):
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
                                from utils.math_helpers import aplicar_imputacion_gps_global
                                registros_sesion = aplicar_imputacion_gps_global(registros_sesion, sesion, st.session_state.plantilla)
                                
                                st.session_state.sesiones[idx_real]['datos_informe'] = registros_sesion
                                st.session_state.sesiones[idx_real]['informe_generado'] = True
                                guardar_datos(modulo="sesiones")
                                
                                msgs = [f":material/check_circle: Sincronización completada. Se generó la tabla con los {len(nombres_plantilla)} jugadores de tu plantilla."]
                                if archivo_well and faltan_w: msgs.append(f":material/warning: **Faltan en Wellness:** {', '.join(faltan_w)}")
                                if archivo_rpe and faltan_r: msgs.append(f":material/warning: **Faltan en RPE:** {', '.join(faltan_r)}")
                                if no_encontrados_en_app: msgs.append(f":material/help: **Están en Excel pero NO en tu App:** {', '.join(no_encontrados_en_app)}")
                                st.session_state[f'msg_sync_{idx_real}'] = msgs
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error al procesar: {e}")

            # ---------------------------------------------------------
            # HERRAMIENTA 4: LESIONES (FORMULARIO COMPRIMIDO)
            # ---------------------------------------------------------
            elif active_view == "les":
                st.markdown(f"#### :material/emergency: PARTE MÉDICO | {sesion['fecha']}")
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
                        
                        if st.form_submit_button(":material/save: Registrar Lesión", type="primary"):
                            nueva_lesion = {"id_sesion": sesion["fecha"], "tipo_sesion": "Partido" if es_partido else "Entrenamiento", "jugador": les_jugador, "tipo": les_tipo, "zona": les_zona, "lado": les_lado, "lateralidad": les_lat, "contacto": les_contacto, "cesped": les_cesped, "recidiva": les_recidiva, "comentarios": les_comentarios, "dias_baja": None, "estado": "Activa", "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                            st.session_state.lesiones.append(nueva_lesion)
                            guardar_datos(modulo="lesiones")
                            st.success(f"¡Parte médico de {les_jugador} guardado!")
                            st.rerun()

            # ---------------------------------------------------------
            # HERRAMIENTA 5: ESTADÍSTICAS DEL PARTIDO
            # ---------------------------------------------------------
            elif active_view == "stats" and es_partido:
                st.markdown(f"#### :material/bolt: ESTADÍSTICAS DE PARTIDO | vs {sesion.get('rival', 'Rival')} ({sesion['fecha']})")
                col_g1, col_g2 = st.columns(2)
                condicion_actual = sesion.get("condicion", "Casa")
                nueva_condicion = col_g1.selectbox("Condición:", ["Casa", "Fuera"], index=["Casa", "Fuera"].index(condicion_actual), key=f"cond_{idx_real}")
                goles_f_actual = sesion.get("goles_favor", 0)
                nuevo_gf = col_g2.number_input("Goles Anotados (Favor del Equipo):", min_value=0, value=int(goles_f_actual or 0), key=f"gf_{idx_real}")
                
                sesion["condicion"] = nueva_condicion
                sesion["goles_favor"] = nuevo_gf

                st.markdown("##### :material/list_alt: Rendimiento de Jugadores Convocados")
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

                with st.expander(":material/add_circle: Añadir jugador del filial / juvenil / invitado"):
                    c_inv1, c_inv2, c_inv3, c_inv4 = st.columns([2, 1, 1, 1])
                    nombre_invitado = c_inv1.text_input("Nombre del Jugador Invitado:", key=f"nombre_inv_{idx_real}")
                    pos_invitado = c_inv2.selectbox("Posición:", ["POR", "DEF", "MED", "ATA"], key=f"pos_inv_{idx_real}")
                    rol_invitado = c_inv3.selectbox("Rol:", ["Suplente", "Titular"], key=f"rol_inv_{idx_real}")
                    min_invitado = c_inv4.number_input("Minutos:", min_value=0, max_value=120, value=45, key=f"min_inv_{idx_real}")
                    if st.button(":material/add_circle: Incluir en la tabla del partido", key=f"btn_add_inv_{idx_real}"):
                        if nombre_invitado.strip():
                            if "estadisticas_invitados" not in sesion: sesion["estadisticas_invitados"] = []
                            sesion["estadisticas_invitados"].append({"JUGADOR": nombre_invitado.strip() + " (Cantera)", "POS": pos_invitado, "Rol": rol_invitado, "Minutos": min_invitado, "Goles": 0, "Goles Encajados": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0})
                            guardar_datos(modulo="sesiones")
                            st.success(f":material/check_circle: {nombre_invitado} añadido al partido.")
                            st.rerun()
                        else: st.warning("Escribe un nombre válido.")

                if not jugadores_convocados:
                    st.warning(":material/warning: No hay jugadores convocados. Configura la disponibilidad o añade un jugador invitado arriba.")
                else:
                    df_stats_base = pd.DataFrame(jugadores_convocados)
                    cols_orden_stats = ["JUGADOR", "POS", "Rol", "Minutos", "Goles", "Goles Encajados", "Asistencias", "Amarillas", "Rojas"]
                    for c in cols_orden_stats:
                        if c not in df_stats_base.columns: df_stats_base[c] = 0
                    
                    with st.form(f"form_stats_{idx_real}"):
                        edited_stats = st.data_editor(df_stats_base[cols_orden_stats], use_container_width=True, hide_index=True, disabled=["JUGADOR", "POS", "Rol"])
                        if st.form_submit_button(":material/save: Guardar Estadísticas de Partido", type="primary"):
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
                            
                            # NUEVO: Recalcular imputación al cambiar los minutos del partido
                            if sesion.get("informe_generado") and sesion.get("datos_informe"):
                                from utils.math_helpers import aplicar_imputacion_gps_global
                                sesion["datos_informe"] = aplicar_imputacion_gps_global(sesion["datos_informe"], sesion, st.session_state.plantilla)

                            guardar_datos(modulo="sesiones")
                            st.success(f":material/check_circle: ¡Estadísticas guardadas y datos GPS re-imputados con éxito! (Goles en contra totales: {goles_contra_totales})")
                            st.rerun()
with tab_add:
    st.markdown("### :material/add_circle: Planificación de Sesiones")
    st.caption("Selecciona la fecha e introduce los datos del evento para registrarlo en el calendario.")
    
    col_add1, col_add2, col_add3 = st.columns([1, 2, 1])
    
    with col_add2:
        with st.container(border=True):
            st.markdown("#### :material/calendar_month: 1. Fecha del Evento")
            dia_clicado = st.date_input("Selecciona una fecha:", date.today())
            fecha_formateada = dia_clicado.strftime("%d-%m-%Y")
            
            sesiones_en_fecha = [s for s in st.session_state.sesiones if s["fecha"] == str(dia_clicado)]
            if sesiones_en_fecha: 
                st.info(f":material/info: Ya hay {len(sesiones_en_fecha)} evento(s) el {fecha_formateada}.")
            else:
                st.success(f":material/check_circle: Día libre el {fecha_formateada}. Listo para programar.")
                
        with st.container(border=True):
            st.markdown("#### :material/settings: 2. Detalles de la Sesión")
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
                        st.info(":material/info: Rival no guardado en la BBDD.")
                        ciudad_manual_nuevo = st.text_input("Ciudad (Necesario para clima autom.):")
                
            if st.button(":material/save: Guardar Sesión", use_container_width=True, type="primary"):
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
