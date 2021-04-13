import ssl
import threading
import sys
import math
import select
import socket
import pyglet
from pyglet.gl import *
import datetime
from client_protocol import parse_data_from_server, \
    join_to_room_request, make_move_request

# dla IPv4:
# host = 'localhost'
# dla IPv6:
host = '::1'

port = 50000
CLIENT_KEY = 'cert/client.key'
CLIENT_CERT = 'cert/client.crt'
SERVER_CERT = 'cert/server.crt'
close = False

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=SERVER_CERT)
context.check_hostname = False
context.load_cert_chain(certfile=CLIENT_CERT, keyfile=CLIENT_KEY)
LINE_THICKNESS = 24
O = "O"
X = "X"

LOG_INFO = True
LOG_DEBUG = True

LOG_FILE_NAME = 'Client.log'


def LogInfo(msg, *args):
    if LOG_INFO:
        msg = "[INFO] - " + msg.format(*args)
        _Log(msg)

def LogWarn(msg, *args):
    msg = "[WARNING] - " + msg.format(*args)
    _Log(msg)

def LogDebug(msg, *args):
    if LOG_DEBUG:
        msg = "[DEBUG] - " + msg.format(*args)
        _Log(msg)

def _Log(msg):
    timestamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    _LogToFile(timestamp + " " + msg + "\n")
    _LogToConsole(msg)

def _LogToFile(msg):
    logging_file = open(LOG_FILE_NAME, "a+")
    logging_file.write(msg)
    logging_file.close

def _LogToConsole(msg):
    print(msg)


class Game:
    def __init__(self):
        self.win = None
        self.your_move = False
        self.board = "---------"
        self.queued = False
        self.serveroff = False
        self.in_game = False
        # dla IPv4:
        # self.client_socket = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_side=False)
        # LogInfo("Starting IPv4 socket")
        # dla IPv6:
        self.client_socket = context.wrap_socket(socket.socket(socket.AF_INET6, socket.SOCK_STREAM), server_side=False)
        LogInfo("Starting IPv6 socket")
        try:
            self.client_socket.connect((host, port))
            LogInfo("A successful connection to the server")
        except(ConnectionError) as error:
            self.serveroff = True
            LogWarn("Connection error" + str(error))

    def state(self):
        if self.serveroff:
            return "Serwer jest offline"

        if self.queued:
            return "Szukanie przeciwnika"

        if self.in_game:
            if self.your_move and self.in_game:
                return "Twoja tura"

            if not self.your_move and self.in_game:
                return "Tura przeciwnka"

        elif not self.in_game:
            if self.win is None:
                return "Kliknij aby wyszukac przeciwnika"

            if self.win == 1:
                return "Wygrałeś, kliknij aby grac dalej"

            if self.win == -1:
                return "Przegrałeś, kliknij aby grac dalej"

            if self.win == 0:
                return "Remis, kliknij aby grac dalej"

    def update(self, dt=0):
        global close
        r, _, _ = select.select([self.client_socket], [], [], 1)
        if not r:
            return
        data = ""

        try:
            data = self.client_socket.recv(1024)
            LogDebug("Recive data = {}", data)
        except(ConnectionError) as error:
            self.serveroff = True
            close = True
            LogWarn("Connection error" + str(error))


        if not data and not self.serveroff:
            LogDebug("No data")
            return
        elif self.serveroff:
            return

        parsed_data = parse_data_from_server(data)
        header = parsed_data[0]

        if header == "GAMESTATE":
            if parsed_data[1] == True or parsed_data[1] == False and len(parsed_data[2]) == 9:
                self.your_move = parsed_data[1]
                self.board = parsed_data[2]
                self.in_game = True
                self.queued = False
                LogDebug("GAMESTATE your_move=[{}] board=[{}] in_game=[{}] queued=[{}]", self.your_move, self.board,
                         self.in_game, self.queued)
        elif header == "END":
            if parsed_data[1] == "True" or parsed_data[1] == "False" or parsed_data[1] == "Draw":
                result = parsed_data[1]
                self.in_game = False
                self.win = 1 if result == "True" else -1 if result == "False" else 0
                self.queued = False
                LogDebug("END in_game=[{}] win=[{}] queued=[{}]", self.in_game, self.win, self.queued)
        elif header == "BADREQUEST":
            if parsed_data[1] == "1":
                LogWarn("Wrong player data format")
            if parsed_data[1] == "2":
                LogWarn("Wrong player header")
            if parsed_data[1] == "3":
                LogWarn("Unknown error")

    def place_tile(self, x, y):
        global close
        if self.serveroff:
            LogInfo("Server offline")
            window.close()
            LogInfo("Close game")
            close = True
            return

        if not self.queued and not self.in_game:
            LogInfo("Looking for an opponent")
            self.client_socket.send(join_to_room_request())
            self.queued = True
            self.win = None
            return

        if self.your_move:
            LogDebug("Chosen tile: X:[{}], Y:[{}]", x, y)
        if not self.in_game:
            return
        if self.board[x + y * 3] != "-":
            return
        if (self.win == -1 or self.win == 1) and not self.in_game:
            LogInfo("Game over")
            return
        if not self.your_move:
            LogInfo("Now the opponent's turn")
            return
        try:
            self.client_socket.send(make_move_request(x, y))
        except(ConnectionError) as error:
            self.serveroff = True
            LogWarn("Connection error" + str(error))


