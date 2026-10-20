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
st.set_page_config(page_title="LoadLab", page_icon="assets/logo_icono.png", layout="wide")

import plotly.io as pio
import plotly.graph_objects as go

pio.templates["loadlab_elite_dark"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#94a3b8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#3b82f6", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#0ea5e9"],
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="rgba(15, 23, 42, 0.95)",
            font_size=12,
            font_family="Plus Jakarta Sans, sans-serif",
            bordercolor="#334155"
        ),
        xaxis=dict(
            gridcolor="#1e293b",
            gridwidth=1,
            griddash="dot",
            zerolinecolor="#334155",
            zerolinewidth=2,
            showline=False,
            title=dict(font=dict(size=12, color="#e2e8f0")),
            tickfont=dict(size=10, color="#94a3b8")
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            gridwidth=1,
            griddash="dot",
            zerolinecolor="#334155",
            zerolinewidth=2,
            showline=False,
            title=dict(font=dict(size=12, color="#e2e8f0")),
            tickfont=dict(size=10, color="#94a3b8")
        ),
        title=dict(
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#f8fafc", size=15),
            pad=dict(b=15)
        ),
        legend=dict(
            font=dict(size=11, color="#cbd5e1"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)"
        ),
        margin=dict(l=40, r=20, t=50, b=30)
    )
)
pio.templates.default = "loadlab_elite_dark"

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
# 0. CONTROL DE VISIBILIDAD DEL MENÚ LATERAL
# ==========================================
# Si el usuario no ha seleccionado un equipo, ocultamos el menú lateral con CSS
if not st.session_state.get("equipo_seleccionado", False):
    st.markdown("""
        <style>
            /* Ocultar el contenedor de la barra lateral */
            [data-testid="stSidebar"] {
                display: none !important;
            }
            /* Ocultar el botón/flecha superior izquierda que despliega la barra */
            [data-testid="collapsedControl"] {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 1. PANTALLA DE LOGIN / REGISTRO (DISEÑO SPLIT ÉLITE)
# ==========================================
if not st.session_state.autenticado:
    set_login_background()
    
    st.markdown("<div style='margin-top: 2vh;'></div>", unsafe_allow_html=True)
    col_info, col_espacio, col_login = st.columns([1.4, 0.2, 1.1])
    
    with col_info:
        import base64
        import os
        
        # Ruta exacta donde el sistema buscará tu logo
        ruta_logo = os.path.join("assets", "logo_completo.png")
        
        try:
            with open(ruta_logo, "rb") as image_file:
                logo_b64 = base64.b64encode(image_file.read()).decode()
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 140px; margin-bottom: 20px;">'
        except FileNotFoundError:
            # Si la ruta falla, te mostrará este error en pantalla para que sepas dónde poner la imagen
            logo_html = f'<div style="color: #ef4444; border: 1px solid #ef4444; padding: 10px; border-radius: 5px; margin-bottom: 20px;">⚠️ FALTA EL LOGO: Crea una carpeta llamada "assets" y guarda ahí la imagen como "logo_completo.png"</div>'

        html_info = f"""<div style="padding-right: 20px;">
{logo_html}
<h2 style='color: #E2E8F0; font-weight: 900; font-size: 2.8rem; letter-spacing: -1.5px; margin-bottom: 5px; font-family: "Plus Jakarta Sans", sans-serif;'>
LOAD<span style='color: #C5A059;'>LAB</span>
</h2>
<h1 style="font-size: 2.2rem; font-weight: 800; line-height: 1.2; margin-bottom: 20px; color: #E2E8F0; letter-spacing: -0.5px;">
Decisiones basadas en datos,<br><span style="color: #C5A059;">rendimiento de élite.</span>
</h1>
<p style="color: #a1a1aa; font-size: 1.05rem; margin-bottom: 30px; max-width: 95%; line-height: 1.6;">
Centraliza y analiza las variables de rendimiento, carga y salud de tus futbolistas en un único ecosistema premium diseñado para cuerpos técnicos profesionales.
</p>

<!-- Sección de Características Científicas de LoadLab -->
<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 16px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 10px; border-radius: 8px; color: #C5A059; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex-shrink: 0;">📉</div>
<div>
<h4 style="margin: 0 0 3px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Carga y Demandas (EWMA / ACWR)</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">Monitoriza el Ratio A/C (Sweet Spot), el strain acumulado y la densidad competitiva por jugador para mitigar el riesgo.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 16px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 10px; border-radius: 8px; color: #C5A059; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex-shrink: 0;">🧠</div>
<div>
<h4 style="margin: 0 0 3px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Oráculo Predictivo AI</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">Algoritmos avanzados (XGBoost) para detectar y anticipar riesgo de lesión inminente en la plantilla.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 16px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 10px; border-radius: 8px; color: #C5A059; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex-shrink: 0;">🏋️‍♂️</div>
<div>
<h4 style="margin: 0 0 3px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Rendimiento & Fuerza VBT</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">Seguimiento neuromuscular, perfiles Fuerza-Velocidad, test de salto (CMJ) y asimetrías bilaterales.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 16px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: flex-start; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 10px; border-radius: 8px; color: #C5A059; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex-shrink: 0;">🚑</div>
<div>
<h4 style="margin: 0 0 3px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Enfermería, RTP & Antropometría</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.4;">Control de bajas, fases de readaptación (Return to Play) y composición corporal de élite.</p>
</div>
</div>
</div>"""
        # ESTA ES LA LÍNEA CRÍTICA QUE SE PERDIÓ Y CAUSABA EL FALLO VISUAL:
        st.markdown(html_info, unsafe_allow_html=True)

    with col_login:
        st.markdown("<div style='margin-top: 1vh;'></div>", unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["INICIAR SESIÓN", "REGISTRARSE"])
        
        with tab_login:
            st.markdown("<h3 style='color: #f8fafc; font-weight: 800; font-size: 1.6rem; margin-bottom: 5px; margin-top: 10px;'>Bienvenido de nuevo</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 25px;'>Accede a tu cuenta para continuar.</p>", unsafe_allow_html=True)
            
            with st.form(key="login_form"):
                email = st.text_input("Correo electrónico", key="log_email", placeholder="tu@email.com")
                password = st.text_input("Contraseña", type="password", key="log_pass", placeholder="••••••••")
                st.markdown("<div style='text-align: right; margin-bottom: 15px;'><a href='#' style='color: #C5A059; font-size: 0.8rem; text-decoration: none; font-weight: 600;'>¿Has olvidado tu contraseña?</a></div>", unsafe_allow_html=True)
                
                submit_btn = st.form_submit_button("Iniciar Sesión", use_container_width=True)
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
                        
        with tab_reg:
            st.markdown("<h3 style='color: #f8fafc; font-weight: 800; font-size: 1.6rem; margin-bottom: 5px; margin-top: 10px;'>Crear cuenta</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 20px;'>Únete a la plataforma de alto rendimiento.</p>", unsafe_allow_html=True)
            
            with st.form(key="register_form"):
                reg_email = st.text_input("Correo electrónico", key="reg_email", placeholder="tu@email.com")
                reg_password = st.text_input("Contraseña", type="password", key="reg_pass", placeholder="Mínimo 6 caracteres")
                
                st.markdown("""
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 10px; margin-bottom: 15px; line-height: 1.5; background-color: rgba(15, 23, 42, 0.5); padding: 12px; border-radius: 6px; border-left: 3px solid #C5A059;">
                        🔒 <strong>Aviso RGPD:</strong> Eres el <strong>Responsable del Tratamiento</strong> de los datos. Usa alias si no tienes consentimiento explícito.
                    </div>
                """, unsafe_allow_html=True)

                acepta_privacidad = st.checkbox("Acepto los términos y el aviso de privacidad", key="check_privacidad")
                submit_reg = st.form_submit_button("Registrarse", use_container_width=True)
                
                if submit_reg:
                    if not acepta_privacidad:
                        st.warning("Debes aceptar el aviso de privacidad para registrarte.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                            if res.user:
                                supabase.table("usuarios").insert({"id": res.user.id, "email": reg_email}).execute()
                            st.success("¡Cuenta creada con éxito! Inicia sesión para continuar.")
                        except Exception as e:
                            st.error(f"Error al registrarse: {e}")
    st.stop()
    
# ==========================================
# 2. SELECCIÓN DE EQUIPO
# ==========================================
if st.session_state.autenticado and not st.session_state.equipo_seleccionado:
    # 1. Aplicamos el fondo dinámico de datos (sin imagen local)
    css_fondo_equipos = """
    <style>
    .stApp {
        background-color: #0b1120 !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08), transparent 25%),
            radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.05), transparent 25%);
        animation: bgShift 15s ease-in-out infinite alternate;
    }
    .stApp::before {
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 40px 40px; pointer-events: none; z-index: 0;
    }
    @keyframes bgShift { 0% { background-position: 0% 0%; } 100% { background-position: 100% 100%; } }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    
    /* Botones de acceder a los equipos */
    div[data-testid="column"] button {
        background-color: #3b82f6 !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4) !important;
    }
    div[data-testid="column"] button:hover {
        background-color: #2563eb !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(59, 130, 246, 0.6) !important;
    }
    
    /* Fondo cristal para el desplegable de Crear Equipo */
    div[data-testid="stExpander"] details {
        background-color: rgba(30, 41, 59, 0.95) !important;
        border-radius: 12px !important;
        border: 1px solid #334155 !important;
        border-top: 4px solid #3b82f6 !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8) !important;
    }
    div[data-testid="stExpander"] summary p {
        color: #f8fafc !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Inputs dentro de crear equipo */
    div[data-testid="stExpander"] div[data-testid="stTextInput"] input,
    div[data-testid="stExpander"] div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #f4f4f5 !important;
        border: 1px solid #d4d4d8 !important;
        border-radius: 6px !important;
        color: #0a0a0a !important;
        font-weight: 600 !important;
    }
    </style>
    """
    st.markdown(css_fondo_equipos, unsafe_allow_html=True)

    # Un poco de espacio superior y título rediseñado
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 40px; font-size: 2.5rem; letter-spacing: -1px; text-shadow: 0px 4px 15px rgba(0,0,0,0.8);'>SELECCIONA TU <span style='color: #3b82f6;'>EQUIPO</span></h2>", unsafe_allow_html=True)
    
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
                        escudo = eq_info.get("escudo_base64")
                        if escudo:
                            img_src = escudo if str(escudo).startswith("http") else f"data:image/jpeg;base64,{escudo}"
                            img_html = f'<img src="{img_src}" style="width:90px; height:90px; object-fit: cover; border-radius:50%; margin-bottom: 15px; box-shadow: 0 6px 12px rgba(0,0,0,0.15); border: 2px solid #e4e4e7;">'
                        else:
                            img_html = '<div style="font-size: 50px; margin-bottom: 15px;">🛡️</div>'
                            
                        nombre = eq_info.get('nombre', 'Equipo')
                        division = eq_info.get('division') or "Sin división"
                        categoria = eq_info.get('categoria') or ""
                        
                        tarjeta_html = f"""
                        <div style="background-color: rgba(30, 41, 59, 0.85); padding: 30px 20px 20px 20px; border-radius: 12px; border: 1px solid #334155; border-top: 4px solid #3b82f6; box-shadow: 0 20px 40px rgba(0,0,0,0.6); text-align: center; margin-bottom: 15px; backdrop-filter: blur(10px);">
                            {img_html}
                            <h3 style="color: #f8fafc; font-weight: 800; margin-bottom: 5px; font-size: 1.3rem; text-transform: uppercase; letter-spacing: -0.5px;">{nombre}</h3>
                            <p style="color: #94a3b8; font-size: 0.85rem; font-weight: 700; margin-top: 0px; text-transform: uppercase; letter-spacing: 0.5px;">{categoria} | {division}</p>
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
    
    # 4. BOTÓN "CREAR NUEVO EQUIPO" CENTRADO
    col_exp_izq, col_exp_cen, col_exp_der = st.columns([2, 1.5, 2])
    
    with col_exp_cen:
        with st.expander("➕ CREAR NUEVO EQUIPO"):
            with st.form("form_nuevo_equipo"):
                n_nombre = st.text_input("Nombre del Club / Equipo:")
                n_categoria = st.selectbox("Categoría:", ["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"])
                n_division = st.text_input("División / Liga:")
                n_temporada = st.text_input("Temporada:", value="2026/2027")
                
                # Inyectar CSS solo para el botón de este formulario específico (Rojo)
                st.markdown("""
                    <style>
                    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
                        background-color: #dc2626 !important;
                        color: #ffffff !important;
                        border: none !important;
                        font-weight: 800 !important;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        box-shadow: 0 4px 6px rgba(220, 38, 38, 0.3) !important;
                    }
                    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
                        background-color: #b91c1c !important;
                        transform: translateY(-2px);
                    }
                    </style>
                """, unsafe_allow_html=True)
                
                c_btn1, c_btn2, c_btn3 = st.columns([1, 1.5, 1])
                with c_btn2:
                    btn_crear = st.form_submit_button("🚀 CREAR Y ACCEDER", use_container_width=True)
                
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

