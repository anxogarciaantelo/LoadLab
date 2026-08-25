import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Importar las herramientas visuales
from utils.math_helpers import *

# --- COMPROBACIÓN DE SEGURIDAD ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    st.stop()

st.title("📈 Estadísticas de Rendimiento")

partidos_totales = [s for s in st.session_state.sesiones if "Partido" in s.get("tipo", "")]

# ==========================================
# 1. SELECTOR DE COMPETICIÓN
# ==========================================
col_comp1, col_comp2 = st.columns([1, 3])
filtro_competicion = col_comp1.selectbox(
    "🏆 Competición:", 
    ["Liga", "Copa", "Amistosos", "Global"]
)

# Filtrar partidos sin bloquear la pantalla si están a cero
if filtro_competicion == "Global":
    partidos = partidos_totales
elif filtro_competicion == "Amistosos":
    partidos = [p for p in partidos_totales if p.get("tipo") == "Partido Amistoso"]
else:
    partidos = [p for p in partidos_totales if p.get("tipo") == "Partido Oficial" and p.get("competicion") == filtro_competicion]

tab_equipo, tab_jugadores, tab_rivales = st.tabs(["🛡️ Estadísticas de Equipo", "👤 Estadísticas de Jugadores", "🆚 Estadísticas de Rival"])

# ==========================================
# 🛡️ PESTAÑA 1: ESTADÍSTICAS DE EQUIPO
# ==========================================
with tab_equipo:
    st.markdown(f"### 🏆 Balance de Resultados | {filtro_competicion}")
    
    totales = {
        "Casa": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}, 
        "Fuera": {"P": 0, "V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0}
    }
    
    for p in partidos:
        cond = p.get("condicion", "Casa")
        if cond not in totales: cond = "Casa"
        
        gf = p.get("goles_favor", 0)
        gc = p.get("goles_contra", 0)
        
        totales[cond]["P"] += 1
        totales[cond]["GF"] += gf
        totales[cond]["GC"] += gc
        
        if gf > gc: totales[cond]["V"] += 1
        elif gf == gc: totales[cond]["E"] += 1
        else: totales[cond]["D"] += 1
        
    pj = totales["Casa"]["P"] + totales["Fuera"]["P"]
    v = totales["Casa"]["V"] + totales["Fuera"]["V"]
    e = totales["Casa"]["E"] + totales["Fuera"]["E"]
    d = totales["Casa"]["D"] + totales["Fuera"]["D"]
    gf = totales["Casa"]["GF"] + totales["Fuera"]["GF"]
    gc = totales["Casa"]["GC"] + totales["Fuera"]["GC"]
    dif = gf - gc
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Partidos Jugados", pj)
    c2.metric("Victorias", v)
    c3.metric("Empates", e)
    c4.metric("Derrotas", d)
    c5.metric("Diferencia Goles", f"+{dif}" if dif > 0 else str(dif))
    
    st.markdown("---")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🏠 Rendimiento como Local")
        pj_casa = totales["Casa"]["P"]
        gf_pp_casa = (totales["Casa"]["GF"] / pj_casa) if pj_casa > 0 else 0
        gc_pp_casa = (totales["Casa"]["GC"] / pj_casa) if pj_casa > 0 else 0
        
        df_casa = pd.DataFrame([{
            "PJ": pj_casa, "V": totales["Casa"]["V"], "E": totales["Casa"]["E"], "D": totales["Casa"]["D"], 
            "GF": totales["Casa"]["GF"], "GC": totales["Casa"]["GC"], 
            "GF/P": gf_pp_casa, "GC/P": gc_pp_casa
        }])
        mostrar_tabla_moderna(df_casa.style.hide(axis="index").format({"GF/P": "{:.2f}", "GC/P": "{:.2f}"}))
        
    with col_t2:
        st.markdown("#### ✈️ Rendimiento como Visitante")
        pj_fuera = totales["Fuera"]["P"]
        gf_pp_fuera = (totales["Fuera"]["GF"] / pj_fuera) if pj_fuera > 0 else 0
        gc_pp_fuera = (totales["Fuera"]["GC"] / pj_fuera) if pj_fuera > 0 else 0
        
        df_fuera = pd.DataFrame([{
            "PJ": pj_fuera, "V": totales["Fuera"]["V"], "E": totales["Fuera"]["E"], "D": totales["Fuera"]["D"], 
            "GF": totales["Fuera"]["GF"], "GC": totales["Fuera"]["GC"],
            "GF/P": gf_pp_fuera, "GC/P": gc_pp_fuera
        }])
        mostrar_tabla_moderna(df_fuera.style.hide(axis="index").format({"GF/P": "{:.2f}", "GC/P": "{:.2f}"}))

    # ==========================================
    # WIDGETS DE LIGA
    # ==========================================
    if filtro_competicion == "Liga":
        comp_id = st.session_state.get("lapreferente_comp_id", "26710")
        st.markdown("---")
        st.markdown("### 📊 Jornada y Clasificación en Vivo (Liga)")
        
        col_widget1, col_widget2 = st.columns(2)
        
        with col_widget1:
            st.markdown("#### 📋 Clasificación")
            url_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="570" src="{url_clasif}"></iframe>', 
                height=590,
                scrolling=True
            )
            
        with col_widget2:
            st.markdown("#### ⚽ Resultados y Próxima Jornada")
            url_res_actual = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            url_res_prox = f"https://www.lapreferente.com/widgetResultados.php?comp={comp_id}&proximaJornada=1&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
            
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%; margin-bottom: -15px;" height="340" src="{url_res_actual}" scrolling="no"></iframe>', 
                height=345,
                scrolling=False
            )
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="340" src="{url_res_prox}" scrolling="no"></iframe>', 
                height=345,
                scrolling=False
            )

    # ==========================================
    # WIDGETS DE COPA
    # ==========================================
    if filtro_competicion == "Copa":
        copa_comp_id = st.session_state.get("lapreferente_copa_id", "")
        st.markdown("---")
        st.markdown("### 🏆 Información de Copa en Vivo")
        
        if not copa_comp_id:
            st.info("💡 No hay configurado ningún ID de competición para la Copa. Añádelo abajo en la sección de configuración.")
        else:
            col_copa1, col_copa2 = st.columns(2)
            with col_copa1:
                st.markdown("#### 📋 Cuadro / Clasificación de Copa")
                url_copa_clasif = f"https://www.lapreferente.com/widgetClasificacion.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=12&favorito=&ocultaEvolucion=1&ocultaPosicionAnterior=0"
                st.components.v1.html(
                    f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_clasif}"></iframe>', 
                    height=590,
                    scrolling=True
                )
            with col_copa2:
                st.markdown("#### ⚽ Resultados de Copa")
                url_copa_res = f"https://www.lapreferente.com/widgetResultados.php?comp={copa_comp_id}&colorFondo=FFFFFF&colorFondoCabecera=FFFFFF&colorTextoCabecera=000000&anchoEscudos=25&fontSize=12&favorito="
                st.components.v1.html(
                    f'<iframe style="border:0px; width:100%;" height="570" src="{url_copa_res}"></iframe>', 
                    height=590,
                    scrolling=True
                )

