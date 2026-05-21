#!/usr/bin/env python3
"""
███╗   ███╗██╗   ██╗███████╗██╗ ██████╗
████╗ ████║██║   ██║██╔════╝██║██╔════╝
██╔████╔██║██║   ██║███████╗██║██║
██║╚██╔╝██║██║   ██║╚════██║██║██║
██║ ╚═╝ ██║╚██████╔╝███████║██║╚██████╗
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝ ╚═════╝
██████╗  ██████╗  █████╗ ███╗   ██╗███╗   ██╗███████╗██████╗
██╔══██╗██╔════╝ ██╔══██╗████╗  ██║████╗  ██║██╔════╝██╔══██╗
██████╔╝██║  ███╗███████║██╔██╗ ██║██╔██╗ ██║█████╗  ██████╔╝
██╔═══╝ ██║   ██║██╔══██║██║╚██╗██║██║╚██╗██║██╔══╝  ██╔══██╗
██║     ╚██████╔╝██║  ██║██║ ╚████║██║ ╚████║███████╗██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝
Music Scanner Ultimate 2.0 — YT Music API Edition
"""

import os
import json
import time
import random
import logging
import hashlib
import re
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple

# ─────────────────────────────────────────────
# Dependências
# ─────────────────────────────────────────────
try:
    from tinytag import TinyTag
    from ytmusicapi import YTMusic
    from tqdm import tqdm
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError as e:
    print(f"\n❌  Biblioteca em falta: {e}")
    print("Execute:\n  pip install ytmusicapi tinytag tqdm colorama\n")
    exit(1)

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
LOG_FILE = Path("musicscanner.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger("musicscanner")


# ─────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────
FORMATOS_AUDIO = {
    ".mp3", ".wav", ".flac", ".m4a", ".aac",
    ".ogg", ".wma", ".opus", ".ape", ".alac",
    ".aiff", ".mp4", ".webm",
}

MAX_WORKERS   = 3      # Máximo seguro para a YT Music API
RETRY_MAX     = 3      # Tentativas por música
RETRY_BACKOFF = 2.0    # Backoff exponencial (segundos)
CACHE_FILE    = Path(".musicscanner_cache.json")


# ─────────────────────────────────────────────
# Utilitários de cor
# ─────────────────────────────────────────────
class C:
    TITLE = Fore.MAGENTA + Style.BRIGHT
    OK    = Fore.GREEN
    WARN  = Fore.YELLOW
    ERR   = Fore.RED + Style.BRIGHT
    INFO  = Fore.CYAN
    DIM   = Style.DIM
    BOLD  = Style.BRIGHT
    RESET = Style.RESET_ALL

    @staticmethod
    def header(text):
        w = 62
        print(f"\n{C.TITLE}╭{'─'*w}╮")
        print(f"│  {text:<{w-2}}│")
        print(f"╰{'─'*w}╯{C.RESET}\n")

    @staticmethod
    def ok(msg):   print(f"{C.OK}  ✅  {msg}{C.RESET}")
    @staticmethod
    def warn(msg): print(f"{C.WARN}  ⚠️   {msg}{C.RESET}")
    @staticmethod
    def err(msg):  print(f"{C.ERR}  ❌  {msg}{C.RESET}")
    @staticmethod
    def info(msg): print(f"{C.INFO}  ℹ️   {msg}{C.RESET}")


# ─────────────────────────────────────────────
# CACHE DE RESULTADOS (evita re-buscar)
# ─────────────────────────────────────────────
class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, Dict] = {}
        self._load()

    def _key(self, term: str) -> str:
        return hashlib.md5(term.lower().encode()).hexdigest()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"Cache carregado: {len(self.data)} entradas")
            except Exception:
                self.data = {}

    def get(self, term: str) -> Optional[Dict]:
        return self.data.get(self._key(term))

    def set(self, term: str, result: Dict):
        self.data[self._key(term)] = result
        self._save()

    def _save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")


