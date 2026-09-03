#!/usr/bin/env python3
"""Servidor Python para Jogo 3D Multiplayer - Usa websockets para comunica&ccedil;&atilde;o em tempo real"""
import http.server, socketserver, json, threading
try:
    import websocket_server
    USE_WEBSOCKETS = True
except ImportError:
    USE_WEBSOCKETS = False
    print("⚠️ websocket_server n&atilde;o instalado. Instalando...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'websocket-server'])
    import websocket_server
players = {}
class MultiplayerWebSocket:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.server = None
    def start(self):
        self.server = websocket_server.WebSocketServer(port=self.port, host=self.host)
        self.server.run_forever(threaded=True)
        print(f"🚀 WebSocket rodando em {self.host}:{self.port}")
    def broadcast(self, message):
        if self.server: self.server.send_message(json.dumps(message))
    def handle_message(self, client, message):
        try:
            data = json.loads(message)
            event_type = data.get('type')
            if event_type == 'join':
                player_id = data.get('id')
                player_name = data.get('name', 'Anonimo')
                players[player_id] = {'id': player_id, 'name': player_name, 'x': data.get('x', 0), 'y': data.get('y', 2), 'z': data.get('z', 0)}
                print(f"👥 Jogador entrou: {player_name} ({player_id})")
                self.broadcast({'type': 'playerList', 'players': players})
                self.broadcast({'type': 'playerJoined', 'data': players[player_id]})
            elif event_type == 'playerMove':
                player_id = data.get('id')
                if player_id in players:
                    players[player_id]['x'] = data.get('x')
                    players[player_id]['y'] = data.get('y')
                    players[player_id]['z'] = data.get('z')
                self.broadcast({'type': 'playerMove', 'data': data})
        except Exception as e: print(f"❌ Erro: {e}")
class HTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/': self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    def log_message(self, format, *args): print(f"🌐 {args[0]}")
def run_http_server(port=8000):
    handler = HTTPHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 HTTP rodando em http://localhost:{port}")
        print(f"📝 Acesse: http://localhost:{port}/multiplayer.html")
        httpd.serve_forever()
def main():
    print("=" * 50)
    print("🎮 Servidor Jogo 3D Multiplayer")
    print("=" * 50)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    if USE_WEBSOCKETS:
        ws = MultiplayerWebSocket()
        ws.start()
    else: print("❌ WebSockets n&atilde;o dispon&iacute;veis")
    try: http_thread.join()
    except KeyboardInterrupt: print("\n👋 Servidor encerrado")
if __name__ == '__main__': main()
