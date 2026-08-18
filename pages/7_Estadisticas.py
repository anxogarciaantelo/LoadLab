import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    st.stop()

st.title("📈 Estadísticas Globales")

# 1. FILTRAR SÓLO PARTIDOS
partidos = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")]

if not partidos:
    st.info("No hay partidos registrados todavía. Ve a la sección de Entrenamiento y genera un Partido Oficial o Amistoso para empezar a acumular estadísticas.")
    st.stop()

tab_equipo, tab_jugadores = st.tabs(["🛡️ Estadísticas de Equipo", "👤 Estadísticas de Jugadores"])

# ==========================================
# 🛡️ PESTAÑA 1: ESTADÍSTICAS DE EQUIPO
# ==========================================
with tab_equipo:
    st.markdown("### 🏆 Balance de Resultados")
    
    # Cálculos globales
    totales = {
        "Casa": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}, 
        "Fuera": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}
    }
    
    for p in partidos:
        cond = p.get("condicion", "Casa")
        if cond not in totales: cond = "Casa" # Fallback seguridad
        
        gf = p.get("goles_favor", 0)
        gc = p.get("goles_contra", 0)
        
        totales[cond]["P"] += 1
        totales[cond]["GF"] += gf
        totales[cond]["GC"] += gc
        
        if gf > gc: totales[cond]["V"] += 1
        elif gf == gc: totales[cond]["E"] += 1
        else: totales[cond]["D"] += 1
        
    # Agrupación Global
    pj = totales["Casa"]["P"] + totales["Fuera"]["P"]
    v = totales["Casa"]["V"] + totales["Fuera"]["V"]
    e = totales["Casa"]["E"] + totales["Fuera"]["E"]
    d = totales["Casa"]["D"] + totales["Fuera"]["D"]
    gf = totales["Casa"]["GF"] + totales["Fuera"]["GF"]
    gc = totales["Casa"]["GC"] + totales["Fuera"]["GC"]
    dif = gf - gc
    
    # Métricas Globales
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Partidos Jugados", pj)
    c2.metric("Victorias", v)
    c3.metric("Empates", e)
    c4.metric("Derrotas", d)
    c5.metric("Diferencia Goles", f"+{dif}" if dif > 0 else str(dif))
    
    st.markdown("---")
    
    # Desglose Local / Visitante
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🏠 Rendimiento como Local")
        df_casa = pd.DataFrame([{
            "Partidos": totales["Casa"]["P"], "V": totales["Casa"]["V"], 
            "E": totales["Casa"]["E"], "D": totales["Casa"]["D"], 
            "GF": totales["Casa"]["GF"], "GC": totales["Casa"]["GC"]
        }])
        st.dataframe(df_casa, use_container_width=True, hide_index=True)
        
    with col_t2:
        st.markdown("#### ✈️ Rendimiento como Visitante")
        df_fuera = pd.DataFrame([{
            "Partidos": totales["Fuera"]["P"], "V": totales["Fuera"]["V"], 
            "E": totales["Fuera"]["E"], "D": totales["Fuera"]["D"], 
            "GF": totales["Fuera"]["GF"], "GC": totales["Fuera"]["GC"]
        }])
        st.dataframe(df_fuera, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📊 Clasificación / Tabla de Liga")
    
    # Placeholder interactivo para el Iframe de Clasificación
    link_clasificacion = st.text_input(
        "Pega aquí el enlace o iframe de tu liga (ej. BeSoccer, RFEF, etc.):", 
        value=st.session_state.get("link_clasificacion", "")
    )
    if link_clasificacion:
        st.session_state["link_clasificacion"] = link_clasificacion
        if "<iframe" in link_clasificacion:
            st.components.v1.html(link_clasificacion, height=600, scrolling=True)
        else:
            st.info(f"🔗 Enlace guardado: [Ver Clasificación]({link_clasificacion})")
    else:
        st.caption("Aquí podremos integrar el widget web con la clasificación en vivo de tu liga.")

# ==========================================
# 👤 PESTAÑA 2: ESTADÍSTICAS DE JUGADORES
# ==========================================
with tab_jugadores:
    st.markdown("### 📋 Acumulado Individual")
    
    # 1. Inicializar diccionario con todos los jugadores
    datos_jugadores = {}
    for p in st.session_state.plantilla:
        datos_jugadores[p["JUGADOR"]] = {
            "POS": p["POS"], 
            "Convocatorias": 0, 
            "Partidos Jugados": 0,
            "Minutos": 0.0, 
            "Goles": 0, 
            "Asistencias": 0, 
            "Amarillas": 0, 
            "Rojas": 0, 
            "Goles Encajados": 0
        }
    
    # 2. Recorrer partidos para sumar estadísticas
    for p in partidos:
        stats = p.get("estadisticas_partido", {})
        disp = p.get("disponibilidad", {})
        invitados = p.get("estadisticas_invitados", [])
        
        # Sumar Convocatorias desde Disponibilidad (limpiando nombres)
        disp_clean = {k.strip().lower(): v for k, v in disp.items()}
        for jug in datos_jugadores.keys():
            jug_clean = jug.strip().lower()
            if disp_clean.get(jug_clean) in ["Titular", "Suplente"]:
                datos_jugadores[jug]["Convocatorias"] += 1
                
        # Sumar estadísticas de rendimiento de la plantilla
        for jug, vals in stats.items():
            if jug in datos_jugadores:
                mins = vals.get("Minutos", 0)
                datos_jugadores[jug]["Minutos"] += mins
                datos_jugadores[jug]["Goles"] += vals.get("Goles", 0)
                datos_jugadores[jug]["Goles Encajados"] += vals.get("Goles Encajados", 0)
                datos_jugadores[jug]["Asistencias"] += vals.get("Asistencias", 0)
                datos_jugadores[jug]["Amarillas"] += vals.get("Amarillas", 0)
                datos_jugadores[jug]["Rojas"] += vals.get("Rojas", 0)
                
                if mins > 0:
                    datos_jugadores[jug]["Partidos Jugados"] += 1
                    
        # Sumar a invitados/filial
        for inv in invitados:
            n_inv = inv["JUGADOR"]
            if n_inv not in datos_jugadores:
                datos_jugadores[n_inv] = {
                    "POS": inv.get("POS", "CANTERA"), "Convocatorias": 1, "Partidos Jugados": 0,
                    "Minutos": 0.0, "Goles": 0, "Asistencias": 0, "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0
                }
            else:
                datos_jugadores[n_inv]["Convocatorias"] += 1
                
            mins = inv.get("Minutos", 0)
            datos_jugadores[n_inv]["Minutos"] += mins
            datos_jugadores[n_inv]["Goles"] += inv.get("Goles", 0)
            datos_jugadores[n_inv]["Goles Encajados"] += inv.get("Goles Encajados", 0)
            datos_jugadores[n_inv]["Asistencias"] += inv.get("Asistencias", 0)
            datos_jugadores[n_inv]["Amarillas"] += inv.get("Amarillas", 0)
            datos_jugadores[n_inv]["Rojas"] += inv.get("Rojas", 0)
            if mins > 0: datos_jugadores[n_inv]["Partidos Jugados"] += 1

    # 3. Transformar a DataFrame y calcular métricas avanzadas (Goles/90, Asist/90)
    lista_stats = []
    minutos_posibles = pj * 90 if pj > 0 else 0
    
    for jug, d in datos_jugadores.items():
        mins = d["Minutos"]
        goles = d["Goles"]
        asistencias = d["Asistencias"]
        
        goles_90 = (goles / mins * 90) if mins > 0 else 0
        asist_90 = (asistencias / mins * 90) if mins > 0 else 0
        porc_mins = (mins / minutos_posibles * 100) if minutos_posibles > 0 else 0
        
        lista_stats.append({
            "JUGADOR": jug,
            "POS": d["POS"],
            "Conv.": d["Convocatorias"],
            "PJ": d["Partidos Jugados"],
            "MIN": int(mins),
            "% MIN": porc_mins,
            "G": goles,
            "A": asistencias,
            "G/90": goles_90,
            "A/90": asist_90,
            "GE": d["Goles Encajados"],
            "🟨": d["Amarillas"],
            "🟥": d["Rojas"]
        })
        
    df_jugadores = pd.DataFrame(lista_stats)
    
    if not df_jugadores.empty:
        # Ordenamos por minutos jugados por defecto
        df_jugadores = df_jugadores.sort_values(by="MIN", ascending=False)
        
        # Filtros visuales
        c_f1, c_f2 = st.columns(2)
        filtro_pos = c_f1.selectbox("Filtrar por Posición:", ["TODOS", "POR", "DEF", "MED", "ATA", "CANTERA"])
        
        if filtro_pos != "TODOS":
            df_mostrar = df_jugadores[df_jugadores["POS"] == filtro_pos]
        else:
            df_mostrar = df_jugadores
            
        # Tabla estilizada
        st.dataframe(
            df_mostrar.style.format({
                "% MIN": "{:.1f}%",
                "G/90": "{:.2f}",
                "A/90": "{:.2f}"
            }).background_gradient(subset=["MIN", "G", "A"], cmap="Blues"),
            use_container_width=True,
            hide_index=True
        )
        st.caption("Acrónimos: Conv. (Convocatorias) | PJ (Partidos Jugados) | MIN (Minutos) | G (Goles) | A (Asistencias) | G/90 (Goles cada 90') | GE (Goles Encajados porteros).")
