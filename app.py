from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from baixar_imagens import baixar_imagens, excluir_downloads, download_status
import threading
import time
import json
from flask_compress import Compress
from flask_caching import Cache
import mimetypes

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'  # Necessário para o Flask-WTF

# Configuração de compressão para reduzir tamanho das respostas
Compress(app)

# Configuração de cache para melhorar a performance
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Variável para acompanhar a thread atual
current_download_thread = None

@app.route('/')
@cache.cached(timeout=3600)  # Cache da página inicial por 1 hora
def index():
    return render_template('index.html')

@app.route('/baixar', methods=['POST'])
def iniciar_download():
    global current_download_thread
    
    if download_status['em_andamento']:
        return jsonify({'erro': 'Já existe um download em andamento'})
    
    pesquisa = request.form.get('pesquisa')
    quantidade = int(request.form.get('quantidade'))
    
    if not pesquisa or quantidade <= 0:
        return jsonify({'erro': 'Parâmetros inválidos'})
    
    # Encerrar qualquer thread anterior que possa estar rodando
    if current_download_thread and current_download_thread.is_alive():
        # Não podemos realmente "matar" uma thread em Python,
        # mas podemos garantir que uma nova thread seja criada
        download_status['em_andamento'] = False
    
    # Iniciar o download em uma thread separada
    current_download_thread = threading.Thread(target=processar_download, args=(pesquisa, quantidade))
    current_download_thread.daemon = True
    current_download_thread.start()
    
    return jsonify({'mensagem': 'Download iniciado com sucesso!'})

@app.route('/status')
def status_download():
    return jsonify(download_status)

@app.route('/excluir', methods=['POST'])
def excluir_imagens():
    try:
        excluir_downloads()
        cache.clear()  # Limpar o cache ao excluir imagens
        return jsonify({'mensagem': 'Imagens excluídas com sucesso!'})
    except Exception as e:
        return jsonify({'erro': str(e)})

@app.route('/downloads/<path:filename>')
@cache.cached(timeout=3600, query_string=True)  # Cache das imagens por 1 hora
def serve_file(filename):
    try:
        # Procurar o arquivo em todas as subpastas de downloads
        pasta_downloads = os.path.join('/tmp', 'downloads')
        for root, dirs, files in os.walk(pasta_downloads):
            if filename in files:
                caminho_completo = os.path.join(root, filename)
                
                # Detectar o tipo MIME correto para o arquivo
                tipo_mime = mimetypes.guess_type(caminho_completo)[0]
                
                return send_file(
                    caminho_completo, 
                    mimetype=tipo_mime,
                    as_attachment=False,
                    download_name=filename
                )
        return jsonify({'erro': 'Arquivo não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

@app.route('/metadata/<path:filename>')
@cache.cached(timeout=3600, query_string=True)  # Cache dos metadados por 1 hora
def get_metadata(filename):
    try:
        # Procurar o arquivo de metadados em todas as subpastas de downloads
        pasta_downloads = os.path.join('/tmp', 'downloads')
        
        # Uso de um dicionário global para armazenar metadados em memória
        if not hasattr(app, 'metadata_cache'):
            app.metadata_cache = {}
        
        # Verificar se já temos este metadata em cache
        if filename in app.metadata_cache:
            return jsonify({'url': app.metadata_cache[filename]})
        
        for root, dirs, files in os.walk(pasta_downloads):
            if 'metadata.json' in files:
                with open(os.path.join(root, 'metadata.json'), 'r') as f:
                    metadata = json.load(f)
                    
                    # Armazenar todo o metadata no cache em memória
                    app.metadata_cache.update(metadata)
                    
                    if filename in metadata:
                        return jsonify({'url': metadata[filename]})
        return jsonify({'erro': 'URL não encontrada'}), 404
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
    # Configurar mimetypes comuns para evitar detecção incorreta
    mimetypes.add_type('image/jpeg', '.jpg')
    mimetypes.add_type('image/jpeg', '.jpeg')
    mimetypes.add_type('image/png', '.png')
    mimetypes.add_type('image/gif', '.gif')
    
    app.run(debug=True) 