# ─────────────────────────────────────────────
# SCANNER PRINCIPAL
# ─────────────────────────────────────────────
class MusicScannerUltimate:
    def __init__(self, pasta_musicas: str,
                 output_dir: str = ".",
                 resume: bool = True,
                 min_score: int = 0):

        self.pasta      = Path(pasta_musicas)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.resume     = resume
        self.min_score  = min_score
        self.musicas:   List[Dict] = []
        self.cache      = Cache(CACHE_FILE)

        try:
            self.ytmusic = YTMusic()
        except Exception as e:
            C.err(f"Erro ao inicializar YTMusic API: {e}")
            exit(1)

    # ─── Extração de metadados ────────────────────────────────────────────────
    def _extrair_metadados(self, caminho: Path) -> Dict:
        """Extrai metadados completos do arquivo de áudio."""
        meta = {
            "arquivo":  caminho.name,
            "caminho":  str(caminho),
            "tamanho":  caminho.stat().st_size,
            "artista":  None,
            "titulo":   None,
            "album":    None,
            "ano":      None,
            "genero":   None,
            "duracao":  None,
            "link":     None,
            "titulo_yt": None,
            "artista_yt": None,
            "album_yt":  None,
            "thumb_yt":  None,
            "score":    0,
            "termo":    None,
        }
        try:
            tag = TinyTag.get(caminho)
            meta["artista"] = tag.artist
            meta["titulo"]  = tag.title
            meta["album"]   = tag.album
            meta["ano"]     = tag.year
            meta["genero"]  = tag.genre
            meta["duracao"] = tag.duration

            if tag.artist and tag.title:
                meta["termo"] = f"{tag.artist} - {tag.title}"
            elif tag.title:
                meta["termo"] = tag.title
        except Exception:
            pass

        if not meta["termo"]:
            # Limpa o nome do arquivo
            nome = caminho.stem
            nome = re.sub(r"\[.*?\]|\(.*?\)", "", nome)  # remove colchetes e parênteses
            nome = re.sub(r"[\-_]+", " ", nome)
            nome = re.sub(r"\s{2,}", " ", nome).strip()
            meta["termo"] = nome

        return meta

    # ─── Scan local ───────────────────────────────────────────────────────────
    def escanear_local(self) -> bool:
        C.header(f"📂 Escaneando: {self.pasta}")

        if not self.pasta.exists():
            C.err(f"Pasta não encontrada: {self.pasta}")
            return False

        arquivos = [
            p for p in self.pasta.rglob("*")
            if p.is_file() and p.suffix.lower() in FORMATOS_AUDIO
        ]

        if not arquivos:
            C.warn("Nenhum arquivo de áudio encontrado.")
            return False

        C.ok(f"Arquivos encontrados: {len(arquivos)}")
        C.info("Lendo metadados...")

        for caminho in tqdm(arquivos, unit="arq", colour="cyan"):
            self.musicas.append(self._extrair_metadados(caminho))

        # Estatísticas de metadados
        com_meta = sum(1 for m in self.musicas if m["artista"] and m["titulo"])
        C.info(f"Com metadados completos: {com_meta}/{len(self.musicas)}")
        return True

    # ─── Busca online (com retry + cache) ────────────────────────────────────
    def _buscar_uma(self, musica: Dict) -> bool:
        """Busca uma música com retry e backoff exponencial."""
        termo = musica["termo"]

        # Tenta cache primeiro
        cached = self.cache.get(termo)
        if cached:
            musica.update(cached)
            return bool(musica.get("link"))

        for tentativa in range(RETRY_MAX):
            try:
                # Prioridade: songs > videos
                for filtro in ("songs", "videos"):
                    resultados = self.ytmusic.search(termo, filter=filtro, limit=3)
                    if resultados:
                        item = resultados[0]
                        video_id = item.get("videoId")
                        if not video_id:
                            continue

                        result = {
                            "link":       f"https://music.youtube.com/watch?v={video_id}",
                            "titulo_yt":  item.get("title"),
                            "artista_yt": (item.get("artists") or [{}])[0].get("name"),
                            "album_yt":   (item.get("album") or {}).get("name"),
                            "thumb_yt":   (
                                (item.get("thumbnails") or [{}])[-1].get("url")
                            ),
                        }
                        musica.update(result)
                        self.cache.set(termo, result)
                        return True

                return False

            except Exception as e:
                logger.warning(f"Tentativa {tentativa+1}/{RETRY_MAX} falhou para '{termo}': {e}")
                if tentativa < RETRY_MAX - 1:
                    sleep_t = RETRY_BACKOFF ** (tentativa + 1) + random.uniform(0, 1)
                    time.sleep(sleep_t)

        return False

    # ─── Busca em paralelo ────────────────────────────────────────────────────
    def buscar_online(self):
        total = len(self.musicas)
        C.header(f"🌍 Buscando no YouTube Music: {total} músicas")

        # Filtra as que já têm link (se --resume)
        pendentes = self.musicas if not self.resume else [
            m for m in self.musicas if not m.get("link")
        ]
        ja_encontradas = total - len(pendentes)

        if ja_encontradas:
            C.info(f"Já encontradas (cache/resume): {ja_encontradas}")

        encontradas = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futuros = {ex.submit(self._buscar_uma, m): m for m in pendentes}
            bar = tqdm(as_completed(futuros), total=len(pendentes),
                       unit="busca", colour="green",
                       bar_format="{l_bar}{bar:40}{r_bar}")

            for fut in bar:
                if fut.result():
                    encontradas += 1
                    bar.set_postfix_str(f"✅ {encontradas}")
                else:
                    time.sleep(0.3)

        total_ok = encontradas + ja_encontradas
        C.ok(f"Concluído! Sucesso: {total_ok}/{total}")

    # ─── Exportar resultados ──────────────────────────────────────────────────
    def salvar(self):
        C.header("💾 Exportando resultados")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        validas = [m for m in self.musicas if m.get("link")]
        sem_link = [m for m in self.musicas if not m.get("link")]

        # 1. TXT de links (compatível com yt-dlp -a)
        txt_path = self.output_dir / f"playlist_links_{ts}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(m["link"] for m in validas))
        C.ok(f"Links TXT: {txt_path}")

        # 2. M3U Playlist (compatível com VLC, Winamp, etc.)
        m3u_path = self.output_dir / f"playlist_{ts}.m3u8"
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for m in self.musicas:
                dur    = int(m.get("duracao") or -1)
                artista = m.get("artista_yt") or m.get("artista") or "?"
                titulo  = m.get("titulo_yt")  or m.get("titulo")  or m["arquivo"]
                f.write(f"#EXTINF:{dur},{artista} - {titulo}\n")
                if m.get("link"):
                    f.write(m["link"] + "\n")
                else:
                    f.write(m["caminho"] + "\n")
        C.ok(f"Playlist M3U8: {m3u_path}")

        # 3. JSON completo
        json_path = self.output_dir / f"musicscanner_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.musicas, f, indent=2, ensure_ascii=False, default=str)
        C.ok(f"JSON completo: {json_path}")

        # 4. HTML Visual (dark mode, thumbnails, filtros)
        html_path = self.output_dir / f"relatorio_{ts}.html"
        self._gerar_html(html_path, validas, sem_link, ts)
        C.ok(f"Relatório HTML: {html_path}")

        # 5. Resumo
        print(f"\n{C.BOLD}  Estatísticas finais{C.RESET}")
        print(f"  {'Total de músicas':<30} {len(self.musicas)}")
        print(f"  {'Encontradas no YT Music':<30} {len(validas)}")
        print(f"  {'Não encontradas':<30} {len(sem_link)}")
        print(f"  {'Taxa de sucesso':<30} {len(validas)/len(self.musicas)*100:.1f}%\n")

        if sem_link:
            nf_path = self.output_dir / f"nao_encontradas_{ts}.txt"
            with open(nf_path, "w", encoding="utf-8") as f:
                f.write("\n".join(m["arquivo"] for m in sem_link))
            C.warn(f"Não encontradas salvas: {nf_path}")

    def _gerar_html(self, path: Path, validas: List[Dict],
                    sem_link: List[Dict], ts: str):
        """Gera relatório HTML rico com dark mode, thumbnails e filtros."""

        def card(m: Dict, found: bool) -> str:
            thumb = m.get("thumb_yt") or ""
            artista = m.get("artista_yt") or m.get("artista") or "—"
            titulo  = m.get("titulo_yt")  or m.get("titulo")  or m["arquivo"]
            album   = m.get("album_yt")   or m.get("album")   or ""
            link    = m.get("link", "#")
            dur     = m.get("duracao")
            dur_str = (f"{int(dur)//60}:{int(dur)%60:02d}") if dur else "—"
            badge_class = "badge-ok" if found else "badge-fail"
            badge_text  = "✅ Encontrado" if found else "❌ Não encontrado"

            thumb_html = (
                f'<img src="{thumb}" alt="thumb" class="thumb">'
                if thumb else '<div class="thumb-placeholder">🎵</div>'
            )

            return f"""
            <div class="card" data-status="{'found' if found else 'missing'}">
                {thumb_html}
                <div class="info">
                    <div class="titulo">{titulo}</div>
                    <div class="artista">{artista}</div>
                    {"<div class='album'>💿 " + album + "</div>" if album else ""}
                    <div class="meta">
                        <span class="badge {badge_class}">{badge_text}</span>
                        <span class="dur">⏱ {dur_str}</span>
                        <span class="arquivo" title="{m['arquivo']}">{m['arquivo'][:50]}{'…' if len(m['arquivo'])>50 else ''}</span>
                    </div>
                </div>
                {"<a href='" + link + "' target='_blank' class='btn'>▶ Ouvir</a>" if found else ""}
            </div>"""

        cards_found  = "\n".join(card(m, True)  for m in validas)
        cards_missing= "\n".join(card(m, False) for m in sem_link)

        html = f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🎵 Music Scanner — {ts}</title>
