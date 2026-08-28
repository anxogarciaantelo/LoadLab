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

@st.cache_data
def calcular_ewma_historico(_sesiones, fecha_objetivo):
    registros = []
    # Añadimos el guion bajo aquí:
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
    
    # Enmascarar ceros previos a la primera sesión del jugador
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
        
        # Limpieza de posibles NaNs si el jugador no tiene ningún dato
        if pd.isna(a): a = 0.0
        if pd.isna(c): c = 0.0
        
        r = a / c if c > 0 else 1.0
        res[jug] = {"EWMA AGUDA": round(a, 2), "EWMA CRÓNICA": round(c, 2), "RATIO A/C": round(r, 2)}
        
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

@st.cache_data
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
    if hasattr(styler_obj, 'data'):
        df_temp = styler_obj.data.copy()
        
        # 1. Limpieza y formato automático de fechas en toda la app
        for col in df_temp.columns:
            if 'fecha' in col.lower() or 'id_sesion' in col.lower():
                df_temp[col] = pd.to_datetime(df_temp[col], errors='coerce').dt.strftime('%d-%m-%Y')
            
            # 2. Redondeo automático inteligente por nombre de columna
            elif pd.api.types.is_numeric_dtype(df_temp[col]):
                col_lower = col.lower()
                if any(m in col_lower for m in ['wellness', 'tqr', 'rpe', 'ratio', 'dis (km)', 'dis ai', 'vmax', 'v_max']):
                    df_temp[col] = df_temp[col].round(1)
                elif any(m in col_lower for m in ['min', 'carga', 'sprint', 'acc', 'dcc', 'z1', 'z2', 'z3', 'z4', 'z5', 'z6']):
                    df_temp[col] = df_temp[col].round(0)
                else:
                    df_temp[col] = df_temp[col].round(2)
                    
        html_tabla = df_temp.to_html(index=False, classes="modern-table", escape=False)
    else:
        html_tabla = styler_obj.to_html()

    css_personalizado = "<style>.modern-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); background-color: white; margin-bottom: 20px; } .modern-table thead tr { background-color: #000000; color: #ffffff; } .modern-table th { padding: 12px 15px; font-weight: bold; text-align: center !important; border-bottom: 2px solid #333333; } .modern-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #eeeeee; } .modern-table tbody tr:hover td { filter: brightness(0.95); }</style>"
    st.markdown(css_personalizado + html_tabla, unsafe_allow_html=True)
def set_login_background(image_path):
    try:
        import base64
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        css = f"""
        <style>
        /* 1. Fondo general de la app con la imagen */
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* 2. Eliminar la barra superior */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            box-shadow: none !important;
        }}
        
        .block-container {{
            padding-top: 1rem !important;
        }}
        
        /* 3. CONVERTIR TODO EL BLOQUE DE TABS EN LA TARJETA BLANCA */
        div[data-testid="stTabs"] {{
            background-color: #ffffff !important;
            padding: 30px !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4) !important;
            border: 1px solid #e2e8f0 !important;
        }}
        
        /* Asegurar que el fondo del contenido herede el blanco */
        div[role="tabpanel"] {{
            background-color: transparent !important; 
        }}
        
        /* 4. INTEGRACIÓN DE LAS PESTAÑAS (TABS HEADER) */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background-color: #f8fafc !important;
            border-radius: 10px !important;
            padding: 5px !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 15px !important;
        }}
        div[data-testid="stTabs"] [data-baseweb="tab"] {{
            color: #64748b !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stTabs"] [aria-selected="true"] {{
            background-color: #ffffff !important;
            color: #0f172a !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            border-radius: 8px !important;
        }}
        
        /* 5. TEXTOS Y FORMULARIOS DENTRO DE LA TARJETA */
        div[data-testid="stTabs"] label {{
            color: #0f172a !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
        }}
        
        /* Forzar que textos extra (como el checkbox) se vean en oscuro */
        div[data-testid="stTabs"] div[data-testid="stMarkdownContainer"] p {{
            color: #475569 !important; 
        }}
        
        div[data-testid="stTextInput"] input {{
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            color: #0f172a !important;
            padding: 12px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }}
        
        div[data-testid="stTextInput"] input:focus {{
            border: 1px solid #00b4d8 !important;
            background-color: #ffffff !important;
            box-shadow: 0 0 8px rgba(0, 180, 216, 0.3) !important;
        }}
        
        /* 6. BOTÓN DE ACCESO */
        div[data-testid="stFormSubmitButton"] button {{
            background-color: #0f172a !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            padding: 10px !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1) !important;
            margin-top: 15px;
            width: 100% !important;
            transition: all 0.3s ease;
        }}
        
        div[data-testid="stFormSubmitButton"] button:hover {{
            background-color: #1e293b !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.15) !important;
        }}
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

def aplicar_color_sidebar():
    """Inyecta el color dinámico, la tipografía de la barra lateral y el CSS global en todas las páginas"""
    color = st.session_state.get("color_sidebar", "#0a0a0a") 
    
    # 1. Color dinámico y forzado de tipografía (negrita y blanco) para la barra lateral
    css_dinamico = f"""
    <style>
        [data-testid="stSidebar"] {{
            background-color: {color} !important;
            border-right: 1px solid #262626 !important;
        }}
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {{
            color: #000000 !important;
            font-weight: 800 !important;
        }}
    </style>
    """
    st.markdown(css_dinamico, unsafe_allow_html=True)
    
    # 2. Carga automática del archivo Style.css para asegurar que el diseño 
    #    sea el mismo en todas las páginas de la aplicación.
    try:
        # Asegúrate de que el nombre del archivo coincida exactamente (mayúsculas/minúsculas)
        with open("Style.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        pass
