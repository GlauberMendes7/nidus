import argparse
import logging
import queue
import re
import sys
import time
from types import FrameType
from typing import Any

from nidus.actors import Actor, get_system
from nidus.config import load_user_config
from nidus.kvstore import KVStore
from nidus.messages import ClientRequest
from nidus.raft import RaftNetwork

response = queue.Queue()


class Client(Actor):
    def handle_client_response(self, res):
        response.put(res.result)


def main():
    parser = argparse.ArgumentParser(description="Start a node or run a client command")
    parser.add_argument(
        "-c", "--config", help="Configuration file to be used for the cluster"
    )
    parser.add_argument(
        "-l", "--leader", help="The leader address for a client command"
    )
    parser.add_argument(
        "name", nargs="*", help="Name or command if --leader flag is provided"
    )
    args = parser.parse_args()

    if args.leader:
        host, port = args.leader.split(":")

        actor_system = get_system()
        addr = actor_system.create(("localhost", 12345), Client)
        actor_system.send((host, int(port)), ClientRequest(addr, args.name))
        try:
            res = response.get(timeout=5)
        except queue.Empty:
            print("Timeout waiting for response")
        else:
            print(res)
        actor_system.shutdown()
    else:
        config = load_user_config(args.config)
        net = RaftNetwork(config, KVStore)

        nodes = [net.create_node(n) for n in args.name]
        return nodes

logger = logging.getLogger('trace')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(f'nidus_logs/{time.strftime("%Y%m%d-%H%M%S")}_trace.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s,%(msecs)d %(message)s'))
logger.addHandler(fh)


# https://stackoverflow.com/questions/5103735/better-way-to-log-method-calls-in-python
def trace(frame: FrameType, event: str, arg: Any):
    
    if event != "call":
        return None
    
    filename = frame.f_code.co_filename
    funcname = frame.f_code.co_name
    
    if "/nidus/" not in filename or re.match("((__\\w+__)|(\\<\\w+\\>))", funcname):
        return None
    
    locals = frame.f_locals
    line = frame.f_lineno

    logger.info("%s @ %s - %s (%s)" % (filename, line, funcname, str(locals).replace('\n', '')))
    
    return trace


# if not __debug__:
    
sys.settrace(trace)

nodes = main()

sys.settrace(None)

