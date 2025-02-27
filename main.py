from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import time
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Almacenamiento en memoria (en producción usarías una base de datos)
users = {}
groups = {}
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and check_password_hash(users[username]['password'], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        
        return render_template('login.html', error="Usuario o contraseña incorrectos")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users:
            return render_template('register.html', error="El usuario ya existe")
        
        users[username] = {
            'password': generate_password_hash(password),
            'groups': []
        }
        
        session['username'] = username
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session['username'], 
                           groups=users[session['username']]['groups'],
                           all_groups=list(groups.keys()))

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    group_name = request.form.get('group_name')
    
    if group_name in groups:
        return render_template('dashboard.html', error="El grupo ya existe", 
                               username=session['username'], 
                               groups=users[session['username']]['groups'],
                               all_groups=list(groups.keys()))
    
    group_id = str(uuid.uuid4())
    groups[group_name] = {
        'id': group_id,
        'members': [session['username']],
        'created_by': session['username']
    }
    
    users[session['username']]['groups'].append(group_name)
    
    return redirect(url_for('dashboard'))

@app.route('/join_group', methods=['POST'])
def join_group():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    group_name = request.form.get('group_name')
    
    if group_name not in groups:
        return render_template('dashboard.html', error="El grupo no existe", 
                               username=session['username'], 
                               groups=users[session['username']]['groups'],
                               all_groups=list(groups.keys()))
    
    if session['username'] not in groups[group_name]['members']:
        groups[group_name]['members'].append(session['username'])
        users[session['username']]['groups'].append(group_name)
    
    return redirect(url_for('dashboard'))

