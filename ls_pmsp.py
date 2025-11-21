import copy
import json
import argparse
import time


# --- 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS ---
def carregar_instancia_de_json(caminho_arquivo):
    """
    Lê um arquivo de instância .json, converte as estruturas de dados e
    prepara os dados para o algoritmo, incluindo a criação da linha '0' da matriz de setup.
    """
    with open(caminho_arquivo, 'r') as f:
        dados = json.load(f)

    config = dados['configuracao']
    n_jobs = config['n_jobs']

    # Converte listas para dicionários com chaves de 1 a N_JOBS
    processing_times = {i + 1: val for i, val in enumerate(dados['tempos_processamento'])}
    release_dates = {i + 1: val for i, val in enumerate(dados['ready_times'])}
    
    # Converte a matriz (lista de listas) para um dicionário aninhado com chaves inteiras
    setup_matrix_dict = {}
    matriz_lista = dados['matriz_setup']
    for i in range(n_jobs):
        setup_matrix_dict[i + 1] = {}
        for j in range(n_jobs):
            valor = matriz_lista[i][j] if matriz_lista[i][j] is not None else 0
            setup_matrix_dict[i + 1][j + 1] = valor

    # Cria a linha '0' da matriz de setup (setup do estado inicial para a primeira tarefa)
    setup_matrix_dict['0'] = {}
    for j in range(1, n_jobs + 1):
        # O setup inicial para 'j' é o maior tempo de setup de qualquer outra tarefa para 'j'
        max_setup_to_j = 0
        for i in range(1, n_jobs + 1):
            if i == j: continue
            max_setup_to_j = max(max_setup_to_j, setup_matrix_dict[i][j])
        setup_matrix_dict['0'][j] = max_setup_to_j

    return config, processing_times, setup_matrix_dict, release_dates

# --- 2. FUNÇÕES DO ALGORITMO ---
def calculate_sequence_time(sequence, processing_times, setup_matrix, release_dates):
    """Calcula o tempo total de conclusão para uma dada sequência de tarefas em uma máquina
       NO MESMO MODELO DO GA: sem setup inicial de '0'."""
    completion_time = 0
    last_task = None  # nenhuma tarefa antes do primeiro job

    if not sequence:
        return 0
    
    for task_id in sequence:
        start_time = max(completion_time, release_dates[task_id])
        
        if last_task is None:
            # Primeiro job da máquina: não paga setup
            setup_time = 0
        else:
            # Demais jobs: pagam setup entre tarefas reais
            setup_time = setup_matrix[last_task][task_id]
        
        proc_time = processing_times[task_id]
        completion_time = start_time + setup_time + proc_time
        last_task = task_id
        
    return completion_time

# --- 3. SOLUÇÃO INICIAL COM FFD ---
def solve_with_ffd(config, processing_times, setup_matrix, release_dates):
    """Gera uma solução inicial usando uma abordagem baseada em First Fit Decreasing (FFD)."""
    n_machines = config['n_maquinas']
    sorted_tasks = sorted(processing_times.keys(), key=lambda task: processing_times[task], reverse=True)
    
    machines = {m_id: [] for m_id in range(1, n_machines + 1)}
    
    for task_id in sorted_tasks:
        potential_times = {}
        for machine_id in machines:
            temp_sequence = machines[machine_id] + [task_id]
            potential_times[machine_id] = calculate_sequence_time(temp_sequence, processing_times, setup_matrix, release_dates)
        
        best_machine = min(potential_times, key=potential_times.get)
        machines[best_machine].append(task_id)
        
    return machines

