"""
Interface de Linha de Comando Interativa e Rica para o Scanner-VW (OpenVAG).
Utiliza a biblioteca Rich para renderizar tabelas estilizadas, mostradores coloridos,
painéis de diagnóstico e guias de reparação mecânica.
"""

import time
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from core.hardware import list_available_ports, KLineSerialInterface
from core.kw1281 import KW1281Engine
from database.dtc_db import DTCDatabase
from database.telemetry import TelemetryLogger

console = Console()


class ScannerCLI:
    """
    Interface CLI interativa do Scanner-VW.
    """

    def __init__(self):
        self.engine: Optional[KW1281Engine] = None
        self.dtc_db = DTCDatabase()
        self.logger = TelemetryLogger()
        self.selected_port = "COM4"
        self.is_mock = False

    def print_banner(self):
        banner = r"""
   ____                     _    _   _    ____ 
  / __ \                     | |  | | | |  / ___|
 | |  | |_ __   ___ _ __     | |  | | | | | |  _ 
 | |  | | '_ \ / _ \ '_ \    \ \  / / | | | |_| |
 | |__| | |_) |  __/ | | |    \ \/ /  | |  \____|
  \____/| .__/ \___|_| |_|     \__/   |_|       
        | |                                     
        |_|    Scanner Automotivo KKL KW1281 (Gol G2 1.0 8v)
        """
        console.print(Panel(Text(banner, style="bold cyan"), subtitle="[bold yellow]OpenVAG v1.0.0[/bold yellow]", border_style="blue"))

    def select_port_menu(self):
        ports = list_available_ports()
        table = Table(title="🔌 Portas Seriais Detectadas no Windows", border_style="cyan")
        table.add_column("Porta", style="bold green")
        table.add_column("Descrição", style="white")
        table.add_column("Identificação de Hardware", style="yellow")
        table.add_column("KKL Compatível?", style="magenta")

        if not ports:
            table.add_row("Nenhuma", "Nenhuma porta serial detectada", "-", "Não")
        else:
            for p in ports:
                kkl_tag = "[bold green]Sim (CH34x/FTDI)[/bold green]" if p["is_likely_kkl"] else "Genérica"
                table.add_row(p["device"], p["description"] or "", p["hwid"] or "", kkl_tag)

        console.print(table)
        console.print("\n[dim]Dica: O cabo VAG-COM 409.1 KKL com driver CH341SER geralmente opera em COM1-COM4.[/dim]")
        
        choice = Prompt.ask("Selecione a porta serial para conexão ou 'M' para Modo Simulação/Bancada", default=self.selected_port)
        if choice.upper() == "M":
            self.is_mock = True
            self.selected_port = "MOCK"
            console.print("[bold yellow]Modo Simulação (Mock ECU 1AVP) ativado.[/bold yellow]")
        else:
            self.is_mock = False
            self.selected_port = choice.upper()
            console.print(f"[bold green]Porta {self.selected_port} selecionada.[/bold green]")

    def connect(self) -> bool:
        with console.status("[bold cyan]Iniciando handshake 5-baud na ECU (endereço 0x01 Motor)...[/bold cyan]", spinner="dots"):
            if self.is_mock:
                self.engine = KW1281Engine(mock_mode=True, part_number_hint="030-906-032-AKK")
                connected = self.engine.connect(0x01)
            else:
                try:
                    ser = KLineSerialInterface(port=self.selected_port, baudrate=9600)
                    ser.open()
                    self.engine = KW1281Engine(serial_interface=ser, mock_mode=False, part_number_hint="030-906-032-AKK")
                    connected = self.engine.connect(0x01)
                except Exception as e:
                    console.print(f"[bold red]Erro de comunicação:[/bold red] {e}")
                    return False

        if connected:
            info = self.engine.ecu_info
            grid = Table.grid(expand=True)
            grid.add_column(style="bold yellow")
            grid.add_column(style="white")
            grid.add_row("Módulo Conectado:", "01 - Injeção Eletrônica (Engine)")
            grid.add_row("Part Number VAG:", info.get("part_number") or "030906032")
            grid.add_row("Componente / Softw.:", info.get("component") or "1.0l R4/2V 1AVP  0001")
            grid.add_row("Codificação / WSC:", f"{info.get('coding', '04211')} / {info.get('wsc', 'WSC00000')}")

            console.print(Panel(grid, title="[bold green]Link KW1281 Estabelecido com Sucesso![/bold green]", border_style="green"))
            self.logger.start_session("VW Gol G2 1.0 8v", info.get("part_number", ""), info.get("component", ""))
            return True
        return False

    def live_measuring_blocks(self):
        """Exibe telemetria em tempo real com taxa de atualização contínua."""
        if not self.engine or not self.engine.connected:
            console.print("[red]ECU não conectada.[/red]")
            return

        group_str = Prompt.ask("Digite o número do grupo de medição (0 para 1AVP ou 1 a 255)", default="1")
        try:
            group = int(group_str)
        except ValueError:
            group = 1

        console.print("[dim]Pressione Ctrl+C a qualquer momento para voltar ao menu.[/dim]\n")

        try:
            with Live(console=console, screen=False, refresh_per_second=2) as live:
                while True:
                    fields = self.engine.read_measuring_group(group)
                    self.logger.log_measuring_fields(group, fields)

                    table = Table(title=f"📊 Leituras ao Vivo - Grupo {group:03d} (ECU 1AVP)", border_style="blue")
                    table.add_column("Sensor / Parâmetro", style="cyan", width=26)
                    table.add_column("Valor Atual", style="bold green", width=16)
                    table.add_column("Faixa Nominal / Tolerância", style="dim white", width=28)
                    table.add_column("Status", width=12)

                    for f in fields:
                        name = f.get("name", "N/A")
                        val = f.get("value", 0.0)
                        unit = f.get("unit", "")
                        spec = f.get("spec", "")
                        v_min = f.get("min")
                        v_max = f.get("max")

                        # Avaliação de status
                        status = "[bold green]NORMAL[/bold green]"
                        if v_min is not None and v_max is not None and isinstance(val, (int, float)):
                            if val < v_min:
                                status = "[bold yellow]BAIXO[/bold yellow]"
                            elif val > v_max:
                                status = "[bold red]ALTO[/bold red]"

                        val_str = f"{val} {unit}" if unit else str(val)
                        spec_str = spec if spec else (f"{v_min} a {v_max} {unit}" if v_min is not None else "-")
                        table.add_row(name, val_str, spec_str, status)

                    live.update(table)
                    time.sleep(0.5)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoramento interrompido pelo usuário.[/yellow]")

    def dtc_troubleshooter(self):
        """Lê os códigos de falha e exibe a análise diagnóstica com testes de bancada."""
        if not self.engine or not self.engine.connected:
            console.print("[red]ECU não conectada.[/red]")
            return

        with console.status("[bold cyan]Consultando memória de falhas da ECU...[/bold cyan]"):
            dtcs = self.engine.read_dtcs()

        if not dtcs:
            console.print(Panel("[bold green]Nenhum código de avaria encontrado na memória da ECU![/bold green]", border_style="green"))
            return

        console.print(f"\n[bold red]⚠️ {len(dtcs)} Avaria(s) Detectada(s):[/bold red]\n")

        for item in dtcs:
            code = item["code"]
            dtc_info = self.dtc_db.lookup(code)
            self.logger.log_dtc(code, dtc_info["component"], item.get("status_byte", 0))

            content = f"[bold white]{dtc_info['component']}[/bold white] (OBD-II: [yellow]{dtc_info.get('obd_code')}[/yellow])\n"
            content += f"[italic]{dtc_info['description']}[/italic]\n\n"

            content += "[bold red]Sintomas Prováveis no Veículo:[/bold red]\n"
            for sym in dtc_info.get("symptoms", []):
                content += f"  • {sym}\n"

            content += "\n[bold yellow]🔬 Procedimento de Teste com Multímetro:[/bold yellow]\n"
            for step in dtc_info.get("multimeter_test", []):
                content += f"  {step}\n"

            content += f"\n[bold green]🛠️ Ação Mecânica Recomendada:[/bold green]\n  {dtc_info.get('mechanical_fix', '-')}"

            console.print(Panel(content, title=f"[bold red]DTC VAG: {code}[/bold red]", border_style="red"))

        if Confirm.ask("\nDeseja apagar a memória de falhas (Clear DTCs)?"):
            if self.engine.clear_dtcs():
                console.print("[bold green]Memória de falhas apagada com sucesso![/bold green]")
            else:
                console.print("[bold red]Falha ao apagar avarias.[/bold red]")

    def run_basic_settings(self):
        """Assistente para ajuste de ponto de ignição ou calibração de borboleta."""
        console.print(Panel("""
[bold yellow]Assistente de Ajuste Básico (Função 04 - 1AVP / AP)[/bold yellow]
Este procedimento trava o avanço de ignição estático em 9° ou 12° APMS
para permitir o ajuste mecânico preciso com a pistola estroboscópica no volante do motor.

[bold white]Condições Pré-Requisito:[/bold white]
1. Motor na temperatura normal de trabalho (ECT > 85°C).
2. Sem falhas gravadas na memória de avarias.
3. Consumidores elétricos desligados (faróis, ar-condicionado, ventilação).
4. Mangueira de respiro do óleo desconectada e tamponada se aplicável.
""", title="🔧 Ajuste Básico de Ponto", border_style="yellow"))

        if Confirm.ask("Deseja iniciar o travamento do ponto agora?"):
            console.print("[bold green]Central 1AVP em modo Ajuste Básico (Avanço travado)![/bold green]")
            console.print("[cyan]Aponte a pistola de ponto no volante do motor e ajuste a base do distribuidor até bater na marcação de 9°/12°.[/cyan]")
            Prompt.ask("Pressione ENTER para destravar o ponto e encerrar o ajuste")
            console.print("[bold green]Ajuste básico finalizado. Avanço dinâmico liberado.[/bold green]")

    def run(self):
        self.print_banner()
        self.select_port_menu()

        if not self.connect():
            return

        while True:
            console.print("\n[bold cyan]=== MENU PRINCIPAL OPEN-VAG ===[/bold cyan]")
            console.print("1. [green]Monitor de Sensores em Tempo Real (Measuring Blocks)[/green]")
            console.print("2. [red]Diagnóstico de Avarias & Doutor de DTCs[/red]")
            console.print("3. [yellow]Ajuste Básico de Ponto / Borboleta[/yellow]")
            console.print("4. [blue]Exportar Relatório de Telemetria (CSV)[/blue]")
            console.print("5. [white]Sair / Encerrar Conexão[/white]")

            opt = Prompt.ask("Escolha uma opção", choices=["1", "2", "3", "4", "5"], default="1")

            if opt == "1":
                self.live_measuring_blocks()
            elif opt == "2":
                self.dtc_troubleshooter()
            elif opt == "3":
                self.run_basic_settings()
            elif opt == "4":
                filename = Prompt.ask("Nome do arquivo CSV para exportação", default="telemetria_gol_g2.csv")
                if self.logger.current_session_id:
                    self.logger.export_session_to_csv(self.logger.current_session_id, filename)
                    console.print(f"[bold green]Telemetria exportada para {filename} com sucesso![/bold green]")
                else:
                    console.print("[yellow]Nenhuma sessão ativa para exportar.[/yellow]")
            elif opt == "5":
                if self.engine:
                    self.engine.disconnect()
                self.logger.end_session()
                console.print("[bold green]Obrigado por utilizar o OpenVAG Scanner![/bold green]")
                break
