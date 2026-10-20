import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import streamlit as st
import base64
import io
from PIL import Image

def safe_float(val):
    try:
        if pd.isna(val) or val == "" or val == " ": return 0.0
        return float(val)
    except:
        return 0.0

def get_col(row, possible_names):
    # Motor de búsqueda robusto: ignora mayúsculas y espacios invisibles en el Excel
    row_keys = {str(k).strip().lower(): k for k in row.index}
    for name in possible_names:
        clean_name = str(name).strip().lower()
        if clean_name in row_keys:
            original_key = row_keys[clean_name]
            if not pd.isna(row[original_key]):
                try:
                    return float(row[original_key])
                except:
                    pass
    return 0.0

def limpiar_nombre(nombre):
    if pd.isna(nombre): return ""
    return str(nombre).strip().lower()

def extraer_minutos(tiempo_str):
    if pd.isna(tiempo_str): return 0
    if isinstance(tiempo_str, (int, float)): return int(tiempo_str)
    match = re.search(r"(\d+)'", str(tiempo_str))
    if match: return int(match.group(1))
    return 0

def obtener_numero_semana(fecha_str):
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    return fecha.isocalendar()[1]

def obtener_rango_fechas_semana(fecha_str):
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
    lunes = fecha - timedelta(days=fecha.weekday())
    domingo = lunes + timedelta(days=6)
    return lunes.strftime("%d/%m"), domingo.strftime("%d/%m"), lunes, domingo

def calcular_ewma_historico(_sesiones, fecha_objetivo):
    """
    Versión optimizada: Utiliza df_master_informes del session_state si existe,
    evitando la costosa reconstrucción iterativa de diccionarios.
    """
    import pandas as pd
    import numpy as np
    import streamlit as st
    
    metricas = {'CARGA': '', 'DIS AI': ' HSR', 'ACC': ' ACC'}
    res = {}
    fecha_fin = pd.to_datetime(fecha_objetivo)
    
    # 1. Usar la caché maestra si está disponible para O(1) de acceso a datos base
    if "df_master_informes" in st.session_state and not st.session_state.df_master_informes.empty:
        df_hist = st.session_state.df_master_informes[st.session_state.df_master_informes['FECHA'] <= fecha_objetivo].copy()
    else:
        # Fallback de seguridad (solo se ejecuta si la caché falló)
        df_hist = pd.DataFrame([
            {
                "fecha": s["fecha"], "JUGADOR": d["JUGADOR"], 
                "CARGA": float(d.get("CARGA", 0)), 
                "DIS AI": float(d.get("DIS AI", d.get("HID >21", 0))), 
                "ACC": float(d.get("ACC", d.get("ACC >3", 0)))
            }
            for s in _sesiones if s.get("informe_generado") and s["fecha"] <= fecha_objetivo
            for d in s["datos_informe"]
        ])
        if not df_hist.empty:
            df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
    
    if df_hist.empty: return {}
    
    # Asegurar formato fecha para el pivot
    if 'FECHA' in df_hist.columns:
        df_hist['fecha'] = pd.to_datetime(df_hist['FECHA'])
        
    for jug in df_hist['JUGADOR'].unique():
        res[jug] = {}
        
    for col_metrica, sufijo in metricas.items():
        if col_metrica not in df_hist.columns: continue
        
        df_pivot = df_hist.pivot_table(index='fecha', columns='JUGADOR', values=col_metrica, aggfunc='sum').fillna(0)
        if df_pivot.empty: continue
            
        fecha_ini = min(df_pivot.index.min(), fecha_fin)
        rango_fechas = pd.date_range(start=fecha_ini, end=fecha_fin, freq='D')
        df_pivot = df_pivot.reindex(rango_fechas, fill_value=0)
        
        # Máscara para evitar que el EWMA se diluya antes de que el jugador llegue al club
        for col in df_pivot.columns:
            s_cargas = df_pivot[col]
            primer_idx = s_cargas[s_cargas > 0].first_valid_index()
            if primer_idx:
                df_pivot.loc[:primer_idx - pd.Timedelta(days=1), col] = np.nan

        # Cálculo vectorizado C y A
        aguda = df_pivot.ewm(span=7, adjust=False).mean()
        cronica = df_pivot.ewm(span=28, adjust=False).mean()
        
        try:
            aguda_hoy = aguda.loc[fecha_fin]
            cronica_hoy = cronica.loc[fecha_fin]
        except KeyError:
            continue
        
        for jug in df_pivot.columns:
            a = aguda_hoy.get(jug, 0.0)
            c = cronica_hoy.get(jug, 0.0)
            a_sem = (a if pd.notna(a) else 0.0) * 7
            c_sem = (c if pd.notna(c) else 0.0) * 7
            
            # Control de under-loading crónico (evita ratios infinitos irreales tras parón de verano)
            c_sem_seguro = max(c_sem, 10.0) if col_metrica == 'CARGA' else max(c_sem, 1.0)
            r = a_sem / c_sem_seguro if c_sem > 0 else 1.0
            
            res[jug][f"EWMA AGUDA{sufijo}"] = round(a_sem, 2)
            res[jug][f"EWMA CRÓNICA{sufijo}"] = round(c_sem, 2)
            res[jug][f"RATIO A/C{sufijo}"] = round(r, 2)
            
    return res

