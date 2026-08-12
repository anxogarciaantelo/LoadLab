import streamlit as st
from database.db_manager import guardar_datos
from utils.math_helpers import get_base64_of_bin_file # O la función que uses para el escudo

def render_panel_principal():
    # --- 5. PANEL PRINCIPAL DEL EQUIPO ---
    st.markdown(f"### 🛡️ Gestión del Equipo: {st.session_state.get('nombre_equipo', 'Mi Equipo')}")
    
    # --- BOTÓN Y EXPANDER DE MODIFICAR CUENTA ---
    with st.expander("⚙️ Modificar Configuración y Datos del Equipo"):
        with st.form("form_modificar_cuenta"):
            nuevo_nombre = st.text_input("Nombre del Equipo", value=st.session_state.get("nombre_equipo", ""))
            nueva_categoria = st.text_input("Categoría", value=st.session_state.get("categoria_equipo", ""))
            nueva_division = st.text_input("División", value=st.session_state.get("division_equipo", ""))
            nueva_temporada = st.text_input("Temporada", value=st.session_state.get("temporada_equipo", ""))
            
            # Selector de color para la barra lateral
            nuevo_color = st.color_picker("Color de la Barra Lateral", value=st.session_state.get("color_sidebar", "#f1f5f9"))
            
            # Escudo
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
    
    # Aquí puedes incluir también el botón de borrar datos o cerrar sesión si los tenías juntos en ese bloque
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
