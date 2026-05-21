#!/usr/bin/env python3
"""
██████╗ ███████╗██████╗ ██╗   ██╗██████╗     ██╗   ██╗██╗  ████████╗██████╗  █████╗
██╔══██╗██╔════╝██╔══██╗██║   ██║██╔══██╗    ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔══██╗
██║  ██║█████╗  ██║  ██║██║   ██║██████╔╝    ██║   ██║██║     ██║   ██████╔╝███████║
██║  ██║██╔══╝  ██║  ██║██║   ██║██╔═══╝     ██║   ██║██║     ██║   ██╔══██╗██╔══██║
██████╔╝███████╗██████╔╝╚██████╔╝██║         ╚██████╔╝███████╗██║   ██║  ██║██║  ██║
╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝          ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
Dedup Ultra 3.0 - Ferramenta Profissional de Deduplicação
"""

import os
import sys
import hashlib
import json
import csv
import shutil
import argparse
import logging
import time
from pathlib import Path
from collections import defaultdict
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────
# Tentativa de importar dependências opcionais
# ─────────────────────────────────────────────
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from colorama import init as colorama_init, Fore, Style, Back
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = Style = Back = _Dummy()

try:
    import send2trash
    HAS_TRASH = True
except ImportError:
    HAS_TRASH = False


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
LOG_FILE = Path("dedup_ultra.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dedup")


# ─────────────────────────────────────────────
# CORES / ESTILOS
# ─────────────────────────────────────────────
class C:
    TITLE   = Fore.MAGENTA + Style.BRIGHT
    INFO    = Fore.CYAN
    OK      = Fore.GREEN
    WARN    = Fore.YELLOW
    ERR     = Fore.RED + Style.BRIGHT
    DIM     = Style.DIM
    BOLD    = Style.BRIGHT
    RESET   = Style.RESET_ALL

    @staticmethod
    def banner(text: str):
        width = 62
        line  = "─" * width
        print(f"\n{C.TITLE}╭{line}╮")
        print(f"│  {text:<{width-2}}│")
        print(f"╰{line}╯{C.RESET}\n")

    @staticmethod
    def ok(msg): print(f"{C.OK}  ✅  {msg}{C.RESET}")

    @staticmethod
    def warn(msg): print(f"{C.WARN}  ⚠️   {msg}{C.RESET}")

    @staticmethod
    def err(msg):
        print(f"{C.ERR}  ❌  {msg}{C.RESET}", file=sys.stderr)
        logger.error(msg)

    @staticmethod
    def info(msg): print(f"{C.INFO}  ℹ️   {msg}{C.RESET}")

    @staticmethod
    def section(msg): print(f"\n{C.BOLD}{'━'*62}\n  {msg}\n{'━'*62}{C.RESET}")