def color_ratio_ac(valor):
    if valor >= 1.5: return '#ef4444'
    if valor >= 1.31: return '#f59e0b'
    if valor >= 0.8: return '#10b981'
    if valor > 0: return '#3b82f6'
    return '#64748b'

def categorizar_duracion(dias):
    if pd.isna(dias) or dias is None or dias == "": return "Activa"
    dias = int(dias)
    if dias <= 3: return "Mínima (1-3d)"
    if dias <= 7: return "Leve (4-7d)"
    if dias <= 28: return "Moderada (8-28d)"
    return "Grave (>28d)"

def calcular_monotonia_7d(_sesiones, jugador, fecha_objetivo, metrica="CARGA", devolver_strain=False):
    fecha_fin = datetime.strptime(fecha_objetivo, "%Y-%m-%d")
    fecha_ini = fecha_fin - timedelta(days=6)
    
    dic_cargas = {(fecha_ini + timedelta(days=i)).strftime("%Y-%m-%d"): 0.0 for i in range(7)}
    
    for s in _sesiones: 
        if s.get("informe_generado") and s["fecha"] in dic_cargas:
            for d in s["datos_informe"]:
                if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jugador):
                    dic_cargas[s["fecha"]] += safe_float(d.get(metrica, 0))
                    break
                    
    cargas = list(dic_cargas.values())
    carga_7d = float(np.sum(cargas))
    media = float(np.mean(cargas))
    desviacion = float(np.std(cargas, ddof=1)) 
    
    if desviacion > 0:
        monotonia = media / desviacion
    elif media > 0:
        monotonia = 4.0 
    else:
        monotonia = 0.0
        
    if devolver_strain:
        return monotonia, carga_7d * monotonia
    return monotonia

def validar_estructuras_memoria():
    for p in st.session_state.get("plantilla", []):
        if "lateralidad" not in p: p["lateralidad"] = "Diestro"
        if "foto" not in p: p["foto"] = None

    for les in st.session_state.get("lesiones", []):
        if "dias_baja" not in les: les["dias_baja"] = None
        if "estado" not in les: les["estado"] = "Activa"

    for s in st.session_state.get("sesiones", []):
        if s.get("informe_generado"):
            for d in s.get("datos_informe", []):
                for z in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor', 'MIN_GPS']:
                    if z not in d: d[z] = 0.0

def sincronizar_plantilla_sesiones():
    if "plantilla" in st.session_state and st.session_state.plantilla:
        dict_pos = {limpiar_nombre(p["JUGADOR"]): p["POS"] for p in st.session_state.plantilla}
        dict_nombres = {limpiar_nombre(p["JUGADOR"]): p["JUGADOR"] for p in st.session_state.plantilla}

        for s in st.session_state.get("sesiones", []):
            if s.get("datos_informe"):
                for d in s["datos_informe"]:
                    jug_limpio = limpiar_nombre(d.get("JUGADOR", ""))
                    if jug_limpio in dict_pos:
                        d["POS"] = dict_pos[jug_limpio]
                        d["JUGADOR"] = dict_nombres[jug_limpio]

def get_base64_of_bin_file(bin_file):
    if bin_file:
        try:
            # 1. Abrir la imagen subida
            img = Image.open(bin_file)
            
            # 2. Convertir a RGB (Evita errores con PNGs transparentes al guardar como JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            # 3. Redimensionar manteniendo la proporción (máximo 200x200)
            img.thumbnail((200, 200))
            
            # 4. Guardar temporalmente en memoria con compresión
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            
            # 5. Convertir a Base64 el archivo ya comprimido
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            # Fallback de seguridad por si falla la lectura de la imagen
            bin_file.seek(0)
            return base64.b64encode(bin_file.read()).decode()
    return None

