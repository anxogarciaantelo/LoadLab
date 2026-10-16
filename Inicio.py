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
# SUSTITUYE POR:
st.set_page_config(page_title="My Performance AMS", page_icon="⚽", layout="wide")

import plotly.io as pio
import plotly.graph_objects as go

pio.templates["loadlab_elite_dark"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#94a3b8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#3b82f6", "#10b981", "#8b5cf6", "#ef4444", "#f59e0b", "#0ea5e9"],
        xaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#334155",
            title=dict(font=dict(weight="bold", color="#e2e8f0")),
            tickfont=dict(color="#94a3b8")
        ),
        yaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#334155",
            title=dict(font=dict(weight="bold", color="#e2e8f0")),
            tickfont=dict(color="#94a3b8")
        ),
        title=dict(font=dict(color="#f8fafc", size=16, weight="bold")),
        legend=dict(font=dict(color="#e2e8f0"))
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
# 1. PANTALLA DE LOGIN / REGISTRO
# ==========================================
if not st.session_state.autenticado:
    set_login_background("fondo_login.jpg")
    
    # Reducimos los saltos de línea para que quede bien centrado en pantalla
    st.markdown("<br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    
    col_izq, col_centro, col_der = st.columns([1.2, 1, 1.2])
    
    with col_centro:
        tab_login, tab_reg = st.tabs(["INICIAR SESIÓN", "NUEVA CUENTA"])
        
        with tab_login:
            # Título de Marca Profesional
            st.markdown("<h2 style='text-align: center; color: #0a0a0a; font-weight: 800; margin-bottom: 25px; font-size: 2.2rem; letter-spacing: -1px;'>LOAD<span style='color: #dc2626;'>LAB</span></h2>", unsafe_allow_html=True)
            
            with st.form(key="login_form"):
                email = st.text_input("Correo electrónico", key="log_email")
                password = st.text_input("Contraseña", type="password", key="log_pass")
                submit_btn = st.form_submit_button("Entrar al Sistema", use_container_width=True)
                
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
            st.markdown("<h2 style='text-align: center; color: #0a0a0a; font-weight: 800; margin-bottom: 20px; font-size: 1.5rem;'>CREAR CUENTA</h2>", unsafe_allow_html=True)
            with st.form(key="register_form"):
                reg_email = st.text_input("Correo electrónico", key="reg_email")
                reg_password = st.text_input("Contraseña (mín. 6 caracteres)", type="password", key="reg_pass")
                
                # Aviso rediseñado al estilo Carbón
                st.markdown("""
                    <div style="font-size: 0.75rem; color: #475569; margin-bottom: 15px; line-height: 1.5; background-color: #f4f4f5; padding: 12px; border-radius: 6px; border-left: 3px solid #1c1c1e;">
                        🔒 <strong>Aviso de Privacidad (RGPD):</strong><br>
                        Al registrarte asumes la figura de <strong>Responsable del Tratamiento</strong> de los datos.<br>
                        ⚠️ <strong>Recomendación:</strong> Utiliza alias o iniciales para los deportistas a menos que cuentes con su consentimiento explícito.
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander("📄 Leer Términos y Condiciones"):
                    st.markdown("""
                        <small>
                        **1. Responsabilidad de los Datos:** El usuario es el único responsable de la legalidad de los datos. LoadLab actúa como Encargado de Tratamiento.<br>
                        **2. Uso de la Plataforma:** LoadLab no cederá ni explotará estos datos con terceros.<br>
                        **3. Fase Beta:** Se recomienda exportar y mantener copias de seguridad de sus informes PDF.
                        </small>
                    """, unsafe_allow_html=True)

                acepta_privacidad = st.checkbox("He leído y acepto el aviso de privacidad", key="check_privacidad")
                submit_reg = st.form_submit_button("Registrarse", use_container_width=True)
                
                if submit_reg:
                    if not acepta_privacidad:
                        st.warning("Debes aceptar el aviso de privacidad para registrarte.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                            
                            # NUEVO: Insertar el ID del usuario recién creado en la tabla pública 'usuarios'
                            # Asegúrate de que las columnas ("id", "email") coinciden con tu tabla 'usuarios' real
                            if res.user:
                                supabase.table("usuarios").insert({
                                    "id": res.user.id,
                                    "email": reg_email
                                }).execute()
                                
                            st.success("¡Cuenta creada con éxito! Inicia sesión para continuar.")
                        except Exception as e:
                            st.error(f"Error al registrarse: {e}")
    st.stop()
    
# ==========================================
# 2. SELECCIÓN DE EQUIPO
# ==========================================
if st.session_state.autenticado and not st.session_state.equipo_seleccionado:
    # 1. Aplicamos el fondo de imagen oscuro con efecto cristal (Glassmorphism)
    try:
        import base64
        with open("fondo_login.jpg", "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        css_fondo_equipos = f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(10, 10, 10, 0.6), rgba(10, 10, 10, 0.8)), url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        
        /* Botones de acceder a los equipos (Azul MPA) */
        div[data-testid="column"] button {{
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
        }}
        div[data-testid="column"] button:hover {{
            background-color: #2563eb !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(59, 130, 246, 0.6) !important;
        }}
        
        /* Fondo cristal para el desplegable de Crear Equipo */
        div[data-testid="stExpander"] details {{
            background-color: rgba(30, 41, 59, 0.95) !important;
            border-radius: 12px !important;
            border: 1px solid #334155 !important;
            border-top: 4px solid #3b82f6 !important;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8) !important;
        }}
        div[data-testid="stExpander"] summary p {{
            color: #f8fafc !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        /* Inputs dentro de crear equipo */
        div[data-testid="stExpander"] div[data-testid="stTextInput"] input,
        div[data-testid="stExpander"] div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
            background-color: #f4f4f5 !important;
            border: 1px solid #d4d4d8 !important;
            border-radius: 6px !important;
            color: #0a0a0a !important;
            font-weight: 600 !important;
        }}
        </style>
        """
        st.markdown(css_fondo_equipos, unsafe_allow_html=True)
    except FileNotFoundError:
        pass

    # Un poco de espacio superior y título rediseñado
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 40px; font-size: 2.5rem; letter-spacing: -1px; text-shadow: 0px 4px 15px rgba(0,0,0,0.8);'>SELECCIONA TU <span style='color: #dc2626;'>EQUIPO</span></h2>", unsafe_allow_html=True)
    
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
    # 🚨 INFORMACIÓN DIARIA (DASHBOARD)
    # ==========================================
    st.markdown("### 🚨 Información diaria")
    
    # 1. Recalcular numeración dinámica de las sesiones (S56, J3, etc.)
    sesiones_crono = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
    c_entrenos, c_liga, c_copa, c_amistosos = 0, 0, 0, 0
    for s in sesiones_crono:
        if s["tipo"] == "Entrenamiento":
            c_entrenos += 1
            s["nombre_dinamico"] = f"S{c_entrenos}"
        elif s["tipo"] == "Partido Oficial":
            if s.get("competicion") == "Liga":
                c_liga += 1
                s["nombre_dinamico"] = f"J{c_liga}"
            else:
                c_copa += 1
                s["nombre_dinamico"] = f"Ronda {c_copa}"
        elif s["tipo"] == "Partido Amistoso":
            c_amistosos += 1
            s["nombre_dinamico"] = f"Amistoso {c_amistosos}"

    # 2. Seleccionar la sesión de referencia
    hoy_str = str(date.today())
    sesion_ref = next((s for s in sesiones_crono if s["fecha"] == hoy_str), None)
    if not sesion_ref and sesiones_crono:
        pasadas = [s for s in sesiones_crono if s["fecha"] <= hoy_str]
        sesion_ref = pasadas[-1] if pasadas else sesiones_crono[0]

    def get_avatar_html(jugador_nombre):
        for p in st.session_state.get("plantilla", []):
            if limpiar_nombre(p["JUGADOR"]) == limpiar_nombre(jugador_nombre):
                if p.get("foto"):
                    img_src = p["foto"] if str(p["foto"]).startswith("http") else f"data:image/jpeg;base64,{p['foto']}"
                    return f'<img src="{img_src}" style="width:28px; height:28px; border-radius:50%; object-fit: cover; vertical-align: middle; margin-right: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">'
                break
        return '<span style="font-size: 22px; margin-right: 8px; vertical-align: middle;">👤</span>'

    def render_estado_jugador(jugador_nombre, subtexto, nivel_alerta="moderado", avatar_html=""):
        if nivel_alerta == "critico": borde, bg_badge, color_badge = "#ef4444", "rgba(239, 68, 68, 0.2)", "#ef4444"
        elif nivel_alerta == "moderado": borde, bg_badge, color_badge = "#f59e0b", "rgba(245, 158, 11, 0.2)", "#f59e0b"
        else: borde, bg_badge, color_badge = "#10b981", "rgba(16, 185, 129, 0.2)", "#10b981"
            
        html = f"""
        <div style="background-color: #1e293b; border: 1px solid #334155; border-left: 4px solid {borde}; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center;">
                    {avatar_html}
                    <strong style="color: #f8fafc; font-size: 0.95rem; margin-left: 8px; font-weight: 700;">{jugador_nombre}</strong>
                </div>
                <span style="background-color: {bg_badge}; color: {color_badge}; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; border: 1px solid {color_badge};">
                    {subtexto}
                </span>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    bajas, a_vigilar, zona_roja = [], [], []
    if sesion_ref:
        disp = sesion_ref.get("disponibilidad", {})
        for j_nombre, estado in disp.items():
            if estado in ["Lesionado", "Enfermo", "No disponible", "Falta"]:
                bajas.append({"jug": j_nombre, "est": estado, "ava": get_avatar_html(j_nombre)})
                    
        if sesion_ref.get("datos_informe"):
            for d in sesion_ref["datos_informe"]:
                tqr, well = safe_float(d.get("TQR")), safe_float(d.get("WELLNESS"))
                alertas = []
                if 0 < tqr <= 4: alertas.append(f"TQR {tqr}")
                if well >= 18: alertas.append(f"Fatiga {well}")
                if alertas:
                    a_vigilar.append({"jug": d["JUGADOR"], "est": " / ".join(alertas), "ava": get_avatar_html(d["JUGADOR"])})
                    
        ewma_hoy = calcular_ewma_historico(st.session_state.sesiones, sesion_ref["fecha"])
        for jug, vals in ewma_hoy.items():
            ratio, aguda = vals.get("RATIO A/C", 0), vals.get("EWMA AGUDA", 0)
            if aguda > 1000 and ratio >= 1.35:
                zona_roja.append({"jug": jug, "est": f"A/C: {ratio:.2f}", "ava": get_avatar_html(jug)})

    # --- RENDERIZADO VISUAL A 4 COLUMNAS ---
    c_ctx, c_b, c_a, c_z = st.columns([1.2, 1, 1, 1])
    
    with c_ctx:
        if sesion_ref:
            nom_dyn = sesion_ref.get("nombre_dinamico", "")
            if "Partido" in sesion_ref.get("tipo", ""):
                contexto_str = f"{nom_dyn} vs {sesion_ref.get('rival', 'Rival')}"
                sub_str = "Match Day"
            else:
                contexto_str = f"{nom_dyn} | {sesion_ref.get('descripcion', 'TD')}"
                sub_str = "Entrenamiento"

            fecha_str = datetime.strptime(sesion_ref["fecha"], "%Y-%m-%d").strftime("%d %b")
            clima = sesion_ref.get("clima", {})
            clima_icon = "🌧️" if clima and clima.get("estado") == "Lluvia" else ("☀️" if clima else "⏱️")
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 12px; padding: 25px; height: 100%; border: 1px solid #334155; border-left: 5px solid #3b82f6; box-shadow: 0 10px 20px rgba(0,0,0,0.2); display: flex; flex-direction: column; justify-content: center;">
                <span style="color: #94a3b8; font-size: 0.85rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Última Referencia ({sub_str})</span>
                <h2 style="color: #f8fafc; font-size: 1.8rem; font-weight: 800; margin: 0 0 12px 0; line-height: 1.2;">{contexto_str}</h2>
                <div style="display: inline-block; background: #3b82f6; color: #ffffff; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; width: fit-content;">
                    {fecha_str} {clima_icon}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No hay sesiones programadas recientemente.")
            
    with c_b:
        st.markdown(f"**🏥 BAJAS CONFIRMADAS ({len(bajas)})**")
        if bajas:
            for b in bajas: render_estado_jugador(b["jug"], b["est"], "critico", b["ava"])
        else: st.success("✅ Plantilla sana.")
            
    with c_a:
        st.markdown(f"**🔋 A VIGILAR ({len(a_vigilar)})**")
        if a_vigilar:
            for a in a_vigilar: render_estado_jugador(a["jug"], a["est"], "moderado", a["ava"])
        else: st.success("✅ Buena recuperación.")
            
    with c_z:
        st.markdown(f"**⚠️ ZONA ALTA CARGA ({len(zona_roja)})**")
        if zona_roja:
            for z in zona_roja: render_estado_jugador(z["jug"], z["est"], "critico", z["ava"])
        else: st.success("✅ Cargas controladas.")

    st.markdown("---")
    
    # --- BOTÓN DE CONFIGURACIÓN A LA DERECHA ---
    c_vacio, c_btn = st.columns([5, 1])
    with c_btn:
        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state.mostrar_configuracion = not st.session_state.get("mostrar_configuracion", False)

    if st.session_state.get("mostrar_configuracion", False):
        render_panel_principal()
