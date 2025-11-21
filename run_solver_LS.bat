@echo off
setlocal

REM ============================================================================
REM == Script para executar o solver em todas as instâncias JSON geradas      ==
REM ============================================================================

echo.
echo INICIANDO EXECUCAO EM LOTE DO SOLVER...
echo.

REM --- Configurações de Caminho ---
REM A variável especial %~dp0 garante que os caminhos sempre funcionem,
REM não importa de onde o script seja executado.
set "ROOT_FOLDER=%~dp0"
set "INSTANCIAS_FOLDER=%ROOT_FOLDER%instancias"
set "SOLVER_SCRIPT=%ROOT_FOLDER%ls_pmsp.py"
set "RESULTS_FILE=%ROOT_FOLDER%resultados_LS.txt"

REM --- Verificações Iniciais ---
REM Verifica se o script do solver existe.
if not exist "%SOLVER_SCRIPT%" (
    echo ERRO FATAL: O script do solver '%SOLVER_SCRIPT%' nao foi encontrado.
    pause
    exit /b
)
REM Verifica se a pasta de instâncias existe.
if not exist "%INSTANCIAS_FOLDER%" (
    echo ERRO FATAL: A pasta de instancias '%INSTANCIAS_FOLDER%' nao foi encontrada.
    echo Por favor, execute o 'run_generator.py' primeiro.
    pause
    exit /b
)

REM --- Preparação do Arquivo de Resultados ---
REM Apaga o arquivo de resultados antigo para começar uma nova execução limpa.
if exist "%RESULTS_FILE%" (
    del "%RESULTS_FILE%"
)
echo === Log de Execucao iniciado em %date% %time% === > "%RESULTS_FILE%"
echo. >> "%RESULTS_FILE%"

echo Buscando e processando todos os arquivos .json em '%INSTANCIAS_FOLDER%'...
echo Os resultados serao salvos em '%RESULTS_FILE%'.
echo.

REM --- Loop Principal de Execução ---
REM O loop 'for /r' busca recursivamente por todos os arquivos *.json
REM a partir da pasta de instâncias. É simples e eficiente.
for /r "%INSTANCIAS_FOLDER%" %%f in (*.json) do (
    echo Processando instancia: "%%~nxf"
    
    REM Executa o script Python para o arquivo encontrado.
    REM A saida normal (stdout) e a saida de erro (stderr) sao anexadas (>>) ao arquivo de resultados.
    py "%SOLVER_SCRIPT%" "%%f" >> "%RESULTS_FILE%" 2>>&1
)

echo. >> "%RESULTS_FILE%"
echo === Execucao concluida em %date% %time% === >> "%RESULTS_FILE%"

echo.
echo ==========================================================
echo      EXECUCAO EM LOTE CONCLUIDA!
echo      Resultados salvos em '%RESULTS_FILE%'.
echo ==========================================================
echo.
pause
endlocal