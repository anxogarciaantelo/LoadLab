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
    # 🚨 TORRE DE CONTROL (DASHBOARD DIARIO)
    # ==========================================
    st.markdown("### Información Diaria")
    
    hoy_dt = date.today()
    hoy_str = str(hoy_dt)
    
    # --- 1. CABECERA DE CONTEXTO ---
    sesiones_partido = sorted([s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")], key=lambda x: x["fecha"])
    proximo_partido = next((s for s in sesiones_partido if s["fecha"] >= hoy_str), None)
    
    md_text = "SIN PARTIDO PROGRAMADO"
    rival_text = "N/A"
    fecha_partido_text = ""
    
    if proximo_partido:
        fecha_p_dt = datetime.strptime(proximo_partido["fecha"], "%Y-%m-%d").date()
        dias_diff = (fecha_p_dt - hoy_dt).days
        rival_text = proximo_partido.get('rival', 'Rival Desconocido')
        fecha_partido_text = fecha_p_dt.strftime("%d/%m/%Y")
        
        if dias_diff == 0: md_text = "🚨 MATCH DAY (MD)"
        elif dias_diff == 1: md_text = "⚡ MD - 1 (Activación)"
        elif dias_diff == 2: md_text = "🔥 MD - 2 (Tensión / Velocidad)"
        elif dias_diff == 3: md_text = "🏃‍♂️ MD - 3 (Fuerza / Resistencia)"
        elif dias_diff == 4: md_text = "🧠 MD - 4 (Recuperación Activa)"
        else: md_text = f"📅 MD - {dias_diff}"

    # Clima de hoy (usamos la ubicación del club)
    from utils.math_helpers import obtener_clima
    ciudad_club = st.session_state.get("ubicacion_local", "Santiago de Compostela")
    clima_hoy = obtener_clima(ciudad_club, hoy_str)
    clima_str = f"{clima_hoy['temp']}°C | {clima_hoy['estado']}" if clima_hoy else "Desconocido"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0f172a, #1e293b); border: 1px solid #334155; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 12px 18px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <p style="color: #94a3b8; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; margin: 0 0 2px 0;">Contexto del Microciclo</p>
            <h2 style="color: #f8fafc; font-size: 1.4rem; font-weight: 800; margin: 0;">{md_text}</h2>
        </div>
        <div style="text-align: right;">
            <div style="color: #f8fafc; font-size: 1rem; font-weight: 800; margin-bottom: 0px;">🆚 {rival_text}</div>
            <div style="color: #94a3b8; font-size: 0.75rem; font-weight: 600;">{fecha_partido_text}</div>
            <div style="color: #3b82f6; font-size: 0.75rem; font-weight: 800; margin-top: 2px;">📍 {ciudad_club} | {clima_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Funciones auxiliares visuales
    def get_avatar_html(jugador_nombre):
        for p in st.session_state.get("plantilla", []):
            if limpiar_nombre(p["JUGADOR"]) == limpiar_nombre(jugador_nombre):
                if p.get("foto"):
                    img_src = p["foto"] if str(p["foto"]).startswith("http") else f"data:image/jpeg;base64,{p['foto']}"
                    return f'<img src="{img_src}" style="width:22px; height:22px; border-radius:50%; object-fit: cover; vertical-align: middle; margin-right: 6px; border: 1px solid #334155;">'
                break
        return '<span style="font-size: 16px; margin-right: 6px; vertical-align: middle;">👤</span>'

    def item_alerta(jugador, texto, nivel="rojo"):
        color = "#ef4444" if nivel == "rojo" else ("#f59e0b" if nivel == "amarillo" else "#10b981")
        bg = "rgba(239, 68, 68, 0.1)" if nivel == "rojo" else ("rgba(245, 158, 11, 0.1)" if nivel == "amarillo" else "rgba(16, 185, 129, 0.1)")
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; background: {bg}; border: 1px solid {color}40; border-left: 3px solid {color}; padding: 4px 8px; border-radius: 6px; margin-bottom: 4px;">
            <div style="display: flex; align-items: center;">
                {get_avatar_html(jugador)}
                <span style="color: #f8fafc; font-size: 0.8rem; font-weight: 700;">{jugador}</span>
            </div>
            <span style="color: {color}; font-size: 0.7rem; font-weight: 800;">{texto}</span>
        </div>
        """, unsafe_allow_html=True)

    # --- RECOPILACIÓN DE DATOS (READINESS, CARGA Y MÉDICO) ---
    bajas_medicas = []
    readaptacion = []
    alertas_readiness = []
    alertas_carga = []

    # 1. PARTE MÉDICO
    for l in st.session_state.lesiones:
        if l.get("estado") == "Activa":
            dias_lesionado = (hoy_dt - datetime.strptime(l["id_sesion"], "%Y-%m-%d").date()).days
            bajas_medicas.append({"jug": l["jugador"], "txt": f"{l['tipo']} ({dias_lesionado}d)"})
        elif l.get("estado") == "Recuperado" and l.get("dias_baja"):
            fecha_alta = datetime.strptime(l["id_sesion"], "%Y-%m-%d").date() + timedelta(days=int(l["dias_baja"]))
            if 0 <= (hoy_dt - fecha_alta).days <= 7: # Alta en los últimos 7 días
                readaptacion.append({"jug": l["jugador"], "txt": "Alta reciente (RTP)"})

    # 2. READINESS (Último registro de bienestar disponible)
    sesiones_con_datos = [s for s in st.session_state.sesiones if s.get("informe_generado") and s["fecha"] <= hoy_str]
    if sesiones_con_datos:
        ult_sesion = sorted(sesiones_con_datos, key=lambda x: x["fecha"])[-1]
        for d in ult_sesion.get("datos_informe", []):
            jug = d["JUGADOR"]
            # Excluir a los lesionados del readiness
            if jug in [b["jug"] for b in bajas_medicas]: continue
            tqr = safe_float(d.get("TQR", 0))
            well = safe_float(d.get("WELLNESS", 0))
            if 0 < tqr <= 3: alertas_readiness.append({"jug": jug, "txt": f"TQR {tqr:.0f}", "lvl": "rojo"})
            elif tqr == 4: alertas_readiness.append({"jug": jug, "txt": f"TQR {tqr:.0f}", "lvl": "amarillo"})
            if well >= 24: alertas_readiness.append({"jug": jug, "txt": f"Fatiga {well:.0f}", "lvl": "rojo"})
            elif 18 <= well < 24: alertas_readiness.append({"jug": jug, "txt": f"Fatiga {well:.0f}", "lvl": "amarillo"})

    # 3. CARGA (EWMA y GPS)
    ewma_hoy = calcular_ewma_historico(st.session_state.sesiones, hoy_str)
    
    # HSR acumulado en 7 días (para carga mecánica)
    df_master = st.session_state.get("df_master_informes", pd.DataFrame())
    hsr_dict = {}
    if not df_master.empty and 'DIS AI' in df_master.columns:
        df_7d = df_master[(df_master['FECHA'] <= hoy_str) & (df_master['FECHA'] > str(hoy_dt - timedelta(days=7)))]
        if not df_7d.empty:
            hsr_dict = df_7d.groupby('JUGADOR')['DIS AI'].sum().to_dict()

    for jug, vals in ewma_hoy.items():
        if jug in [b["jug"] for b in bajas_medicas]: continue
        ratio = vals.get("RATIO A/C", 0)
        aguda = vals.get("EWMA AGUDA", 0)
        hsr_7d = hsr_dict.get(jug, 0)
        
        if aguda > 800:
            if ratio >= 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C: {ratio:.2f}", "lvl": "rojo"})
            elif 1.35 <= ratio < 1.5: alertas_carga.append({"jug": jug, "txt": f"A/C: {ratio:.2f}", "lvl": "amarillo"})
            elif ratio < 0.8: alertas_carga.append({"jug": jug, "txt": f"A/C Bajo: {ratio:.2f}", "lvl": "amarillo"})
            
        if hsr_7d > 2500: # Threshold heurístico de HSR semanal
            alertas_carga.append({"jug": jug, "txt": f"HSR 7d: {hsr_7d:.0f}m", "lvl": "amarillo"})

    # Limpiar duplicados de un mismo jugador en listas (mostrar solo la peor alerta si hay varias)
    def dedup_alertas(lista):
        vistos = {}
        for item in lista:
            if item["jug"] not in vistos: vistos[item["jug"]] = item
            else:
                if item["lvl"] == "rojo" and vistos[item["jug"]]["lvl"] == "amarillo":
                    vistos[item["jug"]] = item # Priorizar rojo
                elif item["lvl"] == vistos[item["jug"]]["lvl"]:
                    vistos[item["jug"]]["txt"] += f" | {item['txt']}"
        return list(vistos.values())
        
    alertas_readiness = dedup_alertas(alertas_readiness)
    alertas_carga = dedup_alertas(alertas_carga)

    # --- RENDERIZADO DE LAS 3 COLUMNAS ---
    c_read, c_carga, c_med = st.columns(3)

    with c_read:
        st.markdown("""
        <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #f59e0b; border-radius: 8px; padding: 8px; height: 100%;">
            <p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 8px 0;">🧠 Readiness & Bienestar</p>
        """, unsafe_allow_html=True)
        if alertas_readiness:
            for a in alertas_readiness: item_alerta(a["jug"], a["txt"], a["lvl"])
        else:
            st.success("✅ Equipo en parámetros óptimos.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_carga:
        st.markdown("""
        <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #ef4444; border-radius: 8px; padding: 8px; height: 100%;">
            <p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 8px 0;">🔥 Riesgo de Carga Acumulada</p>
        """, unsafe_allow_html=True)
        if alertas_carga:
            for a in alertas_carga: item_alerta(a["jug"], a["txt"], a["lvl"])
        else:
            st.success("✅ Cargas crónicas balanceadas.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c_med:
        st.markdown("""
        <div style="background: #1e293b; border: 1px solid #334155; border-top: 3px solid #8b5cf6; border-radius: 8px; padding: 8px; height: 100%;">
            <p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 8px 0;">🚑 Enfermería & RTP</p>
        """, unsafe_allow_html=True)
        if not bajas_medicas and not readaptacion:
            st.success("✅ Plantilla 100% disponible.")
        else:
            for b in bajas_medicas: item_alerta(b["jug"], b["txt"], "rojo")
            for r in readaptacion: item_alerta(r["jug"], r["txt"], "verde")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # --- BOTÓN DE CONFIGURACIÓN ESTRECHO A LA DERECHA ---
    c_vacio, c_btn = st.columns([6, 1])
    with c_btn:
        if st.button("⚙️ Configuración", use_container_width=True):
            st.session_state.mostrar_configuracion = not st.session_state.get("mostrar_configuracion", False)

    if st.session_state.get("mostrar_configuracion", False):
        render_panel_principal()