<style>
  :root {{
    --bg: #0f0f0f; --surface: #1e1e1e; --surface2: #2a2a2a;
    --text: #e8e8e8; --muted: #888; --accent: #1db954;
    --red: #f44336; --radius: 12px;
  }}
  * {{ box-sizing: border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; padding:24px; }}
  h1 {{ font-size:2rem; margin-bottom:8px; color:var(--accent); }}
  .subtitle {{ color:var(--muted); margin-bottom:24px; font-size:.95rem; }}
  .stats {{ display:flex; gap:16px; margin-bottom:28px; flex-wrap:wrap; }}
  .stat {{ background:var(--surface); border-radius:var(--radius); padding:12px 20px; }}
  .stat-n {{ font-size:1.8rem; font-weight:700; color:var(--accent); }}
  .stat-l {{ font-size:.8rem; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
  .filters {{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap; }}
  .filter-btn {{ background:var(--surface); border:2px solid transparent; color:var(--text);
                 padding:8px 18px; border-radius:999px; cursor:pointer; font-size:.9rem; transition:.2s; }}
  .filter-btn.active {{ border-color:var(--accent); color:var(--accent); }}
  .search-bar {{ background:var(--surface); border:1px solid #333; color:var(--text);
                 padding:10px 16px; border-radius:999px; width:320px; font-size:.95rem; outline:none; }}
  .search-bar:focus {{ border-color:var(--accent); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; }}
  .card {{ background:var(--surface); border-radius:var(--radius); padding:14px;
           display:flex; gap:12px; align-items:flex-start; transition:.2s; position:relative; }}
  .card:hover {{ background:var(--surface2); transform:translateY(-2px); }}
  .thumb {{ width:72px; height:72px; border-radius:8px; object-fit:cover; flex-shrink:0; }}
  .thumb-placeholder {{ width:72px; height:72px; border-radius:8px; background:#333;
                         display:flex; align-items:center; justify-content:center;
                         font-size:1.8rem; flex-shrink:0; }}
  .info {{ flex:1; min-width:0; }}
  .titulo {{ font-weight:600; font-size:.95rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .artista {{ color:var(--accent); font-size:.85rem; margin:2px 0; }}
  .album {{ color:var(--muted); font-size:.8rem; margin-bottom:6px; }}
  .meta {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:6px; }}
  .badge {{ font-size:.72rem; padding:2px 8px; border-radius:999px; font-weight:600; }}
  .badge-ok {{ background:#1db95420; color:var(--accent); }}
  .badge-fail {{ background:#f4433620; color:var(--red); }}
  .dur, .arquivo {{ font-size:.75rem; color:var(--muted); }}
  .btn {{ background:var(--accent); color:#000; padding:8px 14px; border-radius:999px;
          text-decoration:none; font-weight:700; font-size:.8rem; white-space:nowrap;
          align-self:center; transition:.2s; flex-shrink:0; }}
  .btn:hover {{ background:#17a845; }}
  .section-title {{ font-size:1.1rem; font-weight:700; margin:24px 0 12px;
                    padding-left:12px; border-left:3px solid var(--accent); }}
  .hidden {{ display:none !important; }}
  footer {{ margin-top:40px; color:var(--muted); font-size:.8rem; text-align:center; }}
</style>
</head>
<body>
<h1>🎵 Music Scanner Report</h1>
<p class="subtitle">Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} · {len(validas)+len(sem_link)} músicas escaneadas</p>

<div class="stats">
  <div class="stat"><div class="stat-n">{len(validas)+len(sem_link)}</div><div class="stat-l">Total</div></div>
  <div class="stat"><div class="stat-n" style="color:var(--accent)">{len(validas)}</div><div class="stat-l">Encontradas</div></div>
  <div class="stat"><div class="stat-n" style="color:var(--red)">{len(sem_link)}</div><div class="stat-l">Não encontradas</div></div>
  <div class="stat"><div class="stat-n">{len(validas)/(len(validas)+len(sem_link))*100:.0f}%</div><div class="stat-l">Taxa sucesso</div></div>
</div>

<div class="filters">
  <button class="filter-btn active" onclick="filter('all',this)">Todas</button>
  <button class="filter-btn" onclick="filter('found',this)">✅ Encontradas</button>
  <button class="filter-btn" onclick="filter('missing',this)">❌ Não encontradas</button>
  <input class="search-bar" type="text" placeholder="🔍 Buscar por nome..." oninput="search(this.value)">
</div>

<div class="grid" id="grid">
{cards_found}
{cards_missing}
</div>

<footer>Music Scanner Ultimate 2.0 · {len(validas)} links gerados</footer>

<script>
let currentFilter = 'all';
function filter(status, btn) {{
  currentFilter = status;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyFilters();
}}
function search(val) {{ applyFilters(val); }}
function applyFilters(searchVal) {{
  if (searchVal === undefined) searchVal = document.querySelector('.search-bar').value;
  const q = searchVal.toLowerCase();
  document.querySelectorAll('.card').forEach(c => {{
    const matchFilter = currentFilter === 'all' || c.dataset.status === currentFilter;
    const matchSearch = !q || c.innerText.toLowerCase().includes(q);
    c.classList.toggle('hidden', !(matchFilter && matchSearch));
  }});
}}
</script>
</body>
</html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🎵 Music Scanner Ultimate 2.0 — YT Music API Edition",
        epilog=(
            "Exemplos:\n"
            "  python musicscanner.py ~/Música\n"
            "  python musicscanner.py ~/Música --output ./resultados --workers 5\n"
            "  python musicscanner.py ~/Música --no-resume\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pasta", nargs="?", default=None,
                        help="Pasta com os ficheiros de música")
    parser.add_argument("--output", "-o", default=".",
                        help="Pasta de saída para relatórios (default: .)")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS,
                        help=f"Threads paralelas (default: {MAX_WORKERS}, recomendado ≤5)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Ignorar cache e re-buscar tudo")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Apagar cache antes de iniciar")

    args = parser.parse_args()

    print(f"\n{Fore.MAGENTA + Style.BRIGHT}{'═'*64}")
    print(f"  🎵  MUSIC SCANNER ULTIMATE 2.0")
    print(f"{'═'*64}{Style.RESET_ALL}")

    pasta = args.pasta
    if not pasta:
        pasta = input(f"\n{Fore.YELLOW}📂 Caminho da pasta de músicas: {Style.RESET_ALL}").strip('"').strip("'")

    if args.clear_cache and CACHE_FILE.exists():
        CACHE_FILE.unlink()
        C.info("Cache apagado.")

    app = MusicScannerUltimate(
        pasta_musicas = pasta,
        output_dir    = args.output,
        resume        = not args.no_resume,
    )

    if app.escanear_local():
        app.buscar_online()
        app.salvar()
    else:
        C.err("Nenhuma música para processar.")

    input(f"\n{Fore.DIM}Pressione ENTER para sair...{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