meses_esp = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

def mostrar_tabla_moderna(styler_obj):
    if hasattr(styler_obj, 'data'):
        df_base = styler_obj.data
        format_dict = {}
        for col in df_base.columns:
            if pd.api.types.is_numeric_dtype(df_base[col]):
                col_lower = col.lower()
                if any(m in col_lower for m in ['wellness', 'tqr', 'rpe', 'ratio', 'dis (km)', 'dis ai', 'vmax', 'v_max', '%']):
                    format_dict[col] = "{:.1f}"
                elif any(m in col_lower for m in ['min', 'carga', 'sprint', 'acc', 'dcc', 'z1', 'z2', 'z3', 'z4', 'z5', 'z6', 'pj', 'conv']):
                    format_dict[col] = "{:.0f}"
                else:
                    format_dict[col] = "{:.2f}"
        styler_obj = styler_obj.hide(axis="index").set_table_attributes('class="modern-table"')
        html_tabla = styler_obj.to_html()
        st.markdown(html_tabla, unsafe_allow_html=True)
    else:
        df_temp = styler_obj.copy()
        for col in df_temp.columns:
            if 'fecha' in col.lower() or 'id_sesion' in col.lower():
                df_temp[col] = pd.to_datetime(df_temp[col], errors='coerce').dt.strftime('%d-%m-%Y')
            elif pd.api.types.is_numeric_dtype(df_temp[col]):
                col_lower = col.lower()
                if any(m in col_lower for m in ['wellness', 'tqr', 'rpe', 'ratio', 'dis (km)', 'dis ai', 'vmax', 'v_max']):
                    df_temp[col] = df_temp[col].round(1)
                elif any(m in col_lower for m in ['min', 'carga', 'sprint', 'acc', 'dcc', 'z1', 'z2', 'z3', 'z4', 'z5', 'z6']):
                    df_temp[col] = df_temp[col].round(0)
                else:
                    df_temp[col] = df_temp[col].round(2)
        html_tabla = df_temp.to_html(index=False, classes="modern-table", escape=False, border=0)
        st.markdown(html_tabla, unsafe_allow_html=True)
    
