from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime
import os
import pytz
from functools import wraps
import pandas as pd
from flask_login import LoginManager, UserMixin, login_required
from io import BytesIO
import csv
from flask import Response
from flask import Flask, send_file
import json  # Adicionado para persistência JSON

# ------------------------
# Configurações iniciais
# ------------------------
fuso = pytz.timezone('America/Sao_Paulo')
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uma_chave_super_secreta")

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Define a rota de login

# Usuários em memória (usuario: senha)
usuarios = {
    "admin": "123456",
    "usuario1": "senha1"
}

# Classe de usuário
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Arquivos para persistência
NOTIFICACOES_FILE = 'notificacoes.json'
MAQUINAS_FILE = 'maquinas.json'

# Funções para salvar/carregar dados
def salvar_notificacoes():
    with open(NOTIFICACOES_FILE, 'w') as f:
        json.dump(notificacoes, f, default=str)  # default=str para serializar datetime

def carregar_notificacoes():
    if os.path.exists(NOTIFICACOES_FILE):
        with open(NOTIFICACOES_FILE, 'r') as f:
            return json.load(f)
    return []

def salvar_maquinas():
    with open(MAQUINAS_FILE, 'w') as f:
        json.dump(maquinas, f)

def carregar_maquinas():
    if os.path.exists(MAQUINAS_FILE):
        with open(MAQUINAS_FILE, 'r') as f:
            return json.load(f)
    return [
        {"nome": "EM-08 7,0", "disponivel": True, "local_trabalho": None},
        {"nome": "EM-11 7,0  24hrs", "disponivel": True, "local_trabalho": None},
        {"nome": "EEP-01 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EEP-02 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-01 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-02 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EM-10 7,0", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-12 7,0 24hrs", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-04 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-07 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "EEC-08 2,5", "disponivel": True, "local_trabalho": None},
        {"nome": "PC01 7,O", "disponivel": True, "local_trabalho": None},
    ]

# Carregar dados na inicialização
notificacoes = carregar_notificacoes()
maquinas = carregar_maquinas()

@login_manager.user_loader
def load_user(user_id):
    if user_id in usuarios:
        return User(user_id)
    return None

# ------------------------
# Decorator para proteger rotas
# ------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_logado" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------
# Login e Logout
# ------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        if usuario in usuarios and usuarios[usuario] == senha:
            session["usuario_logado"] = usuario
            return redirect(url_for("escolher"))
        else:
            return render_template("login.html", erro="Usuário ou senha inválidos")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for("login"))

# ------------------------
# Página inicial: escolher depósito
# ------------------------
@app.route("/", methods=["GET", "POST"])
@login_required
def escolher():
    if request.method == "POST":
        deposito = request.form["deposito"]
        return redirect(url_for("painel", deposito=deposito))
    return render_template("escolher.html")

# ------------------------
# Painel
# ------------------------
@app.route("/painel/<deposito>")
@login_required
def painel(deposito):
    todas = []
    for n in notificacoes:
        if "deposito_aceitou" not in n:
            n["deposito_aceitou"] = None
        if n["nome"].lower() in ["carro", "empilhadeira"]:
            todas.append(n)
        elif n["local"] == deposito:
            todas.append(n)
        elif n["local"] == "todos":
            todas.append(n)
        n["botoes_desabilitados"] = list(n.get("status_horarios", {}).keys())
        if n.get("visto"):
            n["botoes_desabilitados"].append("visto")
    todas_ordenadas = sorted(todas, key=lambda x: x["id"], reverse=True)
    return render_template("index.html", notificacoes=todas_ordenadas, deposito=deposito, maquinas=maquinas)

# ------------------------
# Escritório protegido
# ------------------------
@app.route("/escritorio")
@login_required
def escritorio():
    return render_template("escritorio.html")

# ------------------------
# Notificações
# ------------------------
@app.route("/nova", methods=["POST"])
@login_required
def nova_notificacao():
    dados = request.get_json()
    nome = dados.get("nome")
    local = dados.get("local")
    setor = dados.get("setor", "")
    mensagem = dados.get("mensagem", "")
    if not nome and not mensagem:
        return jsonify({"success": False, "error": "Faltando dados"}), 400
    agora = datetime.now(fuso)
    notificacao = {
        "id": len(notificacoes) + 1,
        "nome": nome if nome else "Aviso Geral",
        "local": local if local else "todos",
        "setor": setor,
        "mensagem": mensagem,
        "visto": False,
        "visto_depositos": [],
        "status": None,
        "data_criacao": agora.strftime("%d/%m/%Y"),
        "hora_criacao": agora.strftime("%H:%M:%S"),
        "hora_visto": None,
        "status_horarios": {},
        "deposito_aceitou": None
    }
    notificacoes.append(notificacao)
    salvar_notificacoes()  # Salva após criar
    return jsonify({"success": True})

