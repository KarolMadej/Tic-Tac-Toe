from world import World


if __name__ == "__main__":
    world = World("localhost", 50000, "::1")
    world.start()
