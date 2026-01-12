import os
import json
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Bibliotecas externas necessárias
try:
    from tinytag import TinyTag
    from youtubesearchpython import VideosSearch
    from tqdm import tqdm
    from colorama import init, Fore, Style
except ImportError:
    print("❌ Erro: Bibliotecas faltando.")
    print("Por favor, instale: pip install tinytag youtube-search-python tqdm colorama")
    exit()

# Inicializa cores
init(autoreset=True)

class MusicScannerPro:
    def __init__(self, pasta_musicas, max_threads=4):
        self.pasta_musicas = pasta_musicas
        self.max_threads = max_threads
        self.formatos_audio = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', 
                               '.wma', '.opus', '.mp4', '.webm', '.ape', '.alac'}
        self.musicas_encontradas = []
    
    def obter_metadados(self, caminho_arquivo):
        """Tenta ler Artista e Título dos metadados do arquivo"""
        try:
            tag = TinyTag.get(caminho_arquivo)
            if tag.artist and tag.title:
                return f"{tag.artist} - {tag.title}"
            elif tag.title:
                return tag.title
        except:
            pass
        # Fallback: retorna o nome do arquivo limpo
        return Path(caminho_arquivo).stem.replace('_', ' ').replace('-', ' ')

    def escanear_pasta(self):
        """Escaneia a pasta recursivamente"""
        print(f"{Fore.CYAN}🔍 Escaneando diretório: {self.pasta_musicas}")
        
        if not os.path.exists(self.pasta_musicas):
            print(f"{Fore.RED}❌ Erro: A pasta não existe!")
            return False
        
        arquivos_para_processar = []
        
        # Coleta arquivos primeiro
        for root, _, files in os.walk(self.pasta_musicas):
            for arquivo in files:
                extensao = Path(arquivo).suffix.lower()
                if extensao in self.formatos_audio:
                    arquivos_para_processar.append(os.path.join(root, arquivo))

        print(f"{Fore.GREEN}✅ Arquivos de áudio detectados: {len(arquivos_para_processar)}")
        
        # Processa metadados com barra de progresso
        print(f"\n{Fore.YELLOW}📖 Lendo metadados e preparando lista...")
        for caminho_completo in tqdm(arquivos_para_processar, unit="música"):
            arquivo = os.path.basename(caminho_completo)
            termo_busca = self.obter_metadados(caminho_completo)
            
            self.musicas_encontradas.append({
                'nome_arquivo': arquivo,
                'termo_busca': termo_busca, # Muito mais preciso que apenas o nome do arquivo
                'caminho': caminho_completo,
                'formato': Path(arquivo).suffix.lower(),
                'link_youtube': None,
                'duracao': None
            })
            
        return True

    def _buscar_single(self, musica):
        """Função interna para buscar uma única música (usada na thread)"""
        try:
            # Pequeno delay aleatório para evitar bloqueio de IP (mesmo com lib externa)
            time.sleep(random.uniform(0.1, 0.5))
            
            videos_search = VideosSearch(musica['termo_busca'], limit=1)
            resultado = videos_search.result()
            
            if resultado['result']:
                video = resultado['result'][0]
                musica['link_youtube'] = video['link']
                musica['titulo_youtube'] = video['title']
                musica['duracao'] = video['duration']
                return True
            else:
                return False
        except Exception as e:
            return False

    def buscar_links_youtube_paralelo(self):
        """Busca links usando múltiplas threads para velocidade"""
        total = len(self.musicas_encontradas)
        if total == 0:
            return

        print(f"\n{Fore.CYAN}🚀 Iniciando busca no YouTube (Threads: {self.max_threads})...")
        print(f"{Style.DIM}Isso será muito mais rápido que o método anterior.\n")

        encontrados = 0
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Cria um dicionário de futuros para rastrear progresso
            future_to_music = {executor.submit(self._buscar_single, m): m for m in self.musicas_encontradas}
            
            # Barra de progresso para as threads
            for future in tqdm(as_completed(future_to_music), total=total, unit="busca", colour="green"):
                if future.result():
                    encontrados += 1

        print(f"\n{Fore.GREEN}✅ Busca concluída! Encontrados: {encontrados}/{total}")

    def gerar_relatorios(self):
        """Gera relatórios JSON e HTML (mais bonito que TXT)"""
        print(f"\n{Fore.YELLOW}💾 Salvando relatórios...")
        
        # 1. JSON (Dados puros)
        with open("relatorio_completo.json", 'w', encoding='utf-8') as f:
            json.dump(self.musicas_encontradas, f, ensure_ascii=False, indent=2)

        # 2. TXT Simples (Links)
        with open("playlist_links.txt", 'w', encoding='utf-8') as f:
            for m in self.musicas_encontradas:
                if m['link_youtube']:
                    f.write(f"{m['link_youtube']}\n")
        
        # 3. HTML Visual (Melhor para leitura humana)
        html_content = f"""
        <html>
        <head>
            <title>Relatório de Músicas</title>
            <style>
                body {{ font-family: sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }}
                .item {{ background: #2d2d2d; padding: 15px; margin-bottom: 10px; border-radius: 8px; }}
                a {{ color: #4facfe; text-decoration: none; }}
                .found {{ border-left: 5px solid #00ff00; }}
                .missing {{ border-left: 5px solid #ff0000; opacity: 0.7; }}
                h3 {{ margin: 0 0 5px 0; }}
                p {{ margin: 5px 0; color: #aaa; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <h1>🎵 Relatório Musical ({len(self.musicas_encontradas)} arquivos)</h1>
            {''.join([
                f'''<div class="item {'found' if m['link_youtube'] else 'missing'}">
                    <h3>{m['termo_busca']}</h3>
                    <p>Arquivo: {m['nome_arquivo']}</p>
                    {f'<p><a href="{m["link_youtube"]}" target="_blank">📺 Assistir no YouTube ({m.get("titulo_youtube", "")})</a></p>' if m['link_youtube'] else '<p>❌ Não encontrado</p>'}
                </div>''' for m in self.musicas_encontradas
            ])}
        </body>
        </html>
        """
        with open("relatorio_visual.html", 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"{Fore.GREEN}📌 Arquivos gerados:")
        print(f"  - {Fore.WHITE}relatorio_visual.html {Style.DIM}(Abra no navegador)")
        print(f"  - {Fore.WHITE}relatorio_completo.json {Style.DIM}(Dados estruturados)")
        print(f"  - {Fore.WHITE}playlist_links.txt {Style.DIM}(Apenas links)")

def main():
    print(f"{Fore.MAGENTA}{Style.BRIGHT}🎵 MUSIC SCANNER PRO 2.0 🎵")
    print("-" * 50)
    
    pasta = input(f"{Fore.YELLOW}📂 Arraste a pasta de músicas aqui ou digite o caminho:\n> {Fore.WHITE}").strip()
    # Remove aspas que o Windows às vezes adiciona ao copiar caminho
    pasta = pasta.strip('"').strip("'")
    
    # Pergunta sobre threads (velocidade)
    try:
        threads = int(input(f"{Fore.YELLOW}⚡ Nível de velocidade (1-10) [Padrão: 4]: {Fore.WHITE}") or 4)
        threads = max(1, min(10, threads)) # Limita entre 1 e 10
    except ValueError:
        threads = 4

    scanner = MusicScannerPro(pasta, max_threads=threads)
    
    if scanner.escanear_pasta():
        buscar = input(f"\n{Fore.CYAN}🔎 Buscar links no YouTube agora? (s/n): {Fore.WHITE}").lower()
        
        if buscar == 's':
            scanner.buscar_links_youtube_paralelo()
        
        scanner.gerar_relatorios()
        
    print(f"\n{Fore.MAGENTA}✨ Processo finalizado.")
    input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()