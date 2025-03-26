from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
from baixar_imagens import baixar_imagens, excluir_downloads, download_status, get_download_base_dir
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

# Cache global para metadados e URLs
metadados_cache = {}
urls_cache = {}

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
    
    # Limitar a quantidade para evitar timeouts na Vercel
    quantidade_ajustada = min(quantidade, 15)
    if quantidade > quantidade_ajustada:
        print(f"Ajustando quantidade de {quantidade} para {quantidade_ajustada} para melhor performance na Vercel")
    
    # Encerrar qualquer thread anterior que possa estar rodando
    if current_download_thread and current_download_thread.is_alive():
        # Não podemos realmente "matar" uma thread em Python,
        # mas podemos garantir que uma nova thread seja criada
        download_status['em_andamento'] = False
    
    # Iniciar o download em uma thread separada
    current_download_thread = threading.Thread(
        target=processar_download, 
        args=(pesquisa, quantidade_ajustada)
    )
    current_download_thread.daemon = True
    current_download_thread.start()
    
    return jsonify({'mensagem': 'Download iniciado com sucesso!'})

@app.route('/status')
def status_download():
    return jsonify(download_status)

@app.route('/excluir', methods=['POST'])
def excluir_imagens():
    global metadados_cache, urls_cache
    try:
        excluir_downloads()
        # Limpar caches
        cache.clear()  
        metadados_cache = {}
        urls_cache = {}
        return jsonify({'mensagem': 'Imagens excluídas com sucesso!'})
    except Exception as e:
        return jsonify({'erro': str(e)})

@app.route('/downloads/<path:filename>')
@cache.cached(timeout=3600, query_string=True)  # Cache das imagens por 1 hora
def serve_file(filename):
    try:
        # Procurar o arquivo em todas as subpastas de downloads
        pasta_downloads = get_download_base_dir()
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
    global metadados_cache
    try:
        # Verificar primeiro no cache global
        if filename in metadados_cache:
            return jsonify({'url': metadados_cache[filename]})
        
        # Procurar o arquivo de metadados em todas as subpastas de downloads
        pasta_downloads = get_download_base_dir()
        
        for root, dirs, files in os.walk(pasta_downloads):
            if 'metadata.json' in files:
                with open(os.path.join(root, 'metadata.json'), 'r') as f:
                    metadata = json.load(f)
                    
                    # Armazenar todo o metadata no cache em memória
                    metadados_cache.update(metadata)
                    
                    if filename in metadata:
                        return jsonify({'url': metadata[filename]})
        return jsonify({'erro': 'URL não encontrada'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

def processar_download(pesquisa, quantidade):
    global urls_cache
    try:
        # Verificar se já temos resultados em cache para essa pesquisa
        if pesquisa in urls_cache and len(urls_cache[pesquisa]) >= quantidade:
            # Usar cache para evitar download repetido
            print(f"Usando cache para pesquisa: {pesquisa}")
            download_status['em_andamento'] = True
            download_status['progresso'] = quantidade
            download_status['total'] = quantidade
            download_status['mensagem'] = f'Recuperando {quantidade} imagens do cache...'
            download_status['urls'] = urls_cache[pesquisa][:quantidade]
            time.sleep(1)  # Pequena pausa para garantir que o frontend perceba a mudança
            download_status['mensagem'] = f'Download concluído! {quantidade} imagens recuperadas do cache.'
        else:
            # Realizar download normal
            baixar_imagens(pesquisa, quantidade)
            # Armazenar resultados no cache
            if download_status['urls']:
                urls_cache[pesquisa] = download_status['urls']
    except Exception as e:
        download_status['mensagem'] = f'Erro durante o download: {str(e)}'
    finally:
        download_status['em_andamento'] = False

@app.after_request
def add_header(response):
    """Adicionar headers para evitar cache de navegador onde não queremos"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

if __name__ == '__main__':
    # Configurar mimetypes comuns para evitar detecção incorreta
    mimetypes.add_type('image/jpeg', '.jpg')
    mimetypes.add_type('image/jpeg', '.jpeg')
    mimetypes.add_type('image/png', '.png')
    mimetypes.add_type('image/gif', '.gif')
    
    app.run(debug=True) 