# ==========================================
# 4. PANTALLA PRINCIPAL (CUANDO EL EQUIPO ESTÁ SELECCIONADO)
# ==========================================

aplicar_color_sidebar()

if st.session_state.get("equipo_seleccionado", False):
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 1. PREPARAR EL ESCUDO ---
    escudo = st.session_state.get("escudo_equipo")
    if escudo:
        img_src = escudo if str(escudo).startswith("http") else f"data:image/jpeg;base64,{escudo}"
        img_html = f'<img src="{img_src}" style="width:140px; height:140px; object-fit: cover; border-radius:50%; margin-bottom: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">'
    else:
        img_html = '<div style="font-size: 70px; margin-bottom: 15px;">🛡️</div>'

    # ==========================================
    # 🚨 TORRE DE CONTROL (DASHBOARD DIARIO)
    # ==========================================
    st.markdown("### 📊 Información Diaria")

    hoy_dt = date.today()
    hoy_str = str(hoy_dt)
    
    # Cálculos de fechas de la semana actual (Lunes a Domingo)
    lunes = hoy_dt - timedelta(days=hoy_dt.weekday())
    domingo = lunes + timedelta(days=6)
    dias_semana = [lunes + timedelta(days=i) for i in range(7)]
    nombres_dias = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]

    # --- ASIGNACIÓN DE NUMERACIÓN DINÁMICA A SESIONES ---
    sesiones_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
    c_ent, c_ofi, c_ami = 0, 0, 0
    for s_item in sesiones_crono:
        t = s_item.get("tipo", "")
        if t == "Entrenamiento":
            c_ent += 1
            s_item["num_rel"] = c_ent
        elif t == "Partido Oficial":
            c_ofi += 1
            s_item["num_rel"] = c_ofi
        elif t == "Partido Amistoso":
            c_ami += 1
            s_item["num_rel"] = c_ami

    # --- 1. CALENDARIO MICROCICLO ACTUAL ---
    html_cal = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; text-align: center; margin-bottom: 20px;'>"
    for i, d in enumerate(dias_semana):
        d_str = str(d)
        es_hoy = "border: 2px solid #3b82f6;" if d_str == hoy_str else "border: 1px solid #334155;"
        bg_color = "#0f172a" if d_str == hoy_str else "#1e293b"
        
        sesiones_dia = [s for s in st.session_state.sesiones if s["fecha"] == d_str]
        contenido_extra = ""
        for s in sesiones_dia:
            tipo = s.get("tipo", "")
            num_rel = s.get("num_rel", "X")
            
            if tipo == "Entrenamiento":
                sub = s.get('descripcion', 'TD')
                texto_badge = f"S{num_rel} - {sub}"
                color_badge = "#10b981"
            elif tipo == "Partido Oficial":
                sub = s.get('rival', 'Rival')
                texto_badge = f"J{num_rel} vs {sub}"
                color_badge = "#dc2626"
            else:
                sub = s.get('rival', 'Rival')
                texto_badge = f"A{num_rel} vs {sub}"
                color_badge = "#dc2626"
            
            contenido_extra += f"<div style='background-color: {color_badge}; color: white; font-size: 0.75rem; font-weight: 800; padding: 4px 6px; border-radius: 4px; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.2);' title='{texto_badge}'>{texto_badge}</div>"
            
        html_cal += f"<div style='background-color: {bg_color}; {es_hoy} padding: 10px 5px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.15);'><span style='color: #94a3b8; font-size: 0.8rem; font-weight: 800; text-transform: uppercase;'>{nombres_dias[i]}</span><span style='color: #f8fafc; font-weight: 800; font-size: 1.15rem; margin-bottom: 2px;'>{d.day}</span>{contenido_extra}</div>"
    html_cal += "</div>"
    st.markdown(html_cal, unsafe_allow_html=True)

    # --- 2. CABECERA DE CONTEXTO Y ALERTAS ---
    # 2.1 Variables de Contexto
    sesiones_partido = sorted([s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")], key=lambda x: x["fecha"])
    proximo_partido = next((s for s in sesiones_partido if s["fecha"] >= hoy_str), None)
    
    md_text = "SIN PARTIDO"
    rival_text = "N/A"
    fecha_partido_text = ""
    
    if proximo_partido:
        fecha_p_dt = datetime.strptime(proximo_partido["fecha"], "%Y-%m-%d").date()
        dias_diff = (fecha_p_dt - hoy_dt).days
        rival_text = proximo_partido.get('rival', 'Rival Desconocido')
        fecha_partido_text = fecha_p_dt.strftime("%d/%m/%Y")
        
        if dias_diff == 0: md_text = "🚨 MATCH DAY"
        elif dias_diff == 1: md_text = "⚡ MD - 1"
        elif dias_diff == 2: md_text = "🔥 MD - 2"
        elif dias_diff == 3: md_text = "🏃‍♂️ MD - 3"
        elif dias_diff == 4: md_text = "🧠 MD - 4"
        else: md_text = f"📅 MD - {dias_diff}"

    from utils.math_helpers import obtener_clima
    ciudad_club = st.session_state.get("ubicacion_local", "Santiago de Compostela")
    clima_hoy = obtener_clima(ciudad_club, hoy_str)
    clima_str = f"{clima_hoy['temp']}°C | {clima_hoy['estado']}" if clima_hoy else "Desconocido"

    # 2.2 Motor de Alertas
    bajas_medicas = []
    readaptacion = []
    alertas_readiness = []
    alertas_carga = []

    for l in st.session_state.lesiones:
        if l.get("estado") == "Activa":
            dias_lesionado = (hoy_dt - datetime.strptime(l["id_sesion"], "%Y-%m-%d").date()).days
            bajas_medicas.append({"jug": l["jugador"], "txt": f"{l['tipo']} ({dias_lesionado}d)"})
        elif l.get("estado") == "Recuperado" and l.get("dias_baja"):
            fecha_alta = datetime.strptime(l["id_sesion"], "%Y-%m-%d").date() + timedelta(days=int(l["dias_baja"]))
            if 0 <= (hoy_dt - fecha_alta).days <= 7:
                readaptacion.append({"jug": l["jugador"], "txt": "Alta reciente (RTP)"})

    df_master = st.session_state.get("df_master_informes", pd.DataFrame())
    dict_zscore = calcular_zscore_wellness(df_master, hoy_str)
    
    sesiones_con_datos = [s for s in st.session_state.sesiones if s.get("informe_generado") and s["fecha"] <= hoy_str]
    if sesiones_con_datos:
        ult_sesion = sorted(sesiones_con_datos, key=lambda x: x["fecha"])[-1]
        for d in ult_sesion.get("datos_informe", []):
            jug = d["JUGADOR"]
            if jug in [b["jug"] for b in bajas_medicas]: continue
            tqr = safe_float(d.get("TQR", 0))
            well = safe_float(d.get("WELLNESS", 0))
            
            if 0 < tqr <= 3: alertas_readiness.append({"jug": jug, "txt": f"TQR {tqr:.0f}", "lvl": "rojo"})
            elif tqr == 4: alertas_readiness.append({"jug": jug, "txt": f"TQR {tqr:.0f}", "lvl": "amarillo"})
            
            if well > 0:
                st_j = dict_zscore.get(jug, {'media': 0, 'std': 1.0})
                if st_j['media'] > 0:
                    z_score = (well - st_j['media']) / st_j['std']
                    if z_score >= 1.5: 
                        alertas_readiness.append({"jug": jug, "txt": f"Fatiga Anormal (Z: +{z_score:.1f})", "lvl": "rojo"})
                    elif 1.0 <= z_score < 1.5: 
                        alertas_readiness.append({"jug": jug, "txt": f"Alerta Fatiga (Z: +{z_score:.1f})", "lvl": "amarillo"})
                else:
                    # Fallback de seguridad para jugadores sin histórico previo
                    if well >= 24: alertas_readiness.append({"jug": jug, "txt": f"Fatiga {well:.0f}", "lvl": "rojo"})
                    elif 18 <= well < 24: alertas_readiness.append({"jug": jug, "txt": f"Fatiga {well:.0f}", "lvl": "amarillo"})

    ewma_hoy = calcular_ewma_historico(st.session_state.sesiones, hoy_str)
    df_master = st.session_state.get("df_master_informes", pd.DataFrame())
    hsr_dict = {}
    if not df_master.empty and 'DIS AI' in df_master.columns:
        df_7d = df_master[(df_master['FECHA'] <= hoy_str) & (df_master['FECHA'] > str(hoy_dt - timedelta(days=7)))]
        if not df_7d.empty:
            hsr_dict = df_7d.groupby('JUGADOR')['DIS AI'].sum().to_dict()

    for jug, vals in ewma_hoy.items():
        if jug in [b["jug"] for b in bajas_medicas]: continue
        
        ratio_int = vals.get("RATIO A/C", 0)
        aguda_int = vals.get("EWMA AGUDA", 0)
        ratio_hsr = vals.get("RATIO A/C HSR", 0)
        aguda_hsr = vals.get("EWMA AGUDA HSR", 0)
        ratio_acc = vals.get("RATIO A/C ACC", 0)
        
        # Riesgo Interno
        if aguda_int > 800:
            if ratio_int >= 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C Carga: {ratio_int:.2f}", "lvl": "rojo"})
            elif 1.35 <= ratio_int < 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C Carga: {ratio_int:.2f}", "lvl": "amarillo"})
            elif ratio_int < 0.8: alertas_carga.append({"jug": jug, "txt": f"A/C Carga: {ratio_int:.2f}", "lvl": "amarillo"})
            
        # Riesgo Mecánico Tisular (Isquiosural)
        if aguda_hsr > 400:
            if ratio_hsr >= 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C HSR: {ratio_hsr:.2f}", "lvl": "rojo"})
            elif 1.35 <= ratio_hsr < 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C HSR: {ratio_hsr:.2f}", "lvl": "amarillo"})
            
        # Riesgo Mecánico Periférico (Articular/Cadera)
        if ratio_acc >= 1.5:
             alertas_carga.append({"jug": jug, "txt": f"A/C ACC: {ratio_acc:.2f}", "lvl": "rojo"})

    def dedup_alertas(lista):
        vistos = {}
        for item in lista:
            if item["jug"] not in vistos: vistos[item["jug"]] = item
            else:
                if item["lvl"] == "rojo" and vistos[item["jug"]]["lvl"] == "amarillo":
                    vistos[item["jug"]] = item
                elif item["lvl"] == vistos[item["jug"]]["lvl"]:
                    vistos[item["jug"]]["txt"] += f" | {item['txt']}"
        return list(vistos.values())
        
    alertas_readiness = dedup_alertas(alertas_readiness)
    alertas_carga = dedup_alertas(alertas_carga)
    alertas_medicas = [{"jug": b["jug"], "txt": b["txt"], "lvl": "rojo"} for b in bajas_medicas] + [{"jug": r["jug"], "txt": r["txt"], "lvl": "verde"} for r in readaptacion]

    def get_avatar_html(jugador_nombre):
        for p in st.session_state.get("plantilla", []):
            if limpiar_nombre(p["JUGADOR"]) == limpiar_nombre(jugador_nombre):
                if p.get("foto"):
                    img_src = p["foto"] if str(p["foto"]).startswith("http") else f"data:image/jpeg;base64,{p['foto']}"
                    return f"<img src='{img_src}' style='width:20px; height:20px; border-radius:50%; object-fit: cover; margin-right: 6px; border: 1px solid #334155;'>"
                break
        return "<span style='font-size: 16px; margin-right: 6px;'>👤</span>"

    def render_alertas_grid(alertas, nivel_predeterminado="verde"):
        if not alertas:
            return "<div style='color: #10b981; font-weight: 800; font-size: 0.8rem; padding: 10px; text-align: center; margin-top: 20px;'>✅ En parámetros</div>"
        
        orden_niveles = {"rojo": 0, "amarillo": 1, "verde": 2}
        alertas_ordenadas = sorted(alertas, key=lambda x: orden_niveles.get(x.get("lvl", nivel_predeterminado), 3))
        
        html = "<style>.alerta-scroll::-webkit-scrollbar { width: 4px; } .alerta-scroll::-webkit-scrollbar-track { background: transparent; } .alerta-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }</style>"
        html += "<div class='alerta-scroll' style='display: grid; grid-template-columns: 1fr 1fr; gap: 6px; max-height: 140px; overflow-y: auto; padding-right: 4px;'>"
        
        for a in alertas_ordenadas:
            nivel = a.get("lvl", nivel_predeterminado)
            color = "#ef4444" if nivel == "rojo" else ("#f59e0b" if nivel == "amarillo" else "#10b981")
            bg = "rgba(239, 68, 68, 0.1)" if nivel == "rojo" else ("rgba(245, 158, 11, 0.1)" if nivel == "amarillo" else "rgba(16, 185, 129, 0.1)")
            avatar = get_avatar_html(a["jug"])
            
            html += f"<div style='background: {bg}; border: 1px solid {color}40; border-left: 3px solid {color}; padding: 6px; border-radius: 6px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'><div style='display: flex; align-items: center; margin-bottom: 3px;'>{avatar}<span style='color: #f8fafc; font-size: 0.75rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{a['jug']}'>{a['jug']}</span></div><span style='color: {color}; font-size: 0.7rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;' title='{a['txt']}'>{a['txt']}</span></div>"
            
        html += "</div>"
        return html

    c_ctx, c_read, c_carga, c_med = st.columns([1.2, 1.5, 1.5, 1.5])

    with c_ctx:
        html_ctx = f"""
<div style="background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid #334155; border-top: 4px solid #3b82f6; border-radius: 8px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); height: 100%; display: flex; flex-direction: column; justify-content: center; text-align: center;">
<h2 style="color: #f8fafc; font-size: 1.5rem; font-weight: 800; margin: 0 0 10px 0;">{md_text}</h2>
<div style="color: #f8fafc; font-size: 1.1rem; font-weight: 800; margin-bottom: 2px;">🆚 {rival_text}</div>
<div style="color: #94a3b8; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px;">{fecha_partido_text}</div>
<div style="color: #3b82f6; font-size: 0.8rem; font-weight: 800; margin-top: auto; padding-top: 10px; border-top: 1px solid #334155;">📍 {ciudad_club} | {clima_str}</div>
</div>
"""
        st.markdown(html_ctx, unsafe_allow_html=True)

    with c_read:
        html_read = f"""
<div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #f59e0b; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;">🧠 Readiness & Bienestar</p>
{render_alertas_grid(alertas_readiness)}
</div>
"""
        st.markdown(html_read, unsafe_allow_html=True)

    with c_carga:
        html_carga = f"""
<div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #ef4444; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;">🔥 Riesgo de Carga</p>
{render_alertas_grid(alertas_carga)}
</div>
"""
        st.markdown(html_carga, unsafe_allow_html=True)

    with c_med:
        html_med = f"""
<div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #8b5cf6; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;">🚑 Enfermería & RTP</p>
{render_alertas_grid(alertas_medicas)}
</div>
"""
        st.markdown(html_med, unsafe_allow_html=True)

    st.markdown("---")

    # --- 3. GRÁFICOS DE EVOLUCIÓN DEL MICROCICLO ---
    if not df_master.empty:
        df_sem = df_master[(df_master['FECHA'] >= str(lunes)) & (df_master['FECHA'] <= str(domingo))].copy()
        
        if not df_sem.empty:
            df_sem['TQR'] = df_sem['TQR'].replace(0, np.nan)
            df_sem['WELLNESS'] = df_sem['WELLNESS'].replace(0, np.nan)
            
            df_diario_int = df_sem.groupby('FECHA')[['WELLNESS', 'TQR', 'CARGA']].mean().reset_index()
            
            df_sem_gps = df_sem[df_sem['DIS'] > 0]
            if not df_sem_gps.empty:
                df_diario_ext = df_sem_gps.groupby('FECHA')[['DIS', 'DIS AI']].mean().reset_index()
            else:
                df_diario_ext = pd.DataFrame(columns=['FECHA', 'DIS', 'DIS AI'])
                
            df_diario = pd.merge(df_diario_int, df_diario_ext, on='FECHA', how='left').fillna(0)
            
            df_diario['DIA_NOMBRE'] = pd.to_datetime(df_diario['FECHA']).dt.weekday.map({
                0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
            })
            
            cg1, cg2, cg3 = st.columns(3)
            
            with cg1:
                fig_w = go.Figure()
                fig_w.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario['WELLNESS'], name="Fatiga (Wellness)", marker_color="rgba(239, 68, 68, 0.7)", yaxis="y1"))
                fig_w.add_trace(go.Scatter(x=df_diario['DIA_NOMBRE'], y=df_diario['TQR'], name="TQR", mode="lines+markers", line=dict(color="#10b981", width=3), yaxis="y2"))
                fig_w.update_layout(title="🧠 Bienestar", yaxis=dict(title="Puntos Wellness", range=[0, 35]), yaxis2=dict(title="TQR", overlaying="y", side="right", range=[0, 10]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_w, use_container_width=True)
                
            with cg2:
                fig_c = go.Figure()
                fig_c.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario['CARGA'], name="Carga (UA)", marker_color="#3b82f6"))
                fig_c.update_layout(title="🔥 Carga Interna Acumulada", yaxis_title="UA", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_c, use_container_width=True)
                
            with cg3:
                fig_ext = go.Figure()
                if 'DIS' in df_diario.columns:
                    fig_ext.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario['DIS'], name="Distancia (km)", marker_color="rgba(59, 130, 246, 0.6)", yaxis="y1"))
                    fig_ext.add_trace(go.Scatter(x=df_diario['DIA_NOMBRE'], y=df_diario['DIS AI'], name="HSR (m)", mode="lines+markers", line=dict(color="#f59e0b", width=3), yaxis="y2"))
                fig_ext.update_layout(title="🏃‍♂️ Carga Externa", yaxis=dict(title="km"), yaxis2=dict(title="HSR (m)", overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_ext, use_container_width=True)
        else:
            st.info("Aún no hay datos de sesión procesados para la semana actual.")
    else:
        st.info("No hay datos cargados en la base de datos de rendimiento para procesar gráficas.")
    
    # --- BOTÓN DE CONFIGURACIÓN ESTRECHO A LA DERECHA ---
    c_vacio, c_btn = st.columns([6, 1])
    with c_btn:
        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state.mostrar_configuracion = not st.session_state.get("mostrar_configuracion", False)

    if st.session_state.get("mostrar_configuracion", False):
        render_panel_principal()
