# 🗂️ Importantes

**Importantes** é uma coleção de utilitários Python para resolver tarefas práticas de organização local: encontrar e tratar duplicatas, limpar dados repetidos e relacionar arquivos de música com resultados do YouTube Music. O repositório também inclui um guia de comandos para `yt-dlp`.

## Ferramentas

### `dedup.py` — Dedup Ultra

Deduplicador com quatro modos:

- `files`: localiza arquivos iguais usando tamanho, hash parcial de 4 KB e hash completo; pode gerar relatório, apagar, mover ou enviar duplicatas para a lixeira.
- `lines`: remove linhas repetidas de arquivos de texto, com opção de ignorar maiúsculas/minúsculas.
- `csv`: deduplica registros por todas as colunas ou por colunas escolhidas, mantendo a primeira ou a última ocorrência.
- `json`: remove itens repetidos por conteúdo ou por uma chave como `id`.

O processamento de arquivos usa `ThreadPoolExecutor`, suporta `--dry-run`, filtros de tamanho, padrões `--exclude`, logs e relatórios JSON. `send2trash`, `tqdm`, `colorama` e `xxhash` são opcionais conforme o recurso desejado.

### `musicscanner.py` — Music Scanner

Varre uma pasta em busca de formatos de áudio, lê metadados com TinyTag e procura cada faixa na API não autenticada do YouTube Music via `ytmusicapi`. Há cache persistente, retomada, tentativas com backoff e busca paralela controlada.

Ao final, gera links TXT, playlist M3U8, JSON completo, relatório HTML com miniaturas e uma lista das faixas não encontradas.

### `comandos.txt`

Guia de referência com exemplos de `yt-dlp`, playlists, templates de nomes, histórico, aria2c, SponsorBlock, legendas e configurações úteis.

## Instalação

Recomendado: Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\\Scripts\\activate        # Windows
pip install ytmusicapi tinytag tqdm colorama send2trash
```

Para hashing opcional mais rápido:

```bash
pip install xxhash
```

## Exemplos de uso

### Arquivos duplicados

```bash
# Apenas analisar
python dedup.py files ./pasta

# Simular exclusão sem alterar nada
python dedup.py files ./pasta --delete --dry-run

# Enviar duplicatas para a lixeira
python dedup.py files ./pasta --delete --trash

# Mover para outra pasta
python dedup.py files ./pasta --move-to ./duplicatas

# Ignorar arquivos temporários e usar mais workers
python dedup.py files ./pasta --workers 8 --exclude "*.tmp" "*.log"
```

### Texto, CSV e JSON

```bash
python dedup.py lines lista.txt -o lista_limpa.txt --ignore-case
python dedup.py csv dados.csv --cols email,nome --keep last
python dedup.py json users.json --key id
```

### Biblioteca de música

```bash
python musicscanner.py ~/Música
python musicscanner.py ~/Música --output ./resultados
python musicscanner.py ~/Música --no-resume
python musicscanner.py ~/Música --clear-cache
```

## Arquivos gerados

- `dedup_ultra.log` e relatórios `dedup_report_*.json`.
- `.musicscanner_cache.json` e `musicscanner.log`.
- `playlist_links_*.txt`, `playlist_*.m3u8`, `musicscanner_*.json` e `relatorio_*.html`.
- `nao_encontradas_*.txt` quando há faixas sem correspondência.

## Cuidados

Faça backup antes de operações destrutivas. Prefira `--dry-run` e `--trash` antes de apagar definitivamente. As buscas no YouTube Music dependem da disponibilidade do serviço e os arquivos gerados podem conter caminhos locais.

Consulte `license` para a licença do projeto.
