import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import json
import os
import re
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
import base64
from PIL import Image
import io
from fpdf import FPDF
import tempfile

# --- NUESTRAS LIBRERÍAS LOCALES ---
from utils.math_helpers import *
from utils.pdf_generator import *
from database.db_manager import *

# Configuración inicial de la página
st.set_page_config(page_title="LoadLab - Football Performance AMS", page_icon="⚽", layout="wide")
st.markdown(f"""
    <style>
        /* Importar fuente moderna */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}

        /* Fondo general de la app totalmente blanco */
        .stApp {{
            background-color: #ffffff;
        }}

        /* Barra lateral (Sidebar) con color dinámico y texto negro en negrita */
        [data-testid="stSidebar"] {{
            background-color: {st.session_state.get("color_sidebar", "#f1f5f9")};
            color: #000000;
        }}
        
        /* Forzar negrita y color negro en absolutamente todo el texto del sidebar */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] md {{
            color: #000000 !important;
            font-weight: 800 !important;
        }}

        [data-testid="stSidebar"] hr {{
            border-color: rgba(0, 0, 0, 0.2);
        }}

        /* Tarjetas de contenedores con diseño flotante y sombra sutil */
        div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {{
            background: #ffffff;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
        }}

        /* Tarjetas de métricas profesionales tipo Widget */
        div[data-testid="stMetric"] {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }}
        div[data-testid="stMetric"] label {{
            font-size: 0.75rem !important;
            color: #64748b !important;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            font-size: 1.6rem !important;
            color: #0f172a !important;
            font-weight: 700;
        }}

        /* Botones de acción comerciales */
        .stButton > button {{
            background: #ffffff;
            color: #0f172a;
            border-radius: 8px;
            font-weight: 600;
            border: 1px solid #cbd5e1;
            box-shadow: 0 1px 2px rgba(0,0,0,0.02);
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background: #0f172a;
            color: #ffffff;
            border-color: #0f172a;
        }}

        /* Estilo para pestañas (Tabs) */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: #f1f5f9;
            padding: 4px;
            border-radius: 10px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px;
            color: #475569;
            font-weight: 600;
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #ffffff !important;
            color: #0f172a !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
    </style>
""", unsafe_allow_html=True)


# Configuración global para forzar negrita y color negro en todos los gráficos de Plotly
import plotly.io as pio
pio.templates["loadlab_bold"] = {
    "layout": {
        "font": {"weight": "bold", "color": "black", "family": "sans-serif"},
        "title": {"font": {"weight": "bold", "color": "black"}},
        "xaxis": {
            "color": "black",
            "title_font": {"weight": "bold", "color": "black"}, 
            "tickfont": {"weight": "bold", "color": "black"}
        },
        "yaxis": {
            "color": "black",
            "title_font": {"weight": "bold", "color": "black"}, 
            "tickfont": {"weight": "bold", "color": "black"}
        },
        "legend": {
            "font": {"weight": "bold", "color": "black"},
            "title": {"font": {"weight": "bold", "color": "black"}}
        }
    }
}
pio.templates.default = "loadlab_bold"


# --- FUNCIONES AUXILIARES ---

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

# --- INICIALIZACIÓN DE ESTADOS CLAVE ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_id" not in st.session_state:
    st.session_state.usuario_id = None
if "equipo_seleccionado" not in st.session_state:
    st.session_state.equipo_seleccionado = False
if "lesiones" not in st.session_state: 
    st.session_state.lesiones = []
if "antropometria" not in st.session_state: 
    st.session_state.antropometria = []
if "plantilla" not in st.session_state: 
    st.session_state.plantilla = []
if "sesiones" not in st.session_state: 
    st.session_state.sesiones = []
if "color_sidebar" not in st.session_state:
    st.session_state.color_sidebar = "#f1f5f9"
    
