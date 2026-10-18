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

st.subheader("🚑 Lesiones")

tab_les_res, tab_gest_med, tab_les_list, tab_rtp = st.tabs(["📊 Resumen", "🩺 Gestión Médica", "📋 Listado de Lesiones", "🏃‍♂️ Protocolo RTP"])

les_data = st.session_state.get("lesiones", [])
if not les_data:
    with tab_les_res: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
    with tab_gest_med: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
    with tab_les_list: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
    with tab_rtp: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
else:
    df_les = st.session_state.df_lesiones.copy()
    df_les['Mes_Num'] = pd.to_datetime(df_les['id_sesion']).dt.month
    df_les['Mes'] = df_les['Mes_Num'].map(meses_esp)
    df_les['Gravedad'] = df_les['dias_baja'].apply(categorizar_duracion)
    
    with tab_les_res:
        # 1. RESERVA DE ESPACIOS VISUALES (Se dibujarán arriba, aunque se calculen abajo)
        cont_kpis = st.container()
        st.markdown("---")
        cont_graficos = st.container()
        st.markdown("---")
        
        # 2. FILTROS AL FONDO (Desplegables)
        with st.expander("🔍 Filtros Epidemiológicos", expanded=False):
            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                meses_unicos = ["TODOS"] + list(df_les['Mes'].dropna().unique())
                filtro_mes = st.selectbox("Mes:", meses_unicos)
            with c_f2:
                filtro_tipo_ses = st.selectbox("Sesión:", ["TODOS", "Entrenamiento", "Partido"])
            with c_f3:
                jugs_unicos = ["TODOS"] + sorted([j["JUGADOR"] for j in st.session_state.plantilla])
                filtro_jugador = st.selectbox("Jugador:", jugs_unicos)
                
        # 3. LÓGICA DE CÁLCULO
        def calcular_dias_reales(row):
            if row.get('estado') == 'Activa':
                fecha_les = datetime.strptime(row['id_sesion'], "%Y-%m-%d").date()
                return max((date.today() - fecha_les).days, 0)
            else:
                return safe_float(row.get('dias_baja', 0))

        df_anual = df_les.copy()
        df_filtrado = df_anual.copy()
        if filtro_mes != "TODOS": df_filtrado = df_filtrado[df_filtrado['Mes'] == filtro_mes]
        if filtro_tipo_ses != "TODOS": df_filtrado = df_filtrado[df_filtrado['tipo_sesion'] == filtro_tipo_ses]
        if filtro_jugador != "TODOS": df_filtrado = df_filtrado[df_filtrado['jugador'] == filtro_jugador]

        def calcular_metricas(df_eval, mes_eval, ses_eval, jug_eval):
            if df_eval.empty:
                return 0, 0, 0.0, 0.0, 0.0
                
            df_eval_calc = df_eval.copy()
            df_eval_calc['dias_reales'] = df_eval_calc.apply(calcular_dias_reales, axis=1)
            t_les = len(df_eval_calc)
            t_dias = int(df_eval_calc['dias_reales'].sum())
            p_dias = t_dias / t_les if t_les > 0 else 0
            
            h_tot = 0
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    try:
                        mes_s = meses_esp[datetime.strptime(s["fecha"], "%Y-%m-%d").month]
                    except: continue
                    
                    if mes_eval != "TODOS" and mes_s != mes_eval: continue
                    
                    es_partido_s = "Partido" in s["tipo"]
                    if ses_eval == "Entrenamiento" and es_partido_s: continue
                    if ses_eval == "Partido" and not es_partido_s: continue
                    
                    for d in s["datos_informe"]:
                        if jug_eval == "TODOS" or d["JUGADOR"] == jug_eval:
                            h_tot += float(d.get("MIN", 0)) / 60.0

            inc = (t_les / h_tot * 1000) if h_tot > 0 else 0
            bur = (t_dias / h_tot * 1000) if h_tot > 0 else 0
            return t_les, t_dias, p_dias, inc, bur

        # 4. DIBUJAR KPIs ARRIBA (Usando el contenedor reservado)
        with cont_kpis:
            if df_filtrado.empty:
                st.warning("No hay lesiones que coincidan con los filtros aplicados.")
            else:
                total_lesiones, total_dias, promedio_dias, incidencia, burden = calcular_metricas(df_filtrado, filtro_mes, filtro_tipo_ses, filtro_jugador)

                from utils.math_helpers import render_kpi_elite
                
                # Tarjetas renderizadas con texto en el título para evitar el fallo HTML interno
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1: render_kpi_elite("Lesiones Totales", f"{total_lesiones}", color_borde="#3b82f6")
                with k2: render_kpi_elite("Días de Baja Totales", f"{total_dias}", color_borde="#f59e0b")
                with k3: render_kpi_elite("Días de baja  / Lesión", f"{promedio_dias:.1f}", color_borde="#8b5cf6")
                with k4: render_kpi_elite("Incidencia Lesional", f"{incidencia:.1f}", color_borde="#ef4444")
                with k5: render_kpi_elite("Burden", f"{burden:.0f}", color_borde="#ef4444")
                
        # 5. DIBUJAR GRÁFICOS EN MEDIO (Usando el contenedor reservado)
        with cont_graficos:
            st.markdown("#### 📈 Desglose Estadístico")
            if not df_filtrado.empty:
                cg1, cg2, cg3 = st.columns(3)
                with cg1:
                    conteo_dur = df_filtrado['Gravedad'].value_counts().reset_index()
                    fig_dur = px.pie(conteo_dur, names='Gravedad', values='count', title="1. Duración", hole=0.5)
                    fig_dur.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_dur.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_dur, use_container_width=True, key="les_pie_dur")
                with cg2:
                    conteo_tipo = df_filtrado['tipo'].value_counts().reset_index()
                    fig_tipo = px.pie(conteo_tipo, names='tipo', values='count', title="2. Tipo", hole=0.5)
                    fig_tipo.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_tipo.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_tipo, use_container_width=True, key="les_pie_tipo")
                with cg3:
                    conteo_zona = df_filtrado['zona'].value_counts().reset_index()
                    fig_zona = px.pie(conteo_zona, names='zona', values='count', title="3. Zona", hole=0.5)
                    fig_zona.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_zona.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_zona, use_container_width=True, key="les_pie_zona")
                    
                cg4, cg5, cg6 = st.columns(3)
                with cg4:
                    conteo_lat = df_filtrado['lateralidad'].value_counts().reset_index()
                    fig_lat = px.pie(conteo_lat, names='lateralidad', values='count', title="4. Lateralidad", hole=0.5)
                    fig_lat.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_lat.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_lat, use_container_width=True, key="les_pie_lat")
                with cg5:
                    conteo_recidiva = df_filtrado['recidiva'].value_counts().reset_index()
                    fig_rec = px.pie(conteo_recidiva, names='recidiva', values='count', title="5. Recidiva", hole=0.5)
                    fig_rec.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_rec.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_rec, use_container_width=True, key="les_pie_rec")
                with cg6:
                    conteo_sup = df_filtrado['cesped'].value_counts().reset_index()
                    fig_sup = px.pie(conteo_sup, names='cesped', values='count', title="6. Superficie", hole=0.5)
                    fig_sup.update_layout(showlegend=True, height=280, margin=dict(t=40, b=10, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    fig_sup.update_traces(textposition='inside', textinfo='percent')
                    st.plotly_chart(fig_sup, use_container_width=True, key="les_pie_sup")

    with tab_gest_med:
        st.markdown("#### 🩺 Gestor de Altas Médicas")
        lesiones_activas = [l for l in st.session_state.lesiones if l.get("estado") == "Activa"]
        
        if not lesiones_activas:
            st.success("✅ ¡Toda la plantilla está sana! No hay ninguna lesión activa pendiente de cerrar.")
        else:
            nombres_lesiones_activas = [f"{l['id_sesion']} | {l['jugador']} - {l['tipo']} ({l['zona']})" for l in lesiones_activas]
            les_seleccionada_idx = st.selectbox("Selecciona la lesión que deseas dar de alta:", range(len(lesiones_activas)), format_func=lambda x: nombres_lesiones_activas[x])
            les_obj = lesiones_activas[les_seleccionada_idx]
            
            fecha_lesion = datetime.strptime(les_obj["id_sesion"], "%Y-%m-%d")
            fecha_alta_sugerida = None
            dias_sugeridos = 0
            
            sesiones_ordenadas_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
            for s in sesiones_ordenadas_crono:
                s_dt = datetime.strptime(s["fecha"], "%Y-%m-%d")
                if s_dt > fecha_lesion:
                    # Normalizamos la búsqueda ignorando posibles espacios o mayúsculas en el diccionario
                    disp_dict_clean = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
                    disp_jug = disp_dict_clean.get(limpiar_nombre(les_obj["jugador"]), "")
                    
                    # Añadido "Readaptación" como estado válido de alta médica
                    if disp_jug in ["Disponible", "Readaptación", "Titular", "Suplente"]:
                        fecha_alta_sugerida = s_dt
                        dias_sugeridos = (fecha_alta_sugerida - fecha_lesion).days
                        break
            
            with st.form("form_alta_medica"):
                st.write(f"Actualizando lesión de **{les_obj['jugador']}** (Iniciada el {les_obj['id_sesion']})")
                
                if fecha_alta_sugerida:
                    st.info(f"💡 **Auto-Detección:** {les_obj['jugador']} volvió a estar '{disp_jug}' el **{fecha_alta_sugerida.strftime('%Y-%m-%d')}**.")
                    dias_baja_input = st.number_input("Días de Baja Totales:", min_value=1, max_value=500, value=dias_sugeridos)
                else:
                    st.warning("El jugador no ha vuelto a estar disponible en ninguna sesión registrada.")
                    dias_baja_input = st.number_input("Días de Baja Totales (Añadir manualmente):", min_value=1, max_value=500, value=7)
                    
                if st.form_submit_button("✅ Procesar Alta Médica"):
                    # 1. Búsqueda por índice exacto en lugar de bucle
                    real_idx = st.session_state.lesiones.index(les_obj)
                    
                    # 2. Modificación directa en memoria
                    st.session_state.lesiones[real_idx]["estado"] = "Recuperado"
                    st.session_state.lesiones[real_idx]["dias_baja"] = dias_baja_input
                    
                    # 3. CRÍTICO: Forzar sincronización del DataFrame para el guardado en BBDD
                    st.session_state.df_lesiones = pd.DataFrame(st.session_state.lesiones)
                    
                    guardar_datos(modulo="lesiones")
                    st.success(f"Alta médica procesada. {les_obj['jugador']} estuvo {dias_baja_input} días de baja.")
                    st.rerun()

    with tab_les_list:
        df_mostrar_list = df_les.copy()
        
        def display_dias_tabla(row):
            if row.get('estado') == 'Activa':
                dias_actuales = max((date.today() - datetime.strptime(row['id_sesion'], "%Y-%m-%d").date()).days, 0)
                return f"{dias_actuales} (Activa)"
            return str(int(safe_float(row.get('dias_baja', 0))))
            
        df_mostrar_list['dias_baja_display'] = df_mostrar_list.apply(display_dias_tabla, axis=1)

        cols_mostrar = ["id_sesion", "tipo_sesion", "jugador", "tipo", "zona", "lado", "lateralidad", "contacto", "cesped", "recidiva", "estado", "dias_baja_display", "comentarios"]
        df_mostrar = df_mostrar_list[cols_mostrar].rename(columns={
            "id_sesion": "Fecha", "tipo_sesion": "Sesión", "jugador": "Jugador", "tipo": "Tipo", 
            "zona": "Zona", "lado": "Lado", "lateralidad": "Lateralidad", "contacto": "Contacto", 
            "cesped": "Superficie", "recidiva": "Recidiva", "estado": "Estado", "dias_baja_display": "Días Baja", "comentarios": "Comentarios"
        })
        
        st.dataframe(
            df_mostrar,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Estado": st.column_config.TextColumn("Estado", help="Indica si la lesión sigue activa o está de alta"),
                "Días Baja": st.column_config.TextColumn("Días Baja", help="Días acumulados"),
                "Comentarios": st.column_config.TextColumn("Comentarios", width="large")
            }
        )
        
        st.markdown("---")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("#### 📝 Editar Comentarios")
            lesiones_todas_ordenadas = sorted(st.session_state.lesiones, key=lambda x: x.get("fecha_registro", "2000-01-01"), reverse=True)
            nombres_les_todas = [f"{l['id_sesion']} | {l['jugador']} ({l['tipo']})" for l in lesiones_todas_ordenadas]
            
            les_edit_idx = st.selectbox("Selecciona una lesión del historial:", range(len(lesiones_todas_ordenadas)), format_func=lambda x: nombres_les_todas[x])
            les_edit_obj = lesiones_todas_ordenadas[les_edit_idx]
            
            with st.form("form_edit_coment"):
                nuevo_com = st.text_area("Modificar comentario / mecanismo lesional:", value=les_edit_obj.get("comentarios", ""))
                if st.form_submit_button("💾 Guardar Cambios"):
                    real_idx = st.session_state.lesiones.index(les_edit_obj)
                    st.session_state.lesiones[real_idx]["comentarios"] = nuevo_com
                    
                    # CRÍTICO: Sincronizar BBDD
                    st.session_state.df_lesiones = pd.DataFrame(st.session_state.lesiones)
                    
                    guardar_datos(modulo="lesiones")
                    st.success("¡Comentario actualizado correctamente!")
                    st.rerun()
        
        with col_m2:
            st.markdown("#### 🗑️ Eliminar Registro de Lesión")
            if st.session_state.lesiones:
                lesiones_todas_del = sorted(st.session_state.lesiones, key=lambda x: x.get("fecha_registro", "2000-01-01"), reverse=True)
                nombres_les_borrar = [f"{l['id_sesion']} | {l['jugador']} ({l['tipo']} - {l['zona']})" for l in lesiones_todas_del]
                
                with st.form("form_eliminar_lesion"):
                    les_del_idx = st.selectbox("Selecciona la lesión duplicada o errónea:", range(len(lesiones_todas_del)), format_func=lambda x: nombres_les_borrar[x])
                    st.warning("⚠️ Cuidado: Esta acción borrará el registro médico de la base de datos para siempre.")
                    
                    if st.form_submit_button("❌ Eliminar Lesión Definitivamente"):
                        les_a_borrar = lesiones_todas_del[les_del_idx]
                        real_idx_del = st.session_state.lesiones.index(les_a_borrar)
                        del st.session_state.lesiones[real_idx_del]
                        
                        # CRÍTICO: Sincronizar BBDD
                        st.session_state.df_lesiones = pd.DataFrame(st.session_state.lesiones)
                        
                        guardar_datos(modulo="lesiones")
                        st.success("¡Registro de lesión eliminado correctamente!")
                        st.rerun()
            else:
                st.info("No hay lesiones en el historial para eliminar.")
                
    with tab_rtp:
        st.markdown("#### 🏃‍♂️ Motor Automatizado de Return To Play (RTP)")
        st.caption("Sistema inteligente de fases. Analiza automáticamente el volumen, la tolerancia a la carga (Ratio A/C ajustado), el dolor post-sesión y la exposición a alta velocidad. Evalúa los criterios de alta competitiva cruzándolos con el historial pre-lesión del jugador.")

        # 1. IDENTIFICACIÓN AUTOMÁTICA DE JUGADORES EN READAPTACIÓN (Exclusivo de Entrenamientos)
        jugadores_readaptacion = []
        if st.session_state.sesiones:
            # Ordenamos todas las sesiones para el uso general posterior del RTP
            sesiones_ordenadas = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
            
            # Filtramos solo los entrenamientos para evaluar el estado médico/disponibilidad real
            entrenamientos = [s for s in st.session_state.sesiones if s.get("tipo") == "Entrenamiento"]
            
            if entrenamientos:
                entrenamientos_ordenados = sorted(entrenamientos, key=lambda x: x["fecha"])
                ult_entreno = entrenamientos_ordenados[-1]
                disp_ult = {limpiar_nombre(k): v for k, v in ult_entreno.get("disponibilidad", {}).items()}
                
                for j in st.session_state.plantilla:
                    if disp_ult.get(limpiar_nombre(j["JUGADOR"])) == "Readaptación":
                        jugadores_readaptacion.append(j["JUGADOR"])

        if not jugadores_readaptacion:
            st.success("✅ No hay ningún jugador en proceso de readaptación actualmente (basado en la disponibilidad de la última sesión registrada).")
        else:
            c_sel_rtp, _ = st.columns([1, 2])
            jug_rtp = c_sel_rtp.selectbox("Selecciona al deportista en proceso RTP:", sorted(jugadores_readaptacion))
            
            lesiones_jugador = [l for l in df_les.to_dict('records') if l['jugador'] == jug_rtp]
            
            if not lesiones_jugador:
                st.warning(f"⚠️ {jug_rtp} está marcado como 'Readaptación', pero no tiene registros de lesiones previas en la base de datos.")
            else:
                l_rtp = sorted(lesiones_jugador, key=lambda x: x['id_sesion'])[-1]
                fecha_lesion_dt = datetime.strptime(l_rtp['id_sesion'], "%Y-%m-%d").date()
                
                # Calcular días de baja
                if l_rtp['estado'] == 'Activa':
                    dias_rtp = max((date.today() - fecha_lesion_dt).days, 0)
                else:
                    dias_rtp = int(safe_float(l_rtp.get('dias_baja', 0)))
                
                # 2. DETERMINAR GRAVEDAD Y FASES BASE
                if dias_rtp <= 4: grav_rtp = "Mínima"
                elif dias_rtp <= 7: grav_rtp = "Leve"
                elif dias_rtp <= 14: grav_rtp = "Moderada I"
                elif dias_rtp <= 28: grav_rtp = "Moderada II"
                else: grav_rtp = "Grave"

                s1, s2, s3 = 0, 0, 0
                if grav_rtp == "Leve": s3 = 1
                elif grav_rtp == "Moderada I": s1, s2, s3 = 1, 1, 1
                elif grav_rtp == "Moderada II": s1, s2, s3 = 2, 2, 2
                elif grav_rtp == "Grave": s1, s2, s3 = 3, 3, 3

                # Penalización inicial por tejido o recidiva
                es_tend_o_recidiva = (l_rtp.get('recidiva') == "Sí" or l_rtp.get('tipo') == "Tendinosa")
                if es_tend_o_recidiva:
                    s1 += 1; s2 += 1; s3 += 1

                req_fases = [s1, s2, s3, 999] # Fase 4 es indefinida hasta el alta
                
                st.markdown(f"**Lesión Evaluada:** {l_rtp['tipo']} en {l_rtp['zona']} ({l_rtp['id_sesion']}) | **Gravedad Base:** {grav_rtp} ({dias_rtp} días)")
                if es_tend_o_recidiva: 
                    st.warning("⚠️ **Penalización estructural aplicada:** +1 sesión requerida por fase (Lesión tendinosa o recidiva).")

                # 3. BASELINE DEL JUGADOR (Vmax histórica, Carga Crónica y Demandas Posicionales)
                partidos_jug = []
                vmax_hist = 0
                
                # Variables para el fallback posicional
                jugador_datos_rtp = next((j for j in st.session_state.plantilla if limpiar_nombre(j["JUGADOR"]) == limpiar_nombre(jug_rtp)), None)
                pos_esp_rtp = jugador_datos_rtp.get("pos_1", jugador_datos_rtp.get("POS", "DEF")) if jugador_datos_rtp else "DEF"
                partidos_posicion = []
                vmax_posicion = 0
                
                for s in sesiones_ordenadas:
                    if s.get("informe_generado"):
                        es_partido = "Partido" in s.get("tipo", "")
                        for d in s.get("datos_informe", []):
                            j_n = limpiar_nombre(d["JUGADOR"])
                            v_actual = safe_float(d.get("VMAX", d.get("V_Max", 0)))
                            m_actual = safe_float(d.get("MIN", 0))
                            dis_actual = safe_float(d.get("DIS", 0)) # CLAVE: Filtrar registros sin GPS
                            
                            # Datos propios del jugador lesionado
                            if j_n == limpiar_nombre(jug_rtp):
                                if v_actual > vmax_hist: vmax_hist = v_actual
                                
                                # Solo sumamos si realmente llevó GPS en el partido (DIS > 0)
                                if es_partido and m_actual > 0 and dis_actual > 0:
                                    partidos_jug.append({
                                        "DIS_pm": dis_actual / m_actual,
                                        "HSR_pm": safe_float(d.get("DIS AI", d.get("HID >21", 0))) / m_actual,
                                        "SPR_pm": safe_float(d.get("Nº SPR", d.get("SPR >24", 0))) / m_actual,
                                        "ACC_pm": safe_float(d.get("ACC", d.get("ACC >3", 0))) / m_actual,
                                        "DCC_pm": safe_float(d.get("DCC", d.get("DCC >3", 0))) / m_actual,
                                    })
                            # Datos de compañeros para herencia posicional
                            else:
                                comp_datos = next((j for j in st.session_state.plantilla if limpiar_nombre(j["JUGADOR"]) == j_n), None)
                                pos_esp_comp = comp_datos.get("pos_1", comp_datos.get("POS", "")) if comp_datos else ""
                                
                                if pos_esp_comp == pos_esp_rtp:
                                    if v_actual > vmax_posicion: vmax_posicion = v_actual
                                    # Solo sumamos si el compañero realmente llevó GPS en el partido (DIS > 0)
                                    if es_partido and m_actual > 0 and dis_actual > 0:
                                        partidos_posicion.append({
                                            "DIS_pm": dis_actual / m_actual,
                                            "HSR_pm": safe_float(d.get("DIS AI", d.get("HID >21", 0))) / m_actual,
                                            "SPR_pm": safe_float(d.get("Nº SPR", d.get("SPR >24", 0))) / m_actual,
                                            "ACC_pm": safe_float(d.get("ACC", d.get("ACC >3", 0))) / m_actual,
                                            "DCC_pm": safe_float(d.get("DCC", d.get("DCC >3", 0))) / m_actual,
                                        })
                
                # Crónica Pre-Lesión
                fecha_pre_lesion = (fecha_lesion_dt - timedelta(days=1)).strftime("%Y-%m-%d")
                ewma_pre = calcular_ewma_historico(st.session_state.sesiones, fecha_pre_lesion)
                cronica_pre_lesion = ewma_pre.get(jug_rtp, {}).get("EWMA CRÓNICA", 0)

                # 4. MOTOR DE PROGRESIÓN (EVALUACIÓN DE SESIONES DE ENTRENAMIENTO COMPLETADAS)
                sesiones_rehab = []
                for s in sesiones_ordenadas:
                    if s.get("tipo") != "Entrenamiento": continue # Ignoramos partidos
                    
                    s_dt = datetime.strptime(s["fecha"], "%Y-%m-%d").date()
                    if s_dt >= fecha_lesion_dt:
                        d_disp = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
                        if d_disp.get(limpiar_nombre(jug_rtp)) == "Readaptación":
                            datos_jug = next((d for d in s.get("datos_informe", []) if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jug_rtp)), None)
                            if datos_jug and safe_float(datos_jug.get("MIN", 0)) > 0:
                                sesiones_rehab.append({"fecha": s["fecha"], "datos": datos_jug})

                comp_fases = [0, 0, 0, 0]
                fase_actual = 0
                historial_progresion = []
                exposiciones_vmax = 0

                def get_dolor_siguiente_dia(fecha_actual, nombre_jug):
                    f_dt = datetime.strptime(fecha_actual, "%Y-%m-%d")
                    next_day_str = (f_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                    s_next = next((s for s in sesiones_ordenadas if s["fecha"] == next_day_str), None)
                    if s_next and s_next.get("datos_informe"):
                        for d in s_next["datos_informe"]:
                            if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(nombre_jug):
                                return safe_float(d.get("W_Dolor", 0))
                    return 0.0

                for i, ses in enumerate(sesiones_rehab):
                    ewma_dia = calcular_ewma_historico(st.session_state.sesiones, ses["fecha"])
                    ratio_ac = ewma_dia.get(jug_rtp, {}).get("RATIO A/C", 1.0)
                    carga_aguda_sesion = ewma_dia.get(jug_rtp, {}).get("EWMA AGUDA", 0)
                    dolor_post = get_dolor_siguiente_dia(ses["fecha"], jug_rtp)
                    
                    penalizado = False
                    motivos = []
                    
                    # Regla de Regresión por ACWR protegiendo cargas absolutas bajas
                    if ratio_ac > 1.5 and carga_aguda_sesion > 400:
                        penalizado = True
                        motivos.append(f"Ratio A/C Alto ({ratio_ac:.2f} con Carga > 400)")
                    elif ratio_ac > 1.5:
                        motivos.append(f"Ratio A/C {ratio_ac:.2f} (Ignorado por Carga Baja < 400)")

                    if dolor_post >= 4:
                        penalizado = True
                        motivos.append(f"Dolor Post-Sesión ({dolor_post:.0f}/7)")
                        
                    # Contador de Exposiciones a Alta Velocidad (Fase 3 y 4)
                    v_sesion = safe_float(ses["datos"].get("VMAX", ses["datos"].get("V_Max", 0)))
                    if fase_actual >= 2 and v_sesion >= (vmax_hist * 0.90):
                        exposiciones_vmax += 1

                    if penalizado:
                        req_fases[fase_actual] += 1
                        
                    comp_fases[fase_actual] += 1
                    
                    historial_progresion.append({
                        "Fecha": ses["fecha"],
                        "Fase Cursada": f"Fase {fase_actual + 1}",
                        "Ratio A/C": f"{ratio_ac:.2f}",
                        "Dolor D+1": f"{dolor_post:.0f}",
                        "V. Máx": f"{v_sesion:.1f} km/h",
                        "Estado": "🔴 Regresión (+1 Sesión req.)" if penalizado else "🟢 Superada",
                        "Motivo / Notas": " | ".join(motivos) if motivos else "-"
                    })
                    
                    # Avanzar fase si cumple requisitos
                    if comp_fases[fase_actual] >= req_fases[fase_actual] and fase_actual < 3:
                        fase_actual += 1

                # 5. RENDERIZADO VISUAL DE FASES
                st.markdown("---")
                st.markdown(f"#### 🧱 Estado de Progresión: **Fase {fase_actual + 1}**")
                
                c_p1, c_p2, c_p3, c_p4 = st.columns(4)
                fases_ui = [
                    (c_p1, "1. Analítico", "30-40% vol. tiempo"),
                    (c_p2, "2. Espacios Reducidos", "50-75% vol. ACC/DCC"),
                    (c_p3, "3. Espacios Amplios", "80-90% vol. DIS/HSR"),
                    (c_p4, "4. Entreno Completo", "100% de la sesión")
                ]
                
                for idx, (col, titulo, desc) in enumerate(fases_ui):
                    req_txt = str(req_fases[idx]) if idx < 3 else "Libre"
                    comp_txt = str(comp_fases[idx])
                    
                    if idx < fase_actual: 
                        bg, border = "#064e3b", "#10b981" # Completado
                        estado = "✅ COMPLETADO"
                    elif idx == fase_actual: 
                        bg, border = "#1e293b", "#3b82f6" # En curso
                        estado = f"🔄 EN CURSO ({comp_txt}/{req_txt})"
                    else: 
                        bg, border = "#0f172a", "#334155" # Pendiente
                        estado = f"⏳ PENDIENTE (0/{req_txt})"
                        
                    col.markdown(f"""
                    <div style="background-color: {bg}; border: 1px solid {border}; border-top: 4px solid {border}; padding: 10px; border-radius: 8px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.2);">
                        <p style="color: #f8fafc; font-size: 0.85rem; font-weight: 800; margin: 0 0 5px 0; text-transform: uppercase;">{titulo}</p>
                        <p style="color: #94a3b8; font-size: 0.7rem; margin: 0 0 10px 0;">{desc}</p>
                        <div style="background-color: rgba(0,0,0,0.2); padding: 4px; border-radius: 4px; text-align: center; font-size: 0.75rem; font-weight: 800; color: {border};">{estado}</div>
                    </div>
                    """, unsafe_allow_html=True)

                if historial_progresion:
                    with st.expander("🔍 Ver Historial de Sesiones de Readaptación"):
                        df_hist = pd.DataFrame(historial_progresion)
                        mostrar_tabla_moderna(df_hist.style.hide(axis="index").map(lambda x: "color: #ef4444;" if "🔴" in str(x) else "color: #10b981;", subset=["Estado"]))

                st.markdown("---")
                
                # 6. EVALUACIÓN AUTOMÁTICA DE CRITERIOS DE ALTA COMPETITIVA
                st.markdown("#### ✅ Criterios de Alta Competitiva (RTP)")
                
                hoy_str = str(date.today())
                _, _, lunes, domingo = obtener_rango_fechas_semana(hoy_str)
                
                # Filtramos estrictamente por Entrenamientos para evaluar volumen, HSR y VMax sin distorsión de partidos
                sesiones_micro = [
                    s for s in sesiones_ordenadas 
                    if str(lunes.date()) <= s['fecha'] <= str(domingo.date()) 
                    and s.get("tipo") == "Entrenamiento"
                ]
                
                # Extraer minutos medios del equipo para CRIT_1
                minutos_disponibles_eq = []
                for s in sesiones_micro:
                    if not s.get("informe_generado"): continue
                    disp = {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}
                    for d in s.get("datos_informe", []):
                        if disp.get(limpiar_nombre(d["JUGADOR"])) in ["Disponible", "Titular", "Suplente"]:
                            minutos_disponibles_eq.append(safe_float(d.get("MIN", 0)))
                            
                avg_min_eq = np.sum(minutos_disponibles_eq) / len(set([d["JUGADOR"] for s in sesiones_micro for d in s.get("datos_informe", []) if {limpiar_nombre(k): v for k, v in s.get("disponibilidad", {}).items()}.get(limpiar_nombre(d["JUGADOR"])) in ["Disponible", "Titular", "Suplente"]])) if minutos_disponibles_eq else 1

                # Extracción semanal del jugador
                min_jug = 0
                gps_jug_micro = {"DIS": 0, "HSR": 0, "SPR": 0, "ACC": 0, "DCC": 0}
                vmax_micro = 0
                dolores, fatigas = [], []
                
                for s in sesiones_micro:
                    if not s.get("informe_generado"): continue
                    d_jug = next((d for d in s.get("datos_informe", []) if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jug_rtp)), None)
                    if d_jug:
                        min_jug += safe_float(d_jug.get("MIN", 0))
                        gps_jug_micro["DIS"] += safe_float(d_jug.get("DIS", 0))
                        gps_jug_micro["HSR"] += safe_float(d_jug.get("DIS AI", d_jug.get("HID >21", 0)))
                        gps_jug_micro["SPR"] += safe_float(d_jug.get("Nº SPR", d_jug.get("SPR >24", 0)))
                        gps_jug_micro["ACC"] += safe_float(d_jug.get("ACC", d_jug.get("ACC >3", 0)))
                        gps_jug_micro["DCC"] += safe_float(d_jug.get("DCC", d_jug.get("DCC >3", 0)))
                        
                        v = safe_float(d_jug.get("VMAX", d_jug.get("V_Max", 0)))
                        if v > vmax_micro: vmax_micro = v
                        
                        dol = safe_float(d_jug.get("W_Dolor", 0))
                        fat = safe_float(d_jug.get("W_Fatiga", 0))
                        if dol > 0: dolores.append(dol)
                        if fat > 0: fatigas.append(fat)

                ewma_jug = calcular_ewma_historico(st.session_state.sesiones, hoy_str).get(jug_rtp, {"EWMA AGUDA": 0, "EWMA CRÓNICA": 0})
                
                # --- Demandas en 90min de Partido del Jugador (Con Fallback Posicional) ---
                gps_90 = {"DIS_pm": 0, "HSR_pm": 0, "SPR_pm": 0, "ACC_pm": 0, "DCC_pm": 0}
                usa_fallback = False
                
                if partidos_jug:
                    df_p = pd.DataFrame(partidos_jug)
                    gps_90 = (df_p.mean() * 90).to_dict()
                elif partidos_posicion:
                    df_p_pos = pd.DataFrame(partidos_posicion)
                    gps_90 = (df_p_pos.mean() * 90).to_dict()
                    usa_fallback = True
                    # Si nunca ha entrenado con GPS, hereda también el pico de velocidad de su posición
                    if vmax_hist == 0: vmax_hist = vmax_posicion 
                else:
                    gps_90 = {"DIS_pm": 9, "HSR_pm": 400, "SPR_pm": 10, "ACC_pm": 20, "DCC_pm": 20}
                    usa_fallback = True

                # --- Evaluación Booleana ---
                crit_1 = min_jug >= (avg_min_eq * 0.85)
                
                crit_2 = True
                falla_demanda = []
                for m_key in ["DIS", "HSR", "SPR", "ACC", "DCC"]:
                    val_90 = gps_90.get(f"{m_key}_pm", 0)
                    if gps_jug_micro[m_key] < val_90:
                        crit_2 = False
                        falla_demanda.append(m_key)
                        
                crit_3 = vmax_micro >= (vmax_hist * 0.90) if vmax_hist > 0 else False
                
                avg_dolor = np.mean(dolores) if dolores else 0
                avg_fatiga = np.mean(fatigas) if fatigas else 0
                crit_4 = (avg_dolor < 4 and avg_fatiga < 4) if (dolores and fatigas) else False
                
                # Fallback de crónica pre-lesión si es el inicio de temporada
                if cronica_pre_lesion == 0:
                    cronica_pre_lesion = ewma_jug["EWMA CRÓNICA"]
                crit_5 = (ewma_jug["EWMA CRÓNICA"] >= cronica_pre_lesion * 0.9)

                req_exposiciones = 2 if dias_rtp > 7 else 1
                crit_6 = exposiciones_vmax >= req_exposiciones

                # --- RENDERIZADO DE LOS CRITERIOS AUTOMÁTICOS ---
                def render_criterio(cumple, titulo, detalle):
                    icon = "✅" if cumple else "❌"
                    color = "#10b981" if cumple else "#ef4444"
                    bg = "rgba(16, 185, 129, 0.1)" if cumple else "rgba(239, 68, 68, 0.1)"
                    st.markdown(f"""
                    <div style="background-color: {bg}; border-left: 4px solid {color}; padding: 12px; margin-bottom: 8px; border-radius: 6px; display: flex; align-items: center;">
                        <span style="font-size: 1.2rem; margin-right: 12px;">{icon}</span>
                        <div>
                            <strong style="color: #f8fafc; font-size: 0.9rem; display: block;">{titulo}</strong>
                            <span style="color: #94a3b8; font-size: 0.8rem;">{detalle}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                c_auto1, c_auto2 = st.columns(2)
                with c_auto1:
                    render_criterio(crit_1, "Microciclo Completo (>85% Minutos)", f"Completados {min_jug:.0f}' vs {avg_min_eq*0.85:.0f}' requeridos (Media Equipo {avg_min_eq:.0f}')")
                    render_criterio(crit_3, "Velocidad Máxima Recuperada (>90%)", f"Alcanzados {vmax_micro:.1f} km/h vs {vmax_hist*0.90:.1f} km/h requeridos (VMax Histórica: {vmax_hist:.1f})")
                    render_criterio(crit_5, "Tolerancia Crónica Individual (>90% Pre-Lesión)", f"Crónica Actual: {ewma_jug['EWMA CRÓNICA']:.0f} UA | Crónica Pre-lesión: {cronica_pre_lesion:.0f} UA")
                
                with c_auto2:
                    if usa_fallback:
                        fallos_txt = f"Falla en: {', '.join(falla_demanda)}" if not crit_2 else "Métricas superan estándar."
                        render_criterio(crit_2, "Demandas de Partido Alcanzadas", f"Volumen semanal >= 90' (Heredadas de su posición: {pos_esp_rtp}). {fallos_txt}")
                    else:
                        fallos_txt = f"Falla en: {', '.join(falla_demanda)}" if not crit_2 else "Todas las métricas superan su media."
                        render_criterio(crit_2, "Demandas de Partido Alcanzadas", f"Volumen semanal >= a 90' de partido propio. {fallos_txt}")
                        
                    render_criterio(crit_4, "Dolor y Fatiga bajo control (< 4/7)", f"Media Semanal -> Dolor: {avg_dolor:.1f} | Fatiga: {avg_fatiga:.1f}")
                    render_criterio(crit_6, f"Exposiciones Vmax (>90%) en Fase 3/4", f"Conseguidas {exposiciones_vmax} exposiciones de {req_exposiciones} requeridas.")

                st.markdown("---")
                
                # 7. EVALUACIÓN MANUAL (TESTS ESPECÍFICOS)
                st.markdown("#### 🧠 Criterios Médicos y Neuromusculares (Inputs)")
                c_man1, c_man2 = st.columns(2)
                
                with c_man1:
                    with st.container(border=True):
                        st.markdown("**Cuestionario I-PRRS (Confianza RTP)**")
                        st.caption("Puntuación de 0 a 60. El estándar de élite exige superar los 50 puntos (aprox. 8.3/10) para asegurar la ausencia de kinesiofobia.")
                        punt_cuest = st.number_input("Puntuación (sobre 60):", min_value=0, max_value=60, value=0)
                        if punt_cuest >= 50:
                            st.success(f"✅ Apto ({punt_cuest}/60)")
                        elif punt_cuest > 0:
                            st.error(f"❌ No Apto ({punt_cuest}/60) - Requiere consolidación psicológica")
                            
                with c_man2:
                    with st.container(border=True):
                        st.markdown("**Test CMJ en Fatiga (Simetría)**")
                        
                        vals_jug = [v for v in st.session_state.get('val_rom', []) if limpiar_nombre(v.get('jugador')) == limpiar_nombre(jug_rtp)]
                        cmj_base_d, cmj_base_i = 0, 0
                        asim_base = 0
                        if vals_jug:
                            v_latest = sorted(vals_jug, key=lambda x: x.get('fecha', ''))[-1]
                            cmj_base_d = safe_float(v_latest.get('cmj_uni_d', 0))
                            cmj_base_i = safe_float(v_latest.get('cmj_uni_i', 0))
                            if max(cmj_base_d, cmj_base_i) > 0:
                                asim_base = (min(cmj_base_d, cmj_base_i) / max(cmj_base_d, cmj_base_i)) * 100
                                
                        st.caption(f"Baseline Previo: DER {cmj_base_d:.1f}cm | IZQ {cmj_base_i:.1f}cm (LSI: {asim_base:.1f}%)")
                        
                        cj1, cj2 = st.columns(2)
                        cmj_d_act = cj1.number_input("CMJ Der. Actual (cm):", min_value=0.0, step=0.5)
                        cmj_i_act = cj2.number_input("CMJ Izq. Actual (cm):", min_value=0.0, step=0.5)
                        
                        if cmj_d_act > 0 and cmj_i_act > 0:
                            lsi_act = (min(cmj_d_act, cmj_i_act) / max(cmj_d_act, cmj_i_act)) * 100
                            pct_base_d = (cmj_d_act / cmj_base_d * 100) if cmj_base_d > 0 else 100
                            pct_base_i = (cmj_i_act / cmj_base_i * 100) if cmj_base_i > 0 else 100
                            
                            crit_lsi = lsi_act >= 90
                            crit_recup = pct_base_d >= 90 and pct_base_i >= 90
                            
                            if crit_lsi and crit_recup:
                                st.success(f"✅ Apto. LSI: {lsi_act:.1f}% | Recup. Fuerza: {min(pct_base_d, pct_base_i):.1f}%")
                            else:
                                st.error(f"❌ Falla criterio. LSI: {lsi_act:.1f}% | Recup. Fuerza: {min(pct_base_d, pct_base_i):.1f}%")
