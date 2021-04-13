import random


class Game:

    winners = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6),
               (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6))

    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.player_turn = \
            self.player1 if random.uniform(0, 1) else self.player2
        self.current_mark = "X"  # only X or O

        self.game_board = [
            "-", "-", "-",
            "-", "-", "-",
            "-", "-", "-"
            # -  empty, only default
            # X   x
            # O   0 
        ]

        self.winner = None
        self.end = False

    def enemy_player(self, player):
        return self.player1 if player == self.player2 else self.player2

    def move(self, player, x, y):
        if player is not self.player_turn:
            return False

        if self.end or self.winner:
            return False

        if x > 2 or x < 0 or y > 2 or y < 0:
            return False

        if self.game_board[x+y*3] != "-":
            return False

        self.game_board[x+y*3] = self.current_mark

        if self._check_win():
            print("Player won: "+str(player))
            self.winner = player
            self.end = True

        if self._check_draw():
            print("Playes draw")
            self.end = True

        self._next_mark()
        self._next_player()
        return True

    def game_state(self, player):
        # game_state
        # "your_move": boolean
        # "game_board": string , example: ------XOX--O
        # "winner": int
        #        1  - won
        #        -1 - lose
        #        0  - no winner (draw or still playing)
        # "end": boolean
        # cases:
        # winner = 0 and end = false -> players still playing
        # winner = 0 and end = true  -> draw
        # winner = -1 or 1           -> game ended anyway 

        if self.winner is None:
            winner = 0
        elif player is self.winner:
            winner = 1
        else:
            winner = -1

        game_state = {
            "your_move": player is self.player_turn,
            "game_board": ''.join(self.game_board),
            "winner": str(winner),
            "end": self.end
        }

        return game_state

    def _next_mark(self):
        self.current_mark = "X" if self.current_mark == "O" else "O"

    def _next_player(self):
        self.player_turn = \
            self.player1 if self.player_turn is self.player2 else self.player2

    def _check_win(self):

        for tup in Game.winners:
            win = True
            for ix in tup:
                if self.game_board[ix] != self.current_mark:
                    win = False
                    break
            if win:
                break
        return win

    def _check_draw(self):
        return False if "-" in self.game_board else True