# ==========================================
# 1. PANTALLA DE LOGIN
# ==========================================
if not st.session_state.autenticado:
    set_login_background("fondo_login.jpg")
    
    # Reducimos los saltos de línea para que quede más centrado con la imagen
    st.markdown("<br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    
    col_izq, col_centro, col_der = st.columns([1.5, 1, 1.5]) # <--- 1. Proporciones ajustadas para estrechar el centro
    
    with col_centro:
        st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 10px;'>Iniciar Sesión</h2>", unsafe_allow_html=True)
        
        # <--- 2. Envolvemos en un formulario para habilitar la tecla "Enter"
        with st.form(key="login_form", clear_on_submit=False):
            email = st.text_input("Correo electrónico")
            password = st.text_input("Contraseña", type="password")
            
            # El botón ahora es un form_submit_button
            submit_btn = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit_btn:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.usuario_id = res.user.id
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    st.session_state.autenticado = True
                    st.rerun()
                except Exception as e:
                    st.error("Credenciales incorrectas o error de conexión.")
    st.stop()
# ==========================================
# 2. SELECCIÓN DE EQUIPO
# ==========================================
if st.session_state.autenticado and not st.session_state.equipo_seleccionado:
    # 1. Aplicamos el fondo de imagen
    try:
        import base64
        with open("fondo_login.jpg", "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        css_fondo_equipos = f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        
        /* Asegurar que los botones de acceder tengan el estilo correcto */
        div[data-testid="column"] button {{
            background-color: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            color: #0f172a !important;
            font-weight: 800 !important;
        }}
        div[data-testid="column"] button:hover {{
            background-color: #e2e8f0 !important;
        }}
        
        /* Fondo blanco para el desplegable de Crear Equipo */
        div[data-testid="stExpander"] details {{
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 10px !important;
            border: 1px solid #cbd5e1 !important;
        }}
        div[data-testid="stExpander"] summary p {{
            color: #0f172a !important;
            font-weight: 800 !important;
        }}
        </style>
        """
        st.markdown(css_fondo_equipos, unsafe_allow_html=True)
    except FileNotFoundError:
        pass

    # Un poco de espacio superior y título centrado
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 40px; text-shadow: 0px 4px 10px rgba(0,0,0,0.6);'>📋 Selecciona tu Equipo</h2>", unsafe_allow_html=True)
    
    # Consulta a Supabase
    res_equipos = supabase.table("equipo_usuarios").select("equipo_id, equipos(nombre, categoria, division, escudo_base64)").eq("usuario_id", st.session_state.usuario_id).execute()
    
    if res_equipos.data:
        equipos_lista = res_equipos.data
        
        # Generar las tarjetas en una cuadrícula de 3 columnas
        for i in range(0, len(equipos_lista), 3):
            cols = st.columns(3)
            for j in range(3):
                idx_global = i + j
                if idx_global < len(equipos_lista):
                    eq_info = equipos_lista[idx_global]["equipos"]
                    eq_id = equipos_lista[idx_global]["equipo_id"]
                    
                    with cols[j]:
                        # 🌟 SOLUCIÓN DEFINITIVA: Cajas HTML nativas con estilos inline. 
                        # ¡Es imposible que Streamlit las vuelva transparentes!
                        escudo = eq_info.get("escudo_base64")
                        if escudo:
                            img_html = f'<img src="data:image/jpeg;base64,{escudo}" style="width:90px; height:90px; object-fit: cover; border-radius:50%; margin-bottom: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">'
                        else:
                            img_html = '<div style="font-size: 50px; margin-bottom: 10px;">🛡️</div>'
                            
                        nombre = eq_info.get('nombre', 'Equipo')
                        division = eq_info.get('division') or "Sin división"
                        categoria = eq_info.get('categoria') or ""
                        
                        tarjeta_html = f"""
                        <div style="background-color: #ffffff; padding: 25px 20px 15px 20px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 30px rgba(0,0,0,0.15); text-align: center; margin-bottom: 15px;">
                            {img_html}
                            <h3 style="color: #0f172a; font-weight: 800; margin-bottom: 0px; font-size: 1.25rem;">{nombre}</h3>
                            <p style="color: #475569; font-size: 0.85rem; margin-top: 2px;">{categoria} | {division}</p>
                        </div>
                        """
                        st.markdown(tarjeta_html, unsafe_allow_html=True)
                        
                        if st.button("🚀 Acceder", key=f"btn_{eq_id}", use_container_width=True):
                            if cargar_datos_equipo(eq_id):
                                st.session_state.equipo_seleccionado = True
                                st.rerun()
    else:
        st.info("No tienes equipos asignados actualmente.")
        
    st.markdown("---")
    
    # 4. BOTÓN "CREAR NUEVO EQUIPO" CENTRADO, ESTRECHO Y BLANCO
    col_exp_izq, col_exp_cen, col_exp_der = st.columns([2, 1.5, 2])
    
    with col_exp_cen:
        with st.expander("➕ Crear Nuevo Equipo"):
            with st.form("form_nuevo_equipo"):
                n_nombre = st.text_input("Nombre del Club / Equipo:")
                n_categoria = st.selectbox("Categoría:", ["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"])
                n_division = st.text_input("División / Liga:")
                n_temporada = st.text_input("Temporada:", value="2026/2027")
                
                # Inyectar CSS solo para el botón de este formulario específico
                st.markdown("""
                    <style>
                    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
                        background-color: #ffffff !important;
                        color: #000000 !important;
                        border: 1px solid #cbd5e1 !important;
                        font-weight: 800 !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                # Columnas internas para hacer el botón en sí aún más pequeño dentro del formulario
                c_btn1, c_btn2, c_btn3 = st.columns([1, 1.5, 1])
                with c_btn2:
                    btn_crear = st.form_submit_button("🚀 Crear y Acceder", use_container_width=True)
                
                if btn_crear and n_nombre:
                    res_insert = supabase.table("equipos").insert({
                        "nombre": n_nombre, "categoria": n_categoria, 
                        "division": n_division, "temporada": n_temporada,
                        "created_by": st.session_state.usuario_id
                    }).execute()
                    
                    nuevo_id = res_insert.data[0]['id']
                    
                    supabase.table("equipo_usuarios").insert({
                        "equipo_id": nuevo_id, "usuario_id": st.session_state.usuario_id, "rol": "owner"
                    }).execute()
                    
                    supabase.table("datos_equipo").insert({"equipo_id": nuevo_id}).execute()
                    
                    st.success("Equipo creado.")
                    st.rerun()

    st.stop()

# ==========================================
# 3. VALIDACIÓN DE ESTRUCTURAS EN MEMORIA
# ==========================================
for p in st.session_state.plantilla:
    if "lateralidad" not in p: p["lateralidad"] = "Diestro"
    if "foto" not in p: p["foto"] = None

for les in st.session_state.lesiones:
    if "dias_baja" not in les: les["dias_baja"] = None
    if "estado" not in les: les["estado"] = "Activa"

for s in st.session_state.sesiones:
    if s.get("informe_generado"):
        for d in s["datos_informe"]:
            for z in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor', 'MIN_GPS']:
                if z not in d: d[z] = 0.0

# ==========================================
# 4. SINCRONIZADOR DINÁMICO DE PLANTILLA
# ==========================================
if "plantilla" in st.session_state and st.session_state.plantilla:
    dict_pos = {limpiar_nombre(p["JUGADOR"]): p["POS"] for p in st.session_state.plantilla}
    dict_nombres = {limpiar_nombre(p["JUGADOR"]): p["JUGADOR"] for p in st.session_state.plantilla}
    
    for s in st.session_state.sesiones:
        if s.get("datos_informe"):
            for d in s["datos_informe"]:
                jug_limpio = limpiar_nombre(d.get("JUGADOR", ""))
                if jug_limpio in dict_pos:
                    d["POS"] = dict_pos[jug_limpio]
                    d["JUGADOR"] = dict_nombres[jug_limpio]

# ==========================================
# 5. PANEL PRINCIPAL DEL EQUIPO
# ==========================================

# --- GESTIÓN DEL ESCUDO Y DATOS DE CUENTA EN SESSION STATE ---
if "escudo_equipo" not in st.session_state:
    st.session_state.escudo_equipo = None

# Renderizar escudo y nombre en la barra lateral
st.sidebar.markdown('<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 5px;">', unsafe_allow_html=True)
if st.session_state.escudo_equipo:
    st.sidebar.markdown(f'<img src="data:image/jpeg;base64,{st.session_state.escudo_equipo}" style="width: 36px; height: 36px; object-fit: cover; border-radius: 50%;">', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span style="font-size: 28px;">🛡️</span>', unsafe_allow_html=True)

st.sidebar.markdown(f"<h2 style='margin: 0; font-size: 1.4rem;'>{st.session_state.nombre_equipo}</h2>", unsafe_allow_html=True)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

st.sidebar.caption(f"{st.session_state.categoria_equipo} | {st.session_state.division_equipo}")
st.sidebar.caption(f"Temp. {st.session_state.temporada_equipo}")
st.sidebar.markdown("---")

seccion_principal = st.sidebar.radio("Secciones:", [
    "📅 Entrenamiento", 
    "👥 Plantilla",
    "🚑 Lesiones",
    "📡 GPS",
    "⚖️ Antropometría",
    "📊 Valoraciones"
])

st.sidebar.markdown("---")

# --- BOTÓN Y EXPANDER DE MODIFICAR CUENTA ---
with st.sidebar.expander("⚙️ Modificar cuenta", expanded=False):
    with st.form("form_modificar_cuenta"):
        nuevo_nombre = st.text_input("Nombre del Club / Equipo:", value=st.session_state.nombre_equipo)
        nueva_categoria = st.selectbox("Categoría:", ["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"], index=["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"].index(st.session_state.categoria_equipo) if st.session_state.categoria_equipo in ["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"] else 0)
        nueva_division = st.text_input("División / Liga:", value=st.session_state.division_equipo)
        nueva_temporada = st.text_input("Temporada:", value=st.session_state.temporada_equipo)
        
        # --- AÑADIR ESTA LÍNEA PARA EL SELECTOR DE COLOR ---
        nuevo_color = st.color_picker("Color de la barra lateral:", value=st.session_state.get("color_sidebar", "#f1f5f9"))
        
        nuevo_escudo_up = st.file_uploader("Escudo del Equipo (Imagen):", type=["jpg", "png", "jpeg"])
        
        btn_guardar_cuenta = st.form_submit_button("💾 Guardar Cambios")
        if btn_guardar_cuenta:
            st.session_state.nombre_equipo = nuevo_nombre
            st.session_state.categoria_equipo = nueva_categoria
            st.session_state.division_equipo = nueva_division
            st.session_state.temporada_equipo = nueva_temporada
            st.session_state.color_sidebar = nuevo_color # <--- ACTUALIZAR ESTADO
            if nuevo_escudo_up:
                st.session_state.escudo_equipo = get_base64_of_bin_file(nuevo_escudo_up)
            guardar_datos()
            st.success("¡Datos de cuenta actualizados!")
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Borrar datos y empezar de cero", use_container_width=True):
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
            supabase.auth.sign_out()
        except:
            pass
        st.session_state.clear()
        st.rerun()
sesiones_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
conteo_entrenos = 0
conteo_amistosos = 0
conteo_liga = 0
conteo_copa = 0

for s in sesiones_crono:
    if s["tipo"] == "Entrenamiento":
        conteo_entrenos += 1
        s["nombre_dinamico"] = f"Sesión {conteo_entrenos}"
        s["subtitulo_dinamico"] = s.get("descripcion", "")
    elif s["tipo"] == "Partido Amistoso":
        conteo_amistosos += 1
        s["nombre_dinamico"] = f"Partido Amistoso {conteo_amistosos}"
        s["subtitulo_dinamico"] = f"vs {s.get('rival', 'Rival')}"
    elif s["tipo"] == "Partido Oficial":
        comp = s.get("competicion", "Liga")
        if comp == "Liga":
            conteo_liga += 1
            s["nombre_dinamico"] = f"Jornada {conteo_liga}"
        elif comp == "Copa":
            conteo_copa += 1
            s["nombre_dinamico"] = f"Ronda {conteo_copa}"
        s["subtitulo_dinamico"] = f"vs {s.get('rival', 'Rival')}"


# ==========================================
# PLANTILLA E INDIVIDUAL
# ==========================================
elif seccion_principal == "👥 Plantilla":
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

# ==========================================
# LESIONES
# ==========================================
elif seccion_principal == "🚑 Lesiones":
    st.subheader("🚑 Lesiones")
    
    tab_les_res, tab_les_list = st.tabs(["📊 Resumen", "📋 Listado de Lesiones"])
    
    les_data = st.session_state.get("lesiones", [])
    if not les_data:
        with tab_les_res: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
        with tab_les_list: st.success("¡Buenas noticias! No hay ninguna lesión registrada en el historial del equipo.")
    else:
        df_les = pd.DataFrame(les_data)
        df_les['Mes_Num'] = pd.to_datetime(df_les['id_sesion']).dt.month
        df_les['Mes'] = df_les['Mes_Num'].map(meses_esp)
        df_les['Gravedad'] = df_les['dias_baja'].apply(categorizar_duracion)
        
        with tab_les_res:
            st.markdown("#### 🔍 Filtros Epidemiológicos")
            cf1, cf2, cf3 = st.columns(3)
            
            meses_unicos = ["TODOS"] + list(df_les['Mes'].dropna().unique())
            filtro_mes = cf1.selectbox("Filtrar por Mes:", meses_unicos)
            
            filtro_tipo_ses = cf2.selectbox("Filtrar por Sesión:", ["TODOS", "Entrenamiento", "Partido"])
            
            jugs_unicos = ["TODOS"] + sorted([j["JUGADOR"] for j in st.session_state.plantilla])
            filtro_jugador = cf3.selectbox("Filtrar por Jugador:", jugs_unicos)
            
            df_filtrado = df_les.copy()
            if filtro_mes != "TODOS": df_filtrado = df_filtrado[df_filtrado['Mes'] == filtro_mes]
            if filtro_tipo_ses != "TODOS": df_filtrado = df_filtrado[df_filtrado['tipo_sesion'] == filtro_tipo_ses]
            if filtro_jugador != "TODOS": df_filtrado = df_filtrado[df_filtrado['jugador'] == filtro_jugador]
            
            if df_filtrado.empty:
                st.warning("No hay lesiones que coincidan con los filtros aplicados para este jugador/periodo.")
            else:
                total_lesiones = len(df_filtrado)
                total_dias = int(df_filtrado['dias_baja'].fillna(0).sum())
                promedio_dias = total_dias / total_lesiones if total_lesiones > 0 else 0
                
                horas_totales = 0
                for s in st.session_state.sesiones:
                    if s.get("informe_generado", False):
                        if filtro_mes != "TODOS" and meses_esp[datetime.strptime(s["fecha"], "%Y-%m-%d").month] != filtro_mes: continue
                        es_partido_s = "Partido" in s["tipo"]
                        if filtro_tipo_ses == "Entrenamiento" and es_partido_s: continue
                        if filtro_tipo_ses == "Partido" and not es_partido_s: continue
                        
                        for d in s["datos_informe"]:
                            if filtro_jugador == "TODOS" or d["JUGADOR"] == filtro_jugador:
                                horas_totales += float(d.get("MIN", 0)) / 60.0

                incidencia = (total_lesiones / horas_totales * 1000) if horas_totales > 0 else 0

                st.markdown("#### 🎯 Métricas Globales")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total de Lesiones", total_lesiones)
                k2.metric("Total Días de Baja", f"{total_dias} días")
                k3.metric("Promedio de Baja", f"{promedio_dias:.1f} días / lesión")
                k4.metric("Incidencia (/1000h)", f"{incidencia:.1f}", help="Fórmula: (Total Lesiones / Horas Totales Exposición) * 1000. \nCalculado usando los minutos GPS/RPE.")
                
                st.markdown("---")
                st.markdown("#### 📈 Desglose Estadístico")
                
                cg1, cg2 = st.columns(2)
                with cg1:
                    fig_dur = px.histogram(df_filtrado, x='Gravedad', title="1. Duración de la Lesión", color='Gravedad', category_orders={"Gravedad": ["Mínima (1-3d)", "Leve (4-7d)", "Moderada (8-28d)", "Grave (>28d)", "Activa"]})
                    fig_dur.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                    st.plotly_chart(fig_dur, use_container_width=True, key="les_hist_dur")
                with cg2:
                    fig_tipo = px.histogram(df_filtrado, x='tipo', title="2. Tipo de Lesión", color='tipo')
                    fig_tipo.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                    st.plotly_chart(fig_tipo, use_container_width=True, key="les_hist_tipo")
                    
                cg3, cg4 = st.columns(2)
                with cg3:
                    fig_zona = px.histogram(df_filtrado, x='zona', title="3. Zona Afectada", color='zona')
                    fig_zona.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                    st.plotly_chart(fig_zona, use_container_width=True, key="les_hist_zona")
                with cg4:
                    fig_lat = px.histogram(df_filtrado, x='lateralidad', title="4. Lateralidad Lesional", color='lateralidad')
                    fig_lat.update_layout(xaxis_title="", yaxis_title="Nº Lesiones")
                    st.plotly_chart(fig_lat, use_container_width=True, key="les_hist_lat")
                    
                cg5, cg6 = st.columns(2)
                with cg5:
                    conteo_recidiva = df_filtrado['recidiva'].value_counts().reset_index()
                    fig_rec = px.pie(conteo_recidiva, names='recidiva', values='count', title="5. Índice de Recidiva", hole=0.4)
                    st.plotly_chart(fig_rec, use_container_width=True, key="les_pie_rec")
                with cg6:
                    conteo_sup = df_filtrado['cesped'].value_counts().reset_index()
                    fig_sup = px.pie(conteo_sup, names='cesped', values='count', title="6. Superficie de Juego", hole=0.4)
                    st.plotly_chart(fig_sup, use_container_width=True, key="les_pie_sup")

        with tab_les_list:
            cols_mostrar = ["id_sesion", "tipo_sesion", "jugador", "tipo", "zona", "lado", "lateralidad", "contacto", "cesped", "recidiva", "estado", "dias_baja", "comentarios"]
            df_mostrar = df_les[cols_mostrar].rename(columns={
                "id_sesion": "Fecha", "tipo_sesion": "Sesión", "jugador": "Jugador", "tipo": "Tipo", 
                "zona": "Zona", "lado": "Lado", "lateralidad": "Lateralidad", "contacto": "Contacto", 
                "cesped": "Superficie", "recidiva": "Recidiva", "estado": "Estado", "dias_baja": "Días Baja", "comentarios": "Comentarios"
            })
            mostrar_tabla_moderna(df_mostrar.style.hide(axis="index"))
            
            st.markdown("---")
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                st.markdown("#### 🩺 Gestor de Altas Médicas")
                lesiones_activas = [l for l in st.session_state.lesiones if l.get("estado") == "Activa"]
                
                if not lesiones_activas:
                    st.success("✅ ¡Toda la plantilla está sana! No hay ninguna lesión activa pendiente de cerrar.")
                else:
                    nombres_lesiones_activas = [f"{l['id_sesion']} | {l['jugador']} - {l['tipo']} ({l['zona']})" for l in lesiones_activas]
                    les_seleccionada_idx = st.selectbox("Selecciona la lesión que deseas dar de alta:", range(len(lesiones_activas)), format_func=lambda x: nombres_lesiones_activas[x])
                    les_obj = lesiones_activas[les_seleccionada_idx]
                    
                    fecha_lesion = datetime.strptime(les_obj["id_sesion"], "%Y-%m-%d")
                    fecha_alta_sugerida = None
                    dias_sugeridos = 0
                    
                    sesiones_ordenadas_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
                    for s in sesiones_ordenadas_crono:
                        s_dt = datetime.strptime(s["fecha"], "%Y-%m-%d")
                        if s_dt > fecha_lesion:
                            disp_jug = s.get("disponibilidad", {}).get(les_obj["jugador"], "")
                            if disp_jug in ["Disponible", "Titular", "Suplente"]:
                                fecha_alta_sugerida = s_dt
                                dias_sugeridos = (fecha_alta_sugerida - fecha_lesion).days
                                break
                    
                    with st.form("form_alta_medica"):
                        st.write(f"Actualizando lesión de **{les_obj['jugador']}** (Iniciada el {les_obj['id_sesion']})")
                        
                        if fecha_alta_sugerida:
                            st.info(f"💡 **Auto-Detección:** {les_obj['jugador']} volvió a estar '{disp_jug}' el **{fecha_alta_sugerida.strftime('%Y-%m-%d')}**.")
                            dias_baja_input = st.number_input("Días de Baja Totales:", min_value=1, max_value=500, value=dias_sugeridos)
                        else:
                            st.warning("El jugador no ha vuelto a estar disponible en ninguna sesión registrada.")
                            dias_baja_input = st.number_input("Días de Baja Totales (Añadir manualmente):", min_value=1, max_value=500, value=7)
                            
                        if st.form_submit_button("✅ Procesar Alta Médica"):
                            for L in st.session_state.lesiones:
                                if L["id_sesion"] == les_obj["id_sesion"] and L["jugador"] == les_obj["jugador"] and L["tipo"] == les_obj["tipo"]:
                                    L["estado"] = "Recuperado"
                                    L["dias_baja"] = dias_baja_input
                                    break
                            guardar_datos()
                            st.success(f"Alta médica procesada. {les_obj['jugador']} estuvo {dias_baja_input} días de baja.")
                            st.rerun()

            with col_m2:
                st.markdown("#### 📝 Editar Comentarios")
                lesiones_todas_ordenadas = sorted(st.session_state.lesiones, key=lambda x: x.get("fecha_registro", "2000-01-01"), reverse=True)
                nombres_les_todas = [f"{l['id_sesion']} | {l['jugador']} ({l['tipo']})" for l in lesiones_todas_ordenadas]
                
                les_edit_idx = st.selectbox("Selecciona una lesión del historial:", range(len(lesiones_todas_ordenadas)), format_func=lambda x: nombres_les_todas[x])
                les_edit_obj = lesiones_todas_ordenadas[les_edit_idx]
                
                with st.form("form_edit_coment"):
                    nuevo_com = st.text_area("Modificar comentario / mecanismo lesional:", value=les_edit_obj.get("comentarios", ""))
                    if st.form_submit_button("💾 Guardar Cambios"):
                        real_idx = st.session_state.lesiones.index(les_edit_obj)
                        st.session_state.lesiones[real_idx]["comentarios"] = nuevo_com
                        guardar_datos()
                        st.success("¡Comentario actualizado correctamente!")
                        st.rerun()

# ==========================================
# GPS
# ==========================================
elif seccion_principal == "📡 GPS":
    st.subheader("📡 GPS")
    
    lista_micro_map = []
    for s in st.session_state.sesiones:
        if s.get("informe_generado"):
            num_sem = obtener_numero_semana(s["fecha"])
            _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
            lista_micro_map.append({"num_semana": num_sem, "lunes_dt": lunes})
            
    mapa_micros = {}
    if lista_micro_map:
        df_m_map = pd.DataFrame(lista_micro_map).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
        mapa_micros = {row["num_semana"]: i + 1 for i, row in df_m_map.iterrows()}
    
    datos_gps = []
    for s in st.session_state.sesiones:
        if s.get("informe_generado"):
            es_partido = "Partido" in s["tipo"]
            tipo_str = "Partido" if es_partido else "Entrenamiento"
            md_str = s["descripcion"]
            
            disp_s = s.get("disponibilidad", {})
            disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
            
            for d in s["datos_informe"]:
                jug_nombre = d["JUGADOR"]
                est_jug = disp_s_clean.get(limpiar_nombre(jug_nombre), "Disponible")
                
                # FILTRO DE EXCLUSIÓN PARA GPS GLOBAL: Solo jugadores válidos y con distancia > 0
                if est_jug in ["Disponible", "Titular", "Suplente"] and float(d.get("DIS", 0)) > 0:
                    min_val = float(d.get("MIN_GPS", d.get("MIN", 0)))
                    if min_val == 0: min_val = 1 
                    
                    num_sem = obtener_numero_semana(s["fecha"])
                    id_micro = mapa_micros.get(num_sem, num_sem)
                    
                    datos_gps.append({
                        "FECHA": s["fecha"],
                        "TIPO": tipo_str,
                        "MD": md_str,
                        "Microciclo": f"Microciclo {id_micro}",
                        "Nombre_Sesion": f"{s['fecha']} | {s.get('nombre_dinamico', s['tipo'])}",
                        "JUGADOR": d["JUGADOR"],
                        "POS": d.get("POS", ""),
                        "MIN": min_val,
                        "DIS": float(d.get("DIS", 0)),
                        "DIS AI": float(d.get("HID >21", d.get("DIS AI", 0))),
                        "Nº SPR": float(d.get("SPR >24", d.get("Nº SPR", 0))),
                        "ACC": float(d.get("ACC >3", d.get("ACC", 0))),
                        "DCC": float(d.get("DCC >3", d.get("DCC", 0))),
                        "VMAX": float(d.get("V_Max", d.get("VMAX", 0))),
                        "Z1": float(d.get("Z1", 0)),
                        "Z2": float(d.get("Z2", 0)),
                        "Z3": float(d.get("Z3", 0)),
                        "Z4": float(d.get("Z4", 0)),
                        "Z5": float(d.get("Z5", 0)),
                        "Z6": float(d.get("Z6", 0))
                    })
                    
    df_gps = pd.DataFrame(datos_gps)
    
    tab_gps_perf, tab_gps_comp = st.tabs(["📈 Perfil de Rendimiento", "⚖️ Comparador"])
    
    if df_gps.empty:
        st.info("No hay datos de GPS registrados todavía. Procesa datos en alguna sesión para visualizarlos aquí.")
    else:
        cols_dinamicas = ['DIS', 'DIS AI', 'ACC', 'DCC', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
        for c in cols_dinamicas:
            df_gps[f'{c}/min'] = np.where(df_gps['MIN'] > 0, df_gps[c] / df_gps['MIN'], 0)

        lista_jugs = sorted(df_gps['JUGADOR'].unique())
        lista_pos = ["POR", "DEF", "MED", "ATA"]
        lista_mds = ["TODOS", "MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"]

        def aplicar_filtros_gps(df, target_tipo, target_md, target_nivel, target_jug, target_pos, target_tiempo="Histórico Completo", target_sel_tiempo="TODOS"):
            res = df.copy()
            
            if target_tiempo == "Microciclo Concreto" and target_sel_tiempo != "TODOS":
                res = res[res['Microciclo'] == target_sel_tiempo]
            elif target_tiempo == "Sesión Concreta" and target_sel_tiempo != "TODOS":
                res = res[res['Nombre_Sesion'] == target_sel_tiempo]
                
            if target_tipo != "TODOS":
                res = res[res['TIPO'] == target_tipo]
                if target_tipo == "Entrenamiento" and target_md != "TODOS":
                    res = res[res['MD'] == target_md]
            if target_nivel == "Jugador":
                if target_jug != "TODOS": res = res[res['JUGADOR'] == target_jug]
            elif target_nivel == "Posición":
                res = res[res['POS'] == target_pos]
            return res

        with tab_gps_perf:
            st.markdown("#### 🔍 Filtros de Rendimiento")
            
            c_t1, c_t2 = st.columns(2)
            f_tiempo = c_t1.selectbox("Filtro Temporal:", ["Histórico Completo", "Microciclo Concreto", "Sesión Concreta"], key="p_tiempo")
            f_sel_tiempo = "TODOS"
            
            if f_tiempo == "Microciclo Concreto":
                lista_micros = sorted(df_gps['Microciclo'].unique(), key=lambda x: int(x.split()[1]))
                f_sel_tiempo = c_t2.selectbox("Seleccionar Microciclo:", lista_micros, key="p_sel_micro")
            elif f_tiempo == "Sesión Concreta":
                lista_sesiones = sorted(df_gps['Nombre_Sesion'].unique(), reverse=True)
                f_sel_tiempo = c_t2.selectbox("Seleccionar Sesión:", lista_sesiones, key="p_sel_ses")

            c1, c2, c3, c4 = st.columns(4)
            f_tipo = c1.selectbox("Sesión:", ["TODOS", "Entrenamiento", "Partido"], key="p_tipo")
            f_md = "TODOS"
            if f_tipo == "Entrenamiento": f_md = c2.selectbox("Match Day:", lista_mds, key="p_md")
            
            f_nivel = c3.radio("Analizar por:", ["Equipo Completo", "Posición", "Jugador"], key="p_niv")
            f_jug, f_pos = "TODOS", "DEF"
            if f_nivel == "Jugador": f_jug = c4.selectbox("Seleccionar Jugador:", ["TODOS"] + lista_jugs, key="p_jug")
            elif f_nivel == "Posición": f_pos = c4.selectbox("Seleccionar Posición:", lista_pos, key="p_pos")

            df_perfil = aplicar_filtros_gps(df_gps, f_tipo, f_md, f_nivel, f_jug, f_pos, f_tiempo, f_sel_tiempo)

            if df_perfil.empty:
                st.warning("No hay datos para esta combinación de filtros.")
            else:
                kpis = df_perfil[['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX']].mean()
                kpis_rel = df_perfil[['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min']].mean()

                st.markdown("---")
                st.markdown("#### 🚀 Promedios Absolutos (Totales)")
                kp1, kp2, kp3, kp4, kp5, kp6, kp7 = st.columns(7)
                kp1.metric("Minutos GPS", f"{kpis['MIN']:.1f}")
                kp2.metric("Distancia (km)", f"{kpis['DIS']:.2f}")
                kp3.metric("HSR (m)", f"{kpis['DIS AI']:.1f}")
                kp4.metric("Sprints", f"{kpis['Nº SPR']:.1f}")
                kp5.metric("Aceleraciones", f"{kpis['ACC']:.1f}")
                kp6.metric("Deceleraciones", f"{kpis['DCC']:.1f}")
                kp7.metric("V. Max (km/h)", f"{kpis['VMAX']:.1f}")

                st.markdown("#### ⏱️ Promedios Relativos (Por Minuto de GPS)")
                kr1, kr2, kr3, kr4 = st.columns(4)
                kr1.metric("m / min", f"{(kpis_rel['DIS/min']*1000):.1f}")
                kr2.metric("HSR m / min", f"{(kpis_rel['DIS AI/min']*1000):.2f}")
                kr3.metric("ACC / min", f"{kpis_rel['ACC/min']:.2f}")
                kr4.metric("DCC / min", f"{kpis_rel['DCC/min']:.2f}")
                
                st.markdown("---")
                st.markdown("#### 🔬 Desglose Exhaustivo de Zonas de Velocidad")
                
                todas_kpis = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
                todas_kpis_rel = [f'{c}/min' for c in ['DIS', 'DIS AI', 'ACC', 'DCC', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']]
                
                medias_abs = df_perfil[todas_kpis].mean().round(2).to_dict()
                medias_rel = df_perfil[todas_kpis_rel].mean().round(3).to_dict()
                
                df_detallado = pd.DataFrame({
                    "Variable": ["Minutos GPS", "Distancia Total", "HSR (>21km/h)", "Sprints", "ACC", "DCC", "V. Máxima", "Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5", "Zona 6"],
                    "Promedio Acumulado": [
                        medias_abs['MIN'], medias_abs['DIS'], medias_abs['DIS AI'], medias_abs['Nº SPR'], 
                        medias_abs['ACC'], medias_abs['DCC'], medias_abs['VMAX'],
                        medias_abs['Z1'], medias_abs['Z2'], medias_abs['Z3'], medias_abs['Z4'], medias_abs['Z5'], medias_abs['Z6']
                    ],
                    "Promedio por Minuto": [
                        "-", medias_rel['DIS/min'], medias_rel['DIS AI/min'], "-", 
                        medias_rel['ACC/min'], medias_rel['DCC/min'], "-",
                        medias_rel['Z1/min'], medias_rel['Z2/min'], medias_rel['Z3/min'], 
                        medias_rel['Z4/min'], medias_rel['Z5/min'], medias_rel['Z6/min']
                    ]
                })
                mostrar_tabla_moderna(df_detallado.style.hide(axis="index"))

        with tab_gps_comp:
            st.markdown("#### ⚖️ Comparador (A vs B vs C)")
            
            colA, colB, colC = st.columns(3)
            with colA:
                st.markdown("##### 🔵 Perfil A")
                a_tipo = st.selectbox("Sesión (A):", ["TODOS", "Entrenamiento", "Partido"], key="c_a_tipo")
                a_md = "TODOS"
                if a_tipo == "Entrenamiento": a_md = st.selectbox("MD (A):", lista_mds, key="c_a_md")
                a_nivel = st.radio("Filtro (A):", ["Jugador", "Posición", "Equipo Completo"], key="c_a_niv")
                a_jug, a_pos = "TODOS", "DEF"
                if a_nivel == "Jugador": a_jug = st.selectbox("Jugador (A):", lista_jugs, key="c_a_jug")
                elif a_nivel == "Posición": a_pos = st.selectbox("Posición (A):", lista_pos, key="c_a_pos")
            
            with colB:
                st.markdown("##### 🔴 Perfil B")
                b_tipo = st.selectbox("Sesión (B):", ["TODOS", "Entrenamiento", "Partido"], key="c_b_tipo")
                b_md = "TODOS"
                if b_tipo == "Entrenamiento": b_md = st.selectbox("MD (B):", lista_mds, key="c_b_md")
                b_nivel = st.radio("Filtro (B):", ["Jugador", "Posición", "Equipo Completo"], key="c_b_niv")
                b_jug, b_pos = "TODOS", "MED"
                if b_nivel == "Jugador": b_jug = st.selectbox("Jugador (B):", lista_jugs, key="c_b_jug")
                elif b_nivel == "Posición": b_pos = st.selectbox("Posición (B):", lista_pos, key="c_b_pos")

            with colC:
                st.markdown("##### 🟢 Perfil C (Opcional)")
                usar_C = st.checkbox("Activar Perfil C")
                if usar_C:
                    c_tipo = st.selectbox("Sesión (C):", ["TODOS", "Entrenamiento", "Partido"], key="c_c_tipo")
                    c_md = "TODOS"
                    if c_tipo == "Entrenamiento": c_md = st.selectbox("MD (C):", lista_mds, key="c_c_md")
                    c_nivel = st.radio("Filtro (C):", ["Jugador", "Posición", "Equipo Completo"], key="c_c_niv")
                    c_jug, c_pos = "TODOS", "ATA"
                    if c_nivel == "Jugador": c_jug = st.selectbox("Jugador (C):", lista_jugs, key="c_c_jug")
                    elif c_nivel == "Posición": c_pos = st.selectbox("Posición (C):", lista_pos, key="c_c_pos")
                else:
                    c_tipo, c_md, c_nivel, c_jug, c_pos = "TODOS", "TODOS", "Equipo Completo", "TODOS", "ATA"

            df_A = aplicar_filtros_gps(df_gps, a_tipo, a_md, a_nivel, a_jug, a_pos)
            df_B = aplicar_filtros_gps(df_gps, b_tipo, b_md, b_nivel, b_jug, b_pos)
            df_C = aplicar_filtros_gps(df_gps, c_tipo, c_md, c_nivel, c_jug, c_pos) if usar_C else pd.DataFrame()

            if df_A.empty or df_B.empty or (usar_C and df_C.empty):
                st.warning("⚠️ Uno de los perfiles activos no tiene datos. Revisa los filtros.")
            else:
                st.markdown("---")
                modo_comp = st.radio("¿Qué tipo de métricas quieres comparar?", ["Absolutas (Totales)", "Relativas (Por Minuto)"], horizontal=True)
                
                if modo_comp == "Absolutas (Totales)":
                    metrics_to_compare = ['MIN', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']
                else:
                    metrics_to_compare = ['DIS/min', 'DIS AI/min', 'ACC/min', 'DCC/min', 'Z1/min', 'Z2/min', 'Z3/min', 'Z4/min', 'Z5/min', 'Z6/min']

                mean_A = df_A[metrics_to_compare].mean()
                mean_B = df_B[metrics_to_compare].mean()
                mean_C = df_C[metrics_to_compare].mean() if usar_C else None

                comp_data = []
                for m in metrics_to_compare:
                    valA = mean_A[m] if not pd.isna(mean_A[m]) else 0
                    valB = mean_B[m] if not pd.isna(mean_B[m]) else 0
                    valC = mean_C[m] if usar_C and not pd.isna(mean_C[m]) else 0
                    
                    if 'DIS/min' in m or 'DIS AI/min' in m:
                        valA, valB, valC = valA * 1000, valB * 1000, valC * 1000

                    diff_str_B = f"{(((valB - valA) / valA) * 100):+.1f}%" if valA > 0 else "N/A"
                    diff_str_C = f"{(((valC - valA) / valA) * 100):+.1f}%" if usar_C and valA > 0 else "N/A"
                        
                    fila = {
                        "Métrica": m.replace("/min", " (m/min)" if "DIS" in m else " / min"),
                        "A": round(valA, 2),
                        "B": round(valB, 2),
                        "Dif. B vs A": diff_str_B
                    }
                    if usar_C:
                        fila["C"] = round(valC, 2)
                        fila["Dif. C vs A"] = diff_str_C
                        
                    comp_data.append(fila)
                    
                st.markdown("#### 📊 Tabla de Comparación Triple")
                columnas_estilo = ["Dif. B vs A", "Dif. C vs A"] if usar_C else ["Dif. B vs A"]
                mostrar_tabla_moderna(pd.DataFrame(comp_data).style.hide(axis="index").map(lambda x: "color: #28a745" if "+" in str(x) else ("color: #ff4b4b" if "-" in str(x) else ""), subset=columnas_estilo))

# ==========================================
# ANTROPOMETRÍA
# ==========================================
elif seccion_principal == "⚖️ Antropometría":
    st.subheader("⚖️ Antropometría y Composición Corporal")
    
    tab_antro_res, tab_antro_jug, tab_antro_up = st.tabs(["📊 Resumen Analítico", "👤 Jugadores", "📂 Cargar Datos"])
    
    antro_data = st.session_state.get("antropometria", [])
    
    with tab_antro_res:
        if not antro_data:
            st.info("Aún no hay datos antropométricos registrados. Sube tu Excel en la pestaña 'Cargar Datos'.")
        else:
            df_antro = pd.DataFrame(antro_data)
            
            df_antro['fecha_dt'] = pd.to_datetime(df_antro['fecha'])
            df_antro['Mes_Num'] = df_antro['fecha_dt'].dt.month
            df_antro['Mes'] = df_antro['Mes_Num'].map(meses_esp)
            
            df_antro['Suma_Pliegues'] = df_antro['P_Tricipital'] + df_antro['P_Subescapular'] + df_antro['P_Suprailiaco'] + df_antro['P_Abdominal']
            df_antro['% Graso'] = (df_antro['Suma_Pliegues'] * 0.1537) + 5.783
            df_antro['Kg Magros'] = df_antro['Peso'] - (df_antro['Peso'] * (df_antro['% Graso'] / 100))
            
            dict_pos = {j['JUGADOR']: j['POS'] for j in st.session_state.plantilla}
            df_antro['POS'] = df_antro['jugador'].map(lambda x: dict_pos.get(x, "N/A"))

            st.markdown("#### 🔍 Filtros Antropométricos")
            ca1, ca2, ca3 = st.columns(3)
            
            jugs_unicos = ["TODOS"] + sorted(df_antro['jugador'].unique())
            filtro_jug = ca1.selectbox("Jugador:", jugs_unicos, key="ant_jug")
            
            filtro_pos = ca2.selectbox("Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], key="ant_pos")
            
            meses_unicos = ["TODOS Anual"] + list(df_antro['Mes'].dropna().unique())
            filtro_mes = ca3.selectbox("Mes:", meses_unicos, key="ant_mes")
            
            df_filt = df_antro.copy()
            if filtro_jug != "TODOS": df_filt = df_filt[df_filt['jugador'] == filtro_jug]
            if filtro_pos != "TODOS": df_filt = df_filt[df_filt['POS'] == filtro_pos]
            if filtro_mes != "TODOS Anual": df_filt = df_filt[df_filt['Mes'] == filtro_mes]
            
            if df_filt.empty:
                st.warning("No hay datos para esta combinación.")
            else:
                kpi_peso = df_filt['Peso'].mean()
                kpi_grasa = df_filt['% Graso'].mean()
                kpi_magro = df_filt['Kg Magros'].mean()
                
                st.markdown("#### 🎯 Promedios del Filtro")
                k1, k2, k3 = st.columns(3)
                k1.metric("Peso Medio", f"{kpi_peso:.1f} kg")
                k2.metric("% Graso Medio (Yuhasz)", f"{kpi_grasa:.2f} %")
                k3.metric("Masa Magra Media", f"{kpi_magro:.1f} kg")
                
                st.markdown("---")
                st.markdown("#### 📈 Evolución Mensual")
                
                meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
                df_evo = df_filt.groupby('Mes')[['Peso', '% Graso', 'Kg Magros']].mean().reindex(meses_temporada).reset_index()
                
                fig_evo = go.Figure()
                fig_evo.add_trace(go.Bar(x=df_evo['Mes'], y=df_evo['Peso'], name="Peso (kg)", marker_color='#00b4d8'))
                fig_evo.add_trace(go.Scatter(x=df_evo['Mes'], y=df_evo['% Graso'], name="% Graso", yaxis="y2", mode="lines+markers", line=dict(color="#ff4b4b", width=3)))
                fig_evo.update_layout(
                    title="Evolución: Peso vs % Graso", 
                    yaxis_title="Peso (kg)", 
                    yaxis2=dict(title="% Grasa", overlaying="y", side="right"),
                    xaxis=dict(categoryorder='array', categoryarray=meses_temporada)
                )
                
                st.plotly_chart(fig_evo, use_container_width=True, key="antro_resumen_evo")

    with tab_antro_jug:
        if not st.session_state.plantilla:
            st.info("Primero debes añadir jugadores en la sección 'Plantilla'.")
        elif not antro_data:
            st.info("Sube primero un archivo Excel con pesajes en la pestaña 'Cargar Datos'.")
        else:
            nombres_plantilla = sorted([j["JUGADOR"] for j in st.session_state.plantilla])
            jugador_seleccionado = st.selectbox("Selecciona un jugador para ver su perfil antropométrico:", nombres_plantilla)
            
            df_antro = pd.DataFrame(antro_data)
            df_antro['fecha_dt'] = pd.to_datetime(df_antro['fecha'])
            df_jug_antro = df_antro[df_antro['jugador'] == jugador_seleccionado].sort_values('fecha_dt', ascending=False)
            
            if df_jug_antro.empty:
                st.warning(f"No hay registros antropométricos para {jugador_seleccionado}.")
            else:
                df_jug_antro['Suma_Pliegues'] = df_jug_antro['P_Tricipital'] + df_jug_antro['P_Subescapular'] + df_jug_antro['P_Suprailiaco'] + df_jug_antro['P_Abdominal']
                df_jug_antro['% Graso'] = (df_jug_antro['Suma_Pliegues'] * 0.1537) + 5.783
                df_jug_antro['Kg Magros'] = df_jug_antro['Peso'] - (df_jug_antro['Peso'] * (df_jug_antro['% Graso'] / 100))
                
                ultimo_pesaje = df_jug_antro.iloc[0]
                
                st.markdown(f"#### ⚖️ Pesaje Actual ({ultimo_pesaje['fecha']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Peso", f"{ultimo_pesaje['Peso']:.1f} kg")
                c2.metric("% Graso (Yuhasz)", f"{ultimo_pesaje['% Graso']:.2f} %")
                c3.metric("Masa Magra", f"{ultimo_pesaje['Kg Magros']:.1f} kg")
                c4.metric("∑ 4 Pliegues", f"{ultimo_pesaje['Suma_Pliegues']:.1f} mm")
                
                st.markdown("#### 📏 Asimetrías Perimetrales (Actual)")
                st.caption("Valores en cm. Un número positivo indica que el lado Derecho es mayor; negativo, el Izquierdo.")
                ca1, ca2, ca3 = st.columns(3)
                dif_muslo = ultimo_pesaje['Per_Muslo_D'] - ultimo_pesaje['Per_Muslo_I']
                dif_pierna = ultimo_pesaje['Per_Pierna_D'] - ultimo_pesaje['Per_Pierna_I']
                dif_biceps = ultimo_pesaje['Per_Biceps_D'] - ultimo_pesaje['Per_Biceps_I']
                
                ca1.metric("Muslo (D - I)", f"{dif_muslo:+.1f} cm")
                ca2.metric("Pierna (D - I)", f"{dif_pierna:+.1f} cm")
                ca3.metric("Bíceps (D - I)", f"{dif_biceps:+.1f} cm")
                
                st.markdown("---")
                st.markdown("#### 📈 Evolución Histórica")
                
                df_jug_antro['Mes_Num'] = df_jug_antro['fecha_dt'].dt.month
                df_jug_antro['Mes'] = df_jug_antro['Mes_Num'].map(meses_esp)
                
                meses_temporada = ["Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio"]
                df_evo_jug = df_jug_antro.groupby('Mes')[['Peso', '% Graso']].mean().reindex(meses_temporada).reset_index()
                
                fig_evo_jug = go.Figure()
                fig_evo_jug.add_trace(go.Bar(x=df_evo_jug['Mes'], y=df_evo_jug['Peso'], name="Peso (kg)", marker_color='#00b4d8'))
                fig_evo_jug.add_trace(go.Scatter(x=df_evo_jug['Mes'], y=df_evo_jug['% Graso'], name="% Graso", yaxis="y2", mode="lines+markers", line=dict(color="#ff4b4b", width=3)))
                fig_evo_jug.update_layout(
                    title=f"Evolución: {jugador_seleccionado}", 
                    yaxis_title="Peso (kg)", 
                    yaxis2=dict(title="% Grasa", overlaying="y", side="right"),
                    xaxis=dict(categoryorder='array', categoryarray=meses_temporada)
                )
                st.plotly_chart(fig_evo_jug, use_container_width=True, key=f"antro_jug_evo_{jugador_seleccionado}")
                
                st.markdown("#### 📋 Historial Completo")
                columnas_mostrar = ['fecha', 'Peso', '% Graso', 'Kg Magros', 'Suma_Pliegues', 'Per_Pecho', 'Per_Cintura', 'Per_Cadera']
                mostrar_tabla_moderna(df_jug_antro[columnas_mostrar].style.hide(axis="index").format(precision=2))

    with tab_antro_up:
        st.info("Prepara un archivo Excel (.xlsx) con los pesajes. El sistema leerá automáticamente las 15 primeras columnas en el orden exacto indicado abajo.")
        st.markdown("""
        **Orden estricto de columnas (La fila 1 debe ser para los títulos):**
        1. Nombre del jugador
        2. Peso
        3. Pliegue tricipital
        4. Pliegue subescapular
        5. Pliegue suprailíaco
        6. Pliegue abdominal
        7. Perímetro pecho
        8. Perímetro cintura
        9. Perímetro cadera
        10. Perímetro muslo derecho
        11. Perímetro muslo izquierdo
        12. Perímetro pierna derecha
        13. Perímetro pierna izquierda
        14. Perímetro bíceps derecho
        15. Perímetro bíceps izquierdo
        """)
        
        c_up1, c_up2 = st.columns([1, 2])
        with c_up1:
            fecha_pesaje = st.date_input("Fecha del pesaje:", date.today())
        with c_up2:
            archivo_antro = st.file_uploader("Sube el Excel mensual de antropometría:", type=["xlsx"])
        
        if st.button("Procesar Archivo Antropométrico") and archivo_antro is not None:
            try:
                df_up = pd.read_excel(archivo_antro)
                
                if len(df_up.columns) < 15:
                    st.error("❌ El archivo Excel no tiene las 15 columnas necesarias. Revisa la plantilla.")
                else:
                    registros_nuevos = 0
                    for idx, row in df_up.iterrows():
                        nombre_crudo = str(row.iloc[0]).strip()
                        if pd.isna(row.iloc[0]) or nombre_crudo == "nan" or nombre_crudo == "":
                            continue
                            
                        jug_nombre_limpio = limpiar_nombre(nombre_crudo)
                        match_jugador = next((p["JUGADOR"] for p in st.session_state.plantilla if limpiar_nombre(p["JUGADOR"]) == jug_nombre_limpio), None)
                        
                        nombre_final = match_jugador if match_jugador else nombre_crudo
                        
                        nuevo_pesaje = {
                            "fecha": str(fecha_pesaje),
                            "jugador": nombre_final,
                            "Peso": float(row.iloc[1]) if not pd.isna(row.iloc[1]) else 0.0,
                            "P_Tricipital": float(row.iloc[2]) if not pd.isna(row.iloc[2]) else 0.0,
                            "P_Subescapular": float(row.iloc[3]) if not pd.isna(row.iloc[3]) else 0.0,
                            "P_Suprailiaco": float(row.iloc[4]) if not pd.isna(row.iloc[4]) else 0.0,
                            "P_Abdominal": float(row.iloc[5]) if not pd.isna(row.iloc[5]) else 0.0,
                            "Per_Pecho": float(row.iloc[6]) if not pd.isna(row.iloc[6]) else 0.0,
                            "Per_Cintura": float(row.iloc[7]) if not pd.isna(row.iloc[7]) else 0.0,
                            "Per_Cadera": float(row.iloc[8]) if not pd.isna(row.iloc[8]) else 0.0,
                            "Per_Muslo_D": float(row.iloc[9]) if not pd.isna(row.iloc[9]) else 0.0,
                            "Per_Muslo_I": float(row.iloc[10]) if not pd.isna(row.iloc[10]) else 0.0,
                            "Per_Pierna_D": float(row.iloc[11]) if not pd.isna(row.iloc[11]) else 0.0,
                            "Per_Pierna_I": float(row.iloc[12]) if not pd.isna(row.iloc[12]) else 0.0,
                            "Per_Biceps_D": float(row.iloc[13]) if not pd.isna(row.iloc[13]) else 0.0,
                            "Per_Biceps_I": float(row.iloc[14]) if not pd.isna(row.iloc[14]) else 0.0,
                        }
                        st.session_state.antropometria.append(nuevo_pesaje)
                        registros_nuevos += 1
                        
                    guardar_datos()
                    st.success(f"✅ ¡{registros_nuevos} pesajes procesados e integrados con éxito!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al leer el archivo. Asegúrate de que el formato es correcto. Detalle técnico: {e}")

# ==========================================
# VALORACIONES
# ==========================================
elif seccion_principal == "📊 Valoraciones":
    st.subheader("📊 Valoraciones Físicas y Tests")
    
    # Inicializar memoria para valoraciones si no existe
    if "val_inicial" not in st.session_state: st.session_state.val_inicial = []
    if "val_rom" not in st.session_state: st.session_state.val_rom = []
    if "val_1rm" not in st.session_state: st.session_state.val_1rm = []
    
    tab_val_res, tab_val_jug, tab_val_up = st.tabs(["📊 Resumen", "👤 Jugadores", "📂 Subir datos"])
    
    # --- FUNCIONES MATEMÁTICAS Y DE AYUDA ---
    def calcular_1rm(cargas, velocidades):
        validos = [(safe_float(c), safe_float(v)) for c, v in zip(cargas, velocidades) if safe_float(c) > 0 and safe_float(v) > 0]
        if not validos: return 0.0
        carga_max, vel_max = max(validos, key=lambda item: item[0])
        porcentaje_rm = -5.961 * (vel_max**2) - 50.71 * vel_max + 117
        if porcentaje_rm <= 0: return 0.0
        return carga_max / (porcentaje_rm / 100)

    def calcular_potencia_max(cargas, velocidades):
        potencias = []
        for c, v in zip(cargas, velocidades):
            c_val, v_val = safe_float(c), safe_float(v)
            if c_val > 0 and v_val > 0:
                pot_val = (c_val * 9.81) * v_val
                potencias.append(pot_val)
        return max(potencias) if potencias else 0.0

    def calc_asimetria(der, izq):
        d, i = safe_float(der), safe_float(izq)
        if max(d, i) == 0: return 0.0
        return (abs(d - i) / max(d, i)) * 100
        
    def procesar_textos(lista_dicts, columna):
        items = []
        for row in lista_dicts:
            val = row.get(columna)
            if val is not None and str(val).strip() != "" and str(val).lower() != "nan":
                items.extend([t.strip().capitalize() for t in str(val).split(',')])
        return Counter(items).most_common(5)

    # ---------------------------------------------------------
    # PESTAÑA 3: SUBIR DATOS
    # ---------------------------------------------------------
    with tab_val_up:
        st.markdown("#### 📂 Carga de Archivos Excel y Sincronización")
        
        import difflib
        import json
        
        def sincronizar_nombres_df(df, col_jugador):
            if df.empty or col_jugador not in df.columns:
                return df
            
            nombres_plantilla = [p["JUGADOR"] for p in st.session_state.plantilla]
            
            def emparejar(nombre_excel):
                if pd.isna(nombre_excel): return None
                n_ex = str(nombre_excel).strip().lower()
                for n_app in nombres_plantilla:
                    if n_ex == n_app.lower(): return n_app
                for n_app in nombres_plantilla:
                    if n_ex in n_app.lower() or n_app.lower() in n_ex: return n_app
                matches = difflib.get_close_matches(n_ex, [n.lower() for n in nombres_plantilla], n=1, cutoff=0.7)
                if matches:
                    for n_app in nombres_plantilla:
                        if n_app.lower() == matches[0]: return n_app
                return None 
                
            df[col_jugador] = df[col_jugador].apply(emparejar)
            return df.dropna(subset=[col_jugador])

        c_up1, c_up2, c_up3 = st.columns(3)
        
        with c_up1:
            f_inicial = st.file_uploader("1. Valoración Inicial", type=["xlsx"], key="up_val_ini")
            if st.button("Procesar V. Inicial") and f_inicial:
                df = pd.read_excel(f_inicial)
                # Búsqueda dinámica de la columna nombre
                col_nombre = next((c for c in df.columns if str(c).upper() in ['JUGADOR', 'NOMBRE']), None)
                if col_nombre: df = sincronizar_nombres_df(df, col_nombre)
                
                # Serialización absoluta a JSON para evitar el crash de fechas y NaNs
                st.session_state.val_inicial = json.loads(df.to_json(orient='records', date_format='iso'))
                guardar_datos()
                st.success(f"✅ V. Inicial cargada.")
                st.rerun()
                
        with c_up2:
            f_rom = st.file_uploader("2. ROM y Fuerza ISO", type=["xlsx"], key="up_val_rom")
            if st.button("Procesar ROM/ISO") and f_rom:
                df = pd.read_excel(f_rom)
                col_nombre = next((c for c in df.columns if str(c).upper() in ['JUGADOR', 'NOMBRE']), None)
                if col_nombre: df = sincronizar_nombres_df(df, col_nombre)
                
                st.session_state.val_rom = json.loads(df.to_json(orient='records', date_format='iso'))
                guardar_datos()
                st.success(f"✅ ROM/Fuerza cargados.")
                st.rerun()
                
        with c_up3:
            f_1rm = st.file_uploader("3. Perfil 1RM (Carga/Vel)", type=["xlsx"], key="up_val_1rm")
            if st.button("Procesar 1RM") and f_1rm:
                df = pd.read_excel(f_1rm)
                col_nombre = next((c for c in df.columns if str(c).upper() in ['JUGADOR', 'NOMBRE']), None)
                if col_nombre: df = sincronizar_nombres_df(df, col_nombre)
                
                st.session_state.val_1rm = json.loads(df.to_json(orient='records', date_format='iso'))
                guardar_datos()
                st.success(f"✅ Datos 1RM cargados.")
                st.rerun()
                
        st.markdown("---")
        if st.button("🗑️ Borrar todas las valoraciones"):
            st.session_state.val_inicial, st.session_state.val_rom, st.session_state.val_1rm = [], [], []
            guardar_datos()
            st.success("Valoraciones borradas correctamente.")
            st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 1: RESUMEN
    # ---------------------------------------------------------
    with tab_val_res:
        st.markdown("### 1️⃣ Valoración Inicial (Tendencias del Equipo)")
        if not st.session_state.val_inicial:
            st.info("Sube el archivo de Valoración Inicial para ver el resumen.")
        else:
            c_vi1, c_vi2 = st.columns(2)
            with c_vi1:
                st.markdown("**🤕 Principales Molestias Habituales:**")
                for mol, count in procesar_textos(st.session_state.val_inicial, 'Molestias habituales'): st.write(f"- {mol} ({count} jugadores)")
                
                st.markdown("**🛡️ Aspectos Fuertes (Top 5):**")
                for af, count in procesar_textos(st.session_state.val_inicial, 'Aspectos fuertes'): st.write(f"- {af} ({count} jugadores)")
            with c_vi2:
                df_ini = pd.DataFrame(st.session_state.val_inicial)
                if 'Calidad del sueño' in df_ini.columns and 'Calidad de nutrición' in df_ini.columns:
                    sueno_m = pd.to_numeric(df_ini['Calidad del sueño'], errors='coerce').mean()
                    nutri_m = pd.to_numeric(df_ini['Calidad de nutrición'], errors='coerce').mean()
                    
                    s_str = f"{sueno_m:.1f}" if pd.notna(sueno_m) else "N/A"
                    n_str = f"{nutri_m:.1f}" if pd.notna(nutri_m) else "N/A"
                    
                    st.metric("Calidad de Sueño (Promedio / 5)", s_str)
                    st.metric("Calidad de Nutrición (Promedio / 5)", n_str)
                    
                st.markdown("**📈 Aspectos a Mejorar (Top 5):**")
                for am, count in procesar_textos(st.session_state.val_inicial, 'Aspectos a mejorar'): st.write(f"- {am} ({count} jugadores)")

        st.markdown("---")
        st.markdown("### 2️⃣ ROM y Fuerza Máxima Isométrica")
        if not st.session_state.val_rom:
            st.info("Sube el archivo de ROM y Fuerza ISO para ver el resumen.")
        else:
            df_rom = pd.DataFrame(st.session_state.val_rom)
            pares = [
                ('Rot. ext. cadera', 'Rot. ext. cadera D (°)', 'Rot. ext. cadera I (°)'),
                ('Rot. int. cadera', 'Rot. int. cadera D (°)', 'Rot. int. cadera I (°)'),
                ('Dorsiflexión', 'Dorsiflexión D (°)', 'Dorsiflexión I (°)'),
                ('Isquios', 'Isquios D (N)', 'Isquios I (N)'),
                ('Cuádriceps', 'Cuádriceps D (N)', 'Cuádriceps I (N)'),
                ('Aductores', 'Aductores D (N)', 'Aductores I (N)')
            ]
            orden_pruebas = {p[0]: i for i, p in enumerate(pares)}
            alertas_rom_data = []
            
            for idx, row in df_rom.iterrows():
                # Flexibilidad para la columna Jugador
                jug = row.get('JUGADOR', row.get('Jugador', row.get('NOMBRE', 'Desconocido')))
                for nombre, col_d, col_i in pares:
                    if col_d in df_rom.columns and col_i in df_rom.columns:
                        asimetria = calc_asimetria(row[col_d], row[col_i])
                        df_rom.at[idx, f'Asimetría {nombre} (%)'] = asimetria
                        if asimetria > 15:
                            alertas_rom_data.append({'prueba': nombre, 'jugador': jug, 'asimetria': asimetria, 'gravedad': 1, 'mensaje': f"🔴 **{jug}**: {asimetria:.1f}%"})
                        elif 10 <= asimetria <= 15:
                            alertas_rom_data.append({'prueba': nombre, 'jugador': jug, 'asimetria': asimetria, 'gravedad': 2, 'mensaje': f"🟡 **{jug}**: {asimetria:.1f}%"})

            alertas_rom_data.sort(key=lambda x: (orden_pruebas.get(x['prueba'], 99), x['gravedad'], -x['asimetria']))
            cols_mostrar = [c for c in ['JUGADOR', 'Jugador', 'NOMBRE'] if c in df_rom.columns]
            if cols_mostrar:
                cols_finales = [cols_mostrar[0]] + [f'Asimetría {n} (%)' for n, _, _ in pares if f'Asimetría {n} (%)' in df_rom.columns]
                mostrar_tabla_moderna(df_rom[cols_finales].style.hide(axis="index").format(precision=1))
            
            if alertas_rom_data:
                with st.expander("⚠️ Alertas de Asimetría Estructuradas", expanded=True):
                    pruebas_unicas = []
                    for a in alertas_rom_data:
                        if a['prueba'] not in pruebas_unicas: pruebas_unicas.append(a['prueba'])
                            
                    for idx_p, prueba in enumerate(pruebas_unicas):
                        if idx_p > 0: st.markdown("---")
                        st.markdown(f"##### 📌 {prueba}")
                        col_crit, col_cons = st.columns(2)
                        criticas = [a for a in alertas_rom_data if a['prueba'] == prueba and a['gravedad'] == 1]
                        considerar = [a for a in alertas_rom_data if a['prueba'] == prueba and a['gravedad'] == 2]
                        
                        with col_crit:
                            st.markdown("**🔴 Críticas (>15%)**")
                            if criticas:
                                for c in criticas: st.write(c['mensaje'])
                            else:
                                st.caption("✅ Ninguna")
                                
                        with col_cons:
                            st.markdown("**🟡 A considerar (10-15%)**")
                            if considerar:
                                for c in considerar: st.write(c['mensaje'])
                            else:
                                st.caption("✅ Ninguna")

        st.markdown("---")
        st.markdown("### 3️⃣ Perfil 1RM y Potencia")
        if not st.session_state.val_1rm:
            st.info("Sube el archivo de 1RM para ver el resumen.")
        else:
            df_1rm = pd.DataFrame(st.session_state.val_1rm)
            resultados_1rm = []
            for _, row in df_1rm.iterrows():
                cargas = [row.get(f'PESO{i}') for i in range(1, 5)]
                vels = [row.get(f'VELOCIDAD{i}') for i in range(1, 5)]
                rm_est = calcular_1rm(cargas, vels)
                pot_max = calcular_potencia_max(cargas, vels)
                
                # Búsqueda flexible de jugador
                jug = row.get('JUGADOR', row.get('Jugador', row.get('NOMBRE', 'Desconocido')))
                resultados_1rm.append({"Jugador": jug, "1RM Sentadilla (kg)": rm_est, "Potencia Máxima (W)": pot_max})
                
            df_res_1rm = pd.DataFrame(resultados_1rm)
            mostrar_tabla_moderna(df_res_1rm.style.hide(axis="index").format(precision=1))
            
            st.markdown("#### 🏋️‍♂️ Grupos de Fuerza (Márgenes de 10 kg)")
            bins = range(0, 300, 10)
            labels = [f"{i}-{i+9} kg" for i in bins[:-1]]
            df_res_1rm['Rango'] = pd.cut(df_res_1rm['1RM Sentadilla (kg)'], bins=bins, labels=labels, right=False)
            
            agrupado = df_res_1rm[df_res_1rm['1RM Sentadilla (kg)'] > 0].groupby('Rango', observed=True)['Jugador'].apply(list)
            for rango, jugs in agrupado.items():
                if jugs: st.write(f"**{rango}:** {', '.join(jugs)}")

    # ---------------------------------------------------------
    # PESTAÑA 2: JUGADORES (PERFIL INDIVIDUAL Y RECOMENDACIONES)
    # ---------------------------------------------------------
    with tab_val_jug:
        if not st.session_state.plantilla:
            st.info("Añade jugadores en la plantilla primero.")
        else:
            nombres_plantilla = sorted([j["JUGADOR"] for j in st.session_state.plantilla])
            jug_sel = st.selectbox("Selecciona un jugador:", nombres_plantilla, key="sel_val_jug")
            st.markdown("---")
            
            peso_jugador = 75.0 
            ant_jug = [a for a in st.session_state.get("antropometria", []) if limpiar_nombre(a['jugador']) == limpiar_nombre(jug_sel)]
            if ant_jug:
                df_aj = pd.DataFrame(ant_jug).sort_values('fecha', ascending=False)
                peso_jugador = float(df_aj.iloc[0]['Peso'])

            # 1. VALORACIÓN INICIAL INDIVIDUAL
            st.markdown("#### 1️⃣ Valoración Inicial")
            # Búsqueda dinámica para la columna que contenga el nombre
            v_ini = next((row for row in st.session_state.val_inicial if limpiar_nombre(row.get('JUGADOR', row.get('Jugador', row.get('NOMBRE', '')))) == limpiar_nombre(jug_sel)), None)
            calidad_sueno = 3
            if v_ini:
                calidad_sueno = safe_float(v_ini.get('Calidad del sueño', 3))
                c1, c2 = st.columns(2)
                
                # Seguro contra renderizados de la palabra "None"
                les_graves = v_ini.get('Lesiones graves')
                les_rec = v_ini.get('Lesiones recientes')
                mol = v_ini.get('Molestias habituales')
                asp_f = v_ini.get('Aspectos fuertes')
                asp_m = v_ini.get('Aspectos a mejorar')
                nutri = v_ini.get('Calidad de nutrición')
                
                c1.write(f"**Lesiones graves:** {les_graves if les_graves is not None else '-'}")
                c1.write(f"**Lesiones recientes:** {les_rec if les_rec is not None else '-'}")
                c1.write(f"**Molestias habituales:** {mol if mol is not None else '-'}")
                c2.write(f"**Aspectos fuertes:** {asp_f if asp_f is not None else '-'}")
                c2.write(f"**Aspectos a mejorar:** {asp_m if asp_m is not None else '-'}")
                c2.write(f"**Sueño (1-5):** {calidad_sueno} | **Nutrición (1-5):** {nutri if nutri is not None else '-'}")
            else:
                st.warning("No hay datos de valoración inicial para este jugador.")

            # 2. ROM Y FUERZA ISO INDIVIDUAL
            st.markdown("---")
            st.markdown("#### 2️⃣ ROM y Fuerza Máxima Isométrica")
            v_rom = next((row for row in st.session_state.val_rom if limpiar_nombre(row.get('JUGADOR', row.get('Jugador', row.get('NOMBRE', '')))) == limpiar_nombre(jug_sel)), None)
            alertas_asimetria_jugador = []
            
            if v_rom:
                datos_rom_ind = []
                for nombre, col_d, col_i in pares:
                    d, i = safe_float(v_rom.get(col_d, 0)), safe_float(v_rom.get(col_i, 0))
                    asim = calc_asimetria(d, i)
                    datos_rom_ind.append({"Prueba": nombre, "Derecha": d, "Izquierda": i, "Asimetría (%)": asim})
                    if asim > 15: alertas_asimetria_jugador.append((nombre, asim, "Crítica"))
                    elif 10 <= asim <= 15: alertas_asimetria_jugador.append((nombre, asim, "A considerar"))
                    
                df_rom_ind = pd.DataFrame(datos_rom_ind)
                def color_asim(val):
                    if val > 15: return 'color: red; font-weight: bold;'
                    elif val >= 10: return 'color: orange; font-weight: bold;'
                    return 'color: green;'
                mostrar_tabla_moderna(df_rom_ind.style.hide(axis="index").map(color_asim, subset=['Asimetría (%)']).format(precision=1))
            else:
                st.warning("No hay datos de ROM y Fuerza ISO para este jugador.")

            # 3. 1RM INDIVIDUAL
            st.markdown("---")
            st.markdown("#### 3️⃣ Perfil 1RM (Fuerza y Potencia)")
            v_1rm = next((row for row in st.session_state.val_1rm if limpiar_nombre(row.get('JUGADOR', row.get('Jugador', row.get('NOMBRE', '')))) == limpiar_nombre(jug_sel)), None)
            ratio_fuerza = 0.0
            
            if v_1rm:
                cargas = [safe_float(v_1rm.get(f'PESO{i}')) for i in range(1, 5)]
                vels = [safe_float(v_1rm.get(f'VELOCIDAD{i}')) for i in range(1, 5)]
                rm_sq = calcular_1rm(cargas, vels)
                pot_max = calcular_potencia_max(cargas, vels)
                ratio_fuerza = rm_sq / peso_jugador if peso_jugador > 0 else 0
                
                rm_pm, rm_ht = rm_sq * 1.15, rm_sq * 1.30
                
                c1, c2, c3 = st.columns(3)
                c1.metric("1RM Sentadilla", f"{rm_sq:.1f} kg", help="Estimado con VMP de 0.30 m/s")
                c2.metric("Potencia Máxima", f"{pot_max:.0f} W")
                c3.metric("Fuerza Relativa (1RM/Peso)", f"{ratio_fuerza:.2f}", help=f"Peso utilizado: {peso_jugador:.1f} kg")
                
                zonas_1rm = pd.DataFrame({
                    "Ejercicio": ["Sentadilla", "Peso Muerto (Extrapolado)", "Hip Thrust (Extrapolado)"],
                    "100% (1RM)": [rm_sq, rm_pm, rm_ht],
                    "90%": [rm_sq*0.9, rm_pm*0.9, rm_ht*0.9],
                    "80%": [rm_sq*0.8, rm_pm*0.8, rm_ht*0.8],
                    "70%": [rm_sq*0.7, rm_pm*0.7, rm_ht*0.7],
                    "60%": [rm_sq*0.6, rm_pm*0.6, rm_ht*0.6]
                })
                mostrar_tabla_moderna(zonas_1rm.style.hide(axis="index").format(precision=1))
            else:
                st.warning("No hay datos de 1RM para este jugador.")

            # ==========================================
            # RECOMENDACIONES AUTOMÁTICAS E INTELIGENCIA ARTIFICIAL
            # ==========================================
            st.markdown("---")
            st.markdown("### 🎯 Plan de Trabajo Personalizado")
            
            tiene_datos = v_ini or v_rom or v_1rm
            if not tiene_datos:
                st.info("Se necesitan cargar datos de las valoraciones para generar un plan.")
            else:
                criticas = [f"{a[0]} ({a[1]:.1f}%)" for a in alertas_asimetria_jugador if a[2] == "Crítica"]
                considerar = [f"{a[0]} ({a[1]:.1f}%)" for a in alertas_asimetria_jugador if a[2] == "A considerar"]
                
                criticas_txt = ", ".join(criticas) if criticas else "Ninguna"
                mod_txt = ", ".join(considerar) if considerar else "Ninguna"
                
                # Seguridad contra extracciones vacías para el prompt
                mol_crudas = v_ini.get('Molestias habituales') if v_ini else None
                molestias_txt = mol_crudas if mol_crudas is not None and str(mol_crudas).strip() != "" else 'Ninguna'
                
                if st.button("🤖 Generar Plan Estructurado con Gemini", use_container_width=True):
                    with st.spinner(f"Analizando perfil biomecánico y de fuerza de {jug_sel}..."):
                        try:
                            import google.generativeai as genai
                            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                            
                            prompt_directo = f"""
                            Eres un preparador físico de élite. Redacta UNICAMENTE un plan de entrenamiento individualizado y limpio para el jugador {jug_sel} siguiendo estrictamente este formato de 4 líneas y sin añadir ningún texto adicional ni explicaciones previas:

                            📋 **Diagnóstico Principal:** Desequilibrio neuromuscular severo en {criticas_txt} con déficit de fuerza relativa (Ratio actual: {ratio_fuerza:.2f}) y alerta por molestias en {molestias_txt}.
                            🛡️ **Fase Preventiva / Correctiva:** 
                            - Cadera: Movilidad dinámica 90/90 y trabajo corrector para las asimetrías críticas en {criticas_txt}.
                            - Zona Púbica/Aductores: Copenhagen Plank progresivo y estabilidad de core para manejo de {molestias_txt}.
                            - Isquios/Cuádriceps: Curl nórdico y sentadilla búlgara unilateral para equilibrar las diferencias detectadas en {criticas_txt} y {mod_txt}.
                            ⚡ **Fase de Rendimiento (Fuerza):** 
                            - Objetivo superar el Ratio >1.5 mediante bloque de fuerza máxima (Peso Muerto y Sentadilla).
                            - Priorizar cargas unilaterales en los patrones afectados para reducir asimetrías (>15%).
                            🛌 **Pautas Invisibles:** 
                            - Sueño: Optimizar descanso (actual: {calidad_sueno}/5) para favorecer la recuperación tisular y la regeneración de la zona afectada.
                            - Nutricion: Aporte proteico elevado y enfoque antiinflamatorio para el manejo de la sobrecarga.
                            """

                            modelos_validos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                            plan_generado = None
                            
                            for nombre_modelo in modelos_validos:
                                if "2.5-flash" in nombre_modelo: continue
                                try:
                                    model = genai.GenerativeModel(nombre_modelo)
                                    response = model.generate_content(prompt_directo)
                                    texto = response.text.strip()
                                    if "Diagnóstico Principal" in texto:
                                        if "📋" in texto: texto = texto[texto.find("📋"):]
                                        plan_generado = texto
                                        break
                                except Exception:
                                    continue
                            
                            if plan_generado:
                                st.success(f"¡Plan generado con éxito para {jug_sel}!")
                                st.markdown(plan_generado)
                            else:
                                st.error("No se ha podido conectar con el modelo. Revisa la clave API.")
                        except Exception as e:
                            st.error(f"Error general al conectar con la API: {e}")
