import asyncio
import logging
import subprocess

async def call_terminal_command(command, index):
    try:
        result = await asyncio.to_thread(subprocess.run, command, shell=True, check=True, capture_output=True, text=True)
        return f"Execução {index} - Saída:\n{result.stdout}"
    except subprocess.CalledProcessError as err:
        return f"Execução {index} - Erro ao executar a request: {err}"

async def main():

    leader=""
    with open('leader.txt', 'r') as f:
        leader = f.read()
    # Request
    host = "10.7.125.172:12000"
    # host = "127.0.0.1:12000"
    request = f"python -m nidus --leader={leader.rstrip()} SET requests req "

    # Configuração do logger
    log_filename = "requests.log"
    logging.basicConfig(filename=log_filename, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Criar tarefas assíncronas para as chamadas ao terminal
    tasks = []
    for i in range(1, 70):
        full_request = f"{request} {i}"
        task = asyncio.create_task(call_terminal_command(full_request, i))
        tasks.append(task)
        await asyncio.sleep(0.5)

    # Aguardar todas as tarefas assíncronas
    # responses = await asyncio.gather(*tasks)

    # # Registrar e imprimir as respostas
    # for response in responses:
    #     logging.info(response)
    #     print(response)

    print("Final da execução")

# Executar o loop de eventos assíncronos
if __name__ == "__main__":
    asyncio.run(main())
