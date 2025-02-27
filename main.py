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
          "project_id": "walkie-c3681",
          "private_key_id": "d9e5139444ec642dee5f02fe9ba15c423dc6934f",
          "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCh5oj22PJZ4tm5\nWbxQsXCVVdxGyXDavsCrWyyN3l3uy1PlY55rhZWbtlEftE9Pfy+sw4wzOIP9bgpw\nPqfA+kn+YAN3Xqk8+lXLKnQ85Pim4XMtDecXTWdyBH4MNIkG+FrlszESn709yPvs\n9Skpa2qahyHB7YubQS5yg0/jVh7ChkZWF6Khl/ittA5KPa5FY+yr6FG2WPsQt6MT\n0DiTbJsNe2ylqJ6wpws8bDVlwte/Gd3J9rFmbrM3ulFdrKpZqGuCX4LDfnINlSuP\nt0VfoubdxfG2SWQvuKj06kyLNoAERIyobF5T4384onlG1nk8zVUSRbQA34kMAZj/\nXJ175a2/AgMBAAECggEAEcIcLttQBez8jbiaj81OuIqg7UDGOLAoqQMIqY0FB57U\n1nntVATkip5eWphoBKPCQnR2id2+mIs76ODufJvXhufYKX1AGfipdW30LwO8hG2B\nOSVnviYW3SpB+yu+Bf4y1jQoA09zLfZAL9caSzlFiaqd2Mwp/n8RTa06k4iMOjDc\nhdOVQINcyid73z2TjvuYEN3oa5ItlIwm9y8ifh3UrHYbxoTWUP0X0Temuu9R8tpt\nBW+zE34KleicME7Elxp9JRDlmW3XydGkIIwNB6seaVMWruvVJXwwHgGAjoJhSabi\nXxcmq3W2HVNqGO5KzskxBK01BcBwfDjH5s5ExBb74QKBgQDXWJvN6l/2O8z0oqc1\nHCwDCS5QAmnWZQI40Eu6fT+grlZIEAvlV9sRQ9jGe5FbjVWL2OJtaSOjZx1Ots9m\nMP4qlmRHFV1dbMBXlG8sJOmYWt5EpNkuMGQ1KyyzFfOpOkxKq0/Utc6/797/bQp1\nOcLWWMK3ehCEaJPUfEb0KKn23wKBgQDAdvjGPF6e1hs8Yvbmr1jjVWm1TBEl0fK4\nsCripa6rDWeNOh6t/iF4lHhw3tTFtclhq2VEABo3b33ByWRiKrpOU/NNsEAOP3Og\nNlIaV+cnpHOvocHVDIxJ+N6TB5O42wWhINR3bvPEduqQOIw5rVJnS97psGfE7Ah2\nsh9hjaWFIQKBgDA/7kjo5q9pHrcBaq1/rmzPtcy/fa9H2oOYSB90yLjb1wE2dzPf\nx3nK1dtC/IKi3DQFWFZjZFTMWci1NSsUdx5brAQxSUYRg9cbrv0ZGC3Gzl5bAT5U\nIV+4WL+Xf4y/PzDLyYtDYRuoRzK738f8NSeJo7cwZlsEg3rsjYlPQyXJAoGAXuaK\n9lxwH4vdNCJsMgVGJBpKnE2cqvRh5XVgQA+IF+ntJHMDC7IiWO2EkcseSTrAyLsV\nnLkcNDdyX+po6Aq/gL3eW3FLtHrPDbGbPEgZv69UJ8bv55hfWF4xiXgT+/NrTC7+\n9MEty7MDKAfqBMqUtkBv8vS7xhrIdZaQ6K5KbmECgYEAyRdfsGzWpCdy7hSGamBg\nI9ZPMY/O7vsB3c7vdt0gCCGa30to6JWRkyjHsiyAJYEZ8u+Em8IZb2wnIF6Hlv+T\nVyUJT1/38LvDU+lIpUNI50lpc5ivg+FpJUiVO/gpHqv6+niDnSSEK5kDX5k13WG1\nTTacpi++OKLWyqBciiY2CKM=\n-----END PRIVATE KEY-----\n",
          "client_email": "firebase-adminsdk-fbsvc@walkie-c3681.iam.gserviceaccount.com",
          "client_id": "102913928283174122005",
          "auth_uri": "https://accounts.google.com/o/oauth2/auth",
          "token_uri": "https://oauth2.googleapis.com/token",
          "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
          "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40walkie-c3681.iam.gserviceaccount.com",
          "universe_domain": "googleapis.com"
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
    
# Ejemplo de un botón
if st.button("Haz clic aquí"):
    st.write("¡Funciona!")
