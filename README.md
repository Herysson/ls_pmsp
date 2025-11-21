# Busca Local para o Problema de Máquinas Paralelas (PMSP)

Este repositório contém uma implementação em Python de uma **Busca Local (Local Search – LS)** para resolver o problema de **Agendamento em Máquinas Paralelas com tempos de setup dependentes da sequência e tempos de liberação (ready times)**. 

As instâncias do problema usadas nos testes podem ser obtidas no repositório:

> [https://github.com/Herysson/pmsp-instance-generator](https://github.com/Herysson/pmsp-instance-generator)
> (arquivo `instancias.zip`)

---

## 1. Visão geral do problema

De forma simples, o problema é:

* Temos **vários jobs** (tarefas) para processar.
* Temos **várias máquinas paralelas** que podem receber esses jobs.
* Cada job:

  * possui um **tempo de processamento**;
  * só pode começar após um certo **tempo de liberação** (*ready time*);
  * quando trocamos de um job para outro, há um **tempo de setup** que depende da sequência (quem vem antes de quem).

O objetivo é **distribuir e ordenar** esses jobs nas máquinas de modo a **minimizar o makespan**, isto é, o tempo em que o último job termina.

---

## 2. Ideia geral da heurística de Busca Local

O código principal está em `ls_pmsp.py`. A busca local não começa “do zero”: primeiro é construída uma **solução inicial** usando uma heurística do tipo **FFD (First Fit Decreasing)**, que distribui os jobs nas máquinas de maneira razoável (mas não ótima). Em seguida, a função `local_search` tenta **melhorar essa solução inicial**. 

A ideia da `local_search` é:

1. Calcular o **tempo total de cada máquina** (quanto tempo leva para processar todos os jobs alocados nela).
2. Identificar:

   * a máquina com **maior makespan** (chamada `m_max`),
   * a máquina com **menor tempo** (chamada `m_min`).
3. Gerar soluções vizinhas mexendo **apenas nessas máquinas**:

   * mover jobs de `m_max` para `m_min`,
   * trocar jobs entre `m_max` e `m_min`,
   * trocar a ordem dos jobs **dentro** de `m_max`.
4. Entre todas as vizinhas, escolher **aquela que realmente melhora o makespan**.
5. Atualizar a solução e repetir o processo enquanto for possível melhorar.

Quando não há mais vizinho que melhore o makespan, a busca local **para em um ótimo local**.

---

## 3. Cálculo do tempo de uma sequência (função de apoio)

Antes de entrar na busca local, é importante entender a função:

```python
calculate_sequence_time(sequence, processing_times, setup_matrix, release_dates)
```

Ela calcula o **tempo total** de uma máquina, dada a lista de jobs (`sequence`) que estão nela. O funcionamento é:

* Começa com `completion_time = 0` (máquina livre no tempo 0).
* Para cada job na sequência:

  * o job só pode começar quando:

    * a máquina estiver livre **e**
    * o job estiver liberado (`ready_time`) → usamos o `max(...)`.
  * somamos:

    * o tempo de setup entre o último job e o job atual (exceto para o primeiro, que não paga setup),
    * o tempo de processamento do job.

O pseudo-código é:

```text
completion_time = 0
last_task = nenhum

para cada job na sequência:
    start_time = max(completion_time, release_date[job])

    se last_task é nenhum:
        setup_time = 0          # primeiro job não paga setup
    senão:
        setup_time = setup_matrix[last_task][job]

    completion_time = start_time + setup_time + processing_time[job]
    last_task = job

retornar completion_time
```

Essa função é usada para:

* calcular o tempo de cada máquina,
* avaliar o impacto de qualquer alteração na sequência (trocas, transferências).

---

## 4. Detalhamento da função `local_search`

A função principal de melhoria é:

```python
local_search(initial_sequences, config, processing_times, setup_matrix, release_dates)
```

Ela recebe:

* `initial_sequences`: um dicionário onde cada chave é o ID da máquina, e o valor é a lista de jobs alocados naquela máquina (solução inicial, gerada pelo FFD),
* `config`: contém, por exemplo, o número de máquinas,
* `processing_times`, `setup_matrix`, `release_dates`: dados da instância.

E devolve:

* a **melhor solução encontrada**,
* o **melhor makespan**,
* o **número de iterações** realizadas. 

### 4.1. Passo 1 – Inicialização

* Faz uma cópia da solução inicial.
* Calcula o tempo de cada máquina usando `calculate_sequence_time`.
* Define:

  * `current_solution` = solução atual;
  * `machine_times[m]` = tempo da máquina `m`;
  * `current_makespan` = maior valor em `machine_times`.

Em pseudo-código:

```text
current_solution = cópia da solução inicial
para cada máquina m:
    machine_times[m] = calculate_sequence_time(sequencia_da_maquina_m)

current_makespan = max(machine_times[m] para todas as máquinas m)
iteration = 0
```

### 4.2. Passo 2 – Loop principal da busca local

A função entra em um `while True`, repetindo até que nenhuma melhoria seja encontrada:

```text
enquanto (verdadeiro):
    iteration += 1
    best_neighbor_solution = nenhum
    best_neighbor_makespan = current_makespan

    identificar m_max (máquina com maior tempo) e m_min (máquina com menor tempo)
    obter seq_max = sequência em m_max
    obter seq_min = sequência em m_min

    considerar vizinhanças:
        1) Transferência m_max -> m_min
        2) Troca entre m_max e m_min
        3) Troca interna em m_max

    se best_neighbor_solution ainda é nenhum:
        parar (ótimo local)
    senão:
        atualizar current_solution, current_makespan e machine_times
        imprimir ganho da iteração
```

Vamos detalhar cada vizinhança.

---

### 4.3. Vizinhança 1 – Transferência da máquina mais carregada para a menos carregada

**Ideia:** mover **um job** da máquina `m_max` para o final da máquina `m_min`.

Passos:

1. Para cada posição `i` em `seq_max`:

   * remove o job naquela posição,
   * adiciona esse job ao final da sequência de `m_min`.

2. Recalcula o tempo de ambas:

   * `time_max` = tempo de `m_max` com a nova sequência,
   * `time_min` = tempo de `m_min` com a nova sequência.

3. O makespan da solução vizinha é:

   * se há só 2 máquinas → `max(time_max, time_min)`,
   * senão → `max(time_max, time_min, max_outros)`
     (`max_outros` é o maior tempo entre as máquinas que não mudaram).

4. Se esse novo makespan for **menor** que o melhor vizinho encontrado até agora,

   * guarda essa solução como `best_neighbor_solution`,
   * atualiza `best_neighbor_makespan`.

Pseudo-código:

```text
para cada posição i em seq_max:
    new_seq_max = seq_max sem o elemento na posição i
    task_to_move = job removido

    new_seq_min = seq_min + [task_to_move]

    time_max = calculate_sequence_time(new_seq_max)
    time_min = calculate_sequence_time(new_seq_min)

    neighbor_makespan = max(time_max, time_min, tempos_das_outras_máquinas)

    se neighbor_makespan < best_neighbor_makespan:
        best_neighbor_makespan = neighbor_makespan
        best_neighbor_solution = solução com new_seq_max e new_seq_min
```

---

### 4.4. Vizinhança 2 – Troca entre máquinas (`m_max` e `m_min`)

**Ideia:** trocar um job de `m_max` com um job de `m_min`.

Passos:

1. Para cada posição `i` em `seq_max`:
2. Para cada posição `j` em `seq_min`:

   * faz uma cópia das duas sequências,
   * troca `new_seq_max[i]` com `new_seq_min[j]`.
3. Recalcula `time_max` e `time_min`.
4. Calcula o makespan da solução vizinha.
5. Se for melhor que o atual melhor vizinho, atualiza.

Pseudo-código:

```text
para cada i em seq_max:
    para cada j em seq_min:
        new_seq_max = cópia de seq_max
        new_seq_min = cópia de seq_min

        trocar new_seq_max[i] com new_seq_min[j]

        time_max = calculate_sequence_time(new_seq_max)
        time_min = calculate_sequence_time(new_seq_min)

        neighbor_makespan = max(time_max, time_min, tempos_das_outras_máquinas)

        se neighbor_makespan < best_neighbor_makespan:
            atualizar best_neighbor_solution e best_neighbor_makespan
```

---

### 4.5. Vizinhança 3 – Troca interna na máquina mais carregada

**Ideia:** mexer na **ordem** dos jobs **dentro de `m_max`**, trocando posições.

Passos:

1. Se `seq_max` tiver pelo menos 2 jobs:
2. Para cada par de posições `i < j` em `seq_max`:

   * faz uma cópia da sequência,
   * troca os jobs nas posições `i` e `j`.
3. Recalcula apenas o tempo de `m_max` (as outras máquinas não mudam).
4. Calcula o makespan.
5. Se melhorar, atualiza o melhor vizinho.

Pseudo-código:

```text
se tamanho(seq_max) >= 2:
    para cada i:
        para cada j > i:
            new_seq_max = cópia de seq_max
            trocar new_seq_max[i] com new_seq_max[j]

            time_max = calculate_sequence_time(new_seq_max)
            neighbor_makespan = max(time_max, tempos_das_outras_máquinas)

            se neighbor_makespan < best_neighbor_makespan:
                atualizar best_neighbor_solution e best_neighbor_makespan
```

---

### 4.6. Atualização da solução ou parada

Depois de testar **todas** as vizinhanças:

* Se `best_neighbor_solution` ainda for `None`:

  * **não existe vizinho melhor** → a busca local para, e a solução atual é um **ótimo local**.
* Caso contrário:

  * substitui a solução atual pela melhor vizinha,
  * atualiza `current_makespan`,
  * recalcula `machine_times` para todas as máquinas,
  * imprime um resumo da iteração:

    * novo makespan,
    * ganho obtido.

Ao final, `local_search` devolve:

* `current_solution` (solução final),
* `current_makespan` (makespan final),
* `iteration` (quantidade de iterações realizadas). 

---

## 5. Cálculo do Limite Inferior (DDLB)

O código também implementa uma função:

```python
calcular_ddlb(config, processing_times, setup_matrix, release_dates)
```

Ela calcula um **limite inferior** (Data Dependent Lower Bound – DDLB) compatível com o mesmo modelo usado na função de tempo (sem teardown final, setups apenas entre jobs reais). 

A ideia resumida:

1. Para cada job `i`, calcula `δᵢ` = menor setup saindo de `i` para qualquer outro job.
2. Supõe que em uma solução com `m` máquinas, **apenas `n_jobs - m` jobs pagarão esse setup mínimo de saída**.
3. Com isso, constrói:

   * um **limite de carga de trabalho**:
     [
     \text{Limite_Carga} = \frac{\sum p_i + \text{Setup Total Mínimo}}{m}
     ]
   * um **limite de caminho crítico**:
     [
     \text{Limite_Caminho} = \max_i (r_i + p_i + δ_i)
     ]
4. O DDLB é:
   [
   \text{DDLB} = \max(\text{Limite_Carga}, \text{Limite_Caminho})
   ]

Na saída, o programa mostra, por exemplo:

* `Makespan Final (MS)`
* `Limite Inferior (DDLB)`
* `Razão MS/DDLB` (quanto mais próximo de 1, melhor)
* `Tempo de execução da busca local` em milissegundos. 

---

## 6. Como usar o código

### 6.1. Pré-requisitos

* **Python 3.8+** (recomendado 3.10 ou superior).
* Sistema operacional:

  * qualquer (Windows, Linux, macOS) para o `.py`;
  * o `.bat` é específico para **Windows**.

Bibliotecas usadas (todas da **biblioteca padrão**):

* `json`, `copy`, `time`, `argparse`.

Não é necessário instalar nada via `pip`. 

---

### 6.2. Estrutura sugerida de pastas

Um exemplo de organização do repositório:

```text
.
├── ls_pmsp.py           # Implementação da Busca Local
├── run_solver_LS.bat    # Script em lote (Windows) para rodar múltiplos cenários
├── resultados_LS.txt    # Exemplo de resultados obtidos com o solver
└── instancias/          # Pasta com instâncias extraídas de instancias.zip
    ├── HHHHHHH/
    │   ├── HHHHHHH_1.json
    │   ├── HHHHHHH_2.json
    │   └── ...
    ├── HHHHHHL/
    │   ├── HHHHHHL_1.json
    │   └── ...
    └── ...
```

O arquivo `resultados_LS.txt` contém logs de execução de vários cenários (instâncias diferentes), incluindo evolução do makespan nas iterações e as métricas finais. 

---

### 6.3. Obtendo e organizando as instâncias

1. Acesse o repositório:
   [https://github.com/Herysson/pmsp-instance-generator](https://github.com/Herysson/pmsp-instance-generator)
2. Baixe o arquivo `instancias.zip`.
3. Extraia o conteúdo para uma pasta chamada, por exemplo, `instancias/`.
4. Os arquivos `.json` gerados já possuem o formato esperado pela função `carregar_instancia_de_json` do `ls_pmsp.py`. 

---

### 6.4. Executando o solver para uma única instância

No terminal (cmd / PowerShell / bash), dentro da pasta onde está o arquivo `ls_pmsp.py`, execute:

```bash
python ls_pmsp.py caminho/para/instancia/HHHHHHH_1.json
```

Exemplos em Windows:

```bash
python ls_pmsp.py instancias\HHHHHHH\HHHHHHH_1.json
```

A saída terá duas fases principais:

1. **FASE 1 – Solução inicial com FFD**

   * Mostra a sequência inicial de jobs em cada máquina.
   * Mostra o tempo de cada máquina e o makespan inicial.

2. **FASE 2 – Busca Local**

   * Mostra, a cada iteração, quando encontra uma melhoria:

     * novo makespan,
     * ganho obtido na iteração.
   * Ao final, imprime:

     * solução final (jobs por máquina),
     * makespan final,
     * DDLB,
     * razão MS/DDLB,
     * melhoria em relação à solução inicial,
     * número de iterações,
     * tempo de execução da busca local em milissegundos. 

---

### 6.5. Executando múltiplos cenários com o arquivo `.bat`

O repositório inclui um script em lote:

* `run_solver_LS.bat`

Ele serve para:

* rodar o `ls_pmsp.py` automaticamente em **várias instâncias**,
* salvar toda a saída em um arquivo de log (por exemplo, `resultados_LS.txt`).

Para usar:

1. Abra o `run_solver_LS.bat` em um editor de texto.
2. Ajuste:

   * o caminho do Python (se necessário),
   * o caminho da pasta de instâncias,
   * o nome do arquivo de log (se quiser personalizar).
3. Execute:

   ```bash
   run_solver_LS.bat
   ```

Depois disso, consulte o arquivo de resultados (como `resultados_LS.txt`) para ver as métricas de todas as instâncias testadas. 

---

## 7. Determinismo e reprodutibilidade

A heurística de busca local em `ls_pmsp.py` é **determinística**:

* não usa sorteio dentro da `local_search`,
* a solução inicial (FFD) é montada ordenando os jobs por tempo de processamento, o que também é determinístico.

Isso significa que:

* Executando o código com a **mesma instância**, você obterá **sempre o mesmo resultado** (mesmas sequências, makespan, iterações, etc.), o que facilita comparação e validação científica. 

---

## 8. Resultados de exemplo

O arquivo `resultados_LS.txt` mostra, para diversas instâncias, por exemplo:

* o makespan inicial gerado pelo FFD,
* a sequência de melhorias encontradas pela busca local,
* o makespan final,
* o DDLB e a razão MS/DDLB,
* o tempo de execução. 

Isso pode ser utilizado:

* como referência para novos experimentos,
* para comparação com outros algoritmos (como GA, GRASP, etc.),
* para uso em trabalhos acadêmicos (análises de desempenho, gráficos, tabelas, etc.).

