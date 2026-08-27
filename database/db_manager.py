import streamlit as st
from supabase import create_client
import base64
import unicodedata

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

if "access_token" in st.session_state and "refresh_token" in st.session_state:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except:
        pass

def limpiar_nombre_archivo(texto):
    texto_limpio = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_limpio.replace(' ', '_').lower()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_datos_equipo_supabase(equipo_id):
    res_eq = supabase.table("equipos").select("*").eq("id", equipo_id).execute()
    res_plan = supabase.table("plantilla").select("*").eq("equipo_id", equipo_id).execute()
    res_ses = supabase.table("sesiones").select("*").eq("equipo_id", equipo_id).execute()
    res_les = supabase.table("lesiones_historial").select("*").eq("equipo_id", equipo_id).execute()
    res_ant = supabase.table("antropometria_historial").select("*").eq("equipo_id", equipo_id).execute()
    res_cfg = supabase.table("configuracion_equipo").select("*").eq("equipo_id", equipo_id).execute()
    return res_eq.data, res_plan.data, res_ses.data, res_les.data, res_ant.data, res_cfg.data

def cargar_datos_equipo(equipo_id):
    try:
        eq_data, plan_data, ses_data, les_data, ant_data, cfg_data = fetch_datos_equipo_supabase(equipo_id)
        if eq_data:
            eq = eq_data[0]
            st.session_state.equipo_creado = True
            st.session_state.equipo_id = equipo_id
            st.session_state.nombre_equipo = eq.get("nombre", "")
            st.session_state.categoria_equipo = eq.get("categoria", "")
            st.session_state.division_equipo = eq.get("division", "")
            st.session_state.temporada_equipo = eq.get("temporada", "")
            st.session_state.escudo_equipo = eq.get("escudo_base64", None) 
            st.session_state.color_sidebar = eq.get("color_sidebar", "#f1f5f9")
            
            plantilla = []
            for p in plan_data:
                plantilla.append({
                    "JUGADOR": p["jugador"], "POS": p["pos"], "pos_1": p["pos_1"],
                    "pos_2": p["pos_2"], "edad": p["edad"], "dorsal": p["dorsal"],
                    "altura": p["altura"], "lateralidad": p["lateralidad"],
                    "foto": p["foto_url"] # AHORA CARGAMOS LA URL LIGERA
                })
            st.session_state.plantilla = plantilla

            sesiones = []
            for s in ses_data:
                sesiones.append({
                    "fecha": s["fecha"], "tipo": s["tipo"], "descripcion": s["descripcion"],
                    "competicion": s["competicion"], "rival": s["rival"], "condicion": s["condicion"],
                    "ciudad_manual": s["ciudad_manual"], "goles_favor": s["goles_favor"],
                    "goles_contra": s["goles_contra"], "clima": s["clima"],
                    "disponibilidad": s["disponibilidad"], "estadisticas_partido": s["estadisticas_partido"],
                    "estadisticas_invitados": s["estadisticas_invitados"], "informe_generado": s["informe_generado"],
                    "datos_informe": s["datos_informe"]
                })
            st.session_state.sesiones = sesiones
            st.session_state.lesiones = les_data
            st.session_state.antropometria = [a["datos"] for a in ant_data]

            cfg = cfg_data[0] if cfg_data else {}
            st.session_state.val_inicial = cfg.get("val_inicial", [])
            st.session_state.val_rom = cfg.get("val_rom", [])
            st.session_state.val_1rm = cfg.get("val_1rm", [])
            st.session_state.ubicacion_local = cfg.get("ubicacion_local", "Santiago de Compostela")
            st.session_state.rivales_guardados = cfg.get("rivales_guardados", {})
            
            st.session_state.config_mapeo = cfg.get("config_mapeo", {})
            if not st.session_state.config_mapeo:
                st.session_state.config_mapeo = {
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
            st.session_state.datos_cargados = True
            reconstruir_dataframes_globales()
            return True
    except Exception as e:
        st.error(f"Error al cargar desde Supabase: {e}")
    return False

def guardar_datos(modulo="todo"):
    if "equipo_id" not in st.session_state: return
    eq_id = st.session_state.equipo_id
    
    try:
        # 1. GUARDAR EQUIPO Y CONFIGURACIÓN
        if modulo in ["todo", "equipo", "configuracion"]:
            supabase.table("equipos").update({
                "nombre": st.session_state.nombre_equipo, "categoria": st.session_state.categoria_equipo,
                "division": st.session_state.division_equipo, "temporada": st.session_state.temporada_equipo,
                "escudo_base64": st.session_state.get("escudo_equipo", None)
            }).eq("id", eq_id).execute()

            supabase.table("configuracion_equipo").upsert({
                "equipo_id": eq_id, "ubicacion_local": st.session_state.get("ubicacion_local", "Santiago de Compostela"),
                "color_sidebar": st.session_state.get("color_sidebar", "#f1f5f9"), "rivales_guardados": st.session_state.get("rivales_guardados", {}),
                "config_mapeo": st.session_state.get("config_mapeo", {}), "val_inicial": st.session_state.get("val_inicial", []),
                "val_rom": st.session_state.get("val_rom", []), "val_1rm": st.session_state.get("val_1rm", [])
            }).execute()

        # 2. GUARDAR PLANTILLA
        if modulo in ["todo", "plantilla"]:
            plantilla_db = []
            for p in st.session_state.plantilla:
                foto_url = p.get("foto")
                if foto_url and not str(foto_url).startswith("http") and len(foto_url) > 1000:
                    try:
                        b64_clean = foto_url.split(",")[1] if foto_url.startswith("data:image") else foto_url
                        img_bytes = base64.b64decode(b64_clean)
                        nombre_arch = f"{eq_id}/jugadores/{limpiar_nombre_archivo(p['JUGADOR'])}.jpg"
                        supabase.storage.from_("loadlab_media").upload(nombre_arch, img_bytes, file_options={"content-type": "image/jpeg", "upsert": "true"})
                        foto_url = supabase.storage.from_("loadlab_media").get_public_url(nombre_arch)
                        p["foto"] = foto_url 
                    except Exception as e:
                        print(f"Error subiendo foto al guardar: {e}")
                
                plantilla_db.append({
                    "equipo_id": eq_id, "jugador": p.get("JUGADOR"), "pos": p.get("POS"),
                    "pos_1": p.get("pos_1"), "pos_2": p.get("pos_2"), "edad": p.get("edad"),
                    "dorsal": p.get("dorsal"), "altura": p.get("altura"),
                    "lateralidad": p.get("lateralidad"), "foto_url": foto_url
                })
            supabase.table("plantilla").delete().eq("equipo_id", eq_id).execute()
            if plantilla_db: supabase.table("plantilla").insert(plantilla_db).execute()

        # 3. GUARDAR SESIONES
        if modulo in ["todo", "sesiones"]:
            sesiones_db = []
            for s in st.session_state.sesiones:
                sesiones_db.append({
                    "equipo_id": eq_id, "fecha": s.get("fecha"), "tipo": s.get("tipo"), "descripcion": s.get("descripcion"),
                    "competicion": s.get("competicion"), "rival": s.get("rival"), "condicion": s.get("condicion"),
                    "ciudad_manual": s.get("ciudad_manual"), "goles_favor": s.get("goles_favor"), "goles_contra": s.get("goles_contra"),
                    "clima": s.get("clima", {}), "disponibilidad": s.get("disponibilidad", {}), "estadisticas_partido": s.get("estadisticas_partido", {}),
                    "estadisticas_invitados": s.get("estadisticas_invitados", []), "informe_generado": s.get("informe_generado", False),
                    "datos_informe": s.get("datos_informe", [])
                })
            supabase.table("sesiones").delete().eq("equipo_id", eq_id).execute()
            if sesiones_db: supabase.table("sesiones").insert(sesiones_db).execute()

        # 4. GUARDAR LESIONES
        if modulo in ["todo", "lesiones"]:
            lesiones_db = []
            for l in st.session_state.lesiones:
                lesiones_db.append({
                    "equipo_id": eq_id, "fecha_registro": l.get("fecha_registro"), "id_sesion": l.get("id_sesion"),
                    "tipo_sesion": l.get("tipo_sesion"), "jugador": l.get("jugador"), "tipo": l.get("tipo"),
                    "zona": l.get("zona"), "lado": l.get("lado"), "lateralidad": l.get("lateralidad"),
                    "contacto": l.get("contacto"), "cesped": l.get("cesped"), "recidiva": l.get("recidiva"),
                    "estado": l.get("estado"), "dias_baja": l.get("dias_baja"), "comentarios": l.get("comentarios")
                })
            supabase.table("lesiones_historial").delete().eq("equipo_id", eq_id).execute()
            if lesiones_db: supabase.table("lesiones_historial").insert(lesiones_db).execute()

        # 5. GUARDAR ANTROPOMETRÍA
        if modulo in ["todo", "antropometria"]:
            antro_db = [{"equipo_id": eq_id, "fecha": a.get("fecha"), "jugador": a.get("jugador"), "datos": a} for a in st.session_state.antropometria]
            supabase.table("antropometria_historial").delete().eq("equipo_id", eq_id).execute()
            if antro_db: supabase.table("antropometria_historial").insert(antro_db).execute()

        if modulo in ["todo", "configuracion"]:
            fetch_datos_equipo_supabase.clear()

        reconstruir_dataframes_globales()
            
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {e}")

import pandas as pd

def reconstruir_dataframes_globales():
    """Construye los DataFrames pesados una sola vez y los guarda en memoria RAM listos para usar"""
    
    # 1. DataFrame de Plantilla
    if "plantilla" in st.session_state and st.session_state.plantilla:
        st.session_state.df_plantilla = pd.DataFrame(st.session_state.plantilla)
    else:
        st.session_state.df_plantilla = pd.DataFrame()

    # 2. DataFrame de Lesiones
    if "lesiones" in st.session_state and st.session_state.lesiones:
        st.session_state.df_lesiones = pd.DataFrame(st.session_state.lesiones)
    else:
        st.session_state.df_lesiones = pd.DataFrame()

    # 3. EL MÁS IMPORTANTE: El "Master" de GPS, Carga y Wellness
    # En lugar de que 4_GPS.py o 1_Entrenamiento.py hagan esto en cada clic, lo hacemos aquí.
    datos_completos = []
    if "sesiones" in st.session_state:
        for s in st.session_state.sesiones:
            if s.get("informe_generado") and s.get("datos_informe"):
                for d in s["datos_informe"]:
                    # Hacemos una copia de los datos del jugador
                    row = d.copy() 
                    # Le inyectamos los datos de la sesión padre
                    row["FECHA"] = s.get("fecha")
                    row["TIPO_SESION"] = s.get("tipo")
                    row["MD"] = s.get("descripcion")
                    row["COMPETICION"] = s.get("competicion", "")
                    datos_completos.append(row)
                    
    if datos_completos:
        # Lo guardamos en session_state listo para usar en cualquier gráfica
        st.session_state.df_master_informes = pd.DataFrame(datos_completos)
    else:
        st.session_state.df_master_informes = pd.DataFrame()
