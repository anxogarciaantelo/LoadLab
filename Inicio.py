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
import extra_streamlit_components as stx 
# --- NUESTRAS LIBRERÍAS LOCALES ---
from utils.math_helpers import *
from utils.pdf_generator import *
from database.db_manager import *
from views.team_settings import render_panel_principal

# Configuración inicial de la página
st.set_page_config(page_title="LoadLab", page_icon="assets/logo_icono.png", layout="wide", initial_sidebar_state="expanded")

import plotly.io as pio
import plotly.graph_objects as go

pio.templates["loadlab_elite_dark"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Plus Jakarta Sans, sans-serif", size=11, color="#94a3b8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=["#C5A059", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#0ea5e9"],
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="rgba(15, 23, 42, 0.95)",
            font_size=12,
            font_family="Plus Jakarta Sans, sans-serif",
            bordercolor="#111318"
        ),
        xaxis=dict(
            gridcolor="#111318",
            gridwidth=1,
            griddash="dot",
            zerolinecolor="#111318",
            zerolinewidth=2,
            showline=False,
            title=dict(font=dict(size=12, color="#e2e8f0")),
            tickfont=dict(size=10, color="#94a3b8")
        ),
        yaxis=dict(
            gridcolor="#111318",
            gridwidth=1,
            griddash="dot",
            zerolinecolor="#111318",
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

# --- GESTOR DE COOKIES ---
import extra_streamlit_components as stx
cookie_manager = stx.CookieManager(key="loadlab_cookies")

# Si venimos de hacer clic en "Cerrar Sesión", borramos las cookies desde la raíz
if st.session_state.get("borrar_cookies", False):
    cookie_manager.delete("loadlab_access", key="del_1")
    cookie_manager.delete("loadlab_refresh", key="del_2")
    cookie_manager.delete("loadlab_uid", key="del_3")
    st.session_state.borrar_cookies = False

# --- RECUPERACIÓN DE SESIÓN (RECUÉRDAME) ---
# Si no estamos autenticados y no acabamos de darle al botón de cerrar sesión
if not st.session_state.get("autenticado", False) and not st.session_state.get("logout_intent", False):
    token = cookie_manager.get("loadlab_access")
    refresh = cookie_manager.get("loadlab_refresh")
    uid = cookie_manager.get("loadlab_uid")
    
    if token and refresh and uid:
        try:
            res = supabase.auth.set_session(token, refresh)
            st.session_state.usuario_id = uid
            st.session_state.access_token = token
            st.session_state.refresh_token = refresh
            st.session_state.autenticado = True
            st.rerun()
        except Exception:
            # Si el token ha caducado tras semanas, limpiamos las cookies rotas
            cookie_manager.delete("loadlab_access", key="del_err1")
            cookie_manager.delete("loadlab_refresh", key="del_err2")
            cookie_manager.delete("loadlab_uid", key="del_err3")

# ==========================================
# 0. CARGA DE CSS GLOBAL
# ==========================================
st.markdown(cargar_css_global(), unsafe_allow_html=True)

# ==========================================
# 1. LANDING PAGE COMERCIAL Y PANTALLA DE LOGIN / REGISTRO
# ==========================================
if not st.session_state.autenticado:
    set_login_background()
    
    if "mostrar_login_view" not in st.session_state:
        st.session_state.mostrar_login_view = False

    import base64
    import os
    ruta_logo = os.path.join("assets", "logo_completo.png")
    try:
        with open(ruta_logo, "rb") as image_file:
            logo_b64 = base64.b64encode(image_file.read()).decode()
        logo_html_nav = f'<img src="data:image/png;base64,{logo_b64}" style="height: 46px; object-fit: contain;">'
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 260px; margin-bottom: 10px;">'
    except FileNotFoundError:
        logo_html_nav = '<span style="font-size: 1.5rem; font-weight: 900; color: #f8fafc;">LOAD<span style="color: #C5A059;">LAB</span></span>'
        logo_html = '<h2 style="font-size: 2.2rem; font-weight: 900; color: #f8fafc;">LOAD<span style="color: #C5A059;">LAB</span></h2>'

    # ----------------------------------------------------
    # A. VISTA LANDING PAGE COMERCIAL (ESCAPARATE SAAS)
    # ----------------------------------------------------
    if not st.session_state.mostrar_login_view:
        c_nav1, c_nav2, c_nav3 = st.columns([1.5, 2.5, 1])
        with c_nav1:
            st.markdown(f"<div style='padding-top: 4px;'>{logo_html_nav}</div>", unsafe_allow_html=True)
        with c_nav2:
            st.markdown("""
            <div style="display: flex; justify-content: center; gap: 28px; padding-top: 14px; font-size: 0.85rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px;">
                <span>Carga EWMA</span><span>•</span><span>Oráculo IA</span><span>•</span><span>Fuerza VBT</span><span>•</span><span>Protocolo RTP</span>
            </div>
            """, unsafe_allow_html=True)
        with c_nav3:
            if st.button(":material/login: INICIAR SESIÓN", key="btn_nav_login", use_container_width=True):
                st.session_state.mostrar_login_view = True
                st.rerun()

        st.markdown("<hr style='border-color: rgba(197,160,89,0.15); margin: 12px 0 35px 0;'>", unsafe_allow_html=True)

        # HERO SECTION + HUD 3D PREVIEW
        col_hero_txt, col_hero_hud = st.columns([1.15, 1.1], gap="large")
        with col_hero_txt:
            st.markdown("""
            <div style="display: inline-flex; align-items: center; gap: 8px; background: rgba(197, 160, 89, 0.1); border: 1px solid rgba(197, 160, 89, 0.35); padding: 6px 14px; border-radius: 999px; margin-bottom: 18px;">
                <span class="live-dot"></span>
                <span style="color: #C5A059; font-size: 0.75rem; font-weight: 800; letter-spacing: 1px; text-transform: uppercase;">ECOSISTEMA DE RENDIMIENTO DEPORTIVO DE ÉLITE</span>
            </div>
            <h1 style="font-size: 3.1rem; font-weight: 800; line-height: 1.08; color: #f8fafc; letter-spacing: -1px; margin-bottom: 18px;">
                Domina el rendimiento.<br>Anticipa lesiones.<br><span style="background: linear-gradient(90deg, #C5A059, #f3e5ab); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Gana el fin de semana.</span>
            </h1>
            <p style="color: #94a3b8; font-size: 1.05rem; line-height: 1.6; margin-bottom: 28px; max-width: 92%;">
                El sistema operativo integral para preparadores físicos, readaptadores y cuerpos técnicos. Unifica GPS, carga interna EWMA, perfiles Fuerza-Velocidad (VBT), composición corporal e Inteligencia Artificial predictiva en una sola plataforma.
            </p>
            """, unsafe_allow_html=True)
            
            c_cta1, c_cta2 = st.columns([1.2, 1])
            with c_cta1:
                if st.button(":material/rocket_launch: ACCEDER A LA PLATAFORMA", key="btn_hero_login", use_container_width=True):
                    st.session_state.mostrar_login_view = True
                    st.rerun()
            with c_cta2:
                st.markdown("""
                <div style="display: flex; align-items: center; height: 46px; padding-left: 10px; color: #cbd5e1; font-size: 0.85rem; font-weight: 700;">
                    <span class="material-symbols-rounded" style="color: #10b981; margin-right: 6px;">verified</span> Estándar UEFA ECIS & FIFA EPTS
                </div>
                """, unsafe_allow_html=True)

        with col_hero_hud:
            st.markdown("""
            <div style="background: radial-gradient(120% 120% at 50% 0%, rgba(197, 160, 89, 0.16) 0%, rgba(11, 14, 20, 0.95) 75%); border: 1px solid rgba(197, 160, 89, 0.3); border-top: 2px solid #C5A059; border-radius: 16px; padding: 20px; box-shadow: 0 30px 60px -15px rgba(0,0,0,0.85), 0 0 30px rgba(197,160,89,0.12); transform: perspective(1000px) rotateY(-4deg) rotateX(2deg);">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 14px;">
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #ef4444; display: inline-block;"></span>
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #f59e0b; display: inline-block;"></span>
                        <span style="width: 10px; height: 10px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                        <span class="font-mono-hud" style="color: #94a3b8; font-size: 0.72rem; margin-left: 8px;">LOADLAB // TELEMETRY_HUD_V2.6</span>
                    </div>
                    <span class="font-mono-hud" style="color: #10b981; font-size: 0.72rem; background: rgba(16,185,129,0.12); padding: 2px 8px; border-radius: 4px; font-weight: 800;">● LIVE SYNC</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;">
                    <div style="background: #111318; border: 1px solid rgba(255,255,255,0.06); border-top: 2px solid #10b981; padding: 10px; border-radius: 8px; text-align: center;">
                        <span style="font-size: 0.65rem; color: #94a3b8; font-weight: 800; display: block;">READINESS PLANTILLA</span>
                        <span class="font-mono-hud" style="font-size: 1.45rem; color: #10b981; font-weight: 800;">88.4%</span>
                        <span class="font-mono-hud" style="font-size: 0.65rem; color: #10b981; display: block;">▲ +4.2% vs MD-3</span>
                    </div>
                    <div style="background: #111318; border: 1px solid rgba(255,255,255,0.06); border-top: 2px solid #C5A059; padding: 10px; border-radius: 8px; text-align: center;">
                        <span style="font-size: 0.65rem; color: #94a3b8; font-weight: 800; display: block;">ACWR UNCOUPLED</span>
                        <span class="font-mono-hud" style="font-size: 1.45rem; color: #f8fafc; font-weight: 800;">1.08</span>
                        <span style="font-size: 0.65rem; color: #C5A059; font-weight: 700; display: block;">SWEET SPOT ZONE</span>
                    </div>
                    <div style="background: #111318; border: 1px solid rgba(255,255,255,0.06); border-top: 2px solid #0ea5e9; padding: 10px; border-radius: 8px; text-align: center;">
                        <span style="font-size: 0.65rem; color: #94a3b8; font-weight: 800; display: block;">CUMPLIMIENTO HSR</span>
                        <span class="font-mono-hud" style="font-size: 1.45rem; color: #0ea5e9; font-weight: 800;">94.1%</span>
                        <span class="font-mono-hud" style="font-size: 0.65rem; color: #94a3b8; display: block;">642m (>21 km/h)</span>
                    </div>
                </div>
                <div style="background: #0b0e14; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #cbd5e1; font-weight: 800; margin-bottom: 8px;">
                        <span>🧠 ORÁCULO IA (XGBOOST) — PREDICCIÓN A 7 DÍAS</span>
                        <span class="font-mono-hud" style="color: #C5A059;">PRECISIÓN Z-SCORE + EWMA</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(239,68,68,0.1); border-left: 3px solid #ef4444; border-radius: 4px; margin-bottom: 6px;">
                        <span style="font-size: 0.78rem; font-weight: 800; color: #f8fafc;">#10 M. Oyarzabal <span style="color:#94a3b8; font-weight:600;">(EXT)</span></span>
                        <span class="font-mono-hud" style="font-size: 0.72rem; color: #ef4444; font-weight: 800;">A/C HSR: 1.54 | Z-Dolor: +1.8 ➔ 68% RIESGO</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: rgba(16,185,129,0.08); border-left: 3px solid #10b981; border-radius: 4px;">
                        <span style="font-size: 0.78rem; font-weight: 800; color: #f8fafc;">#8 M. Merino <span style="color:#94a3b8; font-weight:600;">(MED)</span></span>
                        <span class="font-mono-hud" style="font-size: 0.72rem; color: #10b981; font-weight: 800;">A/C INT: 1.04 | VMax >91% ➔ 6% ÓPTIMO</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # CINTA DE AUTORIDAD CIENTÍFICA
        st.markdown("""
        <div style="background: rgba(17, 19, 24, 0.75); border-top: 1px solid rgba(197,160,89,0.15); border-bottom: 1px solid rgba(197,160,89,0.15); padding: 14px 20px; margin: 40px 0 35px 0; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px; text-align: center;">
            <div><span style="color: #C5A059; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">MODELO DE CARGA</span><br><span style="color: #f8fafc; font-weight: 800; font-size: 0.9rem;">Uncoupled EWMA (Williams & Gabbett)</span></div>
            <div><span style="color: #C5A059; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">FATIGA NEURO-METABÓLICA</span><br><span style="color: #f8fafc; font-weight: 800; font-size: 0.9rem;">Z-Score Intra-Sujeto 28d & Monotonía (Foster)</span></div>
            <div><span style="color: #C5A059; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">BIOMECÁNICA & VBT</span><br><span style="color: #f8fafc; font-weight: 800; font-size: 0.9rem;">Perfil Fuerza-Velocidad (J.B. Morin / Samozino)</span></div>
            <div><span style="color: #C5A059; font-weight: 800; font-size: 0.75rem; text-transform: uppercase;">EPIDEMIOLOGÍA CLÍNICA</span><br><span style="color: #f8fafc; font-weight: 800; font-size: 0.9rem;">Consenso UEFA ECIS (Incidencia & Burden /1000h)</span></div>
        </div>
        """, unsafe_allow_html=True)

        # BENTO GRID DE MÓDULOS
        st.markdown("<h2 style='text-align: center; color: #f8fafc; font-weight: 800; font-size: 2rem; margin-bottom: 8px;'>Arquitectura de <span style='color: #C5A059;'>Grado Profesional</span></h2><p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>6 módulos interconectados en tiempo real para cubrir cada eslabón del rendimiento en fútbol.</p>", unsafe_allow_html=True)
        
        b_col1, b_col2, b_col3 = st.columns(3)
        bento_items = [
            (b_col1, "monitoring", "1. Control de Carga & Periodización Táctica", "Algoritmo Uncoupled EWMA para Carga Interna, HSR (>21 km/h) y Tensión Mecánica (ACC/DCC). Incluye cálculo en vivo de Carga Compensatoria post-partido para suplentes y bandas objetivo por Match Day (MD-4 a MD-1)."),
            (b_col2, "psychology", "2. Oráculo IA Predictivo (XGBoost)", "Motor híbrido que entrena con el historial de tu plantilla. Combina spikes de ACWR, daño excéntrico (DCC 7d), Z-Score de dolor, fatiga residual (Strain) y la 'Vacuna de Velocidad' (>85% VMax) para anticipar roturas musculares."),
            (b_col3, "healing", "3. Motor Automatizado de Return to Play (RTP)", "Progresión inteligente en 4 fases. Evalúa automáticamente si el jugador tolera la carga sin regresión clínica (Dolor D+1 < 4) y verifica los 6 criterios de alta competitiva frente a su perfil pre-lesión."),
            (b_col1, "fitness_center", "4. Laboratorio VBT, Isometría y Asimetrías", "Cálculo de 1RM y perfil Fuerza-Velocidad mediante regresión lineal (V0, F0 y R²), ratios clínicos H:Q de isquiosurales/cuádriceps (N/kg), déficit bilateral en CMJ y gráfico Tornado de asimetrías."),
            (b_col2, "developer_board", "5. Pizarra Táctica 2D & Sinergias de Partido", "Recomendador algorítmico del Once Ideal según sistema táctico, estado de frescura (Readiness), ACWR e impacto competitivo (+/- cada 90'). Analiza tramos de gol de 15', factor revulsivo y parejas de oro."),
            (b_col3, "picture_as_pdf", "6. Imputación GPS Virtual & Reporting PDF", "Nunca pierdas la trazabilidad cuando falte un dispositivo: el motor imputa la carga externa según rol, posición y minutos jugados, protegiendo los récords reales. Exporta dossieres PDF ejecutivos en 1 clic.")
        ]
        for col_b, ic_b, tit_b, desc_b in bento_items:
            with col_b:
                st.markdown(f"""
                <div style="background: radial-gradient(120% 100% at 50% 0%, rgba(197, 160, 89, 0.10) 0%, #111318 75%); border: 1px solid rgba(255,255,255,0.07); border-top: 2px solid #C5A059; border-radius: 12px; padding: 20px; margin-bottom: 18px; min-height: 200px; box-shadow: 0 10px 25px rgba(0,0,0,0.4);">
                    <div style="background: rgba(197, 160, 89, 0.12); width: 42px; height: 42px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #C5A059; margin-bottom: 12px;">
                        <span class="material-symbols-rounded" style="font-size: 1.6rem;">{ic_b}</span>
                    </div>
                    <h4 style="color: #f8fafc; font-size: 1.05rem; font-weight: 800; margin: 0 0 8px 0;">{tit_b}</h4>
                    <p style="color: #94a3b8; font-size: 0.86rem; line-height: 1.5; margin: 0;">{desc_b}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        _, c_bot_cta, _ = st.columns([1.5, 1.5, 1.5])
        with c_bot_cta:
            if st.button(":material/login: ENTRAR A LOADLAB / CREAR CUENTA", key="btn_footer_login", use_container_width=True):
                st.session_state.mostrar_login_view = True
                st.rerun()
        st.stop()

    # ----------------------------------------------------
    # B. VISTA DE LOGIN / REGISTRO (DISEÑO SPLIT ÉLITE)
    # ----------------------------------------------------
    c_back_l, _ = st.columns([1, 4])
    with c_back_l:
        if st.button(":material/arrow_back: Volver a la presentación", key="btn_back_landing", use_container_width=True):
            st.session_state.mostrar_login_view = False
            st.rerun()

    col_info, col_espacio, col_login = st.columns([1.5, 0.2, 1.2])
    
    with col_info:
        html_info = f"""<div style="padding-right: 20px;">
{logo_html}
<h1 style="font-size: 2.1rem; font-weight: 800; line-height: 1.2; margin-bottom: 15px; color: #E2E8F0; letter-spacing: -0.5px;">
Decisiones basadas en datos, <span style="color: #C5A059;">rendimiento de élite.</span>
</h1>
<p style="color: #a1a1aa; font-size: 1rem; margin-bottom: 25px; max-width: 95%; line-height: 1.5;">
Centraliza y analiza las variables de rendimiento, carga y salud de tus futbolistas en un único ecosistema premium diseñado para cuerpos técnicos profesionales.
</p>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 8px; border-radius: 8px; color: #C5A059; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex-shrink: 0;"><span class="material-symbols-rounded" style="font-size: 1.5rem;">monitoring</span></div>
<div>
<h4 style="margin: 0 0 2px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Carga y Demandas (EWMA / ACWR)</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.3;">Monitoriza el Ratio A/C (Sweet Spot), strain acumulado y densidad competitiva para mitigar riesgo.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 8px; border-radius: 8px; color: #C5A059; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex-shrink: 0;"><span class="material-symbols-rounded" style="font-size: 1.5rem;">psychology</span></div>
<div>
<h4 style="margin: 0 0 2px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Oráculo Predictivo AI</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.3;">Algoritmos avanzados (XGBoost) para detectar y anticipar riesgo de lesión inminente en la plantilla.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 8px; border-radius: 8px; color: #C5A059; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex-shrink: 0;"><span class="material-symbols-rounded" style="font-size: 1.5rem;">fitness_center</span></div>
<div>
<h4 style="margin: 0 0 2px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Rendimiento & Fuerza VBT</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.3;">Seguimiento neuromuscular, perfiles Fuerza-Velocidad, test de salto (CMJ) y asimetrías.</p>
</div>
</div>

<div style="background: rgba(197, 160, 89, 0.03); border: 1px solid rgba(197, 160, 89, 0.15); padding: 12px 16px; border-radius: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 14px; backdrop-filter: blur(5px);">
<div style="background: rgba(197, 160, 89, 0.1); padding: 8px; border-radius: 8px; color: #C5A059; display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex-shrink: 0;"><span class="material-symbols-rounded" style="font-size: 1.5rem;">healing</span></div>
<div>
<h4 style="margin: 0 0 2px 0; font-size: 0.95rem; color: #E2E8F0; font-weight: 800;">Enfermería, RTP & Antropometría</h4>
<p style="margin: 0; font-size: 0.85rem; color: #94a3b8; line-height: 1.3;">Control de bajas, fases de readaptación (Return to Play) y composición corporal de élite.</p>
</div>
</div>
</div>"""
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
                
                # --- NUEVO: Checkbox de recordar ---
                c_chk, c_link = st.columns([1, 1])
                with c_chk:
                    recordarme = st.checkbox("Mantenerme conectado", value=True)
                with c_link:
                    st.markdown("<div style='text-align: right; margin-top: 5px;'><a href='#' style='color: #C5A059; font-size: 0.8rem; text-decoration: none; font-weight: 600;'>¿Has olvidado tu contraseña?</a></div>", unsafe_allow_html=True)
                
                submit_btn = st.form_submit_button("Iniciar Sesión", use_container_width=True)
                if submit_btn:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.usuario_id = res.user.id
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        
                        if recordarme:
                            exp_date = datetime.now() + timedelta(days=30)
                            cookie_manager.set("loadlab_access", res.session.access_token, expires_at=exp_date, key="set_1")
                            cookie_manager.set("loadlab_refresh", res.session.refresh_token, expires_at=exp_date, key="set_2")
                            cookie_manager.set("loadlab_uid", res.user.id, expires_at=exp_date, key="set_3")
                            
                            st.success("✅ Autenticado. Guardando credenciales de forma segura...")
                            import streamlit.components.v1 as components
                            components.html("<script>setTimeout(function(){ window.parent.location.reload(); }, 1500);</script>", height=0)
                        else:
                            st.session_state.autenticado = True
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Credenciales incorrectas o error de conexión. Detalle técnico: {e}")
                        
        with tab_reg:
            st.markdown("<h3 style='color: #f8fafc; font-weight: 800; font-size: 1.6rem; margin-bottom: 5px; margin-top: 10px;'>Crear cuenta</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 20px;'>Únete a la plataforma de alto rendimiento.</p>", unsafe_allow_html=True)
            
            with st.form(key="register_form"):
                reg_email = st.text_input("Correo electrónico", key="reg_email", placeholder="tu@email.com")
                reg_password = st.text_input("Contraseña", type="password", key="reg_pass", placeholder="Mínimo 6 caracteres")
                
                st.markdown("""
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 10px; margin-bottom: 15px; line-height: 1.5; background-color: rgba(15, 23, 42, 0.5); padding: 12px; border-radius: 6px; border-left: 3px solid #C5A059;">
                        <span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1rem; margin-right: 4px; color: #C5A059;">lock</span> <strong>Aviso RGPD:</strong> Eres el <strong>Responsable del Tratamiento</strong> de los datos. Usa alias si no tienes consentimiento explícito.
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
        background-color: #0b0e14 !important;
        background-image: 
            radial-gradient(circle at 15% 50%, rgba(197, 160, 89, 0.08), transparent 30%), 
            radial-gradient(circle at 85% 30%, rgba(226, 232, 240, 0.05), transparent 25%) !important;
    }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-image: linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
        background-size: 50px 50px; pointer-events: none; z-index: 0;
    }
    .stApp::after {
        content: ""; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%;
        background-image: radial-gradient(1.5px 1.5px at 20px 30px, #C5A059, rgba(0,0,0,0)), radial-gradient(1.5px 1.5px at 40px 70px, #E2E8F0, rgba(0,0,0,0)), radial-gradient(2px 2px at 90px 40px, #C5A059, rgba(0,0,0,0));
        background-size: 250px 250px; animation: particleDrift 70s linear infinite; pointer-events: none; z-index: 0; opacity: 0.35;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stToolbar"] { display: none !important; }
    
    /* Botones de acceder a los equipos */
    div[data-testid="column"] button {
        background-color: #C5A059 !important;
        border: none !important;
        color: #111318 !important;
        font-weight: 800 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 10px rgba(197, 160, 89, 0.3) !important;
    }
    div[data-testid="column"] button:hover {
        background-color: #D6B26E !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(197, 160, 89, 0.5) !important;
    }
    
    /* Fondo cristal para el desplegable de Crear Equipo */
    div[data-testid="stExpander"] details {
        background-color: rgba(17, 19, 24, 0.95) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(197, 160, 89, 0.2) !important;
        border-top: 4px solid #C5A059 !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
    }
    div[data-testid="stExpander"] summary p {
        color: #f8fafc !important; font-weight: 800 !important; text-transform: uppercase; letter-spacing: 1px;
    }
    
    /* Inputs dentro de crear equipo */
    div[data-testid="stExpander"] div[data-testid="stTextInput"] input,
    div[data-testid="stExpander"] div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #0b0e14 !important; border: 1px solid #111318 !important; color: #f8fafc !important; font-weight: 600 !important;
    }
    </style>
    """
    st.markdown(css_fondo_equipos, unsafe_allow_html=True)

    # Un poco de espacio superior y título rediseñado
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 40px; font-size: 2.5rem; letter-spacing: -1px; text-shadow: 0px 4px 15px rgba(0,0,0,0.8);'>SELECCIONA TU <span style='color: #C5A059;'>EQUIPO</span></h2>", unsafe_allow_html=True)    
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
                            img_html = '<div style="display: flex; justify-content: center; align-items: center; height: 90px; margin-bottom: 15px;"><span class="material-symbols-rounded" style="font-size: 50px; color: #C5A059;">shield</span></div>'
                            
                        nombre = eq_info.get('nombre', 'Equipo')
                        division = eq_info.get('division') or "Sin división"
                        categoria = eq_info.get('categoria') or ""
                        
                        tarjeta_html = f"""
                        <div style="background-color: rgba(17, 19, 24, 0.85); padding: 30px 20px 20px 20px; border-radius: 12px; border: 1px solid rgba(197, 160, 89, 0.15); border-top: 4px solid #C5A059; box-shadow: 0 20px 40px rgba(0,0,0,0.6); text-align: center; margin-bottom: 15px; backdrop-filter: blur(10px);">
                            {img_html}
                            <h3 style="color: #f8fafc; font-weight: 800; margin-bottom: 5px; font-size: 1.3rem; text-transform: uppercase; letter-spacing: -0.5px;">{nombre}</h3>
                            <p style="color: #94a3b8; font-size: 0.85rem; font-weight: 700; margin-top: 0px; text-transform: uppercase; letter-spacing: 0.5px;">{categoria} | {division}</p>
                        </div>
                        """
                        st.markdown(tarjeta_html, unsafe_allow_html=True)
                        
                        if st.button(":material/login: Acceder", key=f"btn_{eq_id}", use_container_width=True):
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
        with st.expander(":material/add_circle: CREAR NUEVO EQUIPO"):
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
                    btn_crear = st.form_submit_button(":material/rocket_launch: CREAR Y ACCEDER", use_container_width=True)
                
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
                    
                    supabase.table("configuracion_equipo").insert({"equipo_id": nuevo_id}).execute()
                    
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
        img_html = '<div style="display: flex; justify-content: center; align-items: center; height: 140px; margin-bottom: 15px;"><span class="material-symbols-rounded" style="font-size: 70px; color: #C5A059;">shield</span></div>'

    # ==========================================
    # 🚨 TORRE DE CONTROL (DASHBOARD DIARIO)
    # ==========================================
    st.markdown("### :material/analytics: Información Diaria")

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
        es_hoy = "border: 2px solid #C5A059;" if d_str == hoy_str else "border: 1px solid #111318;"
        bg_color = "#0b0e14" if d_str == hoy_str else "#111318"
        
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
        
        if dias_diff == 0: md_text = "<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>emergency</span> MATCH DAY"
        elif dias_diff == 1: md_text = "<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>bolt</span> MD - 1"
        elif dias_diff == 2: md_text = "<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>local_fire_department</span> MD - 2"
        elif dias_diff == 3: md_text = "<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>directions_run</span> MD - 3"
        elif dias_diff == 4: md_text = "<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>psychology</span> MD - 4"
        else: md_text = f"<span class='material-symbols-rounded' style='vertical-align: bottom; font-size: inherit; margin-right: 6px;'>calendar_month</span> MD - {dias_diff}"

    from utils.math_helpers import obtener_clima
    ciudad_club = st.session_state.get("ubicacion_local", "Santiago de Compostela")
    clima_hoy = obtener_clima(ciudad_club, hoy_str)
    clima_str = f"{clima_hoy['temp']}°C | {clima_hoy['estado']}" if clima_hoy else "Desconocido"

    # 2.2 Motor de Alertas
    alertas_readiness = []
    alertas_carga = []
    bajas_medicas = []
    readaptacion = []

    df_master = st.session_state.get("df_master_informes", pd.DataFrame())
    dict_zscore = calcular_zscore_wellness(df_master, hoy_str)
    dict_zscore_efi = calcular_zscores_eficiencia(df_master, hoy_str)
    
    # 1. Extraer última sesión con datos ORDENADA CRONOLÓGICAMENTE por fecha
    ultimas_sesiones = {}
    sesiones_con_datos = sorted(
        [s for s in st.session_state.sesiones if s.get("informe_generado") and s["fecha"] <= hoy_str],
        key=lambda x: x["fecha"]
    )
    
    # --- NUEVA LÓGICA DE ENFERMERÍA ---
    # Lesionados según la última sesión con datos; Readaptación según el último ENTRENAMIENTO
    if sesiones_con_datos:
        ult_sesion = sesiones_con_datos[-1]
        disp_ult = {limpiar_nombre(k): v for k, v in ult_sesion.get("disponibilidad", {}).items()}
        
        entrenamientos_pasados = sorted(
            [s for s in st.session_state.sesiones if s.get("tipo") == "Entrenamiento" and s["fecha"] <= hoy_str],
            key=lambda x: x["fecha"]
        )
        disp_ult_entreno = {limpiar_nombre(k): v for k, v in entrenamientos_pasados[-1].get("disponibilidad", {}).items()} if entrenamientos_pasados else {}

        for p in st.session_state.plantilla:
            jug_nom = p["JUGADOR"]
            jug_clean = limpiar_nombre(jug_nom)
            estado_general = disp_ult.get(jug_clean, "Disponible")
            estado_entreno = disp_ult_entreno.get(jug_clean, "Disponible")
            
            if estado_general == "Lesionado" or estado_entreno == "Lesionado":
                bajas_medicas.append({"jug": jug_nom, "txt": "Lesionado"})
            elif estado_entreno == "Readaptación":
                readaptacion.append({"jug": jug_nom, "txt": "Readaptación (RTP)"})

    for s in sesiones_con_datos:
        md_s = "MD" if "Partido" in str(s.get("tipo", "")) else s.get("descripcion", "TD")
        for d in s.get("datos_informe", []):
            if safe_float(d.get("TQR", 0)) > 0 or safe_float(d.get("WELLNESS", 0)) > 0 or safe_float(d.get("MIN", 0)) > 0:
                ultimas_sesiones[limpiar_nombre(d["JUGADOR"])] = {"fecha": s["fecha"], "md": md_s, "datos": d}

    for jug_limpio, info_ult in ultimas_sesiones.items():
        jug = info_ult["datos"]["JUGADOR"]
        if jug in [b["jug"] for b in bajas_medicas]: continue
        
        d = info_ult["datos"]
        tqr, well = safe_float(d.get("TQR", 0)), safe_float(d.get("WELLNESS", 0))
        w_dolor, w_fatiga = safe_float(d.get('W_Dolor', 0)), safe_float(d.get('W_Fatiga', 0))
        
        # --- A. ALERTAS DE READINESS Y DAÑO TISULAR ---
        st_j = dict_zscore.get(jug, {'media': 0, 'std': 1.0, 'dolor_media': 0, 'dolor_std': 0.5, 'fatiga_media': 0, 'fatiga_std': 0.5})
        z_well = (well - st_j['media']) / st_j['std'] if st_j['std'] > 0 else 0
        z_dolor = (w_dolor - st_j['dolor_media']) / st_j['dolor_std'] if st_j['dolor_std'] > 0 else 0
        z_fatiga = (w_fatiga - st_j['fatiga_media']) / st_j['fatiga_std'] if st_j['fatiga_std'] > 0 else 0

        if w_dolor > 0 and z_dolor >= 1.5: alertas_readiness.append({"jug": jug, "txt": f"Daño Muscular (Z: +{z_dolor:.1f})", "lvl": "rojo"})
        elif w_dolor > 0 and z_dolor >= 1.0: alertas_readiness.append({"jug": jug, "txt": f"Sobrecarga Tisular (Z: +{z_dolor:.1f})", "lvl": "amarillo"})
        
        if tqr > 0 and well > 0:
            if tqr <= 3 and z_well >= 1.0: alertas_readiness.append({"jug": jug, "txt": f"Fatiga Sistémica (Z: +{z_well:.1f})", "lvl": "rojo"})
            elif tqr <= 4 and z_fatiga >= 1.5: alertas_readiness.append({"jug": jug, "txt": f"Fatiga Muscular (Z: +{z_fatiga:.1f})", "lvl": "rojo"})
            elif (tqr <= 4 and z_well < 1.0) or (tqr > 4 and z_well >= 1.5): alertas_readiness.append({"jug": jug, "txt": "Discordancia TQR/Wellness", "lvl": "amarillo"})
    
    # --- B. ALERTAS DE CARGA Y EFICIENCIA METABÓLICA ---
    fecha_ewma = hoy_str
    if sesiones_con_datos:
        fecha_ewma = sorted(sesiones_con_datos, key=lambda x: x["fecha"])[-1]["fecha"]
    
    ewma_hoy = calcular_ewma_historico(st.session_state.sesiones, fecha_ewma)
    hsr_dict = {}
    vmax_hist_dict = {}
    ult_sprint_dict = {}
    
    if not df_master.empty and 'DIS AI' in df_master.columns:
        df_7d = df_master[(df_master['FECHA'] <= hoy_str) & (df_master['FECHA'] > str(hoy_dt - timedelta(days=7)))]
        if not df_7d.empty:
            hsr_dict = df_7d.groupby('JUGADOR')['DIS AI'].sum().to_dict()
            
        # Vacuna de Velocidad: Última exposición a >= 85% Vmax (SOLO GPS REAL)
        if 'VMAX' in df_master.columns:
            df_real_gps = df_master[df_master.get('GPS_VIRTUAL', False) != True].copy()
            if not df_real_gps.empty:
                vmax_hist_dict = df_real_gps.groupby('JUGADOR')['VMAX'].max().to_dict()
                df_real_gps['es_pico'] = df_real_gps.apply(lambda r: r['VMAX'] >= (vmax_hist_dict.get(r['JUGADOR'], 0) * 0.85) if vmax_hist_dict.get(r['JUGADOR'], 0) > 25.0 else False, axis=1)
                df_picos = df_real_gps[df_real_gps['es_pico'] & (df_real_gps['FECHA'] <= hoy_str)]
                ult_sprint_dict = df_picos.groupby('JUGADOR')['FECHA'].max().to_dict()

    altas_medicas_dict = {}
    for l in st.session_state.lesiones:
        if l.get("estado") == "Recuperado" and l.get("dias_baja"):
            fecha_alta = datetime.strptime(l["id_sesion"], "%Y-%m-%d").date() + timedelta(days=int(l["dias_baja"]))
            jug_alta = l["jugador"]
            if jug_alta not in altas_medicas_dict or fecha_alta > altas_medicas_dict[jug_alta]:
                altas_medicas_dict[jug_alta] = fecha_alta

    for jug, vals in ewma_hoy.items():
        if jug in [b["jug"] for b in bajas_medicas]: continue
        
        ratio_int = vals.get("RATIO A/C", 1.0)
        aguda_int = vals.get("EWMA AGUDA", 0)
        ratio_hsr = vals.get("RATIO A/C HSR", 1.0)
        ratio_acc = vals.get("RATIO A/C ACC", 1.0)
        
        # 1. Picos de Carga y Desentrenamiento
        if aguda_int > 1500:
            if ratio_int >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Spike Carga: {ratio_int:.2f}", "lvl": "rojo"})
            elif ratio_int <= 0.8: alertas_carga.append({"jug": jug, "txt": f"Desentrenamiento: A/C {ratio_int:.2f}", "lvl": "amarillo"})
            
        if ratio_hsr >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Spike HSR: {ratio_hsr:.2f}", "lvl": "rojo"})
        if ratio_acc >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Spike Tensión: {ratio_acc:.2f}", "lvl": "rojo"})

        # 2. Eficiencia Metabólica y Neuromuscular (Cruzado con la última sesión del mismo MD)
        jug_l = limpiar_nombre(jug)
        if jug_l in ultimas_sesiones:
            d_ult = ultimas_sesiones[jug_l]["datos"]
            md_ult = ultimas_sesiones[jug_l].get("md", "TD")
            min_ses = safe_float(d_ult.get('MIN', 0))
            dis_ses = safe_float(d_ult.get('DIS', 0))
            rpe_ses = safe_float(d_ult.get('RPE', 0))
            es_virtual_ult = d_ult.get('GPS_VIRTUAL', False)
            
            if min_ses > 0 and dis_ses > 0 and rpe_ses > 0 and not es_virtual_ult:
                m_min_actual = (dis_ses * 1000) / min_ses
                mec_actual = safe_float(d_ult.get('ACC', 0)) + safe_float(d_ult.get('DCC', 0)) + safe_float(d_ult.get('Nº SPR', 0))
                
                efi_cardio = rpe_ses / m_min_actual if m_min_actual > 0 else 0
                efi_neuro = rpe_ses / mec_actual if mec_actual > 0 else 0
                
                st_efi = dict_zscore_efi.get((jug, md_ult), dict_zscore_efi.get(jug, {'cardio_mean': 0, 'cardio_std': 0.05, 'neuro_mean': 0, 'neuro_std': 0.05}))
                if st_efi['cardio_mean'] > 0 and st_efi['neuro_mean'] > 0:
                    z_cardio = (efi_cardio - st_efi['cardio_mean']) / st_efi['cardio_std']
                    z_neuro = (efi_neuro - st_efi['neuro_mean']) / st_efi['neuro_std']
                    
                    if z_cardio >= 1.5 and z_neuro >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Fatiga Integral (Cardio Z:+{z_cardio:.1f}, Neuro Z:+{z_neuro:.1f})", "lvl": "rojo"})
                    elif z_cardio >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Coste Cardio Z:+{z_cardio:.1f}", "lvl": "amarillo"})
                    elif z_neuro >= 1.5: alertas_carga.append({"jug": jug, "txt": f"Coste Neuro Z:+{z_neuro:.1f}", "lvl": "amarillo"})

        # 3. Riesgo de Burnout (Monotonía y Strain 7 días)
        monot, strain = calcular_monotonia_7d(st.session_state.sesiones, jug, hoy_str, devolver_strain=True)
        if monot > 2.0 and strain > 4000:
            alertas_carga.append({"jug": jug, "txt": f"Riesgo Burnout (Monotonía {monot:.1f})", "lvl": "rojo"})

        # 4. Vacuna de Velocidad
        if vmax_hist_dict.get(jug, 0) > 25.0:
            ult_fecha_str = ult_sprint_dict.get(jug)
            fecha_base_conteo = datetime.strptime(ult_fecha_str, "%Y-%m-%d").date() if ult_fecha_str else None
            
            alta_dt = altas_medicas_dict.get(jug)
            if alta_dt:
                if not fecha_base_conteo or alta_dt > fecha_base_conteo:
                    fecha_base_conteo = alta_dt
                    
            if fecha_base_conteo:
                dias_sin_sprint = (hoy_dt - fecha_base_conteo).days
                if dias_sin_sprint >= 10:
                    alertas_carga.append({"jug": jug, "txt": f"Sin >85% VMax: {dias_sin_sprint}d", "lvl": "rojo"})
                elif dias_sin_sprint >= 8:
                    alertas_carga.append({"jug": jug, "txt": f"Sin >85% VMax: {dias_sin_sprint}d", "lvl": "amarillo"})
            else:
                alertas_carga.append({"jug": jug, "txt": f"Falta estímulo VMax", "lvl": "amarillo"})

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
    alertas_medicas = [{"jug": b["jug"], "txt": b["txt"], "lvl": "rojo"} for b in bajas_medicas] + [{"jug": r["jug"], "txt": r["txt"], "lvl": "amarillo"} for r in readaptacion]

    def get_avatar_html(jugador_nombre):
        for p in st.session_state.get("plantilla", []):
            if limpiar_nombre(p["JUGADOR"]) == limpiar_nombre(jugador_nombre):
                if p.get("foto"):
                    img_src = p["foto"] if str(p["foto"]).startswith("http") else f"data:image/jpeg;base64,{p['foto']}"
                    return f"<img src='{img_src}' style='width:24px; height:24px; border-radius:50%; object-fit: cover; margin-right: 8px; border: 1px solid #111318;'>"
                break
        return "<span class='material-symbols-rounded' style='font-size: 20px; margin-right: 8px; vertical-align: middle;'>person</span>"

    def render_alertas_grid(alertas, nivel_predeterminado="verde"):
        if not alertas:
            return "<div style='color: #10b981; font-weight: 800; font-size: 0.95rem; padding: 20px 10px; text-align: center; margin-top: 10px;'><span class='material-symbols-rounded' style='vertical-align: text-bottom; font-size: 1.4rem; margin-right: 6px;'>check_circle</span> Sin alertas activas</div>"
        
        orden_niveles = {"rojo": 0, "amarillo": 1, "verde": 2}
        alertas_ordenadas = sorted(alertas, key=lambda x: orden_niveles.get(x.get("lvl", nivel_predeterminado), 3))
        
        # Eliminamos el scroll para que las tarjetas ocupen su tamaño natural completo
        html = "<div style='display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px;'>"
        
        for a in alertas_ordenadas:
            nivel = a.get("lvl", nivel_predeterminado)
            color = "#ef4444" if nivel == "rojo" else ("#f59e0b" if nivel == "amarillo" else "#10b981")
            bg = "rgba(239, 68, 68, 0.1)" if nivel == "rojo" else ("rgba(245, 158, 11, 0.1)" if nivel == "amarillo" else "rgba(16, 185, 129, 0.1)")
            avatar = get_avatar_html(a["jug"])
            
            html += f"<div style='background: {bg}; border: 1px solid {color}40; border-left: 4px solid {color}; padding: 12px 14px; border-radius: 8px; display: flex; flex-direction: column; box-shadow: 0 2px 6px rgba(0,0,0,0.15);'><div style='display: flex; align-items: center; margin-bottom: 6px;'>{avatar}<span style='color: #f8fafc; font-size: 0.95rem; font-weight: 800;'>{a['jug']}</span></div><span style='color: {color}; font-size: 0.85rem; font-weight: 800; line-height: 1.3;'>{a['txt']}</span></div>"
            
        html += "</div>"
        return html

    # Modificamos las proporciones: Menos contexto (0.9), mucho más espacio a las alertas (1.7)
    c_ctx, c_read, c_carga, c_med = st.columns([0.9, 1.7, 1.7, 1.7])

    with c_ctx:
        html_ctx = f"""
<div style="background: linear-gradient(135deg, #111318, #16191f); border: 1px solid rgba(197, 160, 89, 0.15); border-top: 4px solid #C5A059; border-radius: 8px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); height: 100%; display: flex; flex-direction: column; justify-content: center; text-align: center;">
<h2 style="color: #f8fafc; font-size: 1.5rem; font-weight: 800; margin: 0 0 10px 0;">{md_text}</h2>
<div style="color: #f8fafc; font-size: 1.1rem; font-weight: 800; margin-bottom: 2px;"><span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1.2rem; margin-right: 6px;">sports_score</span> {rival_text}</div>
<div style="color: #94a3b8; font-size: 0.8rem; font-weight: 600; margin-bottom: 12px;">{fecha_partido_text}</div>
<div style="color: #C5A059; font-size: 0.8rem; font-weight: 800; margin-top: auto; padding-top: 10px; border-top: 1px solid #111318;"><span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1rem; margin-right: 4px;">location_on</span> {ciudad_club} | {clima_str}</div>
</div>
"""
        st.markdown(html_ctx, unsafe_allow_html=True)
        # NUEVO BLOQUE: ÚLTIMOS 5 PARTIDOS
        partidos_jugados = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "") and s["fecha"] < hoy_str]
        partidos_jugados.sort(key=lambda x: x["fecha"], reverse=True)
        ultimos_5 = partidos_jugados[:5]
        
        html_ultimos = "<div style='margin-top: 12px;'><p style='color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 800; margin-bottom: 8px; letter-spacing: 0.5px;'>Últimos 5 Partidos</p>"
        
        if ultimos_5:
            for p in ultimos_5:
                gf = int(safe_float(p.get("goles_favor", 0)))
                gc = int(safe_float(p.get("goles_contra", 0)))
                rival = p.get("rival", "Rival")
                
                if gf > gc: color_res, letra = "#10b981", "V"
                elif gf < gc: color_res, letra = "#ef4444", "D"
                else: color_res, letra = "#f59e0b", "E"
                
                # Se construye en una sola línea continua para evitar el bug del parser Markdown de Streamlit
                html_ultimos += f"<div style='background: #111318; border: 1px solid #1c1f26; border-left: 3px solid {color_res}; border-radius: 6px; padding: 6px 10px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.15);'><div style='display: flex; align-items: center; gap: 8px; overflow: hidden;'><span style='color: {color_res}; font-weight: 900; font-size: 0.7rem; background: {color_res}20; padding: 2px 5px; border-radius: 4px;'>{letra}</span><span style='color: #94a3b8; font-size: 0.8rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>vs {rival}</span></div><span style='color: #f8fafc; font-size: 0.9rem; font-weight: 800; margin-left: 10px; flex-shrink: 0;'>{gf} - {gc}</span></div>"
        else:
            html_ultimos += "<div style='background: #111318; border: 1px solid #1c1f26; border-radius: 6px; padding: 10px; text-align: center;'><span style='color: #64748b; font-size: 0.75rem; font-weight: 700;'>Sin historial previo</span></div>"
            
        html_ultimos += "</div>"
        st.markdown(html_ultimos, unsafe_allow_html=True)
        
    with c_read:
        html_read = f"""
<div style="background: #111318; border: 1px solid #111318; border-top: 3px solid #f59e0b; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;"><span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1rem; margin-right: 4px;">psychology</span> Readiness & Bienestar</p>
{render_alertas_grid(alertas_readiness)}
</div>
"""
        st.markdown(html_read, unsafe_allow_html=True)

    with c_carga:
        html_carga = f"""
<div style="background: #111318; border: 1px solid #111318; border-top: 3px solid #ef4444; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;"><span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1rem; margin-right: 4px;">local_fire_department</span> Riesgo de Carga</p>
{render_alertas_grid(alertas_carga)}
</div>
"""
        st.markdown(html_carga, unsafe_allow_html=True)

    with c_med:
        html_med = f"""
<div style="background: #111318; border: 1px solid #111318; border-top: 3px solid #8b5cf6; border-radius: 8px; padding: 10px; height: 100%; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">
<p style="color: #f8fafc; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; margin: 0 0 10px 0;"><span class="material-symbols-rounded" style="vertical-align: text-bottom; font-size: 1rem; margin-right: 4px;">healing</span> Enfermería & RTP</p>
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
            
            # Agrupación interna ampliada
            cols_int = ['WELLNESS', 'TQR', 'CARGA']
            for factor in ['W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor']:
                if factor in df_sem.columns: cols_int.append(factor)
                
            df_diario_int = df_sem.groupby('FECHA')[cols_int].mean().reset_index()
            
            # Agrupación externa ampliada
            df_sem_gps = df_sem[df_sem['DIS'] > 0]
            if not df_sem_gps.empty:
                df_diario_ext = df_sem_gps.groupby('FECHA')[['DIS', 'DIS AI', 'ACC', 'DCC']].mean().reset_index()
            else:
                df_diario_ext = pd.DataFrame(columns=['FECHA', 'DIS', 'DIS AI', 'ACC', 'DCC'])
                
            df_diario = pd.merge(df_diario_int, df_diario_ext, on='FECHA', how='left').fillna(0)
            
            df_diario['DIA_NOMBRE'] = pd.to_datetime(df_diario['FECHA']).dt.weekday.map({
                0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
            })
            
            cg1, cg2, cg3 = st.columns(3)
            
            with cg1:
                fig_w = go.Figure()
                
                # Barras apiladas para factores de Wellness
                colores_w = px.colors.qualitative.Set2
                factores = ['W_Fatiga', 'W_Sueño', 'W_Dolor', 'W_Estres', 'W_Humor']
                nombres_w = ['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor']
                for i, factor in enumerate(factores):
                    if factor in df_diario.columns:
                        fig_w.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario[factor], name=nombres_w[i], marker_color=colores_w[i], yaxis="y1"))
                
                # Línea Dorada de TQR
                fig_w.add_trace(go.Scatter(x=df_diario['DIA_NOMBRE'], y=df_diario['TQR'], name="TQR", mode="lines+markers", line=dict(color="#C5A059", width=3), yaxis="y2"))
                
                fig_w.update_layout(title="Bienestar", barmode='stack', yaxis=dict(title="Puntos Wellness", range=[0, 35]), yaxis2=dict(title="TQR", overlaying="y", side="right", range=[0, 10]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_w, use_container_width=True)
                
            with cg2:
                fig_c = go.Figure()
                fig_c.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario['CARGA'], name="Carga (UA)", marker_color="#C5A059"))
                fig_c.update_layout(title="Carga Interna Acumulada", yaxis_title="UA", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_c, use_container_width=True)
                
            with cg3:
                fig_ext = go.Figure()
                if 'DIS' in df_diario.columns:
                    # Barra dorada sólida al 100% de opacidad
                    fig_ext.add_trace(go.Bar(x=df_diario['DIA_NOMBRE'], y=df_diario['DIS'], name="Distancia (km)", marker_color="#C5A059", opacity=1.0, yaxis="y1"))
                    
                    # Suma de tensión mecánica (ACC + DCC) en color verde de la app
                    df_diario['TENSION'] = df_diario['ACC'] + df_diario['DCC']
                    fig_ext.add_trace(go.Scatter(x=df_diario['DIA_NOMBRE'], y=df_diario['TENSION'], name="Tensión (ACC+DCC)", mode="lines+markers", line=dict(color="#10b981", width=3, dash="dot"), yaxis="y2"))
                    
                    # Línea plateada (e2e8f0) para HSR
                    fig_ext.add_trace(go.Scatter(x=df_diario['DIA_NOMBRE'], y=df_diario['DIS AI'], name="HSR (m)", mode="lines+markers", line=dict(color="#e2e8f0", width=3), yaxis="y2"))
                    
                fig_ext.update_layout(title="Carga Externa", yaxis=dict(title="km"), yaxis2=dict(title="HSR / Tensión", overlaying="y", side="right"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_ext, use_container_width=True)
        else:
            st.info("Aún no hay datos de sesión procesados para la semana actual.")
    else:
        st.info("No hay datos cargados en la base de datos de rendimiento para procesar gráficas.")
    
    # --- BOTÓN DE CONFIGURACIÓN ESTRECHO A LA DERECHA ---
    c_vacio, c_btn = st.columns([6, 1])
    with c_btn:
        if st.button(":material/settings: Configuración", use_container_width=True):
            st.session_state.mostrar_configuracion = not st.session_state.get("mostrar_configuracion", False)

    if st.session_state.get("mostrar_configuracion", False):
        render_panel_principal()