@app.route('/group/<group_name>')
def group(group_name):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if group_name not in groups or session['username'] not in groups[group_name]['members']:
        return redirect(url_for('dashboard'))
    
    return render_template('group.html', username=session['username'], group_name=group_name, 
                           members=groups[group_name]['members'])

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        active_users[session['username']] = request.sid
        emit('user_status', {'username': session['username'], 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        if session['username'] in active_users:
            del active_users[session['username']]
        emit('user_status', {'username': session['username'], 'status': 'offline'}, broadcast=True)

@socketio.on('join_group')
def handle_join_group(data):
    username = session.get('username')
    group_name = data['group_name']
    
    if username and group_name in groups and username in groups[group_name]['members']:
        join_room(group_name)
        emit('status', {'msg': f'{username} ha ingresado al grupo {group_name}'}, room=group_name)

@socketio.on('leave_group')
def handle_leave_group(data):
    username = session.get('username')
    group_name = data['group_name']
    
    if username and group_name in groups and username in groups[group_name]['members']:
        leave_room(group_name)
        emit('status', {'msg': f'{username} ha salido del grupo {group_name}'}, room=group_name)

@socketio.on('audio_message')
def handle_audio_message(data):
    username = session.get('username')
    group_name = data['group_name']
    audio_data = data['audio_data']
    
    if username and group_name in groups and username in groups[group_name]['members']:
        emit('audio_broadcast', {
            'username': username,
            'audio_data': audio_data,
            'timestamp': time.time()
        }, room=group_name)

@socketio.on('text_message')
def handle_text_message(data):
    username = session.get('username')
    group_name = data['group_name']
    message = data['message']
    
    if username and group_name in groups and username in groups[group_name]['members']:
        emit('text_broadcast', {
            'username': username,
            'message': message,
            'timestamp': time.time()
        }, room=group_name)

# API endpoints para aplicaciones móviles
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in users and check_password_hash(users[username]['password'], password):
        return {'success': True, 'username': username, 'groups': users[username]['groups']}
    
    return {'success': False, 'error': 'Usuario o contraseña incorrectos'}

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in users:
        return {'success': False, 'error': 'El usuario ya existe'}
    
    users[username] = {
        'password': generate_password_hash(password),
        'groups': []
    }
    
    return {'success': True, 'username': username}

@app.route('/api/groups', methods=['GET'])
def api_groups():
    return {'groups': list(groups.keys())}

@app.route('/api/create_group', methods=['POST'])
def api_create_group():
    data = request.json
    username = data.get('username')
    group_name = data.get('group_name')
    
    if group_name in groups:
        return {'success': False, 'error': 'El grupo ya existe'}
    
    group_id = str(uuid.uuid4())
    groups[group_name] = {
        'id': group_id,
        'members': [username],
        'created_by': username
    }
    
    users[username]['groups'].append(group_name)
    
    return {'success': True, 'group_name': group_name}

@app.route('/api/join_group', methods=['POST'])
def api_join_group():
    data = request.json
    username = data.get('username')
    group_name = data.get('group_name')
    
    if group_name not in groups:
        return {'success': False, 'error': 'El grupo no existe'}
    
    if username not in groups[group_name]['members']:
        groups[group_name]['members'].append(username)
        users[username]['groups'].append(group_name)
    
    return {'success': True, 'group_name': group_name, 'members': groups[group_name]['members']}

if __name__ == '__main__':
    # Crear directorio de plantillas si no existe
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Crear plantillas HTML básicas
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Walkie-Talkie Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <style>
        body { padding: 20px; }
        .container { max-width: 800px; }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="center-align">Walkie-Talkie Web</h2>
        <div class="row">
            <div class="col s12 center-align">
                <a href="/login" class="waves-effect waves-light btn-large">Iniciar Sesión</a>
                <a href="/register" class="waves-effect waves-light btn-large">Registrarse</a>
            </div>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
        ''')
    
    with open('templates/login.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Iniciar Sesión - Walkie-Talkie Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <style>
        body { padding: 20px; }
        .container { max-width: 500px; }
    </style>
</head>
<body>
    <div class="container">
        <h3 class="center-align">Iniciar Sesión</h3>
        {% if error %}
        <div class="card-panel red lighten-3">{{ error }}</div>
        {% endif %}
        <div class="row">
            <form class="col s12" method="POST">
                <div class="row">
                    <div class="input-field col s12">
                        <input id="username" name="username" type="text" class="validate" required>
                        <label for="username">Usuario</label>
                    </div>
                </div>
                <div class="row">
                    <div class="input-field col s12">
                        <input id="password" name="password" type="password" class="validate" required>
                        <label for="password">Contraseña</label>
                    </div>
                </div>
                <div class="row">
                    <div class="col s12 center-align">
                        <button class="btn waves-effect waves-light" type="submit">Iniciar Sesión</button>
                        <a href="/register" class="btn-flat">Registrarse</a>
                    </div>
                </div>
            </form>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
        ''')
    
    with open('templates/register.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Registrarse - Walkie-Talkie Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <style>
        body { padding: 20px; }
        .container { max-width: 500px; }
    </style>
</head>
<body>
    <div class="container">
        <h3 class="center-align">Registrarse</h3>
        {% if error %}
        <div class="card-panel red lighten-3">{{ error }}</div>
        {% endif %}
        <div class="row">
            <form class="col s12" method="POST">
                <div class="row">
                    <div class="input-field col s12">
                        <input id="username" name="username" type="text" class="validate" required>
                        <label for="username">Usuario</label>
                    </div>
                </div>
                <div class="row">
                    <div class="input-field col s12">
                        <input id="password" name="password" type="password" class="validate" required>
                        <label for="password">Contraseña</label>
                    </div>
                </div>
                <div class="row">
                    <div class="col s12 center-align">
                        <button class="btn waves-effect waves-light" type="submit">Registrarse</button>
                        <a href="/login" class="btn-flat">Iniciar Sesión</a>
                    </div>
                </div>
            </form>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
        ''')
    
    with open('templates/dashboard.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Walkie-Talkie Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .container { max-width: 800px; }
        .card-action { display: flex; justify-content: space-between; }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <div class="nav-wrapper">
                <a href="#" class="brand-logo">Walkie-Talkie</a>
                <ul id="nav-mobile" class="right hide-on-med-and-down">
                    <li><a href="/logout">Cerrar Sesión</a></li>
                </ul>
            </div>
        </nav>
        
        <h4>Bienvenido, {{ username }}</h4>
        {% if error %}
        <div class="card-panel red lighten-3">{{ error }}</div>
        {% endif %}
        
        <div class="row">
            <div class="col s12 m6">
                <div class="card">
                    <div class="card-content">
                        <span class="card-title">Crear Grupo</span>
                        <form action="/create_group" method="POST">
                            <div class="input-field">
                                <input id="group_name" name="group_name" type="text" class="validate" required>
                                <label for="group_name">Nombre del Grupo</label>
                            </div>
                            <button class="btn waves-effect waves-light" type="submit">Crear</button>
                        </form>
                    </div>
                </div>
            </div>
            
            <div class="col s12 m6">
                <div class="card">
                    <div class="card-content">
                        <span class="card-title">Unirse a un Grupo</span>
                        <form action="/join_group" method="POST">
                            <div class="input-field">
                                <select id="group_name" name="group_name" class="browser-default" required>
                                    <option value="" disabled selected>Elige un grupo</option>
                                    {% for group in all_groups %}
                                    <option value="{{ group }}">{{ group }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <button class="btn waves-effect waves-light" type="submit">Unirse</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col s12">
                <h5>Mis Grupos</h5>
                <div class="collection">
                    {% for group in groups %}
                    <a href="/group/{{ group }}" class="collection-item">{{ group }}</a>
                    {% else %}
                    <div class="collection-item">No perteneces a ningún grupo todavía.</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
        ''')
    
    with open('templates/group.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>{{ group_name }} - Walkie-Talkie Web</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body { padding: 0; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        nav { padding: 0 20px; }
        .container { flex: 1; display: flex; flex-direction: column; max-width: 100%; width: 100%; margin: 0; padding: 0 20px; }
        #messages { flex: 1; overflow-y: auto; padding: 10px; margin-bottom: 10px; background-color: #f5f5f5; border-radius: 5px; }
        .message { margin: 5px 0; padding: 8px 12px; border-radius: 15px; max-width: 80%; }
        .message.own { background-color: #e3f2fd; margin-left: auto; }
        .message.other { background-color: #f0f0f0; margin-right: auto; }
        .controls { display: flex; padding: 10px 0; }
        .controls button { margin: 0 5px; }
        .audio-controls { display: flex; align-items: center; }
        .members-list { margin-top: 20px; }
        #ptt-button { width: 100%; height: 60px; margin: 10px 0; }
        #text-input { flex: 1; margin-right: 10px; }
    </style>
</head>
<body>
    <nav>
        <div class="nav-wrapper">
            <a href="#" class="brand-logo">{{ group_name }}</a>
            <ul id="nav-mobile" class="right">
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="/logout">Cerrar Sesión</a></li>
            </ul>
        </div>
    </nav>
    
    <div class="container">
        <div id="messages"></div>
        
        <div class="controls">
            <input type="text" id="text-input" placeholder="Escribe un mensaje...">
            <button id="send-text" class="btn waves-effect waves-light">
                <i class="material-icons">send</i>
            </button>
        </div>
        
        <button id="ptt-button" class="btn-large waves-effect waves-light red">
            Mantén presionado para hablar
        </button>
        
        <div class="members-list">
            <h5>Miembros ({{ members|length }})</h5>
            <ul class="collection">
                {% for member in members %}
                <li id="member-{{ member }}" class="collection-item">{{ member }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        // Conectar al servidor Socket.IO
        const socket = io();
        const username = '{{ username }}';
        const groupName = '{{ group_name }}';
        let isRecording = false;
        let mediaRecorder = null;
        let audioChunks = [];
        
        // Unirse al grupo al cargar la página
        socket.emit('join_group', { group_name: groupName });
        
        // Manejar desconexión al cerrar la ventana
        window.addEventListener('beforeunload', () => {
            socket.emit('leave_group', { group_name: groupName });
        });
        
        // Botón PTT (Push-to-Talk)
        const pttButton = document.getElementById('ptt-button');
        
        pttButton.addEventListener('mousedown', startRecording);
        pttButton.addEventListener('touchstart', startRecording);
        
        pttButton.addEventListener('mouseup', stopRecording);
        pttButton.addEventListener('touchend', stopRecording);
        pttButton.addEventListener('mouseleave', stopRecording);
        
        // Entrada de texto
        const textInput = document.getElementById('text-input');
        const sendTextButton = document.getElementById('send-text');
        
        sendTextButton.addEventListener('click', () => {
            const message = textInput.value.trim();
            if (message) {
                socket.emit('text_message', {
                    group_name: groupName,
                    message: message
                });
                textInput.value = '';
            }
        });
        
        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendTextButton.click();
            }
        });
        
        // Recibir mensajes de audio
        socket.on('audio_broadcast', (data) => {
            const messagesContainer = document.getElementById('messages');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${data.username === username ? 'own' : 'other'}`;
            
            const nameSpan = document.createElement('div');
            nameSpan.className = 'message-name';
            nameSpan.textContent = data.username;
            
            const audio = document.createElement('audio');
            audio.controls = true;
            
            // Convertir la base64 a blob y establecerlo como fuente del audio
            const audioBlob = b64toBlob(data.audio_data, 'audio/webm');
            const audioUrl = URL.createObjectURL(audioBlob);
            audio.src = audioUrl;
            
            messageDiv.appendChild(nameSpan);
            messageDiv.appendChild(audio);
            messagesContainer.appendChild(messageDiv);
            
            // Desplazar al último mensaje
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });
        
        // Recibir mensajes de texto
        socket.on('text_broadcast', (data) => {
            const messagesContainer = document.getElementById('messages');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${data.username === username ? 'own' : 'other'}`;
            
            const nameSpan = document.createElement('div');
            nameSpan.className = 'message-name';
            nameSpan.textContent = data.username;
            
            const textSpan = document.createElement('div');
            textSpan.textContent = data.message;
            
            messageDiv.appendChild(nameSpan);
            messageDiv.appendChild(textSpan);
            messagesContainer.appendChild(messageDiv);
            
            // Desplazar al último mensaje
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });
        
        // Estado de usuarios
        socket.on('user_status', (data) => {
            const memberItem = document.getElementById(`member-${data.username}`);
            if (memberItem) {
                if (data.status === 'online') {
                    memberItem.classList.add('active');
                } else {
                    memberItem.classList.remove('active');
                }
            }
        });
        
        // Mensajes de estado
        socket.on('status', (data) => {
            const messagesContainer = document.getElementById('messages');
            
            const statusDiv = document.createElement('div');
            statusDiv.className = 'center-align';
            statusDiv.style.color = '#757575';
            statusDiv.style.margin = '10px 0';
            statusDiv.textContent = data.msg;
            
            messagesContainer.appendChild(statusDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        });
        
        // Funciones auxiliares
        async function startRecording(e) {
            e.preventDefault();
            
            if (isRecording) return;
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                isRecording = true;
                
                pttButton.classList.remove('red');
                pttButton.classList.add('green');
                pttButton.textContent = 'Hablando...';
                
                audioChunks = [];
                mediaRecorder.ondataavailable = (e) => {
                    audioChunks.push(e.data);
                };
                
                mediaRecorder.start();
            } catch (err) {
                console.error('Error al acceder al micrófono:', err);
                alert('No se pudo acceder al micrófono. Verifica que has dado los permisos necesarios.');
            }
        }
        
        function stopRecording(e) {
            e.preventDefault();
            
            if (!isRecording) return;
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                
                // Convertir blob a base64
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = () => {
                    const base64data = reader.result.split(',')[1];
                    
                    // Enviar audio al servidor
                    socket.emit('audio_message', {
                        group_name: groupName,
                        audio_data: base64data
                    });
                };
                
                // Detener todas las pistas
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                
                isRecording = false;
                pttButton.classList.remove('green');
                pttButton.classList.add('red');
                pttButton.textContent = 'Mantén presionado para hablar';
            };
            
            mediaRecorder.stop();
        }
        
        // Convertir base64 a Blob
        function b64toBlob(b64Data, contentType = '', sliceSize = 512) {
            const byteCharacters = atob(b64Data);
            const byteArrays = [];
            
            for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                const slice = byteCharacters.slice(offset, offset + sliceSize);
                
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                
                const byteArray = new Uint8Array(byteNumbers);
                byteArrays.push(byteArray);
            }
            
            const blob = new Blob(byteArrays, { type: contentType });
            return blob;
        }
    </script>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
        ''')
    
    # Iniciar el servidor
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
