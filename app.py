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
from fpdf import FPDF
import tempfile

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
from supabase import create_client

# Inicialización de Supabase con los secretos de Streamlit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# RESTAURAR SESIÓN PARA RLS
if "access_token" in st.session_state and "refresh_token" in st.session_state:
    try:
        supabase.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
    except:
        pass

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

def cargar_datos_equipo(equipo_id):
    try:
        # Extraer metadatos del equipo
        res_eq = supabase.table("equipos").select("*").eq("id", equipo_id).execute()
        # Extraer arrays de datos
        res_dat = supabase.table("datos_equipo").select("*").eq("equipo_id", equipo_id).execute()

        if res_eq.data and res_dat.data:
            eq = res_eq.data[0]
            dat = res_dat.data[0]
            
            st.session_state.equipo_creado = True
            st.session_state.equipo_id = equipo_id
            st.session_state.nombre_equipo = eq.get("nombre", "")
            st.session_state.categoria_equipo = eq.get("categoria", "")
            st.session_state.division_equipo = eq.get("division", "")
            st.session_state.temporada_equipo = eq.get("temporada", "")
            st.session_state.escudo_equipo = eq.get("escudo_base64", None)
            st.session_state.color_sidebar = eq.get("color_sidebar", "#f1f5f9") # Gris claro por defecto
            
            st.session_state.plantilla = dat.get("plantilla", [])
            st.session_state.sesiones = dat.get("sesiones", [])
            st.session_state.lesiones = dat.get("lesiones", [])
            st.session_state.antropometria = dat.get("antropometria", [])
            
            vals = dat.get("valoraciones", {})
            st.session_state.val_inicial = vals.get("val_inicial", [])
            st.session_state.val_rom = vals.get("val_rom", [])
            st.session_state.val_1rm = vals.get("val_1rm", [])
            
            st.session_state.datos_cargados = True
            return True
    except Exception as e:
        st.error(f"Error al cargar desde Supabase: {e}")
    return False

def guardar_datos():
    if "equipo_id" not in st.session_state:
        return
        
    eq_id = st.session_state.equipo_id
    
    try:
        # Guardar metadatos
        supabase.table("equipos").update({
            "nombre": st.session_state.nombre_equipo,
            "categoria": st.session_state.categoria_equipo,
            "division": st.session_state.division_equipo,
            "temporada": st.session_state.temporada_equipo,
            "escudo_base64": st.session_state.get("escudo_equipo", None),
            "color_sidebar": st.session_state.get("color_sidebar", "#f1f5f9") # <--- AÑADIR ESTA LÍNEA
        }).eq("id", eq_id).execute()
        
        # Guardar arrays
        data_json = {
            "plantilla": st.session_state.plantilla,
            "sesiones": st.session_state.sesiones,
            "lesiones": st.session_state.get("lesiones", []),
            "antropometria": st.session_state.get("antropometria", []),
            "valoraciones": {
                "val_inicial": st.session_state.get("val_inicial", []),
                "val_rom": st.session_state.get("val_rom", []),
                "val_1rm": st.session_state.get("val_1rm", [])
            }
        }
        supabase.table("datos_equipo").update(data_json).eq("equipo_id", eq_id).execute()
    except Exception as e:
        st.error(f"Error al guardar en Supabase: {e}")

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

def get_base64_of_bin_file(bin_file):
    if bin_file:
        return base64.b64encode(bin_file.read()).decode()
    return None

meses_esp = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

def categorizar_duracion(dias):
    if pd.isna(dias) or dias is None or dias == "": return "Activa"
    dias = int(dias)
    if dias <= 3: return "Mínima (1-3d)"
    if dias <= 7: return "Leve (4-7d)"
    if dias <= 28: return "Moderada (8-28d)"
    return "Grave (>28d)"
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

def generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, dict_figs):
    # Formato horizontal (Landscape)
    pdf = FPDF(orientation='L', unit='mm', format='A4') 
    pdf.set_auto_page_break(auto=True, margin=15)

    # CORRECCIÓN EMOJIS: 'ignore' elimina los caracteres especiales sin dejar '?'
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()

    # Paleta de colores
    C_PRIMARY = (41, 128, 185)
    C_BG_KPI = (240, 240, 240)
    C_BG_TAB_H = (220, 220, 220)
    C_BG_TAB_R = (248, 248, 248)

    # Guardar temporalmente las imágenes
    img_paths = {}
    for name, fig in dict_figs.items():
        if fig is not None:
            # 1. Forzar fondo blanco sólido
            fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            
            # 2. Cambiar a JPG para que FPDF no pierda los colores por la transparencia
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=750, height=450, format="jpg")
            img_paths[name] = tmp.name

    pdf.add_page()

    # --- PORTADA Y TÍTULO ---
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_txt(f"INFORME DE SESIÓN | {sesion['fecha']} | {sesion.get('tipo', '')}"), ln=True, align='C')
    pdf.ln(5)

    # --- KPIs GLOBALES ---
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi = 277 / 4 
    
    tqr_m = df_para_medias['TQR'].mean() if not df_para_medias.empty else 0
    well_m = df_para_medias['WELLNESS'].mean() if not df_para_medias.empty else 0
    rpe_m = df_para_medias['RPE'].mean() if not df_para_medias.empty else 0
    carga_m = df_para_medias['CARGA'].mean() if not df_para_medias.empty else 0

    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"TQR Medio (Recuperación)\n{tqr_m:.1f} / 10"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Wellness Medio (Fatiga)\n{well_m:.1f} pts"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"RPE Medio (Esfuerzo)\n{rpe_m:.1f} / 10"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Carga Media Sesión\n{carga_m:.0f} UA"), border=1, align='C', fill=True)
    pdf.ln(8)

    # --- SECCIÓN 1: BIENESTAR ---
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("1. Bienestar y Recuperación"), ln=True)
    pdf.set_text_color(0, 0, 0)

    y_img = pdf.get_y()
    if "Desglose de Wellness" in img_paths:
        pdf.image(img_paths["Desglose de Wellness"], x=10, y=y_img, w=135)
    if "Calidad de Recuperación (TQR)" in img_paths:
        pdf.image(img_paths["Calidad de Recuperación (TQR)"], x=150, y=y_img, w=135)
    
    # --- SECCIÓN 2: CARGA INTERNA ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("2. Carga Interna (RPE & Acumulada)"), ln=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi3 = 277 / 3
    y_kpi = pdf.get_y()
    min_m = df_para_medias['MIN'].mean() if not df_para_medias.empty else 0
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"Minutos Sesión (Media)\n{min_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi3, y_kpi)
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"RPE Medio\n{rpe_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi3*2, y_kpi)
    pdf.multi_cell(w_kpi3, 6, clean_txt(f"Carga Media (UA)\n{carga_m:.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_img = pdf.get_y()
    if "Carga de Sesión" in img_paths:
        pdf.image(img_paths["Carga de Sesión"], x=10, y=y_img, w=135)
    if "Riesgo de Lesión (Ratio A/C)" in img_paths:
        pdf.image(img_paths["Riesgo de Lesión (Ratio A/C)"], x=150, y=y_img, w=135)
    
    # Salto de página para la primera tabla
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    cols_ci = ['JUGADOR', 'POS', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']
    widths_ci = [45, 15, 25, 20, 15, 20, 30, 32, 25] 
    
    offset_x = (297 - sum(widths_ci)) / 2
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_ci):
        pdf.cell(widths_ci[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    row_count = 0
    for _, row in df_graficos.iterrows():
        pdf.set_x(offset_x)
        if row_count % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_ci):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:20]
            pdf.cell(widths_ci[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()
        row_count += 1

    # --- SECCIÓN 3: CARGA EXTERNA ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("3. Carga Externa (GPS) - Solo jugadores con GPS > 0m"), ln=True)
    pdf.set_text_color(0, 0, 0)

    df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0]
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi5 = 277 / 5
    y_kpi = pdf.get_y()
    
    dis_m = df_para_medias_gps['DIS'].mean() if not df_para_medias_gps.empty else 0
    hsr_m = df_para_medias_gps['DIS AI'].mean() if not df_para_medias_gps.empty else 0
    spr_m = df_para_medias_gps['Nº SPR'].mean() if not df_para_medias_gps.empty else 0
    acc_m = df_para_medias_gps['ACC'].mean() if not df_para_medias_gps.empty else 0
    dcc_m = df_para_medias_gps['DCC'].mean() if not df_para_medias_gps.empty else 0

    pdf.multi_cell(w_kpi5, 6, clean_txt(f"Distancia (km)\n{dis_m:.2f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"HSR (>21 km/h)\n{hsr_m:.2f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*2, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"Nº SPRINTS (>24)\n{spr_m:.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*3, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"ACC (>3 m/s²)\n{acc_m:.0f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi5*4, y_kpi)
    pdf.multi_cell(w_kpi5, 6, clean_txt(f"DCC (>3 m/s²)\n{dcc_m:.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_img = pdf.get_y()
    if "Volumen vs Intensidad" in img_paths:
        pdf.image(img_paths["Volumen vs Intensidad"], x=10, y=y_img, w=135)
    if "ACC vs DCC" in img_paths:
        pdf.image(img_paths["ACC vs DCC"], x=150, y=y_img, w=135)
    
    # Salto de página para la segunda tabla
    pdf.add_page()
    
    if 'HID >21' not in df_graficos.columns:
        df_graficos['HID >21'] = df_graficos.get('DIS AI', 0.0)

    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    cols_ce = ['JUGADOR', 'POS', 'ESTADO', 'DIS', 'HID >21', 'Nº SPR', 'ACC', 'DCC', 'VMAX']
    widths_ce = [45, 15, 25, 20, 25, 20, 20, 20, 20]
    
    offset_x = (297 - sum(widths_ce)) / 2
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_ce):
        pdf.cell(widths_ce[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    row_count = 0
    for _, row in df_graficos.iterrows():
        pdf.set_x(offset_x)
        if row_count % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_ce):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)[:20]
            pdf.cell(widths_ce[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()
        row_count += 1

    # --- SECCIÓN 4: ALERTAS MÉDICAS ---
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, clean_txt("Alertas de Rendimiento y Riesgo"), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)

    if not alertas_multi and not alertas_rec and not alertas_car:
        pdf.cell(0, 6, clean_txt("Todo en parámetros normales."), ln=True)
    else:
        if alertas_multi:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, clean_txt("RIESGO MULTIFACTORIAL (2 o más alertas simultáneas):"), ln=True)
            pdf.set_font("Arial", '', 10)
            for al in alertas_multi: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
            pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, clean_txt("Recuperación (1 alerta):"), ln=True)
        pdf.set_font("Arial", '', 10)
        if alertas_rec:
            for al in alertas_rec: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
        else:
            pdf.cell(0, 6, clean_txt("Sin alertas individuales."), ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, clean_txt("Carga (1 alerta):"), ln=True)
        pdf.set_font("Arial", '', 10)
        if alertas_car:
            for al in alertas_car: 
                pdf.set_x(15)
                pdf.multi_cell(260, 6, clean_txt(f"- {al.replace('**', '')}"))
        else:
            pdf.cell(0, 6, clean_txt("Sin alertas individuales."), ln=True)

    # Limpieza de imágenes temporales
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

import tempfile
import os
from fpdf import FPDF

def generar_pdf_microciclo(nombre_micro, df_diario, df_indiv, kpis_globales, dict_figs):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    def clean_txt(t): return str(t).encode('latin-1', 'ignore').decode('latin-1').strip()
    
    C_PRIMARY = (41, 128, 185)
    C_BG_KPI = (240, 240, 240)
    C_BG_TAB_H = (220, 220, 220)
    C_BG_TAB_R = (248, 248, 248)

    # Exportar gráficos de Plotly a JPG temporales
    img_paths = {}
    for name, fig in dict_figs.items():
        if fig is not None:
            fig.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.close()  
            fig.write_image(tmp.name, engine="kaleido", width=750, height=450, format="jpg")
            img_paths[name] = tmp.name

    pdf.add_page()

    # TÍTULO
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_txt(f"INFORME DE MICROCICLO | {nombre_micro}"), ln=True, align='C')
    pdf.ln(5)

    # BLOQUE DE KPIs
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(*C_BG_KPI)
    w_kpi = 277 / 5
    
    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Wellness Medio\n{kpis_globales.get('Wellness', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"TQR Medio\n{kpis_globales.get('TQR', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"RPE Medio\n{kpis_globales.get('RPE', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Minutos Totales\n{kpis_globales.get('Minutos', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*4, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Carga Total (UA)\n{kpis_globales.get('Carga', 0):.0f}"), border=1, align='C', fill=True)
    pdf.ln(8)

    y_kpi = pdf.get_y()
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Distancia Total\n{kpis_globales.get('DIS', 0):.2f} km"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"HSR Total\n{kpis_globales.get('HSR', 0):.2f} m"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*2, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"Sprints Totales\n{kpis_globales.get('SPR', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*3, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"ACC Totales\n{kpis_globales.get('ACC', 0):.1f}"), border=1, align='C', fill=True)
    pdf.set_xy(10 + w_kpi*4, y_kpi)
    pdf.multi_cell(w_kpi, 6, clean_txt(f"DCC Totales\n{kpis_globales.get('DCC', 0):.1f}"), border=1, align='C', fill=True)
    pdf.ln(10)

    # TABLA: RESUMEN POR DÍA
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Resumen por Día"), ln=True)
    pdf.set_text_color(0, 0, 0)
    
    cols_dia = ['DIA', 'WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_dia = [25, 25, 20, 20, 20, 25, 25, 25, 25, 25, 25] 
    offset_x = (297 - sum(widths_dia)) / 2
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    pdf.set_x(offset_x)
    for i, col in enumerate(cols_dia):
        pdf.cell(widths_dia[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    for r_idx, row in df_diario.iterrows():
        pdf.set_x(offset_x)
        if r_idx % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_dia):
            val = row.get(col, 0)
            val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
            pdf.cell(widths_dia[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()

    # SECCIÓN: GRÁFICOS DE BIENESTAR
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Bienestar"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    if "TQR" in img_paths: pdf.image(img_paths["TQR"], x=10, y=y_img, w=135)
    if "Wellness" in img_paths: pdf.image(img_paths["Wellness"], x=150, y=y_img, w=135)

    # SECCIÓN: GRÁFICOS DE CARGA INTERNA
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Carga Interna"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    w_img3 = 277 / 3
    if "Minutos" in img_paths: pdf.image(img_paths["Minutos"], x=10, y=y_img, w=w_img3)
    if "RPE" in img_paths: pdf.image(img_paths["RPE"], x=10 + w_img3, y=y_img, w=w_img3)
    if "Carga" in img_paths: pdf.image(img_paths["Carga"], x=10 + w_img3*2, y=y_img, w=w_img3)

    # SECCIÓN: GRÁFICOS DE CARGA EXTERNA
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Carga Externa (Solo datos GPS > 0m)"), ln=True)
    pdf.set_text_color(0, 0, 0)
    y_img = pdf.get_y()
    if "ACC_DCC" in img_paths: pdf.image(img_paths["ACC_DCC"], x=10, y=y_img, w=w_img3)
    if "DIS" in img_paths: pdf.image(img_paths["DIS"], x=10 + w_img3, y=y_img, w=w_img3)
    if "DIS_AI" in img_paths: pdf.image(img_paths["DIS_AI"], x=10 + w_img3*2, y=y_img, w=w_img3)

    # TABLA: RESUMEN SEMANAL POR JUGADOR
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, clean_txt("Resumen Semanal por Jugador"), ln=True)
    pdf.set_text_color(0, 0, 0)
    
    cols_indiv = ['JUGADOR', 'POS', 'MIN', 'TQR', 'WELLNESS', 'RPE', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
    widths_indiv = [40, 15, 15, 15, 22, 15, 20, 20, 20, 20, 20, 20] 
    offset_x_indiv = (297 - sum(widths_indiv)) / 2
    
    pdf.set_font("Arial", 'B', 8)
    pdf.set_fill_color(*C_BG_TAB_H)
    pdf.set_x(offset_x_indiv)
    for i, col in enumerate(cols_indiv):
        pdf.cell(widths_indiv[i], 6, clean_txt(col), border=1, fill=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 8)
    for r_idx, row in df_indiv.iterrows():
        pdf.set_x(offset_x_indiv)
        if r_idx % 2 == 0:
            pdf.set_fill_color(*C_BG_TAB_R)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        for i, col in enumerate(cols_indiv):
            val = row.get(col, 0)
            if isinstance(val, float):
                val_str = f"{val:.1f}" if col in ['TQR', 'WELLNESS', 'RPE', 'Nº SPR', 'ACC', 'DCC'] else f"{val:.2f}" if col in ['DIS', 'DIS AI'] else f"{val:.0f}"
            else:
                val_str = str(val)[:20]
            pdf.cell(widths_indiv[i], 6, clean_txt(val_str), border=1, align='C', fill=True)
        pdf.ln()

    # LIMPIEZA ARCHIVOS TEMPORALES
    for path in img_paths.values():
        if os.path.exists(path): os.unlink(path)

    out = pdf.output(dest='S')
    return out.encode('latin-1') if isinstance(out, str) else bytes(out)

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
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    col_izq, col_centro, col_der = st.columns([1.5, 2, 1.5])
    
    with col_centro:
        st.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 10px;'>Iniciar Sesión</h2>", unsafe_allow_html=True)
        
        email = st.text_input("Correo electrónico")
        password = st.text_input("Contraseña", type="password")
        
        if st.button("Entrar", use_container_width=True):
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
    st.markdown("### 📋 Selecciona tu Equipo")
    
    res_equipos = supabase.table("equipo_usuarios").select("equipo_id, equipos(nombre, categoria)").eq("usuario_id", st.session_state.usuario_id).execute()
    
    if res_equipos.data:
        for relacion in res_equipos.data:
            eq_info = relacion["equipos"]
            eq_id = relacion["equipo_id"]
            if st.button(f"⚽ {eq_info['nombre']} ({eq_info['categoria']})", key=f"btn_{eq_id}"):
                if cargar_datos_equipo(eq_id):
                    st.session_state.equipo_seleccionado = True
                    st.rerun()
    else:
        st.info("No tienes equipos asignados actualmente.")
        
    st.markdown("---")
    with st.expander("➕ Crear Nuevo Equipo"):
        with st.form("form_nuevo_equipo"):
            n_nombre = st.text_input("Nombre del Club / Equipo:")
            n_categoria = st.selectbox("Categoría:", ["Senior", "Juvenil", "Cadete", "Infantil", "Alevín", "Benjamín", "Prebenjamín", "Biberón"])
            n_division = st.text_input("División / Liga:")
            n_temporada = st.text_input("Temporada:", value="2026/2027")
            
            if st.form_submit_button("🚀 Crear y Acceder") and n_nombre:
                # 1. Crear el equipo en DB
                res_insert = supabase.table("equipos").insert({
                    "nombre": n_nombre, "categoria": n_categoria, 
                    "division": n_division, "temporada": n_temporada,
                    "created_by": st.session_state.usuario_id
                }).execute()
                
                nuevo_id = res_insert.data[0]['id']
                
                # 2. Vincular usuario como owner
                supabase.table("equipo_usuarios").insert({
                    "equipo_id": nuevo_id, "usuario_id": st.session_state.usuario_id, "rol": "owner"
                }).execute()
                
                # 3. Inicializar fila vacía en datos_equipo
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
# ENTRENAMIENTO
# ==========================================
if seccion_principal == "📅 Entrenamiento":
    st.subheader("📅 Entrenamiento")
    
    tab_cal, tab_temp, tab_micro, tab_ses = st.tabs(["🗓️ Calendario", "🏆 Temporada", "🔄 Microciclos", "📋 Sesiones"])
    
    with tab_cal:
        c_dia1, c_dia2 = st.columns([1, 2])
        with c_dia1:
            # Diccionarios para traducir los meses y días del selector al castellano
            meses_trad = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
            dias_trad = {0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves", 4: "viernes", 5: "sábado", 6: "domingo"}
            
            dia_clicado = st.date_input("Selecciona un día del calendario:", date.today())
            
            # Formateamos la fecha seleccionada a Día-Mes-Año en texto para los mensajes
            fecha_formateada = dia_clicado.strftime("%d-%m-%Y")
            
            sesiones_en_fecha = [s for s in st.session_state.sesiones if s["fecha"] == str(dia_clicado)]
            if sesiones_en_fecha: 
                st.success(f"¡Hay sesión programada para el {fecha_formateada}!")
            else:
                st.warning(f"No hay registros para el {fecha_formateada}.")
                with st.expander("➕ Generar Sesión"):
                    tipo_nuevo = st.selectbox("Tipo de Evento:", ["Entrenamiento", "Partido Oficial", "Partido Amistoso"])
                    
                    desc_nuevo = ""
                    comp_nuevo = ""
                    rival_nuevo = ""
                    
                    if tipo_nuevo == "Entrenamiento":
                        desc_nuevo = st.selectbox("Match Day:", ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD+1", "MD+2", "TD"])
                    elif tipo_nuevo == "Partido Oficial":
                        comp_nuevo = st.selectbox("Competición:", ["Liga", "Copa"])
                        rival_nuevo = st.text_input("Rival:")
                    elif tipo_nuevo == "Partido Amistoso":
                        rival_nuevo = st.text_input("Rival:")
                        
                    if st.button("Guardar Sesión"):
                        st.session_state.sesiones.append({
                            "fecha": str(dia_clicado), 
                            "tipo": tipo_nuevo, 
                            "descripcion": desc_nuevo,
                            "competicion": comp_nuevo,
                            "rival": rival_nuevo,
                            "disponibilidad": {},
                            "informe_generado": False, 
                            "datos_informe": []
                        })
                        guardar_datos()
                        st.success("¡Evento creado en el calendario!")
                        st.rerun()
        with c_dia2:
            if st.session_state.sesiones:
                df_s = pd.DataFrame(st.session_state.sesiones).sort_values("fecha", ascending=False)
                df_s["Sesión"] = df_s.apply(lambda row: row.get("nombre_dinamico", row["tipo"]), axis=1)
                df_s["MD / Rival"] = df_s.apply(lambda row: row.get("subtitulo_dinamico", row.get("descripcion", "")), axis=1)
                df_s["Fecha"] = df_s["fecha"]
                mostrar_tabla_moderna(df_s[["Fecha", "Sesión", "MD / Rival"]].style.hide(axis="index"))

        # --- IMPORTADOR MASIVO DE HISTÓRICO ---
        st.markdown("---")
        with st.expander("📥 Importar Histórico Masivo (Excel de Temporada)"):
            st.caption("Sube tu archivo Excel con todo el histórico. El sistema creará o actualizará las sesiones automáticamente y añadirá a los jugadores nuevos si no existen.")
            archivo_historico = st.file_uploader("Sube el Excel de histórico:", type=["xlsx"])
            if st.button("🚀 Procesar Histórico Masivo") and archivo_historico is not None:
                try:
                    df_hist = pd.read_excel(archivo_historico)
                    df_hist_valid = df_hist[df_hist['JUGADOR'] != 0].copy()
                    df_hist_valid['FECHA_STR'] = pd.to_datetime(df_hist_valid['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                    df_hist_valid = df_hist_valid.dropna(subset=['FECHA_STR'])
                    
                    sesiones_creadas_count = 0
                    for fecha_str, grupo in df_hist_valid.groupby('FECHA_STR'):
                        sesion_obj = next((s for s in st.session_state.sesiones if s["fecha"] == fecha_str), None)
                        if not sesion_obj:
                            sesion_obj = {
                                "fecha": fecha_str,
                                "tipo": "Entrenamiento",
                                "descripcion": "TD",
                                "competicion": "",
                                "rival": "",
                                "disponibilidad": {},
                                "informe_generado": True,
                                "datos_informe": []
                            }
                            st.session_state.sesiones.append(sesion_obj)
                            sesiones_creadas_count += 1
                        else:
                            sesion_obj["informe_generado"] = True
                            
                        registros_sesion = []
                        for idx, row in grupo.iterrows():
                            jug_nombre = str(row['JUGADOR']).strip()
                            if pd.isna(row['JUGADOR']) or jug_nombre == "" or jug_nombre == "nan": continue
                            
                            match_p = next((p for p in st.session_state.plantilla if limpiar_nombre(p['JUGADOR']) == limpiar_nombre(jug_nombre)), None)
                            if not match_p:
                                st.session_state.plantilla.append({
                                    "JUGADOR": jug_nombre,
                                    "POS": "DEF",
                                    "edad": 20,
                                    "pos_1": "Central",
                                    "pos_2": "Ninguna",
                                    "dorsal": 99,
                                    "altura": 180,
                                    "lateralidad": "Diestro",
                                    "foto": None
                                })
                                
                            fatiga = get_col(row, ['FATIGA', 'Fatiga'])
                            sueño = get_col(row, ['SUEÑO', 'Sueño', 'SUENO'])
                            dolor = get_col(row, ['DOLOR', 'Dolor'])
                            estres = get_col(row, ['ESTRÉS', 'Estrés', 'ESTRES'])
                            humor = get_col(row, ['HUMOR', 'Humor'])
                            well_sum = fatiga + sueño + dolor + estres + humor
                            
                            min_sesion = get_col(row, ['MINUTOS SESIÓN', 'MINUTOS SESION', 'Minutos Sesión'])
                            min_gps = get_col(row, ['MINUTOS GPS', 'Time Played', 'Minutos GPS'])
                            rpe = get_col(row, ['RPE'])
                            
                            dis = get_col(row, ['DISTANCIA', 'Distance (km)'])
                            
                            # Si el jugador no llevó GPS (distancia = 0) o min gps = 0, se anulan sus métricas de GPS
                            if min_gps > 0 and dis > 0:
                                dis_ai_21 = get_col(row, ['DISTANCIA AI >21', 'HID distance (> 21.00 km/h)'])
                                dis_ai_24 = get_col(row, ['DISTANCIA AI >24', 'HID distance (> 24.00 km/h)'])
                                spr_24 = get_col(row, ['SPRINTS >24', '# of Sprints (> 24.00 km/h)'])
                                spr_27 = get_col(row, ['SPRINTS >27'])
                                v_med = get_col(row, ['V.MEDIA', 'V. MEDIA', 'Avg Speed (km/h)'])
                                v_max = get_col(row, ['V. MÁXIMA', 'Max Speed (km/h)'])
                                acc_max = get_col(row, ['ACC. MÁXIMA'])
                                acc_2 = get_col(row, ['ACC >2 m/s', '# of Accelerations (> 2.00 m/s²)'])
                                acc_3 = get_col(row, ['ACC >3 m/s', '# of Accelerations (> 3.00 m/s²)'])
                                acc_4 = get_col(row, ['ACC >4 m/s', '# of Accelerations (> 4.00 m/s²)'])
                                dcc_2 = get_col(row, ['DCC >2 m/s', '# of Decelerations (> 2.00 m/s²)'])
                                dcc_3 = get_col(row, ['DCC >3 m/s', '# of Decelerations (> 3.00 m/s²)'])
                                dcc_4 = get_col(row, ['DCC >4 m/s', '# of Decelerations (> 4.00 m/s²)'])
                                r_0_7 = get_col(row, ['DISTANCIA 0-7 KM/H', 'Distance Speed Range (0 - 7 km)'])
                                r_7_14 = get_col(row, ['DISTANCIA 7-14 KM/H', 'Distance Speed Range (7 - 14 km)'])
                                r_14_21 = get_col(row, ['DISTANCIA 14-21 KM/H', 'Distance Speed Range (14 - 21 km)'])
                                r_21_24 = get_col(row, ['DISTANCIA 21-24 KM/H', 'Distance Speed Range (21 - 24 km)'])
                                r_24_27 = get_col(row, ['DISTANCIA 24-27 KM/H', 'Distance Speed Range (24 - 27 km)'])
                                r_27_30 = get_col(row, ['DISTANCIA 27-30 KM/H', 'Distance Speed Range (27 - 30 km)'])
                                r_30 = get_col(row, ['DISTANCIA >30 KM/H', 'Distance Speed Range (30 - 45 km)'])
                            else:
                                dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_27 = v_med = v_max = acc_max = acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = r_30 = 0.0
                                min_gps = 0.0

                            rec = {
                                "JUGADOR": jug_nombre,
                                "POS": next((p['POS'] for p in st.session_state.plantilla if limpiar_nombre(p['JUGADOR']) == limpiar_nombre(jug_nombre)), "DEF"),
                                "TQR": get_col(row, ['TQR']),
                                "WELLNESS": well_sum,
                                "W_Humor": humor, "W_Sueño": sueño, "W_Fatiga": fatiga, "W_Dolor": dolor, "W_Estres": estres,
                                "RPE": rpe,
                                "MIN": min_sesion,
                                "MIN_GPS": min_gps,
                                "CARGA": min_sesion * rpe,
                                
                                # Formato Standard (Para Dashboards Globales)
                                "DIS": dis,
                                "DIS AI": dis_ai_21,
                                "Nº SPR": spr_24,
                                "ACC": acc_3,
                                "DCC": dcc_3,
                                "VMAX": v_max,
                                "Z1": r_0_7 + r_7_14,
                                "Z2": r_14_21,
                                "Z3": r_21_24,
                                "Z4": r_24_27,
                                "Z5": r_27_30,
                                "Z6": r_30,
                                
                                # Formato Extendido Exacto (Para la Tabla de Carga Manual y Mapeo Estricto)
                                "HID >21": dis_ai_21,
                                "HID >24": dis_ai_24,
                                "SPR >24": spr_24,
                                "SPR >27": spr_27,
                                "V_Med": v_med,
                                "V_Max": v_max,
                                "ACC_Max": acc_max,
                                "ACC >2": acc_2,
                                "ACC >3": acc_3,
                                "ACC >4": acc_4,
                                "DCC >2": dcc_2,
                                "DCC >3": dcc_3,
                                "DCC >4": dcc_4,
                                "R_0_7": r_0_7,
                                "R_7_14": r_7_14,
                                "R_14_21": r_14_21,
                                "R_21_24": r_21_24,
                                "R_24_27": r_24_27,
                                "R_27_30": r_27_30,
                                "R_30_45": r_30
                            }
                            registros_sesion.append(rec)
                            
                        sesion_obj["datos_informe"] = registros_sesion
                        
                    guardar_datos()
                    st.success(f"✅ ¡Histórico importado correctamente! Se procesaron {len(df_hist_valid)} registros en total.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo histórico: {e}")

    with tab_temp:
        st.markdown("### 🏆 Evolución de la Temporada")
        if not st.session_state.sesiones:
            st.info("No hay datos suficientes para generar el informe de temporada.")
        else:
            lista_micro = []
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    num_sem = obtener_numero_semana(s["fecha"])
                    _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
                    lista_micro.append({"num_semana": num_sem, "lunes_dt": lunes})
            
            if not lista_micro:
                st.warning("Debes procesar datos en las sesiones para ver la evolución de la temporada.")
            else:
                df_m = pd.DataFrame(lista_micro).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
                
                kpis_temporada = []
                for i, row in df_m.iterrows():
                    num_sem = row["num_semana"]
                    nombre_micro = f"Microciclo {i+1}"
                    ses_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem and s.get("informe_generado", False)]
                    datos_acum = []
                    for s in ses_sem:
                        disp_s = s.get("disponibilidad", {})
                        disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                        
                        for d in s["datos_informe"]:
                            jug_name = d["JUGADOR"]
                            est_jug = disp_s_clean.get(limpiar_nombre(jug_name), "Disponible")
                            
                            # EXCLUSIÓN PARA MEDIAS DE CARGA INTERNA: Ni lesionados, ni readaptación, ni no disponibles
                            if est_jug in ["Disponible", "Titular", "Suplente"]:
                                datos_acum.append({
                                    "JUGADOR": jug_name, "DIA": s["fecha"],
                                    "TQR": safe_float(d.get("TQR")), "WELLNESS": safe_float(d.get("WELLNESS")),
                                    "RPE": safe_float(d.get("RPE")), "MIN": safe_float(d.get("MIN")),
                                    "CARGA": safe_float(d.get("CARGA")), "DIS": safe_float(d.get("DIS")),
                                    "DIS AI": safe_float(d.get("HID >21", d.get("DIS AI", 0))), 
                                    "Nº SPR": safe_float(d.get("SPR >24", d.get("Nº SPR", 0))),
                                    "ACC": safe_float(d.get("ACC >3", d.get("ACC", 0))), 
                                    "DCC": safe_float(d.get("DCC >3", d.get("DCC", 0)))
                                })
                    df_sem = pd.DataFrame(datos_acum)
                    if not df_sem.empty:
                        # Reemplazar 0 por NaN en encuestas para que los no-rellenados no bajen la media
                        df_sem['TQR'] = df_sem['TQR'].replace(0, np.nan)
                        df_sem['WELLNESS'] = df_sem['WELLNESS'].replace(0, np.nan)
                        df_sem['RPE'] = df_sem['RPE'].replace(0, np.nan)
                        
                        df_jug_sum_int = df_sem.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
                        
                        # PARA GPS: SOLO LOS QUE TIENEN DISTANCIA > 0
                        df_sem_gps = df_sem[df_sem['DIS'] > 0]
                        if not df_sem_gps.empty:
                            df_jug_sum_ext = df_sem_gps.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].sum().reset_index()
                        else:
                            df_jug_sum_ext = pd.DataFrame(columns=['JUGADOR', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                            
                        df_no_ceros = df_sem.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                        df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE']].mean().reset_index().fillna(0)
                        
                        kpis_temporada.append({
                            "ID": i+1,
                            "Microciclo": nombre_micro,
                            "Wellness": df_jug_mean['WELLNESS'].mean(),
                            "TQR": df_jug_mean['TQR'].mean(),
                            "RPE": df_jug_mean['RPE'].mean(),
                            "Minutos": df_jug_sum_int['MIN'].mean() if not df_jug_sum_int.empty else 0,
                            "Carga (UA)": df_jug_sum_int['CARGA'].mean() if not df_jug_sum_int.empty else 0,
                            "DIS (km)": df_jug_sum_ext['DIS'].mean() if not df_jug_sum_ext.empty else 0,
                            "DIS AI (m)": df_jug_sum_ext['DIS AI'].mean() if not df_jug_sum_ext.empty else 0,
                            "Nº Sprints": df_jug_sum_ext['Nº SPR'].mean() if not df_jug_sum_ext.empty else 0,
                            "ACC": df_jug_sum_ext['ACC'].mean() if not df_jug_sum_ext.empty else 0,
                            "DCC": df_jug_sum_ext['DCC'].mean() if not df_jug_sum_ext.empty else 0
                        })
                
                if not kpis_temporada:
                    st.warning("No hay suficientes datos de jugadores disponibles (sin contar lesiones/readaptación/no disponibles) para generar la temporada.")
                else:
                    df_temporada = pd.DataFrame(kpis_temporada)
                    
                    st.markdown("#### 🎯 Promedios")
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Wellness", f"{df_temporada['Wellness'].mean():.1f}")
                    c2.metric("TQR", f"{df_temporada['TQR'].mean():.1f}")
                    c3.metric("RPE", f"{df_temporada['RPE'].mean():.1f}")
                    c4.metric("Minutos", f"{df_temporada['Minutos'].mean():.1f}")
                    c5.metric("Carga media (UA)", f"{df_temporada['Carga (UA)'].mean():.0f}")
                    
                    c6, c7, c8, c9, c10 = st.columns(5)
                    c6.metric("Distancia (km)", f"{df_temporada['DIS (km)'].mean():.2f}")
                    c7.metric("HSR (>21 km/h)", f"{df_temporada['DIS AI (m)'].mean():.2f}")
                    c8.metric("N.º Sprints (>24 km/h)", f"{df_temporada['Nº Sprints'].mean():.1f}")
                    c9.metric("ACC (>3 m/s²)", f"{df_temporada['ACC'].mean():.1f}")
                    c10.metric("DCC (>3 m/s²)", f"{df_temporada['DCC'].mean():.1f}")
                    
                    st.markdown("---")
                    st.markdown("#### 📋 Resumen por Microciclo")
                    cols_order = ["Microciclo", "Wellness", "TQR", "RPE", "Minutos", "Carga (UA)", "DIS (km)", "DIS AI (m)", "Nº Sprints", "ACC", "DCC"]
                    mostrar_tabla_moderna(df_temporada[cols_order].sort_values("Microciclo", ascending=False).style.hide(axis="index").format(precision=1))

                    st.markdown("---")
                    st.markdown("#### 🧠 Bienestar")
                    cg_b1, cg_b2 = st.columns(2)
                    with cg_b1:
                        fig_tqr = px.bar(
                            df_temporada, x='Microciclo', y='TQR', 
                            color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10],
                            title="Evolución TQR"
                        )
                        fig_tqr.update_yaxes(range=[1, 10])
                        st.plotly_chart(fig_tqr, use_container_width=True, key="temp_tqr_bar")
                    with cg_b2:
                        # Extraer los componentes de wellness directamente del DataFrame de temporada o recalculando con los datos filtrados válidos del microciclo
                        datos_w_temp = []
                        for i, row in df_temporada.iterrows():
                            m_id = row["Microciclo"]
                            num_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == row.get("num_semana", obtener_numero_semana(st.session_state.sesiones[0]["fecha"]))] # fallback seguro
                            # Buscamos las sesiones de esta semana directamente por el número de semana guardado en el bucle principal de temporada
                            num_sem_val = None
                            # Recuperamos el num_semana correcto de df_m original
                            for m_item in lista_micro:
                                # Relacionamos por índice o nombre
                                pass
                            
                            # Forma más directa y robusta usando las fechas del microciclo acumuladas:
                            ses_sem = [s for s in st.session_state.sesiones if f"Microciclo {i+1}" == m_id and s.get("informe_generado", False)]
                            # Si no coincide exactamente por el texto, filtramos por el número de semana de df_m correspondiente a este índice i:
                            num_sem_real = df_m.iloc[i]["num_semana"]
                            ses_sem = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem_real and s.get("informe_generado", False)]
                            
                            f, s_lista, d_lista, e, h = [], [], [], [], []
                            for ses in ses_sem:
                                disp_s = ses.get("disponibilidad", {})
                                disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                                for d_jug in ses["datos_informe"]:
                                    jug_name = d_jug["JUGADOR"]
                                    est_jug = disp_s_clean.get(limpiar_nombre(jug_name), "Disponible")
                                    # Mismo filtro estricto de exclusión que en las tablas y métricas
                                    if est_jug in ["Disponible", "Titular", "Suplente"] and safe_float(d_jug.get("WELLNESS")) > 0:
                                        f.append(safe_float(d_jug.get("W_Fatiga")))
                                        s_lista.append(safe_float(d_jug.get("W_Sueño")))
                                        d_lista.append(safe_float(d_jug.get("W_Dolor")))
                                        e.append(safe_float(d_jug.get("W_Estres")))
                                        h.append(safe_float(d_jug.get("W_Humor")))
                            
                            datos_w_temp.append({
                                "Microciclo": m_id, 
                                "Fatiga": np.mean(f) if f else 0, 
                                "Sueño": np.mean(s_lista) if s_lista else 0, 
                                "Dolor": np.mean(d_lista) if d_lista else 0, 
                                "Estrés": np.mean(e) if e else 0, 
                                "Humor": np.mean(h) if h else 0
                            })
                        
                        df_well_temp = pd.DataFrame(datos_w_temp)
                        
                        fig_well = px.bar(
                            df_well_temp, x='Microciclo', y=['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor'],
                            title="Evolución Wellness por Componentes", color_discrete_sequence=px.colors.qualitative.Set2,
                            labels={'value': 'Puntos', 'variable': 'Factor', 'Microciclo': ''}
                        )
                        fig_well.update_layout(barmode='stack', yaxis_range=[5, 35])
                        fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                        fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                        st.plotly_chart(fig_well, use_container_width=True, key="temp_well_bar")

                    st.markdown("---")
                    st.markdown("#### 🔥 Carga Interna")
                    cg_i1, cg_i2, cg_i3 = st.columns(3)
                    with cg_i1:
                        fig_min = px.bar(df_temporada, x='Microciclo', y='Minutos', title="Evolución Minutos de Sesión", color_discrete_sequence=["#00b4d8"])
                        st.plotly_chart(fig_min, use_container_width=True, key="temp_min_bar")
                    with cg_i2:
                        fig_rpe = px.bar(
                            df_temporada, x='Microciclo', y='RPE', 
                            color='RPE', color_continuous_scale="Reds", range_color=[0, 10],
                            title="Evolución RPE"
                        )
                        fig_rpe.update_yaxes(range=[1, 10])
                        st.plotly_chart(fig_rpe, use_container_width=True, key="temp_rpe_bar")
                    with cg_i3:
                        min_c_temp = df_temporada['Carga (UA)'].min() * 0.9 if not df_temporada.empty else 0.0
                        max_c_temp = df_temporada['Carga (UA)'].max() * 1.1 if not df_temporada.empty else 1000.0

                        fig_carga = px.bar(
                            df_temporada, x='Microciclo', y='Carga (UA)', 
                            color='Carga (UA)', color_continuous_scale="Reds", 
                            range_color=[min_c_temp, max_c_temp],
                            title="Evolución Carga (Aguda)"
                        )
                        fig_carga.update_yaxes(range=[min_c_temp, max_c_temp])
                        st.plotly_chart(fig_carga, use_container_width=True, key="temp_carga_bar")

    with tab_micro:
        if not st.session_state.sesiones:
            st.info("Genera sesiones en el calendario para calcular los microciclos automáticamente.")
        else:
            lista_micro = []
            for s in st.session_state.sesiones:
                if s.get("informe_generado", False):
                    num_sem = obtener_numero_semana(s["fecha"])
                    _, _, lunes, domingo = obtener_rango_fechas_semana(s["fecha"])
                    lista_micro.append({"num_semana": num_sem, "ini": lunes.strftime("%d/%m"), "fin": domingo.strftime("%d/%m"), "lunes_dt": lunes, "domingo_dt": domingo})
            
            if not lista_micro:
                st.warning("Debes cargar y procesar datos en al menos una sesión para poder generar informes semanales.")
            else:
                df_m = pd.DataFrame(lista_micro).drop_duplicates(subset=["num_semana"]).sort_values("lunes_dt", ascending=True).reset_index(drop=True)
                
                for idx_real, row in df_m.sort_values(by="lunes_dt", ascending=False).iterrows():
                    num_sem = row["num_semana"]
                    nombre_etiqueta = f"📦 Microciclo {idx_real + 1} | Semana del {row['ini']} al {row['fin']}"
                    
                    with st.expander(nombre_etiqueta, expanded=False):
                        sesiones_semana = [s for s in st.session_state.sesiones if obtener_numero_semana(s["fecha"]) == num_sem and s.get("informe_generado", False)]
                        rol_semanal = {j["JUGADOR"]: "Sin Partido" for j in st.session_state.plantilla}
                        hubo_partido = False
                        for s in sesiones_semana:
                            if "Partido" in s['tipo']:
                                hubo_partido = True
                                disp = s.get("disponibilidad", {})
                                disp_clean = {limpiar_nombre(k): v for k, v in disp.items()}
                                for j in st.session_state.plantilla:
                                    if disp_clean.get(limpiar_nombre(j["JUGADOR"]), "") == "Titular":
                                        rol_semanal[j["JUGADOR"]] = "Titular"
                        if hubo_partido:
                            for k in rol_semanal.keys():
                                if rol_semanal[k] == "Sin Partido": rol_semanal[k] = "Suplente"

                        datos_7_dias = []
                        for offset in range(7):
                            dia_actual = row["lunes_dt"] + timedelta(days=offset)
                            fecha_str = dia_actual.strftime("%Y-%m-%d")
                            dia_semana_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][offset]
                            sesion_dia = next((s for s in sesiones_semana if s["fecha"] == fecha_str), None)
                            
                            for j in st.session_state.plantilla:
                                jugador = j["JUGADOR"]
                                if sesion_dia:
                                    disp_s = sesion_dia.get("disponibilidad", {})
                                    disp_s_clean = {limpiar_nombre(k): v for k, v in disp_s.items()}
                                    est_jug = disp_s_clean.get(limpiar_nombre(jugador), "Disponible")
                                    d_jug = next((d for d in sesion_dia["datos_informe"] if limpiar_nombre(d["JUGADOR"]) == limpiar_nombre(jugador)), None)
                                    
                                    if d_jug:
                                        datos_7_dias.append({
                                            "JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador],
                                            "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": est_jug,
                                            "TQR": safe_float(d_jug.get("TQR")), "WELLNESS": safe_float(d_jug.get("WELLNESS")),
                                            "RPE": safe_float(d_jug.get("RPE")), "MIN": safe_float(d_jug.get("MIN")),
                                            "CARGA": safe_float(d_jug.get("CARGA")),
                                            "DIS": safe_float(d_jug.get("DIS")),
                                            "DIS AI": safe_float(d_jug.get("HID >21", d_jug.get("DIS AI", 0))),
                                            "Nº SPR": safe_float(d_jug.get("SPR >24", d_jug.get("Nº SPR", 0))),
                                            "ACC": safe_float(d_jug.get("ACC >3", d_jug.get("ACC", 0))),
                                            "DCC": safe_float(d_jug.get("DCC >3", d_jug.get("DCC", 0))),
                                            "VMAX": safe_float(d_jug.get("V_Max", d_jug.get("VMAX", 0))), 
                                            "ENTRENO": 1 # Anclaje clave para promediar solo a los que entrenaron
                                        })
                                    else:
                                        # Si no está en datos_informe, no promediará
                                        datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": est_jug, "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})
                                else:
                                    datos_7_dias.append({"JUGADOR": jugador, "POS": j["POS"], "ROL": rol_semanal[jugador], "FECHA": fecha_str, "DIA": dia_semana_nombre, "ESTADO": "Sin Sesión", "TQR": 0, "WELLNESS": 0, "RPE": 0, "MIN": 0, "CARGA": 0, "DIS": 0, "DIS AI": 0, "Nº SPR": 0, "ACC": 0, "DCC": 0, "VMAX": 0, "ENTRENO": 0})

                        df_semana = pd.DataFrame(datos_7_dias)

                        col_f1, col_f2 = st.columns(2)
                        with col_f1: pos_filtro = st.radio("Filtrar Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"fw_p_{num_sem}")
                        with col_f2: rol_filtro = st.radio("Filtrar Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"fw_r_{num_sem}")
                        
                        df_filtrado = df_semana.copy()
                        if pos_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["POS"] == pos_filtro]
                        if rol_filtro != "TODOS": df_filtrado = df_filtrado[df_filtrado["ROL"] == rol_filtro]

                        if df_filtrado.empty:
                            st.warning("No hay jugadores que coincidan con estos filtros en esta semana.")
                        else:
                            # FILTRO EXCLUSIÓN DIARIO PARA MEDIAS DEL EQUIPO (Sincronizado con el Informe)
                            df_disp = df_filtrado[(df_filtrado['ESTADO'].isin(["Disponible", "Titular", "Suplente"])) & (df_filtrado['ENTRENO'] == 1)].copy()
                            
                            df_disp['TQR'] = df_disp['TQR'].replace(0, np.nan)
                            df_disp['WELLNESS'] = df_disp['WELLNESS'].replace(0, np.nan)
                            df_disp['RPE'] = df_disp['RPE'].replace(0, np.nan)
                            
                            if not df_disp.empty:
                                df_diario_int = df_disp.groupby('DIA', sort=False)[['WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA']].mean().reset_index()
                                df_disp_gps = df_disp[df_disp['DIS'] > 0]
                                if not df_disp_gps.empty:
                                    df_diario_ext = df_disp_gps.groupby('DIA', sort=False)[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].mean().reset_index()
                                else:
                                    df_diario_ext = pd.DataFrame(columns=['DIA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                                
                                df_diario = pd.merge(df_diario_int, df_diario_ext, on='DIA', how='left').fillna(0)
                            else:
                                df_diario = pd.DataFrame(columns=['DIA', 'WELLNESS', 'TQR', 'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])

                            orden_dias = {"Lunes":1, "Martes":2, "Miércoles":3, "Jueves":4, "Viernes":5, "Sábado":6, "Domingo":7}
                            df_diario["Orden"] = df_diario["DIA"].map(orden_dias)
                            df_diario = df_diario.sort_values("Orden").drop(columns=["Orden"])

                            st.markdown("#### 🎯 Resumen del Microciclo")
                            c1, c2, c3, c4, c5 = st.columns(5)
                            c1.metric("Wellness medio", f"{df_diario['WELLNESS'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c2.metric("TQR medio", f"{df_diario['TQR'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c3.metric("RPE medio", f"{df_diario['RPE'].replace(0, np.nan).mean():.1f}" if not df_diario.empty else "0")
                            c4.metric("Minutos totales", f"{df_diario['MIN'].sum():.1f}" if not df_diario.empty else "0")
                            c5.metric("Carga total (UA)", f"{df_diario['CARGA'].sum():.0f}" if not df_diario.empty else "0")
                            
                            c6, c7, c8, c9, c10 = st.columns(5)
                            c6.metric("Distancia total", f"{df_diario['DIS'].sum():.2f}" if not df_diario.empty else "0")
                            c7.metric("HSR total (>21 km/h)", f"{df_diario['DIS AI'].sum():.2f}" if not df_diario.empty else "0")
                            c8.metric("Sprints totales (>24 km/h)", f"{df_diario['Nº SPR'].sum():.1f}" if not df_diario.empty else "0")
                            c9.metric("ACC totales (>3 m/s²)", f"{df_diario['ACC'].sum():.1f}" if not df_diario.empty else "0")
                            c10.metric("DCC totales (>3 m/s²)", f"{df_diario['DCC'].sum():.1f}" if not df_diario.empty else "0")

                            st.markdown("---")
                            st.markdown("#### 📋 Resumen por Día")
                            if not df_diario.empty:
                                mostrar_tabla_moderna(df_diario.style.hide(axis="index").format(precision=2))

                            st.markdown("---")
                            st.markdown("#### 🧠 Bienestar")
                            cg_b1, cg_b2 = st.columns(2)
                            with cg_b1:
                                df_tqr_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                fig_tqr = px.bar(
                                    df_tqr_plot, x='DIA', y='TQR', 
                                    color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10],
                                    title="Calidad de Recuperación (TQR)"
                                )
                                fig_tqr.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_tqr.update_yaxes(range=[1, 10])
                                st.plotly_chart(fig_tqr, use_container_width=True, key=f"micro_tqr_{num_sem}_{idx_real}")
                            with cg_b2:
                                datos_w = []
                                for offset in range(7):
                                    dia_n = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][offset]
                                    f_str = (row["lunes_dt"] + timedelta(days=offset)).strftime("%Y-%m-%d")
                                    ses = next((s for s in sesiones_semana if s["fecha"] == f_str), None)
                                    
                                    f_val = s_val = d_val = e_val = h_val = 0.0
                                    if ses and ses.get("datos_informe"):
                                        j_validos = df_disp[df_disp['DIA'] == dia_n]['JUGADOR'].tolist()
                                        d_validos = [d for d in ses["datos_informe"] if d["JUGADOR"] in j_validos and safe_float(d.get("WELLNESS")) > 0]
                                        
                                        if d_validos:
                                            f_val = np.mean([safe_float(d.get("W_Fatiga")) for d in d_validos])
                                            s_val = np.mean([safe_float(d.get("W_Sueño")) for d in d_validos])
                                            d_val = np.mean([safe_float(d.get("W_Dolor")) for d in d_validos])
                                            e_val = np.mean([safe_float(d.get("W_Estres")) for d in d_validos])
                                            h_val = np.mean([safe_float(d.get("W_Humor")) for d in d_validos])
                                            
                                    datos_w.append({"DIA": dia_n, "Fatiga": f_val, "Sueño": s_val, "Dolor": d_val, "Estrés": e_val, "Humor": h_val})
                                
                                fig_well = px.bar(
                                    pd.DataFrame(datos_w), x='DIA', y=['Fatiga', 'Sueño', 'Dolor', 'Estrés', 'Humor'], 
                                    title="Evolución Wellness Diario", color_discrete_sequence=px.colors.qualitative.Set2,
                                    labels={'value': 'Puntos', 'variable': 'Factor', 'DIA': ''}
                                )
                                fig_well.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_well.update_yaxes(range=[5, 35])
                                fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                                fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                                fig_well.update_traces(hovertemplate="%{variable}: %{y:.1f} pts")
                                fig_well.update_layout(barmode='stack', legend_title_text='Factores', hovermode="x unified")
                                st.plotly_chart(fig_well, use_container_width=True, key=f"micro_well_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 🔥 Carga Interna")
                            cg_i1, cg_i2, cg_i3 = st.columns(3)
                            with cg_i1:
                                fig_min = px.bar(df_diario, x='DIA', y='MIN', title="Evolución Minutos")
                                st.plotly_chart(fig_min, use_container_width=True, key=f"micro_min_{num_sem}")
                            with cg_i2:
                                df_rpe_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                fig_rpe = px.bar(df_rpe_plot, x='DIA', y='RPE', title="Evolución RPE", color='RPE', color_continuous_scale="Reds", range_color=[0, 10])
                                fig_rpe.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_rpe.update_yaxes(range=[1, 10])
                                st.plotly_chart(fig_rpe, use_container_width=True, key=f"micro_rpe_{num_sem}_{idx_real}")
                            with cg_i3:
                                df_carga_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index()
                                
                                min_c_temp = 0.0
                                max_c_temp = 1000.0
                                todas_cargas_temp = []
                                for s_t in st.session_state.sesiones:
                                    if s_t.get("informe_generado", False) and s_t.get("datos_informe"):
                                        for d in s_t["datos_informe"]:
                                            val_c = safe_float(d.get("CARGA"))
                                            if val_c > 0:
                                                todas_cargas_temp.append(val_c)
                                                
                                if todas_cargas_temp:
                                    min_c_temp = min(todas_cargas_temp)
                                    max_c_temp = max(todas_cargas_temp) * 1.1

                                fig_carga = px.bar(
                                    df_carga_plot, x='DIA', y='CARGA', 
                                    color='CARGA', color_continuous_scale="Reds", 
                                    range_color=[min_c_temp, max_c_temp],
                                    title="Evolución Carga"
                                )
                                fig_carga.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_carga.update_yaxes(range=[0, max_c_temp])
                                
                                media_equipo_semana = df_diario['CARGA'].mean()
                                if media_equipo_semana > 0:
                                    fig_carga.add_hline(
                                        y=media_equipo_semana, 
                                        line_dash="dot", 
                                        line_color="gray", 
                                        annotation_text=f"Media Semana: {media_equipo_semana:.0f} UA", 
                                        annotation_position="top right"
                                    )
                                    
                                st.plotly_chart(fig_carga, use_container_width=True, key=f"micro_carga_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 🏃‍♂️ Carga Externa (Solo datos GPS > 0m)")
                            
                            df_diario_plot = df_diario.set_index('DIA').reindex(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]).reset_index().fillna(0)
                            
                            cg_e1, cg_e2, cg_e3 = st.columns(3)
                            with cg_e1:
                                fig_accdcc = go.Figure()
                                fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['ACC'], mode='lines+markers', name='ACC (>3)', line=dict(color='blue')))
                                fig_accdcc.add_trace(go.Scatter(x=df_diario_plot['DIA'], y=df_diario_plot['DCC'], mode='lines+markers', name='DCC (>3)', line=dict(color='red')))
                                fig_accdcc.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                fig_accdcc.update_layout(title="Evolución ACC vs DCC")
                                st.plotly_chart(fig_accdcc, use_container_width=True, key=f"micro_accdcc_{num_sem}_{idx_real}")
                            with cg_e2:
                                fig_dis = px.bar(df_diario_plot, x='DIA', y='DIS', title="Evolución DIS (km)", color_discrete_sequence=['#00b4d8'])
                                fig_dis.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                st.plotly_chart(fig_dis, use_container_width=True, key=f"micro_dis_{num_sem}_{idx_real}")
                            with cg_e3:
                                fig_disai = px.bar(df_diario_plot, x='DIA', y='DIS AI', title="Evolución HSR (>21 km/h)", color_discrete_sequence=['#f50057'])
                                fig_disai.update_xaxes(categoryorder='array', categoryarray=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
                                st.plotly_chart(fig_disai, use_container_width=True, key=f"micro_disai_{num_sem}_{idx_real}")

                            st.markdown("---")
                            st.markdown("#### 👤 Resumen Semanal por Jugador")
                            # El resumen de jugador suma todas sus sesiones, aunque un día estuviera lesionado, sus datos de ese día serán 0.
                            df_jug_sum_int = df_filtrado.groupby('JUGADOR')[['MIN', 'CARGA']].sum().reset_index()
                            df_filtrado_gps = df_filtrado[df_filtrado['DIS'] > 0]
                            df_jug_sum_ext = df_filtrado_gps.groupby('JUGADOR')[['DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']].sum().reset_index() if not df_filtrado_gps.empty else pd.DataFrame(columns=['JUGADOR', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC'])
                            
                            df_jug_sum = pd.merge(df_jug_sum_int, df_jug_sum_ext, on='JUGADOR', how='left').fillna(0)
                            
                            df_no_ceros = df_filtrado.replace({'TQR': 0, 'WELLNESS': 0, 'RPE': 0}, np.nan)
                            df_jug_mean = df_no_ceros.groupby('JUGADOR')[['TQR', 'WELLNESS', 'RPE']].mean().reset_index().fillna(0)
                            df_indiv = df_jug_sum.merge(df_jug_mean, on='JUGADOR')
                            
                            df_info_extra = df_filtrado[['JUGADOR', 'POS', 'ROL']].drop_duplicates()
                            df_indiv = df_indiv.merge(df_info_extra, on='JUGADOR')
                            cols_ordenadas = ['JUGADOR', 'POS', 'ROL', 'MIN', 'TQR', 'WELLNESS', 'RPE', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC']
                            df_indiv = df_indiv[cols_ordenadas]
                            mostrar_tabla_moderna(df_indiv.style.hide(axis="index").format(precision=2)) # <--- CORREGIDO A df_indiv
                            
                            # --- PEGAR A CONTINUACIÓN ---
                            kpis_micro = {
                                "Wellness": df_diario['WELLNESS'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "TQR": df_diario['TQR'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "RPE": df_diario['RPE'].replace(0, np.nan).mean() if not df_diario.empty else 0,
                                "Minutos": df_diario['MIN'].sum() if not df_diario.empty else 0,
                                "Carga": df_diario['CARGA'].sum() if not df_diario.empty else 0,
                                "DIS": df_diario['DIS'].sum() if not df_diario.empty else 0,
                                "HSR": df_diario['DIS AI'].sum() if not df_diario.empty else 0,
                                "SPR": df_diario['Nº SPR'].sum() if not df_diario.empty else 0,
                                "ACC": df_diario['ACC'].sum() if not df_diario.empty else 0,
                                "DCC": df_diario['DCC'].sum() if not df_diario.empty else 0
                            }

                            diccionario_figuras_micro = {
                                "TQR": fig_tqr,
                                "Wellness": fig_well,
                                "Minutos": fig_min,
                                "RPE": fig_rpe,
                                "Carga": fig_carga,
                                "ACC_DCC": fig_accdcc,
                                "DIS": fig_dis,
                                "DIS_AI": fig_disai
                            }

                        st.markdown("---")
                        pdf_key = f"pdf_listo_{num_sem}_{idx_real}"

                        if pdf_key not in st.session_state:
                            if st.button("⚙️ Generar PDF del Microciclo", key=f"btn_prepara_pdf_{num_sem}_{idx_real}"):
                                with st.spinner("Procesando gráficos y PDF (esto puede tardar unos segundos)..."):
                                    st.session_state[pdf_key] = generar_pdf_microciclo(nombre_etiqueta, df_diario, df_indiv, kpis_micro, diccionario_figuras_micro)
                                st.rerun()
                        else:
                            col_pdf1, col_pdf2 = st.columns(2)
                            with col_pdf1:
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=st.session_state[pdf_key],
                                    file_name=f"Microciclo_Semana_{num_sem}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_descarga_pdf_{num_sem}_{idx_real}"
                                )
                            with col_pdf2:
                                if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_{num_sem}_{idx_real}"):
                                    del st.session_state[pdf_key]
                                    st.rerun()

    with tab_ses:
        if not st.session_state.sesiones:
            st.info("Aún no has generado ninguna sesión.")
        
        sesiones_ordenadas = sorted(st.session_state.sesiones, key=lambda x: x["fecha"], reverse=True)
            
        for idx_visual, sesion in enumerate(sesiones_ordenadas):
            idx_real = st.session_state.sesiones.index(sesion)
            es_partido = "Partido" in sesion['tipo']
            nombre_ev = sesion.get("nombre_dinamico", sesion["tipo"])
            detalle_ev = sesion.get("subtitulo_dinamico", sesion.get("descripcion", ""))
            
            with st.container():
                col_s1, col_s2, col_s3, col_s4, col_s5, col_s6 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5, 1.5])
                fecha_formateada = datetime.strptime(sesion['fecha'], "%Y-%m-%d").strftime("%d-%m-%Y")
                col_s1.write(f"📅 **{fecha_formateada}**")
                col_s2.write(f"⚽ **{nombre_ev}**\n\n<small>{detalle_ev}</small>", unsafe_allow_html=True)
                
                if col_s3.button("🏥 Disponibilidad", key=f"btn_disp_{idx_real}"):
                    st.session_state[f"mostrar_disp_{idx_real}"] = not st.session_state.get(f"mostrar_disp_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False
                
                if col_s4.button("📊 Informe", key=f"btn_inf_{idx_real}"):
                    st.session_state[f"mostrar_informe_{idx_real}"] = not st.session_state.get(f"mostrar_informe_{idx_real}", False)
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False
                    
                if col_s5.button("📂 Cargar Datos", key=f"btn_datos_{idx_real}"):
                    st.session_state[f"mostrar_datos_{idx_real}"] = not st.session_state.get(f"mostrar_datos_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_lesion_{idx_real}"] = False

                if col_s6.button("🚑 Lesión", key=f"btn_lesion_{idx_real}"):
                    st.session_state[f"mostrar_lesion_{idx_real}"] = not st.session_state.get(f"mostrar_lesion_{idx_real}", False)
                    st.session_state[f"mostrar_informe_{idx_real}"] = False
                    st.session_state[f"mostrar_disp_{idx_real}"] = False
                    st.session_state[f"mostrar_datos_{idx_real}"] = False
            
            if st.session_state.get(f"mostrar_disp_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 🏥 CONTROL DE DISPONIBILIDAD | {sesion['fecha']}")
                if es_partido:
                    opciones_disp = ["Titular", "Suplente", "No convocado", "Lesionado", "Enfermo", "Selección", "No disponible"]
                    default_disp = "Titular"
                else:
                    opciones_disp = ["Disponible", "Lesionado", "Readaptación", "Enfermo", "Falta", "Selección", "No disponible"]
                    default_disp = "Disponible"
                
                disp_dict = sesion.get("disponibilidad", {})
                disp_dict_clean = {limpiar_nombre(k): v for k, v in disp_dict.items()}
                
                conteos = Counter([disp_dict_clean.get(limpiar_nombre(j["JUGADOR"]), default_disp) for j in st.session_state.plantilla])
                cols_metricas = st.columns(len(opciones_disp))
                for i, opc in enumerate(opciones_disp): cols_metricas[i].metric(opc, conteos.get(opc, 0))
                
                with st.form(key=f"form_disp_{idx_real}"):
                    for i in range(0, len(st.session_state.plantilla), 2):
                        col_d1, col_d2 = st.columns(2)
                        jugador1 = st.session_state.plantilla[i]["JUGADOR"]
                        estado1 = disp_dict_clean.get(limpiar_nombre(jugador1), default_disp)
                        if estado1 not in opciones_disp: estado1 = opciones_disp[0]
                        nuevo1 = col_d1.selectbox(f"👤 {jugador1}", opciones_disp, index=opciones_disp.index(estado1), key=f"sel1_{idx_real}_{jugador1}")
                        if "disponibilidad" not in st.session_state.sesiones[idx_real]: st.session_state.sesiones[idx_real]["disponibilidad"] = {}
                        st.session_state.sesiones[idx_real]["disponibilidad"][jugador1] = nuevo1
                        
                        if i + 1 < len(st.session_state.plantilla):
                            jugador2 = st.session_state.plantilla[i+1]["JUGADOR"]
                            estado2 = disp_dict_clean.get(limpiar_nombre(jugador2), default_disp)
                            if estado2 not in opciones_disp: estado2 = opciones_disp[0]
                            nuevo2 = col_d2.selectbox(f"👤 {jugador2}", opciones_disp, index=opciones_disp.index(estado2), key=f"sel2_{idx_real}_{jugador2}")
                            st.session_state.sesiones[idx_real]["disponibilidad"][jugador2] = nuevo2
                    if st.form_submit_button("💾 Guardar Cambios"):
                        guardar_datos()
                        st.success("Disponibilidad guardada.")
                        st.rerun()
                st.markdown("---")

            if st.session_state.get(f"mostrar_informe_{idx_real}", False):
                st.markdown("---")
                if sesion.get("informe_generado", False) and sesion.get("datos_informe"):
                    df_informe = pd.DataFrame(sesion["datos_informe"])
                    
                    # --- 1. FORZAR CONVERSIÓN NUMÉRICA ESTRICTA ---
                    cols_metricas = [
                        'TQR', 'WELLNESS', 'W_Humor', 'W_Sueño', 'W_Fatiga', 'W_Dolor', 'W_Estres', 
                        'RPE', 'MIN', 'CARGA', 'DIS', 'DIS AI', 'Nº SPR', 'ACC', 'DCC', 'VMAX',
                        'HID >21', 'SPR >24', 'ACC >3', 'DCC >3', 'V_Max'
                    ]
                    for c in cols_metricas:
                        if c in df_informe.columns:
                            df_informe[c] = pd.to_numeric(df_informe[c], errors='coerce').fillna(0.0)
                    # ---------------------------------------------
                    
                    # MAPEO ESTRICTO PARA EL INFORME: Que use los nombres de las columnas detalladas si existen
                    if 'HID >21' in df_informe.columns: df_informe['DIS AI'] = df_informe['HID >21']
                    if 'SPR >24' in df_informe.columns: df_informe['Nº SPR'] = df_informe['SPR >24']
                    if 'ACC >3' in df_informe.columns:  df_informe['ACC'] = df_informe['ACC >3']
                    if 'DCC >3' in df_informe.columns:  df_informe['DCC'] = df_informe['DCC >3']
                    if 'V_Max' in df_informe.columns:   df_informe['VMAX'] = df_informe['V_Max']
                    
                    disp_dict = sesion.get("disponibilidad", {})
                    disp_dict_clean = {limpiar_nombre(k): v for k, v in disp_dict.items()}
                    default_disp = "Titular" if es_partido else "Disponible"
                    
                    df_informe['ESTADO'] = df_informe['JUGADOR'].map(lambda j: disp_dict_clean.get(limpiar_nombre(j), default_disp))

                    dic_ewma = calcular_ewma_historico(st.session_state.sesiones, sesion["fecha"])
                    df_informe['EWMA AGUDA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA AGUDA', 0))
                    df_informe['EWMA CRÓNICA'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('EWMA CRÓNICA', 0))
                    df_informe['RATIO A/C'] = df_informe['JUGADOR'].map(lambda j: dic_ewma.get(j, {}).get('RATIO A/C', 0))

                    col_filt1, col_filt2 = st.columns(2)
                    with col_filt1:
                        filtro_pos = st.radio("Posición:", ["TODOS", "POR", "DEF", "MED", "ATA"], horizontal=True, key=f"rp_{idx_real}")
                        if filtro_pos != "TODOS": df_informe = df_informe[df_informe["POS"] == filtro_pos]
                    if es_partido:
                        with col_filt2:
                            filtro_rol = st.radio("Rol:", ["TODOS", "Titular", "Suplente"], horizontal=True, key=f"rr_{idx_real}")
                            if filtro_rol != "TODOS": df_informe = df_informe[df_informe["ESTADO"] == filtro_rol]

                    # FILTRO ESTRICTO DE MEDIAS PARA EL EQUIPO (Sin Porteros)
                    estados_validos_medias = ["Disponible", "Titular", "Suplente"]
                    df_para_medias = df_informe[(df_informe['ESTADO'].isin(estados_validos_medias)) & (df_informe['POS'] != "POR")].copy()
                    
                    df_para_medias['TQR'] = df_para_medias['TQR'].replace(0, np.nan)
                    df_para_medias['WELLNESS'] = df_para_medias['WELLNESS'].replace(0, np.nan)
                    df_para_medias['RPE'] = df_para_medias['RPE'].replace(0, np.nan)
                    
                    # FILTRO ESTRICTO DE MEDIAS GPS (Solo si tienen distancia > 0)
                    df_para_medias_gps = df_para_medias[df_para_medias['DIS'] > 0].copy()
                    
                    # TABLAS Y GRÁFICOS MOSTRARÁN A TODOS LOS JUGADORES
                    df_graficos = df_informe[df_informe['JUGADOR'] != ""].copy()
                    fig_well = fig_tqr = fig2 = fig3 = fig5 = fig4 = None

                    if not df_informe.empty:
                        # --- 2. CÁLCULO SEGURO DE MEDIAS GLOBALES ---
                        tqr_m = df_para_medias['TQR'].mean()
                        tqr_m = tqr_m if pd.notna(tqr_m) else 0.0
                        
                        well_m = df_para_medias['WELLNESS'].mean()
                        well_m = well_m if pd.notna(well_m) else 0.0
                        
                        rpe_m = df_para_medias['RPE'].mean()
                        rpe_m = rpe_m if pd.notna(rpe_m) else 0.0
                        
                        carga_m = df_para_medias['CARGA'].mean()
                        carga_m = carga_m if pd.notna(carga_m) else 0.0
                        
                        min_m = df_para_medias['MIN'].mean()
                        min_m = min_m if pd.notna(min_m) else 0.0

                        # --- KPIs GLOBALES SUPERIORES DE LA SESIÓN ---
                        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                        kpi1.metric("TQR Medio (Recuperación)", f"{tqr_m:.1f} / 10")
                        kpi2.metric("Wellness Medio (Fatiga)", f"{well_m:.1f} pts")
                        kpi3.metric("RPE Medio (Esfuerzo)", f"{rpe_m:.1f} / 10")
                        kpi4.metric("Carga Media Sesión", f"{carga_m:.0f} UA")

                        st.markdown("---")

                        # --- SECCIÓN 1: BIENESTAR Y RECUPERACIÓN ---
                        st.markdown("#### 🧠 1. Bienestar y Recuperación")
                        cg1, cg2 = st.columns(2)
                        
                        with cg1:
                            if df_graficos['WELLNESS'].sum() > 0:
                                df_well = df_graficos[df_graficos['WELLNESS'] > 0].sort_values('WELLNESS', ascending=False).copy()
                                nombres_limpios = {
                                    'W_Sueño': 'Sueño', 
                                    'W_Fatiga': 'Fatiga', 
                                    'W_Dolor': 'Dolor', 
                                    'W_Estres': 'Estrés', 
                                    'W_Humor': 'Humor'
                                }
                                df_well = df_well.rename(columns=nombres_limpios)
                                cols_wellness = list(nombres_limpios.values())
                                
                                fig_well = px.bar(
                                    df_well,
                                    x='JUGADOR',
                                    y=cols_wellness,
                                    title="<b>Desglose de Wellness por Componentes</b>",
                                    labels={'value': 'Puntos', 'variable': '', 'JUGADOR': ''},
                                    color_discrete_sequence=px.colors.qualitative.Set2
                                )

                                fig_well.add_hline(y=18, line_dash="dot", line_color="orange", annotation_text="Moderado (18)", annotation_position="bottom right")
                                fig_well.add_hline(y=24, line_dash="dash", line_color="red", annotation_text="Crítico (24)", annotation_position="top right")
                                
                                # MODIFICACIÓN: Fijar el eje Y de 5 a 35 obligatoriamente
                                fig_well.update_yaxes(range=[5, 35])
                                
                                fig_well.update_traces(hovertemplate="%{y}")
                                fig_well.update_layout(
                                    barmode='stack',
                                    xaxis_tickangle=-45,
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    margin=dict(t=40, b=120, l=40, r=40),
                                    legend_title_text='Factores',
                                    hovermode="x unified"
                                )
                                st.plotly_chart(fig_well, use_container_width=True, key=f"ses_well_detalle_grafico_{idx_real}")
                        
                        with cg2:
                            if df_graficos['TQR'].sum() > 0:
                                df_tqr = df_graficos[df_graficos['TQR'] > 0].sort_values('TQR')
                                fig_tqr = px.bar(df_tqr, x='JUGADOR', y='TQR', color='TQR', color_continuous_scale="RdYlGn", range_color=[1, 10], title="Calidad de Recuperación (TQR)")
                                st.plotly_chart(fig_tqr, use_container_width=True, key=f"ses_tqr_grafico_{idx_real}")
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN 2: CARGA INTERNA ---
                        st.markdown("#### 🔥 2. Carga Interna")
                        ci1, ci2, ci3 = st.columns(3)
                        ci1.metric("Minutos Sesión (Media)", f"{min_m:.1f}")
                        ci2.metric("RPE Medio", f"{rpe_m:.1f}")
                        ci3.metric("Carga Media (UA)", f"{carga_m:.0f}")
                        
                        cols_ver_ci = ['JUGADOR', 'POS', 'ESTADO', 'MIN', 'RPE', 'CARGA', 'EWMA AGUDA', 'EWMA CRÓNICA', 'RATIO A/C']
                        
                        estilo_ci = (df_informe[cols_ver_ci].style
                                     .hide(axis="index")
                                     .format(precision=2)
                                     .background_gradient(subset=['RPE'], cmap='Reds', vmin=0, vmax=10)
                                     .map(lambda x: f"background-color: {color_ratio_ac(x)}; color: black;" if isinstance(x, (int, float)) else "", subset=['RATIO A/C'])
                                     .set_table_attributes('class="modern-table"')
                                    )
                        
                        css_personalizado = "<style>.modern-table { width: 100%; border-collapse: collapse; font-family: sans-serif; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); background-color: white; margin-bottom: 20px; } .modern-table thead tr { background-color: #000000; color: #ffffff; } .modern-table th { padding: 12px 15px; font-weight: bold; text-align: center !important; border-bottom: 2px solid #333333; } .modern-table td { padding: 10px 15px; text-align: center !important; border-bottom: 1px solid #eeeeee; } .modern-table tbody tr:hover td { filter: brightness(0.95); }</style>"
                        
                        st.markdown(css_personalizado + estilo_ci.to_html(), unsafe_allow_html=True)
                        
                        cg3, cg4 = st.columns(2)
                        with cg3:
                            if df_graficos['CARGA'].sum() > 0:
                                df_ci = df_graficos[df_graficos['CARGA'] > 0].sort_values('CARGA', ascending=False)
                                fig2 = px.bar(
                                    df_ci, x='JUGADOR', y='CARGA', 
                                    color='RPE', color_continuous_scale="Reds", 
                                    range_color=[0, 10], title="Carga de Sesión (Min * RPE)"
                                )
                                if not df_para_medias.empty:
                                    media_equipo = df_para_medias['CARGA'].mean()
                                    fig2.add_hline(
                                        y=media_equipo, 
                                        line_dash="dot", 
                                        line_color="gray", 
                                        annotation_text=f"Media Equipo: {media_equipo:.0f} UA", 
                                        annotation_position="top right"
                                    )
                                st.plotly_chart(fig2, use_container_width=True, key=f"ses_carga_grafico_{idx_real}")
                        with cg4:
                            if df_graficos['RATIO A/C'].sum() > 0:
                                df_ac = df_graficos[df_graficos['RATIO A/C'] > 0].sort_values('RATIO A/C', ascending=False).copy()
                                df_ac['Color_AC'] = df_ac['RATIO A/C'].apply(color_ratio_ac)
                                fig3 = go.Figure(data=[go.Bar(
                                    x=df_ac['JUGADOR'], 
                                    y=df_ac['RATIO A/C'], 
                                    marker_color=df_ac['Color_AC'], 
                                    text=df_ac['RATIO A/C'].round(2), 
                                    textposition='auto'
                                )])
                                fig3.update_layout(title="Riesgo de Lesión (Ratio A/C)")
                                fig3.add_hline(y=1.4, line_dash="dash", line_color="#ff4b4b")
                                st.plotly_chart(fig3, use_container_width=True, key=f"ses_ac_grafico_{idx_real}")
                        
                        st.markdown("---")
                        
                        # --- SECCIÓN 3: CARGA EXTERNA ---
                        st.markdown("#### 🏃‍♂️ 3. Carga Externa (GPS) - Solo jugadores con GPS > 0m")
                        
                        dis_m = df_para_medias_gps['DIS'].mean()
                        dis_m = dis_m if pd.notna(dis_m) else 0.0
                        
                        hsr_m = df_para_medias_gps['DIS AI'].mean()
                        hsr_m = hsr_m if pd.notna(hsr_m) else 0.0
                        
                        spr_m = df_para_medias_gps['Nº SPR'].mean()
                        spr_m = spr_m if pd.notna(spr_m) else 0.0
                        
                        acc_m = df_para_medias_gps['ACC'].mean()
                        acc_m = acc_m if pd.notna(acc_m) else 0.0
                        
                        dcc_m = df_para_medias_gps['DCC'].mean()
                        dcc_m = dcc_m if pd.notna(dcc_m) else 0.0
                        
                        ce1, ce2, ce3, ce4, ce5 = st.columns(5)
                        ce1.metric("Distancia (km)", f"{dis_m:.2f}")
                        ce2.metric("HSR (>21 km/h)", f"{hsr_m:.2f}")
                        ce3.metric("Nº SPRINTS (>24 km/h)", f"{spr_m:.1f}")
                        ce4.metric("ACC (>3 m/s²)", f"{acc_m:.0f}")
                        ce5.metric("DCC (>3 m/s²)", f"{dcc_m:.0f}")
                        
                        if 'HID >21' not in df_informe.columns:
                            df_informe['HID >21'] = df_informe.get('DIS AI', 0.0)
                        
                        cols_ver_ce = ['JUGADOR', 'POS', 'ESTADO', 'DIS', 'HID >21', 'Nº SPR', 'ACC', 'DCC', 'VMAX']
                        mostrar_tabla_moderna(df_informe[cols_ver_ce].style.hide(axis="index").format(precision=2))
                        
                        cg5, cg6 = st.columns(2)
                        with cg5:
                            if df_graficos['DIS'].sum() > 0:
                                df_gps_sesion = df_graficos[df_graficos['DIS'] > 0].copy()
                                fig5 = px.scatter(
                                    df_gps_sesion, 
                                    x='DIS', 
                                    y='DIS AI', 
                                    color='POS', 
                                    hover_name='JUGADOR', 
                                    text='JUGADOR', 
                                    title="Volumen vs Intensidad",
                                    color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"}
                                )
                                fig5.update_traces(
                                    textposition='top center', 
                                    marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey'))
                                )
                                media_vol = df_gps_sesion['DIS'].mean()
                                media_int = df_gps_sesion['DIS AI'].mean()
                                fig5.add_vline(x=media_vol, line_dash="dot", line_color="gray", opacity=0.6)
                                fig5.add_hline(y=media_int, line_dash="dot", line_color="gray", opacity=0.6)
                                st.plotly_chart(fig5, use_container_width=True, key=f"ses_hsr_grafico_{idx_real}")
                        with cg6:
                            if df_graficos['ACC'].sum() > 0 or df_graficos['DCC'].sum() > 0:
                                df_accdcc = df_graficos[df_graficos['DIS'] > 0]
                                max_val = max(df_accdcc['ACC'].max(), df_accdcc['DCC'].max()) * 1.1 if not df_accdcc.empty else 10
                                fig4 = px.scatter(
                                    df_accdcc, x='DCC', y='ACC', color='POS', 
                                    hover_name='JUGADOR', 
                                    title="ACC vs DCC",
                                    color_discrete_map={"POR": "gray", "DEF": "#00b4d8", "MED": "#28a745", "ATA": "#ff4b4b"}
                                )
                                fig4.update_traces(marker=dict(size=12, opacity=0.8))
                                fig4.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="gray", dash="dot"))
                                fig4.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1))
                                st.plotly_chart(fig4, use_container_width=True, key=f"ses_accdcc_grafico_{idx_real}")
                        st.markdown("---")
                        st.markdown("#### ⚠️ Alertas de Riesgo lesivo alto")
                    
                        media_carga = df_para_medias['CARGA'].mean() if not df_para_medias.empty else 0
                        std_carga = df_para_medias['CARGA'].std(ddof=0) if not df_para_medias.empty else 0
                        umbral_carga = media_carga + (2.0 * std_carga) if std_carga > 0 else media_carga * 1.4

                        alertas_jugadores = {}
                        activos = df_informe[df_informe['ESTADO'].isin(["Disponible", "Titular", "Suplente"])]

                        for idx_row, row in activos.iterrows():
                            jug = row['JUGADOR']
                            alertas_jugadores[jug] = {'recuperacion': [], 'carga': [], 'total': 0}
                            
                            tqr = safe_float(row.get('TQR'))
                            well = safe_float(row.get('WELLNESS'))
                            
                            if tqr > 0:
                                if tqr <= 3:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 Recuperación Crítica ({tqr:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif tqr == 4:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🟡 Recuperación Moderada ({tqr:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                    
                            if well > 0:
                                if well >= 24:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🔴 Wellness Crítico ({well:.1f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif 18 <= well <= 23:
                                    alertas_jugadores[jug]['recuperacion'].append(f"🟡 Wellness Moderado ({well:.1f})")
                                    alertas_jugadores[jug]['total'] += 1

                            ratio_ac = safe_float(row.get('RATIO A/C'))
                            carga_aguda = safe_float(row.get('EWMA AGUDA'))
                            carga_sesion = safe_float(row.get('CARGA'))
                            
                            if carga_aguda > 1000:
                                if ratio_ac >= 1.5:
                                    alertas_jugadores[jug]['carga'].append(f"🔴 Ratio A/C en riesgo alto ({ratio_ac:.2f})")
                                    alertas_jugadores[jug]['total'] += 1
                                elif 1.35 <= ratio_ac < 1.5:
                                    alertas_jugadores[jug]['carga'].append(f"🟡 Ratio A/C en riesgo moderado ({ratio_ac:.2f})")
                                    alertas_jugadores[jug]['total'] += 1
                                    
                            if media_carga > 0 and carga_sesion > umbral_carga:
                                alertas_jugadores[jug]['carga'].append(f"🟠 Carga Anormal ({carga_sesion:.0f} UA vs Media {media_carga:.0f} UA)")
                                alertas_jugadores[jug]['total'] += 1
                                
                            monot = calcular_monotonia_7d(st.session_state.sesiones, jug, sesion['fecha'])
                            strain = carga_aguda * monot
                            if monot > 2.0 and strain > 4000:
                                alertas_jugadores[jug]['carga'].append(f"🟡 Riesgo por monotonía y fatiga acumulada (Monotonía {monot:.2f}, Strain {strain:.0f})")
                                alertas_jugadores[jug]['total'] += 1
                                
                        alertas_multi = []
                        alertas_rec = []
                        alertas_car = []
                        
                        for jug, data in alertas_jugadores.items():
                            if data['total'] >= 2:
                                alertas_multi.append(f"**{jug}** ({data['total']} alertas): " + " | ".join(data['recuperacion'] + data['carga']))
                            elif data['total'] == 1:
                                if data['recuperacion']: alertas_rec.append(f"**{jug}**: {data['recuperacion'][0]}")
                                if data['carga']: alertas_car.append(f"**{jug}**: {data['carga'][0]}")

                        if not alertas_multi and not alertas_rec and not alertas_car:
                            st.success("✅ Todos los marcadores de fatiga y riesgo del equipo están dentro de los parámetros normales.")
                        else:
                            if alertas_multi:
                                st.error("🚨 **RIESGO MULTIFACTORIAL (2 o más alertas simultáneas)**")
                                for al in alertas_multi: st.write(f"- {al}")
                                st.markdown("---")
                                
                            c_al1, c_al2 = st.columns(2)
                            with c_al1:
                                st.markdown("#### 🧠 Recuperación")
                                if alertas_rec:
                                    for al in alertas_rec: st.warning(al)
                                else:
                                    st.info("✅ Sin alertas individuales.")
                                    
                            with c_al2:
                                st.markdown("#### 🔥 Carga")
                                if alertas_car:
                                    for al in alertas_car: st.warning(al)
                                else:
                                    st.info("✅ Sin alertas individuales.")
                        
                        dict_figs = {
                            "Desglose de Wellness": fig_well,
                            "Calidad de Recuperación (TQR)": fig_tqr,
                            "Carga de Sesión": fig2,
                            "Riesgo de Lesión (Ratio A/C)": fig3,
                            "Volumen vs Intensidad": fig5,
                            "ACC vs DCC": fig4
                        }
                        
                        st.markdown("---")
                        pdf_key = f"pdf_sesion_listo_{idx_real}"
                        
                        if pdf_key not in st.session_state:
                            if st.button("⚙️ Generar PDF de la Sesión", key=f"btn_prepara_pdf_ses_{idx_real}"):
                                with st.spinner("Procesando gráficos y PDF (esto puede tardar unos segundos)..."):
                                    st.session_state[pdf_key] = generar_pdf_completo(sesion, df_para_medias, df_graficos, alertas_multi, alertas_rec, alertas_car, dict_figs)
                                st.rerun()
                        else:
                            col_pdf1, col_pdf2 = st.columns(2)
                            with col_pdf1:
                                st.download_button(
                                    label="📥 Descargar PDF",
                                    data=st.session_state[pdf_key],
                                    file_name=f"Sesion_{sesion['fecha']}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_descarga_pdf_ses_{idx_real}"
                                )
                            with col_pdf2:
                                if st.button("🗑️ Descartar PDF", key=f"btn_borrar_pdf_ses_{idx_real}"):
                                    del st.session_state[pdf_key]
                                    st.rerun()                                                          
                    else:
                        st.warning("No hay datos que coincidan con los filtros seleccionados.")
                st.markdown("---")
            
            # --- NUEVA CONDICIÓN AÑADIDA AQUÍ ---
            if st.session_state.get(f"mostrar_datos_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 📂 CARGA DE DATOS DE LA SESIÓN | {sesion['fecha']}")
                # --- NUEVO: MOSTRADOR DE MENSAJES DE SINCRONIZACIÓN ---
                if f'msg_sync_{idx_real}' in st.session_state:
                    for msg in st.session_state[f'msg_sync_{idx_real}']:
                        if "✅" in msg: st.success(msg)
                        elif "⚠️" in msg: st.warning(msg)
                        elif "❓" in msg: st.info(msg)
                    del st.session_state[f'msg_sync_{idx_real}']
                # ------------------------------------------------------
                with st.expander("✍️ Introducción o Edición Manual de Datos", expanded=not sesion.get("informe_generado", False)):
                    st.caption("Introduce Wellness (1-7), Minutos de Sesión, Minutos de GPS, RPE y métricas detalladas.")
                    
                    if sesion.get("datos_informe"):
                        df_manual_base = pd.DataFrame(sesion["datos_informe"])
                    else:
                        rows = []
                        for p in st.session_state.plantilla:
                            rows.append({
                                "JUGADOR": p["JUGADOR"],
                                "POS": p["POS"],
                                "TQR": 0.0,
                                "W_Humor": 0.0,
                                "W_Sueño": 0.0,
                                "W_Fatiga": 0.0,
                                "W_Dolor": 0.0,
                                "W_Estres": 0.0,
                                "RPE": 0.0,
                                "MIN": 0.0,
                                "MIN_GPS": 0.0,
                                "DIS": 0.0,
                                "HID >21": 0.0,
                                "HID >24": 0.0,
                                "SPR >24": 0.0,
                                "SPR >27": 0.0,
                                "V_Med": 0.0,
                                "V_Max": 0.0,
                                "ACC_Max": 0.0,
                                "ACC >2": 0.0,
                                "ACC >3": 0.0,
                                "ACC >4": 0.0,
                                "DCC >2": 0.0,
                                "DCC >3": 0.0,
                                "DCC >4": 0.0,
                                "R_0_7": 0.0,
                                "R_7_14": 0.0,
                                "R_14_21": 0.0,
                                "R_21_24": 0.0,
                                "R_24_27": 0.0,
                                "R_27_30": 0.0,
                                "R_30_45": 0.0
                            })
                        df_manual_base = pd.DataFrame(rows)
                        
                    if "V_Max" not in df_manual_base.columns: df_manual_base["V_Max"] = df_manual_base.get("VMAX", 0.0)
                    if "HID >21" not in df_manual_base.columns: df_manual_base["HID >21"] = df_manual_base.get("DIS AI", 0.0)
                    if "SPR >24" not in df_manual_base.columns: df_manual_base["SPR >24"] = df_manual_base.get("Nº SPR", 0.0)
                    if "ACC >3" not in df_manual_base.columns: df_manual_base["ACC >3"] = df_manual_base.get("ACC", 0.0)
                    if "DCC >3" not in df_manual_base.columns: df_manual_base["DCC >3"] = df_manual_base.get("DCC", 0.0)

                    cols_to_show = [
                        "JUGADOR", "POS", "TQR", 
                        "W_Humor", "W_Sueño", "W_Fatiga", "W_Dolor", "W_Estres", 
                        "RPE", "MIN", "MIN_GPS", "DIS", 
                        "HID >21", "HID >24", "SPR >24", "SPR >27", "V_Med", "V_Max", "ACC_Max",
                        "ACC >2", "ACC >3", "ACC >4", "DCC >2", "DCC >3", "DCC >4",
                        "R_0_7", "R_7_14", "R_14_21", "R_21_24", "R_24_27", "R_27_30", "R_30_45"
                    ]
                    for c in cols_to_show:
                        if c not in df_manual_base.columns:
                            df_manual_base[c] = 0.0
                            
                    edited_df = st.data_editor(
                        df_manual_base[cols_to_show],
                        key=f"editor_manual_{idx_real}",
                        use_container_width=True,
                        hide_index=True,
                        disabled=["JUGADOR", "POS"]
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Guardar Datos Manuales", key=f"btn_save_manual_{idx_real}"):
                            full_records = []
                            for idx_row, row in edited_df.iterrows():
                                suma_well = safe_float(row["W_Humor"]) + safe_float(row["W_Sueño"]) + safe_float(row["W_Fatiga"]) + safe_float(row["W_Dolor"]) + safe_float(row["W_Estres"])
                                min_ses = safe_float(row["MIN"])
                                min_gps_val = safe_float(row["MIN_GPS"])
                                
                                if min_gps_val > 0 and safe_float(row["DIS"]) > 0:
                                    dis = safe_float(row["DIS"])
                                    dis_ai_21 = safe_float(row["HID >21"])
                                    dis_ai_24 = safe_float(row["HID >24"])
                                    spr_24 = safe_float(row["SPR >24"])
                                    spr_27 = safe_float(row["SPR >27"])
                                    v_med = safe_float(row["V_Med"])
                                    v_max = safe_float(row["V_Max"])
                                    acc_max = safe_float(row["ACC_Max"])
                                    acc_2 = safe_float(row["ACC >2"])
                                    acc_3 = safe_float(row["ACC >3"])
                                    acc_4 = safe_float(row["ACC >4"])
                                    dcc_2 = safe_float(row["DCC >2"])
                                    dcc_3 = safe_float(row["DCC >3"])
                                    dcc_4 = safe_float(row["DCC >4"])
                                    r_0_7 = safe_float(row["R_0_7"])
                                    r_7_14 = safe_float(row["R_7_14"])
                                    r_14_21 = safe_float(row["R_14_21"])
                                    r_21_24 = safe_float(row["R_21_24"])
                                    r_24_27 = safe_float(row["R_24_27"])
                                    r_27_30 = safe_float(row["R_27_30"])
                                    r_30_45 = safe_float(row["R_30_45"])
                                else:
                                    dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_27 = v_med = v_max = acc_max = acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = r_30_45 = 0.0

                                rec = {
                                    "JUGADOR": row["JUGADOR"],
                                    "POS": row["POS"],
                                    "TQR": safe_float(row["TQR"]),
                                    "WELLNESS": suma_well,
                                    "W_Humor": safe_float(row["W_Humor"]),
                                    "W_Sueño": safe_float(row["W_Sueño"]),
                                    "W_Fatiga": safe_float(row["W_Fatiga"]),
                                    "W_Dolor": safe_float(row["W_Dolor"]),
                                    "W_Estres": safe_float(row["W_Estres"]),
                                    "RPE": safe_float(row["RPE"]),
                                    "MIN": min_ses,
                                    "MIN_GPS": min_gps_val,
                                    "CARGA": min_ses * safe_float(row["RPE"]),
                                    
                                    "DIS": dis,
                                    "DIS AI": dis_ai_21,
                                    "Nº SPR": spr_24,
                                    "ACC": acc_3,
                                    "DCC": dcc_3,
                                    "VMAX": v_max,
                                    "Z1": r_0_7 + r_7_14,
                                    "Z2": r_14_21,
                                    "Z3": r_21_24,
                                    "Z4": r_24_27,
                                    "Z5": r_27_30,
                                    "Z6": r_30_45,
                                    
                                    "HID >21": dis_ai_21,
                                    "HID >24": dis_ai_24,
                                    "SPR >24": spr_24,
                                    "SPR >27": spr_27,
                                    "V_Med": v_med,
                                    "V_Max": v_max,
                                    "ACC_Max": acc_max,
                                    "ACC >2": acc_2,
                                    "ACC >3": acc_3,
                                    "ACC >4": acc_4,
                                    "DCC >2": dcc_2,
                                    "DCC >3": dcc_3,
                                    "DCC >4": dcc_4,
                                    "R_0_7": r_0_7,
                                    "R_7_14": r_7_14,
                                    "R_14_21": r_14_21,
                                    "R_21_24": r_21_24,
                                    "R_24_27": r_24_27,
                                    "R_27_30": r_27_30,
                                    "R_30_45": r_30_45
                                }
                                full_records.append(rec)
                                
                            st.session_state.sesiones[idx_real]['datos_informe'] = full_records
                            st.session_state.sesiones[idx_real]['informe_generado'] = True
                            guardar_datos()
                            st.success("✅ ¡Datos manuales guardados correctamente!")
                            st.rerun()

                    with col_btn2:
                        if st.button("🗑️ Borrar Datos de la Sesión", key=f"btn_del_session_{idx_real}"):
                            st.session_state.sesiones[idx_real]['datos_informe'] = []
                            st.session_state.sesiones[idx_real]['informe_generado'] = False
                            guardar_datos()
                            st.success("✅ Datos de la sesión borrados correctamente.")
                            st.rerun()

                with st.expander("📁 Importar desde Archivos Excel (Wellness, RPE, GPS)"):
                    st.caption("Sube tus archivos. El sistema integrará a toda la plantilla cruzando Wellness, RPE y los GPS disponibles.")
                    col_up1, col_up2, col_up3 = st.columns(3)
                    with col_up1: archivo_well = st.file_uploader("1. Bienestar (Wellness):", type=["xlsx"], key=f"up_well_{idx_real}")
                    with col_up2: archivo_rpe = st.file_uploader("2. Carga Interna (RPE):", type=["xlsx"], key=f"up_rpe_{idx_real}")
                    with col_up3: archivo_gps = st.file_uploader("3. Carga Externa (GPS):", type=["xlsx"], key=f"up_gps_{idx_real}")
                    
                    if st.button("⚙️ Procesar y Sincronizar Archivos", key=f"btn_proc_{idx_real}"):
                        try:
                            import difflib
                            
                            df_w_up = pd.read_excel(archivo_well) if archivo_well else pd.DataFrame()
                            df_r_up = pd.read_excel(archivo_rpe) if archivo_rpe else pd.DataFrame()
                            df_g_up = pd.read_excel(archivo_gps) if archivo_gps else pd.DataFrame()
                            
                            fecha_sesion_str = pd.to_datetime(sesion['fecha']).strftime('%Y-%m-%d')
                            
                            def filtrar_fecha(df):
                                if df.empty: return df
                                col_f = next((c for c in df.columns if 'marca temporal' in str(c).lower() or 'activity date' in str(c).lower()), None)
                                if col_f:
                                    df['FECHA_TEMP'] = pd.to_datetime(df[col_f], errors='coerce').dt.strftime('%Y-%m-%d')
                                    return df[df['FECHA_TEMP'] == fecha_sesion_str].drop(columns=['FECHA_TEMP'])
                                return df

                            df_w_up = filtrar_fecha(df_w_up)
                            df_r_up = filtrar_fecha(df_r_up)
                            df_g_up = filtrar_fecha(df_g_up)

                            nombres_plantilla = [p['JUGADOR'] for p in st.session_state.plantilla]
                            no_encontrados_en_app = set()
                            
                            def emparejar_nombre(nombre_excel):
                                if pd.isna(nombre_excel): return None
                                n_ex = limpiar_nombre(nombre_excel)
                                for n_app in nombres_plantilla:
                                    if n_ex == limpiar_nombre(n_app): return n_app
                                for n_app in nombres_plantilla:
                                    n_app_cl = limpiar_nombre(n_app)
                                    if n_ex in n_app_cl or n_app_cl in n_ex: return n_app
                                matches = difflib.get_close_matches(n_ex, [limpiar_nombre(n) for n in nombres_plantilla], n=1, cutoff=0.7)
                                if matches:
                                    for n_app in nombres_plantilla:
                                        if limpiar_nombre(n_app) == matches[0]: return n_app
                                return None

                            faltan_w = []
                            if not df_w_up.empty and 'Nombre' in df_w_up.columns:
                                df_w_up['JUGADOR_MATCH'] = df_w_up['Nombre'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_w_up[df_w_up['JUGADOR_MATCH'].isna()]['Nombre'].dropna().tolist())
                                df_w_up = df_w_up.dropna(subset=['JUGADOR_MATCH'])
                                faltan_w = [n for n in nombres_plantilla if n not in df_w_up['JUGADOR_MATCH'].tolist()]
                            elif archivo_well: faltan_w = nombres_plantilla.copy()

                            faltan_r = []
                            if not df_r_up.empty and 'Nombre' in df_r_up.columns:
                                df_r_up['JUGADOR_MATCH'] = df_r_up['Nombre'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_r_up[df_r_up['JUGADOR_MATCH'].isna()]['Nombre'].dropna().tolist())
                                df_r_up = df_r_up.dropna(subset=['JUGADOR_MATCH'])
                                faltan_r = [n for n in nombres_plantilla if n not in df_r_up['JUGADOR_MATCH'].tolist()]
                            elif archivo_rpe: faltan_r = nombres_plantilla.copy()

                            if not df_g_up.empty and 'Player Name' in df_g_up.columns:
                                df_g_up['JUGADOR_MATCH'] = df_g_up['Player Name'].apply(emparejar_nombre)
                                no_encontrados_en_app.update(df_g_up[df_g_up['JUGADOR_MATCH'].isna()]['Player Name'].dropna().tolist())
                                df_g_up = df_g_up.dropna(subset=['JUGADOR_MATCH'])

                            registros_sesion = []
                            for nombre_final in sorted(nombres_plantilla):
                                match_p = next((p for p in st.session_state.plantilla if p['JUGADOR'] == nombre_final), None)
                                pos_jug = match_p['POS']

                                rpe_val = 0.0
                                if not df_r_up.empty:
                                    match_r = df_r_up[df_r_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_r.empty: rpe_val = safe_float(match_r.iloc[0].get('Índice de Esfuerzo Percibido', 0))

                                tqr_val = fatiga = sueño = dolor = estres = humor = well_sum = 0.0
                                if not df_w_up.empty:
                                    match_w = df_w_up[df_w_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_w.empty:
                                        r_w = match_w.iloc[0]
                                        tqr_val = safe_float(r_w.get('Índice de Calidad de Recuperación', 0))
                                        fatiga = safe_float(r_w.get('Fatiga:', 0))
                                        sueño = safe_float(r_w.get('Calidad del sueño:', 0))
                                        dolor = safe_float(r_w.get('Dolor muscular:', 0))
                                        estres = safe_float(r_w.get('Nivel de estrés:', 0))
                                        humor = safe_float(r_w.get('Humor:', 0))
                                        well_sum = fatiga + sueño + dolor + estres + humor

                                min_sesion = 90.0 if rpe_val > 0 else 0.0
                                carga_calc = min_sesion * rpe_val

                                dis = dis_ai_21 = dis_ai_24 = spr_24 = spr_30 = v_med = v_max = 0.0
                                acc_2 = acc_3 = acc_4 = dcc_2 = dcc_3 = dcc_4 = 0.0
                                r_0_7 = r_7_14 = r_14_21 = r_21_24 = r_24_27 = r_27_30 = 0.0

                                if not df_g_up.empty:
                                    match_g = df_g_up[df_g_up['JUGADOR_MATCH'] == nombre_final]
                                    if not match_g.empty:
                                        row_g = match_g.iloc[0]
                                        min_sesion = extraer_minutos(str(row_g.get('Time Played', '0'))) or 90.0
                                        carga_calc = min_sesion * rpe_val
                                        dis = safe_float(row_g.get('Distance (km)', 0))
                                        if dis > 0:
                                            dis_ai_21 = safe_float(row_g.get('HID distance (> 21.00 km/h)', 0))
                                            dis_ai_24 = safe_float(row_g.get('HID distance (> 24.00 km/h)', 0))
                                            spr_24 = safe_float(row_g.get('# of Sprints (> 24.00 km/h)', 0))
                                            spr_30 = safe_float(row_g.get('# of Sprints (> 30.00 km/h)', 0))
                                            v_med = safe_float(row_g.get('Avg Speed (km/h)', 0))
                                            v_max = safe_float(row_g.get('Max Speed (km/h)', 0))
                                            acc_2 = safe_float(row_g.get('# of Accelerations (> 2.00 m/s²)', 0))
                                            acc_3 = safe_float(row_g.get('# of Accelerations (> 3.00 m/s²)', 0))
                                            acc_4 = safe_float(row_g.get('# of Accelerations (> 4.00 m/s²)', 0))
                                            dcc_2 = safe_float(row_g.get('# of Decelerations (> 2.00 m/s²)', 0))
                                            dcc_3 = safe_float(row_g.get('# of Decelerations (> 3.00 m/s²)', 0))
                                            dcc_4 = safe_float(row_g.get('# of Decelerations (> 4.00 m/s²)', 0))
                                            r_0_7 = safe_float(row_g.get('Distance Speed Range (0 - 7 km)', 0))
                                            r_7_14 = safe_float(row_g.get('Distance Speed Range (7 - 14 km)', 0))
                                            r_14_21 = safe_float(row_g.get('Distance Speed Range (14 - 21 km)', 0))
                                            r_21_24 = safe_float(row_g.get('Distance Speed Range (21 - 24 km)', 0))
                                            r_24_27 = safe_float(row_g.get('Distance Speed Range (24 - 27 km)', 0))
                                            r_27_30 = safe_float(row_g.get('Distance Speed Range (27 - 30 km)', 0))

                                registros_sesion.append({
                                    "JUGADOR": nombre_final, "POS": pos_jug,
                                    "TQR": tqr_val, "WELLNESS": well_sum,
                                    "W_Humor": humor, "W_Sueño": sueño, "W_Fatiga": fatiga, "W_Dolor": dolor, "W_Estres": estres,
                                    "RPE": rpe_val, "MIN": min_sesion, "MIN_GPS": min_sesion if dis > 0 else 0.0, "CARGA": carga_calc,
                                    "DIS": dis, "DIS AI": dis_ai_21, "Nº SPR": spr_24, "ACC": acc_3, "DCC": dcc_3, "VMAX": v_max,
                                    "Z1": r_0_7 + r_7_14, "Z2": r_14_21, "Z3": r_21_24, "Z4": r_24_27, "Z5": r_27_30, "Z6": 0.0,
                                    "HID >21": dis_ai_21, "HID >24": dis_ai_24, "SPR >24": spr_24, "SPR >27": spr_30,
                                    "V_Med": v_med, "V_Max": v_max, "ACC_Max": 0.0, "ACC >2": acc_2, "ACC >3": acc_3, "ACC >4": acc_4,
                                    "DCC >2": dcc_2, "DCC >3": dcc_3, "DCC >4": dcc_4, "R_0_7": r_0_7, "R_7_14": r_7_14,
                                    "R_14_21": r_14_21, "R_21_24": r_21_24, "R_24_27": r_24_27, "R_27_30": r_27_30, "R_30_45": spr_30
                                })
                                
                            st.session_state.sesiones[idx_real]['datos_informe'] = registros_sesion
                            st.session_state.sesiones[idx_real]['informe_generado'] = True
                            guardar_datos()
                            
                            msgs = [f"✅ Sincronización completada. Se generó la tabla con los {len(nombres_plantilla)} jugadores de tu plantilla."]
                            if archivo_well and faltan_w: msgs.append(f"⚠️ **Faltan en Wellness:** {', '.join(faltan_w)}")
                            if archivo_rpe and faltan_r: msgs.append(f"⚠️ **Faltan en RPE:** {', '.join(faltan_r)}")
                            if no_encontrados_en_app: msgs.append(f"❓ **Están en Excel pero NO en tu App:** {', '.join(no_encontrados_en_app)}")
                            st.session_state[f'msg_sync_{idx_real}'] = msgs
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al procesar: {e}")
                            st.error(f"Error al procesar y sincronizar los archivos: {e}")

            if st.session_state.get(f"mostrar_lesion_{idx_real}", False):
                st.markdown("---")
                st.markdown(f"#### 🚑 PARTE MÉDICO | {sesion['fecha']}")
                st.caption("Registra aquí una incidencia ocurrida durante esta sesión.")
                
                if not st.session_state.plantilla:
                    st.warning("No hay jugadores en la plantilla para registrar lesiones.")
                else:
                    with st.form(key=f"form_lesion_{idx_real}"):
                        nombres_plantilla = [j["JUGADOR"] for j in st.session_state.plantilla]
                        
                        c_L1, c_L2 = st.columns(2)
                        les_jugador = c_L1.selectbox("Jugador Afectado:", nombres_plantilla)
                        les_tipo = c_L2.selectbox("Tipo de Lesión:", ["Muscular", "Tendinosa", "Artículo-ligamentosa", "Fractura", "Otra"])
                        
                        c_L3, c_L4 = st.columns(2)
                        les_zona = c_L3.selectbox("Zona Afectada:", ["Pie", "Tobillo", "Pierna", "Rodilla", "Muslo", "Cadera - Ingles", "Extremidades Superiores", "Tronco", "Cabeza"])
                        
                        zonas_bilaterales = ["Pie", "Tobillo", "Pierna", "Rodilla", "Muslo", "Cadera - Ingles", "Extremidades Superiores"]
                        if les_zona in zonas_bilaterales:
                            les_lado = c_L4.selectbox("Lado:", ["Derecha", "Izquierda"])
                        else:
                            les_lado = "N/A"
                            c_L4.write("") 
                            
                        c_L5, c_L6, c_L7 = st.columns(3)
                        les_lat = c_L5.selectbox("Lateralidad de la lesión:", ["Dominante", "No dominante", "Sin lateralidad"])
                        les_contacto = c_L6.radio("¿Hubo contacto?", ["Sí", "No"], horizontal=True)
                        les_cesped = c_L7.radio("Superficie:", ["Natural", "Artificial"], horizontal=True)
                        
                        c_L8, c_L9 = st.columns([1, 3])
                        les_recidiva = c_L8.radio("¿Es Recidiva?", ["No", "Sí"], horizontal=True)
                        les_comentarios = c_L9.text_input("Comentarios / Mecanismo lesional:")
                        
                        if st.form_submit_button("💾 Registrar Lesión"):
                            nueva_lesion = {
                                "id_sesion": sesion["fecha"],
                                "tipo_sesion": "Partido" if es_partido else "Entrenamiento",
                                "jugador": les_jugador,
                                "tipo": les_tipo,
                                "zona": les_zona,
                                "lado": les_lado,
                                "lateralidad": les_lat,
                                "contacto": les_contacto,
                                "cesped": les_cesped,
                                "recidiva": les_recidiva,
                                "comentarios": les_comentarios,
                                "dias_baja": None,
                                "estado": "Activa",
                                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            st.session_state.lesiones.append(nueva_lesion)
                            guardar_datos()
                            st.success(f"¡Parte médico de {les_jugador} guardado correctamente!")
                            st.rerun()
                st.markdown("---")

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