# --- 4. APLICANDO BUSCA LOCAL ---
def local_search(initial_sequences, config, processing_times, setup_matrix, release_dates):
    """
    Aplica busca local focada em makespan, com vizinhanças restritas:

    - Transferência: apenas da máquina com maior makespan (m_max) para a com menor makespan (m_min)
    - Troca inter-máquinas: apenas entre m_max e m_min
    - Troca intra-máquina: apenas dentro de m_max

    Mantém o mesmo modelo de cálculo de tempo:
      - setup inicial a partir da tarefa '0'
      - setups entre tarefas reais conforme setup_matrix
    """
    # Cópia da solução inicial
    current_solution = copy.deepcopy(initial_sequences)
    n_machines = config['n_maquinas']
    machine_ids = list(range(1, n_machines + 1))

    # Calcula tempos iniciais por máquina
    machine_times = {
        m_id: calculate_sequence_time(seq, processing_times, setup_matrix, release_dates)
        for m_id, seq in current_solution.items()
    }
    current_makespan = max(machine_times.values()) if machine_times else 0

    iteration = 0
    while True:
        iteration += 1
        best_neighbor_solution = None
        best_neighbor_makespan = current_makespan

        # Identifica a máquina com maior makespan (m_max) e menor makespan (m_min)
        m_max = max(machine_times, key=machine_times.get)
        m_min = min(machine_times, key=machine_times.get)

        seq_max = current_solution[m_max]
        seq_min = current_solution[m_min]

        # Maior tempo entre as demais máquinas (que não mudam nos vizinhos)
        other_ids = [m for m in machine_ids if m not in (m_max, m_min)]
        if other_ids:
            max_outros = max(machine_times[m] for m in other_ids)
        else:
            max_outros = 0

        # ---------------------------------------------------------
        # VIZINHANÇA 1: Transferência m_max -> m_min
        # (move uma tarefa de m_max para o fim de m_min)
        # ---------------------------------------------------------
        for i in range(len(seq_max)):
            # Remove tarefa de m_max
            new_seq_max = seq_max[:]          # cópia rasa
            task_to_move = new_seq_max.pop(i) # retira a tarefa na posição i

            # Adiciona no final de m_min
            new_seq_min = seq_min[:] + [task_to_move]

            # Recalcula só tempos de m_max e m_min
            time_max = calculate_sequence_time(new_seq_max, processing_times, setup_matrix, release_dates)
            time_min = calculate_sequence_time(new_seq_min, processing_times, setup_matrix, release_dates)

            # As demais máquinas mantêm seus tempos
            if n_machines == 1:
                neighbor_makespan = time_max
            elif n_machines == 2:
                neighbor_makespan = max(time_max, time_min)
            else:
                neighbor_makespan = max(time_max, time_min, max_outros)

            if neighbor_makespan < best_neighbor_makespan:
                best_neighbor_makespan = neighbor_makespan
                # Monta solução vizinha completa
                neighbor = copy.deepcopy(current_solution)
                neighbor[m_max] = new_seq_max
                neighbor[m_min] = new_seq_min
                best_neighbor_solution = neighbor

        # ---------------------------------------------------------
        # VIZINHANÇA 2: Troca Inter-Máquinas entre m_max e m_min
        # ---------------------------------------------------------
        for i in range(len(seq_max)):
            for j in range(len(seq_min)):
                new_seq_max = seq_max[:]
                new_seq_min = seq_min[:]

                # Troca as tarefas nas posições i e j
                new_seq_max[i], new_seq_min[j] = new_seq_min[j], new_seq_max[i]

                # Recalcula só tempos de m_max e m_min
                time_max = calculate_sequence_time(new_seq_max, processing_times, setup_matrix, release_dates)
                time_min = calculate_sequence_time(new_seq_min, processing_times, setup_matrix, release_dates)

                if n_machines == 2:
                    neighbor_makespan = max(time_max, time_min)
                else:
                    neighbor_makespan = max(time_max, time_min, max_outros)

                if neighbor_makespan < best_neighbor_makespan:
                    best_neighbor_makespan = neighbor_makespan
                    neighbor = copy.deepcopy(current_solution)
                    neighbor[m_max] = new_seq_max
                    neighbor[m_min] = new_seq_min
                    best_neighbor_solution = neighbor

        # ---------------------------------------------------------
        # VIZINHANÇA 3: Troca Intra-Máquina apenas em m_max
        # ---------------------------------------------------------
        seq_len = len(seq_max)
        if seq_len >= 2:
            for i in range(seq_len):
                for j in range(i + 1, seq_len):
                    new_seq_max = seq_max[:]
                    new_seq_max[i], new_seq_max[j] = new_seq_max[j], new_seq_max[i]

                    # Só m_max muda
                    time_max = calculate_sequence_time(new_seq_max, processing_times, setup_matrix, release_dates)

                    if n_machines == 1:
                        neighbor_makespan = time_max
                    elif n_machines == 2:
                        neighbor_makespan = max(time_max, machine_times[m_min])
                    else:
                        neighbor_makespan = max(time_max, machine_times[m_min], max_outros)

                    if neighbor_makespan < best_neighbor_makespan:
                        best_neighbor_makespan = neighbor_makespan
                        neighbor = copy.deepcopy(current_solution)
                        neighbor[m_max] = new_seq_max
                        best_neighbor_solution = neighbor

        # ---------------------------------------------------------
        # Atualização da solução
        # ---------------------------------------------------------
        if best_neighbor_solution is None:
            print("=> Ótimo local encontrado. Nenhuma melhoria adicional.")
            break
        else:
            makespan_anterior = current_makespan
            current_solution = best_neighbor_solution
            current_makespan = best_neighbor_makespan
            melhoria_iteracao = makespan_anterior - current_makespan

            # Recalcula tempos de todas as máquinas para a nova solução
            machine_times = {
                m_id: calculate_sequence_time(seq, processing_times, setup_matrix, release_dates)
                for m_id, seq in current_solution.items()
            }

            print(f"=> Iteração {iteration}: Melhoria encontrada! "
                  f"Novo Makespan: {current_makespan:.2f} (Ganho: {melhoria_iteracao:.2f})")

    return current_solution, current_makespan, iteration




