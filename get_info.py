import csv
import os
import re
import subprocess
import tempfile
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

from common import ERROR_TAXONOMY

# =====================================================
# CONFIGURATION
# =====================================================
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

COLLECTION_QUERIES = [
    "language:C student exercise",
    "language:C beginner programming",
    "language:C programming assignment",
    "language:C introductory programming"
]

MAX_CODES = 500

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

# =====================================================
# COLLECT CODE
# =====================================================
def collect_code_references(query):
    url = "https://api.github.com/search/code"
    
    params = {
        "q": f"{query} extension:c",
        "per_page": 100,
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS
    )

    if response.status_code != 200:
        print(response.status_code, response.text)
        return []

    return response.json().get("items", [])


def collect_source_code(item):
    raw_url = (
        item["html_url"]
        .replace(
            "github.com",
            "raw.githubusercontent.com"
        )
        .replace(
            "/blob/",
            "/"
        )
    )

    try:
        response = requests.get(
            raw_url,
            timeout=10
        )

        if response.status_code == 200:
            return response.text

    except Exception as e:
        print(e)

    return None

# =====================================================
# COLLECT COMPILER OUTPUT
# =====================================================
def collect_compiler_messages(code):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".c",
            delete=False,
            encoding="utf-8",
            errors="ignore"
        ) as file:
            file.write(code)
            temp_path = file.name

        process = subprocess.run(
            [
                "gcc",
                "-fsyntax-only",
                temp_path
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        return process.stderr or ""

    except Exception as e:
        print("GCC não enconrado")
        return ""

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

# =====================================================
# CLASSIFICATION
# =====================================================
def classify_code(code):

    labels = set()
    compiler_output = (collect_compiler_messages(code))

    text = code.lower()

    # 1 — syntax
    syntax_patterns = [
        "expected",
        "missing",
        "syntax error",
        "undeclared"
    ]

    if any (
        pattern in compiler_output.lower()
        for pattern in syntax_patterns
    ):
        labels.add(ERROR_TAXONOMY["syntax_error"])

    # 2 — semantic
    if re.search(r"if\s*\(.*=.*\)", text) and "==" not in text:
        labels.add(ERROR_TAXONOMY["semantic_error"])

    # 3 — function misuse
    if re.search(
        r"(char|int|long|short)\s+\w+\(.*\)\s*\{",
        text,
        re.DOTALL
    ) and "return" not in text:
        labels.add(ERROR_TAXONOMY["function_misuse"])

    if (text.count("main(") and text.count("void") == 0):
        labels.add(ERROR_TAXONOMY["function_misuse"])

    # 4 — pointer
    if re.search(r"\*\w+\s*=", text):
        labels.add(ERROR_TAXONOMY["pointer_error"])

    # 5 — memory
    if ("malloc(" in text and "free(" not in text):
        labels.add(ERROR_TAXONOMY["memory_error"])

    if "gets(" in text:
        labels.add(ERROR_TAXONOMY["memory_error"])

    # 6 — control structure
    if re.search(r"while\s*\(\s*1\s*\)", text):
        labels.add(ERROR_TAXONOMY["control_structure_error"])

    # 7 — compiler difficulty
    if compiler_output:
        labels.add(ERROR_TAXONOMY["compiler_message_difficulty"])

    # 8 — typing
    #TODO: Usar algum algoritmo como aquele que o braço apresentou para verificar typos
    # muito melhor que esse set
    typo_patterns = {
        "print",
        "pritnf",
        "scnaf",
        "scan"
    }

    if any(typo in text for typo in typo_patterns):
        labels.add(ERROR_TAXONOMY["typing_error"])

    # 9 — abstraction
    #TODO: Não entendi esse?
    if text.count("scanf") > 5:
        labels.add(ERROR_TAXONOMY["abstraction_difficulty"])

    return list(labels), compiler_output

# =====================================================
# COLLECT DATASET
# =====================================================
def collect_dataset():
    records = []
    collected = 0

    for query in COLLECTION_QUERIES:
        print(f"\nCollecting: {query}")

        references = collect_code_references(query)

        for item in tqdm(references):

            if collected >= MAX_CODES:
                break

            code = (collect_source_code(item))

            if not code:
                continue

            labels, messages = (classify_code(code))

            if labels:
                records.append({
                    "repository":
                    item["repository"]["full_name"],

                    "file":
                    item["name"],

                    "labels":
                    labels,

                    "compiler_messages":
                    messages,

                    "code":
                    code
                })
                collected += 1
            time.sleep(0.3)

    return pd.DataFrame(records)

# =====================================================
# EXECUTION
# =====================================================
dataset = collect_dataset()
dataset.to_csv(
    "collected_c_code_dataset.csv",
    index=False,
    quoting=csv.QUOTE_NONNUMERIC,
    escapechar='//'
)

print("\nCollection completed.")
print(f"Total collected: {len(dataset)}")
