#!/usr/bin/python3
import sys
import time
import json
import ssl
import queue
import select
import socket
from server_protocol import *
from room import RoomList, Room
from game import Game
import os
import datetime

LOG_INFO = True
LOG_DEBUG = True

LOG_FILE_NAME = 'World.log'

class World:
    CLIENT_CERT = 'cert/client.crt'
    SERVER_CERT = 'cert/server.crt'
    SERVER_KEY = 'cert/server.key'

    def __init__(self, addr, port, addr_v6,
                 socket_blocking=0,
                 socket_listen=5,
                 socket_buff_size=1337):
        self.room_list = RoomList()
        self.games = {}
        self.addr = addr
        self.port = port
        self.addr_v6 = addr_v6
        self.socket_blocking = socket_blocking
        self.socket_listen = socket_listen
        self.socket_buff_size = socket_buff_size

        self.context = self._get_ssl_context(World.SERVER_CERT,
                                             World.SERVER_KEY,
                                             World.CLIENT_CERT)


    def start(self):
        LogInfo("Starting IPv4 socket...")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setblocking(self.socket_blocking)
        self.server_socket.bind((self.addr, self.port))
        self.server_socket.listen(self.socket_listen)
        LogInfo("Started IPv4 socket.")

        LogInfo("Starting IPv6 socket...")
        self.server_socket_v6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.server_socket_v6.setblocking(self.socket_blocking)
        self.server_socket_v6.bind((self.addr_v6, self.port))
        self.server_socket_v6.listen(self.socket_listen)
        LogInfo("Started IPv6 socket.")

        self.inputs = [self.server_socket, self.server_socket_v6]
        self.outputs = []

        self.message_queues = {}

        self._handle_msg()

    def _handle_msg(self):
        LogInfo("Started handling messages.")
        while self.inputs:
            readable, writable, exceptional \
                = select.select(self.inputs, self.outputs, self.inputs)

            self._handle_readable(readable)
            self._handle_writeable(writable)
            self._handle_exceptional(exceptional)
        LogInfo("Ended handling messages.")
       

    def _handle_readable(self, readable):
        for s in readable:
            if s is self.server_socket:
                try:
                    self._accept_new_connection(s)
                except Exception as error:
                    LogDebug("IPv4 - Accept connection error: [{}]", str(error))
                continue
            elif s is self.server_socket_v6:
                try:
                    self._accept_new_connection(s)
                except Exception as error:
                    LogDebug("IPv6 - Accept connection error: [{}]", str(error))
                continue

            data = None
            try:
                data = s.recv(self.socket_buff_size)
            except (ConnectionError):
                self._disconnect_player(s)
                continue

            if not data or len(data) == 0:
                self._disconnect_player(s)
                continue

            try:
                try:
                    parsedData = parse_data_from_client(data)
                    header = parsedData[0]
                except BadDataFormatException as error:
                    LogWarn("Wrong player data format: ", str(error))
                    s.send(bad_request_error("1"))
                    continue
                except BadHeaderException as error:
                    LogWarn("Wrong player header: ", str(error))
                    s.send(bad_request_error("2"))
                    continue
                except Exception as exception:
                    LogWarn("Unknown error: ", exception)
                    s.send(bad_request_error("3"))
                    continue
            except Exception as send_error:
                LogWarn("Sending messsage error: ", str(send_error))
                continue

            LogDebug("Handled header: [{}]", header)
            if header == "JOINROOM":
                room = self.room_list.add_player(s)
                LogDebug("Room size size=[{}] room=[{}]", str(room.size()), str(room))

                if room.full():
                    self._create_new_game(room)

            elif header == "MAKEMOVE":
                x = parsedData[1]
                y = parsedData[2]

                LogDebug("Make move x=[{}] y=[{}]\nplayer=[{}]", x, y, str(s))

                room = self.room_list.get_room(s)
                if room is None:
                    LogWarn("Player [{}] making move, but isnt in any room", str(s))
                    return

                game = self.games.get(room)
                if game is None:
                    LogWarn("Player [{}] making move, \
                            but game isnt started in his room", str(s))
                    return

                succes = game.move(s, x, y)

                if succes:
                    self._broadcast_game_state(room)
                else:
                    LogDebug("Make move failed. x=[{}], y=[{}] ", x, y)
            else:
                LogWarn("Not supported header=[{}]", header)

    def _handle_writeable(self, writable_sockets):
        for s in writable_sockets:

            socket_queue = self.message_queues.get(s)
            if not socket_queue:
                continue

            try:
                next_msg = socket_queue.get_nowait()
                if next_msg:
                    LogDebug("Sending data size=[{}] data=[{}] to=[{}]", len(next_msg), next_msg, str(s))
                    try:
                        s.send(next_msg)
                    except Exception as send_error:
                        LogWarn("Sending messsage error: [{}]", send_error)
                        self._disconnect_player(s)
                        continue
            except queue.Empty:
                self.outputs.remove(s)

    def _handle_exceptional(self, exceptional):
        for s in exceptional:
            self._disconnect_player(s)

    def _accept_new_connection(self, server_socket):
        new_connection, addr = server_socket.accept()
        LogInfo("Got new connection from IP=[{}] Port=[{}]", addr[0], addr[1])

        connection = self.context.wrap_socket(new_connection,
                                              server_side=True)
        LogInfo("SSL established. Peer: [{}]", connection.getpeercert())

        connection.setblocking(self.socket_blocking)
        self.inputs.append(connection)
        self.message_queues[connection] = queue.Queue()

    def _create_new_game(self, room):
        players = room.players
        LogInfo(
            "Creating new game for:\n player1=[{}]\nplayer2=[{}]",
            str(players[0]), str(players[1]))

        self.games[room] = Game(players[0], players[1])

        self._broadcast_game_state(room)

    def _broadcast_game_state(self, room):
        room_ended_game = False
        for s in room.players:
            game_state = self.games[room].game_state(s)

            LogDebug("Broadcast game_state: [{}]", game_state)
            self.message_queues[s].put(game_state_response(game_state))
            self.outputs.append(s)

            if game_state["end"]:
                if game_state["winner"] == "1":
                    res = "True"
                elif game_state["winner"] == "-1":
                    res = "False"
                else:
                    res = "Draw"
                self.message_queues[s].put(end_response(res))
                self.outputs.append(s)
                room_ended_game = True

        if room_ended_game:
            self.room_list.remove_room(room)

    def _get_ssl_context(self, server_cert, server_key, client_cert):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_cert_chain(certfile=server_cert, keyfile=server_key)
        context.load_verify_locations(cafile=client_cert)
        return context

    def _disconnect_player(self, s):
        LogInfo("Disconnecting player=[{}]", str(s))
        self._close_connection(s)

        room = self.room_list.get_room(s)
        if room is None:
            return

        game = self.games.get(room)
        if game:  # if room is in game
            enemy_player = game.enemy_player(s)
            del self.games[room]
            try:
                LogInfo("Ending players game player=[{}]", str(s))
                enemy_player.send(end_response("True"))
            except Exception as send_error:
                LogWarn("Send messsage problem: msg=[{}]", str(send_error))
                self._disconnect_player(enemy_player)

        room.remove_player(s)
        if room.empty():
            LogInfo("Removing empty room=[{}]", str(room))
            self.room_list.remove_room(room)

    def _close_connection(self, socket):
        if socket in self.inputs:
            self.inputs.remove(socket)
        if socket in self.outputs:
            self.outputs.remove(socket)
        if socket in self.message_queues:
            del self.message_queues[socket]
        socket.close()


# Simplest logger :D
# example usage: LogInfo("X:{} Y:{} Z:{}", 123, "asd", 1.0)
def LogInfo(msg, *args):
    if LOG_INFO:
        msg = "[INFO] - " + msg.format(*args)
        _Log(msg)


# example usage: LogDebug("X:{} Y:{} Z:{}", 123, "asd", 1.0)
def LogDebug(msg, *args):
    if LOG_DEBUG:
        msg = "[DEBUG] - " + msg.format(*args)
        _Log(msg)


def LogWarn(msg, *args):
    msg = "[WARNING] - " + msg.format(*args)
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
