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

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("Por favor, inicia sesión y selecciona un equipo primero.")
    st.stop()

    st.subheader("⚖️ Antropometría y Composición Corporal")
    
    tab_antro_res, tab_antro_jug, tab_antro_up = st.tabs(["📊 Resumen Analítico", "👤 Jugadores", "📂 Cargar Datos"])
    
    antro_data = st.session_state.get("antropometria", [])
    
    with tab_antro_res:
        if not antro_data:
            st.info("Aún no hay datos antropométricos registrados. Sube tu Excel en la pestaña 'Cargar Datos'.")
        else:
            df_antro = pd.DataFrame(antro_data)
            
            df_antro['fecha_dt'] = pd.to_datetime(df_antro['fecha'])
            df_antro['Mes_Num'] = df_antro['fecha_dt'].dt.month
            df_antro['Mes'] = df_antro['Mes_Num'].map(meses_esp)
            
            df_antro['Suma_Pliegues'] = df_antro['P_Tricipital'] + df_antro['P_Subescapular'] + df_antro['P_Suprailiaco'] + df_antro['P_Abdominal']
            df_antro['% Graso'] = (df_antro['Suma_Pliegues'] * 0.1537) + 5.783
            df_antro['Kg Magros'] = df_antro['Peso'] - (df_antro['Peso'] * (df_antro['% Graso'] / 100))
            
            dict_pos = {j['JUGADOR']: j['POS'] for j in st.session_state.plantilla}
            df_antro['POS'] = df_antro['jugador'].map(lambda x: dict_pos.get(x, "N/A"))

            st.markdown("#### 🔍 Filtros Antropométricos")
            ca1, ca2, ca3 = st.columns(3)
            
            jugs_unicos = ["TODOS"] + sorted(df_antro['jugador'].unique())
            filtro_jug = ca1.selectbox("Jugador:", jugs_unicos, key="ant_jug")
            
            filtro_pos = ca2.selectbox("Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], key="ant_pos")
            
            meses_unicos = ["TODOS Anual"] + list(df_antro['Mes'].dropna().unique())
            filtro_mes = ca3.selectbox("Mes:", meses_unicos, key="ant_mes")
            
            df_filt = df_antro.copy()
            if filtro_jug != "TODOS": df_filt = df_filt[df_filt['jugador'] == filtro_jug]
            if filtro_pos != "TODOS": df_filt = df_filt[df_filt['POS'] == filtro_pos]
            if filtro_mes != "TODOS Anual": df_filt = df_filt[df_filt['Mes'] == filtro_mes]
            
            if df_filt.empty:
                st.warning("No hay datos para esta combinación.")
            else:
                kpi_peso = df_filt['Peso'].mean()
                kpi_grasa = df_filt['% Graso'].mean()
                kpi_magro = df_filt['Kg Magros'].mean()
                
                st.markdown("#### 🎯 Promedios del Filtro")
                k1, k2, k3 = st.columns(3)
                k1.metric("Peso Medio", f"{kpi_peso:.1f} kg")
                k2.metric("% Graso Medio (Yuhasz)", f"{kpi_grasa:.2f} %")
                k3.metric("Masa Magra Media", f"{kpi_magro:.1f} kg")
                
                st.markdown("---")
                st.markdown("#### 📈 Evolución Mensual")
                
                meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
                df_evo = df_filt.groupby('Mes')[['Peso', '% Graso', 'Kg Magros']].mean().reindex(meses_temporada).reset_index()
                
                fig_evo = go.Figure()
                fig_evo.add_trace(go.Bar(x=df_evo['Mes'], y=df_evo['Peso'], name="Peso (kg)", marker_color='#00b4d8'))
                fig_evo.add_trace(go.Scatter(x=df_evo['Mes'], y=df_evo['% Graso'], name="% Graso", yaxis="y2", mode="lines+markers", line=dict(color="#ff4b4b", width=3)))
                fig_evo.update_layout(
                    title="Evolución: Peso vs % Graso", 
                    yaxis_title="Peso (kg)", 
                    yaxis2=dict(title="% Grasa", overlaying="y", side="right"),
                    xaxis=dict(categoryorder='array', categoryarray=meses_temporada)
                )
                
                st.plotly_chart(fig_evo, use_container_width=True, key="antro_resumen_evo")

    with tab_antro_jug:
        if not st.session_state.plantilla:
            st.info("Primero debes añadir jugadores en la sección 'Plantilla'.")
        elif not antro_data:
            st.info("Sube primero un archivo Excel con pesajes en la pestaña 'Cargar Datos'.")
        else:
            nombres_plantilla = sorted([j["JUGADOR"] for j in st.session_state.plantilla])
            jugador_seleccionado = st.selectbox("Selecciona un jugador para ver su perfil antropométrico:", nombres_plantilla)
            
            df_antro = pd.DataFrame(antro_data)
            df_antro['fecha_dt'] = pd.to_datetime(df_antro['fecha'])
            df_jug_antro = df_antro[df_antro['jugador'] == jugador_seleccionado].sort_values('fecha_dt', ascending=False)
            
            if df_jug_antro.empty:
                st.warning(f"No hay registros antropométricos para {jugador_seleccionado}.")
            else:
                df_jug_antro['Suma_Pliegues'] = df_jug_antro['P_Tricipital'] + df_jug_antro['P_Subescapular'] + df_jug_antro['P_Suprailiaco'] + df_jug_antro['P_Abdominal']
                df_jug_antro['% Graso'] = (df_jug_antro['Suma_Pliegues'] * 0.1537) + 5.783
                df_jug_antro['Kg Magros'] = df_jug_antro['Peso'] - (df_jug_antro['Peso'] * (df_jug_antro['% Graso'] / 100))
                
                ultimo_pesaje = df_jug_antro.iloc[0]
                
                st.markdown(f"#### ⚖️ Pesaje Actual ({ultimo_pesaje['fecha']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Peso", f"{ultimo_pesaje['Peso']:.1f} kg")
                c2.metric("% Graso (Yuhasz)", f"{ultimo_pesaje['% Graso']:.2f} %")
                c3.metric("Masa Magra", f"{ultimo_pesaje['Kg Magros']:.1f} kg")
                c4.metric("∑ 4 Pliegues", f"{ultimo_pesaje['Suma_Pliegues']:.1f} mm")
                
                st.markdown("#### 📏 Asimetrías Perimetrales (Actual)")
                st.caption("Valores en cm. Un número positivo indica que el lado Derecho es mayor; negativo, el Izquierdo.")
                ca1, ca2, ca3 = st.columns(3)
                dif_muslo = ultimo_pesaje['Per_Muslo_D'] - ultimo_pesaje['Per_Muslo_I']
                dif_pierna = ultimo_pesaje['Per_Pierna_D'] - ultimo_pesaje['Per_Pierna_I']
                dif_biceps = ultimo_pesaje['Per_Biceps_D'] - ultimo_pesaje['Per_Biceps_I']
                
                ca1.metric("Muslo (D - I)", f"{dif_muslo:+.1f} cm")
                ca2.metric("Pierna (D - I)", f"{dif_pierna:+.1f} cm")
                ca3.metric("Bíceps (D - I)", f"{dif_biceps:+.1f} cm")
                
                st.markdown("---")
                st.markdown("#### 📈 Evolución Histórica")
                
                df_jug_antro['Mes_Num'] = df_jug_antro['fecha_dt'].dt.month
                df_jug_antro['Mes'] = df_jug_antro['Mes_Num'].map(meses_esp)
                
                meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
                df_evo_jug = df_jug_antro.groupby('Mes')[['Peso', '% Graso']].mean().reindex(meses_temporada).reset_index()
                
                fig_evo_jug = go.Figure()
                fig_evo_jug.add_trace(go.Bar(x=df_evo_jug['Mes'], y=df_evo_jug['Peso'], name="Peso (kg)", marker_color='#00b4d8'))
                fig_evo_jug.add_trace(go.Scatter(x=df_evo_jug['Mes'], y=df_evo_jug['% Graso'], name="% Graso", yaxis="y2", mode="lines+markers", line=dict(color="#ff4b4b", width=3)))
                fig_evo_jug.update_layout(
                    title=f"Evolución: {jugador_seleccionado}", 
                    yaxis_title="Peso (kg)", 
                    yaxis2=dict(title="% Grasa", overlaying="y", side="right"),
                    xaxis=dict(categoryorder='array', categoryarray=meses_temporada)
                )
                st.plotly_chart(fig_evo_jug, use_container_width=True, key=f"antro_jug_evo_{jugador_seleccionado}")
                
                st.markdown("#### 📋 Historial Completo")
                columnas_mostrar = ['fecha', 'Peso', '% Graso', 'Kg Magros', 'Suma_Pliegues', 'Per_Pecho', 'Per_Cintura', 'Per_Cadera']
                mostrar_tabla_moderna(df_jug_antro[columnas_mostrar].style.hide(axis="index").format(precision=2))

    with tab_antro_up:
        st.info("Prepara un archivo Excel (.xlsx) con los pesajes. El sistema leerá automáticamente las 15 primeras columnas en el orden exacto indicado abajo.")
        st.markdown("""
        **Orden estricto de columnas (La fila 1 debe ser para los títulos):**
        1. Nombre del jugador
        2. Peso
        3. Pliegue tricipital
        4. Pliegue subescapular
        5. Pliegue suprailíaco
        6. Pliegue abdominal
        7. Perímetro pecho
        8. Perímetro cintura
        9. Perímetro cadera
        10. Perímetro muslo derecho
        11. Perímetro muslo izquierdo
        12. Perímetro pierna derecha
        13. Perímetro pierna izquierda
        14. Perímetro bíceps derecho
        15. Perímetro bíceps izquierdo
        """)
        
        c_up1, c_up2 = st.columns([1, 2])
        with c_up1:
            fecha_pesaje = st.date_input("Fecha del pesaje:", date.today())
        with c_up2:
            archivo_antro = st.file_uploader("Sube el Excel mensual de antropometría:", type=["xlsx"])
        
        if st.button("Procesar Archivo Antropométrico") and archivo_antro is not None:
            try:
                df_up = pd.read_excel(archivo_antro)
                
                if len(df_up.columns) < 15:
                    st.error("❌ El archivo Excel no tiene las 15 columnas necesarias. Revisa la plantilla.")
                else:
                    registros_nuevos = 0
                    for idx, row in df_up.iterrows():
                        nombre_crudo = str(row.iloc[0]).strip()
                        if pd.isna(row.iloc[0]) or nombre_crudo == "nan" or nombre_crudo == "":
                            continue
                            
                        jug_nombre_limpio = limpiar_nombre(nombre_crudo)
                        match_jugador = next((p["JUGADOR"] for p in st.session_state.plantilla if limpiar_nombre(p["JUGADOR"]) == jug_nombre_limpio), None)
                        
                        nombre_final = match_jugador if match_jugador else nombre_crudo
                        
                        nuevo_pesaje = {
                            "fecha": str(fecha_pesaje),
                            "jugador": nombre_final,
                            "Peso": float(row.iloc[1]) if not pd.isna(row.iloc[1]) else 0.0,
                            "P_Tricipital": float(row.iloc[2]) if not pd.isna(row.iloc[2]) else 0.0,
                            "P_Subescapular": float(row.iloc[3]) if not pd.isna(row.iloc[3]) else 0.0,
                            "P_Suprailiaco": float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 0.0,
                            "P_Abdominal": float(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0.0,
                            "Per_Pecho": float(row.iloc[6]) if not pd.isna(row.iloc[6]) else 0.0,
                            "Per_Cintura": float(row.iloc[7]) if not pd.isna(row.iloc[7]) else 0.0,
                            "Per_Cadera": float(row.iloc[8]) if not pd.isna(row.iloc[8]) else 0.0,
                            "Per_Muslo_D": float(row.iloc[9]) if not pd.isna(row.iloc[9]) else 0.0,
                            "Per_Muslo_I": float(row.iloc[10]) if not pd.isna(row.iloc[10]) else 0.0,
                            "Per_Pierna_D": float(row.iloc[11]) if not pd.isna(row.iloc[11]) else 0.0,
                            "Per_Pierna_I": float(row.iloc[12]) if not pd.isna(row.iloc[12]) else 0.0,
                            "Per_Biceps_D": float(row.iloc[13]) if not pd.isna(row.iloc[13]) else 0.0,
                            "Per_Biceps_I": float(row.iloc[14]) if not pd.isna(row.iloc[14]) else 0.0,
                        }
                        st.session_state.antropometria.append(nuevo_pesaje)
                        registros_nuevos += 1
                        
                    guardar_datos()
                    st.success(f"✅ ¡{registros_nuevos} pesajes procesados e integrados con éxito!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al leer el archivo. Asegúrate de que el formato es correcto. Detalle técnico: {e}")
