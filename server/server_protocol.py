import re

# CREATING RESPONSE
def _create_protocol(header, data_in_bytes):
    return header.encode() + " ".encode() + data_in_bytes + "\n".encode()


def _create_protocol_with_no_data(header):
    return (header + "\n").encode()


def _dictionary_to_string_list(game_state):
    area = ""
    for field in game_state["game_board"]:
        area += field
    return str(game_state["your_move"]) + " " + area


def end_response(value):
    return _create_protocol("END", value.encode())


def game_state_response(game_state):
    return _create_protocol("GAMESTATE", _dictionary_to_string_list(game_state).encode())


def bad_request_error(value):
    return _create_protocol("BADREQUEST", value.encode())


# PARSING REQUEST
def _service_protocol_from_client(data_in_bytes):
    header = data_in_bytes[0].decode()
    if header == "JOINROOM":
        return [header]
    elif header == "MAKEMOVE":
        if _re_makemove(data_in_bytes):
            return [header,
                    int(data_in_bytes[1].decode()),
                    int(data_in_bytes[2].decode())]
        else:
            raise BadDataFormatException('Bad MAKEMOVE data format: ' + str(data_in_bytes))
    else:
        raise BadHeaderException('Bad header: ' + header)


def parse_data_from_client(data):
    return _service_protocol_from_client(data[:-1].split(b' '))


def _re_makemove(data_in_bytes):
    data = ""
    for x in data_in_bytes:
        data += x.decode() + " "
    data = data[:-1]
    return re.match(r'^MAKEMOVE [0-2] [0-2]', data, flags=re.MULTILINE + re.DOTALL)
