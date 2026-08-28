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

st.subheader("⚖️ Antropometría y Composición Corporal")

tab_antro_res, tab_antro_jug, tab_antro_up = st.tabs(["📊 Resumen Analítico", "👤 Jugadores", "📂 Cargar Datos"])

antro_data = st.session_state.get("antropometria", [])

with tab_antro_res:
    if not antro_data:
        st.info("Aún no hay datos antropométricos registrados. Sube tu Excel en la pestaña 'Cargar Datos'.")
    else:
        df_antro = st.session_state.df_antropometria.copy()
        
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
            
            # ==========================================
            # NUEVO: CUADRANTE DE COMPOSICIÓN CORPORAL (FFMI)
            # ==========================================
            st.markdown("---")
            st.markdown("#### 🎯 Cuadrante de Composición Corporal (Último Pesaje)")
            st.caption("Relación entre % Graso y el Índice de Masa Libre de Grasa (FFMI). Aísla la masa muscular real anulando el sesgo de la estatura del jugador.")

            # 1. Obtener la altura de los jugadores desde la plantilla
            dict_altura = {limpiar_nombre(p['JUGADOR']): safe_float(p.get('altura', 175)) for p in st.session_state.plantilla}

            # 2. Quedarnos solo con el último pesaje de cada jugador (dentro del filtro actual)
            df_latest = df_filt_clean.sort_values('fecha_dt', ascending=False).drop_duplicates(subset=['jugador']).copy()

            # 3. Calcular FFMI (Kg Magros / (Altura en metros)^2)
            def calcular_ffmi(row):
                altura_cm = dict_altura.get(limpiar_nombre(row['jugador']), 175)
                altura_m = altura_cm / 100.0
                if altura_m > 0 and row['Kg Magros'] > 0:
                    return row['Kg Magros'] / (altura_m ** 2)
                return 0.0

            df_latest['FFMI'] = df_latest.apply(calcular_ffmi, axis=1)
            df_latest_valid = df_latest[df_latest['FFMI'] > 0].copy()

            if not df_latest_valid.empty:
                media_grasa = df_latest_valid['% Graso'].mean()
                media_ffmi = df_latest_valid['FFMI'].mean()

                fig_quad = px.scatter(
                    df_latest_valid, 
                    x='% Graso', 
                    y='FFMI', 
                    color='POS',
                    hover_name='jugador',
                    text='jugador',
                    color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"}
                )

                fig_quad.update_traces(
                    textposition='top center', 
                    marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey'))
                )

                # --- NUEVO: ZONA OBJETIVO ÉLITE ---
                fig_quad.add_shape(
                    type="rect",
                    x0=7.5, x1=10.0,
                    y0=20.0, y1=23.0,
                    fillcolor="green",
                    opacity=0.15,
                    line_width=2,
                    line_color="green",
                    layer="below"
                )
                fig_quad.add_annotation(
                    x=8.75, y=23.3, 
                    text="ZONA ÉLITE", 
                    showarrow=False, 
                    font=dict(color="green", size=12, weight="bold")
                )

                # Líneas divisorias (Cuadrantes) usando la media del grupo filtrado
                fig_quad.add_vline(x=media_grasa, line_dash="dot", line_color="gray", opacity=0.7)
                fig_quad.add_hline(y=media_ffmi, line_dash="dot", line_color="gray", opacity=0.7)

                # Configuración visual de los cuadrantes
                fig_quad.update_layout(
                    xaxis_title="% Grasa (Yuhasz)",
                    yaxis_title="FFMI (Índice de Masa Magra)",
                    height=550,
                    margin=dict(l=20, r=20, t=40, b=20)
                )

                # Anotaciones descriptivas sutiles en las esquinas
                fig_quad.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper", text="↑ Musculados / Finos ↓", showarrow=False, font=dict(color="gray", size=10), opacity=0.6)
                fig_quad.add_annotation(x=0.98, y=0.98, xref="paper", yref="paper", text="↑ Musculados / Pesados ↑", showarrow=False, font=dict(color="gray", size=10), opacity=0.6)
                fig_quad.add_annotation(x=0.02, y=0.02, xref="paper", yref="paper", text="↓ Ligeros / Finos ↓", showarrow=False, font=dict(color="gray", size=10), opacity=0.6)
                fig_quad.add_annotation(x=0.98, y=0.02, xref="paper", yref="paper", text="↓ Ligeros / Pesados ↑", showarrow=False, font=dict(color="gray", size=10), opacity=0.6)

                st.plotly_chart(fig_quad, use_container_width=True, key="antro_quadrant")
            else:
                st.info("No hay suficientes datos válidos (peso y altura en la plantilla) para generar el cuadrante.")

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
                    img_src = jugador_datos["foto"] if str(jugador_datos["foto"]).startswith("http") else f"data:image/jpeg;base64,{jugador_datos['foto']}"
                    st.markdown(f'<img src="{img_src}" style="width:100%; max-width:130px; border-radius:12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">', unsafe_allow_html=True)
                except:
                    st.markdown('<div style="font-size: 70px; text-align: center;">👤</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size: 70px; text-align: center;">👤</div>', unsafe_allow_html=True)
        with col_info:
            st.markdown(f"<h2 style='margin-bottom: 0px;'>{jugador_seleccionado}</h2>", unsafe_allow_html=True)
            if jugador_datos:
                st.caption(f"**{jugador_datos.get('pos_1', jugador_datos.get('POS', ''))}** | Edad: {jugador_datos.get('edad', '-')} | Altura: {jugador_datos.get('altura', '-')} cm")
        
        st.markdown("---")
        
        df_antro = st.session_state.df_antropometria.copy()
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
                
                # --- NUEVO: CÁLCULO DE OBJETIVOS AUTOMÁTICOS (ANCLADO A SU GENÉTICA) ---
                st.markdown("---")
                st.markdown("#### 🎯 Objetivos de Composición Corporal")
                
                peso_actual = safe_float(ultimo_pesaje['Peso'])
                grasa_actual = safe_float(ultimo_pesaje['% Graso'])
                masa_magra_actual = safe_float(ultimo_pesaje['Kg Magros'])
                
                altura_cm = safe_float(jugador_datos.get('altura', 175)) if jugador_datos else 175
                altura_m = altura_cm / 100.0
                
                # 1. Calculamos el FFMI real del jugador en este momento
                ffmi_actual = masa_magra_actual / (altura_m ** 2) if altura_m > 0 else 21.0
                
                # 2. Creamos un rango muscular hiper-personalizado: Su FFMI actual ± 0.3
                # Lo limitamos ("clipeamos") a los topes de salud del fútbol (20.0 mínimo, 23.0 máximo)
                ffmi_min = max(20.0, ffmi_actual - 0.3)
                ffmi_max = min(23.0, ffmi_actual + 0.3)
                
                # 3. Rango de grasa estándar de élite (ventana estrecha)
                grasa_min, grasa_max = 8.0, 9.5
                
                st.caption(f"Metas individualizadas basadas en su propia estructura muscular actual (FFMI: **{ffmi_actual:.1f}**). Se ha calculado un rango objetivo de mantenimiento muscular ({ffmi_min:.1f} - {ffmi_max:.1f}) ajustando la grasa al nivel élite ({grasa_min}% - {grasa_max}%).")
                
                # 4. Cálculo de rangos de peso exactos (Esto generará una ventana de ~2 o 3 kg adaptada al 100% a él)
                peso_min = (ffmi_min * (altura_m ** 2)) / (1 - (grasa_min / 100))
                peso_max = (ffmi_max * (altura_m ** 2)) / (1 - (grasa_max / 100))
                
                # 5. Evaluador de estado (te dice exactamente cuántos kilos o % sobran o faltan)
                def evaluar_objetivo(actual, v_min, v_max, unidad):
                    if actual < v_min:
                        dif = v_min - actual
                        return f"🟡 Faltan {dif:.1f} {unidad}"
                    elif actual > v_max:
                        dif = actual - v_max
                        return f"🔴 Sobran {dif:.1f} {unidad}"
                    else:
                        return f"✅ En rango óptimo"

                est_peso = evaluar_objetivo(peso_actual, peso_min, peso_max, "kg")
                est_grasa = evaluar_objetivo(grasa_actual, grasa_min, grasa_max, "%")
                
                co1, co2 = st.columns(2)
                co1.info(f"**Rango de Peso Ideal:** {peso_min:.1f} kg — {peso_max:.1f} kg\n\n**Estado:** {est_peso}")
                co2.info(f"**Rango de Grasa Ideal:** {grasa_min:.1f} % — {grasa_max:.1f} %\n\n**Estado:** {est_grasa}")
            
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

            # --- PREPARACIÓN DE DICCIONARIOS PARA EL PDF ---
            kpis_perimetros = {
                'Pecho': f"{ultimo_valido['Per_Pecho']:.1f} cm" if ultimo_valido['Per_Pecho'] > 0 else "-",
                'Cintura': f"{ultimo_valido['Per_Cintura']:.1f} cm" if ultimo_valido['Per_Cintura'] > 0 else "-",
                'Cadera': f"{ultimo_valido['Per_Cadera']:.1f} cm" if ultimo_valido['Per_Cadera'] > 0 else "-",
                'Muslo': f"{prom_muslo_jug:.1f} cm" if prom_muslo_jug > 0 else "-",
                'Pierna': f"{prom_pierna_jug:.1f} cm" if prom_pierna_jug > 0 else "-",
                'Biceps': f"{prom_biceps_jug:.1f} cm" if prom_biceps_jug > 0 else "-"
            }
            
            kpis_asimetrias = {
                'Muslo': calc_asim_str_jug(ultimo_valido['Per_Muslo_D'], ultimo_valido['Per_Muslo_I']),
                'Pierna': calc_asim_str_jug(ultimo_valido['Per_Pierna_D'], ultimo_valido['Per_Pierna_I']),
                'Biceps': calc_asim_str_jug(ultimo_valido['Per_Biceps_D'], ultimo_valido['Per_Biceps_I'])
            }
            
            dict_figs_jug = {
                'peso': fig_peso_j, 'grasa': fig_grasa_j,
                'per1': fig_p1_j, 'per2': fig_p2_j,
                'per3': fig_p3_j, 'per4': fig_p4_j
            }
            # ==========================================
            # 1. DESCARGA INDIVIDUAL
            # ==========================================
            st.markdown("---")
            pdf_key = f"pdf_antro_{jugador_seleccionado}"
            
            if pdf_key not in st.session_state:
                if st.button("⚙️ Generar PDF Antropométrico", use_container_width=True):
                    with st.spinner("Procesando gráficos y compilando PDF..."):
                        jugador_info = f"{jugador_datos.get('pos_1', jugador_datos.get('POS', ''))} | Edad: {jugador_datos.get('edad', '-')} | Altura: {jugador_datos.get('altura', '-')} cm" if jugador_datos else ""
                        kpis_pes = {'Peso': f"{ultimo_pesaje['Peso']:.1f} kg", 'Grasa': f"{ultimo_pesaje['% Graso']:.2f} %", 'Magra': f"{ultimo_pesaje['Kg Magros']:.1f} kg", 'Pliegues': f"{ultimo_pesaje['Suma_Pliegues']:.1f} mm"}
                        
                        escudo_b64 = st.session_state.get("escudo_equipo")
                        foto_b64 = jugador_datos.get("foto") if jugador_datos else None
                        
                        pdf_bytes = generar_pdf_antropometria_jugador(
                            jugador_seleccionado, jugador_info, ultimo_pesaje['fecha'],
                            kpis_pes, kpis_perimetros, kpis_asimetrias, dict_figs_jug,
                            df_historial, escudo_b64, foto_b64
                        )
                        st.session_state[pdf_key] = pdf_bytes
                    st.rerun()
            else:
                c_down1, c_down2 = st.columns(2)
                with c_down1:
                    st.download_button(
                        label="📥 Descargar PDF",
                        data=st.session_state[pdf_key],
                        file_name=f"Antropometría {jugador_seleccionado}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c_down2:
                    if st.button("🗑️ Descartar PDF", use_container_width=True):
                        del st.session_state[pdf_key]
                        st.rerun()

            # ==========================================
            # 2. DESCARGA MASIVA (TODA LA PLANTILLA EN ZIP)
            # ==========================================
            st.markdown("---")
            st.markdown("#### 🗂️ Descarga Masiva (Toda la Plantilla)")
            st.caption("Genera un archivo ZIP que contendrá los informes individuales en PDF de todos los jugadores.")
            
            if st.button("📦 Generar ZIP con todos los informes", use_container_width=True):
                import zipfile
                import io
                
                with st.status("Generando informes para toda la plantilla...", expanded=True) as status:
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for p in st.session_state.plantilla:
                            jug_masivo = p["JUGADOR"]
                            st.write(f"Procesando datos de {jug_masivo}...")
                            
                            df_jug_masivo = df_antro[df_antro['jugador'] == jug_masivo].sort_values('fecha_dt', ascending=False)
                            
                            if not df_jug_masivo.empty:
                                df_jug_masivo['Suma_Pliegues'] = df_jug_masivo['P_Tricipital'] + df_jug_masivo['P_Subescapular'] + df_jug_masivo['P_Suprailiaco'] + df_jug_masivo['P_Abdominal']
                                df_jug_masivo['% Graso'] = (df_jug_masivo['Suma_Pliegues'] * 0.1537) + 5.783
                                df_jug_masivo['Kg Magros'] = df_jug_masivo['Peso'] - (df_jug_masivo['Peso'] * (df_jug_masivo['% Graso'] / 100))
                                
                                ult_pesaje = df_jug_masivo.iloc[0]
                                
                                ult_valido = {}
                                for col in para_buscar:
                                    serie_val = df_jug_masivo[df_jug_masivo[col] > 0]
                                    ult_valido[col] = serie_val.iloc[0][col] if not serie_val.empty else 0.0
                                
                                p_muslo = (ult_valido['Per_Muslo_D'] + ult_valido['Per_Muslo_I']) / 2 if (ult_valido['Per_Muslo_D']>0 and ult_valido['Per_Muslo_I']>0) else ult_valido['Per_Muslo_D'] or ult_valido['Per_Muslo_I']
                                p_pierna = (ult_valido['Per_Pierna_D'] + ult_valido['Per_Pierna_I']) / 2 if (ult_valido['Per_Pierna_D']>0 and ult_valido['Per_Pierna_I']>0) else ult_valido['Per_Pierna_D'] or ult_valido['Per_Pierna_I']
                                p_biceps = (ult_valido['Per_Biceps_D'] + ult_valido['Per_Biceps_I']) / 2 if (ult_valido['Per_Biceps_D']>0 and ult_valido['Per_Biceps_I']>0) else ult_valido['Per_Biceps_D'] or ult_valido['Per_Biceps_I']

                                kpis_pes_m = {'Peso': f"{ult_pesaje['Peso']:.1f} kg", 'Grasa': f"{ult_pesaje['% Graso']:.2f} %", 'Magra': f"{ult_pesaje['Kg Magros']:.1f} kg", 'Pliegues': f"{ult_pesaje['Suma_Pliegues']:.1f} mm"}
                                kpis_per_m = {
                                    'Pecho': f"{ult_valido['Per_Pecho']:.1f} cm" if ult_valido['Per_Pecho'] > 0 else "-",
                                    'Cintura': f"{ult_valido['Per_Cintura']:.1f} cm" if ult_valido['Per_Cintura'] > 0 else "-",
                                    'Cadera': f"{ult_valido['Per_Cadera']:.1f} cm" if ult_valido['Per_Cadera'] > 0 else "-",
                                    'Muslo': f"{p_muslo:.1f} cm" if p_muslo > 0 else "-",
                                    'Pierna': f"{p_pierna:.1f} cm" if p_pierna > 0 else "-",
                                    'Biceps': f"{p_biceps:.1f} cm" if p_biceps > 0 else "-"
                                }
                                kpis_asim_m = {
                                    'Muslo': calc_asim_str_jug(ult_valido['Per_Muslo_D'], ult_valido['Per_Muslo_I']),
                                    'Pierna': calc_asim_str_jug(ult_valido['Per_Pierna_D'], ult_valido['Per_Pierna_I']),
                                    'Biceps': calc_asim_str_jug(ult_valido['Per_Biceps_D'], ult_valido['Per_Biceps_I'])
                                }
                                
                                df_cl = df_jug_masivo.replace({'Suma_Pliegues': 0, 'Per_Pecho': 0, 'Per_Cintura': 0, 'Per_Cadera': 0, 'Per_Muslo_D': 0, 'Per_Muslo_I': 0, 'Per_Pierna_D': 0, 'Per_Pierna_I': 0, 'Per_Biceps_D': 0, 'Per_Biceps_I': 0}, np.nan)
                                df_cl['Mes_Num'] = df_cl['fecha_dt'].dt.month
                                df_cl['Mes'] = df_cl['Mes_Num'].map(meses_esp)
                                df_evo_m = df_cl.groupby('Mes')[['Peso', '% Graso']].mean().reindex(meses_temporada).reset_index()
                                df_per_m = df_cl.groupby('Mes')[['Per_Pecho', 'Per_Cintura', 'Per_Cadera', 'Per_Muslo_D', 'Per_Muslo_I', 'Per_Pierna_D', 'Per_Pierna_I', 'Per_Biceps_D', 'Per_Biceps_I']].mean().reindex(meses_temporada).reset_index()
                                
                                fig_pm = px.bar(df_evo_m, x='Mes', y='Peso', title="Evolución Peso (kg)", color_discrete_sequence=['#00b4d8']).update_yaxes(range=[60, 100])
                                fig_gm = px.bar(df_evo_m, x='Mes', y='% Graso', title="Evolución % Graso", color_discrete_sequence=['#ff4b4b']).update_yaxes(range=[7, 15])
                                
                                fig_per1_m = go.Figure().add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Pecho'], name='Pecho')).add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Biceps_D'], name='Bíceps D')).add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Biceps_I'], name='Bíceps I', line=dict(dash='dash'))).update_layout(title="Pecho y Bíceps")
                                fig_per2_m = go.Figure().add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Cintura'], name='Cintura')).add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Cadera'], name='Cadera')).update_layout(title="Cintura y Cadera")
                                fig_per3_m = go.Figure().add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Muslo_D'], name='Muslo D')).add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Muslo_I'], name='Muslo I', line=dict(dash='dash'))).update_layout(title="Muslo (D/I)")
                                fig_per4_m = go.Figure().add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Pierna_D'], name='Pierna D')).add_trace(go.Scatter(x=df_per_m['Mes'], y=df_per_m['Per_Pierna_I'], name='Pierna I', line=dict(dash='dash'))).update_layout(title="Pierna (D/I)")

                                dict_figs_m = {'peso': fig_pm, 'grasa': fig_gm, 'per1': fig_per1_m, 'per2': fig_per2_m, 'per3': fig_per3_m, 'per4': fig_per4_m}
                                
                                for part, col_d, col_i in [('Bíceps', 'Per_Biceps_D', 'Per_Biceps_I'), ('Muslo', 'Per_Muslo_D', 'Per_Muslo_I'), ('Pierna', 'Per_Pierna_D', 'Per_Pierna_I')]:
                                    mx = df_jug_masivo[[col_d, col_i]].max(axis=1)
                                    df_jug_masivo[f'Asimetría {part}'] = np.where(mx > 0, (abs(df_jug_masivo[col_d] - df_jug_masivo[col_i]) / mx) * 100, np.nan)
                                
                                df_hist_m = df_jug_masivo[columnas_mostrar].rename(columns=nombres_columnas)
                                
                                cols_numericas_m = ['Peso', '% Graso', 'Peso magro', 'Σ pliegues'] + cols_perimetros + cols_asimetrias
                                for col in cols_numericas_m:
                                    df_hist_m[col] = pd.to_numeric(df_hist_m[col], errors='coerce')
                                    df_hist_m[col] = df_hist_m[col].apply(lambda x: f"{float(x):.1f}" if pd.notna(x) else "-")

                                j_info_m = f"{p.get('pos_1', p.get('POS', ''))} | Edad: {p.get('edad', '-')} | Altura: {p.get('altura', '-')} cm"
                                
                                pdf_bytes_m = generar_pdf_antropometria_jugador(
                                    jug_masivo, j_info_m, ult_pesaje['fecha'],
                                    kpis_pes_m, kpis_per_m, kpis_asim_m, dict_figs_m,
                                    df_hist_m, st.session_state.get("escudo_equipo"), p.get("foto")
                                )
                                
                                zip_file.writestr(f"Antropometría {jug_masivo}.pdf", pdf_bytes_m)

                    st.session_state["zip_antro_all"] = zip_buffer.getvalue()
                    status.update(label="¡ZIP generado con éxito!", state="complete", expanded=False)
                    st.rerun()
                    
            if "zip_antro_all" in st.session_state:
                c_z1, c_z2 = st.columns(2)
                with c_z1:
                    st.download_button(
                        label="📥 Descargar archivo ZIP",
                        data=st.session_state["zip_antro_all"],
                        file_name="Informes_Antropometria_Equipo.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                with c_z2:
                    if st.button("🗑️ Descartar ZIP", use_container_width=True):
                        del st.session_state["zip_antro_all"]
                        st.rerun()

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
                    
                guardar_datos(modulo="antropometria")
                st.success(f"✅ ¡{registros_nuevos} pesajes procesados e integrados con éxito!")
                st.rerun()
        except Exception as e:
            st.error(f"Error al leer el archivo. Asegúrate de que el formato es correcto. Detalle técnico: {e}")
