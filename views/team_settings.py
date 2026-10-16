import streamlit as st
from database.db_manager import guardar_datos
from utils.math_helpers import get_base64_of_bin_file # O la función que uses para el escudo

def render_panel_principal():
    # --- 5. PANEL PRINCIPAL DEL EQUIPO ---
    st.markdown(f"### 🛡️ Gestión del Equipo: {st.session_state.get('nombre_equipo', 'Mi Equipo')}")
    
    # --- BOTÓN Y EXPANDER DE MODIFICAR CUENTA ---
    with st.expander("⚙️ Modificar Configuración y Datos del Equipo"):
        with st.form("form_modificar_cuenta"):
            nuevo_nombre = st.text_input("Nombre del Equipo", value=st.session_state.get("nombre_equipo", ""))
            nueva_categoria = st.text_input("Categoría", value=st.session_state.get("categoria_equipo", ""))
            nueva_division = st.text_input("División", value=st.session_state.get("division_equipo", ""))
            nueva_temporada = st.text_input("Temporada", value=st.session_state.get("temporada_equipo", ""))
            nueva_ubicacion = st.text_input("Ciudad del Equipo (Para clima automático):", value=st.session_state.get("ubicacion_local", ""))
            
            # Selector de color para la barra lateral
            nuevo_color = st.color_picker("Color de la Barra Lateral", value=st.session_state.get("color_sidebar", "#f1f5f9"))
            
            # Escudo
            nuevo_escudo_up = st.file_uploader("Escudo del Equipo (Imagen):", type=["jpg", "png", "jpeg"])
            
            btn_guardar_cuenta = st.form_submit_button("💾 Guardar Cambios")
            if btn_guardar_cuenta:
                st.session_state.nombre_equipo = nuevo_nombre
                st.session_state.categoria_equipo = nueva_categoria
                st.session_state.division_equipo = nueva_division
                st.session_state.temporada_equipo = nueva_temporada
                st.session_state.color_sidebar = nuevo_color 
                st.session_state.ubicacion_local = nueva_ubicacion
                if nuevo_escudo_up:
                    st.session_state.escudo_equipo = get_base64_of_bin_file(nuevo_escudo_up)
                guardar_datos(modulo="configuracion")
                st.success("¡Datos de cuenta actualizados!")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🔄 Mapeador Dinámico de Columnas (Importación Excel)")
    st.caption("Define el nombre EXACTO de las columnas que exporta tu software (WIMU, STATSports, Catapult, Google Forms, etc.) para que LoadLab las lea automáticamente.")

    # Inicializamos el mapeo por defecto si no existe en el estado de la sesión
    if "config_mapeo" not in st.session_state:
        st.session_state.config_mapeo = {
            "wellness": {"tqr": "TQR", "fatiga": "W_Fatiga", "sueno": "W_Sueño", "dolor": "W_Dolor", "estres": "W_Estres", "humor": "W_Humor"},
            "rpe": {"minutos": "MIN", "rpe": "RPE"},
            "gps": {
                "min_gps": "Time Played", "dis": "Distance (km)", "v_med": "Avg Speed (km/h)", "v_max": "Max Speed (km/h)",
                "hid_21": "HID distance (> 21.00 km/h)", "hid_24": "HID distance (> 24.00 km/h)", 
                "spr_24": "# of Sprints (> 24.00 km/h)", "spr_27": "# of Sprints (> 30.00 km/h)",
                "acc_max": "ACC. MÁXIMA", "acc_2": "# of Accelerations (> 2.00 m/s²)", "acc_3": "# of Accelerations (> 3.00 m/s²)", "acc_4": "# of Accelerations (> 4.00 m/s²)",
                "dcc_2": "# of Decelerations (> 2.00 m/s²)", "dcc_3": "# of Decelerations (> 3.00 m/s²)", "dcc_4": "# of Decelerations (> 4.00 m/s²)",
                "r_0_7": "Distance Speed Range (0 - 7 km)", "r_7_14": "Distance Speed Range (7 - 14 km)", "r_14_21": "Distance Speed Range (14 - 21 km)",
                "r_21_24": "Distance Speed Range (21 - 24 km)", "r_24_27": "Distance Speed Range (24 - 27 km)", "r_27_30": "Distance Speed Range (27 - 30 km)", "r_30_45": "Distance Speed Range (30 - 45 km)"
            }
        }

    with st.expander("🛠️ Configurar Nombres de Columnas para Importación", expanded=False):
        with st.form("form_mapeo_columnas"):
            t_well, t_rpe, t_gps1, t_gps2 = st.tabs(["🧠 Wellness", "🔥 RPE", "📡 GPS (General)", "📡 GPS (Rangos y Acc/Dcc)"])
            
            cfg_w = st.session_state.config_mapeo["wellness"]
            cfg_r = st.session_state.config_mapeo["rpe"]
            cfg_g = st.session_state.config_mapeo["gps"]
            
            with t_well:
                st.markdown("**Identificadores**")
                c_w01, c_w02 = st.columns(2)
                n_w_nombre = c_w01.text_input("Columna de Nombre (Wellness):", value=cfg_w.get("nombre", "Nombre"))
                n_w_fecha = c_w02.text_input("Columna de Fecha (Wellness):", value=cfg_w.get("fecha", "Marca temporal"))
                
                st.markdown("---")
                st.markdown("**Columnas del Cuestionario de Bienestar**")
                c_w1, c_w2 = st.columns(2)
                n_tqr = c_w1.text_input("TQR (Recuperación):", value=cfg_w.get("tqr", "TQR"))
                n_fatiga = c_w1.text_input("Fatiga:", value=cfg_w.get("fatiga", "W_Fatiga"))
                n_sueno = c_w1.text_input("Sueño:", value=cfg_w.get("sueno", "W_Sueño"))
                n_dolor = c_w2.text_input("Dolor Muscular:", value=cfg_w.get("dolor", "W_Dolor"))
                n_estres = c_w2.text_input("Estrés:", value=cfg_w.get("estres", "W_Estres"))
                n_humor = c_w2.text_input("Humor/Ánimo:", value=cfg_w.get("humor", "W_Humor"))

            with t_rpe:
                st.markdown("**Identificadores**")
                c_r01, c_r02 = st.columns(2)
                n_r_nombre = c_r01.text_input("Columna de Nombre (RPE):", value=cfg_r.get("nombre", "Nombre"))
                n_r_fecha = c_r02.text_input("Columna de Fecha (RPE):", value=cfg_r.get("fecha", "Marca temporal"))
                
                st.markdown("---")
                st.markdown("**Columnas de Carga Interna**")
                c_r1, c_r2 = st.columns(2)
                n_min = c_r1.text_input("Minutos de Sesión:", value=cfg_r.get("minutos", "MIN"))
                n_rpe = c_r2.text_input("RPE (Esfuerzo):", value=cfg_r.get("rpe", "RPE"))

            with t_gps1:
                st.markdown("**Identificadores**")
                c_g01, c_g02 = st.columns(2)
                n_g_nombre = c_g01.text_input("Columna de Nombre (GPS):", value=cfg_g.get("nombre", "Player Name"))
                n_g_fecha = c_g02.text_input("Columna de Fecha (GPS):", value=cfg_g.get("fecha", "Activity Date"))
                
                st.markdown("---")
                st.markdown("**Métricas Generales y Alta Intensidad**")
                c_g1, c_g2, c_g3 = st.columns(3)
                n_min_gps = c_g1.text_input("Minutos GPS:", value=cfg_g.get("min_gps", "Time Played"))
                n_dis = c_g1.text_input("Distancia Total:", value=cfg_g.get("dis", "Distance (km)"))
                n_vmed = c_g2.text_input("Velocidad Media:", value=cfg_g.get("v_med", "Avg Speed (km/h)"))
                n_vmax = c_g2.text_input("Velocidad Máxima:", value=cfg_g.get("v_max", "Max Speed (km/h)"))
                n_hid21 = c_g3.text_input("HSR (>21 km/h):", value=cfg_g.get("hid_21", "HID distance (> 21.00 km/h)"))
                n_hid24 = c_g3.text_input("Sprint (>24 km/h):", value=cfg_g.get("hid_24", "HID distance (> 24.00 km/h)"))
                n_spr24 = c_g3.text_input("Nº Sprints (>24):", value=cfg_g.get("spr_24", "# of Sprints (> 24.00 km/h)"))
                n_spr27 = c_g3.text_input("Nº Sprints (>27):", value=cfg_g.get("spr_27", "# of Sprints (> 30.00 km/h)"))

            with t_gps2:
                st.markdown("**Rangos de Velocidad y Acelerometría**")
                c_g4, c_g5, c_g6 = st.columns(3)
                n_acc_max = c_g4.text_input("Aceleración Máx:", value=cfg_g.get("acc_max", "ACC. MÁXIMA"))
                n_acc2 = c_g4.text_input("ACC (>2 m/s²):", value=cfg_g.get("acc_2", "# of Accelerations (> 2.00 m/s²)"))
                n_acc3 = c_g4.text_input("ACC (>3 m/s²):", value=cfg_g.get("acc_3", "# of Accelerations (> 3.00 m/s²)"))
                n_acc4 = c_g4.text_input("ACC (>4 m/s²):", value=cfg_g.get("acc_4", "# of Accelerations (> 4.00 m/s²)"))
                n_dcc2 = c_g5.text_input("DCC (>2 m/s²):", value=cfg_g.get("dcc_2", "# of Decelerations (> 2.00 m/s²)"))
                n_dcc3 = c_g5.text_input("DCC (>3 m/s²):", value=cfg_g.get("dcc_3", "# of Decelerations (> 3.00 m/s²)"))
                n_dcc4 = c_g5.text_input("DCC (>4 m/s²):", value=cfg_g.get("dcc_4", "# of Decelerations (> 4.00 m/s²)"))
                n_r0_7 = c_g6.text_input("Rango 0-7 km/h:", value=cfg_g.get("r_0_7", "Distance Speed Range (0 - 7 km)"))
                n_r7_14 = c_g6.text_input("Rango 7-14 km/h:", value=cfg_g.get("r_7_14", "Distance Speed Range (7 - 14 km)"))
                n_r14_21 = c_g6.text_input("Rango 14-21 km/h:", value=cfg_g.get("r_14_21", "Distance Speed Range (14 - 21 km)"))
                n_r21_24 = c_g6.text_input("Rango 21-24 km/h:", value=cfg_g.get("r_21_24", "Distance Speed Range (21 - 24 km)"))
                n_r24_27 = c_g6.text_input("Rango 24-27 km/h:", value=cfg_g.get("r_24_27", "Distance Speed Range (24 - 27 km)"))
                n_r27_30 = c_g6.text_input("Rango 27-30 km/h:", value=cfg_g.get("r_27_30", "Distance Speed Range (27 - 30 km)"))
                n_r30_45 = c_g6.text_input("Rango >30 km/h:", value=cfg_g.get("r_30_45", "Distance Speed Range (30 - 45 km)"))

            btn_mapeo = st.form_submit_button("💾 Guardar Plantilla de Importación", use_container_width=True)
            
            if btn_mapeo:
                st.session_state.config_mapeo = {
                    "wellness": {"nombre": n_w_nombre, "fecha": n_w_fecha, "tqr": n_tqr, "fatiga": n_fatiga, "sueno": n_sueno, "dolor": n_dolor, "estres": n_estres, "humor": n_humor},
                    "rpe": {"nombre": n_r_nombre, "fecha": n_r_fecha, "minutos": n_min, "rpe": n_rpe},
                    "gps": {
                        "nombre": n_g_nombre, "fecha": n_g_fecha,
                        "min_gps": n_min_gps, "dis": n_dis, "v_med": n_vmed, "v_max": n_vmax,
                        "hid_21": n_hid21, "hid_24": n_hid24, "spr_24": n_spr24, "spr_27": n_spr27,
                        "acc_max": n_acc_max, "acc_2": n_acc2, "acc_3": n_acc3, "acc_4": n_acc4,
                        "dcc_2": n_dcc2, "dcc_3": n_dcc3, "dcc_4": n_dcc4,
                        "r_0_7": n_r0_7, "r_7_14": n_r7_14, "r_14_21": n_r14_21,
                        "r_21_24": n_r21_24, "r_24_27": n_r24_27, "r_27_30": n_r27_30, "r_30_45": n_r30_45
                    }
                }
                guardar_datos(modulo="configuracion")
                st.success("✅ Configuración de importación actualizada con éxito.")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🌦️ Mantenimiento del Clima")
    st.caption("Si tienes sesiones antiguas sin datos del clima, pulsa este botón para descargar el histórico de Open-Meteo de forma automática.")
    
    if st.button("☁️ Sincronizar Clima en Sesiones Pasadas", use_container_width=True):
        from utils.math_helpers import obtener_clima 
        
        # 1. Vaciamos la memoria para obligar a la app a preguntar de nuevo a la API
        st.cache_data.clear()
        
        sesiones_actualizadas = 0
        errores = []
        
        with st.spinner("Conectando con Open-Meteo y sincronizando histórico..."):
            for s in st.session_state.sesiones:
                # Determinamos la ciudad correspondiente
                ciudad = st.session_state.get("ubicacion_local", "")
                
                if s.get("tipo") != "Entrenamiento" and s.get("condicion") == "Fuera":
                    rival = s.get("rival", "")
                    rival_info = st.session_state.get("rivales_guardados", {}).get(rival, {})
                    
                    if isinstance(rival_info, dict) and rival_info.get("ciudad"):
                        ciudad = rival_info.get("ciudad")
                    elif s.get("ciudad_manual"):
                        ciudad = s.get("ciudad_manual")
                
                # 2. Comprobamos dónde está el fallo
                if not ciudad:
                    errores.append(f"Sesión {s['fecha']}: No hay ciudad definida en la configuración.")
                    continue
                    
                clima_data = obtener_clima(ciudad, s["fecha"])
                if clima_data:
                    s["clima"] = clima_data
                    sesiones_actualizadas += 1
                else:
                    errores.append(f"Sesión {s['fecha']}: La API falló al buscar el clima de '{ciudad}'.")
                            
            if sesiones_actualizadas > 0:
                guardar_datos(modulo="sesiones")
                st.success(f"✅ ¡Éxito! Se ha actualizado el clima para {sesiones_actualizadas} sesiones.")
            else:
                st.error("No se han podido actualizar las sesiones. Revisa el registro de errores:")
                # 3. Mostramos los errores exactos en pantalla
                if errores:
                    with st.expander("🔍 Ver detalles del error"):
                        for e in errores[:10]:  # Mostramos los 10 primeros para no saturar
                            st.write(e)

    with st.expander("⚠️ Zona de Peligro: Borrado total de datos"):
        st.error("¡CUIDADO! Esta acción eliminará permanentemente la plantilla, todas las sesiones, historial médico y valoraciones de este equipo. No se puede deshacer.")
        
        # Checkbox de seguridad
        confirmacion_borrado = st.checkbox("Entiendo las consecuencias y quiero vaciar la base de datos de este equipo.")
        
        # El botón solo se activará si se ha marcado el checkbox (disabled=not confirmacion_borrado)
        if st.button("🔄 Sí, borrar todos los datos", use_container_width=True, disabled=not confirmacion_borrado):
            st.session_state.plantilla = []
            st.session_state.sesiones = []
            st.session_state.lesiones = []
            st.session_state.antropometria = []
            st.session_state.val_inicial = []
            st.session_state.val_rom = []
            st.session_state.val_1rm = []
            guardar_datos()
            st.success("Datos vaciados. El equipo está limpio.")
            st.rerun()
        
    if st.button("🚪 Cerrar Sesión / Cambiar Equipo", use_container_width=True):
        try:
            # Aquí iría tu código de supabase.auth.sign_out() si corresponde
            pass
        except:
            pass
        st.session_state.clear()
        st.rerun()
