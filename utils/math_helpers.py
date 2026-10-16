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
    registros = []
    for s in _sesiones: 
        if s.get("informe_generado") and s["fecha"] <= fecha_objetivo:
            for d in s["datos_informe"]:
                registros.append({"fecha": s["fecha"], "JUGADOR": d["JUGADOR"], "CARGA": float(d.get("CARGA", 0))})
    if not registros: return {}
    
    df_hist = pd.DataFrame(registros)
    df_hist['fecha'] = pd.to_datetime(df_hist['fecha'])
    df_pivot = df_hist.pivot_table(index='fecha', columns='JUGADOR', values='CARGA', aggfunc='sum').fillna(0)
    
    fecha_fin = pd.to_datetime(fecha_objetivo)
    fecha_ini = df_pivot.index.min()
    rango_fechas = pd.date_range(start=fecha_ini, end=fecha_fin, freq='D')
    df_pivot = df_pivot.reindex(rango_fechas, fill_value=0)
    
    for col in df_pivot.columns:
        s_cargas = df_pivot[col]
        primer_dia_valido = s_cargas[s_cargas > 0].first_valid_index()
        if primer_dia_valido:
            df_pivot.loc[:primer_dia_valido - pd.Timedelta(days=1), col] = np.nan

    aguda = df_pivot.ewm(span=7, adjust=False).mean()
    cronica = df_pivot.ewm(span=28, adjust=False).mean()
    
    aguda_hoy = aguda.loc[fecha_fin]
    cronica_hoy = cronica.loc[fecha_fin]
    
    res = {}
    for jug in df_pivot.columns:
        a = aguda_hoy.get(jug, 0.0)
        c = cronica_hoy.get(jug, 0.0)
        
        if pd.isna(a): a = 0.0
        if pd.isna(c): c = 0.0
        
        # Carga Semanal Equivalente
        a_semanal = a * 7
        c_semanal = c * 7
        
        r = a_semanal / c_semanal if c_semanal > 0 else 1.0
        res[jug] = {"EWMA AGUDA": round(a_semanal, 2), "EWMA CRÓNICA": round(c_semanal, 2), "RATIO A/C": round(r, 2)}
        
    return res

def color_ratio_ac(valor):
    if valor >= 1.4: return '#ff4b4b' 
    if valor >= 1.05: return '#28a745' 
    if valor >= 0.9: return '#8fd19e' 
    if valor >= 0.7: return '#ffc107' 
    return '#17a2b8' 

def categorizar_duracion(dias):
    if pd.isna(dias) or dias is None or dias == "": return "Activa"
    dias = int(dias)
    if dias <= 3: return "Mínima (1-3d)"
    if dias <= 7: return "Leve (4-7d)"
    if dias <= 28: return "Moderada (8-28d)"
    return "Grave (>28d)"

def calcular_monotonia_7d(_sesiones, jugador, fecha_objetivo):
    fecha_fin = datetime.strptime(fecha_objetivo, "%Y-%m-%d")
    fecha_ini = fecha_fin - timedelta(days=6)
    
    dic_cargas = {(fecha_ini + timedelta(days=i)).strftime("%Y-%m-%d"): 0.0 for i in range(7)}
    
    for s in _sesiones: 
        if s.get("informe_generado") and s["fecha"] in dic_cargas:
            for d in s["datos_informe"]:
                if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jugador):
                    dic_cargas[s["fecha"]] += safe_float(d.get("CARGA", 0))
                    break
                    
    cargas = list(dic_cargas.values())
    media = np.mean(cargas)
    desviacion = np.std(cargas)
    
    if desviacion > 0:
        return media / desviacion
    elif media > 0:
        return 10.0
    return 0.0
import tempfile

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
    # 1. Extraemos SIEMPRE el DataFrame puro para eliminar los estilos inline blancos de Pandas
    if hasattr(styler_obj, 'data'):
        df_temp = styler_obj.data.copy()
    else:
        df_temp = styler_obj.copy()
        
    # 2. Formato automático
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
                
    # 3. Generamos HTML LIMPIO sin <style> inline
    html_tabla = df_temp.to_html(index=False, classes="modern-table", escape=False, border=0)

    # 4. Inyectamos la tabla (El CSS visual ahora vive 100% en style.css)
    st.markdown(html_tabla, unsafe_allow_html=True)
    
