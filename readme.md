# 🗂️ Importantes — Edição Máxima

Coleção de scripts utilitários Python para gestão avançada de ficheiros locais e bibliotecas de música.

---

## 📦 Ficheiros do Projeto

| Ficheiro | Descrição |
|---|---|
| `dedup.py` | Deduplicação profissional de arquivos, linhas, CSV e JSON |
| `musicscanner.py` | Scanner de música com busca automática no YouTube Music |
| `comandos.txt` | Guia completo de comandos yt-dlp |

---

## ✨ Novidades desta Edição Máxima

### `dedup.py` — Dedup Ultra 3.0
- ⚡ **Hashing paralelo** com `ThreadPoolExecutor` (4 threads por padrão)
- 🔍 **Algoritmo 3 etapas**: tamanho → hash parcial (4 KB) → hash total (só quando necessário)
- 🗑️ **Modo reciclagem** (`--trash`) via `send2trash`
- 📦 **Mover duplicatas** para pasta (`--move-to DIR`) em vez de deletar
- 🧪 **Dry-run** (`--dry-run`) para simular sem alterar nada
- 🚫 **Exclusão por padrão** (`--exclude *.tmp *.log`)
- 📏 **Filtro por tamanho** (`--min-size` / `--max-size`)
- 📊 **Relatório JSON** automático com todos os grupos duplicados
- 📝 **Log completo** em `dedup_ultra.log`
- 🎨 Banner e interface colorida com `colorama`
- 🔄 Suporte a `xxhash` para performance extra (opcional)

### `musicscanner.py` — Music Scanner Ultimate 2.0
- 💾 **Cache persistente** em `.musicscanner_cache.json` — evita re-buscar
- 🔄 **Resume automático** — continua de onde parou
- 🔁 **Retry com backoff exponencial** (3 tentativas por música)
- 🧵 **Busca paralela** com controlo de rate-limit
- 📋 **Exportação M3U8** — compatível com VLC, Winamp, qualquer player
- 📊 **Relatório HTML** dark mode com thumbnails, filtros e busca
- 🎵 Extração avançada de metadados (artista, álbum, ano, género, duração)
- 🧹 Limpeza inteligente de nomes de ficheiro
- 📁 Pasta de saída configurável (`--output`)
- 📝 Log completo em `musicscanner.log`

### `comandos.txt` — Guia Profissional yt-dlp v3.0
- 🚀 Integração com **aria2c** (downloads até 16× mais rápidos)
- 🧼 **SponsorBlock** (`--sponsorblock-remove all`)
- 📋 **Playlists** com índice e intervalo
- 📁 **Templates avançados** de nome de arquivo
- 🔖 **Arquivo de histórico** para retomar sem re-baixar
- ⚙️ Exemplo de **config global** yt-dlp
- 📖 Guia completo de **legendas e acessibilidade**

---

## 🔧 Instalação

```bash
pip install ytmusicapi tinytag tqdm colorama send2trash
# Opcional para hashing mais rápido:
pip install xxhash
```

---

## 🚀 Como usar

### Dedup Ultra 3.0

```bash
# Encontrar duplicatas (apenas relatório)
python dedup.py files ./pasta

# Deletar duplicatas (move para reciclagem)
python dedup.py files ./pasta --delete --trash

# Mover duplicatas para pasta separada
python dedup.py files ./pasta --move-to ./duplicatas

# Simular sem alterar nada
python dedup.py files ./pasta --delete --dry-run

# Mais rápido com 8 threads, excluindo tmp
python dedup.py files ./pasta --delete --workers 8 --exclude "*.tmp" "*.log"

# Remover linhas duplicadas de um ficheiro texto
python dedup.py lines lista.txt -o lista_limpa.txt --ignore-case

# Deduplicar CSV pelas colunas email e nome
python dedup.py csv dados.csv --cols email,nome --keep last

# Deduplicar JSON pelo campo id
python dedup.py json users.json --key id
```

### Music Scanner Ultimate 2.0

```bash
# Uso básico
python musicscanner.py ~/Música

# Com pasta de saída customizada
python musicscanner.py ~/Música --output ./resultados

# Forçar re-busca (ignorar cache)
python musicscanner.py ~/Música --no-resume

# Limpar cache e começar do zero
python musicscanner.py ~/Música --clear-cache
```

**Saídas geradas:**
- `playlist_links_TIMESTAMP.txt` — links compatíveis com `yt-dlp -a`
- `playlist_TIMESTAMP.m3u8` — playlist para VLC e outros players
- `musicscanner_TIMESTAMP.json` — dados completos em JSON
- `relatorio_TIMESTAMP.html` — relatório visual com thumbnails
- `nao_encontradas_TIMESTAMP.txt` — músicas sem resultado

---

## 📋 Pré-requisitos

- Python 3.10+
- `pip install ytmusicapi tinytag tqdm colorama send2trash`
- *(Opcional)* `pip install xxhash` para hashing mais rápido

---

## 📄 Licença

Ver ficheiro `license`.
