# 🗂️ Importantes

**Importantes** é uma coleção de utilitários Python para resolver tarefas práticas de organização local: encontrar e tratar duplicatas, limpar dados repetidos e relacionar arquivos de música com resultados do YouTube Music. O repositório também inclui um guia de comandos para `yt-dlp`.

## Ferramentas

### `dedup.py` — Dedup Ultra

Deduplicador com quatro modos:

- `files`: localiza arquivos iguais usando tamanho, hash parcial de 4 KB e hash completo. Em cada grupo, o arquivo mais antigo (pela data de modificação) é tratado como original. Por padrão só analisa e gera relatório; apaga, move ou envia para a lixeira apenas com as opções correspondentes.
- `lines`: remove linhas repetidas de arquivos de texto. Espaços nas pontas são ignorados na comparação (use `--no-strip` para considerá-los) e `--ignore-case` ignora maiúsculas e minúsculas.
- `csv`: deduplica registros por todas as colunas ou por colunas escolhidas, mantendo a primeira ou a última ocorrência.
- `json`: remove itens repetidos de uma lista JSON, por conteúdo ou por uma chave como `id`.

O modo `files` usa `ThreadPoolExecutor`, filtros de tamanho (`--min-size`, `--max-size`) e padrões `--exclude`. O algoritmo de hash é `sha256` por padrão (`sha1` e `md5` via `--algorithm`); se o `xxhash` estiver instalado, ele é usado no lugar. Todos os modos escrevem em `dedup_ultra.log`. `send2trash`, `tqdm`, `colorama` e `xxhash` são opcionais.

### `musicscanner.py` — Music Scanner

Varre uma pasta em busca de áudio (`mp3`, `wav`, `flac`, `m4a`, `aac`, `ogg`, `wma`, `opus`, `ape`, `alac`, `aiff`, `mp4` e `webm`), lê metadados com TinyTag e procura cada faixa na API não autenticada do YouTube Music via `ytmusicapi`. O termo de busca é `artista - título`; sem tags, usa o nome do arquivo limpo. A busca tenta primeiro `songs` e depois `videos`, usa o primeiro resultado, tem cache persistente, três tentativas com backoff e três buscas paralelas.

Ao final, gera links TXT, playlist M3U8 (faixas não encontradas entram com o caminho local), JSON completo, relatório HTML com miniaturas e uma lista das faixas não encontradas. `ytmusicapi`, `tinytag`, `tqdm` e `colorama` são obrigatórios para este script.

### `comandos.txt`

Guia de referência com exemplos de `yt-dlp`, playlists, templates de nomes, histórico, aria2c, SponsorBlock, legendas e configurações úteis.

## Instalação

Recomendado: Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
pip install ytmusicapi tinytag tqdm colorama send2trash
```

Para hashing opcional mais rápido:

```bash
pip install xxhash
```

## Exemplos de uso

### Arquivos duplicados

As opções globais (`-v`, `--dry-run`, `--workers`, `--no-backup`, `--algorithm`) vêm **antes** do modo. Colocá-las depois dele gera erro de argumento.

```bash
# Apenas analisar
python dedup.py files ./pasta

# Simular exclusão sem alterar nada
python dedup.py --dry-run files ./pasta --delete

# Enviar duplicatas para a lixeira
python dedup.py files ./pasta --delete --trash

# Mover para outra pasta
python dedup.py files ./pasta --move-to ./duplicatas

# Ignorar arquivos temporários e usar mais workers
python dedup.py --workers 8 files ./pasta --exclude "*.tmp" "*.log"
```

### Texto, CSV e JSON

Sem `-o`, o resultado sobrescreve o arquivo de entrada. Antes disso, é criada uma cópia `.bak_AAAAMMDD_HHMMSS` ao lado do original; `--no-backup` desativa a cópia.

```bash
python dedup.py lines lista.txt -o lista_limpa.txt --ignore-case
python dedup.py csv dados.csv --cols email,nome --keep last
python dedup.py json users.json --key id
```

### Biblioteca de música

```bash
python musicscanner.py ~/Música
python musicscanner.py ~/Música --output ./resultados
python musicscanner.py ~/Música --clear-cache
```

Sem a pasta como argumento, o script pergunta o caminho. No fim, espera um ENTER para encerrar.

## Arquivos gerados

- `dedup_ultra.log` e relatórios `dedup_report_*.json` (o relatório é gravado sempre que há duplicatas, inclusive com `--dry-run`).
- `.musicscanner_cache.json` e `musicscanner.log`, criados na pasta em que o comando é executado.
- `playlist_links_*.txt`, `playlist_*.m3u8`, `musicscanner_*.json` e `relatorio_*.html`, na pasta definida em `--output`.
- `nao_encontradas_*.txt` quando há faixas sem correspondência.

## Comportamentos a conhecer

- `--trash` só envia à lixeira se o `send2trash` estiver instalado. Sem ele, o arquivo é apagado definitivamente. Use `--dry-run` antes.
- `--trash` só tem efeito junto com `--delete`.
- Com `--move-to`, duplicatas com o mesmo nome de arquivo caem no mesmo destino e podem se sobrescrever.
- No `musicscanner.py`, `--workers` é aceito mas não altera nada: o limite fixo é 3 buscas paralelas.
- `--no-resume` não ignora o cache de buscas. Para refazer tudo, use `--clear-cache`.

## Cuidados

Faça backup antes de operações destrutivas. As buscas no YouTube Music dependem da disponibilidade do serviço, e os arquivos gerados podem conter caminhos locais.

Consulte `license` para a licença do projeto.
