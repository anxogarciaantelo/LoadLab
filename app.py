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
from views.team_settings import render_panel_principal

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

        /* Barra lateral (Sidebar) con color dinámico */
        [data-testid="stSidebar"] {{
            background-color: {st.session_state.get("color_sidebar", "#f1f5f9")};
            color: #000000;
        }}
        
        /* Estilizar únicamente los títulos y textos de tus widgets de cuenta, 
           respetando la navegación nativa de Streamlit para las páginas */
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p {
            color: #000000 !important;
            font-weight: 800 !important;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(0, 0, 0, 0.2);
        }

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
                                validar_estructuras_memoria()
                                sincronizar_plantilla_sesiones()
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
                    
                    validar_estructuras_memoria()
                    sincronizar_plantilla_sesiones()
                    
                    st.success("Equipo creado.")
                    st.rerun()

    st.stop()
