# Baixador de Imagens do Google Fotos

Este script permite baixar automaticamente imagens do Google Fotos baseado em uma pesquisa.

## Requisitos

- Python 3.7 ou superior
- Google Chrome instalado
- Conexão com a internet

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Instale as dependências usando pip:
```bash
pip install -r requirements.txt
```

## Como usar

1. Execute o script:
```bash
python baixar_imagens.py
```

2. Digite o termo que você deseja pesquisar quando solicitado
3. O script irá:
   - Criar uma pasta chamada 'downloads' (se não existir)
   - Pesquisar no Google Fotos
   - Baixar as 10 primeiras imagens encontradas
   - Salvar as imagens na pasta 'downloads'

## Observações

- O script executa o Chrome em modo headless (sem interface gráfica)
- As imagens são salvas com nomes sequenciais (imagem_1.jpg, imagem_2.jpg, etc.)
- Certifique-se de ter espaço suficiente em disco para as imagens 