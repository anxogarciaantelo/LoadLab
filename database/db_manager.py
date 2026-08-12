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

@st.cache_data(ttl=3600)
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
                "val_1rm": st.session_state.get("val_1rm", [])
            }
        }
        supabase.table("datos_equipo").update(data_json).eq("equipo_id", eq_id).execute()
        fetch_datos_equipo_supabase.clear()
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {e}")
