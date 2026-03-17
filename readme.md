# 🗂️ Projeto Importantes

Este repositório contém uma coleção de scripts utilitários desenvolvidos em **Python**, focados em simplificar e automatizar a gestão de ficheiros locais. O projeto inclui ferramentas para a eliminação de ficheiros duplicados e para a análise/organização de bibliotecas de música, além de um guia de referência de comandos.

## 🚀 Funcionalidades

O projeto é composto pelos seguintes ficheiros principais:

* **`dedup.py`**: Um script focado na deduplicação de ficheiros. Ajuda a analisar diretórios, identificar ficheiros duplicados (geralmente através de *hashes* ou tamanho) e removê-los para libertar espaço no disco.
* **`musicscanner.py`**: Um utilitário de digitalização e organização de música. Ideal para varrer diretórios à procura de ficheiros de áudio, ler metadados ou organizar bibliotecas musicais.
* **`comandos.txt`**: Um documento de texto puro que serve como uma "cábula" (*cheat sheet*), contendo uma lista de comandos importantes, atalhos de terminal ou instruções de execução para auxiliar no dia a dia.

## 📋 Pré-requisitos

Para executar os scripts deste repositório, necessitas de ter o Python instalado no teu sistema.

* [Python 3.x](https://www.python.org/downloads/) instalado.
* (Opcional) Poderão ser necessárias bibliotecas externas dependendo das importações feitas nos scripts. Recomenda-se a criação de um ambiente virtual (*virtual environment*).

## 🔧 Como usar

1. **Clonar o repositório:**
Abre o teu terminal e executa o seguinte comando:
```bash
git clone [https://github.com/phoenixsrd/importantes.git](https://github.com/phoenixsrd/importantes.git)
cd importantes
```
2. **Para executar o script de deduplicação:**
```bash
python dedup.py
```
3. **Para executar o scanner de música:**
```bash
python musicscanner.py
```
4. **Consultar os comandos:**
```bash
cat comandos.txt
```

## 🤝 Contribuição

* Contribuições são sempre bem-vindas! Se tens ideias para melhorar os scripts atuais ou se queres adicionar novos utilitários, sente-te à vontade para o fazer:
* Faz um Fork do projeto
* Cria uma Branch para a tua funcionalidade (git checkout -b feature/NovaFuncionalidade)
* Faz Commit das tuas alterações (git commit -m 'Adiciona nova funcionalidade de...')
* Faz o Push para a Branch (git push origin feature/NovaFuncionalidade)
* Abre um Pull Request

## 📄 Licença

* Este projeto está sob a licença MIT.
* Consulta o ficheiro [license](https://github.com/phoenixsrd/importantes/blob/6e6e3cf706b5cf30004f51c2bc5bdd7acb7ce139/license) para mais detalhes.
* Qualquer pessoa pode usar, copiar, modificar e distribuir este software de forma livre e gratuita, desde que seja incluída a nota de direitos de autor.
