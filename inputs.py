import subprocess
import asyncio
import time
import logging

def call_terminal_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as err:
        logging.error(f"Erro ao executar a request: {err}")
        return ""

# Request 
request = "python -m nidus --leader=10.7.125.172:12000 SET requests req "

# Configuração do logger
log_filename = "requests_log.txt"
logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Requests ao lider para adicionar valores 30 vezes com um intervalo de 2 segundos
for i in range(1, 31):
    full_request = f"{request} {i}"
    output = call_terminal_command(full_request)
    log_message = f"INPUT: {full_request}\nOUTPUT: {output}"
    logging.info(log_message)
    print(log_message)
    time.sleep(2)

print("final da execução")