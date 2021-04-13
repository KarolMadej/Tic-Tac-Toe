from client.client_protocol import *
from server.server_protocol import *

#PROTOCOL TESTS
def server_protocol_tests():
    game_state = {
            "your_move": True,
            "game_board": "--XXO--O-",
            "winner": 0,
            "end": False
        }
    assert (game_state_response(game_state) == b"GAMESTATE True --XXO--O-\n")
    assert (end_response("True") == b"END True\n")
    print("OK server_protocol_tests")

def client_protocol_tests():
    assert(make_move_request(1, 2) == b"MAKEMOVE 1 2\n")
    print("OK client_protocol_tests")

# PARSER TESTS
def server_parser_tests():
    mock_make_move_request = "MAKEMOVE " + str(1) + " " + str(2) + "\n"

    assert(parse_data_from_client(mock_make_move_request.encode()) == ['MAKEMOVE', 1, 2])

    print("OK parser_tests")


def client_parser_tests():
    mock_game_state_response = "GAMESTATE True -XO--X--- False\n"

    assert (parse_data_from_server("END\n".encode()) == ['END'])
    assert (parse_data_from_server(mock_game_state_response.encode())  == ['GAMESTATE', True, "-XO--X---"])
    print("OK client_parser_tests")


if __name__ == "__main__":
    server_protocol_tests()
    client_protocol_tests()
    server_parser_tests()
    client_parser_tests()
