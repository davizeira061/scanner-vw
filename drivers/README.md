# 🔌 Drivers para Cabo de Diagnóstico VAG-COM KKL 409.1

Para comunicar o software **OpenVAG** com as centrais de injeção (ECUs) do Grupo Volkswagen via Linha K (ISO 9141-2 / KW1281), o Windows precisa reconhecer o chip de conversão USB-Serial interno do cabo.

---

## 1. Cabo com Chip CH340 / CH341 (Mais comum no Brasil)
A grande maioria dos cabos KKL 409.1 azuis vendidos no Mercado Livre, Shopee e AliExpress utilizam o chip **WCH CH340 / CH341**.

### 🚀 Instalação Rápida em 1 Clique:
1. Abra esta pasta (`drivers/`).
2. Dê dois cliques no arquivo executável **[`CH341SER.EXE`](./CH341SER.EXE)**.
3. Se solicitado pelo Windows UAC, confirme **"Sim"**.
4. Na janela do instalador da WCH, clique no botão **"INSTALL"**.
5. Aguarde 5 a 10 segundos até surgir a mensagem: `Driver install success!`.
6. Conecte o cabo KKL na porta USB do computador.

### 🔍 Como Confirmar no Gerenciador de Dispositivos:
1. Pressione as teclas `Win + X` e selecione **Gerenciador de Dispositivos**.
2. Expanda a categoria **Portas (COM e LPT)**.
3. Deve constar: `USB-SERIAL CH340 (COM3)` (ou `COM1`, `COM2`, `COM4`, etc.).
4. O OpenVAG possui watchdog automático e detectará essa porta COM instantaneamente ao abrir.

---

## 2. Cabo com Chip FTDI (FT232RL / FT232BL)
Alguns cabos profissionais ou importados premium utilizam chips FTDI.
- Caso seu cabo seja FTDI, o Windows 10/11 costuma instalar o driver automaticamente via Windows Update.
- Se necessário instalar manualmente, baixe o **FTDI CDM Virtual COM Port Driver**:
  - [Site Oficial FTDI Chip VCP Drivers](https://ftdichip.com/drivers/vcp-drivers/)
  - **Ajuste de Latência recomendado para FTDI**:
    - Gerenciador de Dispositivos -> Portas (COM e LPT) -> Clique duplo na porta FTDI -> **Configurações de Porta** -> **Avançado**.
    - Altere o **Tempo de Latência (ms)** de `16` para `1` ou `2`. Isso acelera o handshake da Linha K.

---

## 3. Solução de Problemas Comuns
- **O cabo foi plugado mas não aparece em Portas (COM e LPT)**:
  - Tente outra porta USB do notebook (de preferência portas USB 2.0 nativas, evitando hubs não alimentados).
  - Execute o `CH341SER.EXE` novamente e clique em **UNINSTALL**, depois em **INSTALL**.
- **O OpenVAG não conecta à ECU**:
  - Verifique se a **chave de ignição está ligada** (luzes do painel acesas, sem dar a partida).
  - Confirme se o LED do cabo KKL acendeu ao plugar na tomada OBD2 do veículo (o pino 16 da OBD2 fornece +12V da bateria). Se o LED não acender, o fusível da tomada diagnóstica pode estar queimado.
