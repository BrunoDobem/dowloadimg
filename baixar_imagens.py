import requests
import os
from PIL import Image
from io import BytesIO
import time
from dotenv import load_dotenv
import re
import shutil
import json

# Variável global para armazenar o status do download
download_status = {
    'em_andamento': False,
    'progresso': 0,
    'total': 0,
    'mensagem': '',
    'urls': []  # Lista para armazenar as URLs das imagens
}

def excluir_downloads():
    pasta_downloads = os.path.join('/tmp', 'downloads')
    if os.path.exists(pasta_downloads):
        try:
            shutil.rmtree(pasta_downloads)
            print('Todas as imagens e pastas foram excluídas com sucesso!')
        except Exception as e:
            print(f'Erro ao excluir as pastas: {str(e)}')
    else:
        print('Nenhuma pasta de downloads encontrada.')

def criar_pasta_downloads(pesquisa):
    # Criar pasta principal downloads
    pasta_downloads = os.path.join('/tmp', 'downloads')
    if not os.path.exists(pasta_downloads):
        os.makedirs(pasta_downloads)
    
    # Limpar o nome da pesquisa para criar uma pasta válida
    nome_pasta = re.sub(r'[<>:"/\\|?*]', '_', pesquisa)
    nome_pasta = nome_pasta.strip()
    
    # Criar subpasta com o nome da pesquisa
    pasta_pesquisa = os.path.join(pasta_downloads, nome_pasta)
    if not os.path.exists(pasta_pesquisa):
        os.makedirs(pasta_pesquisa)
    
    return pasta_pesquisa

def atualizar_status(progresso, mensagem, urls=None):
    global download_status
    download_status['progresso'] = progresso
    download_status['mensagem'] = mensagem
    if urls is not None:
        download_status['urls'] = urls

def baixar_imagens(pesquisa, quantidade):
    global download_status
    
    # Inicializar o status
    download_status['em_andamento'] = True
    download_status['progresso'] = 0
    download_status['total'] = quantidade
    download_status['urls'] = []
    
    # Criar pasta para downloads e obter o caminho completo
    pasta_pesquisa = criar_pasta_downloads(pesquisa)
    atualizar_status(0, f'Criando pasta para salvar as imagens...')
    
    # Configurar o cabeçalho para simular um navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # URL da API do Bing Images
    url = f'https://www.bing.com/images/search?q={pesquisa}&qft=+filterui:photo-photo&FORM=IRFLTR'
    
    try:
        # Fazer a requisição
        atualizar_status(0, 'Buscando imagens...')
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Encontrar URLs das imagens no HTML
        urls_imagens = []
        for line in response.text.split('\n'):
            if 'murl&quot;:&quot;' in line:
                img_url = line.split('murl&quot;:&quot;')[1].split('&quot;')[0]
                urls_imagens.append(img_url)
        
        # Contador para as imagens baixadas
        contador = 0
        urls_salvas = []  # Lista para armazenar as URLs das imagens baixadas
        metadata = {}  # Dicionário para armazenar os metadados
        
        # Baixar as imagens
        for img_url in urls_imagens:
            if contador >= quantidade:  # Limitar à quantidade escolhida
                break
                
            try:
                # Fazer o download da imagem
                atualizar_status(contador, f'Baixando imagem {contador + 1} de {quantidade}...')
                img_response = requests.get(img_url, headers=headers, timeout=10)
                if img_response.status_code == 200:
                    # Verificar se é realmente uma imagem
                    content_type = img_response.headers.get('content-type', '')
                    if 'image' in content_type:
                        # Salvar a imagem
                        img_data = Image.open(BytesIO(img_response.content))
                        nome_arquivo = f'imagem_{contador + 1}.jpg'
                        caminho_imagem = os.path.join(pasta_pesquisa, nome_arquivo)
                        img_data.save(caminho_imagem)
                        
                        # Armazenar metadados
                        metadata[nome_arquivo] = img_url
                        urls_salvas.append(nome_arquivo)  # Adicionar nome do arquivo à lista
                        contador += 1
                        
                        # Pequena pausa entre os downloads
                        time.sleep(1)
                        
            except Exception as e:
                atualizar_status(contador, f'Erro ao baixar imagem {contador + 1}: {str(e)}')
                continue
        
        # Salvar metadados em um arquivo JSON
        if metadata:
            with open(os.path.join(pasta_pesquisa, 'metadata.json'), 'w') as f:
                json.dump(metadata, f)
        
        atualizar_status(contador, f'Download concluído! {contador} imagens baixadas com sucesso.', urls_salvas)
                
    except Exception as e:
        atualizar_status(0, f'Erro durante a execução: {str(e)}')
        raise e
    finally:
        download_status['em_andamento'] = False

def main():
    print('Escolha uma opção:')
    print('1 - Baixar novas imagens')
    print('2 - Excluir todas as imagens existentes')
    
    while True:
        try:
            opcao = int(input('Digite a opção (1 ou 2): '))
            if opcao in [1, 2]:
                break
            else:
                print('Por favor, digite 1 ou 2.')
        except ValueError:
            print('Por favor, digite um número válido.')
    
    if opcao == 1:
        pesquisa = input('Digite o que você quer pesquisar no Bing Images: ')
        
        while True:
            try:
                quantidade = int(input('Quantas imagens você quer baixar? '))
                if quantidade > 0:
                    break
                else:
                    print('Por favor, digite um número maior que zero.')
            except ValueError:
                print('Por favor, digite um número válido.')
        
        print('Iniciando download das imagens...')
        baixar_imagens(pesquisa, quantidade)
        print('Processo finalizado!')
    else:
        excluir_downloads()

if __name__ == '__main__':
    main() 