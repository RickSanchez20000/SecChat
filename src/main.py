import socket
import threading
import sys
import time
from datetime import datetime
import flet as ft

try:
    from cryptography.fernet import Fernet
except ImportError:
    print("[-] Errore: libreria 'cryptography' mancante.")
    sys.exit(1)


def main(page: ft.Page):
    page.title = "SecChat P2P Secure Chat"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 700
    page.padding = 20
    page.bgcolor = "#121212"

    state = {
        "socket_connessione": None,
        "cipher": None,
        "username": "User",
        "partner_name": "Partner",
        "stop_broadcast": False,
    }

    def mostra_menu(e=None):
        page.clean()
        state["stop_broadcast"] = True
        if state["socket_connessione"]:
            try:
                state["socket_connessione"].close()
            except:
                pass
            state["socket_connessione"] = None

        txt_username = ft.TextField(
            label="Il tuo Username", value=state["username"], width=380, height=50
        )

        def go_host(evt):
            state["username"] = txt_username.value.strip() or "User"
            mostra_host()

        def go_client(evt):
            state["username"] = txt_username.value.strip() or "Ghost"
            mostra_client()

        page.add(
            ft.Column(
                [
                    ft.Text("SecChat", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=20),
                    txt_username,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Crea una Stanza (Host)",
                        width=380,
                        height=45,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_700),
                        on_click=go_host,
                    ),
                    ft.ElevatedButton(
                        "Unisciti a una Stanza (Client)",
                        width=380,
                        height=45,
                        on_click=go_client,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        )

    def mostra_host():
        page.clean()
        txt_stanza = ft.TextField(
            label="Nome della Stanza", hint_text="Es. Stanza Segreta", width=380
        )
        status_host = ft.ListView(expand=True, spacing=5, padding=10)

        def log_status_host(testo):
            status_host.controls.append(ft.Text(testo, size=12, color=ft.Colors.WHITE70))
            page.update()

        def broadcast_room(title):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg = f"ROOM:{title}".encode("utf-8")
            while not state["stop_broadcast"]:
                try:
                    s.sendto(msg, ("255.255.255.255", 9998))
                except:
                    pass
                time.sleep(1.5)
            s.close()

        def logica_host(room_title):
            key = Fernet.generate_key()
            state["cipher"] = Fernet(key)
            log_status_host(f"[*] Chiave E2E generata: {key.decode()}")
            state["stop_broadcast"] = False
            threading.Thread(target=broadcast_room, args=(room_title,), daemon=True).start()

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", 9999))
            server.listen(1)
            log_status_host(f"[*] Stanza '{room_title}' attiva. In attesa...")

            while not state["stop_broadcast"]:
                try:
                    conn, addr = server.accept()
                    dati_bussata = conn.recv(1024).decode("utf-8")
                    if dati_bussata.startswith("USER:"):
                        state["partner_name"] = dati_bussata[5:]
                        log_status_host(f"[richiesta] '{state['partner_name']}' ({addr[0]}) connesso.")
                        conn.send(f"OK:{state['username']}".encode("utf-8"))
                        state["socket_connessione"] = conn
                        state["stop_broadcast"] = True
                        log_status_host(f"[+] Accesso consentito!")
                        time.sleep(1)
                        mostra_chat()
                        break
                except:
                    break
            server.close()

        def avvia_server_click(e):
            room_title = txt_stanza.value.strip() or f"Stanza di {state['username']}"
            threading.Thread(target=logica_host, args=(room_title,), daemon=True).start()

        page.add(
            ft.Column(
                [
                    ft.Text("CREA STANZA", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    txt_stanza,
                    ft.Container(
                        content=status_host,
                        bgcolor="#1E1E1E",
                        border_radius=5,
                        height=200,
                        width=380,
                        expand=True,
                    ),
                    ft.ElevatedButton("Avvia Stanza", width=380, on_click=avvia_server_click),
                    ft.OutlinedButton("Indietro", width=200, on_click=mostra_menu),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )

    def mostra_client():
        page.clean()
        status_client = ft.ListView(expand=True, spacing=5, padding=10)
        txt_ip = ft.TextField(label="IP Stanza", hint_text="192.168.1.X", width=380)
        txt_key = ft.TextField(label="Chiave Segreta E2E", hint_text="Incolla chiave...", width=380)

        def log_status_client(testo):
            status_client.controls.append(ft.Text(testo, size=12, color=ft.Colors.WHITE70))
            page.update()

        def esegui_scansione():
            log_status_client("[*] Scansione rete locale...")
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("", 9998))
            except:
                return
            s.settimeout(3.0)
            start = time.time()
            trovate = {}
            while time.time() - start < 3:
                try:
                    data, addr = s.recvfrom(1024)
                    text = data.decode("utf-8")
                    if text.startswith("ROOM:"):
                        trovate[addr[0]] = text[5:]
                except:
                    pass
            s.close()
            if trovate:
                for ip, nome in trovate.items():
                    log_status_client(f"Trovata: {nome} ({ip})")
                    txt_ip.value = ip
            else:
                log_status_client("Nessuna stanza trovata.")
            page.update()

        def scansiona_click(e):
            threading.Thread(target=esegui_scansione, daemon=True).start()

        def logica_client(ip, chiave):
            try:
                state["cipher"] = Fernet(chiave.encode("utf-8"))
            except:
                log_status_client("[-] Chiave non valida.")
                return

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client.connect((ip, 9999))
                client.send(f"USER:{state['username']}".encode("utf-8"))
                risposta = client.recv(1024).decode("utf-8")
                if risposta.startswith("OK:"):
                    state["partner_name"] = risposta[3:]
                    state["socket_connessione"] = client
                    mostra_chat()
                else:
                    client.close()
                    log_status_client("[-] Accesso rifiutato.")
            except:
                log_status_client("[-] Errore di connessione.")

        def connettiti_click(e):
            ip = txt_ip.value.strip() or "127.0.0.1"
            chiave = txt_key.value.strip()
            threading.Thread(target=logica_client, args=(ip, chiave), daemon=True).start()

        page.add(
            ft.Column(
                [
                    ft.Text("UNISCITI A UNA STANZA", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(
                        content=status_client,
                        bgcolor="#1E1E1E",
                        border_radius=5,
                        height=150,
                        width=380,
                    ),
                    ft.ElevatedButton("Scansiona Wi-Fi", width=380, on_click=scansiona_click),
                    txt_ip,
                    txt_key,
                    ft.ElevatedButton(
                        "Connettiti",
                        width=380,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700),
                        on_click=connettiti_click,
                    ),
                    ft.OutlinedButton("Indietro", width=200, on_click=mostra_menu),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )

    def mostra_chat():
        page.clean()
        chat_box = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)
        txt_msg = ft.TextField(hint_text="Scrivi un messaggio...", expand=True, height=45)

        def scrivi_in_chat(mittente, testo):
            orario = datetime.now().strftime("%H:%M")
            chat_box.controls.append(ft.Text(f"[{orario}] {mittente}: {testo}", size=14, color=ft.Colors.WHITE))
            page.update()

        def invia_messaggio(e):
            testo = txt_msg.value.strip()
            if testo and state["socket_connessione"]:
                try:
                    state["socket_connessione"].send(state["cipher"].encrypt(testo.encode("utf-8")))
                    scrivi_in_chat("Tu", testo)
                    txt_msg.value = ""
                    page.update()
                except:
                    scrivi_in_chat("Sistema", "Errore di invio.")

        txt_msg.on_submit = invia_messaggio

        def ricevi_messaggi_loop():
            while True:
                try:
                    encrypted_msg = state["socket_connessione"].recv(1024)
                    if not encrypted_msg:
                        scrivi_in_chat("Sistema", f"{state['partner_name']} ha chiuso la connessione.")
                        break
                    testo = state["cipher"].decrypt(encrypted_msg).decode("utf-8")
                    scrivi_in_chat(state["partner_name"], testo)
                except:
                    break

        threading.Thread(target=ricevi_messaggi_loop, daemon=True).start()

        page.add(
            ft.Column(
                [
                    ft.Text(f"Chat con: {state['partner_name']}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(
                        content=chat_box,
                        bgcolor="#1E1E1E",
                        border_radius=5,
                        expand=True,
                    ),
                    ft.Row(
                        [
                            txt_msg,
                            ft.IconButton(
                                icon=ft.Icons.SEND,
                                icon_color=ft.Colors.BLUE_400,
                                on_click=invia_messaggio,
                            ),
                        ]
                    ),
                    ft.OutlinedButton("Torna al Menu", width=200, on_click=mostra_menu),
                ],
                expand=True,
            )
        )

    mostra_menu()


ft.app(target=main)
