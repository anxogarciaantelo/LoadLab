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
            # 1. Ignorar ceros convirtiéndolos a NaN para que las medias sean reales
            df_filt_clean = df_filt.replace({'Suma_Pliegues': 0, 'Per_Pecho': 0, 'Per_Cintura': 0, 'Per_Cadera': 0, 'Per_Muslo_D': 0, 'Per_Muslo_I': 0, 'Per_Pierna_D': 0, 'Per_Pierna_I': 0, 'Per_Biceps_D': 0, 'Per_Biceps_I': 0}, np.nan)

            kpi_peso = df_filt_clean['Peso'].mean()
            kpi_grasa = df_filt_clean['% Graso'].mean()
            kpi_magro = df_filt_clean['Kg Magros'].mean()
            kpi_pliegues = df_filt_clean['Suma_Pliegues'].mean()
            
            # Promedios de perímetros (ignorando ceros)
            prom_pecho = df_filt_clean['Per_Pecho'].mean()
            prom_cintura = df_filt_clean['Per_Cintura'].mean()
            prom_cadera = df_filt_clean['Per_Cadera'].mean()
            prom_muslo_d = df_filt_clean['Per_Muslo_D'].mean()
            prom_muslo_i = df_filt_clean['Per_Muslo_I'].mean()
            prom_pierna_d = df_filt_clean['Per_Pierna_D'].mean()
            prom_pierna_i = df_filt_clean['Per_Pierna_I'].mean()
            prom_biceps_d = df_filt_clean['Per_Biceps_D'].mean()
            prom_biceps_i = df_filt_clean['Per_Biceps_I'].mean()
            
            prom_muslo = df_filt_clean[['Per_Muslo_D', 'Per_Muslo_I']].mean().mean()
            prom_pierna = df_filt_clean[['Per_Pierna_D', 'Per_Pierna_I']].mean().mean()
            prom_biceps = df_filt_clean[['Per_Biceps_D', 'Per_Biceps_I']].mean().mean()
            
            st.markdown("#### 🎯 Promedios del Filtro")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Peso Medio", f"{kpi_peso:.1f} kg" if pd.notna(kpi_peso) else "0.0 kg")
            k2.metric("% Graso Medio (Yuhasz)", f"{kpi_grasa:.2f} %" if pd.notna(kpi_grasa) else "0.00 %")
            k3.metric("Masa Magra Media", f"{kpi_magro:.1f} kg" if pd.notna(kpi_magro) else "0.0 kg")
            k4.metric("∑ Pliegues Medio", f"{kpi_pliegues:.1f} mm" if pd.notna(kpi_pliegues) else "0.0 mm")
            
            st.markdown("##### 📏 Promedios de Perímetros (excluyendo sin medición)")
            p1, p2, p3, p4, p5, p6 = st.columns(6)
            p1.metric("Pecho", f"{prom_pecho:.1f} cm" if pd.notna(prom_pecho) else "-")
            p2.metric("Cintura", f"{prom_cintura:.1f} cm" if pd.notna(prom_cintura) else "-")
            p3.metric("Cadera", f"{prom_cadera:.1f} cm" if pd.notna(prom_cadera) else "-")
            p4.metric("Muslo", f"{prom_muslo:.1f} cm" if pd.notna(prom_muslo) else "-")
            p5.metric("Pierna", f"{prom_pierna:.1f} cm" if pd.notna(prom_pierna) else "-")
            p6.metric("Bíceps", f"{prom_biceps:.1f} cm" if pd.notna(prom_biceps) else "-")
            
            st.markdown("##### ⚖️ Asimetrías Medias (Derecha - Izquierda)")
            def calc_asim_str(d, i):
                if pd.isna(d) or pd.isna(i) or d==0 or i==0: return "-"
                dif = d - i
                pct = (abs(dif) / max(d, i)) * 100
                return f"{dif:+.1f} cm ({pct:.1f}%)"

            a1, a2, a3 = st.columns(3)
            a1.metric("Muslo (D - I)", calc_asim_str(prom_muslo_d, prom_muslo_i))
            a2.metric("Pierna (D - I)", calc_asim_str(prom_pierna_d, prom_pierna_i))
            a3.metric("Bíceps (D - I)", calc_asim_str(prom_biceps_d, prom_biceps_i))
            
            st.markdown("---")
            st.markdown("#### 📈 Evolución Mensual: Peso y % Graso")
            
            meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
            df_evo = df_filt_clean.groupby('Mes')[['Peso', '% Graso', 'Kg Magros']].mean().reindex(meses_temporada).reset_index()
            
            cg_peso, cg_grasa = st.columns(2)
            with cg_peso:
                fig_peso = px.bar(df_evo, x='Mes', y='Peso', title="Evolución Peso (kg)", color_discrete_sequence=['#00b4d8'])
                fig_peso.update_yaxes(range=[60, 100])
                fig_peso.update_xaxes(categoryorder='array', categoryarray=meses_temporada)
                st.plotly_chart(fig_peso, use_container_width=True, key="res_peso")
            
            with cg_grasa:
                fig_grasa = px.bar(df_evo, x='Mes', y='% Graso', title="Evolución % Graso", color_discrete_sequence=['#ff4b4b'])
                fig_grasa.update_yaxes(range=[8, 13])
                fig_grasa.update_xaxes(categoryorder='array', categoryarray=meses_temporada)
                st.plotly_chart(fig_grasa, use_container_width=True, key="res_grasa")

            st.markdown("---")
            st.markdown("#### 📏 Evolución de Perímetros")
            df_evo_per = df_filt_clean.groupby('Mes')[['Per_Pecho', 'Per_Cintura', 'Per_Cadera', 'Per_Muslo_D', 'Per_Muslo_I', 'Per_Pierna_D', 'Per_Pierna_I', 'Per_Biceps_D', 'Per_Biceps_I']].mean().reindex(meses_temporada).reset_index()

            cp1, cp2 = st.columns(2)
            with cp1:
                fig_p1 = go.Figure()
                fig_p1.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Pecho'], name='Pecho', mode='lines+markers'))
                fig_p1.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Biceps_D'], name='Bíceps D', mode='lines+markers'))
                fig_p1.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Biceps_I'], name='Bíceps I', mode='lines+markers', line=dict(dash='dash')))
                fig_p1.update_layout(title="Pecho y Bíceps", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p1, use_container_width=True, key="res_per_1")
                
            with cp2:
                fig_p2 = go.Figure()
                fig_p2.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Cintura'], name='Cintura', mode='lines+markers'))
                fig_p2.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Cadera'], name='Cadera', mode='lines+markers'))
                fig_p2.update_layout(title="Cintura y Cadera", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p2, use_container_width=True, key="res_per_2")

            cp3, cp4 = st.columns(2)
            with cp3:
                fig_p3 = go.Figure()
                fig_p3.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Muslo_D'], name='Muslo D', mode='lines+markers'))
                fig_p3.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Muslo_I'], name='Muslo I', mode='lines+markers', line=dict(dash='dash')))
                fig_p3.update_layout(title="Muslo (D/I)", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p3, use_container_width=True, key="res_per_3")
                
            with cp4:
                fig_p4 = go.Figure()
                fig_p4.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Pierna_D'], name='Pierna D', mode='lines+markers'))
                fig_p4.add_trace(go.Scatter(x=df_evo_per['Mes'], y=df_evo_per['Per_Pierna_I'], name='Pierna I', mode='lines+markers', line=dict(dash='dash')))
                fig_p4.update_layout(title="Pierna (D/I)", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p4, use_container_width=True, key="res_per_4")

