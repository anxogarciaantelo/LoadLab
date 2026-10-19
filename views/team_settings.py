import streamlit as st
from database.db_manager import guardar_datos
from utils.math_helpers import get_base64_of_bin_file

def render_panel_principal():
    # Envolver en 3 columnas principales
    col_gestion, col_mapeo, col_clima = st.columns(3)
    
    # --- COLUMNA 1: GESTIÓN DEL EQUIPO ---
    with col_gestion:
        st.markdown(f"#### 🛡️ Gestión del Equipo")
        with st.expander("⚙️ Modificar Configuración y Datos", expanded=True):
            with st.form("form_modificar_cuenta"):
                nuevo_nombre = st.text_input("Nombre del Equipo", value=st.session_state.get("nombre_equipo", ""))
                nueva_categoria = st.text_input("Categoría", value=st.session_state.get("categoria_equipo", ""))
                nueva_division = st.text_input("División", value=st.session_state.get("division_equipo", ""))
                nueva_temporada = st.text_input("Temporada", value=st.session_state.get("temporada_equipo", ""))
                nueva_ubicacion = st.text_input("Ciudad del Equipo (Para clima):", value=st.session_state.get("ubicacion_local", ""))
                nuevo_escudo_up = st.file_uploader("Escudo del Equipo (Imagen):", type=["jpg", "png", "jpeg"])
                
                btn_guardar_cuenta = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                if btn_guardar_cuenta:
                    st.session_state.nombre_equipo = nuevo_nombre
                    st.session_state.categoria_equipo = nueva_categoria
                    st.session_state.division_equipo = nueva_division
                    st.session_state.temporada_equipo = nueva_temporada
                    st.session_state.ubicacion_local = nueva_ubicacion
                    if nuevo_escudo_up:
                        st.session_state.escudo_equipo = get_base64_of_bin_file(nuevo_escudo_up)
                    guardar_datos(modulo="configuracion")
                    st.success("¡Datos actualizados!")
                    st.rerun()
        with st.expander("🔄 Sincronización Retrospectiva de GPS"):
            st.caption("Recalcula y traslada los datos de GPS (incluidos los minutos) a jugadores sin dispositivo basándose en su estado, posición y minutos de partido, en todas las sesiones pasadas.")
            if st.button("🚀 Ejecutar Sincronización Histórica", use_container_width=True, type="primary"):
                from utils.math_helpers import aplicar_imputacion_gps_global
                sesiones_modificadas = 0
                for s in st.session_state.sesiones:
                    if s.get("informe_generado") and s.get("datos_informe"):
                        s["datos_informe"] = aplicar_imputacion_gps_global(s["datos_informe"], s, st.session_state.plantilla)
                        sesiones_modificadas += 1
                
                if sesiones_modificadas > 0:
                    guardar_datos(modulo="sesiones")
                    st.success(f"✅ ¡{sesiones_modificadas} sesiones recalculadas y protegidas con la etiqueta GPS_VIRTUAL!")
                    st.rerun()
                else:
                    st.info("No hay sesiones con datos para sincronizar.")
    # --- COLUMNA 2: MAPEADOR DE EXCEL ---
    with col_mapeo:
        st.markdown("#### 🔄 Mapeador (Excel)")
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

        with st.expander("🛠️ Configurar Nombres de Columnas", expanded=True):
            with st.form("form_mapeo_columnas"):
                t_well, t_rpe, t_gps1, t_gps2 = st.tabs(["🧠 Well", "🔥 RPE", "📡 GPS 1", "📡 GPS 2"])
                
                cfg_w = st.session_state.config_mapeo["wellness"]
                cfg_r = st.session_state.config_mapeo["rpe"]
                cfg_g = st.session_state.config_mapeo["gps"]
                
                with t_well:
                    n_w_nombre = st.text_input("Nombre (Well):", value=cfg_w.get("nombre", "Nombre"))
                    n_w_fecha = st.text_input("Fecha (Well):", value=cfg_w.get("fecha", "Marca temporal"))
                    n_tqr = st.text_input("TQR:", value=cfg_w.get("tqr", "TQR"))
                    n_fatiga = st.text_input("Fatiga:", value=cfg_w.get("fatiga", "W_Fatiga"))
                    n_sueno = st.text_input("Sueño:", value=cfg_w.get("sueno", "W_Sueño"))
                    n_dolor = st.text_input("Dolor:", value=cfg_w.get("dolor", "W_Dolor"))
                    n_estres = st.text_input("Estrés:", value=cfg_w.get("estres", "W_Estres"))
                    n_humor = st.text_input("Humor:", value=cfg_w.get("humor", "W_Humor"))

                with t_rpe:
                    n_r_nombre = st.text_input("Nombre (RPE):", value=cfg_r.get("nombre", "Nombre"))
                    n_r_fecha = st.text_input("Fecha (RPE):", value=cfg_r.get("fecha", "Marca temporal"))
                    n_min = st.text_input("Minutos:", value=cfg_r.get("minutos", "MIN"))
                    n_rpe = st.text_input("RPE:", value=cfg_r.get("rpe", "RPE"))

                with t_gps1:
                    n_g_nombre = st.text_input("Nombre (GPS):", value=cfg_g.get("nombre", "Player Name"))
                    n_g_fecha = st.text_input("Fecha (GPS):", value=cfg_g.get("fecha", "Activity Date"))
                    n_min_gps = st.text_input("Minutos GPS:", value=cfg_g.get("min_gps", "Time Played"))
                    n_dis = st.text_input("Distancia:", value=cfg_g.get("dis", "Distance (km)"))
                    n_vmed = st.text_input("V. Media:", value=cfg_g.get("v_med", "Avg Speed (km/h)"))
                    n_vmax = st.text_input("V. Máxima:", value=cfg_g.get("v_max", "Max Speed (km/h)"))
                    n_hid21 = st.text_input("HSR (>21):", value=cfg_g.get("hid_21", "HID distance (> 21.00 km/h)"))
                    n_hid24 = st.text_input("Sprint (>24):", value=cfg_g.get("hid_24", "HID distance (> 24.00 km/h)"))
                    n_spr24 = st.text_input("Nº SPR (>24):", value=cfg_g.get("spr_24", "# of Sprints (> 24.00 km/h)"))
                    n_spr27 = st.text_input("Nº SPR (>27):", value=cfg_g.get("spr_27", "# of Sprints (> 30.00 km/h)"))

                with t_gps2:
                    n_acc_max = st.text_input("ACC Máx:", value=cfg_g.get("acc_max", "ACC. MÁXIMA"))
                    n_acc2 = st.text_input("ACC (>2):", value=cfg_g.get("acc_2", "# of Accelerations (> 2.00 m/s²)"))
                    n_acc3 = st.text_input("ACC (>3):", value=cfg_g.get("acc_3", "# of Accelerations (> 3.00 m/s²)"))
                    n_acc4 = st.text_input("ACC (>4):", value=cfg_g.get("acc_4", "# of Accelerations (> 4.00 m/s²)"))
                    n_dcc2 = st.text_input("DCC (>2):", value=cfg_g.get("dcc_2", "# of Decelerations (> 2.00 m/s²)"))
                    n_dcc3 = st.text_input("DCC (>3):", value=cfg_g.get("dcc_3", "# of Decelerations (> 3.00 m/s²)"))
                    n_dcc4 = st.text_input("DCC (>4):", value=cfg_g.get("dcc_4", "# of Decelerations (> 4.00 m/s²)"))
                    n_r0_7 = st.text_input("0-7 km/h:", value=cfg_g.get("r_0_7", "Distance Speed Range (0 - 7 km)"))
                    n_r7_14 = st.text_input("7-14 km/h:", value=cfg_g.get("r_7_14", "Distance Speed Range (7 - 14 km)"))
                    n_r14_21 = st.text_input("14-21 km/h:", value=cfg_g.get("r_14_21", "Distance Speed Range (14 - 21 km)"))
                    n_r21_24 = st.text_input("21-24 km/h:", value=cfg_g.get("r_21_24", "Distance Speed Range (21 - 24 km)"))
                    n_r24_27 = st.text_input("24-27 km/h:", value=cfg_g.get("r_24_27", "Distance Speed Range (24 - 27 km)"))
                    n_r27_30 = st.text_input("27-30 km/h:", value=cfg_g.get("r_27_30", "Distance Speed Range (27 - 30 km)"))
                    n_r30_45 = st.text_input(">30 km/h:", value=cfg_g.get("r_30_45", "Distance Speed Range (30 - 45 km)"))

                btn_mapeo = st.form_submit_button("💾 Guardar Mapeo", use_container_width=True)
                
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
                    st.success("✅ Mapeo actualizado.")
                    st.rerun()

    # --- COLUMNA 3: MANTENIMIENTO DEL CLIMA ---
    with col_clima:
        st.markdown("#### 🌦️ Sincronizar Clima")
        with st.expander("☁️ Descargar Histórico (Meteo)", expanded=True):
            st.caption("Añade el clima a sesiones pasadas.")
            if st.button("☁️ Sincronizar Clima", use_container_width=True):
                from utils.math_helpers import obtener_clima 
                st.cache_data.clear()
                sesiones_actualizadas = 0
                errores = []
                
                with st.spinner("Conectando con Open-Meteo..."):
                    for s in st.session_state.sesiones:
                        ciudad = st.session_state.get("ubicacion_local", "")
                        if s.get("tipo") != "Entrenamiento" and s.get("condicion") == "Fuera":
                            rival = s.get("rival", "")
                            rival_info = st.session_state.get("rivales_guardados", {}).get(rival, {})
                            if isinstance(rival_info, dict) and rival_info.get("ciudad"): ciudad = rival_info.get("ciudad")
                            elif s.get("ciudad_manual"): ciudad = s.get("ciudad_manual")
                        
                        if not ciudad:
                            errores.append(f"Sesión {s['fecha']}: No hay ciudad definida.")
                            continue
                            
                        clima_data = obtener_clima(ciudad, s["fecha"])
                        if clima_data:
                            s["clima"] = clima_data
                            sesiones_actualizadas += 1
                        else:
                            errores.append(f"Sesión {s['fecha']}: Fallo API en '{ciudad}'.")
                                    
                    if sesiones_actualizadas > 0:
                        guardar_datos(modulo="sesiones")
                        st.success(f"✅ ¡{sesiones_actualizadas} sesiones actualizadas!")
                    else:
                        st.error("No se actualizaron sesiones.")
                        if errores:
                            for e in errores[:5]: st.write(e)

    # --- ZONA DE PELIGRO (No abarca el ancho total) ---
    st.markdown("---")
    col_peligro, col_vacio = st.columns([1.5, 2])
    with col_peligro:
        with st.expander("⚠️ Zona de Peligro: Borrado total"):
            st.error("¡CUIDADO! Se eliminará permanentemente la plantilla y el historial.")
            confirmacion_borrado = st.checkbox("Entiendo las consecuencias.")
            
            if st.button("🔄 Sí, borrar todos los datos", use_container_width=True, disabled=not confirmacion_borrado):
                st.session_state.plantilla = []
                st.session_state.sesiones = []
                st.session_state.lesiones = []
                st.session_state.antropometria = []
                st.session_state.val_inicial = []
                st.session_state.val_rom = []
                st.session_state.val_1rm = []
                guardar_datos()
                st.success("Datos vaciados.")
                st.rerun()