# --- 5. CACULANDO O LIMITE INFERIOR DDLB ---
def calcular_ddlb(config, processing_times, setup_matrix, release_dates):
    """
    Calcula o Data Dependent Lower Bound (DDLB) corrigido,
    consistente com o modelo SEM teardown final e com a estrutura
    de dados deste arquivo (dicionários 1..n).

    Ideia (mesma do GA, só adaptada para dicionário):
    - Para cada job i, δ_i = menor setup saindo de i para qualquer j != i (entre jobs reais).
    - Em qualquer agenda com m máquinas, n_jobs - m jobs pagarão setup de saída.
    - Setup total mínimo = sum(δ_i) - soma dos m maiores δ_i.
    - Limite de carga = (sum p_i + setup_total_min) / m
    - Limite de caminho crítico = max_i (r_i + p_i + δ_i)
    - DDLB = max(limite_carga_trabalho, limite_caminho_critico)
    """
    n_jobs = config['n_jobs']
    n_machines = config['n_maquinas']

    # 1) Calcula δ_i = menor setup saindo de i (somente entre jobs reais 1..n)
    deltas = {}
    for i in range(1, n_jobs + 1):
        min_setup_i = min(
            setup_matrix[i][j]
            for j in range(1, n_jobs + 1)
            if j != i
        )
        deltas[i] = min_setup_i

    # 2) Soma dos tempos de processamento e dos δ_i
    soma_p = sum(processing_times[i] for i in range(1, n_jobs + 1))
    soma_deltas = sum(deltas[i] for i in range(1, n_jobs + 1))

    # 3) Setup total mínimo: tira os m maiores δ_i
    deltas_ordenados = sorted(deltas.values(), reverse=True)
    soma_maiores = sum(deltas_ordenados[:n_machines])
    setup_total_minimo = soma_deltas - soma_maiores

    limite_carga_trabalho = (soma_p + setup_total_minimo) / n_machines

    # 4) Limite de caminho crítico: max_i (r_i + p_i + δ_i)
    limite_caminho_critico = 0.0
    for i in range(1, n_jobs + 1):
        caminho_i = release_dates[i] + processing_times[i] + deltas[i]
        if caminho_i > limite_caminho_critico:
            limite_caminho_critico = caminho_i

    ddlb = max(limite_carga_trabalho, limite_caminho_critico)
    return ddlb