with tab_antro_jug:
    if not st.session_state.plantilla:
        st.info("Primero debes añadir jugadores en la sección 'Plantilla'.")
    elif not antro_data:
        st.info("Sube primero un archivo Excel con pesajes en la pestaña 'Cargar Datos'.")
    else:
        nombres_plantilla = sorted([j["JUGADOR"] for j in st.session_state.plantilla])
        jugador_seleccionado = st.selectbox("Selecciona un jugador para ver su perfil antropométrico:", nombres_plantilla)
        
        # --- NUEVO: FOTO Y ENCABEZADO DEL JUGADOR ---
        jugador_datos = next((j for j in st.session_state.plantilla if j["JUGADOR"] == jugador_seleccionado), None)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_img, col_info = st.columns([1, 4])
        with col_img:
            if jugador_datos and jugador_datos.get("foto"):
                try:
                    st.markdown(f'<img src="data:image/jpeg;base64,{jugador_datos["foto"]}" style="width:100%; max-width:130px; border-radius:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
                except:
                    st.markdown('<div style="font-size: 70px; text-align: center;">👤</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size: 70px; text-align: center;">👤</div>', unsafe_allow_html=True)
        with col_info:
            st.markdown(f"<h2 style='margin-bottom: 0px;'>{jugador_seleccionado}</h2>", unsafe_allow_html=True)
            if jugador_datos:
                st.caption(f"**{jugador_datos.get('pos_1', jugador_datos.get('POS', ''))}** | Edad: {jugador_datos.get('edad', '-')} | Altura: {jugador_datos.get('altura', '-')} cm")
        
        st.markdown("---")
        
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
            
            # --- NUEVO: KPIs EN TARJETAS Y TÍTULOS MODIFICADOS ---
            with st.container(border=True):
                st.markdown(f"#### ⚖️ Pesaje ({ultimo_pesaje['fecha']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Peso", f"{ultimo_pesaje['Peso']:.1f} kg")
                c2.metric("% Graso (Yuhasz)", f"{ultimo_pesaje['% Graso']:.2f} %")
                c3.metric("Masa Magra", f"{ultimo_pesaje['Kg Magros']:.1f} kg")
                c4.metric("∑ 4 Pliegues", f"{ultimo_pesaje['Suma_Pliegues']:.1f} mm")
            
            with st.container(border=True):
                st.markdown("#### 📏 Perímetros")
                ultimo_valido = {}
                para_buscar = ['Per_Pecho', 'Per_Cintura', 'Per_Cadera', 'Per_Muslo_D', 'Per_Muslo_I', 'Per_Pierna_D', 'Per_Pierna_I', 'Per_Biceps_D', 'Per_Biceps_I']
                for col in para_buscar:
                    serie_valida = df_jug_antro[df_jug_antro[col] > 0]
                    ultimo_valido[col] = serie_valida.iloc[0][col] if not serie_valida.empty else 0.0

                p1, p2, p3, p4, p5, p6 = st.columns(6)
                prom_muslo_jug = (ultimo_valido['Per_Muslo_D'] + ultimo_valido['Per_Muslo_I']) / 2 if (ultimo_valido['Per_Muslo_D']>0 and ultimo_valido['Per_Muslo_I']>0) else ultimo_valido['Per_Muslo_D'] or ultimo_valido['Per_Muslo_I']
                prom_pierna_jug = (ultimo_valido['Per_Pierna_D'] + ultimo_valido['Per_Pierna_I']) / 2 if (ultimo_valido['Per_Pierna_D']>0 and ultimo_valido['Per_Pierna_I']>0) else ultimo_valido['Per_Pierna_D'] or ultimo_valido['Per_Pierna_I']
                prom_biceps_jug = (ultimo_valido['Per_Biceps_D'] + ultimo_valido['Per_Biceps_I']) / 2 if (ultimo_valido['Per_Biceps_D']>0 and ultimo_valido['Per_Biceps_I']>0) else ultimo_valido['Per_Biceps_D'] or ultimo_valido['Per_Biceps_I']

                p1.metric("Pecho", f"{ultimo_valido['Per_Pecho']:.1f} cm" if ultimo_valido['Per_Pecho'] > 0 else "-")
                p2.metric("Cintura", f"{ultimo_valido['Per_Cintura']:.1f} cm" if ultimo_valido['Per_Cintura'] > 0 else "-")
                p3.metric("Cadera", f"{ultimo_valido['Per_Cadera']:.1f} cm" if ultimo_valido['Per_Cadera'] > 0 else "-")
                p4.metric("Muslo", f"{prom_muslo_jug:.1f} cm" if prom_muslo_jug > 0 else "-")
                p5.metric("Pierna", f"{prom_pierna_jug:.1f} cm" if prom_pierna_jug > 0 else "-")
                p6.metric("Bíceps", f"{prom_biceps_jug:.1f} cm" if prom_biceps_jug > 0 else "-")

            with st.container(border=True):
                st.markdown("#### ⚖️ Asimetrías Perimetrales")
                st.caption("Diferencia entre lados (Derecha - Izquierda) y porcentaje de asimetría.")
                ca1, ca2, ca3 = st.columns(3)
                
                def calc_asim_str_jug(d, i):
                    if d == 0 or i == 0: return "-"
                    dif = d - i
                    pct = (abs(dif) / max(d, i)) * 100
                    return f"{dif:+.1f} cm ({pct:.1f}%)"

                ca1.metric("Muslo (D - I)", calc_asim_str_jug(ultimo_valido['Per_Muslo_D'], ultimo_valido['Per_Muslo_I']))
                ca2.metric("Pierna (D - I)", calc_asim_str_jug(ultimo_valido['Per_Pierna_D'], ultimo_valido['Per_Pierna_I']))
                ca3.metric("Bíceps (D - I)", calc_asim_str_jug(ultimo_valido['Per_Biceps_D'], ultimo_valido['Per_Biceps_I']))
            
            st.markdown("---")
            st.markdown("#### 📈 Evolución Histórica: Peso y % Graso")
            
            df_jug_antro_clean = df_jug_antro.replace({'Suma_Pliegues': 0, 'Per_Pecho': 0, 'Per_Cintura': 0, 'Per_Cadera': 0, 'Per_Muslo_D': 0, 'Per_Muslo_I': 0, 'Per_Pierna_D': 0, 'Per_Pierna_I': 0, 'Per_Biceps_D': 0, 'Per_Biceps_I': 0}, np.nan)
            df_jug_antro_clean['Mes_Num'] = df_jug_antro_clean['fecha_dt'].dt.month
            df_jug_antro_clean['Mes'] = df_jug_antro_clean['Mes_Num'].map(meses_esp)
            
            meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
            df_evo_jug = df_jug_antro_clean.groupby('Mes')[['Peso', '% Graso']].mean().reindex(meses_temporada).reset_index()
            
            cg_peso_j, cg_grasa_j = st.columns(2)
            with cg_peso_j:
                fig_peso_j = px.bar(df_evo_jug, x='Mes', y='Peso', title="Evolución Peso (kg)", color_discrete_sequence=['#00b4d8'])
                fig_peso_j.update_yaxes(range=[60, 100])
                fig_peso_j.update_xaxes(categoryorder='array', categoryarray=meses_temporada)
                st.plotly_chart(fig_peso_j, use_container_width=True, key=f"jug_peso_{jugador_seleccionado}")
                
            with cg_grasa_j:
                fig_grasa_j = px.bar(df_evo_jug, x='Mes', y='% Graso', title="Evolución % Graso", color_discrete_sequence=['#ff4b4b'])
                fig_grasa_j.update_yaxes(range=[7, 15])
                fig_grasa_j.update_xaxes(categoryorder='array', categoryarray=meses_temporada)
                st.plotly_chart(fig_grasa_j, use_container_width=True, key=f"jug_grasa_{jugador_seleccionado}")

            st.markdown("---")
            st.markdown("#### 📏 Evolución Histórica de Perímetros")
            df_evo_per_j = df_jug_antro_clean.groupby('Mes')[['Per_Pecho', 'Per_Cintura', 'Per_Cadera', 'Per_Muslo_D', 'Per_Muslo_I', 'Per_Pierna_D', 'Per_Pierna_I', 'Per_Biceps_D', 'Per_Biceps_I']].mean().reindex(meses_temporada).reset_index()

            cp1_j, cp2_j = st.columns(2)
            with cp1_j:
                fig_p1_j = go.Figure()
                fig_p1_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Pecho'], name='Pecho', mode='lines+markers'))
                fig_p1_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Biceps_D'], name='Bíceps D', mode='lines+markers'))
                fig_p1_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Biceps_I'], name='Bíceps I', mode='lines+markers', line=dict(dash='dash')))
                fig_p1_j.update_layout(title="Pecho y Bíceps", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p1_j, use_container_width=True, key=f"jug_per1_{jugador_seleccionado}")
                
            with cp2_j:
                fig_p2_j = go.Figure()
                fig_p2_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Cintura'], name='Cintura', mode='lines+markers'))
                fig_p2_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Cadera'], name='Cadera', mode='lines+markers'))
                fig_p2_j.update_layout(title="Cintura y Cadera", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p2_j, use_container_width=True, key=f"jug_per2_{jugador_seleccionado}")

            cp3_j, cp4_j = st.columns(2)
            with cp3_j:
                fig_p3_j = go.Figure()
                fig_p3_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Muslo_D'], name='Muslo D', mode='lines+markers'))
                fig_p3_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Muslo_I'], name='Muslo I', mode='lines+markers', line=dict(dash='dash')))
                fig_p3_j.update_layout(title="Muslo (D/I)", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p3_j, use_container_width=True, key=f"jug_per3_{jugador_seleccionado}")
                
            with cp4_j:
                fig_p4_j = go.Figure()
                fig_p4_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Pierna_D'], name='Pierna D', mode='lines+markers'))
                fig_p4_j.add_trace(go.Scatter(x=df_evo_per_j['Mes'], y=df_evo_per_j['Per_Pierna_I'], name='Pierna I', mode='lines+markers', line=dict(dash='dash')))
                fig_p4_j.update_layout(title="Pierna (D/I)", xaxis=dict(categoryorder='array', categoryarray=meses_temporada))
                st.plotly_chart(fig_p4_j, use_container_width=True, key=f"jug_per4_{jugador_seleccionado}")

            st.markdown("#### 📋 Historial Completo")
            
            # Calcular asimetrías porcentuales para la tabla
            for part, col_d, col_i in [('Bíceps', 'Per_Biceps_D', 'Per_Biceps_I'), 
                                       ('Muslo', 'Per_Muslo_D', 'Per_Muslo_I'), 
                                       ('Pierna', 'Per_Pierna_D', 'Per_Pierna_I')]:
                max_vals = df_jug_antro[[col_d, col_i]].max(axis=1)
                # Si no hay medición (max_vals == 0), asignamos NaN para que quede vacío
                df_jug_antro[f'Asimetría {part}'] = np.where(
                    max_vals > 0, 
                    (abs(df_jug_antro[col_d] - df_jug_antro[col_i]) / max_vals) * 100, 
                    np.nan
                )
            
            columnas_mostrar = [
                'fecha', 'Peso', '% Graso', 'Kg Magros', 'Suma_Pliegues', 
                'Per_Pecho', 'Per_Cintura', 'Per_Cadera', 
                'Per_Biceps_D', 'Per_Biceps_I', 'Asimetría Bíceps', 
                'Per_Muslo_D', 'Per_Muslo_I', 'Asimetría Muslo', 
                'Per_Pierna_D', 'Per_Pierna_I', 'Asimetría Pierna'
            ]
            
            nombres_columnas = {
                'fecha': 'Fecha',
                'Kg Magros': 'Peso magro',
                'Suma_Pliegues': 'Σ pliegues',
                'Per_Pecho': 'P. Pecho',
                'Per_Cintura': 'P. Cintura',
                'Per_Cadera': 'P. Cadera',
                'Per_Biceps_D': 'P. Bíceps D',
                'Per_Biceps_I': 'P. Bíceps I',
                'Per_Muslo_D': 'P. Muslo D',
                'Per_Muslo_I': 'P. Muslo I',
                'Per_Pierna_D': 'P. Pierna D',
                'Per_Pierna_I': 'P. Pierna I'
            }
            
            # Renombramos las columnas y preparamos el DataFrame final
            df_historial = df_jug_antro[columnas_mostrar].rename(columns=nombres_columnas)
            
            # --- NUEVO: Formateo condicional para ausencias de datos ("-") ---
            cols_perimetros = ['P. Pecho', 'P. Cintura', 'P. Cadera', 'P. Bíceps D', 'P. Bíceps I', 'P. Muslo D', 'P. Muslo I', 'P. Pierna D', 'P. Pierna I']
            cols_asimetrias = ['Asimetría Bíceps', 'Asimetría Muslo', 'Asimetría Pierna']
            
            # 1. Los 0.0 en perímetros significan que no se midió, los pasamos a NaN
            df_historial[cols_perimetros] = df_historial[cols_perimetros].replace(0.0, np.nan)
            
            # 2. Formateamos a 2 decimales. Si es NaN (nulo), ponemos el guion.
            for col in cols_perimetros + cols_asimetrias:
                df_historial[col] = df_historial[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "-")
            
            # Mostramos la tabla moderna (el formato de las demás columnas lo maneja la función global)
            mostrar_tabla_moderna(df_historial.style.hide(axis="index"))

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
