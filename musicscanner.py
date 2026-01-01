import os
import json
import time
from pathlib import Path
from urllib.parse import quote, urlencode
import urllib.request
import re

class MusicScanner:
    def __init__(self, pasta_musicas):
        self.pasta_musicas = pasta_musicas
        self.formatos_audio = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', 
                               '.wma', '.opus', '.mp4', '.webm', '.ape', '.alac'}
        self.musicas_encontradas = []
    
    def escanear_pasta(self):
        """Escaneia a pasta em busca de arquivos de áudio"""
        print(f"🔍 Escaneando a pasta: {self.pasta_musicas}")
        print("-" * 60)
        
        if not os.path.exists(self.pasta_musicas):
            print(f"❌ Erro: A pasta '{self.pasta_musicas}' não existe!")
            return False
        
        for root, dirs, files in os.walk(self.pasta_musicas):
            for arquivo in files:
                extensao = Path(arquivo).suffix.lower()
                if extensao in self.formatos_audio:
                    caminho_completo = os.path.join(root, arquivo)
                    nome_sem_extensao = Path(arquivo).stem
                    
                    self.musicas_encontradas.append({
                        'nome': nome_sem_extensao,
                        'arquivo_original': arquivo,
                        'caminho': caminho_completo,
                        'formato': extensao,
                        'pasta': root,
                        'link_youtube': None
                    })
        
        print(f"✅ Total de músicas encontradas: {len(self.musicas_encontradas)}")
        return True
    
    def buscar_video_youtube(self, nome_musica):
        """Busca o link direto do vídeo no YouTube"""
        try:
            # Prepara a busca
            query = quote(nome_musica)
            url = f"https://www.youtube.com/results?search_query={query}"
            
            # Faz a requisição
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Procura pelo primeiro videoId nos resultados
            # Padrão: "videoId":"xxxxxxxxxxx"
            match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
            
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"
            else:
                return None
                
        except Exception as e:
            print(f"⚠️  Erro ao buscar '{nome_musica}': {str(e)}")
            return None
    
    def buscar_todos_links_youtube(self, delay=2):
        """Busca os links do YouTube para todas as músicas"""
        print("\n🔎 Buscando links no YouTube...")
        print("⏳ Isso pode levar alguns minutos...\n")
        print("-" * 60)
        
        total = len(self.musicas_encontradas)
        
        for i, musica in enumerate(self.musicas_encontradas, 1):
            print(f"[{i}/{total}] Buscando: {musica['nome'][:50]}...")
            
            link = self.buscar_video_youtube(musica['nome'])
            musica['link_youtube'] = link
            
            if link:
                print(f"    ✅ Encontrado: {link}")
            else:
                print(f"    ❌ Não encontrado")
            
            # Delay entre requisições para não sobrecarregar
            if i < total:
                time.sleep(delay)
        
        print("-" * 60)
        print("✅ Busca concluída!\n")
    
    def salvar_relatorio_txt(self, arquivo_saida="relatorio_musicas.txt"):
        """Salva um relatório em formato TXT"""
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("RELATÓRIO DE MÚSICAS ENCONTRADAS\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Total de músicas: {len(self.musicas_encontradas)}\n\n")
            
            for i, musica in enumerate(self.musicas_encontradas, 1):
                f.write(f"{i}. {musica['nome']}\n")
                f.write(f"   Arquivo: {musica['arquivo_original']}\n")
                f.write(f"   Formato: {musica['formato']}\n")
                f.write(f"   Local: {musica['pasta']}\n")
                
                if musica['link_youtube']:
                    f.write(f"   YouTube: {musica['link_youtube']}\n")
                else:
                    f.write(f"   YouTube: Não encontrado\n")
                
                f.write("-" * 70 + "\n\n")
        
        print(f"📄 Relatório TXT salvo em: {arquivo_saida}")
    
    def salvar_relatorio_json(self, arquivo_saida="relatorio_musicas.json"):
        """Salva um relatório em formato JSON"""
        dados = []
        for musica in self.musicas_encontradas:
            dados.append({
                'nome': musica['nome'],
                'arquivo_original': musica['arquivo_original'],
                'formato': musica['formato'],
                'caminho_completo': musica['caminho'],
                'link_youtube': musica['link_youtube']
            })
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        print(f"📄 Relatório JSON salvo em: {arquivo_saida}")
    
    def salvar_lista_simples(self, arquivo_saida="lista_musicas.txt"):
        """Salva apenas os nomes das músicas em uma lista simples"""
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            for musica in self.musicas_encontradas:
                f.write(f"{musica['nome']}\n")
        
        print(f"📄 Lista simples salva em: {arquivo_saida}")
    
    def salvar_links_youtube(self, arquivo_saida="links_youtube.txt"):
        """Salva apenas os links do YouTube encontrados"""
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("LINKS DIRETOS DO YOUTUBE\n")
            f.write("=" * 70 + "\n\n")
            
            encontrados = 0
            nao_encontrados = 0
            
            for musica in self.musicas_encontradas:
                f.write(f"Música: {musica['nome']}\n")
                if musica['link_youtube']:
                    f.write(f"Link: {musica['link_youtube']}\n\n")
                    encontrados += 1
                else:
                    f.write(f"Link: NÃO ENCONTRADO\n\n")
                    nao_encontrados += 1
            
            f.write("=" * 70 + "\n")
            f.write(f"Links encontrados: {encontrados}\n")
            f.write(f"Links não encontrados: {nao_encontrados}\n")
        
        print(f"📄 Links do YouTube salvos em: {arquivo_saida}")
    
    def salvar_links_apenas_encontrados(self, arquivo_saida="links_encontrados.txt"):
        """Salva apenas os links que foram realmente encontrados"""
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write("LINKS ENCONTRADOS NO YOUTUBE\n")
            f.write("=" * 70 + "\n\n")
            
            count = 0
            for musica in self.musicas_encontradas:
                if musica['link_youtube']:
                    f.write(f"{musica['nome']}\n")
                    f.write(f"{musica['link_youtube']}\n\n")
                    count += 1
            
            f.write("=" * 70 + "\n")
            f.write(f"Total: {count} links encontrados\n")
        
        print(f"📄 Links encontrados salvos em: {arquivo_saida}")
    
    def mostrar_resumo(self):
        """Mostra um resumo das músicas encontradas"""
        if not self.musicas_encontradas:
            print("❌ Nenhuma música encontrada!")
            return
        
        print("\n" + "=" * 60)
        print("📊 RESUMO DAS MÚSICAS ENCONTRADAS")
        print("=" * 60)
        
        # Conta formatos
        formatos = {}
        for musica in self.musicas_encontradas:
            formato = musica['formato']
            formatos[formato] = formatos.get(formato, 0) + 1
        
        print(f"\nTotal: {len(self.musicas_encontradas)} músicas\n")
        print("Por formato:")
        for formato, qtd in sorted(formatos.items()):
            print(f"  {formato}: {qtd} arquivo(s)")
        
        # Conta links do YouTube
        links_encontrados = sum(1 for m in self.musicas_encontradas if m['link_youtube'])
        if links_encontrados > 0:
            print(f"\nLinks do YouTube encontrados: {links_encontrados}/{len(self.musicas_encontradas)}")
        
        print("\n" + "=" * 60)


