@echo off
chcp 65001 > nul
echo ========================================================
echo       OpenVAG — Compilador Automático Standalone
echo ========================================================
echo.
echo [1/3] Verificando dependências Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo [2/3] Compilando executavel com PyInstaller...
pyinstaller --clean --noconfirm OpenVAG.spec
if errorlevel 1 (
    echo [ERRO] Falha na compilacao com o PyInstaller.
    pause
    exit /b 1
)

echo.
echo [3/3] Compilacao concluida com sucesso!
echo Executavel pronto em: dist\OpenVAG\OpenVAG.exe
echo.
pause
