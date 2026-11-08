"""
Ponto de Entrada Principal do Scanner-VW (OpenVAG).
Inicia a Interface Gráfica Desktop Nativa (padrão), o Terminal Interativo (CLI) ou Dashboard Web.
"""

import sys
import argparse
import time
from rich.console import Console

from core.kw1281 import KW1281Engine
from core.hardware import KLineSerialInterface
from ui.desktop_app import OpenVAGMainWindow, run_desktop_app

console = Console()


def main():
    parser = argparse.ArgumentParser(description="OpenVAG — Scanner Automotivo KW1281 para Cabo KKL (Gol G2 / VW AP)")
    parser.add_argument("--cli", action="store_true", help="Inicia a interface de terminal interativo (Rich CLI)")
    parser.add_argument("--web", action="store_true", help="Inicia o Dashboard Web com telemetria para navegadores e smartphones")
    parser.add_argument("--mock", action="store_true", help="Executa em modo simulação de bancada (Mock ECU 1AVP)")
    parser.add_argument("--port", type=str, default=None, help="Porta serial do cabo KKL (se omitido, detecta automaticamente)")
    parser.add_argument("--web-port", type=int, default=8080, help="Porta do servidor Web (padrão: 8080)")

    args = parser.parse_args()

    if args.web:
        from ui.web_server import start_web_server
        console.print("[bold cyan]Iniciando OpenVAG em Modo Web Dashboard...[/bold cyan]")
        if args.mock:
            console.print("[yellow]Conectando à ECU Simulada 1AVP (Gol G2 1.0 8v)...[/yellow]")
            engine = KW1281Engine(mock_mode=True, part_number_hint="030-906-032-AKK")
        else:
            console.print(f"[green]Abrindo porta serial {args.port}...[/green]")
            ser = KLineSerialInterface(port=args.port)
            ser.open()
            engine = KW1281Engine(serial_interface=ser, mock_mode=False, part_number_hint="030-906-032-AKK")

        engine.connect(0x01)
        server = start_web_server(engine, port=args.web_port)

        url = f"http://localhost:{args.web_port}"
        console.print(f"\n[bold green]✓ Dashboard Web Rodando em:[/bold green] [bold underline cyan]{url}[/bold underline cyan]")
        console.print(f"[dim]Acesse pelo celular na mesma rede Wi-Fi/Hotspot: http://<IP_DO_NOTEBOOK>:{args.web_port}[/dim]\n")
        console.print("[dim]Pressione Ctrl+C para encerrar o servidor.[/dim]")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Servidor Web encerrado.[/yellow]")
            engine.disconnect()
            server.shutdown()

    elif args.cli:
        from ui.cli import ScannerCLI
        cli = ScannerCLI()
        if args.mock:
            cli.is_mock = True
            cli.selected_port = "MOCK"
        elif args.port:
            cli.selected_port = args.port
        cli.run()

    else:
        # Padrão: Interface Desktop Nativa (PyQt6)
        from PyQt6.QtWidgets import QApplication
        from ui.desktop_app import OpenVAGMainWindow

        app = QApplication(sys.argv)
        window = OpenVAGMainWindow()

        if args.mock:
            idx = window.port_combo.findData("MOCK")
            if idx >= 0:
                window.port_combo.setCurrentIndex(idx)
        elif args.port:
            idx = window.port_combo.findData(args.port)
            if idx >= 0:
                window.port_combo.setCurrentIndex(idx)

        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
