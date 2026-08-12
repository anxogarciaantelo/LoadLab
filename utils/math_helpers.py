import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
import streamlit as st

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
