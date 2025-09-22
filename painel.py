from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import os
import pytz

# fuso horário de São Paulo (Brasília)
fuso = pytz.timezone('America/Sao_Paulo')

app = Flask(__name__)

# Lista de notificações em memória
notificacoes = []

# Lista de máquinas
maquinas = [
    {"nome": "EM-08 7,0", "disponivel": True, "local_trabalho": None},
    {"nome": "EM-11 7,0  24X", "disponivel": True, "local_trabalho": None},
    {"nome": "EEP-01 2,5", "disponivel": True, "local_trabalho": None},
    {"nome": "EEP-02 2,5","disponivel": True, "local_trabalho": None},
    {"nome": "EEC-01 2,5","disponivel": True, "local_trabalho": None},
    {"nome": "EEC-02 2,5","disponivel": True, "local_trabalho": None},
    {"nome": "EM-10 7,0", "disponivel": True, "local_trabalho": None},
    {"nome": "EEC-12 7,0 24X", "disponivel": True, "local_trabalho": None},
    {"nome": "EEC-04 2,5","disponivel": True, "local_trabalho": None},
    {"nome": "EEC-07 2,5", "disponivel": True, "local_trabalho": None},
    {"nome": "EEC-08 2,5", "disponivel": True, "local_trabalho": None},
    {"nome": "PC01 7,O", "disponivel": True, "local_trabalho": None},
]

@app.route("/", methods=["GET", "POST"])
def escolher():
    if request.method == "POST":
        deposito = request.form["deposito"]
        return redirect(url_for("painel", deposito=deposito))
    return render_template("escolher.html")


@app.route('/definir_setor_empilhadeira/<nome>/<setor>', methods=['POST'])
def definir_setor_empilhadeira(nome, setor):
    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = False
            m["setor"] = setor
            return jsonify(success=True, setor=setor)
    return jsonify(success=False)


@app.route("/painel/<deposito>")
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


@app.route("/escritorio")
def escritorio():
    return render_template("escritorio.html")


@app.route("/nova", methods=["POST"])
def nova_notificacao():
    dados = request.get_json()
    nome = dados.get("nome")
    local = dados.get("local")
    setor = dados.get("setor", "")
    mensagem = dados.get("mensagem", "")

    if not nome and not mensagem:
        return jsonify({"success": False, "error": "Faltando dados"}), 400

    agora = datetime.now(fuso)

    notificacoes.append({
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
    })
    return jsonify({"success": True})


@app.route("/atualizar_status/<int:id>/<status>/<deposito>", methods=["POST"])
def atualizar_status(id, status, deposito):
    global notificacoes
    for n in notificacoes:
        if n["id"] == id:
            hora = datetime.now(fuso).strftime("%H:%M:%S")

            if status == "visto":
                n["visto"] = True
                n["hora_visto"] = hora
                return jsonify(success=True, hora=hora)

            if status == "aceito":
                if n.get("deposito_aceitou") and n["deposito_aceitou"] != deposito:
                    return jsonify(success=False, error="Já aceito por outro depósito", hora=hora)
                n["deposito_aceitou"] = deposito
                n["status_horarios"][status] = hora
                n["status"] = status
                n["visto"] = True
                return jsonify(success=True, hora=hora)

            if status in ["no_deposito", "a_caminho", "entregue"]:
                if not n.get("deposito_aceitou"):
                    return jsonify(success=False, error="Nenhum depósito aceitou esta solicitação", hora=hora)
                if n["deposito_aceitou"] != deposito:
                    return jsonify(success=False, error="Somente o depósito que aceitou pode atualizar o status", hora=hora)

                n["status_horarios"][status] = hora
                n["status"] = status
                return jsonify(success=True, hora=hora)

            n["status_horarios"][status] = hora
            n["status"] = status
            return jsonify(success=True, hora=hora)

    return jsonify(success=False)


@app.route("/atualizar_maquina", methods=["POST"])
def atualizar_maquina():
    data = request.get_json()
    nome = data["nome"]
    disponivel = data["disponivel"]
    setor = data.get("setor", "")

    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = disponivel
            m["setor"] = setor if not disponivel else ""
            break
    return jsonify(success=True)


@app.route("/marcar_visto_mensagem/<int:id>/<deposito>", methods=["POST"])
def marcar_visto_mensagem(id, deposito):
    for n in notificacoes:
        if n["id"] == id and n.get("mensagem"):
            if deposito not in n["visto_depositos"]:
                n["visto_depositos"].append(deposito)
            return jsonify(success=True)
    return jsonify(success=False)


@app.route("/notificacoes_ativas/<deposito>")
def notificacoes_ativas(deposito):
    todas = []
    for n in notificacoes:
        if not n.get("visto", False):
            if n["nome"].lower() in ["carro", "empilhadeira"]:
                todas.append(n)
            elif n["local"] == deposito or n["local"] == "todos":
                todas.append(n)
    return jsonify({"notificacoes": todas})


@app.route('/atualizar_empilhadeira/<nome>/<disponivel>', methods=['POST'])
def atualizar_empilhadeira(nome, disponivel):
    disponivel = disponivel.lower() == "true"
    for m in maquinas:
        if m["nome"] == nome:
            m["disponivel"] = disponivel
            if disponivel:
                m["setor"] = ""
            return jsonify(success=True, setor=m.get("setor", ""))
    return jsonify(success=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
