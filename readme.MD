# Github C Code Scrapper

# Coletor e Classificador de Erros em Código C

Este projeto coleta arquivos `.c` públicos do GitHub (produzidos por estudantes/iniciantes) e classifica automaticamente possíveis padrões de erro com base em uma taxonomia pré-definida, usando saída do compilador (`gcc`) e heurísticas de regex.

## Como funciona

1. **Coleta de referências** (`collect_code_references`): busca arquivos `.c` no GitHub via [Search API](https://docs.github.com/en/rest/search/search#search-code), usando uma lista de queries configuráveis (`COLLECTION_QUERIES`).
2. **Download do código-fonte** (`collect_source_code`): converte a URL do GitHub (`html_url`) para a versão raw (`raw.githubusercontent.com`) e baixa o conteúdo do arquivo.
3. **Compilação de teste** (`collect_compiler_messages`): salva o código em um arquivo temporário e roda `gcc -fsyntax-only` para capturar erros/avisos do compilador.
4. **Classificação** (`classify_code`): combina a saída do compilador com padrões de regex para atribuir um ou mais rótulos de erro (`ERROR_TAXONOMY`) a cada arquivo.
5. **Montagem do dataset** (`collect_dataset`): repete o processo para todas as queries, respeitando um limite de `MAX_CODES`, e monta um `DataFrame` com os resultados.
6. **Exportação**: salva o dataset final em `collected_c_code_dataset.csv`.

## Taxonomia de erros

Definida em `common.py`:

| Código | Categoria |
|---|---|
| 1 | `syntax_error` |
| 2 | `semantic_error` |
| 3 | `function_misuse` |
| 4 | `pointer_error` |
| 5 | `memory_error` |
| 6 | `control_structure_error` |
| 7 | `compiler_message_difficulty` |
| 8 | `typing_error` |
| 9 | `abstraction_difficulty` |

Cada arquivo coletado pode receber múltiplos rótulos simultaneamente.

## Pré-requisitos

- Python 3.9+
- `gcc` instalado e disponível no `PATH` (usado para checagem de sintaxe)
- Um [Personal Access Token do GitHub](https://github.com/settings/tokens) com permissão de leitura em repositórios públicos

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com:

```
GITHUB_TOKEN=seu_token_aqui
```

O token é carregado automaticamente via `python-dotenv`.

## Uso

```bash
python get_info.py
```

Ao final da execução, o script gera `collected_c_code_dataset.csv` com as colunas:

- `repository`: repositório de origem do arquivo
- `file`: nome do arquivo `.c`
- `labels`: lista de códigos de erro atribuídos (conforme `ERROR_TAXONOMY`)
- `compiler_messages`: saída bruta do `gcc -fsyntax-only`
- `code`: conteúdo completo do arquivo

## Parâmetros ajustáveis

Em `get_info.py`:

- `COLLECTION_QUERIES`: lista de termos de busca no GitHub (combinados com `extension:c`)
- `MAX_CODES`: número máximo de arquivos coletados no total

## Limitações conhecidas

- A **Search API** do GitHub tem limite de **10 requisições/minuto**, mesmo autenticado — buscas muito amplas podem sofrer *rate limiting* (HTTP 403).
- A detecção de `typing_error` atualmente usa um conjunto fixo de substrings (`typo_patterns`) como heurística simples; há um `TODO` no código para substituir por uma checagem baseada em distância de edição (Levenshtein) contra um dicionário de funções/specifiers válidos.
- A checagem de `abstraction_difficulty` (uso excessivo de `scanf`) é uma heurística preliminar e pode não refletir com precisão dificuldade de abstração.
- A classificação é feita por regras/regex, não por um modelo de linguagem — é sensível a falsos positivos/negativos em casos de código não convencional.

## Estrutura do projeto

```
.
├── common.py              # Taxonomia de erros
├── get_info.py             # Script principal (coleta + classificação)
├── requirements.txt        # Dependências Python
└── collected_c_code_dataset.csv  # Saída gerada após execução
```