import streamlit as st
import pyaudio
import wave
import socketio
from flask import Flask
from flask_socketio import SocketIO
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
            frames.append(data)
            socketio.emit('audio_data', {'data': data})
        except Exception as e:
            st.error(f"Error en la grabación: {e}")
            break

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
    st.write(f"Bienvenido, {name}! Te has unido al canal {channel}.")

    if st.button("Iniciar Grabación"):
        threading.Thread(target=record_audio, daemon=True).start()

    if st.button("Detener Grabación"):
        stop_recording()

if __name__ == '__main__':
    socketio.run(flask_app)
