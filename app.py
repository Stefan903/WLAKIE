import streamlit as st
import pyaudio
import wave
import socketio
from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room
import threading
import queue

# Configuración de Flask y SocketIO
flask_app = Flask(__name__)
socketio = SocketIO(flask_app, cors_allowed_origins="*")

# Configuración de PyAudio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

audio = pyaudio.PyAudio()

# Variables globales
stream = None
frames = []
users = {}
audio_queue = queue.Queue()
MAX_USERS = 25  # Límite de usuarios por canal

# Función para grabar audio
def record_audio():
    global stream
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    st.write("Grabando...")
    while True:
        try:
            data = stream.read(CHUNK)
            audio_queue.put(data)  # Encolar el audio para enviarlo a los usuarios
        except Exception as e:
            st.error(f"Error en la grabación: {e}")
            break

# Función para enviar audio a los usuarios
def broadcast_audio(channel):
    while True:
        if not audio_queue.empty():
            data = audio_queue.get()
            socketio.emit('audio_stream', {'data': data}, room=channel)

# Función para detener la grabación
def stop_recording():
    global stream
    if stream:
        stream.stop_stream()
        stream.close()
    st.write("Grabación detenida.")

# Interfaz de Streamlit
st.title("Walkie-Talkie App 🎤")

# Ingreso del nombre
name = st.text_input("Ingresa tu nombre:")

# Ingreso del canal
channel = st.text_input("Ingresa el nombre del canal:")

if name and channel:
    if len(users.get(channel, [])) >= MAX_USERS:
        st.error("El canal está lleno. Solo se permiten 25 usuarios.")
    else:
        st.write(f"Bienvenido, {name}! Te has unido al canal {channel}.")

        if st.button("Iniciar Grabación"):
            threading.Thread(target=record_audio, daemon=True).start()
            threading.Thread(target=broadcast_audio, args=(channel,), daemon=True).start()

        if st.button("Detener Grabación"):
            stop_recording()

# SocketIO events
@socketio.on('connect')
def handle_connect():
    st.write(f"Usuario {request.sid} conectado")

@socketio.on('disconnect')
def handle_disconnect():
    st.write(f"Usuario {request.sid} desconectado")
    for channel, user_list in users.items():
        if request.sid in user_list:
            user_list.remove(request.sid)
            leave_room(channel)
            socketio.emit('user_left', {'name': user_list[request.sid]}, room=channel)
            del user_list[request.sid]

@socketio.on('join_channel')
def handle_join_channel(data):
    name = data['name']
    channel = data['channel']
    if len(users.get(channel, [])) < MAX_USERS:
        join_room(channel)
        users[channel] = users.get(channel, {})
        users[channel][request.sid] = name
        socketio.emit('user_joined', {'name': name}, room=channel)
    else:
        socketio.emit('channel_full', room=request.sid)

@socketio.on('leave_channel')
def handle_leave_channel(data):
    channel = data['channel']
    if request.sid in users.get(channel, {}):
        leave_room(channel)
        name = users[channel][request.sid]
        del users[channel][request.sid]
        socketio.emit('user_left', {'name': name}, room=channel)

if __name__ == '__main__':
    socketio.run(flask_app)