# ==========================================
# 👤 PESTAÑA 2: ESTADÍSTICAS DE JUGADORES
# ==========================================
with tab_jugadores:
    st.markdown(f"### 📋 Rendimiento Individual | {filtro_competicion}")
    
    # Crear un diccionario rápido de fotos si existen en la plantilla
    fotos_plantilla = {}
    for p in st.session_state.plantilla:
        fotos_plantilla[p["JUGADOR"].strip().lower()] = p.get("FOTO", p.get("foto", ""))

    datos_jugadores = {}
    for p in st.session_state.plantilla:
        datos_jugadores[p["JUGADOR"]] = {
            "POS": p["POS"], "Convocatorias": 0, "Partidos Jugados": 0,
            "Minutos": 0.0, "Goles": 0, "Asistencias": 0, 
            "Amarillas": 0, "Rojas": 0, "Goles Encajados": 0
        }
    
    for p in partidos:
        stats = p.get("estadisticas_partido", {})
        disp = p.get("disponibilidad", {})
        invitados = p.get("estadisticas_invitados", [])
        
        disp_clean = {k.strip().lower(): v for k, v in disp.items()}
        for jug in datos_jugadores.keys():
            jug_clean = jug.strip().lower()
            if disp_clean.get(jug_clean) in ["Titular", "Suplente"]:
                datos_jugadores[jug]["Convocatorias"] += 1
                
        for jug, vals in stats.items():
            if jug in datos_jugadores:
                mins = vals.get("Minutos", 0)
                datos_jugadores[jug]["Minutos"] += mins
                datos_jugadores[jug]["Goles"] += vals.get("Goles", 0)
                datos_jugadores[jug]["Goles Encajados"] += vals.get("Goles Encajados", 0)
                datos_jugadores[jug]["Asistencias"] += vals.get("Asistencias", 0)
                datos_jugadores[jug]["Amarillas"] += vals.get("Amarillas", 0)
                datos_jugadores[jug]["Rojas"] += vals.get("Rojas", 0)
                if mins > 0: datos_jugadores[jug]["Partidos Jugados"] += 1
                    
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

    # Alertas de tarjetas
    if filtro_competicion in ["Liga", "Global"]:
        apercibidos = []
        sancionados = []
        for jug, d in datos_jugadores.items():
            tarjetas = d["Amarillas"]
            if tarjetas > 0:
                if tarjetas % 5 == 4:
                    apercibidos.append(f"{jug} ({tarjetas} TA)")
                elif tarjetas % 5 == 0:
                    sancionados.append(f"{jug} ({tarjetas} TA)")
                    
        if apercibidos or sancionados:
            st.markdown("#### ⚖️ Alertas Disciplinarias (Ciclos de 5 Amarillas)")
            c_al1, c_al2 = st.columns(2)
            with c_al1:
                if sancionados:
                    for s in sancionados: st.error(f"🛑 **SANCIONADO (Ciclo Cumplido):** {s}")
                else:
                    st.success("✅ Ningún jugador cumple ciclo.")
            with c_al2:
                if apercibidos:
                    for a in apercibidos: st.warning(f"⚠️ **APERCIBIDO (A una amarilla de sanción):** {a}")
                else:
                    st.info("✅ Ningún jugador apercibido.")
            st.markdown("---")

    lista_stats = []
    minutos_posibles = pj * 90 if pj > 0 else 0
    
    for jug, d in datos_jugadores.items():
        mins = d["Minutos"]
        goles = d["Goles"]
        asistencias = d["Asistencias"]
        
        min_por_gol = (mins / goles) if goles > 0 else 0
        min_por_asist = (mins / asistencias) if asistencias > 0 else 0
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
            "Min/Gol": min_por_gol,
            "Min/Asist": min_por_asist,
            "GE": d["Goles Encajados"],
            "🟨 TA": d["Amarillas"],
            "🟥 TR": d["Rojas"]
        })
        
    df_jugadores = pd.DataFrame(lista_stats)
    
    if not df_jugadores.empty:
        df_jugadores = df_jugadores.sort_values(by="MIN", ascending=False)
        
        # ==========================================
        # 👑 DESTACADOS (Tarjetas Top 3 con fotos en base64 y sin numeración)
        # ==========================================
        st.markdown("#### 👑 Destacados")
        
        def render_tarjeta_top3(titulo_categoria, df_sub, columna_valor, sufijo=""):
            st.markdown(f"**{titulo_categoria}**")
            if not df_sub.empty:
                for idx, row in df_sub.reset_index(drop=True).iterrows():
                    val = row[columna_valor]
                    val_str = f"{val:.1f}{sufijo}" if isinstance(val, float) else f"{val}{sufijo}"
                    nombre_jugador = row['JUGADOR']
                    
                    # Comprobar si hay foto en base64 en la plantilla
                    foto_b64 = fotos_plantilla.get(nombre_jugador.strip().lower(), "")
                    if foto_b64:
                        img_src = foto_b64 if str(foto_b64).startswith("http") else f"data:image/jpeg;base64,{foto_b64}"
                        avatar_html = f'<img src="{img_src}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover; margin-right: 8px; vertical-align: middle;">'
                    else:
                        avatar_html = '<span style="font-size: 20px; margin-right: 8px; vertical-align: middle;">👤</span>'

                    st.markdown(
                        f"""
                        <div style="background-color: #f0f2f6; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; border-left: 4px solid #ff4b4b; display: flex; align-items: center;">
                            {avatar_html}
                            <div style="overflow: hidden;">
                                <strong style="font-size: 0.9em; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{nombre_jugador}</strong>
                                <span style="color: #000000; font-weight: bold; font-size: 1.05em;">{val_str}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.caption("Sin datos.")

        col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
        
        with col_d1:
            df_g = df_jugadores[df_jugadores["G"] > 0].sort_values(by="G", ascending=False).head(3)
            render_tarjeta_top3("⚽ Goles", df_g, "G")
            
        with col_d2:
            df_a = df_jugadores[df_jugadores["A"] > 0].sort_values(by="A", ascending=False).head(3)
            render_tarjeta_top3("🎯 Asistencias", df_a, "A")
            
        with col_d3:
            df_m = df_jugadores.sort_values(by="MIN", ascending=False).head(3)
            render_tarjeta_top3("⏱️ Minutos", df_m, "MIN", " min")
            
        with col_d4:
            df_mg = df_jugadores[df_jugadores["Min/Gol"] > 0].sort_values(by="Min/Gol", ascending=True).head(3)
            render_tarjeta_top3("⚡ Min / Gol", df_mg, "Min/Gol", "'")
            
        with col_d5:
            df_ma = df_jugadores[df_jugadores["Min/Asist"] > 0].sort_values(by="Min/Asist", ascending=True).head(3)
            render_tarjeta_top3("🎯 Min / Asist", df_ma, "Min/Asist", "'")

        st.markdown("---")

        # ==========================================
        # 📊 GRÁFICO: MINUTOS ACUMULADOS (Vertical ordenado por POR, DEF, MED, ATA)
        # ==========================================
        st.markdown("#### 📊 Gráfico de Minutos Acumulados por Jugador")
        
        # Definir el orden jerárquico de las posiciones
        orden_posiciones = ["POR", "DEF", "MED", "ATA", "CANTERA"]
        df_jugadores["POS"] = pd.Categorical(df_jugadores["POS"], categories=orden_posiciones, ordered=True)
        
        # Ordenar primero por posición y luego por minutos de mayor a menor dentro de cada posición
        df_jugadores_sorted = df_jugadores.sort_values(by=["POS", "MIN"], ascending=[True, False])

        fig_mins = px.bar(
            df_jugadores_sorted,
            x="JUGADOR",
            y="MIN",
            color="POS",
            orientation="v",
            labels={"MIN": "Minutos Jugados", "JUGADOR": "Jugador", "POS": "Posición"},
            title="Participación de la Plantilla (Minutos totales)"
        )
        fig_mins.update_layout(
            height=450, 
            xaxis={'tickangle': -45, 'categoryorder': 'array', 'categoryarray': df_jugadores_sorted["JUGADOR"].tolist()}, 
            margin=dict(l=20, r=20, t=40, b=80)
        )
        st.plotly_chart(fig_mins, use_container_width=True)

        # ==========================================
        # 🗺️ MAPA DE DISTRIBUCIÓN DE MINUTOS POR LÍNEA (Ordenado POR, DEF, MED, ATA)
        # ==========================================
        st.markdown("#### 🗺️ Distribución de Minutos por Demarcación")
        
        # Filtrar las posiciones que realmente existan y ordenarlas según POR, DEF, MED, ATA...
        posiciones_existentes = [p for p in orden_posiciones if p in df_jugadores["POS"].values]
        
        if len(posiciones_existentes) > 0:
            cols_pos = st.columns(min(len(posiciones_existentes), 5))
            for i, pos_val in enumerate(posiciones_existentes):
                df_subset = df_jugadores[df_jugadores["POS"] == pos_val]
                with cols_pos[i]:
                    fig_circle = px.pie(
                        df_subset,
                        names="JUGADOR",
                        values="MIN",
                        title=f"Línea: {pos_val}",
                        hole=0.4
                    )
                    fig_circle.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
                    st.plotly_chart(fig_circle, use_container_width=True)
        else:
            st.info("Registra minutos en los partidos para ver la distribución.")

        st.markdown("---")
        c_f1, c_f2 = st.columns(2)
        filtro_pos = c_f1.selectbox("Filtro Rápido (Posición):", ["TODOS", "POR", "DEF", "MED", "ATA", "CANTERA"])
        
        if filtro_pos != "TODOS":
            df_mostrar = df_jugadores[df_jugadores["POS"] == filtro_pos]
        else:
            df_mostrar = df_jugadores
            
        st.markdown("##### Tabla Detallada de Rendimiento e Individuales")
        estilo_jugadores = (df_mostrar.style
                            .hide(axis="index")
                            .format({
                                "% MIN": "{:.1f}%", 
                                "Min/Gol": lambda x: f"{x:.1f}'" if x > 0 else "-", 
                                "Min/Asist": lambda x: f"{x:.1f}'" if x > 0 else "-"
                            })
                            .background_gradient(subset=["MIN"], cmap="Blues")
                            .background_gradient(subset=["G"], cmap="Greens")
                            .background_gradient(subset=["🟨 TA"], cmap="YlOrBr")
                           )
                           
        mostrar_tabla_moderna(estilo_jugadores)
        st.caption("Acrónimos: Conv. (Convocatorias) | PJ (Partidos Jugados) | MIN (Minutos) | G (Goles) | A (Asistencias) | Min/Gol (Minutos necesarios por gol) | GE (Goles Encajados porteros).")
# ==========================================
# 🆚 PESTAÑA 3: ESTADÍSTICAS DE RIVAL
# ==========================================
with tab_rivales:
    st.markdown("### 🆚 Análisis de Equipos Rival (LaPreferente)")
    st.caption("Añade los equipos rivales de tu competición introduciendo su nombre y su ID de LaPreferente una sola vez. Se quedarán guardados para toda la temporada.")

    # Inicializar la lista de rivales guardados en session_state si no existe
    if "rivales_guardados" not in st.session_state:
        st.session_state["rivales_guardados"] = {} # Formato: {"Nombre del Equipo": "ID_preferente"}

    # ==========================================
    # SECCIÓN 1: GESTIÓN / AÑADIR RIVAL A MANO
    # ==========================================
    with st.expander("➕ Añadir o Registrar un Nuevo Equipo Rival"):
        with st.form("form_nuevo_rival"):
            col_fn1, col_fn2, col_fn3, col_fn4 = st.columns([2, 1.5, 1.5, 1])
            with col_fn1:
                nombre_nuevo_rival = st.text_input("Nombre del Equipo Rival:")
            with col_fn2:
                id_nuevo_rival = st.text_input("ID LaPreferente:")
            with col_fn3:
                ciudad_rival = st.text_input("Ciudad (Para Clima):")
            with col_fn4:
                st.markdown("<br>", unsafe_allow_html=True)
                submit_rival = st.form_submit_button("💾 Guardar")
            
            if submit_rival:
                if nombre_nuevo_rival:
                    st.session_state["rivales_guardados"][nombre_nuevo_rival.strip()] = {
                        "id": id_nuevo_rival.strip(),
                        "ciudad": ciudad_rival.strip()
                    }
                    guardar_datos()
                    st.success(f"✅ ¡Rival '{nombre_nuevo_rival}' guardado correctamente!")
                    st.rerun()
                else:
                    st.warning("⚠️ Debes rellenar tanto el nombre como el ID.")

    st.markdown("---")

    # ==========================================
    # SECCIÓN 2: CONSULTA DEL RIVAL SELECCIONADO
    # ==========================================
    rivales_disponibles = list(st.session_state["rivales_guardados"].keys())

    if not rivales_disponibles:
        st.info("💡 Aún no hay ningún equipo rival registrado. Utiliza el desplegable de arriba para añadir el primero.")
    else:
        col_sel1, col_sel2 = st.columns([2, 2])
        with col_sel1:
            rival_elegido = st.selectbox("Selecciona un rival guardado:", ["Selecciona un equipo..."] + rivales_disponibles)
            
        if rival_elegido != "Selecciona un equipo...":
            id_equipo_final = st.session_state["rivales_guardados"][rival_elegido]
            comp_id_actual = st.session_state.get("lapreferente_comp_id", "26710")
            
            st.markdown(f"#### 📋 Plantilla y Estadísticas de: **{rival_elegido}**")
            
            url_widget_rival = f"https://www.lapreferente.com/widgetEquipo.php?tipo=plantilla&comp={comp_id_actual}&colorFondo=FFFFFF&colorFondoCabecera=&colorTextoCabecera=FFFFFF&anchoEscudos=25&fontSize=11&favorito=&IDequipo={id_equipo_final}"
            
            st.components.v1.html(
                f'<iframe style="border:0px; width:100%;" height="850" src="{url_widget_rival}" scrolling="yes"></iframe>', 
                height=870,
                scrolling=True
            )
            
            # Botón opcional para eliminar un rival mal introducido
            if st.button(f"🗑️ Eliminar a {rival_elegido} de la lista"):
                del st.session_state["rivales_guardados"][rival_elegido]
                st.success(f"Equipo {rival_elegido} eliminado.")
                st.rerun()
# ==========================================
# ⚙️ CONFIGURACIÓN ABAJO DE TODO EN PANTALLA
# ==========================================
if filtro_competicion in ["Liga", "Copa"]:
    st.markdown("---")
    with st.expander(f"⚙️ Configurar ID de Competición para: {filtro_competicion}"):
        if filtro_competicion == "Liga":
            comp_id_default = st.session_state.get("lapreferente_comp_id", "26710")
            nuevo_comp_id = st.text_input("ID de Competición de Liga (LaPreferente):", value=comp_id_default)
            if nuevo_comp_id != comp_id_default:
                st.session_state["lapreferente_comp_id"] = nuevo_comp_id
                st.success("✅ ID de Liga actualizado correctamente.")
        elif filtro_competicion == "Copa":
            copa_id_default = st.session_state.get("lapreferente_copa_id", "")
            nuevo_copa_id = st.text_input("ID de Competición de Copa (LaPreferente):", value=copa_id_default)
            if nuevo_copa_id != copa_id_default:
                st.session_state["lapreferente_copa_id"] = nuevo_copa_id
                st.success("✅ ID de Copa actualizado correctamente.")
