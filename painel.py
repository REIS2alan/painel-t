from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Lista de notificações em memória
notificacoes = []

# Lista de máquinas
maquinas = [
    {"nome": "EM-07", "disponivel": True, "local_trabalho": None},
    {"nome": "EEC-07", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 01", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 02", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 03", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 04", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 05", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 06", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 07", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 08", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 09", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 10", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 11", "disponivel": True, "local_trabalho": None},
    {"nome": "Empilhadeira - 12", "disponivel": True, "local_trabalho": None},
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

    agora = datetime.now()
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
        "status_horarios": {}
    })
    return jsonify({"success": True})

@app.route("/atualizar_status/<int:id>/<status>/<deposito>", methods=["POST"])
def atualizar_status(id, status, deposito):
    global notificacoes
    for n in notificacoes:
        if n["id"] == id:
            hora = datetime.now().strftime("%H:%M:%S")
            if status == "visto":
                n["visto"] = True
                n["hora_visto"] = hora
            else:
                n["status_horarios"][status] = hora
                n["status"] = status
                if status == "aceito":
                    n["visto"] = True
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
        # Inclui apenas notificações não vistas
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
                m["setor"] = ""  # limpa o setor quando volta a estar disponível
            return jsonify(success=True, setor=m.get("setor", ""))
    return jsonify(success=False)







if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
