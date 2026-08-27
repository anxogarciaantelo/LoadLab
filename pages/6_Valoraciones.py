import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# Importar nuestras herramientas y base de datos compartida
from utils.math_helpers import *
from utils.pdf_generator import *
from database.db_manager import *

# --- COMPROBACIÓN DE SEGURIDAD Y SESIÓN ---
if not st.session_state.get("autenticado", False) or not st.session_state.get("equipo_seleccionado", False):
    st.warning("⚠️ La sesión ha expirado o no se ha seleccionado un equipo. Por favor, vuelve a iniciar sesión.")
    if st.button("Ir al Login principal"):
        st.session_state.clear()
        st.rerun()
    st.stop()

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
            guardar_datos(modulo="configuracion")
            st.success(f"✅ V. Inicial cargada.")
            st.rerun()
            
    with c_up2:
        f_rom = st.file_uploader("2. ROM y Fuerza ISO", type=["xlsx"], key="up_val_rom")
        if st.button("Procesar ROM/ISO") and f_rom:
            df = pd.read_excel(f_rom)
            col_nombre = next((c for c in df.columns if str(c).upper() in ['JUGADOR', 'NOMBRE']), None)
            if col_nombre: df = sincronizar_nombres_df(df, col_nombre)
            
            st.session_state.val_rom = json.loads(df.to_json(orient='records', date_format='iso'))
            guardar_datos(modulo="configuracion")
            st.success(f"✅ ROM/Fuerza cargados.")
            st.rerun()
            
    with c_up3:
        f_1rm = st.file_uploader("3. Perfil 1RM (Carga/Vel)", type=["xlsx"], key="up_val_1rm")
        if st.button("Procesar 1RM") and f_1rm:
            df = pd.read_excel(f_1rm)
            col_nombre = next((c for c in df.columns if str(c).upper() in ['JUGADOR', 'NOMBRE']), None)
            if col_nombre: df = sincronizar_nombres_df(df, col_nombre)
            
            st.session_state.val_1rm = json.loads(df.to_json(orient='records', date_format='iso'))
            guardar_datos(modulo="configuracion")
            st.success(f"✅ Datos 1RM cargados.")
            st.rerun()
            
    st.markdown("---")
    if st.button("🗑️ Borrar todas las valoraciones"):
        st.session_state.val_inicial, st.session_state.val_rom, st.session_state.val_1rm = [], [], []
        guardar_datos(modulo="configuracion")
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
                        
                        prompt_directo = f"""Eres un preparador físico de élite. Tu ÚNICA tarea es rellenar la plantilla inferior para {jug_sel} usando estos datos:
                        - Asimetrías críticas (>15%): {criticas_txt}
                        - Asimetrías a considerar (10-15%): {mod_txt}
                        - Ratio de Fuerza: {ratio_fuerza:.2f}
                        - Molestias: {molestias_txt}
                        - Sueño: {calidad_sueno}/5

                        REGLA ABSOLUTA: Devuelve ÚNICAMENTE la plantilla completada. Cero razonamientos, cero análisis en inglés, cero "Role:". Si un dato es "Ninguna", indica que está en estado óptimo.

                        📋 **DIAGNÓSTICO CLÍNICO Y FUNCIONAL**
                        [Redacta aquí tu análisis directo de la situación]

                        🛡️ **FASE 1: PREVENCIÓN Y READAPTACIÓN**
                        [Enumera aquí 3 ejercicios clave]

                        ⚡ **FASE 2: DESARROLLO DE FUERZA Y RENDIMIENTO**
                        [Enumera aquí 3 directrices de fuerza]

                        🛌 **ENTRENAMIENTO INVISIBLE**
                        [Pautas sobre su recuperación y sueño]"""

                        modelos_validos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        plan_generado = None
                        
                        for nombre_modelo in modelos_validos:
                            if "2.5-flash" in nombre_modelo: continue
                            try:
                                model = genai.GenerativeModel(nombre_modelo)
                                response = model.generate_content(prompt_directo)
                                texto = response.text.strip()
                                
                                if texto:
                                    # GUILLOTINA PROGRAMÁTICA: Busca el ÚLTIMO 📋 y borra todo el monólogo anterior
                                    if "📋" in texto:
                                        texto = texto[texto.rfind("📋"):]
                                        
                                    plan_generado = texto
                                    break
                            except Exception:
                                continue
                        
                        if plan_generado:
                            st.success(f"¡Plan generado con éxito para {jug_sel}!")
                            st.markdown(plan_generado)
                        else:
                            st.error("No se ha podido conectar con el modelo. Prueba de nuevo.")
                    except Exception as e:
                        st.error(f"Error general al conectar con la API: {e}")
