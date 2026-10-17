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
                with k3: render_kpi_elite("Días Baja / Les", f"{promedio_dias:.1f}", color_borde="#8b5cf6")
                with k4: render_kpi_elite("Incidencia (/1000h)", f"{incidencia:.1f}", color_borde="#ef4444")
                with k5: render_kpi_elite("Burden (/1000h)", f"{burden:.0f}", color_borde="#ef4444")
                
                st.caption("ℹ️ **Valores de Referencia (Fútbol Élite):** Incidencia: 6-9 lesiones por 1000h | Burden: 100-150 días de baja por 1000h")

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
                    disp_jug = s.get("disponibilidad", {}).get(les_obj["jugador"], "")
                    if disp_jug in ["Disponible", "Titular", "Suplente"]:
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
                    for L in st.session_state.lesiones:
                        if L["id_sesion"] == les_obj["id_sesion"] and L["jugador"] == les_obj["jugador"] and L["tipo"] == les_obj["tipo"]:
                            L["estado"] = "Recuperado"
                            L["dias_baja"] = dias_baja_input
                            break
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
        
        # Inyección de tabla interactiva (permite click en cabeceras para ordenar y búsqueda global con ctrl+f)
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
                        
                        guardar_datos(modulo="lesiones")
                        st.success("¡Registro de lesión eliminado correctamente!")
                        st.rerun()
            else:
                st.info("No hay lesiones en el historial para eliminar.")

    # ==========================================
    # PESTAÑA 4: PROTOCOLO RTP
    # ==========================================
    with tab_rtp:
        st.markdown("#### 🏃‍♂️ Gestión de Return To Play (RTP)")
        st.caption("Sistema de progresión estructurada basado en los 4 pasos, duraciones mínimas y criterios de alta competitiva.")

        # Seleccionar lesión
        lesiones_rtp = sorted(df_les.to_dict('records'), key=lambda x: x.get('id_sesion', ''), reverse=True)
        opciones_rtp = [f"{l['id_sesion']} | {l['jugador']} - {l['tipo']} ({l['estado']})" for l in lesiones_rtp]
        rtp_sel_idx = st.selectbox("Selecciona la lesión para evaluar su RTP:", range(len(lesiones_rtp)), format_func=lambda x: opciones_rtp[x])
        
        l_rtp = lesiones_rtp[rtp_sel_idx]
        jug_rtp = l_rtp['jugador']
        
        # Calcular los días exactos para determinar la gravedad
        if l_rtp['estado'] == 'Activa':
            dias_rtp = max((date.today() - datetime.strptime(l_rtp['id_sesion'], "%Y-%m-%d").date()).days, 0)
        else:
            dias_rtp = int(safe_float(l_rtp.get('dias_baja', 0)))
        
        # 1. Determinar Gravedad y Sesiones Mínimas
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

        # Aplicar regla de penalización por tejido o recidiva
        mod_txt = ""
        if l_rtp.get('recidiva') == "Sí" or l_rtp.get('tipo') == "Tendinosa":
            s1 += 1; s2 += 1; s3 += 1
            mod_txt = "⚠️ Se ha sumado **+1 sesión obligatoria por fase** debido al protocolo de seguridad (Lesión Tendinosa o Recidiva)."

        st.markdown(f"**Deportista:** {jug_rtp} | **Gravedad Base:** {grav_rtp} ({dias_rtp} días de baja)")
        if mod_txt: st.warning(mod_txt)
        
        st.markdown("---")
        st.markdown("##### 🧱 Fases de Progresión (Sesiones Mínimas Requeridas)")
        
        # Tarjetas de los 4 Pasos
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        c_p1.info(f"**Paso 1: Analítico / Comodín**\n\nMin. Sesiones: **{s1}**\n\n*30-40% del tiempo total.*")
        c_p2.info(f"**Paso 2: Espacios Reducidos**\n\nMin. Sesiones: **{s2}**\n\n*50-75% vol. ACC/DCC.*")
        c_p3.info(f"**Paso 3: Espacios Amplios**\n\nMin. Sesiones: **{s3}**\n\n*80-90% HSR / Dist. Total.*")
        c_p4.success(f"**Paso 4: Entreno Completo**\n\nMin. Sesiones: **Libre**\n\n*100% de la sesión.*")

        st.markdown("---")
        st.markdown("##### 🚨 Regla de No Progresión / Regresión")
        st.error("Detener avance o retroceder de fase si se cumple alguna de estas banderas rojas post-entrenamiento:\n- **Dolor > 3/10 (EVA)** o inflamación visible en las 12-24 horas posteriores.\n- **Ratio A/C > 1.5** posterior a la sesión de campo.")

        st.markdown("---")
        st.markdown("##### ✅ Criterios Finales de RTP Competitivo (Checklist)")
        
        # Extracción inteligente de métricas actuales del jugador
        ewma_actual = calcular_ewma_historico(st.session_state.sesiones, str(date.today()))
        j_ewma = ewma_actual.get(jug_rtp, {"RATIO A/C": 0})
        ratio_actual = j_ewma.get("RATIO A/C", 0)
        
        vals_jug = [v for v in st.session_state.get('val_rom', []) if v.get('jugador') == jug_rtp]
        asim_cmj_txt = "Sin datos de salto registrados"
        if vals_jug:
            v_latest = sorted(vals_jug, key=lambda x: x.get('fecha', ''))[-1]
            d, i = safe_float(v_latest.get('cmj_uni_d', 0)), safe_float(v_latest.get('cmj_uni_i', 0))
            if max(d, i) > 0:
                lsi = (min(d, i) / max(d, i)) * 100
                asim_cmj_txt = f"{lsi:.1f}% LSI en última prueba"
                
        # Interfaz del Checklist
        st.checkbox("Igualar (>100%) las demandas individuales de partido o de posición (>90%) en microciclo (Dist, HSR, ACC/DCC, Vmax).")
        st.checkbox("Completar una semana al 100% del volumen grupal.")
        st.checkbox(f"Mantenimiento de la simetría (LSI > 90%) en CMJ post MD-3/MD-4. *(Auto-detectado: {asim_cmj_txt})*")
        st.checkbox("Sin dolor entre las 12 y 48 horas tras los entrenamientos.")
        st.checkbox("Cuestionario subjetivo de RTP apto.")
        st.checkbox(f"Igualar EWMA Aguda y Crónica de la media del equipo (>90%). *(Actual Ratio A/C: {ratio_actual:.2f})*")
        st.checkbox("Alcanzar el 90% del 1RM en Sentadilla.")