def main():
    print("🎵 ESCANEADOR DE MÚSICAS E BUSCADOR YOUTUBE 🎵")
    print("=" * 60)
    
    # Solicita a pasta ao usuário
    pasta = input("\n📁 Digite o caminho da pasta com suas músicas: ").strip()
    pasta = pasta.strip('"').strip("'")
    
    # Cria o scanner
    scanner = MusicScanner(pasta)
    
    # Escaneia a pasta
    if scanner.escanear_pasta():
        
        # Pergunta se quer buscar no YouTube
        print("\n" + "=" * 60)
        buscar = input("🔎 Deseja buscar os links no YouTube? (s/n): ").strip().lower()
        
        if buscar == 's':
            scanner.buscar_todos_links_youtube(delay=2)
        
        scanner.mostrar_resumo()
        
        print("\n" + "=" * 60)
        print("💾 SALVANDO RELATÓRIOS...")
        print("=" * 60 + "\n")
        
        # Salva todos os relatórios
        scanner.salvar_relatorio_txt()
        scanner.salvar_relatorio_json()
        scanner.salvar_lista_simples()
        scanner.salvar_links_youtube()
        
        if buscar == 's':
            scanner.salvar_links_apenas_encontrados()
        
        print("\n✅ Processo concluído com sucesso!")
        print("\n📌 Arquivos gerados:")
        print("  - relatorio_musicas.txt (relatório completo)")
        print("  - relatorio_musicas.json (formato estruturado)")
        print("  - lista_musicas.txt (apenas nomes)")
        print("  - links_youtube.txt (todos os links)")
        if buscar == 's':
            print("  - links_encontrados.txt (apenas links encontrados)")
    else:
        print("\n❌ Não foi possível escanear a pasta.")
    
    input("\n\nPressione ENTER para sair...")


if __name__ == "__main__":
    main()