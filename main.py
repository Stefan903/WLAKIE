import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import time
import uuid
import os

# Configuración de Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": os.getenv("type"),
            "project_id": os.getenv("project_id"),
            "private_key_id": os.getenv("private_key_id"),
            "private_key": os.getenv("private_key").replace("\\n", "\n"),
            "client_email": os.getenv("client_email"),
            "client_id": os.getenv("client_id"),
            "auth_uri": os.getenv("auth_uri"),
            "token_uri": os.getenv("token_uri"),
            "auth_provider_x509_cert_url": os.getenv("auth_provider_x509_cert_url"),
            "client_x509_cert_url": os.getenv("client_x509_cert_url"),
            "universe_domain": os.getenv("universe_domain"),
        })
        firebase_admin.initialize_app(cred)

initialize_firebase()
db = firestore.client()

# Estado de la sesión
if 'username' not in st.session_state:
    st.session_state.username = None
if 'current_group' not in st.session_state:
    st.session_state.current_group = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Funciones principales
def create_group():
    group_id = str(uuid.uuid4())[:8]
    group_ref = db.collection('groups').document(group_id)
    group_ref.set({
        'created_at': datetime.now(),
        'members': [st.session_state.username],
        'messages': []
    })
    return group_id

def join_group(group_id):
    group_ref = db.collection('groups').document(group_id)
    if group_ref.get().exists:
        group_ref.update({
            'members': firestore.ArrayUnion([st.session_state.username])
        })
        return True
    return False

def send_message(message):
    if st.session_state.current_group and message:
        group_ref = db.collection('groups').document(st.session_state.current_group)
        group_ref.update({
            'messages': firestore.ArrayUnion([{
                'text': message,
                'sender': st.session_state.username,
                'timestamp': datetime.now().isoformat()
            }])
        })

def get_messages():
    if st.session_state.current_group:
        group_ref = db.collection('groups').document(st.session_state.current_group)
        messages = group_ref.get().to_dict().get('messages', [])
        return sorted(messages, key=lambda x: x['timestamp'])
    return []

# Interfaz de usuario
st.set_page_config(page_title="Walkie-Stream", page_icon="🎙️", layout="wide")
st.title("Walkie-Stream 🎙️")
st.markdown("Crea o únete a un grupo para empezar a chatear en tiempo real.")

# Pantalla de inicio de sesión
if not st.session_state.username:
    with st.form("login_form"):
        username = st.text_input("Ingresa tu nombre de usuario", max_chars=20)
        if st.form_submit_button("Entrar"):
            if username:
                st.session_state.username = username
                st.success(f"¡Bienvenido, {username}!")
                st.experimental_rerun()
            else:
                st.error("Por favor ingresa un nombre de usuario.")

# Pantalla principal
else:
    st.sidebar.title("Opciones")
    if st.sidebar.button("Salir de la aplicación"):
        st.session_state.clear()
        st.experimental_rerun()

    if not st.session_state.current_group:
        st.subheader("Crear o unirse a un grupo")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Crear nuevo grupo")
            if st.button("Crear Grupo"):
                group_id = create_group()
                st.session_state.current_group = group_id
                st.success(f"Grupo creado con ID: {group_id}")
                st.experimental_rerun()

        with col2:
            st.markdown("### Unirse a un grupo existente")
            group_id = st.text_input("Ingresa el ID del grupo")
            if st.button("Unirse al Grupo"):
                if join_group(group_id):
                    st.session_state.current_group = group_id
                    st.success(f"Te has unido al grupo {group_id}!")
                    st.experimental_rerun()
                else:
                    st.error("Grupo no encontrado. Verifica el ID.")

    else:
        st.subheader(f"Grupo: {st.session_state.current_group}")
        st.markdown("---")

        # Área de mensajes
        messages_container = st.container()

        # Actualizar mensajes
        def update_messages():
            messages = get_messages()
            if messages != st.session_state.messages:
                st.session_state.messages = messages
                st.experimental_rerun()

        update_messages()

        # Mostrar mensajes
        with messages_container:
            for msg in st.session_state.messages:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown(f"**{msg['sender']}**")
                    st.caption(msg['timestamp'][11:16])
                with col2:
                    st.info(msg['text'])

        # Enviar mensaje
        message = st.chat_input("Escribe tu mensaje...")
        if message:
            send_message(message)
            time.sleep(0.5)
            update_messages()

        # Auto-refrescar cada 3 segundos
        st_autorefresh(interval=3000, key="chatrefresh")
