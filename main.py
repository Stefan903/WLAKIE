import streamlit as st
import sounddevice as sd
import numpy as np
from flask import Flask
from flask_socketio import SocketIO
import threading
import queue

# Configuración de Flask y SocketIO
flask_app = Flask(__name__)
socketio = SocketIO(flask_app, cors_allowed_origins="*")

# Configuración de audio
RATE = 44100  # Tasa de muestreo
CHUNK = 1024  # Tamaño del búfer de audio

# Variables globales
audio_queue = queue.Queue()
is_recording = False

# Función para grabar audio
def record_audio():
    global is_recording
    st.write("Grabando...")
    with sd.InputStream(samplerate=RATE, channels=1, dtype='int16') as stream:
        while is_recording:
            data, _ = stream.read(CHUNK)
            audio_queue.put(data.tobytes())  # Encolar el audio para enviarlo a los usuarios

# Función para enviar audio a los usuarios
def broadcast_audio(channel):
    while True:
        if not audio_queue.empty():
            data = audio_queue.get()
            socketio.emit('audio_stream', {'data': data}, room=channel)

# Interfaz de Streamlit
st.title("Walkie-Talkie App 🎤")

# Ingreso del nombre
name = st.text_input("Ingresa tu nombre:")

# Ingreso del canal
channel = st.text_input("Ingresa el nombre del canal:")

if name and channel:
    st.write(f"Bienvenido, {name}! Te has unido al canal {channel}.")

    if st.button("Iniciar Grabación"):
        if not is_recording:
            is_recording = True
            threading.Thread(target=record_audio, daemon=True).start()
            threading.Thread(target=broadcast_audio, args=(channel,), daemon=True).start()

    if st.button("Detener Grabación"):
        is_recording = False
        st.write("Grabación detenida.")

if __name__ == '__main__':
    socketio.run(flask_app)
