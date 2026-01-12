#!/usr/bin/env python3
"""
Dedup Ultra - Ferramenta Profissional de Deduplicação
Melhorias: Baixo uso de RAM, Algoritmo de Hashing Rápido, Suporte Real a CSV, Backups.
"""

import os
import sys
import hashlib
import json
import csv
import shutil
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Optional, Generator, Dict, Set, Any

# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class Utils:
    @staticmethod
    def create_backup(filepath: Path) -> Path:
        """Cria um backup do arquivo antes de modificar (ex: arquivo.json.bak)"""
        backup_path = filepath.with_suffix(filepath.suffix + '.bak')
        shutil.copy2(filepath, backup_path)
        return backup_path

    @staticmethod
    def get_file_hash(filepath: Path, first_chunk_only: bool = False) -> str:
        """
        Calcula hash SHA-256.
        Se first_chunk_only=True, calcula apenas dos primeiros 4KB (rápido para descarte inicial).
        """
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                if first_chunk_only:
                    chunk = f.read(4096)
                    hasher.update(chunk)
                else:
                    while chunk := f.read(65536): # Lê em blocos de 64KB
                        hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return ""

class Deduplicator:
    def __init__(self, verbose: bool = False, backup: bool = True):
        self.verbose = verbose
        self.backup = backup
        self.stats = {'removed': 0, 'space_saved': 0}

    def log(self, msg: str, color: str = Colors.OKBLUE):
        if self.verbose:
            print(f"{color}{msg}{Colors.ENDC}")

    def error(self, msg: str):
        print(f"{Colors.FAIL}[ERRO] {msg}{Colors.ENDC}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # MODO ARQUIVOS (Algoritmo Otimizado: Tamanho -> Hash Parcial -> Hash Total)
    # -------------------------------------------------------------------------
    def process_files(self, directory: Path, delete: bool = False):
        print(f"\n{Colors.HEADER}🔍 Analisando diretório: {directory}{Colors.ENDC}")
        
        # 1. Agrupar por tamanho (Muito rápido)
        size_groups = defaultdict(list)
        for p in directory.rglob('*'):
            if p.is_file():
                try:
                    size_groups[p.stat().st_size].append(p)
                except OSError:
                    continue

        # Filtrar apenas tamanhos que tenham mais de 1 arquivo
        potential_dupes = {s: files for s, files in size_groups.items() if len(files) > 1}
        
        duplicates_found = []
        
        # 2. Comparar Hash Parcial e depois Hash Total
        total_groups = len(potential_dupes)
        curr = 0
        
        for size, files in potential_dupes.items():
            curr += 1
            if self.verbose:
                print(f"Processando grupo {curr}/{total_groups} (Tamanho: {size} bytes)...", end='\r')
            
            # Agrupa por hash parcial (4KB iniciais)
            partial_hashes = defaultdict(list)
            for f in files:
                h = Utils.get_file_hash(f, first_chunk_only=True)
                partial_hashes[h].append(f)
            
            # Para colisões de hash parcial, calcula hash total
            for p_files in partial_hashes.values():
                if len(p_files) < 2: continue
                
                full_hashes = defaultdict(list)
                for f in p_files:
                    h = Utils.get_file_hash(f, first_chunk_only=False)
                    full_hashes[h].append(f)
                
                # Adiciona confirmados à lista final
                for f_files in full_hashes.values():
                    if len(f_files) > 1:
                        duplicates_found.append(f_files)

        print(f"\n✅ Análise concluída. Grupos de duplicatas: {len(duplicates_found)}")

        if not duplicates_found:
            return

        # Relatório e Remoção
        for group in duplicates_found:
            original = group[0]
            dupes = group[1:]
            
            print(f"\n{Colors.OKCYAN}📂 Grupo Duplicado ({original.stat().st_size} bytes):{Colors.ENDC}")
            print(f"   Original: {original.name}")
            for d in dupes:
                print(f"   Duplicata: {d.relative_to(directory)}")
            
            if delete:
                for d in dupes:
                    try:
                        size = d.stat().st_size
                        os.remove(d)
                        self.stats['removed'] += 1
                        self.stats['space_saved'] += size
                        print(f"   {Colors.FAIL}🗑️  Deletado: {d.name}{Colors.ENDC}")
                    except OSError as e:
                        self.error(f"Não foi possível deletar {d}: {e}")

    # -------------------------------------------------------------------------
    # MODO LINHAS (Streaming para baixo uso de memória)
    # -------------------------------------------------------------------------
    def process_lines(self, input_file: Path, output_file: Path):
        print(f"\n{Colors.HEADER}🔍 Deduplicando linhas de: {input_file}{Colors.ENDC}")
        
        if self.backup:
            bkp = Utils.create_backup(input_file)
            self.log(f"Backup criado: {bkp}")

        seen_hashes = set()
        original_count = 0
        unique_count = 0
        
        try:
            with open(input_file, 'r', encoding='utf-8', errors='replace') as fin, \
                 open(output_file, 'w', encoding='utf-8') as fout:
                
                for line in fin:
                    original_count += 1
                    # Hash da linha economiza RAM comparado a guardar a string inteira
                    line_hash = hashlib.md5(line.encode('utf-8')).digest()
                    
                    if line_hash not in seen_hashes:
                        seen_hashes.add(line_hash)
                        fout.write(line)
                        unique_count += 1
            
            self.stats['removed'] = original_count - unique_count
            print(f"✅ Linhas Originais: {original_count} | Únicas: {unique_count}")
            print(f"💾 Salvo em: {output_file}")
            
        except Exception as e:
            self.error(f"Erro ao processar linhas: {e}")

    # -------------------------------------------------------------------------
    # MODO CSV (Robusto com biblioteca padrão)
    # -------------------------------------------------------------------------
    def process_csv(self, input_file: Path, output_file: Path, columns: Optional[List[str]]):
        print(f"\n{Colors.HEADER}🔍 Deduplicando CSV: {input_file}{Colors.ENDC}")
        
        if self.backup:
            Utils.create_backup(input_file)

        try:
            with open(input_file, 'r', encoding='utf-8', newline='') as fin:
                # Detecta delimitador automaticamente (ex: ; ou ,)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(fin.read(2048))
                except csv.Error:
                    dialect = 'excel' # fallback
                fin.seek(0)
                
                reader = csv.DictReader(fin, dialect=dialect)
                fieldnames = reader.fieldnames
                
                if not fieldnames:
                    self.error("Arquivo CSV vazio ou sem cabeçalho.")
                    return

                # Verifica colunas solicitadas
                target_cols = columns if columns else fieldnames
                for col in target_cols:
                    if col not in fieldnames:
                        self.error(f"Coluna '{col}' não existe no CSV.")
                        return

                seen_keys = set()
                unique_rows = []
                
                for row in reader:
                    # Cria uma tupla com os valores das colunas alvo para usar como chave única
                    key = tuple(row[c] for c in target_cols)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        unique_rows.append(row)
                    else:
                        self.stats['removed'] += 1

            # Escrevendo saída
            with open(output_file, 'w', encoding='utf-8', newline='') as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames, dialect=dialect)
                writer.writeheader()
                writer.writerows(unique_rows)

            print(f"✅ Registros únicos mantidos: {len(unique_rows)}")
            print(f"🗑️  Duplicatas removidas: {self.stats['removed']}")

        except Exception as e:
            self.error(f"Erro no CSV: {e}")

    # -------------------------------------------------------------------------
    # MODO JSON
    # -------------------------------------------------------------------------
    def process_json(self, input_file: Path, output_file: Path, key: Optional[str]):
        print(f"\n{Colors.HEADER}🔍 Deduplicando JSON: {input_file}{Colors.ENDC}")
        
        if self.backup:
            Utils.create_backup(input_file)

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                self.error("O JSON raiz deve ser uma lista (Array).")
                return

            original_len = len(data)
            unique_data = []
            seen = set()

            for item in data:
                # Se tiver chave específica (ex: 'id')
                if key:
                    if isinstance(item, dict) and key in item:
                        val = item[key]
                        # Hash do valor para garantir que tipos não-hashable (como dicts aninhados) funcionem
                        val_hash = str(val) 
                        if val_hash not in seen:
                            seen.add(val_hash)
                            unique_data.append(item)
                    else:
                        # Se o item não tem a chave, mantém ele (ou podia descartar, depende da lógica)
                        unique_data.append(item)
                else:
                    # Hash do objeto inteiro
                    item_str = json.dumps(item, sort_keys=True)
                    item_hash = hashlib.md5(item_str.encode()).digest()
                    if item_hash not in seen:
                        seen.add(item_hash)
                        unique_data.append(item)

            self.stats['removed'] = original_len - len(unique_data)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Itens únicos: {len(unique_data)}")
            print(f"🗑️  Removidos: {self.stats['removed']}")

        except json.JSONDecodeError:
            self.error("Arquivo JSON inválido ou corrompido.")
        except Exception as e:
            self.error(f"Erro JSON: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="🚀 Dedup Ultra - Removedor Profissional de Duplicatas",
        epilog="Ex: python dedup.py files ./minha_pasta --delete"
    )
    
    subparsers = parser.add_subparsers(dest='mode', required=True, help='Modo de operação')

    # Modo Files
    p_files = subparsers.add_parser('files', help='Encontrar arquivos duplicados')
    p_files.add_argument('path', type=Path, help='Diretório para escanear')
    p_files.add_argument('--delete', action='store_true', help='Deletar arquivos duplicados (mantém o mais antigo/primeiro)')

    # Modo Lines
    p_lines = subparsers.add_parser('lines', help='Remover linhas duplicadas de texto')
    p_lines.add_argument('file', type=Path, help='Arquivo de entrada')
    p_lines.add_argument('-o', '--output', type=Path, help='Arquivo de saída (Opcional)')
    p_lines.add_argument('--no-backup', action='store_true', help='Não criar arquivo .bak')

    # Modo CSV
    p_csv = subparsers.add_parser('csv', help='Remover duplicatas em CSV')
    p_csv.add_argument('file', type=Path, help='Arquivo CSV')
    p_csv.add_argument('-o', '--output', type=Path, help='Arquivo de saída')
    p_csv.add_argument('--cols', help='Colunas para verificar duplicidade (separadas por vírgula)')
    p_csv.add_argument('--no-backup', action='store_true', help='Não criar arquivo .bak')

    # Modo JSON
    p_json = subparsers.add_parser('json', help='Remover duplicatas em JSON')
    p_json.add_argument('file', type=Path, help='Arquivo JSON')
    p_json.add_argument('-o', '--output', type=Path, help='Arquivo de saída')
    p_json.add_argument('--key', help='Chave JSON (ex: id) para verificar unicidade')
    p_json.add_argument('--no-backup', action='store_true', help='Não criar arquivo .bak')

    # Argumentos globais
    parser.add_argument('-v', '--verbose', action='store_true', help='Mostrar detalhes do processo')

    args = parser.parse_args()
    
    # Configuração Inicial
    do_backup = not getattr(args, 'no_backup', False)
    dedup = Deduplicator(verbose=args.verbose, backup=do_backup)

    print("="*60)
    print(f"{Colors.BOLD}🔧 DEDUP ULTRA 2.0{Colors.ENDC}")
    print("="*60)

    # Roteamento de Comandos
    if args.mode == 'files':
        if not args.path.is_dir():
            dedup.error("O caminho deve ser um diretório.")
            sys.exit(1)
        dedup.process_files(args.path, delete=args.delete)
        
        if dedup.stats['removed'] > 0:
            mb_saved = dedup.stats['space_saved'] / (1024 * 1024)
            print(f"\n🎉 Espaço recuperado: {mb_saved:.2f} MB")

    elif args.mode == 'lines':
        out = args.output or args.file
        dedup.process_lines(args.file, out)

    elif args.mode == 'csv':
        out = args.output or args.file
        cols = args.cols.split(',') if args.cols else None
        dedup.process_csv(args.file, out, cols)

    elif args.mode == 'json':
        out = args.output or args.file
        dedup.process_json(args.file, out, args.key)

if __name__ == "__main__":
    main()