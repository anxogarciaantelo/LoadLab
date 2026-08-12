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

    if "vista_plantilla" not in st.session_state:
        st.session_state.vista_plantilla = "📋 Plantilla"

    nombres_jugadores = [j["JUGADOR"] for j in st.session_state.plantilla]
    opciones_vista = ["📋 Plantilla", "⚙️ Modificar Plantilla"] + [f"👤 {nombre}" for nombre in nombres_jugadores]
    
    # Prevenir errores si se elimina un jugador que estaba seleccionado
    if st.session_state.vista_plantilla not in opciones_vista:
        st.session_state.vista_plantilla = "📋 Plantilla"

    idx_actual = opciones_vista.index(st.session_state.vista_plantilla)

    # Función de callback para sincronizar el selector con el estado
    def actualizar_vista():
        st.session_state.vista_plantilla = st.session_state.selector_vista

    st.selectbox(
        "Navegación:", 
        opciones_vista, 
        index=idx_actual, 
        key="selector_vista",
        on_change=actualizar_vista
    )

    st.markdown("---")

    if st.session_state.vista_plantilla == "📋 Plantilla":
        if not st.session_state.plantilla:
            st.info("No hay jugadores en la plantilla.")
        else:
            st.markdown("### 📋 Cuadro de Plantilla")
            st.caption("Haz clic en el botón de perfil de cualquier jugador para acceder directamente a sus datos detallados.")
            
            # Inicializar el estado de la pestaña activa si no existe
            if "index_pestana_activa" not in st.session_state:
                st.session_state.index_pestana_activa = 0

            jugadores_lista = st.session_state.plantilla
            for i in range(0, len(jugadores_lista), 4):
                cols = st.columns(4)
                for j in range(4):
                    idx_global = i + j
                    if idx_global < len(jugadores_lista):
                        jug = jugadores_lista[idx_global]
                        with cols[j]:
                            with st.container(border=True):
                                if jug.get("foto"):
                                    try:
                                        st.markdown(f'<div style="text-align: center;"><img src="data:image/jpeg;base64,{jug["foto"]}" style="width:90px; height:90px; object-fit: cover; border-radius:50%;"></div>', unsafe_allow_html=True)
                                    except:
                                        st.markdown('<div style="text-align: center; font-size: 40px;">👤</div>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div style="text-align: center; font-size: 40px;">👤</div>', unsafe_allow_html=True)
                                
                                st.markdown(f"<h3 style='text-align: center; margin-bottom: 0px;'>#{jug.get('dorsal', '99')}</h3>", unsafe_allow_html=True)
                                st.markdown(f"<h4 style='text-align: center; margin-top: 0px; font-size: 1.1rem;'>{jug['JUGADOR']}</h4>", unsafe_allow_html=True)
                                st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.8rem;'>{jug.get('pos_1', jug.get('POS', ''))}</p>", unsafe_allow_html=True)
                                
                                # Botón interactivo para ir a la vista del jugador
                                if st.button("🔍 Ver Perfil", key=f"btn_ver_perfil_{idx_global}", use_container_width=True):
                                    st.session_state.vista_plantilla = f"👤 {jug['JUGADOR']}"
                                    st.rerun()
            
    elif st.session_state.vista_plantilla == "⚙️ Modificar Plantilla":
        with st.expander("➕ Añadir Jugador"):
            with st.form("form_alta_jugador"):
                c_m1, c_m2, c_m3 = st.columns(3)
                with c_m1:
                    nombre_j = st.text_input("Nombre y Apellidos:")
                    edad_j = st.number_input("Edad:", min_value=5, max_value=45, value=19)
                with c_m2:
                    pos_pri = st.selectbox("Posición Primaria:", ["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"])
                    pos_sec = st.selectbox("Posición Secundaria:", ["Ninguna", "Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"])
                with c_m3:
                    dorsal_j = st.number_input("Dorsal:", min_value=1, max_value=99, value=10)
                    altura_j = st.number_input("Altura (cm):", min_value=120, max_value=220, value=178)
                    
                c_m4, c_m5 = st.columns(2)
                with c_m4:
                    lateralidad_j = st.selectbox("Lateralidad:", ["Diestro", "Zurdo", "Ambidiestro"])
                with c_m5:
                    foto_up = st.file_uploader("Foto de Perfil (Opcional):", type=["jpg", "png", "jpeg"])
                    
                if st.form_submit_button("💾 Guardar Jugador") and nombre_j:
                    st.session_state.plantilla.append({
                        "JUGADOR": nombre_j,
                        "POS": "POR" if pos_pri=="Portero" else ("DEF" if pos_pri in ["Central", "Lateral"] else ("MED" if pos_pri in ["Mediocentro", "Mediapunta"] else "ATA")),
                        "edad": edad_j, "pos_1": pos_pri, "pos_2": pos_sec, "dorsal": dorsal_j, "altura": altura_j,
                        "lateralidad": lateralidad_j,
                        "foto": get_base64_of_bin_file(foto_up)
                    })
                    guardar_datos()
                    st.success(f"¡{nombre_j} añadido!")
                    st.rerun()

        st.markdown("---")
        
        with st.expander("❌ Eliminar Jugador"):
            if st.session_state.plantilla:
                with st.form("form_baja_jugador"):
                    jugador_a_borrar = st.selectbox("Selecciona el jugador a eliminar:", nombres_jugadores)
                    st.warning("⚠️ Cuidado: Si eliminas a un jugador, desaparecerá de la plantilla actual.")
                    if st.form_submit_button("❌ Confirmar Eliminación"):
                        st.session_state.plantilla = [j for j in st.session_state.plantilla if j["JUGADOR"] != jugador_a_borrar]
                        guardar_datos()
                        st.success(f"¡El jugador {jugador_a_borrar} ha sido eliminado!")
                        st.rerun()
            else:
                st.info("No hay jugadores en la plantilla para eliminar.")
            
    else:
        nombre_jugador_actual = st.session_state.vista_plantilla.replace("👤 ", "")
        jugador = next((j for j in st.session_state.plantilla if j["JUGADOR"] == nombre_jugador_actual), None)
        i = st.session_state.plantilla.index(jugador)
        
        if st.button("⬅️ Volver a la Plantilla", key="btn_volver_plantilla"):
            st.session_state.vista_plantilla = "📋 Plantilla"
            st.rerun()
            
        col_i1, col_i2 = st.columns([1, 4])
        with col_i1:
                if jugador.get("foto"):
                    try:
                        st.markdown(f'<img src="data:image/jpeg;base64,{jugador["foto"]}" style="width:100%; max-width:200px; border-radius:10px;">', unsafe_allow_html=True)
                    except:
                        st.markdown("👤")
                else:
                    st.markdown("👤 (Sin foto)")
                
                st.markdown(f"## {jugador['dorsal']} | **{jugador['JUGADOR']}**")
                st.caption(f"{jugador['pos_1']} | {jugador['lateralidad']}")
                st.caption(f"{jugador['edad']} años | {jugador['altura']} cm")
                
                with st.expander("✏️ Editar Perfil"):
                    with st.form(f"edit_jug_{i}"):
                        new_pos1 = st.selectbox("Posición 1:", ["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"], index=["Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"].index(jugador['pos_1']))
                        
                        opciones_pos2 = ["Ninguna", "Portero", "Central", "Lateral", "Mediocentro", "Mediapunta", "Extremo", "Delantero"]
                        idx_pos2 = opciones_pos2.index(jugador.get('pos_2', 'Ninguna')) if jugador.get('pos_2', 'Ninguna') in opciones_pos2 else 0
                        new_pos2 = st.selectbox("Posición 2:", opciones_pos2, index=idx_pos2)
                        
                        new_lat = st.selectbox("Lateralidad:", ["Diestro", "Zurdo", "Ambidiestro"], index=["Diestro", "Zurdo", "Ambidiestro"].index(jugador.get('lateralidad', 'Diestro')))
                        new_edad = st.number_input("Edad:", value=jugador['edad'])
                        new_alt = st.number_input("Altura:", value=jugador['altura'])
                        new_dorsal = st.number_input("Dorsal:", value=jugador['dorsal'])
                        new_foto = st.file_uploader("Actualizar foto (Dejar vacío para mantener):", type=["jpg", "png", "jpeg"])
                        
                        if st.form_submit_button("💾 Guardar Cambios"):
                            st.session_state.plantilla[i]['pos_1'] = new_pos1
                            st.session_state.plantilla[i]['pos_2'] = new_pos2
                            st.session_state.plantilla[i]['POS'] = "POR" if new_pos1=="Portero" else ("DEF" if new_pos1 in ["Central", "Lateral"] else ("MED" if new_pos1 in ["Mediocentro", "Mediapunta"] else "ATA"))
                            st.session_state.plantilla[i]['lateralidad'] = new_lat
                            st.session_state.plantilla[i]['edad'] = new_edad
                            st.session_state.plantilla[i]['altura'] = new_alt
                            st.session_state.plantilla[i]['dorsal'] = new_dorsal
                            if new_foto: st.session_state.plantilla[i]['foto'] = get_base64_of_bin_file(new_foto)
                            guardar_datos()
                            st.rerun()

        with col_i2:
                sub_tabs = st.tabs(["🧠 Bienestar", "🔥 Carga Interna", "🏃‍♂️ Perfil GPS", "🚑 Historial Médico", "⚖️ Composición Corporal", "📊 Valoraciones"])
                
                datos_sesiones_jug = []
                for s in st.session_state.sesiones:
                    if s.get("informe_generado"):
                        for d in s["datos_informe"]:
                            if d["JUGADOR"] == jugador["JUGADOR"]:
                                datos_sesiones_jug.append({"FECHA": s["fecha"], "TIPO": s["tipo"], "MD": s["descripcion"], **d})
                df_j = pd.DataFrame(datos_sesiones_jug)
                
                with sub_tabs[0]:
                    if df_j.empty or 'TQR' not in df_j.columns:
                        st.info("No hay datos de bienestar registrados para este jugador.")
                    else:
                        df_w = df_j[df_j['TQR'] > 0].copy()
                        if df_w.empty:
                            st.info("No hay encuestas de bienestar para este jugador.")
                        else:
                            st.markdown("#### 🧠 Promedios de Bienestar")
                            cw1, cw2, cw3, cw4, cw5, cw6, cw7 = st.columns(7)
                            cw1.metric("TQR Medio", f"{df_w['TQR'].mean():.1f}")
                            cw2.metric("Wellness (Tot)", f"{df_w['WELLNESS'].mean():.1f}")
                            cw3.metric("Fatiga", f"{df_w.get('W_Fatiga', pd.Series([0])).mean():.1f}")
                            cw4.metric("Sueño", f"{df_w.get('W_Sueño', pd.Series([0])).mean():.1f}")
                            cw5.metric("Dolor", f"{df_w.get('W_Dolor', pd.Series([0])).mean():.1f}")
                            cw6.metric("Estrés", f"{df_w.get('W_Estres', pd.Series([0])).mean():.1f}")
                            cw7.metric("Humor", f"{df_w.get('W_Humor', pd.Series([0])).mean():.1f}")
                            
                            u_tqr = safe_float(df_w.iloc[-1]['TQR'])
                            u_well = safe_float(df_w.iloc[-1]['WELLNESS'])
                            
                            alertas_w = []
                            if u_tqr > 0:
                                if u_tqr <= 3:
                                    alertas_w.append(f"🔴 Recuperación Crítica ({u_tqr:.1f})")
                                elif u_tqr == 4:
                                    alertas_w.append(f"🟡 Recuperación Moderada ({u_tqr:.1f})")
                                    
                            if u_well > 0:
                                if u_well >= 24:
                                    alertas_w.append(f"🔴 Wellness Crítico ({u_well:.1f})")
                                elif 18 <= u_well <= 23:
                                    alertas_w.append(f"🟡 Wellness Moderado ({u_well:.1f})")
                            
                            if alertas_w:
                                for al in alertas_w: st.warning(al)
                            else:
                                st.success("✅ Valores de bienestar en rangos óptimos.")
                                
                            st.markdown("#### Últimos Registros")
                            mostrar_tabla_moderna(df_w[['FECHA', 'TIPO', 'TQR', 'WELLNESS', 'W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor']].tail(5).sort_values("FECHA", ascending=False).style.hide(axis="index").format(precision=0))

                with sub_tabs[1]:
                    if df_j.empty or 'CARGA' not in df_j.columns:
                        st.info("No hay datos de carga para este jugador.")
                    else:
                        ewma_dict = calcular_ewma_historico(st.session_state.sesiones, str(date.today()))
                        j_ewma = ewma_dict.get(jugador["JUGADOR"], {"EWMA AGUDA": 0, "EWMA CRÓNICA": 0, "RATIO A/C": 0})
                        
                        st.markdown("#### 🔥 Carga Interna")
                        cc1, cc2, cc3, cc4, cc5 = st.columns(5)
                        cc1.metric("Total Minutos", f"{df_j['MIN'].sum():.0f}'")
                        cc2.metric("RPE Promedio", f"{df_j[df_j['RPE']>0]['RPE'].mean():.1f}")
                        cc3.metric("Carga Aguda Actual", f"{j_ewma['EWMA AGUDA']:.0f}")
                        cc4.metric("Carga Crónica Actual", f"{j_ewma['EWMA CRÓNICA']:.0f}")
                        cc5.metric("EWMA Actual", f"{j_ewma['RATIO A/C']:.2f}")
                        
                        ratio_ac_ind = j_ewma['RATIO A/C']
                        carga_aguda_ind = j_ewma['EWMA AGUDA']
                        monot_ind = calcular_monotonia_7d(st.session_state.sesiones, jugador["JUGADOR"], str(date.today()))
                        strain_ind = carga_aguda_ind * monot_ind
                        
                        alertas_carga_ind = []
                        if carga_aguda_ind > 1000:
                            if ratio_ac_ind >= 1.5:
                                alertas_carga_ind.append(f"🔴 Ratio A/C en riesgo alto ({ratio_ac_ind:.2f})")
                            elif 1.35 <= ratio_ac_ind < 1.5:
                                alertas_carga_ind.append(f"🟡 Ratio A/C en riesgo moderado ({ratio_ac_ind:.2f})")
                                
                        if monot_ind > 2.0 and strain_ind > 4000:
                            alertas_carga_ind.append(f"🟡 Riesgo por monotonía y fatiga acumulada (Monotonía {monot_ind:.2f}, Strain {strain_ind:.0f})")
                            
                        if alertas_carga_ind:
                            for al in alertas_carga_ind: st.warning(al)
                        else:
                            st.success("✅ Parámetros de carga y ratio A/C en zona segura.")

                        st.markdown("#### 📋 Últimos Registros de Carga Interna")
                        
                        df_tabla_ci = df_j.copy()

                        def obtener_ewma_historico_fila(fecha_sesion):
                            dict_historico = calcular_ewma_historico(st.session_state.sesiones, fecha_sesion)
                            return dict_historico.get(jugador["JUGADOR"], {"EWMA AGUDA": 0.0, "EWMA CRÓNICA": 0.0, "RATIO A/C": 0.0})

                        df_tabla_ci['AGUDA'] = df_tabla_ci['FECHA'].apply(lambda f: obtener_ewma_historico_fila(f)['EWMA AGUDA'])
                        df_tabla_ci['CRONICA'] = df_tabla_ci['FECHA'].apply(lambda f: obtener_ewma_historico_fila(f)['EWMA CRÓNICA'])
                        df_tabla_ci['EWMA'] = df_tabla_ci['FECHA'].apply(lambda f: obtener_ewma_historico_fila(f)['RATIO A/C'])

                        cols_ver_ci_indiv = ['FECHA', 'TIPO', 'RPE', 'MIN', 'CARGA', 'AGUDA', 'CRONICA', 'EWMA']
                        df_ultimos_ci_indiv = df_tabla_ci[cols_ver_ci_indiv].sort_values("FECHA", ascending=False).head(5)
                        mostrar_tabla_moderna(df_ultimos_ci_indiv.style.hide(axis="index").format(precision=2))
                with sub_tabs[2]:
                    if df_j.empty or df_j['DIS'].sum() == 0:
                        st.info("No hay datos de GPS validados para este jugador.")
                    else:
                        # MAPEO INDIVIDUAL EXTENDIDO
                        if 'HID >21' in df_j.columns: df_j['DIS AI'] = df_j['HID >21']
                        if 'SPR >24' in df_j.columns: df_j['Nº SPR'] = df_j['SPR >24']
                        if 'ACC >3' in df_j.columns: df_j['ACC'] = df_j['ACC >3']
                        if 'DCC >3' in df_j.columns: df_j['DCC'] = df_j['DCC >3']
                        if 'V_Max' in df_j.columns: df_j['VMAX'] = df_j['V_Max']
                    
                        st.markdown("#### 🏃‍♂️ Perfil de GPS Individual")
                        f_tipo_g = st.selectbox("Filtrar por:", ["TODOS", "Partido", "Entrenamiento"], key=f"g_t_{i}")
                        f_md_g = "TODOS"
                        if f_tipo_g == "Entrenamiento": f_md_g = st.selectbox("Match Day:", ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"], key=f"g_m_{i}")
                        
                        # Filtro estricto: Solo registros donde la distancia sea > 0 (No aplasta la media si estuvo lesionado)
                        df_jg = df_j[df_j['DIS'] > 0].copy()
                        
                        if f_tipo_g != "TODOS": df_jg = df_jg[df_jg['TIPO'] == f_tipo_g]
                        if f_tipo_g == "Entrenamiento" and f_md_g != "TODOS": df_jg = df_jg[df_jg['MD'] == f_md_g]
                        
                        if df_jg.empty:
                            st.warning("No hay registros GPS para este filtro.")
                        else:
                            min_gps_col = df_jg['MIN_GPS'] if 'MIN_GPS' in df_jg.columns else df_jg['MIN']
                            m_gps = df_jg[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']].mean()
                            prom_min = min_gps_col.mean() if not min_gps_col.empty else 1.0
                            
                            cg1, cg2, cg3, cg4 = st.columns(4)
                            cg1.metric("DIS Total (km)", f"{m_gps['DIS']:.2f}")
                            cg2.metric("HSR (>21 km/h)", f"{m_gps['DIS AI']:.2f}")
                            cg3.metric("ACC / DCC (>3 m/s²)", f"{m_gps['ACC']:.1f} / {m_gps['DCC']:.1f}")
                            cg4.metric("V. Máxima Histórica", f"{df_jg['VMAX'].max():.1f} km/h")
                            
                            st.markdown("##### Promedios por Minuto (GPS)")
                            cg5, cg6, cg7 = st.columns(3)
                            cg5.metric("m / min", f"{(m_gps['DIS'] / prom_min * 1000):.1f}" if prom_min > 0 else "0.0")
                            cg6.metric("HSR m / min", f"{(m_gps['DIS AI'] / prom_min):.2f}" if prom_min > 0 else "0.0")
                            cg7.metric("ACC / min", f"{(m_gps['ACC'] / prom_min):.2f}" if prom_min > 0 else "0.0")

                with sub_tabs[3]:
                    les_jug = [l for l in st.session_state.lesiones if l['jugador'] == jugador['JUGADOR']]
                    if not les_jug:
                        st.success("✅ El jugador está limpio. No ha sufrido lesiones esta temporada.")
                    else:
                        df_l = pd.DataFrame(les_jug)
                        conteo_zonas = Counter([l['zona'] for l in les_jug])
                        
                        st.markdown("#### 🚑 Historial Médico")
                        cm1, cm2 = st.columns(2)
                        cm1.metric("Total de Lesiones", len(les_jug))
                        cm2.metric("Días de Baja Acumulados", df_l['dias_baja'].fillna(0).sum())
                        
                        alertas_med = [zona for zona, count in conteo_zonas.items() if count >= 2]
                        if alertas_med:
                            st.error(f"🔴 **Riesgo Crónico:** El jugador ha sufrido múltiples lesiones en: {', '.join(alertas_med)}. Considerar protocolo preventivo específico.")
                        
                        mostrar_tabla_moderna(df_l[['id_sesion', 'tipo', 'zona', 'lado', 'estado', 'dias_baja']].sort_values('id_sesion', ascending=False).style.hide(axis="index"))

                with sub_tabs[4]:
                    ant_jug = [a for a in st.session_state.antropometria if a['jugador'] == jugador['JUGADOR']]
                    if not ant_jug:
                        st.info("No hay datos antropométricos registrados.")
                    else:
                        df_aj = pd.DataFrame(ant_jug)
                        df_aj['fecha_dt'] = pd.to_datetime(df_aj['fecha'])
                        df_aj = df_aj.sort_values('fecha_dt', ascending=False)
                        
                        df_aj['Suma_Pliegues'] = df_aj['P_Tricipital'] + df_aj['P_Subescapular'] + df_aj['P_Suprailiaco'] + df_aj['P_Abdominal']
                        df_aj['% Graso'] = (df_aj['Suma_Pliegues'] * 0.1537) + 5.783
                        df_aj['Kg Magros'] = df_aj['Peso'] - (df_aj['Peso'] * (df_aj['% Graso'] / 100))
                        
                        ultimo = df_aj.iloc[0]
                        st.markdown(f"#### ⚖️ Último Pesaje ({ultimo['fecha']})")
                        ca1, ca2, ca3 = st.columns(3)
                        ca1.metric("Peso", f"{ultimo['Peso']:.1f} kg")
                        ca2.metric("% Graso (Yuhasz)", f"{ultimo['% Graso']:.2f} %")
                        ca3.metric("Masa Magra", f"{ultimo['Kg Magros']:.1f} kg")
                        
                        df_aj['Mes_Num'] = df_aj['fecha_dt'].dt.month
                        df_aj['Mes'] = df_aj['Mes_Num'].map(meses_esp)
                        
                        meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
                        df_evo_jug = df_aj.groupby('Mes')[['Peso', '% Graso']].mean().reindex(meses_temporada).reset_index()
                        
                        fig_evo_jug = go.Figure()
                        fig_evo_jug.add_trace(go.Bar(x=df_evo_jug['Mes'], y=df_evo_jug['Peso'], name="Peso (kg)", marker_color='#00b4d8'))
                        fig_evo_jug.add_trace(go.Scatter(x=df_evo_jug['Mes'], y=df_evo_jug['% Graso'], name="% Graso", yaxis="y2", mode="lines+markers", line=dict(color="#ff4b4b", width=3)))
                        fig_evo_jug.update_layout(
                            title="Evolución Corporal", 
                            yaxis_title="Peso (kg)", 
                            yaxis2=dict(title="% Grasa", overlaying="y", side="right"),
                            xaxis=dict(categoryorder='array', categoryarray=meses_temporada)
                        )
                        st.plotly_chart(fig_evo_jug, use_container_width=True, key=f"jug_antro_{i}")

                with sub_tabs[5]:
                    st.info("⚙️ Módulo de valoraciones físicas y test neuromusculares vacío.")