@app.route('/exportar')
@login_required
def exportar():
    # Monta DataFrame das notificações
    lista_not = []
    for n in notificacoes:
        lista_not.append({
            'ID': n.get('id', ''),
            'Nome': n.get('nome', ''),
            'Local': n.get('local', ''),
            'Setor': n.get('setor', ''),
            'Mensagem': n.get('mensagem', ''),
            'Data Criação': n.get('data_criacao', ''),
            'Hora Criação': n.get('hora_criacao', ''),
            'Hora Visto': n.get('hora_visto', ''),
            'Status': n.get('status', ''),
            'Status Horários': str(n.get('status_horarios', {})),  # pode ajustar pra formato melhor
            'Visto': n.get('visto', False),
            'Depósito Aceitou': n.get('deposito_aceitou', None),
        })
    df_notificacoes = pd.DataFrame(lista_not)

    # Monta DataFrame das máquinas
    lista_maquinas = []
    for m in maquinas:
        lista_maquinas.append({
            'Nome Máquina': m.get('nome', ''),
            'Disponível': m.get('disponivel', False),
            'Local de Trabalho / Setor': m.get('setor', '') or m.get('local_trabalho', '')
        })
    df_maquinas = pd.DataFrame(lista_maquinas)

    # Cria arquivo Excel em memória
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_notificacoes.to_excel(writer, index=False, sheet_name='Notificações')
        df_maquinas.to_excel(writer, index=False, sheet_name='Máquinas')
        # Você pode adicionar mais abas aqui, ex:
        # df_usuarios.to_excel(writer, index=False, sheet_name='Usuários')

    output.seek(0)

    return send_file(
        output,
        download_name='painel_completo.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route("/atualizar_status/<int:id>/<status>/<deposito>", methods=["POST"])
@login_required
def atualizar_status(id, status, deposito):
    for n in notificacoes:
        if n["id"] == id:
            hora = datetime.now(fuso).strftime("%H:%M:%S")
            if status == "visto":
                n["visto"] = True
                n["hora_visto"] = hora
                salvar_notificacoes()  # Salva após atualizar
                return jsonify(success=True, hora=hora)
            if status == "aceito":
                if n.get("deposito_aceitou") and n["deposito_aceitou"] != deposito:
                    return jsonify(success=False, error="Já aceito por outro depósito", hora=hora)
                n["deposito_aceitou"] = deposito
                n["status_horarios"][status] = hora
                n["status"] = status
                n["visto"] = True
                salvar_notificacoes()  # Salva após atualizar
                return jsonify(success=True, hora=hora)
            if status in ["no_deposito", "a_caminho", "entregue"]:
                if not n.get("deposito_aceitou"):
                    return jsonify(success=False, error="Nenhum depósito aceitou esta solicitação", hora=hora)
                if n["deposito_aceitou"] != deposito:
                    return jsonify(success=False, error="Somente o depósito que aceitou pode atualizar o status", hora=hora)
                n["status_horarios"][status] = hora
                n["status"] = status
                salvar_notificacoes()  # Salva após atualizar
                return jsonify(success=True, hora=hora)
            n["status_horarios"][status] = hora
            n["status"] = status
            salvar_notificacoes()  # Salva após atualizar
            return jsonify(success=True, hora=hora)
    return jsonify(success=False)

# ------------------------
# Máquinas
# ------------------------
@app.route("/atualizar_maquina", methods=["POST"])
@login_required
def atualizar_maquina():
    data = request.get_json()
    nome = data["nome"]
    disponivel = data["disponivel"]
    setor = data.get("setor", "")
    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = disponivel
            m["setor"] = setor if not disponivel else ""
            salvar_maquinas()  # Salva após atualizar
            break
    return jsonify(success=True)

@app.route('/definir_setor_empilhadeira/<nome>/<setor>', methods=['POST'])
@login_required
def definir_setor_empilhadeira(nome, setor):
    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = False
            m["setor"] = setor
            salvar_maquinas()  # Salva após atualizar
            return jsonify(success=True, setor=setor)
    return jsonify(success=False)

@app.route('/atualizar_empilhadeira/<nome>/<disponivel>', methods=['POST'])
@login_required
def atualizar_empilhadeira(nome, disponivel):
    disponivel = disponivel.lower() == "true"
    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = disponivel
            if disponivel:
                m["setor"] = ""
            salvar_maquinas()  # Salva após atualizar
            return jsonify(success=True, setor=m.get("setor", ""))
    return jsonify(success=False)

# ------------------------
# Marcar visto
# ------------------------
@app.route("/marcar_visto_mensagem/<int:id>/<deposito>", methods=["POST"])
@login_required
def marcar_visto_mensagem(id, deposito):
    for n in notificacoes:
        if n["id"] == id and n.get("mensagem"):
            if deposito not in n["visto_depositos"]:
                n["visto_depositos"].append(deposito)
            salvar_notificacoes()  # Salva após atualizar
            return jsonify(success=True)
    return jsonify(success=False)

# ------------------------
# Notificações ativas
# ------------------------
@app.route("/notificacoes_ativas/<deposito>")
@login_required
def notificacoes_ativas(deposito):
    todas = []
    for n in notificacoes:
        if not n.get("visto", False):
            if n["nome"].lower() in ["carro", "empilhadeira"]:
                todas.append(n)
            elif n["local"] == deposito or n["local"] == "todos":
                todas.append(n)
    return jsonify({"notificacoes": todas})

# ------------------------
# Run
# ------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
