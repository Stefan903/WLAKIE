import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import time
import uuid
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Estado de la sesión
if 'username' not in st.session_state:
    st.session_state.username = None
if 'current_group' not in st.session_state:
    st.session_state.current_group = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

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
st.title("Walkie-Stream 🎙️")

# Pantalla de inicio de sesión
if not st.session_state.username:
    username = st.text_input("Ingresa tu nombre de usuario")
    if st.button("Entrar"):
        if username:
            st.session_state.username = username
        else:
            st.error("Por favor ingresa un nombre de usuario")

# Pantalla principal
else:
    if not st.session_state.current_group:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Crear nuevo grupo")
            if st.button("Crear Grupo"):
                group_id = create_group()
                st.session_state.current_group = group_id
                st.experimental_rerun()
        
        with col2:
            st.subheader("Unirse a grupo existente")
            group_id = st.text_input("ID del grupo")
            if st.button("Unirse al Grupo"):
                if join_group(group_id):
                    st.session_state.current_group = group_id
                    st.experimental_rerun()
                else:
                    st.error("Grupo no encontrado")
    else:
        st.subheader(f"Grupo: {st.session_state.current_group}")
        
        # Área de mensajes
        messages_container = st.empty()
        
        # Actualizar mensajes
        def update_messages():
            messages = get_messages()
            if messages != st.session_state.messages:
                st.session_state.messages = messages
                st.experimental_rerun()
        
        update_messages()
        
        # Mostrar mensajes
        with messages_container.container():
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

if st.button("Salir de la aplicación"):
    st.session_state.clear()
    st.experimental_rerun()
    
    # Iniciar el servidor
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
