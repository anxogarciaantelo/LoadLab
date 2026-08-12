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
    
st.subheader("🚑 Lesiones")

tab_les_res, tab_les_list = st.tabs(["📊 Resumen", "📋 Listado de Lesiones"])

les_data = st.session_state.get("lesiones", [])
if not les_data:
    with tab_les_res: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
    with tab_les_list: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
else:
    df_les = pd.DataFrame(les_data)
    df_les['Mes_Num'] = pd.to_datetime(df_les['id_sesion']).dt.month
    df_les['Mes'] = df_les['Mes_Num'].map(meses_esp)
    df_les['Gravedad'] = df_les['dias_baja'].apply(categorizar_duracion)
    
    with tab_les_res:
        st.markdown("#### 🔍 Filtros Epidemiológicos")
        cf1, cf2, cf3 = st.columns(3)
        
        meses_unicos = ["TODOS"] + list(df_les['Mes'].dropna().unique())
        filtro_mes = cf1.selectbox("Filtrar por Mes:", meses_unicos)
        
        filtro_tipo_ses = cf2.selectbox("Filtrar por Sesión:", ["TODOS", "Entrenamiento", "Partido"])
        
        jugs_unicos = ["TODOS"] + sorted([j["JUGADOR"] for j in st.session_state.plantilla])
        filtro_jugador = cf3.selectbox("Filtrar por Jugador:", jugs_unicos)
        
        df_filtrado = df_les.copy()
        if filtro_mes != "TODOS": df_filtrado = df_filtrado[df_filtrado['Mes'] == filtro_mes]
        if filtro_tipo_ses != "TODOS": df_filtrado = df_filtrado[df_filtrado['tipo_sesion'] == filtro_tipo_ses]
        if filtro_jugador != "TODOS": df_filtrado = df_filtrado[df_filtrado['jugador'] == filtro_jugador]
        
        if df_filtrado.empty:
            st.warning("No hay lesiones que coincidan con los filtros aplicados para este jugador/periodo.")
        else:
            total_lesiones = len(df_filtrado)
            total_dias = int(df_filtrado['dias_baja'].fillna(0).sum())
            promedio_dias = total_dias / total_lesiones if total_lesiones > 0 else 0
            
            horas_totales = 0
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    if filtro_mes != "TODOS" and meses_esp[datetime.strptime(s["fecha"], "%Y-%m-%d").month] != filtro_mes: continue
                    es_partido_s = "Partido" in s["tipo"]
                    if filtro_tipo_ses == "Entrenamiento" and es_partido_s: continue
                    if filtro_tipo_ses == "Partido" and not es_partido_s: continue
                    
                    for d in s["datos_informe"]:
                        if filtro_jugador == "TODOS" or d["JUGADOR"] == filtro_jugador:
                            horas_totales += float(d.get("MIN", 0)) / 60.0

            incidencia = (total_lesiones / horas_totales * 1000) if horas_totales > 0 else 0

            st.markdown("#### 🎯 Métricas Globales")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total de Lesiones", total_lesiones)
            k2.metric("Total Días de Baja", f"{total_dias} días")
            k3.metric("Promedio de Baja", f"{promedio_dias:.1f} días / lesión")
            k4.metric("Incidencia (/1000h)", f"{incidencia:.1f}", help="Fórmula: (Total Lesiones / Horas Totales Exposición) * 1000. \nCalculado usando los minutos GPS/RPE.")
            
            st.markdown("---")
            st.markdown("#### 📈 Desglose Estadístico")
            
            cg1, cg2 = st.columns(2)
            with cg1:
                fig_dur = px.histogram(df_filtrado, x='Gravedad', title="1. Duración de la Lesión", color='Gravedad', category_orders={"Gravedad": ["Mínima (1-3d)", "Leve (4-7d)", "Moderada (8-28d)", "Grave (>28d)", "Activa"]})
                fig_dur.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                st.plotly_chart(fig_dur, use_container_width=True, key="les_hist_dur")
            with cg2:
                fig_tipo = px.histogram(df_filtrado, x='tipo', title="2. Tipo de Lesión", color='tipo')
                fig_tipo.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                st.plotly_chart(fig_tipo, use_container_width=True, key="les_hist_tipo")
                
            cg3, cg4 = st.columns(2)
            with cg3:
                fig_zona = px.histogram(df_filtrado, x='zona', title="3. Zona Afectada", color='zona')
                fig_zona.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                st.plotly_chart(fig_zona, use_container_width=True, key="les_hist_zona")
            with cg4:
                fig_lat = px.histogram(df_filtrado, x='lateralidad', title="4. Lateralidad Lesional", color='lateralidad')
                fig_lat.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                st.plotly_chart(fig_lat, use_container_width=True, key="les_hist_lat")
                
            cg5, cg6 = st.columns(2)
            with cg5:
                conteo_recidiva = df_filtrado['recidiva'].value_counts().reset_index()
                fig_rec = px.pie(conteo_recidiva, names='recidiva', values='count', title="5. Índice de Recidiva", hole=0.4)
                st.plotly_chart(fig_rec, use_container_width=True, key="les_pie_rec")
            with cg6:
                conteo_sup = df_filtrado['cesped'].value_counts().reset_index()
                fig_sup = px.pie(conteo_sup, names='cesped', values='count', title="6. Superficie de Juego", hole=0.4)
                st.plotly_chart(fig_sup, use_container_width=True, key="les_pie_sup")

    with tab_les_list:
        cols_mostrar = ["id_sesion", "tipo_sesion", "jugador", "tipo", "zona", "lado", "lateralidad", "contacto", "cesped", "recidiva", "estado", "dias_baja", "comentarios"]
        df_mostrar = df_les[cols_mostrar].rename(columns={
            "id_sesion": "Fecha", "tipo_sesion": "Sesión", "jugador": "Jugador", "tipo": "Tipo", 
            "zona": "Zona", "lado": "Lado", "lateralidad": "Lateralidad", "contacto": "Contacto", 
            "cesped": "Superficie", "recidiva": "Recidiva", "estado": "Estado", "dias_baja": "Días Baja", "comentarios": "Comentarios"
        })
        mostrar_tabla_moderna(df_mostrar.style.hide(axis="index"))
        
        st.markdown("---")
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
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
                        guardar_datos()
                        st.success(f"Alta médica procesada. {les_obj['jugador']} estuvo {dias_baja_input} días de baja.")
                        st.rerun()

        with col_m2:
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
                    guardar_datos()
                    st.success("¡Comentario actualizado correctamente!")
                    st.rerun()

