import streamlit as st
from supabase import create_client

# --- INICIALIZACIÓN DE SUPABASE ---
# (Asumimos que los secretos están configurados en Streamlit)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# RESTAURAR SESIÓN PARA RLS
if "access_token" in st.session_state and "refresh_token" in st.session_state:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except:
        pass

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_datos_equipo_supabase(equipo_id):
    res_eq = supabase.table("equipos").select("*").eq("id", equipo_id).execute()
    res_dat = supabase.table("datos_equipo").select("*").eq("equipo_id", equipo_id).execute()
    return res_eq.data, res_dat.data

def cargar_datos_equipo(equipo_id):
    try:
        eq_data, dat_data = fetch_datos_equipo_supabase(equipo_id)
        if eq_data and dat_data:
            eq = eq_data[0]
            dat = dat_data[0]
            
            st.session_state.equipo_creado = True
            st.session_state.equipo_id = equipo_id
            st.session_state.nombre_equipo = eq.get("nombre", "")
            st.session_state.categoria_equipo = eq.get("categoria", "")
            st.session_state.division_equipo = eq.get("division", "")
            st.session_state.temporada_equipo = eq.get("temporada", "")
            st.session_state.escudo_equipo = eq.get("escudo_base64", None)
            st.session_state.color_sidebar = eq.get("color_sidebar", "#f1f5f9")
            
            st.session_state.plantilla = dat.get("plantilla", [])
            st.session_state.sesiones = dat.get("sesiones", [])
            st.session_state.lesiones = dat.get("lesiones", [])
            st.session_state.antropometria = dat.get("antropometria", [])
            
            # Cogemos el bloque de valoraciones
            vals = dat.get("valoraciones", {})
            st.session_state.val_inicial = vals.get("val_inicial", [])
            st.session_state.val_rom = vals.get("val_rom", [])
            st.session_state.val_1rm = vals.get("val_1rm", [])
            
            # --- AQUÍ CARGAMOS NUESTROS AJUSTES ---
            st.session_state.ubicacion_local = vals.get("ubicacion_local", "Santiago de Compostela")
            st.session_state.rivales_guardados = vals.get("rivales_guardados", {})
            
            # Cargar config de mapeo desde 'valoraciones' con valores por defecto seguros
            config_guardada = vals.get("config_mapeo", {})
            if not config_guardada:
                config_guardada = {
                    "wellness": {"nombre": "Nombre", "fecha": "Marca temporal", "tqr": "TQR", "fatiga": "W_Fatiga", "sueno": "W_Sueño", "dolor": "W_Dolor", "estres": "W_Estres", "humor": "W_Humor"},
                    "rpe": {"nombre": "Nombre", "fecha": "Marca temporal", "minutos": "MIN", "rpe": "RPE"},
                    "gps": {
                        "nombre": "Player Name", "fecha": "Activity Date",
                        "min_gps": "Time Played", "dis": "Distance (km)", "v_med": "Avg Speed (km/h)", "v_max": "Max Speed (km/h)",
                        "hid_21": "HID distance (> 21.00 km/h)", "hid_24": "HID distance (> 24.00 km/h)", 
                        "spr_24": "# of Sprints (> 24.00 km/h)", "spr_27": "# of Sprints (> 30.00 km/h)",
                        "acc_max": "ACC. MÁXIMA", "acc_2": "# of Accelerations (> 2.00 m/s²)", "acc_3": "# of Accelerations (> 3.00 m/s²)", "acc_4": "# of Accelerations (> 4.00 m/s²)",
                        "dcc_2": "# of Decelerations (> 2.00 m/s²)", "dcc_3": "# of Decelerations (> 3.00 m/s²)", "dcc_4": "# of Decelerations (> 4.00 m/s²)",
                        "r_0_7": "Distance Speed Range (0 - 7 km)", "r_7_14": "Distance Speed Range (7 - 14 km)", "r_14_21": "Distance Speed Range (14 - 21 km)",
                        "r_21_24": "Distance Speed Range (21 - 24 km)", "r_24_27": "Distance Speed Range (24 - 27 km)", "r_27_30": "Distance Speed Range (27 - 30 km)", "r_30_45": "Distance Speed Range (30 - 45 km)"
                    }
                }
            st.session_state.config_mapeo = config_guardada
            
            vals = dat.get("valoraciones", {})
            st.session_state.val_inicial = vals.get("val_inicial", [])
            st.session_state.val_rom = vals.get("val_rom", [])
            st.session_state.val_1rm = vals.get("val_1rm", [])
            
            st.session_state.datos_cargados = True
            return True
    except Exception as e:
        st.error(f"Error al cargar desde Supabase: {e}")
    return False

def guardar_datos():
    if "equipo_id" not in st.session_state:
        return
        
    eq_id = st.session_state.equipo_id
    
    try:
        # Guardar metadatos
        supabase.table("equipos").update({
            "nombre": st.session_state.nombre_equipo,
            "categoria": st.session_state.categoria_equipo,
            "division": st.session_state.division_equipo,
            "temporada": st.session_state.temporada_equipo,
            "escudo_base64": st.session_state.get("escudo_equipo", None),
            "color_sidebar": st.session_state.get("color_sidebar", "#f1f5f9") # <--- AÑADIR ESTA LÍNEA
        }).eq("id", eq_id).execute()
        
        # Guardar arrays
        data_json = {
            "plantilla": st.session_state.plantilla,
            "sesiones": st.session_state.sesiones,
            "lesiones": st.session_state.get("lesiones", []),
            "antropometria": st.session_state.get("antropometria", []),
            "valoraciones": {
                "val_inicial": st.session_state.get("val_inicial", []),
                "val_rom": st.session_state.get("val_rom", []),
                "val_1rm": st.session_state.get("val_1rm", []),
                "config_mapeo": st.session_state.get("config_mapeo", {}),
                
                # --- AQUÍ GUARDAMOS NUESTROS AJUSTES ---
                "ubicacion_local": st.session_state.get("ubicacion_local", "Santiago de Compostela"),
                "rivales_guardados": st.session_state.get("rivales_guardados", {})
            }
        }
        supabase.table("datos_equipo").update(data_json).eq("equipo_id", eq_id).execute()
        fetch_datos_equipo_supabase.clear()
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {e}")
