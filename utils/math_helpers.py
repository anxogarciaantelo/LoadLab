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
def calcular_ewma_historico(sesiones, fecha_objetivo):
    registros = []
    for s in sesiones:
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
def calcular_monotonia_7d(sesiones, jugador, fecha_objetivo):
    fecha_fin = datetime.strptime(fecha_objetivo, "%Y-%m-%d")
    fecha_ini = fecha_fin - timedelta(days=6)
    
    dic_cargas = {(fecha_ini + timedelta(days=i)).strftime("%Y-%m-%d"): 0.0 for i in range(7)}
    
    for s in sesiones:
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
        /* 1. Fondo general de la app */
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        /* 2. Eliminar la barra blanca superior que corta el logo */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            box-shadow: none !important;
        }}
        
        /* Ajustar el espaciado superior general */
        .block-container {{
            padding-top: 1rem !important;
        }}
        
        /* 3. Crear el recuadro color carbón transparente SOLAMENTE en la columna central */
        div[data-testid="column"]:nth-child(2) > div[data-testid="stVerticalBlock"] {{
            background-color: rgba(20, 20, 20, 0.75) !important; /* Color carbón con 75% de opacidad */
            padding: 40px 30px !important;
            border-radius: 16px !important;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.08); /* Borde sutil blanquecino */
            backdrop-filter: blur(4px); /* Efecto cristal oscuro */
        }}
        
        /* Modificar el texto de los labels (Correo y Contraseña) a blanco y negrita */
        div[data-testid="stVerticalBlock"] label {{
            color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
            letter-spacing: 0.5px;
        }}
        
        /* Estilo moderno para los cajones de texto */
        div[data-testid="stTextInput"] input {{
            background-color: rgba(255, 255, 255, 0.9) !important;
            border: 2px solid transparent !important;
            border-radius: 8px !important;
            color: #000000 !important;
            padding: 12px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }}
        
        /* Efecto al hacer clic en los cajones (borde rojo) */
        div[data-testid="stTextInput"] input:focus {{
            border: 2px solid #e60000 !important;
            background-color: #ffffff !important;
            box-shadow: 0 0 10px rgba(230, 0, 0, 0.4) !important;
        }}
        
        /* Estilo moderno y agresivo para el botón Entrar */
        div[data-testid="stButton"] button {{
            background: linear-gradient(90deg, #8a0000, #e60000) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            padding: 10px !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
            transition: all 0.3s ease;
            margin-top: 15px;
        }}
        
        /* Efecto al pasar el ratón por el botón */
        div[data-testid="stButton"] button:hover {{
            background: linear-gradient(90deg, #e60000, #8a0000) !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(230, 0, 0, 0.6) !important;
            color: #ffffff !important;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        pass
