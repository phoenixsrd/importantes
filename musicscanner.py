import os
import json
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Bibliotecas externas
try:
    from tinytag import TinyTag
    from ytmusicapi import YTMusic  # <--- A SOLUÇÃO: API do YouTube Music
    from tqdm import tqdm
    from colorama import init, Fore, Style
except ImportError:
    print("❌ Erro: Bibliotecas faltando.")
    print("Execute: pip install ytmusicapi tinytag tqdm colorama")
    exit()

init(autoreset=True)

class MusicScannerUltimate:
    def __init__(self, pasta_musicas):
        self.pasta_musicas = pasta_musicas
        self.ytmusic = YTMusic() # Inicializa a API
        self.formatos_audio = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.opus'}
        self.musicas = []
    
    def obter_termo_busca(self, caminho):
        """Extrai Artista - Título ou limpa o nome do arquivo"""
        try:
            tag = TinyTag.get(caminho)
            if tag.artist and tag.title:
                return f"{tag.artist} {tag.title}"
            elif tag.title:
                return tag.title
        except:
            pass
        # Limpeza do nome do arquivo
        nome = Path(caminho).stem
        return nome.replace('_', ' ').replace('-', ' ').replace('  ', ' ')

    def escanear_local(self):
        """Lê os arquivos do PC"""
        print(f"{Fore.CYAN}📂 Lendo pasta: {self.pasta_musicas}")
        
        if not os.path.exists(self.pasta_musicas):
            print(f"{Fore.RED}❌ Pasta não encontrada!")
            return False

        arquivos = []
        for root, _, files in os.walk(self.pasta_musicas):
            for f in files:
                if Path(f).suffix.lower() in self.formatos_audio:
                    arquivos.append(os.path.join(root, f))
        
        print(f"{Fore.GREEN}✅ Arquivos encontrados: {len(arquivos)}")
        
        print(f"{Fore.YELLOW}🏷️ Processando nomes...")
        for caminho in tqdm(arquivos, unit="arquivos"):
            self.musicas.append({
                'arquivo': os.path.basename(caminho),
                'termo': self.obter_termo_busca(caminho),
                'caminho': caminho,
                'link': None,
                'titulo_yt': None
            })
        return True

    def _buscar_musica(self, musica):
        """Busca uma música específica na API"""
        try:
            # Busca filtrando por "songs" (músicas oficiais)
            # Isso evita videoclipes com introdução ou covers ruins
            resultados = self.ytmusic.search(musica['termo'], filter="songs", limit=1)
            
            if not resultados:
                # Se não achar como música oficial, tenta busca geral (videos)
                resultados = self.ytmusic.search(musica['termo'], filter="videos", limit=1)

            if resultados:
                item = resultados[0]
                video_id = item['videoId']
                musica['link'] = f"https://music.youtube.com/watch?v={video_id}"
                musica['titulo_yt'] = item['title']
                return True
                
        except Exception as e:
            # Erros de conexão silenciosos para não poluir, mas retorna False
            return False
        
        return False

    def buscar_online(self):
        """Gerencia a busca com Threads controladas"""
        total = len(self.musicas)
        print(f"\n{Fore.CYAN}🌍 Buscando no YouTube Music API...")
        print(f"{Style.DIM}Buscando links no music.youtube.com")

        encontrados = 0
        
        # Max workers 3 é o ideal para essa API não bloquear
        with ThreadPoolExecutor(max_workers=3) as executor:
            futuros = {executor.submit(self._buscar_musica, m): m for m in self.musicas}
            
            for future in tqdm(as_completed(futuros), total=total, unit="busca", colour="green"):
                if future.result():
                    encontrados += 1
                else:
                    # Pequeno delay se falhar, para respirar a conexão
                    time.sleep(0.5)

        print(f"\n{Fore.GREEN}✅ Concluído! Sucesso: {encontrados}/{total}")

    def salvar(self):
        """Salva os resultados"""
        print(f"\n{Fore.YELLOW}💾 Salvando arquivos...")
        
        # 1. TXT de Links (Apenas os válidos)
        links_validos = [m['link'] for m in self.musicas if m['link']]
        with open("playlist_links.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(links_validos))

        # 2. HTML Visual (Adaptado para youtube music)
        html = f"""
        <html>
        <head>
            <title>Relatório Musical</title>
            <style>
                body {{ background: #121212; color: #fff; font-family: sans-serif; padding: 20px; }}
                .card {{ background: #282828; padding: 15px; margin: 10px 0; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }}
                a {{ background: #ff0000; color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px; font-weight: bold; }}
                .nome {{ color: #aaa; font-size: 0.9em; }}
                .titulo {{ font-size: 1.1em; font-weight: bold; margin-bottom: 5px; }}
            </style>
        </head>
        <body>
            <h1>Relatório ({len(links_validos)} encontrados)</h1>
            {''.join([f'''
                <div class="card">
                    <div>
                        <div class="titulo">{m['termo']}</div>
                        <div class="nome">{m['arquivo']}</div>
                        <div style="color: #4caf50; font-size: 0.8em;">Detectado: {m['titulo_yt']}</div>
                    </div>
                    <a href="{m['link']}" target="_blank">Ouvir no youtube music</a>
                </div>
            ''' for m in self.musicas if m['link']])}
        </body>
        </html>
        """
        with open("relatorio.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print(f"{Fore.WHITE}👉 Lista salva em: {Style.BRIGHT}playlist_links.txt")
        print(f"{Fore.WHITE}👉 Relatório visual: {Style.BRIGHT}relatorio.html")

def main():
    print(f"{Fore.MAGENTA}🎵 MUSIC SCANNER (YT Music API Edition) 🎵")
    
    pasta = input(f"\n{Fore.YELLOW}Caminho da pasta: {Fore.WHITE}").strip('"')
    
    app = MusicScannerUltimate(pasta)
    if app.escanear_local():
        app.buscar_online()
        app.salvar()
        
    input("\nENTER para sair...")

if __name__ == "__main__":
    main()