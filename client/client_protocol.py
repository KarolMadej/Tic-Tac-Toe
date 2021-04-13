import base64
import json


# CREATE RESPONSE
def _create_protocol(header, data_in_bytes):
    return header.encode() + " ".encode() + data_in_bytes + "\n".encode()


def _create_protocol_with_no_data(header):
    return (header + "\n").encode()


def make_move_request(x: int, y: int):
    if x > 2 or x < 0:
        raise ValueError("Bad request value :x" + str(x))
    elif y > 2 or y < 0:
        raise ValueError("Bad request value :x" + str(y))

    return _create_protocol("MAKEMOVE", (str(x) + " " + str(y)).encode())


def join_to_room_request():
    return _create_protocol_with_no_data("JOINROOM")


# PARSE REQUEST
def _service_protocol_from_server(data):
    header = data[0]
    if header == "GAMESTATE":
        return [header, data[1] == "True", data[2]]
    elif header == "END":
        return data
    elif header == "BADREQUEST":
        return data


def parse_data_from_server(data):
    return _service_protocol_from_server(data[:-1].decode().split(' '))