def set_login_background(image_path):
    try:
        import base64
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        css = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(11, 17, 32, 0.8), rgba(11, 17, 32, 0.95)), url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        header[data-testid="stHeader"] {{ background-color: transparent !important; box-shadow: none !important; }}
        .block-container {{ padding-top: 1rem !important; }}
        
        /* Tarjeta de Login Oscura */
        div[data-testid="stTabs"] {{
            background-color: rgba(30, 41, 59, 0.8) !important;
            padding: 35px 30px !important;
            border-radius: 16px !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
            border: 1px solid #334155 !important;
            border-top: 5px solid #3b82f6 !important;
            backdrop-filter: blur(12px);
        }}
        div[role="tabpanel"] {{ background-color: transparent !important; }}
        
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background-color: transparent !important; border: none !important; border-bottom: 2px solid #334155 !important; border-radius: 0 !important; overflow: visible !important; gap: 15px !important;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab"] {{ 
            color: #94a3b8 !important; font-size: 1.25rem !important; white-space: nowrap !important; min-width: max-content !important; background-color: transparent !important; padding: 0 15px !important;
        }}
        div[data-testid="stTabs"] [aria-selected="true"] {{ 
            color: #3b82f6 !important; border-bottom: 3px solid #3b82f6 !important; background-color: transparent !important; box-shadow: none !important;
        }}
        
        div[data-testid="stTabs"] label {{ color: #e2e8f0 !important; font-size: 1.1rem !important; font-weight: 600 !important; margin-bottom: 5px !important; }}
        
        div[data-testid="stTextInput"] input {{
            background-color: #0f172a !important; border: 1px solid #334155 !important; color: #f8fafc !important;
        }}
        div[data-testid="stTextInput"] input:focus {{ border: 1px solid #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important; }}
        
        div[data-testid="stFormSubmitButton"] button {{
            background-color: #3b82f6 !important; color: #ffffff !important; border: none !important; border-radius: 8px !important;
            box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4) !important; width: 100% !important; margin-top: 15px;
        }}
        div[data-testid="stFormSubmitButton"] button:hover {{ background-color: #2563eb !important; transform: translateY(-2px); }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        pass

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
    css_dinamico = """
    <style>
        [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid #1e293b !important;
        }
        /* Convertir el sidebar en Flexbox para empujar elementos al fondo */
        [data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        /* Dejar espacio arriba para que el menú no tape el escudo */
        [data-testid="stSidebarNav"] {
            padding-top: 170px !important;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
            color: #f8fafc !important; 
            font-weight: 800 !important;
        }
    </style>
    """
    st.markdown(css_dinamico, unsafe_allow_html=True)
    
    try:
        with open("style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

    if st.session_state.get("equipo_seleccionado", False):
        with st.sidebar:
            escudo = st.session_state.get("escudo_equipo")
            nombre = st.session_state.get("nombre_equipo", "")
            img_src = escudo if str(escudo).startswith("http") else f"data:image/jpeg;base64,{escudo}" if escudo else ""
            
            # 1. ESCUDO FIJO ARRIBA DE TODO
            if img_src:
                st.markdown(f"""
                    <div style='position: absolute; top: 30px; left: 0; width: 100%; text-align: center; z-index: 999999;'>
                        <img src='{img_src}' style='width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #3b82f6; box-shadow: 0 4px 10px rgba(0,0,0,0.3);'>
                        <h3 style='color: #f8fafc; margin-top: 10px; margin-bottom: 0; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.5px;'>{nombre}</h3>
                        <hr style='border-color: #1e293b; margin-top: 15px; margin-bottom: 0; border-width: 1px;'>
                    </div>
                """, unsafe_allow_html=True)
            
            # 2. SEPARADOR FLEXIBLE (Empuja los botones hacia abajo)
            st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
            
            # 3. BOTONES PEGADOS AL FONDO
            if st.button("🔄 Cambiar Equipo", use_container_width=True, key="btn_cambiar_eq_sb"):
                st.session_state.equipo_seleccionado = False
                st.rerun()
            if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_cerrar_ses_sb"):
                st.session_state.clear()
                st.rerun()

def render_estado_vacio(icono, titulo, descripcion, accion_sugerida=None):
    """Renderiza una tarjeta moderna para pantallas sin datos (Onboarding)"""
    html_accion = f'<p style="color: #dc2626; font-weight: 800; font-size: 0.85rem; margin-top: 20px; text-transform: uppercase; letter-spacing: 0.05em;">↳ {accion_sugerida}</p>' if accion_sugerida else ''
    
    html = f"""
    <div style="background-color: #ffffff; border: 2px dashed #d4d4d8; border-radius: 12px; padding: 50px 20px; text-align: center; margin: 20px 0; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);">
        <div style="font-size: 3.5rem; margin-bottom: 15px; opacity: 0.9;">{icono}</div>
        <h3 style="color: #1c1c1e; font-weight: 800; font-size: 1.3rem; margin-bottom: 10px; text-transform: uppercase;">{titulo}</h3>
        <p style="color: #475569; font-size: 0.95rem; max-width: 500px; margin: 0 auto; line-height: 1.5;">{descripcion}</p>
        {html_accion}
    </div>
    """
    import streamlit as st
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
def render_kpi_elite(titulo, valor, subtitulo="", icono="", color_borde="#3b82f6"):
    """
    Genera una tarjeta KPI con diseño profesional unificado tipo 'Élite'.
    Sustituirá a los st.metric estándar para dar cohesión visual a la app.
    """
    html = f"""
    <div style="background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-top: 3px solid {color_borde}; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); transition: transform 0.2s ease;">
        <p style="color: #94a3b8; font-size: 0.85rem; font-weight: 700; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">{titulo} {icono}</p>
        <h2 style="color: #f8fafc; font-size: 2.2rem; font-weight: 800; margin: 5px 0;">{valor}</h2>
        <p style="color: {color_borde}; font-size: 0.85rem; font-weight: 600; margin: 0;">{subtitulo}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