def set_login_background():
    css = """
    <style>
    /* --- FONDO ANIMADO DE DATOS (Puro CSS, sin imágenes) --- */
    .stApp {
        background-color: #0b1120 !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08), transparent 25%),
            radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.05), transparent 25%);
        animation: bgShift 15s ease-in-out infinite alternate;
    }
    
    /* Malla / Grid de Analytics overlay */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes bgShift {
        0% { background-position: 0% 0%; }
        100% { background-position: 100% 100%; }
    }

    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 2rem !important; max-width: 1200px !important; position: relative; z-index: 1; }
    
    /* --- TARJETA DE LOGIN OSCURA --- */
    div[data-testid="stTabs"] {
        background-color: #0B101A !important; 
        padding: 30px 40px 40px 40px !important;
        border-radius: 20px !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
        border: 1px solid #1e293b !important;
        backdrop-filter: blur(12px);
    }
    div[role="tabpanel"] { background-color: transparent !important; }
    
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        background-color: transparent !important; border: none !important; border-bottom: 1px solid #1e293b !important; border-radius: 0 !important; overflow: visible !important; gap: 20px !important; margin-bottom: 15px !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] { 
        color: #64748b !important; font-size: 0.85rem !important; font-weight: 700 !important; white-space: nowrap !important; min-width: max-content !important; background-color: transparent !important; padding: 0 5px 10px 5px !important; text-transform: uppercase; letter-spacing: 0.5px;
    }
    div[data-testid="stTabs"] [aria-selected="true"] { 
        color: #f8fafc !important; border-bottom: 2px solid #3b82f6 !important; background-color: transparent !important; box-shadow: none !important;
    }
    
    div[data-testid="stTabs"] label { color: #cbd5e1 !important; font-size: 0.85rem !important; font-weight: 600 !important; margin-bottom: 4px !important; }
    
    div[data-testid="stTextInput"] input {
        background-color: #0f172a !important; border: 1px solid #1e293b !important; color: #f8fafc !important; padding: 12px 14px !important; border-radius: 8px !important; font-size: 0.95rem !important;
    }
    div[data-testid="stTextInput"] input:focus { border: 1px solid #3b82f6 !important; box-shadow: none !important; }
    
    div[data-testid="stFormSubmitButton"] button {
        background-color: #3b82f6 !important; color: #ffffff !important; border: none !important; border-radius: 8px !important;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3) !important; width: 100% !important; margin-top: 5px; padding: 12px !important; font-size: 1rem !important; font-weight: 700 !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stFormSubmitButton"] button:hover { background-color: #2563eb !important; transform: translateY(-1px); box-shadow: 0 6px 15px rgba(59, 130, 246, 0.4) !important; }
    
    div[data-testid="stCheckbox"] label span { color: #94a3b8 !important; font-size: 0.85rem !important; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

import requests
from geopy.geocoders import Nominatim
import streamlit as st

@st.cache_data(show_spinner=False)
def obtener_coordenadas(ciudad):
    if not ciudad: return None, None
    try:
        geolocator = Nominatim(user_agent="loadlab_sports_app") 
        location = geolocator.geocode(ciudad, timeout=5)
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return None, None

@st.cache_data(show_spinner=False)
def obtener_clima(ciudad, fecha_str):
    lat, lon = obtener_coordenadas(ciudad)
    if not lat or not lon:
        return None
    
    try:
        # 1. Primero intentamos con el archivo histórico (Ideal para sesiones de semanas pasadas)
        url_archive = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={fecha_str}&end_date={fecha_str}"
        response = requests.get(url_archive).json()
        
        # 2. Si da error (porque la fecha es de hoy o de hace solo 2 días), usamos el pronóstico actual
        if "error" in response or "daily" not in response:
            url_forecast = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={fecha_str}&end_date={fecha_str}"
            response = requests.get(url_forecast).json()

        if "daily" in response and response["daily"].get("temperature_2m_max"):
            t_max = response["daily"]["temperature_2m_max"][0]
            lluvia = response["daily"]["precipitation_sum"][0]
            
            if t_max is not None:
                temp_real = float(t_max)
                estado = "🌧️ Lluvia" if lluvia and lluvia > 1.0 else "☀️ Despejado"
                return {"temp": temp_real, "estado": estado}
    except Exception as e:
        print(f"Error clima: {e}")
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_css_global():
    """Cachea la lectura del archivo CSS para evitar carga de I/O en cada recarga de página"""
    try:
        with open("style.css", "r") as f:
            return f"<style>{f.read()}</style>"
    except Exception:
        return ""

def aplicar_color_sidebar():
    """Inyecta el color dinámico, la tipografía, el CSS global, el escudo y los botones de sesión en orden estricto."""
    css_dinamico = """
    <style>
        /* 1. Ajustes del contenedor del menú lateral para tu navegación custom */
        [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid #1e293b !important;
        }
        
        /* 2. Ajustamos la altura restando los márgenes nativos para evitar el scroll */
        [data-testid="stSidebarUserContent"] {
            height: calc(100vh - 6rem) !important;
            padding-bottom: 0 !important;
        }
        
        /* 3. Convertimos el bloque interno invisible de Streamlit en un contenedor Flexbox */
        [data-testid="stSidebarUserContent"] > div {
            display: flex !important;
            flex-direction: column !important;
            height: 100% !important;
        }
        
        /* 4. Magia CSS: Identificamos el espaciador y le obligamos a empujar todo hacia abajo */
        div.element-container:has(.spacer-bottom) {
            margin-top: auto !important;
        }
        
        /* Animación del Punto Verde (Live Pulse) */
        @keyframes pulse-green {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        .live-dot {
            height: 8px; width: 8px; background-color: #10b981; border-radius: 50%;
            display: inline-block; animation: pulse-green 2s infinite; margin-right: 6px;
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
            color: #f8fafc !important; 
            font-weight: 800 !important;
        }
    </style>
    """
    import streamlit as st
    
    # 1. Inyectar CSS dinámico del sidebar
    st.markdown(css_dinamico, unsafe_allow_html=True)
    
    # 2. Inyectar CSS global desde la memoria caché (Sustituye al try/except)
    st.markdown(cargar_css_global(), unsafe_allow_html=True)

    if st.session_state.get("equipo_seleccionado", False):
        with st.sidebar:
            escudo = st.session_state.get("escudo_equipo")
            nombre = st.session_state.get("nombre_equipo", "")
            img_src = escudo if str(escudo).startswith("http") else f"data:image/jpeg;base64,{escudo}" if escudo else ""
            
            # 1. ESCUDO Y NOMBRE ARRIBA DEL TODO
            if img_src:
                st.markdown(f"""
                    <div style='text-align: center; margin-bottom: 15px;'>
                        <img src='{img_src}' style='width: 85px; height: 85px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'>
                        <h3 style='color: #f8fafc; margin-top: 10px; margin-bottom: 0; font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.5px;'>{nombre}</h3>
                        <hr style='border-color: #1e293b; margin-top: 15px; margin-bottom: 10px; border-width: 1px;'>
                    </div>
                """, unsafe_allow_html=True)
            
            # --- CSS PARA TIPOGRAFÍA DE ENLACES LATERALES ---
            st.markdown("""
            <style>
            [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p, 
            [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span {
                font-weight: 700 !important;
                font-size: 0.95rem !important;
                letter-spacing: 0.3px !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # 2. ENLACES DE PÁGINAS MANUALES (Control total de la posición central)
            st.markdown("<p style='color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 800; margin-bottom: 8px; letter-spacing: 0.5px;'>Navegación</p>", unsafe_allow_html=True)

            st.page_link("Inicio.py", label="Inicio", icon="🏠")
            st.page_link("pages/1_Entrenamiento.py", label="Entrenamiento", icon="📅")
            st.page_link("pages/2_Plantilla.py", label="Plantilla", icon="👥")
            st.page_link("pages/3_Lesiones.py", label="Lesiones", icon="🚑")
            st.page_link("pages/4_GPS.py", label="GPS", icon="📡")
            st.page_link("pages/5_Antropometria.py", label="Antropometría", icon="⚖️")
            st.page_link("pages/6_Valoraciones.py", label="Valoraciones", icon="📊")
            st.page_link("pages/7_Estadisticas.py", label="Estadísticas", icon="📈")
            st.page_link("pages/8_Predicción_de_lesiones.py", label="Predicción de lesiones", icon="🧠")
            
            # 3. ESPACIADOR FLEXIBLE (Empuja los siguientes elementos abajo del todo)
            st.markdown("<div class='spacer-bottom'></div>", unsafe_allow_html=True)
            
            # 4. LIVE SYNC Y BOTONES ABAJO DEL TODO
            st.markdown("<hr style='border-color: #1e293b; margin-top: 10px; margin-bottom: 10px; border-width: 1px;'>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style='display: flex; justify-content: center; margin-bottom: 10px;'>
                    <div style='background-color: rgba(15, 23, 42, 0.9); border: 1px solid #334155; padding: 4px 10px; border-radius: 10px; font-size: 0.6rem; color: #94a3b8; font-weight: 800; text-transform: uppercase; display: flex; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.3);'>
                        <span class='live-dot'></span> LIVE SYNC
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Cambiar Equipo", use_container_width=True, key="btn_cambiar_eq_sb"):
                st.session_state.equipo_seleccionado = False
                st.rerun()
            if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_cerrar_ses_sb"):
                st.session_state.clear()
                st.rerun()
                
def render_estado_vacio(icono, titulo, descripcion, accion_sugerida=None):
    """Renderiza una tarjeta moderna Dark Mode para pantallas sin datos (Onboarding)"""
    html_accion = f'<p style="color: #3b82f6; font-weight: 800; font-size: 0.85rem; margin-top: 20px; text-transform: uppercase; letter-spacing: 0.05em;">↳ {accion_sugerida}</p>' if accion_sugerida else ''
    
    html = f"""
    <div style="background-color: #1e293b; border: 2px dashed #334155; border-radius: 12px; padding: 50px 20px; text-align: center; margin: 20px 0; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);">
        <div style="font-size: 3.5rem; margin-bottom: 15px; opacity: 0.9;">{icono}</div>
        <h3 style="color: #f8fafc; font-weight: 800; font-size: 1.3rem; margin-bottom: 10px; text-transform: uppercase;">{titulo}</h3>
        <p style="color: #94a3b8; font-size: 0.95rem; max-width: 500px; margin: 0 auto; line-height: 1.5;">{descripcion}</p>
        {html_accion}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def validar_columnas_excel(df, nombre_archivo, columnas_esperadas):
    """
    Analiza un DataFrame recién subido. Si le faltan columnas críticas,
    devuelve un mensaje de error descriptivo para el usuario en lugar de un colapso.
    """
    if df.empty:
        return False, f"El archivo <b>{nombre_archivo}</b> está vacío o corrupto."
        
    columnas_reales = [str(c).strip().lower() for c in df.columns]
    faltantes = []
    
    for col_esperada in columnas_esperadas:
        if str(col_esperada).strip().lower() not in columnas_reales:
            faltantes.append(f"'{col_esperada}'")
            
    if faltantes:
        msg = f"<b>🚨 Error de formato en {nombre_archivo}:</b> No se han encontrado las columnas {', '.join(faltantes)}. <br><br><span style='font-size: 0.85rem; color: #475569;'><i>Solución: Revisa que el encabezado del Excel coincida exactamente con lo que espera el sistema o ajusta los nombres en el 'Mapeador Dinámico' de la configuración. Cuidado con los espacios en blanco invisibles.</i></span>"
        return False, msg
        
    return True, "OK"
def render_kpi_elite(titulo, valor, subtitulo="", icono="", color_borde="#3b82f6", tendencia=None):
    """
    Tarjeta KPI compacta unificada: Título a la izquierda, Valor centrado.
    """
    tendencia_html = ""
    if tendencia is not None:
        val_t = tendencia.get('valor', 0)
        inverso = tendencia.get('inverso', False)
        texto_personalizado = tendencia.get('texto', 'vs Sem. Ant.')
        
        if val_t > 0.5:
            color = "#ef4444" if inverso else "#10b981"
            flecha = "▲"
        elif val_t < -0.5:
            color = "#10b981" if inverso else "#ef4444"
            flecha = "▼"
        else:
            color = "#94a3b8"
            flecha = "▬"
            if "semana" in texto_personalizado:
                texto_personalizado = "igual esta semana"
            
        tendencia_html = f"<div style='color: {color}; font-size: 0.85rem; font-weight: 800; margin-top: 8px; line-height: 1.2; text-align: center;'>{flecha} {abs(val_t):.1f}% {texto_personalizado}</div>"

    html = f"""
    <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid {color_borde}; padding: 10px 8px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.15); display: flex; flex-direction: column; justify-content: center; height: 100%;">
        <p style="color: #f8fafc; font-size: 0.85rem; font-weight: 800; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.1; word-wrap: break-word; text-align: left;">{titulo} {icono}</p>
        <h2 style="color: #f8fafc; font-size: 1.4rem; font-weight: 800; margin: 0; line-height: 1; text-align: center;">{valor}</h2>
        {tendencia_html}
        {f"<p style='color: {color_borde}; font-size: 0.65rem; font-weight: 600; margin: 6px 0 0 0; text-align: center;'>{subtitulo}</p>" if subtitulo else ""}
    </div>
    """
    import streamlit as st
    st.markdown(html, unsafe_allow_html=True)
def calcular_zscore_wellness(df_master, fecha_objetivo):
    """
    Calcula la media y desviación estándar histórica intra-sujeto para el Wellness.
    Excluye la fecha objetivo para evitar que el valor actual contamine su propio baseline.
    """
    if df_master.empty or 'WELLNESS' not in df_master.columns:
        return {}
        
    df_hist = df_master[df_master['FECHA'] < fecha_objetivo].copy()
    if df_hist.empty:
        return {}
        
    df_hist['WELLNESS'] = df_hist['WELLNESS'].replace(0, np.nan)
    stats = df_hist.groupby('JUGADOR')['WELLNESS'].agg(['mean', 'std']).fillna(0)
    
    res = {}
    for jug, row in stats.iterrows():
        media = row['mean']
        # Se establece una desviación mínima de 1.0 para evitar división por cero en varianzas nulas
        std = row['std'] if row['std'] > 0 else 1.0 
        res[jug] = {'media': media, 'std': std}
        
    return res
def calcular_zscores_eficiencia(df_master, fecha_objetivo):
    """
    Calcula la media y desviación estándar de la Eficiencia Cardiovascular y Neuromuscular intra-sujeto.
    Excluye la fecha objetivo para evitar contaminación de la línea base.
    """
    if df_master.empty or 'DIS' not in df_master.columns: 
        return {}
        
    df_hist = df_master[df_master['FECHA'] < fecha_objetivo].copy()
    if df_hist.empty: 
        return {}
        
    df_hist['m_min'] = np.where(df_hist['MIN'] > 0, (df_hist['DIS'] * 1000) / df_hist['MIN'], 0)
    df_hist['mec_total'] = df_hist['ACC'] + df_hist['DCC'] + df_hist['Nº SPR']
    
    # Eficiencia = RPE dividido por densidad externa
    df_hist['EFI_CARDIO'] = np.where(df_hist['m_min'] > 0, df_hist['RPE'] / df_hist['m_min'], np.nan)
    df_hist['EFI_NEURO'] = np.where(df_hist['mec_total'] > 0, df_hist['RPE'] / df_hist['mec_total'], np.nan)
    
    stats_c = df_hist.groupby('JUGADOR')['EFI_CARDIO'].agg(['mean', 'std']).fillna({'mean': 0, 'std': 0.05})
    stats_n = df_hist.groupby('JUGADOR')['EFI_NEURO'].agg(['mean', 'std']).fillna({'mean': 0, 'std': 0.05})
    
    res = {}
    for jug in df_hist['JUGADOR'].unique():
        res[jug] = {
            'cardio_mean': stats_c.loc[jug, 'mean'] if jug in stats_c.index else 0,
            'cardio_std': stats_c.loc[jug, 'std'] if jug in stats_c.index and stats_c.loc[jug, 'std'] > 0 else 0.05,
            'neuro_mean': stats_n.loc[jug, 'mean'] if jug in stats_n.index else 0,
            'neuro_std': stats_n.loc[jug, 'std'] if jug in stats_n.index and stats_n.loc[jug, 'std'] > 0 else 0.05
        }
    return res
def aplicar_imputacion_gps_global(registros, sesion_actual, plantilla_global):
    """
    Motor de imputación de élite. 
    Traspasa TODAS las métricas GPS (incluidos MIN_GPS) aislando por Estado y Posición.
    Añade la bandera GPS_VIRTUAL = True para proteger los perfiles de rendimiento individual.
    """
    import pandas as pd
    es_partido_flag = "Partido" in sesion_actual.get("tipo", "")
    disp_dict = {limpiar_nombre(k): v for k, v in sesion_actual.get("disponibilidad", {}).items()}
    default_estado = "Titular" if es_partido_flag else "Disponible"
    stats_partido = {limpiar_nombre(k): v for k, v in sesion_actual.get("estadisticas_partido", {}).items()}
    
    datos_validos = []
    for reg in registros:
        jug = reg["JUGADOR"]
        pos = reg.get("POS", "DEF")
        estado = disp_dict.get(limpiar_nombre(jug), default_estado)
        
        # Solo usamos datos como referencia si tienen GPS real (DIS > 0 y NO virtual) y no son porteros
        if safe_float(reg.get("DIS", 0)) > 0 and not reg.get("GPS_VIRTUAL", False) and pos != "POR":
            p_match = next((p for p in plantilla_global if p["JUGADOR"] == jug), {})
            pos_esp = p_match.get("pos_1", pos)
            min_gps = safe_float(reg.get("MIN_GPS", reg.get("MIN", 0)))
            if min_gps > 0:
                datos_validos.append({
                    "ESTADO": estado, "POS_ESP": pos_esp, "POS_GEN": pos, "MIN_GPS": min_gps,
                    "DIS": safe_float(reg.get("DIS")), "DIS AI": safe_float(reg.get("HID >21", reg.get("DIS AI", 0))),
                    "Nº SPR": safe_float(reg.get("SPR >24", reg.get("Nº SPR", 0))),
                    "ACC": safe_float(reg.get("ACC >3", reg.get("ACC", 0))), "DCC": safe_float(reg.get("DCC >3", reg.get("DCC", 0))),
                    "VMAX": safe_float(reg.get("V_Max", reg.get("VMAX", 0))),
                    "Z1": safe_float(reg.get("Z1", 0)), "Z2": safe_float(reg.get("Z2", 0)), "Z3": safe_float(reg.get("Z3", 0)),
                    "Z4": safe_float(reg.get("Z4", 0)), "Z5": safe_float(reg.get("Z5", 0)), "Z6": safe_float(reg.get("Z6", 0))
                })
                
    if datos_validos:
        df_val = pd.DataFrame(datos_validos)
        df_val["DIS_pm"] = df_val["DIS"] / df_val["MIN_GPS"]
        df_val["DIS_AI_pm"] = df_val["DIS AI"] / df_val["MIN_GPS"]
        df_val["SPR_pm"] = df_val["Nº SPR"] / df_val["MIN_GPS"]
        df_val["ACC_pm"] = df_val["ACC"] / df_val["MIN_GPS"]
        df_val["DCC_pm"] = df_val["DCC"] / df_val["MIN_GPS"]
        
        medias_estado_esp = df_val.groupby(["ESTADO", "POS_ESP"]).mean(numeric_only=True).to_dict('index')
        medias_estado_gen = df_val.groupby(["ESTADO", "POS_GEN"]).mean(numeric_only=True).to_dict('index')
        medias_estado = df_val.groupby("ESTADO").mean(numeric_only=True).to_dict('index')
        medias_eq = df_val.mean(numeric_only=True).to_dict()
        
        for reg in registros:
            jug = reg["JUGADOR"]
            pos = reg.get("POS", "DEF")
            estado = disp_dict.get(limpiar_nombre(jug), default_estado)
            elegible = estado in ["Disponible", "Recuperación Post-Partido", "Titular", "Suplente"]
            
            es_virtual_previo = reg.get("GPS_VIRTUAL", False)
            sin_gps_real = safe_float(reg.get("DIS", 0)) == 0 or es_virtual_previo
            min_jug = safe_float(reg.get("MIN", 0))
            
            if elegible and pos != "POR" and sin_gps_real:
                p_match = next((p for p in plantilla_global if p["JUGADOR"] == jug), {})
                pos_esp = p_match.get("pos_1", pos)
                
                # Respeto estricto del ESTADO de disponibilidad
                ratios = medias_estado_esp.get((estado, pos_esp), 
                         medias_estado_gen.get((estado, pos), 
                         medias_estado.get(estado, medias_eq)))
                
                def seguro(v): return 0.0 if pd.isna(v) else float(v)

                if es_partido_flag:
                    # Los minutos de juego real (GPS) salen de las stats del partido
                    min_partido = safe_float(stats_partido.get(limpiar_nombre(jug), {}).get("Minutos", min_jug))
                    if min_partido == 0: continue
                    
                    # IMPUTACIÓN ESTRICTA DE GPS (Respetando MIN y CARGA manuales)
                    reg["MIN_GPS"] = min_partido
                    reg["DIS"] = seguro(ratios.get("DIS_pm", 0) * min_partido)
                    reg["DIS AI"] = seguro(ratios.get("DIS_AI_pm", 0) * min_partido)
                    reg["HID >21"] = reg["DIS AI"]
                    reg["Nº SPR"] = seguro(ratios.get("SPR_pm", 0) * min_partido)
                    reg["SPR >24"] = reg["Nº SPR"]
                    reg["ACC"] = seguro(ratios.get("ACC_pm", 0) * min_partido)
                    reg["ACC >3"] = reg["ACC"]
                    reg["DCC"] = seguro(ratios.get("DCC_pm", 0) * min_partido)
                    reg["DCC >3"] = reg["DCC"]
                else:
                    # En entrenamientos, usamos la media de MIN_GPS del grupo
                    min_grupo = seguro(ratios.get("MIN_GPS", 0))
                    if min_grupo == 0: continue
                    
                    # IMPUTACIÓN ESTRICTA DE GPS (Respetando MIN y CARGA manuales)
                    reg["MIN_GPS"] = min_grupo
                    reg["DIS"] = seguro(ratios.get("DIS", 0))
                    reg["DIS AI"] = seguro(ratios.get("DIS AI", 0))
                    reg["HID >21"] = reg["DIS AI"]
                    reg["Nº SPR"] = seguro(ratios.get("Nº SPR", 0))
                    reg["SPR >24"] = reg["Nº SPR"]
                    reg["ACC"] = seguro(ratios.get("ACC", 0))
                    reg["ACC >3"] = reg["ACC"]
                    reg["DCC"] = seguro(ratios.get("DCC", 0))
                    reg["DCC >3"] = reg["DCC"]
                    reg["Z1"] = seguro(ratios.get("Z1", 0))
                    reg["Z2"] = seguro(ratios.get("Z2", 0))
                    reg["Z3"] = seguro(ratios.get("Z3", 0))
                    reg["Z4"] = seguro(ratios.get("Z4", 0))
                    reg["Z5"] = seguro(ratios.get("Z5", 0))
                    reg["Z6"] = seguro(ratios.get("Z6", 0))

                reg["VMAX"] = seguro(ratios.get("VMAX", 0))
                reg["V_Max"] = reg["VMAX"]
                reg["GPS_VIRTUAL"] = True
                
    return registros
