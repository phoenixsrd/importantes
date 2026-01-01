#!/usr/bin/env python3

import os
import sys
import hashlib
import json
import argparse
from pathlib import Path
from collections import defaultdict

class DuplicateRemover:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.duplicates_found = 0
        
    def log(self, message):
        if self.verbose:
            print(f"[INFO] {message}")
    
    def hash_file(self, filepath):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.log(f"Erro ao processar {filepath}: {e}")
            return None
    
    def find_duplicate_files(self, directory, remove=False):
        print(f"\n🔍 Procurando arquivos duplicados em: {directory}")
        
        hashes = defaultdict(list)
        
        for root, _, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                file_hash = self.hash_file(filepath)
                
                if file_hash:
                    hashes[file_hash].append(filepath)
        
        duplicates = {h: files for h, files in hashes.items() if len(files) > 1}
        
        if not duplicates:
            print("✅ Nenhum arquivo duplicado encontrado!")
            return
        
        print(f"\n⚠️  Encontrados {len(duplicates)} grupos de arquivos duplicados:")
        
        for hash_val, files in duplicates.items():
            print(f"\n📁 Grupo (hash: {hash_val[:8]}...):")
            for i, f in enumerate(files):
                status = "MANTIDO" if i == 0 else "DUPLICADO"
                print(f"  [{status}] {f}")
            
            if remove and len(files) > 1:
                for duplicate in files[1:]:
                    try:
                        os.remove(duplicate)
                        print(f"  🗑️  Removido: {duplicate}")
                        self.duplicates_found += 1
                    except Exception as e:
                        print(f"  ❌ Erro ao remover {duplicate}: {e}")
    
    def remove_duplicate_lines(self, input_file, output_file=None, keep_order=False):
        print(f"\n🔍 Removendo linhas duplicadas de: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            original_count = len(lines)
            
            if keep_order:
                seen = set()
                unique_lines = []
                for line in lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
            else:
                unique_lines = list(set(lines))
            
            duplicates_removed = original_count - len(unique_lines)
            
            output = output_file or input_file
            with open(output, 'w', encoding='utf-8') as f:
                f.writelines(unique_lines)
            
            print(f"✅ Linhas originais: {original_count}")
            print(f"✅ Linhas únicas: {len(unique_lines)}")
            print(f"🗑️  Duplicatas removidas: {duplicates_removed}")
            print(f"💾 Salvo em: {output}")
            
            self.duplicates_found += duplicates_removed
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def remove_duplicate_json_items(self, input_file, output_file=None, key=None):
        print(f"\n🔍 Removendo duplicatas JSON de: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print("❌ O arquivo JSON deve conter um array no nível raiz")
                return
            
            original_count = len(data)
            
            if key:
                seen = set()
                unique_data = []
                for item in data:
                    if isinstance(item, dict) and key in item:
                        val = item[key]
                        if val not in seen:
                            seen.add(val)
                            unique_data.append(item)
                    else:
                        unique_data.append(item)
            else:
                unique_data = []
                seen = set()
                for item in data:
                    item_str = json.dumps(item, sort_keys=True)
                    if item_str not in seen:
                        seen.add(item_str)
                        unique_data.append(item)
            
            duplicates_removed = original_count - len(unique_data)
            
            output = output_file or input_file
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(unique_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Itens originais: {original_count}")
            print(f"✅ Itens únicos: {len(unique_data)}")
            print(f"🗑️  Duplicatas removidas: {duplicates_removed}")
            print(f"💾 Salvo em: {output}")
            
            self.duplicates_found += duplicates_removed
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def remove_duplicate_csv_rows(self, input_file, output_file=None, columns=None):
        print(f"\n🔍 Removendo linhas duplicadas CSV de: {input_file}")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                print("❌ Arquivo vazio")
                return
            
            header = lines[0]
            data_lines = lines[1:]
            original_count = len(data_lines)
            
            if columns:
                header_parts = header.strip().split(',')
                col_indices = [header_parts.index(col) for col in columns if col in header_parts]
                
                seen = set()
                unique_lines = [header]
                
                for line in data_lines:
                    parts = line.strip().split(',')
                    key = tuple(parts[i] for i in col_indices if i < len(parts))
                    if key not in seen:
                        seen.add(key)
                        unique_lines.append(line)
            else:
                unique_lines = [header] + list(dict.fromkeys(data_lines))
            
            duplicates_removed = original_count - (len(unique_lines) - 1)
            
            output = output_file or input_file
            with open(output, 'w', encoding='utf-8') as f:
                f.writelines(unique_lines)
            
            print(f"✅ Linhas originais: {original_count}")
            print(f"✅ Linhas únicas: {len(unique_lines) - 1}")
            print(f"🗑️  Duplicatas removidas: {duplicates_removed}")
            print(f"💾 Salvo em: {output}")
            
            self.duplicates_found += duplicates_removed
            
        except Exception as e:
            print(f"❌ Erro: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="🔧 Detector e Removedor Universal de Duplicatas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  
  Encontrar arquivos duplicados:
    python dedup.py files /caminho/pasta --scan
  
  Remover arquivos duplicados:
    python dedup.py files /caminho/pasta --remove
  
  Remover linhas duplicadas:
    python dedup.py lines arquivo.txt
  
  Remover duplicatas JSON:
    python dedup.py json dados.json --key id
  
  Remover linhas duplicadas CSV:
    python dedup.py csv dados.csv --columns nome,email
        """
    )
    
    parser.add_argument('mode', choices=['files', 'lines', 'json', 'csv'],
                       help='Modo de operação')
    parser.add_argument('path', help='Arquivo ou diretório para processar')
    parser.add_argument('-o', '--output', help='Arquivo de saída (padrão: sobrescreve o original)')
    parser.add_argument('--remove', action='store_true', 
                       help='Remove duplicatas (para modo files)')
    parser.add_argument('--scan', action='store_true',
                       help='Apenas escaneia sem remover (para modo files)')
    parser.add_argument('--keep-order', action='store_true',
                       help='Mantém a ordem original (para modo lines)')
    parser.add_argument('--key', help='Chave para comparação (para modo json)')
    parser.add_argument('--columns', help='Colunas para comparação, separadas por vírgula (para modo csv)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    remover = DuplicateRemover(verbose=args.verbose)
    
    print("="*60)
    print("🔧 DETECTOR E REMOVEDOR UNIVERSAL DE DUPLICATAS")
    print("="*60)
    
    if args.mode == 'files':
        if not os.path.isdir(args.path):
            print(f"❌ Erro: {args.path} não é um diretório válido")
            sys.exit(1)
        
        should_remove = args.remove and not args.scan
        remover.find_duplicate_files(args.path, remove=should_remove)
    
    elif args.mode == 'lines':
        if not os.path.isfile(args.path):
            print(f"❌ Erro: {args.path} não é um arquivo válido")
            sys.exit(1)
        
        remover.remove_duplicate_lines(args.path, args.output, args.keep_order)
    
    elif args.mode == 'json':
        if not os.path.isfile(args.path):
            print(f"❌ Erro: {args.path} não é um arquivo válido")
            sys.exit(1)
        
        remover.remove_duplicate_json_items(args.path, args.output, args.key)
    
    elif args.mode == 'csv':
        if not os.path.isfile(args.path):
            print(f"❌ Erro: {args.path} não é um arquivo válido")
            sys.exit(1)
        
        columns = args.columns.split(',') if args.columns else None
        remover.remove_duplicate_csv_rows(args.path, args.output, columns)
    
    print("\n" + "="*60)
    print(f"✅ Processo concluído! Total de duplicatas removidas: {remover.duplicates_found}")
    print("="*60)


if __name__ == "__main__":
    main()