# --- 3. ORQUESTRAÇÃO E EXECUÇÃO PRINCIPAL ---

def run_scenario_from_file(file_path):
    """Orquestra o processo: carregar, resolver e exibir resultados para um arquivo."""
    print("="*50)
    print(f"EXECUTANDO CENÁRIO DO ARQUIVO: {file_path}")
    print("="*50)
    
    try:
        config, proc_times, setup_mat, release_dts = carregar_instancia_de_json(file_path)
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{file_path}' não foi encontrado.")
        return
    except Exception as e:
        print(f"ERRO ao carregar ou processar o arquivo: {e}")
        return

    # Gerar Solução Inicial
    print("\n[FASE 1: GERANDO SOLUÇÃO INICIAL COM FFD]")
    initial_solution = solve_with_ffd(config, proc_times, setup_mat, release_dts)
    initial_times = {m_id: calculate_sequence_time(seq, proc_times, setup_mat, release_dts) for m_id, seq in initial_solution.items()}
    makespan_initial = max(initial_times.values()) if initial_times else 0
    
    print("\n--- Solução Inicial Encontrada ---")
    for m_id, seq in initial_solution.items():
        print(f"Máquina {m_id}: Seq={seq}, Tempo={initial_times[m_id]:.0f}")
    print(f"Makespan Inicial: {makespan_initial:.2f}")

    # Aplicar Busca Local
    print("\n[FASE 2: APLICANDO BUSCA LOCAL PARA MELHORIA]")

    #Contagem de tempo
    start_time = time.time()
    # ATUALIZAÇÃO: Captura o número de iterações retornado pela função
    final_solution, final_makespan, total_iteracoes = local_search(initial_solution, config, proc_times, setup_mat, release_dts)
    
    #Final da contagem de tempo.
    end_time = time.time()
    tempo_busca_local = end_time - start_time

    # Calcular DDLB
    ddlb = calcular_ddlb(config, proc_times, setup_mat, release_dts)
    ratio_ms_ddlb = final_makespan / ddlb if ddlb > 0 else 0
    
    # Exibir Resultado Final
    final_times = {m_id: calculate_sequence_time(seq, proc_times, setup_mat, release_dts) for m_id, seq in final_solution.items()}
    
    print("\n" + "="*50)
    print(f"RESULTADO FINAL PARA {config.get('codigo_cenario', 'Cenário Desconhecido')}")
    print("="*50)
    print("--- Solução Após Busca Local ---")
    for m_id, seq in final_solution.items():
        print(f"Máquina {m_id}: Seq={seq}, Tempo={final_times[m_id]:.0f}")
    
    # BLOCO DE MÉTRICAS ATUALIZADO
    print("\n--- Métricas de Avaliação ---")
    print(f"Makespan Final (MS): {final_makespan:.2f}")
    print(f"Limite Inferior (DDLB): {ddlb:.2f}")
    print(f"Razão MS/DDLB: {ratio_ms_ddlb:.4f}")
    print(f"Melhoria de Makespan sobre a solução inicial: {makespan_initial - final_makespan:.2f}")
    print(f"Quantidade de iterações realizadas: {total_iteracoes}")
    print(f"Tempo de execução da busca local: {tempo_busca_local*1000:.2f} ms")
    print("\n")

if __name__ == "__main__":
    # Configura o parser de argumentos para receber o caminho do arquivo
    parser = argparse.ArgumentParser(description="Resolve o Problema de Agendamento a partir de um arquivo de instância JSON.")
    
    # Define "caminho_arquivo" como um argumento posicional obrigatório
    parser.add_argument("caminho_arquivo", type=str, help="O caminho para o arquivo .json da instância do problema.")
    
    # Lê os argumentos fornecidos na linha de comando
    args = parser.parse_args()
    
    # Chama a função principal passando o caminho do arquivo lido
    run_scenario_from_file(args.caminho_arquivo)