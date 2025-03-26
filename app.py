from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from baixar_imagens import baixar_imagens, excluir_downloads, download_status
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'  # Necessário para o Flask-WTF

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/baixar', methods=['POST'])
def iniciar_download():
    if download_status['em_andamento']:
        return jsonify({'erro': 'Já existe um download em andamento'})
    
    pesquisa = request.form.get('pesquisa')
    quantidade = int(request.form.get('quantidade'))
    
    if not pesquisa or quantidade <= 0:
        return jsonify({'erro': 'Parâmetros inválidos'})
    
    # Iniciar o download em uma thread separada
    thread = threading.Thread(target=processar_download, args=(pesquisa, quantidade))
    thread.daemon = True
    thread.start()
    
    return jsonify({'mensagem': 'Download iniciado com sucesso!'})

@app.route('/status')
def status_download():
    return jsonify(download_status)

@app.route('/excluir', methods=['POST'])
def excluir_imagens():
    try:
        excluir_downloads()
        return jsonify({'mensagem': 'Imagens excluídas com sucesso!'})
    except Exception as e:
        return jsonify({'erro': str(e)})

@app.route('/downloads/<path:filename>')
def serve_file(filename):
    try:
        return send_file(os.path.join('/tmp/downloads', filename))
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

def processar_download(pesquisa, quantidade):
    try:
        baixar_imagens(pesquisa, quantidade)
    except Exception as e:
        download_status['mensagem'] = f'Erro durante o download: {str(e)}'
    finally:
        download_status['em_andamento'] = False

if __name__ == '__main__':
    app.run(debug=True) 