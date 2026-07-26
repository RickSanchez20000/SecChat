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
    # Setup Pagina
    page.title = "SecChat P2P Secure Chat"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 700
    page.padding = 20

    # Variabili di Stato
    state = {
        "socket_connessione": None,
        "cipher": None,
        "username": "User",
        "partner_name": "Partner",
        "stop_broadcast": False,
    }

    # ==================== SCHERMATA MENU ====================
    txt_username = ft.TextField(
        label="Il tuo Username", value="User", width=380, height=50
    )

    def go_to_host(e):
        state["username"] = txt_username.value.strip() or "User"
        page.go("/host")

    def go_to_client(e):
        state["username"] = txt_username.value.strip() or "Ghost"
        page.go("/client")

    view_menu = ft.View(
        "/",
        [
            ft.Text("SecChat", size=32, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            txt_username,
            ft.Container(height=20),
            ft.ElevatedButton(
                "Crea una Stanza (Host)",
                width=380,
                height=45,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_700),
                on_click=go_to_host,
            ),
            ft.ElevatedButton(
                "Unisciti a una Stanza (Client)",
                width=380,
                height=45,
                on_click=go_to_client,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )

    # ==================== SCHERMATA HOST ====================
    txt_stanza = ft.TextField(
        label="Nome della Stanza", placeholder="Es. Stanza Segreta", width=380
    )
    status_host = ft.ListView(expand=True, spacing=5, padding=10)

    def log_status_host(testo):
        status_host.controls.append(ft.Text(testo, size=12))
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

        threading.Thread(target=broadcast_room, args=(room_title,), daemon=True).start()

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", 9999))
        server.listen(1)

        log_status_host(f"[*] Stanza '{room_title}' attiva. In attesa di utenti...")

        while True:
            try:
                conn, addr = server.accept()
                dati_bussata = conn.recv(1024).decode("utf-8")
                if dati_bussata.startswith("USER:"):
                    state["partner_name"] = dati_bussata[5:]
                    log_status_host(
                        f"\n[richiesta] '{state['partner_name']}' ({addr[0]}) connesso."
                    )

                    # Accettazione automatica della connessione P2P
                    conn.send(f"OK:{state['username']}".encode("utf-8"))
                    state["socket_connessione"] = conn
                    state["stop_broadcast"] = True
                    log_status_host(f"[+] Accesso consentito a {state['partner_name']}!")

                    time.sleep(1)
                    page.go("/chat")
                    break
            except Exception:
                break

    def avvia_server_click(e):
        room_title = txt_stanza.value.strip() or f"Stanza di {state['username']}"
        threading.Thread(target=logica_host, args=(room_title,), daemon=True).start()

    view_host = ft.View(
        "/host",
        [
            ft.Text("CREA STANZA", size=22, weight=ft.FontWeight.BOLD),
            txt_stanza,
            ft.Container(
                content=status_host,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=5,
                height=200,
                width=380,
            ),
            ft.ElevatedButton("Avvia Stanza", width=380, on_click=avvia_server_click),
            ft.OutlinedButton("Indietro", width=200, on_click=lambda _: page.go("/")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ==================== SCHERMATA CLIENT ====================
    status_client = ft.ListView(expand=True, spacing=5, padding=10)
    txt_ip = ft.TextField(label="IP Stanza", placeholder="192.168.1.X", width=380)
    txt_key = ft.TextField(
        label="Chiave Segreta E2E", placeholder="Incolla chiave...", width=380
    )

    def log_status_client(testo):
        status_client.controls.append(ft.Text(testo, size=12))
        page.update()

    def esegui_scansione():
        log_status_client("[*] Scansione rete locale in corso...")
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
            log_status_client("Nessuna stanza trovata automaticamente.")
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
                page.go("/chat")
            else:
                client.close()
                log_status_client("[-] Accesso rifiutato.")
        except Exception:
            log_status_client("[-] Errore di connessione.")

    def connettiti_click(e):
        ip = txt_ip.value.strip() or "127.0.0.1"
        chiave = txt_key.value.strip()
        threading.Thread(
            target=logica_client, args=(ip, chiave), daemon=True
        ).start()

    view_client = ft.View(
        "/client",
        [
            ft.Text("UNISCITI A UNA STANZA", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=status_client,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=5,
                height=150,
                width=380,
            ),
            ft.ElevatedButton(
                "Scansiona Wi-Fi", width=380, on_click=scansiona_click
            ),
            txt_ip,
            txt_key,
            ft.ElevatedButton(
                "Connettiti",
                width=380,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN_700),
                on_click=connettiti_click,
            ),
            ft.OutlinedButton("Indietro", width=200, on_click=lambda _: page.go("/")),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ==================== SCHERMATA CHAT ====================
    chat_box = ft.ListView(expand=True, spacing=10, padding=10, auto_scroll=True)
    txt_msg = ft.TextField(
        placeholder="Scrivi un messaggio...", expand=True, height=45
    )

    def scrivi_in_chat(mittente, testo):
        orario = datetime.now().strftime("%H:%M")
        chat_box.controls.append(
            ft.Text(f"[{orario}] {mittente}: {testo}", size=14)
        )
        page.update()

    def invia_messaggio(e):
        testo = txt_msg.value.strip()
        if testo and state["socket_connessione"]:
            try:
                state["socket_connessione"].send(
                    state["cipher"].encrypt(testo.encode("utf-8"))
                )
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
                    scrivi_in_chat(
                        "Sistema",
                        f"{state['partner_name']} ha chiuso la connessione.",
                    )
                    break
                testo = state["cipher"].decrypt(encrypted_msg).decode("utf-8")
                scrivi_in_chat(state["partner_name"], testo)
            except:
                break

    def carica_chat():
        threading.Thread(target=ricevi_messaggi_loop, daemon=True).start()

    view_chat = ft.View(
        "/chat",
        [
            ft.Text(
                f"Chat con: {state['partner_name']}",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Container(
                content=chat_box,
                border=ft.border.all(1, ft.Colors.OUTLINE),
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
        ],
    )

    # Gestione delle Viste / Navigazione
    def route_change(route):
        page.views.clear()
        if page.route == "/":
            page.views.append(view_menu)
        elif page.route == "/host":
            page.views.append(view_host)
        elif page.route == "/client":
            page.views.append(view_client)
        elif page.route == "/chat":
            view_chat.controls[0].value = f"Chat con: {state['partner_name']}"
            page.views.append(view_chat)
            carica_chat()
        page.update()

    page.on_route_change = route_change
    page.go(page.route)


ft.app(target=main)