def fmt_size(n: int) -> str:
    """Formata bytes de forma legível."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


def make_progress(iterable, total, desc="", unit="it"):
    """Retorna tqdm ou iterador simples conforme disponibilidade."""
    if HAS_TQDM:
        return tqdm(iterable, total=total, desc=desc, unit=unit, colour="cyan",
                    bar_format="{l_bar}{bar:40}{r_bar}")
    return iterable


# ─────────────────────────────────────────────
# UTILITÁRIOS
# ─────────────────────────────────────────────
class Utils:
    @staticmethod
    def create_backup(filepath: Path) -> Path:
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        bkp = filepath.with_suffix(filepath.suffix + f".bak_{ts}")
        shutil.copy2(filepath, bkp)
        logger.info(f"Backup criado: {bkp}")
        return bkp

    @staticmethod
    def get_file_hash(filepath: Path, first_chunk_only: bool = False,
                      algorithm: str = "sha256") -> str:
        """
        Calcula hash SHA-256 (padrão) ou xxHash se disponível.
        Se first_chunk_only=True, lê apenas os primeiros 4 KB (triagem rápida).
        """
        try:
            # xxHash é 3-5× mais rápido que SHA-256 se disponível
            try:
                import xxhash
                hasher = xxhash.xxh64()
            except ImportError:
                hasher = hashlib.new(algorithm)

            with open(filepath, "rb") as f:
                if first_chunk_only:
                    hasher.update(f.read(4096))
                else:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return ""

    @staticmethod
    def move_to_trash(filepath: Path) -> bool:
        if HAS_TRASH:
            send2trash.send2trash(str(filepath))
            return True
        return False

    @staticmethod
    def safe_delete(filepath: Path, use_trash: bool = False) -> bool:
        """Remove ficheiro, opcionalmente para a reciclagem."""
        try:
            if use_trash and Utils.move_to_trash(filepath):
                logger.info(f"Para reciclagem: {filepath}")
                return True
            os.remove(filepath)
            logger.info(f"Deletado: {filepath}")
            return True
        except OSError as e:
            C.err(f"Não foi possível eliminar {filepath}: {e}")
            return False

    @staticmethod
    def match_patterns(path: Path, patterns: List[str]) -> bool:
        """Verifica se o caminho corresponde a algum glob pattern."""
        from fnmatch import fnmatch
        name = path.name
        return any(fnmatch(name, p) for p in patterns)


# ─────────────────────────────────────────────
# DEDUPLICADOR PRINCIPAL
# ─────────────────────────────────────────────
class Deduplicator:
    def __init__(self,
                 verbose:    bool = False,
                 backup:     bool = True,
                 use_trash:  bool = False,
                 dry_run:    bool = False,
                 workers:    int  = 4,
                 algorithm:  str  = "sha256",
                 exclude:    Optional[List[str]] = None,
                 min_size:   int  = 1,
                 max_size:   Optional[int] = None):

        self.verbose    = verbose
        self.backup     = backup
        self.use_trash  = use_trash
        self.dry_run    = dry_run
        self.workers    = workers
        self.algorithm  = algorithm
        self.exclude    = exclude or []
        self.min_size   = min_size
        self.max_size   = max_size
        self.stats: Dict = {
            "removed": 0, "space_saved": 0,
            "scanned": 0, "errors": 0,
            "elapsed": 0.0
        }

    # ── Modo ARQUIVOS ──────────────────────────────────────────────────────────
    def process_files(self, directory: Path, delete: bool = False,
                      move_to: Optional[Path] = None):
        C.banner(f"🔍 Analisando Diretório: {directory}")
        t0 = time.perf_counter()

        # 1. Coleta todos os arquivos
        all_files: List[Path] = []
        for p in directory.rglob("*"):
            if not p.is_file():
                continue
            if self.exclude and Utils.match_patterns(p, self.exclude):
                continue
            try:
                size = p.stat().st_size
                if size < self.min_size:
                    continue
                if self.max_size is not None and size > self.max_size:
                    continue
                all_files.append(p)
            except OSError:
                self.stats["errors"] += 1

        self.stats["scanned"] = len(all_files)
        C.info(f"Arquivos encontrados: {len(all_files)}")

        # 2. Agrupar por tamanho (O(n))
        size_groups: Dict[int, List[Path]] = defaultdict(list)
        for p in all_files:
            size_groups[p.stat().st_size].append(p)

        candidates = {s: fs for s, fs in size_groups.items() if len(fs) > 1}
        C.info(f"Grupos com mesmo tamanho: {len(candidates)}")

        # 3. Hash parcial (4 KB) com ThreadPoolExecutor
        def partial_hash(p: Path) -> Tuple[Path, str]:
            return p, Utils.get_file_hash(p, first_chunk_only=True,
                                          algorithm=self.algorithm)

        duplicates_found: List[List[Path]] = []

        flat_candidates = [f for fs in candidates.values() for f in fs]
        partial_map: Dict[Path, str] = {}

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(partial_hash, p): p for p in flat_candidates}
            for fut in make_progress(as_completed(futures),
                                     total=len(flat_candidates),
                                     desc="Hash parcial", unit="arq"):
                p, h = fut.result()
                if h:
                    partial_map[p] = h

        # 4. Hash total apenas para colisões de hash parcial
        partial_groups: Dict[str, List[Path]] = defaultdict(list)
        for p, h in partial_map.items():
            key = f"{p.stat().st_size}_{h}"
            partial_groups[key].append(p)

        def full_hash(p: Path) -> Tuple[Path, str]:
            return p, Utils.get_file_hash(p, first_chunk_only=False,
                                          algorithm=self.algorithm)

        need_full = [f for fs in partial_groups.values()
                     if len(fs) > 1 for f in fs]
        full_map: Dict[Path, str] = {}

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(full_hash, p): p for p in need_full}
            for fut in make_progress(as_completed(futures),
                                     total=len(need_full),
                                     desc="Hash completo", unit="arq"):
                p, h = fut.result()
                if h:
                    full_map[p] = h

        full_groups: Dict[str, List[Path]] = defaultdict(list)
        for p, h in full_map.items():
            full_groups[h].append(p)

        for group in full_groups.values():
            if len(group) > 1:
                # Mantém o arquivo mais antigo como original
                group.sort(key=lambda x: x.stat().st_mtime)
                duplicates_found.append(group)

        # 5. Relatório
        self.stats["elapsed"] = time.perf_counter() - t0
        total_wasted = sum(
            p.stat().st_size for g in duplicates_found for p in g[1:]
        )

        C.section(f"📊 RELATÓRIO: {len(duplicates_found)} grupos duplicados")
        print(f"  {'Espaço desperdiçado':<30} {fmt_size(total_wasted)}")
        print(f"  {'Grupos de duplicatas':<30} {len(duplicates_found)}")
        print(f"  {'Tempo de análise':<30} {self.stats['elapsed']:.2f}s\n")

        if not duplicates_found:
            C.ok("Nenhuma duplicata encontrada! ✨")
            return

        # Exportar relatório JSON
        report_path = Path(f"dedup_report_{datetime.now():%Y%m%d_%H%M%S}.json")
        report_data = []
        for group in duplicates_found:
            report_data.append({
                "original":   str(group[0]),
                "duplicates": [str(p) for p in group[1:]],
                "size_bytes": group[0].stat().st_size,
                "size_human": fmt_size(group[0].stat().st_size),
            })
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        C.info(f"Relatório JSON: {report_path}")

        # 6. Ação: deletar / mover / apenas mostrar
        for group in duplicates_found:
            original = group[0]
            dupes    = group[1:]
            sz = fmt_size(original.stat().st_size)

            print(f"\n  {C.INFO}📄 Original  [{sz}]{C.RESET}: "
                  f"{C.BOLD}{original}{C.RESET}")

            for d in dupes:
                rel = d.relative_to(directory) if d.is_relative_to(directory) else d
                print(f"     {C.WARN}↳ Duplicata{C.RESET}: {rel}")

                if self.dry_run:
                    print(f"        {C.DIM}(dry-run: nenhuma ação){C.RESET}")
                    continue

                if delete or move_to:
                    size = d.stat().st_size
                    if move_to:
                        dest = move_to / d.name
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(d), str(dest))
                        C.info(f"Movido para: {dest}")
                    else:
                        if Utils.safe_delete(d, use_trash=self.use_trash):
                            self.stats["removed"] += 1
                            self.stats["space_saved"] += size
                            action = "🗑️  Deletado" if not self.use_trash else "♻️  Reciclagem"
                            print(f"        {C.ERR}{action}: {d.name}{C.RESET}")

        self._print_summary()

    # ── Modo LINHAS ────────────────────────────────────────────────────────────
    def process_lines(self, input_file: Path, output_file: Path,
                      ignore_case: bool = False,
                      strip_whitespace: bool = True):
        C.banner(f"📝 Deduplicando linhas: {input_file.name}")

        if self.backup:
            Utils.create_backup(input_file)

        seen:  Set[bytes] = set()
        orig  = 0
        uniq  = 0

        try:
            with open(input_file, "r", encoding="utf-8", errors="replace") as fin, \
                 open(output_file, "w", encoding="utf-8") as fout:

                lines = fin.readlines()
                orig  = len(lines)

                for line in make_progress(lines, total=orig,
                                          desc="Processando", unit="linha"):
                    key = line
                    if strip_whitespace:
                        key = key.strip()
                    if ignore_case:
                        key = key.lower()
                    key_hash = hashlib.md5(key.encode("utf-8")).digest()
                    if key_hash not in seen:
                        seen.add(key_hash)
                        fout.write(line)
                        uniq += 1

            self.stats["removed"] = orig - uniq
            C.ok(f"Linhas originais : {orig}")
            C.ok(f"Linhas únicas    : {uniq}")
            C.ok(f"Duplicatas removidas: {orig - uniq}")
            C.info(f"Salvo em: {output_file}")

        except Exception as e:
            C.err(f"Erro ao processar linhas: {e}")

    # ── Modo CSV ───────────────────────────────────────────────────────────────
    def process_csv(self, input_file: Path, output_file: Path,
                    columns: Optional[List[str]],
                    keep: str = "first"):
        C.banner(f"📊 Deduplicando CSV: {input_file.name}")

        if self.backup:
            Utils.create_backup(input_file)

        try:
            with open(input_file, "r", encoding="utf-8", newline="") as fin:
                sniffer = csv.Sniffer()
                sample  = fin.read(4096)
                try:
                    dialect = sniffer.sniff(sample)
                except csv.Error:
                    dialect = "excel"
                fin.seek(0)

                reader     = csv.DictReader(fin, dialect=dialect)
                fieldnames = reader.fieldnames or []

                if not fieldnames:
                    C.err("CSV vazio ou sem cabeçalho.")
                    return

                target_cols = columns or fieldnames
                missing = [c for c in target_cols if c not in fieldnames]
                if missing:
                    C.err(f"Colunas não encontradas: {missing}")
                    return

                all_rows = list(reader)

            # Deduplica mantendo primeira ou última ocorrência
            seen_keys: Set[tuple] = set()
            unique_rows = []

            iter_rows = all_rows if keep == "first" else reversed(all_rows)
            for row in iter_rows:
                key = tuple(str(row.get(c, "")).strip() for c in target_cols)
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_rows.append(row)

            if keep == "last":
                unique_rows.reverse()

            removed = len(all_rows) - len(unique_rows)
            self.stats["removed"] = removed

            with open(output_file, "w", encoding="utf-8", newline="") as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames, dialect=dialect)
                writer.writeheader()
                writer.writerows(unique_rows)

            C.ok(f"Registros originais  : {len(all_rows)}")
            C.ok(f"Registros únicos     : {len(unique_rows)}")
            C.warn(f"Duplicatas removidas : {removed}")
            C.info(f"Salvo em: {output_file}")

        except Exception as e:
            C.err(f"Erro no CSV: {e}")
            logger.exception(e)

    # ── Modo JSON ──────────────────────────────────────────────────────────────
    def process_json(self, input_file: Path, output_file: Path,
                     key: Optional[str] = None,
                     keep: str = "first"):
        C.banner(f"🔧 Deduplicando JSON: {input_file.name}")

        if self.backup:
            Utils.create_backup(input_file)

        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                C.err("O JSON raiz deve ser uma lista (Array).")
                return

            orig_len = len(data)
            unique_data = []
            seen: Set = set()

            items = data if keep == "first" else reversed(data)
            for item in items:
                if key:
                    val = str(item.get(key, "")) if isinstance(item, dict) else str(item)
                    if val not in seen:
                        seen.add(val)
                        unique_data.append(item)
                else:
                    item_hash = hashlib.sha256(
                        json.dumps(item, sort_keys=True, ensure_ascii=False).encode()
                    ).digest()
                    if item_hash not in seen:
                        seen.add(item_hash)
                        unique_data.append(item)

            if keep == "last":
                unique_data.reverse()

            self.stats["removed"] = orig_len - len(unique_data)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)

            C.ok(f"Itens originais  : {orig_len}")
            C.ok(f"Itens únicos     : {len(unique_data)}")
            C.warn(f"Duplicatas removidas: {self.stats['removed']}")
            C.info(f"Salvo em: {output_file}")

        except json.JSONDecodeError:
            C.err("Arquivo JSON inválido ou corrompido.")
        except Exception as e:
            C.err(f"Erro JSON: {e}")
            logger.exception(e)

    # ── RESUMO FINAL ───────────────────────────────────────────────────────────
    def _print_summary(self):
        C.section("🏁 RESUMO FINAL")
        print(f"  {'Arquivos escaneados':<30} {self.stats['scanned']}")
        print(f"  {'Duplicatas removidas':<30} {self.stats['removed']}")
        print(f"  {'Espaço recuperado':<30} {fmt_size(self.stats['space_saved'])}")
        print(f"  {'Tempo total':<30} {self.stats['elapsed']:.2f}s")
        print(f"  {'Erros':<30} {self.stats['errors']}")
        print(f"  {C.DIM}Log completo: {LOG_FILE}{C.RESET}\n")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dedup",
        description="🚀 Dedup Ultra 3.0 — Removedor Profissional de Duplicatas",
        epilog=(
            "Exemplos:\n"
            "  python dedup.py files ./fotos --delete --trash --workers 8\n"
            "  python dedup.py files ./fotos --move-to ./duplicatas --exclude '*.tmp' '*.log'\n"
            "  python dedup.py lines lista.txt -o lista_clean.txt --ignore-case\n"
            "  python dedup.py csv dados.csv --cols email,nome --keep last\n"
            "  python dedup.py json users.json --key id\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Globais
    p.add_argument("-v", "--verbose",  action="store_true", help="Detalhes extras")
    p.add_argument("--no-backup",      action="store_true", help="Não criar .bak")
    p.add_argument("--dry-run",        action="store_true", help="Simular sem alterar")
    p.add_argument("--workers",        type=int, default=4,  help="Threads paralelas (default: 4)")
    p.add_argument("--algorithm",      default="sha256",
                   choices=["sha256","sha1","md5"],
                   help="Algoritmo de hash (default: sha256)")

    sub = p.add_subparsers(dest="mode", required=True)

    # ── files ──
    pf = sub.add_parser("files", help="Arquivos duplicados")
    pf.add_argument("path", type=Path)
    pf.add_argument("--delete",   action="store_true", help="Deletar duplicatas")
    pf.add_argument("--trash",    action="store_true", help="Mover para reciclagem (requer send2trash)")
    pf.add_argument("--move-to",  type=Path, metavar="DIR", help="Mover duplicatas para pasta")
    pf.add_argument("--exclude",  nargs="+", metavar="PATTERN", help="Padrões glob a excluir")
    pf.add_argument("--min-size", type=int, default=1, metavar="BYTES",
                    help="Tamanho mínimo em bytes (default: 1)")
    pf.add_argument("--max-size", type=int, default=None, metavar="BYTES",
                    help="Tamanho máximo em bytes")

    # ── lines ──
    pl = sub.add_parser("lines", help="Linhas duplicadas em texto")
    pl.add_argument("file",   type=Path)
    pl.add_argument("-o", "--output", type=Path)
    pl.add_argument("--ignore-case",      action="store_true")
    pl.add_argument("--no-strip",         action="store_true",
                    help="Não remover espaços antes de comparar")

    # ── csv ──
    pc = sub.add_parser("csv", help="Linhas duplicadas em CSV")
    pc.add_argument("file",   type=Path)
    pc.add_argument("-o", "--output", type=Path)
    pc.add_argument("--cols", help="Colunas a verificar (vírgula separada)")
    pc.add_argument("--keep", choices=["first","last"], default="first")

    # ── json ──
    pj = sub.add_parser("json", help="Itens duplicados em JSON")
    pj.add_argument("file",   type=Path)
    pj.add_argument("-o", "--output", type=Path)
    pj.add_argument("--key",  help="Campo chave (ex: id)")
    pj.add_argument("--keep", choices=["first","last"], default="first")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    # Cabeçalho
    print(f"\n{C.TITLE}{'═'*64}")
    print(f"  🔧  DEDUP ULTRA 3.0  |  {datetime.now():%d/%m/%Y %H:%M:%S}")
    print(f"{'═'*64}{C.RESET}")

    if args.dry_run:
        C.warn("MODO DRY-RUN: nenhuma alteração será feita.")

    dedup = Deduplicator(
        verbose   = args.verbose,
        backup    = not args.no_backup,
        use_trash = getattr(args, "trash", False),
        dry_run   = args.dry_run,
        workers   = args.workers,
        algorithm = args.algorithm,
        exclude   = getattr(args, "exclude", None),
        min_size  = getattr(args, "min_size", 1),
        max_size  = getattr(args, "max_size", None),
    )

    if args.mode == "files":
        if not args.path.is_dir():
            C.err("O caminho deve ser um diretório válido.")
            sys.exit(1)
        dedup.process_files(
            args.path,
            delete  = args.delete,
            move_to = args.move_to,
        )

    elif args.mode == "lines":
        out = args.output or args.file
        dedup.process_lines(
            args.file, out,
            ignore_case      = args.ignore_case,
            strip_whitespace = not args.no_strip,
        )

    elif args.mode == "csv":
        out  = args.output or args.file
        cols = [c.strip() for c in args.cols.split(",")] if args.cols else None
        dedup.process_csv(args.file, out, cols, keep=args.keep)

    elif args.mode == "json":
        out = args.output or args.file
        dedup.process_json(args.file, out, key=args.key, keep=args.keep)

    print(f"\n{C.DIM}Log salvo em: {LOG_FILE}{C.RESET}\n")


if __name__ == "__main__":
    main()
