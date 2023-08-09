import os
import struct
import random
import copy
import pickle 

from nidus.log import Log, append_entries
from typing import Tuple

class RaftState:
    # status states
    LEADER = "LEADER"
    CANDIDATE = "CANDIDATE"
    FOLLOWER = "FOLLOWER"
    PROXY = "PROXY"
    PROXYCANDIDATE = "PROXYCANDIDATE"

    PHASE1 = "PHASE 1"
    PHASE2 = "PHASE 2"
    PHASE3 = "PHASE 3"
    PHASE4 = "PHASE 4"

    def __init__(self, storage_dir, node_id, life_time: int, threshold: Tuple[float, float, float]):
        self._storage_dir = storage_dir
        self._node_id = node_id
        
        self.subscriber = None
        self.status = self.FOLLOWER
        self._life_time = life_time + 1 if node_id == "node-0" else life_time
        self._threshold = threshold
        self._phase = None
        
        self._current_term = 0
        self._voted_for = None
        self.proxy_candidates = dict()
        self.votes = set()
        self.log = Log(os.path.join(storage_dir, f"{node_id}.log"))
        self.commit_index = -1
        self.last_applied = -1
        self.match_index = {}
        self.next_index = {}
        
        

        term_path = os.path.join(self._storage_dir, f"{self._node_id}.term")
        if os.path.exists(term_path):
            with open(term_path, "rb+") as f:
                f.seek(0)
                self._current_term = struct.unpack(">L", f.read(4))[0]
        else:
            with open(term_path, "wb+"):
                pass

        vote_path = os.path.join(self._storage_dir, f"{self._node_id}.vote")
        if os.path.exists(vote_path):
            with open(vote_path, "rb+") as f:
                f.seek(0)
                data = f.read()
                if data:
                    self._voted_for = data.decode("utf8")
                else:
                    self._voted_for = None
        else:
            with open(vote_path, "wb+"):
                pass
            
        self.switch_phase() 
            
        
    @property
    def phase(self):
        return self._phase
    
    @phase.setter
    def phase(self, desired_phase):
        """
        Metodo de apoio apoio para aplicar regras dinamicamente de acordo com a mudança de life_time
        """      
        if self._phase != desired_phase:            
            self._phase = desired_phase
            self.notify_subscriber()
            
            ## TODO chamar executor de comportamento
            
    
    @property
    def life_time(self):
        return self._life_time
    
    @life_time.setter
    def life_time(self, desired_life_time):
        """
        Método opoio para aplicar regras dinamicamente de acordo com a mudança de life_time
        """        
        if desired_life_time != self._life_time:            
            self._life_time = desired_life_time
            self.switch_phase()            
            
            
    def switch_phase(self): 
        if  self.life_time >= self._threshold[0]:
            self.phase = RaftState.PHASE1
        elif self.life_time >= self._threshold[1]:
            self.phase = RaftState.PHASE2
        elif self.life_time >= self._threshold[2]:
            self.phase = RaftState.PHASE3
        else:
            self.phase = RaftState.PHASE4
        # print(f"Current Phase: {self._phase}")


    @property
    def current_term(self):
        return self._current_term

    @current_term.setter
    def current_term(self, term):
        path = os.path.join(self._storage_dir, f"{self._node_id}.term")
        with open(path, "rb+") as f:
            f.seek(0)
            f.write(struct.pack(">L", term))
        self._current_term = term

    @property
    def voted_for(self):
        return self._voted_for

    @voted_for.setter
    def voted_for(self, candidate):
        path = os.path.join(self._storage_dir, f"{self._node_id}.vote")
        with open(path, "rb+") as f:
            f.seek(0)
            f.truncate()
            if candidate is not None:
                f.write(candidate.encode("utf8"))
        self._voted_for = candidate

    def become_leader(self, nodes):
        self.status = self.LEADER
        # next log entry to send to peer
        self.next_index = {n: len(self.log) for n in nodes}
        # highest index known to be replicated on a server
        self.match_index = {n: -1 for n in nodes}
        self.notify_subscriber()

    def become_follower(self):
        self.status = self.FOLLOWER
        self.voted_for = None
        self.notify_subscriber()

    def become_candidate(self, node_id, life_time):
        self.status = self.CANDIDATE
        self.life_time = life_time
        self.current_term += 1
        self.voted_for = node_id
        self.votes = set([node_id])
        self.notify_subscriber()

    def become_proxy(self):
        self.status = self.PROXY
        self.notify_subscriber()
        
    def become_proxycandidate(self):
        self.status = self.PROXYCANDIDATE
        self.notify_subscriber()

    def become_phase1(self):
        self._phase = RaftState.PHASE1
        
    def become_phase2(self):
        self._phase = RaftState.PHASE2
        
    def become_phase3(self):
        self._phase = RaftState.PHASE3
        
    def become_phase4(self):
        self._phase = RaftState.PHASE4
        
    def add_subscriber(self, sub):
        self.subscriber = sub
    
    def notify_subscriber(self):        
        if self.subscriber:
            self.subscriber.update_behavior()
   
    def append_entries(self, prev_index, prev_term, entries):
        return append_entries(self.log, prev_index, prev_term, entries)

    def copy_state_proxy(self):
        return [self.match_index , self.next_index, self.current_term, 
                self.commit_index, self.last_applied]
