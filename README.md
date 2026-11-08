# 🚗 OpenVAG Desktop — Scanner Automotivo Profissional para a Linha Volkswagen (KWP1281 / Linha K)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt6-green?logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![Protocol](https://img.shields.io/badge/protocol-KWP1281%20(ISO%209141--2)-orange)]()
[![Parity](https://img.shields.io/badge/VCDS--Lite-100%25%20Paridade%20%2B%20Melhorias-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

O **OpenVAG** é um software de diagnóstico automotivo executável nativo desenvolvido para veículos do **Grupo Volkswagen** (Gol G2/G3/G4, Parati, Saveiro, Santana, Golf IV, Bora, Passat B5, Polo, Audi A3, Seat e Skoda) que utilizam centrais com comunicação via **Linha K (ISO 9141-2 / Protocolo KWP1281)** através do cabo diagnóstico acessível **VAG-COM 409.1 KKL (chips CH340, CH341 ou FTDI FT232RL)**.

Substitui e supera o tradicional **VCDS-Lite** trazendo uma interface moderna em **Dark Mode profissional**, osciloscópio integrado de 60 FPS, **Assistente Guiado de Calibração de TBI e Marcha Lenta**, **Datalogger Contínuo em CSV para testes de rodagem** e o inovador **Doutor de DTCs** com procedimentos práticos de teste com multímetro no chicote.

---

## 📑 Sumário
1. [Diferenciais e Recursos Principais](#-diferenciais-e-recursos-principais)
2. [Matriz de Paridade vs VCDS-Lite](#-matriz-de-paridade-vs-vcds-lite)
3. [Compatibilidade de Veículos e Centrais](#-compatibilidade-de-veículos-e-centrais)
4. [Hardware Necessário](#-hardware-necessário)
5. [Instalação e Configuração Inicial](#-instalação-e-configuração-inicial)
   - [Instalando o Driver do Cabo (1 Clique)](#1-instalando-o-driver-do-cabo-1-clique)
   - [Executando o Aplicativo Compilado (.exe)](#2-executando-o-aplicativo-compilado-exe-recomendado)
   - [Executando a Partir do Código Fonte (Python)](#3-executando-a-partir-do-código-fonte-desenvolvedores)
6. [Guia de Utilização Passo a Passo no Carro](#-guia-de-utilização-passo-a-passo-no-carro)
   - [1. Conexão Física no Veículo](#1-conexão-física-no-veículo)
   - [2. Conectando à Central do Motor (01 — Engine)](#2-conectando-à-central-do-motor-01--engine)
   - [3. Leitura e Limpeza de Avarias (Doutor de DTCs)](#3-leitura-e-limpeza-de-avarias-doutor-de-dtcs)
   - [4. Teste de Rodagem com Datalogger em Tempo Real](#4-teste-de-rodagem-com-datalogger-em-tempo-real-csv)
   - [5. Calibração de TBI e Marcha Lenta (Zero-Friction)](#5-calibração-de-tbi-e-marcha-lenta-zero-friction)
   - [6. Trava de Ponto de Ignição para Lâmpada Estroboscópica](#6-trava-de-ponto-de-ignição-para-lâmpada-estroboscópica)
   - [7. Teste Sequencial de Atuadores](#7-teste-sequencial-de-atuadores)
7. [Solução de Problemas Comuns (Troubleshooting)](#-solução-de-problemas-comuns-troubleshooting)
8. [Compilação Standalone com PyInstaller](#-compilação-standalone-com-pyinstaller)
9. [Suíte de Testes Automatizados](#-suíte-de-testes-automatizados)
10. [Licença](#-licença)

---

## ✨ Diferenciais e Recursos Principais

- 🔌 **Plug-and-Play com Watchdog Serial**: Monitoramento ativo a cada 800ms que detecta e seleciona automaticamente a porta COM (COM1 a COM256) no momento em que o cabo KKL é conectado à porta USB.
- 🚗 **Conexão Direta ao Motor (01 — Engine)**: Acesso instantâneo com um clique na tela inicial, sem menus confusos ou navegações desnecessárias.
- 🎯 **Assistente Auto-Adaptativo de TBI (Zero-Friction)**: Detecta o modelo de injeção física conectada e **apresenta exclusivamente o procedimento do veículo em teste**, eliminando opções irrelevantes para que mecânicos novatos não cometam erros.
- 🔴 **Datalogger em Tempo Real para Testes de Rodagem**: Permite dar voltas com o notebook a bordo gravando todos os parâmetros a cada ciclo da Linha K em arquivos `.csv` com timestamp de milissegundos, ideal para capturar engasgos intermitentes e quedas de sonda.
- 🩺 **Doutor de DTCs (Códigos de Falha Explicados)**: Não exibe apenas textos genéricos em inglês. Cruza códigos VAG e OBD2 apresentando sintomas mecânicos reais e **roteiro de testes elétricos no conector do sensor com multímetro (tensão, aterramento e continuidade)**.
- 🛡️ **Política Estrita de Dados Reais (Zero Ghost Data)**: Nenhuma falha fantasma, part number ou tela de calibração é populada antes de haver comunicação física real estabelecida via cabo.
- 📈 **Osciloscópio Gráfico Embutido**: Traçado fluido de telemetria integrado na tela principal (renderizado a 60 FPS com QPainter), sem necessitar de programas externos instáveis como o `VCScope.exe`.
- 🗃️ **Parser Automático de Labels VCDS (.LBL)**: Lê e decodifica as definições de unidades, fórmulas e tolerâncias originais dos arquivos de label da Ross-Tech.

---

## 📊 Matriz de Paridade vs VCDS-Lite

| Função | VCDS-Lite (Legado) | **OpenVAG Desktop** | Vantagem OpenVAG |
| :--- | :--- | :--- | :--- |
| **Identificação da ECU (01)** | Part number e componente | Exibição em destaque visual com Part Number, versão e WSC | Identificação mais limpa |
| **Códigos de Falha (02)** | Apenas código numérico e texto em inglês seco | Código VAG + OBD2 + **Sintomas mecânicos + Testes com multímetro no chicote** | ⭐ **Muito Superior** |
| **Limpeza de Falhas (05)** | Botão "Clear Codes - 05" | Botão integrado "Apagar Avarias" com confirmação de segurança | Total paridade |
| **Blocos de Medição (08)** | Blocos de 4 campos sem gráficos | Leitura com unidades, tolerâncias e **osciloscópio gráfico na mesma janela** | ⭐ **Muito Superior** |
| **Osciloscópio Gráfico** | Exige programa externo instável (`VCScope.exe`) | **Embutido diretamente na interface (PyQt6 QPainter fluido)** | ⭐ **Muito Superior** |
| **Datalogger de Rodagem** | Log manual simples | **Gravação contínua em CSV com timestamp milissegundo** | ⭐ **Muito Superior** |
| **Ajuste Básico (04)** | Sem guia na tela (exige memorização) | **Trava de ponto da 1AVP em 9.0° APMS e TBA guiado na tela** | ⭐ **Muito Superior** |
| **Teste de Atuadores (03)** | Disparo sequencial básico | Sequenciador: Bomba, bicos, atuador de marcha lenta e cânister | Total paridade |
| **Recodificar Módulo (07)** | Caixa para Soft Coding e WSC | Diálogo moderno com validação de formato | Total paridade |
| **Adaptação de Canais (10)** | Ajuste numérico sem dicas | Leitura/gravação em NVRAM com travas de segurança | Total paridade |
| **Acesso de Segurança / Login (11)** | Campo simples de 5 dígitos | Diálogo com validação de código de acesso (ex: 12233) | Total paridade |
| **Auto-Scan (Varredura Completa)** | Varredura por chassi via `AutoScan.txt` | Dropdown de chassis com barra de progresso em tempo real | ⭐ **Superior** |
| **Detecção do Cabo USB** | Fixo e restrito a COM1-COM4 | **Watchdog automático de portas COM1 a COM256 (CH340/CH341/FTDI)** | ⭐ **Muito Superior** |
| **Simulador de Bancada (Mock)** | Não possui | Modo Mock integrado simulando central Magneti Marelli 1AVP | Permite testes sem carro |

---

## 🚗 Compatibilidade de Veículos e Centrais

### Linhas Atendidas:
- **Volkswagen**: Gol (G2 "Bolinha", G3, G4, Special), Parati, Saveiro, Santana, Quantum, Golf IV, Bora, Passat B5, Polo Classic / Hatch, Fox (K-Line), Kombi 1.4 Flex, Logus / Pointer (injeções com linha K).
- **Audi**: A3 (8L), A4 (B5), A6 (C4/C5), TT (8N).
- **Seat**: Cordoba, Ibiza, Inca, Toledo.
- **Skoda**: Octavia I, Fabia I.

### Injeções Eletrônicas Testadas:
- **Bosch Motronic MP 9.0** (Gol G2 1.0 8v MI / Gol Special): Bloco 098 para alinhamento de batente de borboleta.
- **Magneti Marelli 1AVP / 1AVB** (Gol, Parati, Santana 1.6, 1.8 e 2.0 MI): Canal 00 para reset de adaptação e Grupo 001 em Ajuste Básico para travamento de avanço a 9.0° APMS.
- **Bosch Motronic ME 7.5 / ME 7.5.10 / ME 7.5.20 / ME 7.5.30** (Gol G3/G4 Flex, Golf IV, Polo): Bloco 060 para alinhamento de borboleta eletrônica (E-Gas).
- **Siemens / Magneti Marelli 4LV / 4MV / 4SV / 4BV**.

---

## 🔌 Hardware Necessário

1. **Cabo de Diagnóstico VAG-COM 409.1 KKL**:
   - Conector OBD-II de 16 pinos azul ou preto.
   - Comunica via pino 7 (Linha K) e pino 4/5 (Massa) e pino 16 (+12V da bateria).
   - Chipset USB-Serial compatível: **WCH CH340 / CH341** ou **FTDI FT232RL**.
2. **Computador / Notebook**:
   - Windows 10 ou Windows 11 (64 bits).
   - Porta USB disponível.
3. *(Opcional para veículos pré-1996)*: Adaptador OBD2 16 pinos para 2x2 pinos (preto e branco) para veículos VW mais antigos.

---

## 📥 Instalação e Configuração Inicial

### 1. Instalando o Driver do Cabo (1 Clique)
Na grande maioria dos cabos KKL azuis vendidos na internet, o chip interno é o **CH340 / CH341**.

1. Acesse a pasta [`drivers/`](./drivers/).
2. Execute o instalador oficial: **[`drivers/CH341SER.EXE`](./drivers/CH341SER.EXE)**.
3. Na janela do instalador, clique no botão **"INSTALL"**.
4. Aguarde a mensagem de confirmação: `Driver install success!`.
5. Conecte o cabo KKL na porta USB do notebook.
6. *(Para detalhes ou caso utilize cabo com chip FTDI, consulte o guia detalhado em [drivers/README.md](./drivers/README.md)).*

---

### 2. Executando o Aplicativo Compilado (.exe) *(Recomendado)*
Não é necessário ter Python instalado na máquina para rodar a versão compilada:

1. Baixe o pacote na aba [Releases](https://github.com/davizeira061/scanner-vw/releases) ou use a pasta `dist/OpenVAG`.
2. Dê dois cliques em **`dist/OpenVAG/OpenVAG.exe`** ou no atalho **`Iniciar_OpenVAG.bat`**.
3. O software abrirá imediatamente no padrão Dark Mode.

---

### 3. Executando a Partir do Código Fonte *(Desenvolvedores)*
Caso deseje rodar ou desenvolver diretamente em Python:

```powershell
# 1. Clone o repositório
git clone https://github.com/davizeira061/scanner-vw.git
cd scanner-vw

# 2. Crie e ative um ambiente virtual (recomendado)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o OpenVAG
python main.py

# (Opcional) Iniciar em modo simulação de bancada sem cabo:
python main.py --mock
```

---

## 🚗 Guia de Utilização Passo a Passo no Carro

### 1. Conexão Física no Veículo
1. Localize a tomada diagnóstica OBD2 no veículo:
   - **Gol G2 / G3 / G4**: Na caixa de fusíveis abaixo e à esquerda do volante (remover a tampa plástica).
   - **Golf IV / Bora**: No console central, abaixo dos controles de ar-condicionado.
   - **Santana / Polo Classic**: Abaixo do painel próximo à coluna de direção.
2. Plugue o conector de 16 pinos do cabo KKL na tomada OBD2 do veículo.
3. **Verifique o LED do cabo**: O LED vermelho/azul do cabo **deve acender**. Se não acender, o pino 16 da tomada não está recebendo 12V (verifique o fusível da buzina/acendedor de cigarros/diagnóstico).
4. Plugue a ponta USB no notebook.
5. **Gire a chave de ignição para a posição MARCHA (painel aceso, sem dar a partida)**.

---

### 2. Conectando à Central do Motor (01 — Engine)
1. Abra o **OpenVAG**.
2. No topo da tela, o OpenVAG exibirá: `Porta Serial: COM3 (ou correspondente) [Conectado]`.
3. Clique no botão de destaque: **`🚗 Conectar ao Módulo do Motor (01 - Engine)`**.
4. O OpenVAG iniciará a sincronização lenta (5 Baud Init) e estabelecerá a sessão KWP1281.
5. Na tela surgirá a identificação oficial da central:
   - **Part Number VAG** (Ex: `030906032AKK` para Gol 1.0 8v).
   - **Componente / Sistema** (Ex: `1.0l R4/2V MOTR 0001`).
   - **Codificação de Software (Soft Coding)** e **Código de Oficina (WSC)**.

---

### 3. Leitura e Limpeza de Avarias (Doutor de DTCs)
1. Clique no botão **`02 — Códigos de Falha (DTCs)`**.
2. O sistema fará a varredura da memória não-volátil da ECU.
3. Se houver falhas, cada código será detalhado com:
   - **Código VAG e OBD2** (Ex: `00515 / P0340 — Sensor Hall (G40)`).
   - **Status**: Intermitente ou Permanente.
   - **Sintomas Clínicos**: Dificuldade na partida, corte em 4500 RPM, motor engasgando.
   - **Testes Práticos com Multímetro no Chicote**: Tensões de alimentação (5V/12V), pino de sinal e testes de continuidade no chicote até a central.
4. Para apagar as avarias após o reparo, clique no botão **`05 — Limpar Memória de Falhas`** e confirme o aviso de segurança.

---

### 4. Teste de Rodagem com Datalogger em Tempo Real (CSV)
Para identificar falhas que só ocorrem com o carro em movimento (falhas de aceleração, engasgos em retomada, aquecimento intermitente):

1. Clique em **`08 — Blocos de Medição (Live Data)`**.
2. Digite o canal desejado (ex: Grupo `001` para RPM, Temperatura e Sonda Lambda) e clique em **`Ler Bloco`**.
3. O osciloscópio gráfico exibirá os valores ao vivo.
4. Clique no botão de destaque: **`🔴 Gravar Teste de Rodagem (CSV)`**.
5. O botão mudará para **`⏹️ Parar Gravação`** e o sistema salvará cada ciclo de leitura com data, hora, milissegundos e os 4 valores em um arquivo `.csv` na pasta `logs/`.
6. Realize o percurso de teste com o veículo.
7. Ao retornar, clique em **`⏹️ Parar Gravação`**. O arquivo gerado (ex: `logs/teste_rodagem_2026-11-07_214500.csv`) estará pronto para ser aberto diretamente no Excel para plotagem de gráficos comparativos.

---

### 5. Calibração de TBI e Marcha Lenta (Zero-Friction)
O OpenVAG identifica sua injeção e apresenta apenas o procedimento correto:

#### Caso A: Gol G2 1.0 8v MI (Bosch Motronic MP 9.0)
> **Condições**: Motor frio ou aquecido, ignição ligada, motor desligado, bateria > 12V, cabo do acelerador sem tensão.
1. Na tela principal, clique em **`🎯 Calibração de TBI e Marcha Lenta`**.
2. O sistema selecionará automaticamente o procedimento **Grupo 098**.
3. Clique em **`Iniciar Ajuste Básico (Grupo 098)`**.
4. O corpo de borboleta emitirá um zumbido característico movendo o motor de passo do batente mínimo ao máximo.
5. Observe o Campo 4: mudará de `ADP. RUN` para `ADP. OK` (ou `I.O.`).

#### Caso B: Gol / Santana 1.6 / 1.8 / 2.0 (Magneti Marelli 1AVP / 1AVB)
> Na 1AVP o corpo é mecânico a cabo com motor de passo IAC. O procedimento consiste no reset dos parâmetros autoadaptativos em NVRAM.
1. O assistente selecionará automaticamente a aba **Reset 1AVP (Canal 00)**.
2. Clique no botão **`Executar Reset de Adaptações (Canal 00)`**.
3. Siga o cronômetro visual guiado na tela:
   - Desligue a chave e aguarde 15 segundos.
   - Ligue a chave sem dar partida e aguarde 30 segundos para a central mapear o batente do atuador IAC.
   - Dê a partida sem acelerar e deixe o motor atingir 85°C até o acionamento do eletroventilador.

---

### 6. Trava de Ponto de Ignição para Lâmpada Estroboscópica
Para acertar o distribuidor de ignição em motores AP MI (Magneti Marelli 1AVP):
1. Ligue o motor e deixe aquecer até 85°C.
2. Clique em **`04 — Ajuste Básico (Basic Settings)`**.
3. Selecione o **Grupo 001** e clique em **`Ativar Ajuste Básico`**.
4. A injeção eletrônica travará o avanço estático em **9.0° APMS** (ou 12.0° para modelos a álcool) e desligará a correção dinâmica.
5. Aponte a pistola de ponto no volante do motor / polia e gire o distribuidor até alinhar a marca de ponto de fábrica.
6. Clique em **`Sair do Ajuste Básico`** para destravar o mapa de avanço.

---

### 7. Teste Sequencial de Atuadores
Para testar os componentes no cofre do motor sem ligar o carro:
1. Chave ligada na ignição, motor desligado.
2. Clique em **`03 — Teste de Atuadores (Output Tests)`**.
3. Clique em **`Iniciar Sequência de Testes`**.
4. O sistema acionará um por um:
   - **Bomba de Combustível e Relé Principal** (ouvir o zumbido no tanque).
   - **Bicos Injetores** (ouvir o estalo/clique dos solenoides).
   - **Válvula de Marcha Lenta (IAC)**.
   - **Válvula de Purga do Cânister (EVAP)**.

---

## 🛠️ Solução de Problemas Comuns (Troubleshooting)

### "Sem Resposta da Central / Falha no Handshake 5 Baud"
1. **Chave de ignição**: Certifique-se de que a ignição está realmente ligada.
2. **Alimentação da Tomada OBD2**: Meça com um multímetro a tensão entre o **Pino 16 (+12V)** e o **Pino 4/5 (Massa)** da tomada do carro. Deve constar > 12.0V.
3. **Rádio Não-Original (Problema Clássico K-Line)**: Muitos instaladores de som automotivo ligam o fio da Linha K do chicote original do rádio no pós-chave do rádio novo, curto-circuitando a linha K em 12V. Se o scanner não comunicar, desconecte o plugue traseiro do aparelho de som e tente novamente.
4. **Porta COM**: Confirme no Gerenciador de Dispositivos do Windows se o cabo está reconhecido em `Portas (COM e LPT)`.

### "O Módulo 17 (Painel de Instrumentos) não responde no Gol G2"
- **Comportamento 100% normal**: No Gol G2 (mesmo os equipados com sensor de velocidade eletrônico VSS na caixa e painel com conta-giros), o painel de instrumentos é puramente analógico e elétrico por pulsos de frequência e cablagem direta. Ele **não possui processador digital interligado à Linha K**. Portanto, o endereço `17 - Instruments` nunca responderá. No Gol G2, todo o diagnóstico digital é concentrado no endereço **`01 - Motor`**.

---

## 📦 Compilação Standalone com PyInstaller

Para gerar uma nova versão compilada em pasta standalone (`dist/OpenVAG/OpenVAG.exe`):

1. Basta dar dois cliques no script:
   ```cmd
   compilar_executavel.bat
   ```
2. Ou via terminal:
   ```powershell
   pyinstaller --clean --noconfirm OpenVAG.spec
   ```
3. O executável standalone será gerado em `dist\OpenVAG\OpenVAG.exe`.

---

## 🧪 Suíte de Testes Automatizados

O projeto conta com testes unitários cobrindo o parser de frames KW1281, cálculo de checksum de blocos de medição, decodificação de DTCs e autodetecção de ECUs:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para obter mais informações.

Desenvolvido para entusiastas, preparadores e mecânicos que valorizam a confiabilidade e o diagnóstico preciso da mecânica Volkswagen no Brasil. 🇧🇷🚗
