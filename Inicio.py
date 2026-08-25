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
        [data-testid="stSidebar"] p {{
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
    
    st.markdown("<br><br><br><br><br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
    
    col_izq, col_centro, col_der = st.columns([1.2, 1, 1.2])
    
    with col_centro:
        tab_login, tab_reg = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with tab_login:
            # Color oscuro para la tarjeta blanca
            st.markdown("<h3 style='text-align: center; color: #0f172a; font-weight: 800; margin-bottom: 10px;'>Acceso</h3>", unsafe_allow_html=True)
            with st.form(key="login_form"):
                email = st.text_input("Correo electrónico", key="log_email")
                password = st.text_input("Contraseña", type="password", key="log_pass")
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
                        
        with tab_reg:
            # Color oscuro para la tarjeta blanca
            st.markdown("<h3 style='text-align: center; color: #0f172a; font-weight: 800; margin-bottom: 10px;'>Nuevo Usuario</h3>", unsafe_allow_html=True)
            with st.form(key="register_form"):
                reg_email = st.text_input("Correo electrónico", key="reg_email")
                reg_password = st.text_input("Contraseña (mín. 6 caracteres)", type="password", key="reg_pass")
                
                # Texto legal en gris slate para combinar con la tarjeta
                st.markdown("""
                    <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 10px; line-height: 1.2;">
                        🔒 <strong>Aviso de Privacidad:</strong> Al registrarte, aceptas que los datos de cargas y salud introducidos son responsabilidad exclusiva del usuario. Se recomienda anonimizar a los deportistas.
                    </div>
                """, unsafe_allow_html=True)
                
                acepta_privacidad = st.checkbox("Acepto el aviso de privacidad y LOPD")
                submit_reg = st.form_submit_button("Crear Cuenta", use_container_width=True)
                
                if submit_reg:
                    if not acepta_privacidad:
                        st.warning("Debes aceptar el aviso de privacidad para registrarte.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                            st.success("¡Cuenta creada con éxito! Inicia sesión para continuar.")
                        except Exception as e:
                            st.error(f"Error al registrarse: {e}")
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

# ==========================================
# 4. PANTALLA PRINCIPAL (CUANDO EL EQUIPO ESTÁ SELECCIONADO)
# ==========================================
if st.session_state.get("equipo_seleccionado", False):
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 1. PREPARAR EL ESCUDO ---
    escudo = st.session_state.get("escudo_equipo")
    if escudo:
        img_html = f'<img src="data:image/jpeg;base64,{escudo}" style="width:140px; height:140px; object-fit: cover; border-radius:50%; margin-bottom: 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.15);">'
    else:
        img_html = '<div style="font-size: 70px; margin-bottom: 15px;">🛡️</div>'

    # --- 2. CABECERA DEL EQUIPO ---
    col_w1, col_w2, col_w3 = st.columns([1, 2.5, 1])
    with col_w2:
        st.markdown(f"""
            <div style="background-color: #ffffff; padding: 40px; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 40px;">
                {img_html}
                <h1 style="color: #0f172a; font-weight: 800; margin-bottom: 5px; font-size: 2.2rem;">{st.session_state.get('nombre_equipo', 'LoadLab')}</h1>
                <p style="color: #64748b; font-size: 1.1rem; margin-top: 0;">
            <b>{st.session_state.get('categoria_equipo', '')}</b> | {st.session_state.get('division_equipo', '')} &bull; Temp: {st.session_state.get('temporada_equipo', '')}
        </p>
    </div>
""", unsafe_allow_html=True)

    # ==========================================
    # 🚨 INFORMACIÓN DIARIA (DASHBOARD)
    # ==========================================
    st.markdown("### 🚨 Información diaria")
    
    # 1. Timeline y Clima (Buscamos la sesión más relevante)
    hoy_str = str(date.today())
    sesiones_ordenadas = sorted(st.session_state.sesiones, key=lambda x: x["fecha"])
    sesion_ref = next((s for s in sesiones_ordenadas if s["fecha"] == hoy_str), None)
    
    if not sesion_ref and sesiones_ordenadas:
        pasadas = [s for s in sesiones_ordenadas if s["fecha"] <= hoy_str]
        sesion_ref = pasadas[-1] if pasadas else sesiones_ordenadas[0]

    contexto_txt = "No hay sesiones programadas recientemente."
    if sesion_ref:
        md_txt = sesion_ref.get("descripcion", sesion_ref.get("tipo", ""))
        rival_txt = f" vs {sesion_ref.get('rival', 'Rival')}" if "Partido" in sesion_ref.get("tipo", "") else ""
        fecha_formato = datetime.strptime(sesion_ref["fecha"], "%Y-%m-%d").strftime("%d-%m-%Y")
        clima = sesion_ref.get("clima", {})
        clima_txt = f" | {clima.get('estado', '')} ({clima.get('temp', '')}ºC)" if clima else ""
        contexto_txt = f"📅 **Última Referencia: {fecha_formato}** {clima_txt} | ⏱️ Contexto: **{md_txt}{rival_txt}**"
        
    st.info(contexto_txt)

    # Helper para cargar la foto del jugador en formato pequeño
    def get_avatar_html(jugador_nombre):
        for p in st.session_state.get("plantilla", []):
            if limpiar_nombre(p["JUGADOR"]) == limpiar_nombre(jugador_nombre):
                if p.get("foto"):
                    return f'<img src="data:image/jpeg;base64,{p["foto"]}" style="width:28px; height:28px; border-radius:50%; object-fit: cover; vertical-align: middle; margin-right: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);">'
                break
        return '<span style="font-size: 22px; margin-right: 8px; vertical-align: middle;">👤</span>'

    # 2. Recopilación de Datos para las 3 Columnas
    bajas = []
    if sesion_ref:
        disp = sesion_ref.get("disponibilidad", {})
        for j_nombre, estado in disp.items():
            if estado in ["Lesionado", "Enfermo", "No disponible", "Falta"]:
                avatar = get_avatar_html(j_nombre)
                bajas.append(f"<div style='display:flex; align-items:center;'>{avatar} <strong style='font-size: 1rem;'>{j_nombre}</strong></div><div style='margin-left: 36px; font-size: 0.85rem; color: #555;'>↳ <i>{estado}</i></div>")
                    
    a_vigilar = []
    if sesion_ref and sesion_ref.get("datos_informe"):
        for d in sesion_ref["datos_informe"]:
            tqr = safe_float(d.get("TQR"))
            well = safe_float(d.get("WELLNESS"))
            alertas = []
            if 0 < tqr <= 4: alertas.append(f"TQR Bajo ({tqr}/10)")
            if well >= 18: alertas.append(f"Wellness Alto ({well} pts)")
            
            if alertas:
                avatar = get_avatar_html(d["JUGADOR"])
                a_vigilar.append(f"<div style='display:flex; align-items:center;'>{avatar} <strong style='font-size: 1rem;'>{d['JUGADOR']}</strong></div><div style='margin-left: 36px; font-size: 0.85rem; color: #555;'>↳ <i>{', '.join(alertas)}</i></div>")
                
    zona_roja = []
    if sesion_ref:
        ewma_hoy = calcular_ewma_historico(st.session_state.sesiones, sesion_ref["fecha"])
        for jug, vals in ewma_hoy.items():
            ratio = vals.get("RATIO A/C", 0)
            aguda = vals.get("EWMA AGUDA", 0)
            
            # Filtro exacto que usamos en el informe de 1_Entrenamiento (Aguda > 1000 y Ratio >= 1.35)
            if aguda > 1000 and ratio >= 1.35:
                avatar = get_avatar_html(jug)
                zona_roja.append(f"<div style='display:flex; align-items:center;'>{avatar} <strong style='font-size: 1rem;'>{jug}</strong></div><div style='margin-left: 36px; font-size: 0.85rem; color: #555;'>↳ <i>Ratio A/C de Riesgo ({ratio:.2f})</i></div>")

    # 3. Renderizado de Columnas
    c_b, c_a, c_z = st.columns(3)
    css_tarjeta = "padding: 10px 12px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); background-color: white;"
    
    with c_b:
        st.markdown(f"**🏥 BAJAS CONFIRMADAS ({len(bajas)})**")
        if bajas:
            for b in bajas: st.markdown(f"<div style='border-left: 4px solid #ef4444; {css_tarjeta}'>{b}</div>", unsafe_allow_html=True)
        else:
            st.success("✅ Plantilla sana y disponible.")
            
    with c_a:
        st.markdown(f"**🔋 A VIGILAR ({len(a_vigilar)})**")
        if a_vigilar:
            for a in a_vigilar: st.markdown(f"<div style='border-left: 4px solid #f59e0b; {css_tarjeta}'>{a}</div>", unsafe_allow_html=True)
        else:
            st.success("✅ Buena recuperación general.")
            
    with c_z:
        st.markdown(f"**⚠️ ZONA ALTA DE CARGA ({len(zona_roja)})**")
        if zona_roja:
            for z in zona_roja: st.markdown(f"<div style='border-left: 4px solid #e11d48; {css_tarjeta}'>{z}</div>", unsafe_allow_html=True)
        else:
            st.success("✅ Cargas controladas.")

    # 4. Alertas de Sanciones (Tarjetas)
    partidos = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")]
    tarjetas_jugador = {}
    for p in partidos:
        stats = p.get("estadisticas_partido", {})
        for jug, vals in stats.items():
            tarjetas_jugador[jug] = tarjetas_jugador.get(jug, 0) + vals.get("Amarillas", 0)
            
    apercibidos = []
    sancionados = []
    for jug, ta in tarjetas_jugador.items():
        if ta > 0:
            if ta % 5 == 4: apercibidos.append(jug)
            elif ta % 5 == 0: sancionados.append(jug)
            
    if apercibidos or sancionados:
        st.markdown("---")
        st.markdown("**⚖️ ALERTAS DE PARTIDO:**")
        if sancionados:
            st.error(f"🛑 **Sancionados (Ciclo cumplido):** {', '.join(sancionados)}")
        if apercibidos:
            st.warning(f"🟨 **Apercibidos (A una tarjeta de la sanción):** {', '.join(apercibidos)}")

    st.markdown("---")

    # --- 3. TARJETAS DE NAVEGACIÓN (ACCESOS RÁPIDOS) ---
    st.markdown("<h3 style='text-align: center; color: #0f172a; font-weight: 800; margin-bottom: 25px;'>🚀 Accesos Rápidos</h3>", unsafe_allow_html=True)
    
    # CSS inyectado para que los botones parezcan tarjetas grandes y clickeables
    st.markdown("""
        <style>
        div.stButton > button {
            height: 90px;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            border-radius: 14px !important;
            border: 1px solid #e2e8f0 !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
            transition: all 0.2s ease !important;
            background-color: #ffffff !important;
            color: #0f172a !important;
        }
        div.stButton > button:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 20px rgba(0,0,0,0.08) !important;
            border-color: #cbd5e1 !important;
            background-color: #f8fafc !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Crear una cuadrícula con 4 columnas para los 7 accesos rápidos
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        if st.button("📅 Entrenamientos", use_container_width=True):
            st.switch_page("pages/1_Entrenamiento.py")
        if st.button("⚖️ Antropometría", use_container_width=True):
            st.switch_page("pages/5_Antropometria.py")
            
    with c2:
        if st.button("👥 Plantilla", use_container_width=True):
            st.switch_page("pages/2_Plantilla.py")
        if st.button("📊 Valoraciones", use_container_width=True):
            st.switch_page("pages/6_Valoraciones.py")
            
    with c3:
        if st.button("🚑 Lesiones", use_container_width=True):
            st.switch_page("pages/3_Lesiones.py")
        if st.button("📈 Estadísticas", use_container_width=True):
            st.switch_page("pages/7_Estadisticas.py")

    with c4:
        if st.button("📡 GPS", use_container_width=True):
            st.switch_page("pages/4_GPS.py")

    st.markdown("---")
    render_panel_principal()
