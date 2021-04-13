

class Room:
    max_size = 2

    def __init__(self, player):
        self.players = [player]

    def add_player(self, player):
        if self.full():
            return
        self.players.append(player)

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)

    def full(self):
        return self.size() == self.max_size

    def empty(self):
        return self.size() == 0

    def size(self):
        return len(self.players)


class RoomList:
    def __init__(self):
        self.rooms = []
        self.players_in_room = {}

    def add_player(self, player):
        # if player is in room return this room
        player_room = self.players_in_room.get(player)
        if player_room:
            return player_room

        # if player isnt in any room, find not full room
        for room in self.rooms:
            if not room.full():
                room.add_player(player)
                self.players_in_room[player] = room
                return room
        # if all rooms are full then create new room
        else:
            room = Room(player)
            self.rooms.append(room)
            self.players_in_room[player] = room
            return room

    def get_room(self, player):
        return self.players_in_room.get(player)

    def remove_room(self, room):
        if room in self.rooms:
            for player in room.players:
                if player in self.players_in_room:
                    del self.players_in_room[player]
            self.rooms.remove(room)