class MainWindow(pyglet.window.Window):
    def __init__(self, game, *args, **kwargs):
        pyglet.window.Window.__init__(self, *args, **kwargs)
        self.set_caption("Tic-Tac-Toe")
        self.game = game

    def on_close(self):
        global close
        LogInfo("Close game")
        window.close()
        close = True

    def on_mouse_press(self, x, y, button, modifiers):
        for i in range(1, 4):
            if x < (self.width / 3) * i:
                col = i - 1
                break

        for i in range(1, 4):
            if y < (self.height / 3) * i:
                row = 3 - i
                break
        self.game.place_tile(col, row)

    def update(self, dt=0):
        self.on_draw()

    def on_draw(self):
        self.clear()
        glLineWidth(LINE_THICKNESS)
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.draw_board()

        board = self.game.board
        for x in range(3):
            for y in range(3):
                glPushMatrix()
                glTranslatef(((self.width / 3) * (x - 1)), ((self.height / 3) * (y - 1)), 0.0)
                # 0 + (2  - 1 ) * 3
                if board[x + (2 - y) * 3] == X:
                    self.draw_x()
                if board[x + (2 - y) * 3] == O:
                    self.draw_o()
                glPopMatrix()

        state_label = pyglet.text.Label(self.game.state(),
                                        font_name='Arial',
                                        font_size=self.width // 20,
                                        x=self.width // 2, y=self.width // 10,
                                        anchor_x='center', anchor_y='center',
                                        color=(255, 0, 0, 255))
        state_label.draw()

    def draw_board(self):
        for x in range(1, 3):
            glBegin(GL_LINES)
            glVertex2f(0, ((self.height / 3) * x))
            glVertex2f(self.width, ((self.height / 3) * x))
            glEnd()

        for x in range(1, 3):
            glBegin(GL_LINES)
            glVertex2f(((self.width / 3) * x), 0)
            glVertex2f(((self.width / 3) * x), self.height)
            glEnd()

    def draw_o(self):
        glPushMatrix()
        glTranslatef(self.width / 2, self.height / 2, 0.0)
        glBegin(GL_LINE_LOOP)
        for x in range(360):
            rad = math.radians(x)
            glVertex2f(math.cos(rad) * self.width / 10, math.sin(rad) * self.height / 10)
        glEnd()
        glPopMatrix()

    def draw_x(self):
        glPushMatrix()
        glTranslatef(self.width / 2, self.height / 2, 0.0)
        glBegin(GL_LINES)
        glVertex2f(self.width / 10, -self.height / 10)
        glVertex2f(-self.width / 10, self.height / 10)
        glEnd()
        glBegin(GL_LINES)
        glVertex2f(self.width / 10, self.height / 10)
        glVertex2f(-self.width / 10, -self.height / 10)
        glEnd()
        glPopMatrix()


def update_game_thread(game):
    while close == False:
        game.update()


if __name__ == "__main__":
    game = Game()
    window = MainWindow(game, width=600, height=600, resizable=False)
    thread = threading.Thread(target=update_game_thread, args=(game,))
    thread.start()
    pyglet.clock.schedule_interval(window.update, 1 / 60)

    pyglet.app.run()