
"""
war card game client and server

Patrick Welch
CS 450
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import threading
import sys

import functools

Game = namedtuple("Game", ["p1", "p2"])

class MyConnection:

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

gameQueue = asyncio.Queue()

#make global queue

# https://docs.python.org/3/library/asyncio-stream.html

# def f(reader, writer):
#     g = functools.partial(f, c = myQ)
#     return g

# async def MyHandler(reader, writer, gameQuene = None)

async def MyHandler(reader, writer):
    logging.info("MyHandler")
    data = await reader.readexactly(2)

    logging.info(data)

    # data = await readexactly(reader.get_extra_info('socket'), 2)

    if (data[0]==Command.WANTGAME.value and gameQueue.empty()):
        # wait = reader.get_extra_info('socket')
        logging.info("Put in queue")
        await gameQueue.put(MyConnection(reader, writer))

    elif (data[0]==Command.WANTGAME.value and not gameQueue.empty()):
        # make game logic
        logging.info("Got two")
        newGame = Game(MyConnection(reader, writer), gameQueue.get_nowait())
        
        p1Hand, p2Hand = deal_cards()

        p1Hand = bytes(Command.GAMESTART.value) + p1Hand
        p2Hand = bytes(Command.GAMESTART.value) + p2Hand

        # newGame.p1.writer.write(bytes([Command.GAMESTART.value, p1Hand]))
        # newGame.p2.writer.write(bytes([Command.GAMESTART.value, p2Hand]))

        newGame.p1.writer.write(p1Hand)
        newGame.p2.writer.write(p2Hand)

        count = 0

        while True:
            # logging.info("In Loop")
            try:
                p1Act = await newGame.p1.reader.readexactly(2)
                p2Act = await newGame.p2.reader.readexactly(2)
            except IncompleteReadError:
                logging.info("Incomplete read = kill_game")
                kill_game(newGame)
                return

            if (p1Act[0] == Command.PLAYCARD.value and p2Act[0] == Command.PLAYCARD.value):
                compared = compare_cards(p1Act[1], p2Act[1])
                # logging.info(compared)
                if compared is None:
                    logging.info("Invalid compare = kill_game")
                    kill_game(newGame)
                    return
                elif compared == 1:
                    newGame.p1.writer.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                    newGame.p2.writer.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                elif compared == -1:
                    newGame.p1.writer.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                    newGame.p2.writer.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                elif compared == 0:
                    newGame.p1.writer.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                    newGame.p2.writer.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                else:
                    kill_game(newGame)
                count = count + 1
            else:
                logging.info("Escaped if else struct = kill_game")
                kill_game(newGame)
                return

            if count > 25:
                break
        logging.info("Redundant cleanup = kill_game")
        kill_game(newGame)
        return
    # message = data.decode()
    # addr = writer.get_extra_info('peername')
    # print("Received %r from %r" % (message, addr))

    # print("Send: %r" % message)
    # writer.write(data)
    # yield from writer.drain()


    # writer.close()


class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return.
    """
    byteTotal = b''
    byteRead = b''

    byteRead = sock.recv(1)

    while (len(byteRead) > 0):
        byteTotal = byteTotal + byteRead
        byteRead = sock.recv(1)
        #check invalid characters

    if len(byteTotal) < numbytes:
        #need more here?
        return None

    else:
        byteTotal = byteTotal[:numbytse]
        #check for invalid characters


    return byteTotal
    pass

def kill_game(game):
    logging.info("kill_game")
    # game.p1.reader.close()
    game.p1.writer.close()
    # game.p2.reader.close()
    game.p2.writer.close()
    pass

def compare_cards(card1, card2):
    
    try:
        card1Num = card1%14
        card2Num = card2%14
    except Exception as e:
        logging.info("Invalid compare byte?")
        return None

    # print(card1, card1Num)
    # print(card2, card2Num)

    if (card1Num > card2Num):
        return 1
    elif(card1Num < card2Num):
        return -1
    elif(card1Num == card2Num):
        return 0

    return None
    # pass

def deal_cards():
    
    deck = list(range(52))
    # print(deck)
    random.shuffle(deck)
    # print(deck)
    # print("\n\n")

    half = len(deck)//2

    p1Hand = deck[:half]
    p2Hand = deck[half:]

    p1Hand = (bytes(p1Hand))
    p2Hand = (bytes(p2Hand))

    return p1Hand, p2Hand
    pass




def serve_game(host, port):
    
    # https://docs.python.org/3/library/asyncio-stream.html
    logging.info("Start serve_game")
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(MyHandler, host, port, loop=loop)
    server = loop.run_until_complete(coro)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

    pass

async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port, loop=loop)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
            logging.info(myscore)
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            serve_game(host, port)
        except KeyboardInterrupt:
            pass
        return
    else:
        loop = asyncio.get_event_loop()

    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
