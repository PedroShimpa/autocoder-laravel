import requests
import subprocess
import re
import os
import argparse
import json
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "laravel-coder")
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
MAX_TESTS_ATTEMPTS = os.getenv("MAX_TESTS_ATTEMPTS", 10)
LOG_FILE = "ollama_log.txt"

def run_php_tests():
    try:
        result = subprocess.run(
            ["php", "artisan", "test"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        print(result.stdout)
        return result.stdout
    except Exception as e:
        return f"Erro ao executar testes: {e}"

def log_conversation(user_prompt, response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n=== {timestamp} ===\n")
        log.write("user send:\n")
        log.write(user_prompt.strip() + "\n")
        log.write("=================\n")
        log.write("ollama reply:\n")
        log.write(response.strip() + "\n")
        log.write("=================\n")

def send_to_ollama(messages):
    response = requests.post(
        f"{OLLAMA_ENDPOINT}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True
        },
        stream=True
    )
    response.raise_for_status()

    full_response = ""
    for line in response.iter_lines():
        if not line:
            continue
        data = line.decode("utf-8")
        if data.strip() == "data: [DONE]":
            break
        if data.startswith("data: "):
            try:
                content = json.loads(data[6:])
                chunk = content.get("message", {}).get("content", "")
                print(chunk, end="", flush=True)
                full_response += chunk
            except Exception as e:
                print(f"\n⚠️ Error parsing stream chunk: {e}")

    log_conversation(messages[-1]["content"], full_response)
    return full_response


def apply_response(response):
    command_pattern = re.search(r"^command:\s*(.+)$", response, re.MULTILINE)
    if command_pattern:
        commands = [cmd.strip() for cmd in command_pattern.group(1).split(",")]
        for cmd in commands:
            print(f"\n🛠️ Executing: {cmd}")
            subprocess.run(cmd, shell=True)

    for match in re.finditer(r"edit:\s*(.*?)\s*from\n```php\n(.*?)\n```\nto\n```php\n(.*?)\n```", response, re.DOTALL):
        path, old_code, new_code = match.groups()
        if not os.path.isfile(path):
            print(f"\n❌ File not found for edit: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_code.strip() not in content:
            print(f"\n⚠️ Old code not found in {path}, skipping edit.")
            continue
        updated = content.replace(old_code.strip(), new_code.strip())
        with open(path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"\n✅ Edited: {path}")

    for match in re.finditer(r"create:\s*(.*?)\s*```php\n(.*?)\n```", response, re.DOTALL):
        path, code = match.groups()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip())
        print(f"\n🆕 Created: {path}")

def loop_until_tests_pass(initial_prompt):
    messages = [
        {"role": "user", "content": initial_prompt.strip()}
    ]

    for attempt in range(MAX_TESTS_ATTEMPTS):
        print(f"\n🔁 Tentativa {attempt + 1}/{MAX_TESTS_ATTEMPTS}")

        test_output = run_php_tests()

        if "FAIL" not in test_output and "ERROR" not in test_output:
            print("\n✅ Todos os testes passaram. Nada a fazer.")
            return

        # Acrescenta saída de erro como parte da conversa
        messages.append({
            "role": "user",
            "content": f"Resultado do 'php artisan test':\n{test_output.strip()}"
        })

        response = send_to_ollama(messages)

        # Adiciona a resposta ao histórico
        messages.append({
            "role": "assistant",
            "content": response.strip()
        })

        apply_response(response)

        print("\n▶️ Reexecutando testes...")
        test_output_after = run_php_tests()

        if "FAIL" not in test_output_after and "ERROR" not in test_output_after:
            print("\n✅ Problema corrigido!")
            return
        else:
            print("\n❌ Ainda há falhas. Reenviando novo erro ao Ollama...")

    print("\n🚫 Número máximo de tentativas atingido. Corrija manualmente.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a message to Ollama and apply code changes.")
    parser.add_argument("--user", required=True, help="User prompt (question or task)")
    args = parser.parse_args()

    loop_until_tests_pass(args.user)
