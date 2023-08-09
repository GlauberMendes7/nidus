import logging
import os
import random
import copy
from threading import Timer

from nidus.actors import Actor, get_system
from nidus.log import LogEntry, clear_upto
from nidus.messages import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    ClientResponse,
    ElectionRequest,
    HeartbeatRequest,
    HeartbeatUpdate,
    VoteRequest,
    VoteResponse,
    ProxyRequest,
    ProxyResponse,
    ProxyElectionResponse,
    ProxyElectionRequest,
    
)
from nidus.state import RaftState

from nidus.measurer import Measure
from nidus.bucket import Bucket

logger = logging.getLogger("node_logger")

SLOWHEARTBEAT = 0.02
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class RaftNetwork:
    """
    The raft network.
    """

    def __init__(self, config, state_machine_cls):
        self.actor_system = get_system()
        self.config = config
        self.raft_ctx = None
        self.state_machine_cls = state_machine_cls

        if not os.path.exists(config["storage_dir"]):
            os.makedirs(config["storage_dir"])

    def create_node(self, node_id):
        addr = self.config["cluster"][node_id]
        peers = [n for n in self.config["cluster"] if n != node_id]

        self.actor_system.create(
            addr, RaftNode, node_id, peers, self, self.state_machine_cls()
        )
        logger.info(f"server running on {addr}", extra={"node_id": node_id})
        # this is just nice while debugging
        return self.actor_system._actors[addr]

    def send(self, node_id, msg):
        # node_id is key to a host,port raft node
        if node_id in self.config["cluster"]:
            self.actor_system.send(self.config["cluster"][node_id], msg)
        else:  # it's a host,port addr (probably a client)
            self.actor_system.send(node_id, msg)
        return


class RaftNode(Actor):
    """
    All the message handling and state changing logic is here
    """

    def __init__(self, node_id, peers, network, state_machine):       
        
        self.field = network.config["metric"]
        self.capacity = network.config["capacity"]
        self.initial = random.uniform(network.config["initial"][0], network.config["initial"][1]) 
        self.rate = network.config["rate"]
        self.threshold = tuple(network.config["threshold"])
        self.bucket = Bucket(self.capacity, self.rate, self.initial)

        self.node_id = node_id
        self.peers = peers
        self.proxy_id = None
        self.network = network
        self.state = RaftState(self.network.config["storage_dir"], node_id, self.initial, self.threshold)
        self.state.add_subscriber(self)
        self.state_machine = state_machine
        self.heartbeat_interval = network.config["heartbeat_interval"]
        self.heartbeat_timer = None
        self.election_timer = None
        self.proxy_timer = None
        # dict of log_index: addr where log_index is the index a client is
        # waiting to be commited
        self.client_callbacks = {}
        self.leader_id = None
        self.current_behavior = self.update_behavior()
        self.restart_election_timer()
        
    def handle_client_request(self, req):
        """
        Handle ClientRequest messages to run a command. Append the command to
        the log. If this is not the leader deny the request and redirect.
        Replication will happen for the entry on the next HeartbeatRequest.
        """
        if self.state.status != RaftState.LEADER:
            client_res = ClientResponse(
                f"NotLeader: reconnect to {self.network.config['cluster'].get(self.leader_id, '?')}"
            )
            self.network.send(tuple(req.sender), client_res)
            return

        prev_index = len(self.state.log) - 1
        prev_term = self.state.log[prev_index].term if prev_index >= 0 else -1
        entries = [LogEntry(self.state.current_term, req.command)]

        # append to our own log
        success = self.state.append_entries(prev_index, prev_term, entries)
        if not success:
            raise Exception("This shouldn't happen!")
        self.log(f"append_entries success={success} entries={entries}")

        # update leaders match/next index
        match_index = len(self.state.log) - 1
        self.state.match_index[self.node_id] = match_index
        self.state.next_index[self.node_id] = match_index + 1

        # add client addr to callbacks so we can notify it of the result once
        # it's been commited
        self.client_callbacks[match_index] = tuple(req.sender)
        self.state.life_time = self.get_lifetime()
        print(f'{bcolors.WARNING} DECREASING LIFE_TIME. CURRENT: {self.state.life_time}{bcolors.ENDC}')
        # self.phase_behavior()



    def get_lifetime(self) -> float:
        value = self.measure()
        self.bucket.consume(value)
        return self.capacity - self.bucket.value

    def measure(self) -> float:
        with Measure() as measure:
            delta = measure.take_snapshot_delta()
            if self.field not in delta:
                raise ValueError("Field not found (%s)" % self.field)
            
            value = delta[self.field]

        # print(value)
        
        return value

    def handle_append_entries_request(self, req):
        self.restart_election_timer()
        # print(req.sender)
        if self.state.status == RaftState.LEADER:
            return 
        
        if req.term > self.state.current_term:
            self.state.current_term = req.term

        # so follower can redirect clients            
        if self.leader_id != req.sender:
            self.leader_id = req.sender

        # Reply false if term < currentterm (§5.1)
        if req.term < self.state.current_term :
            res = AppendEntriesResponse(
                self.node_id, self.state.current_term, False, len(self.state.log) - 1, self.state.life_time
            )
            self.network.send(req.sender, res)
            return
        
        entries = [LogEntry(e[0], e[1]) for e in req.entries]
        # Reply false if log doesn’t contain an entry at prevLogIndex whose term matches prevLogTerm (§5.3)
        # If an existing entry conflicts with a new one (same index but different terms), delete the existing entry and all that follow it (§5.3)
        # Append any new entries not already in the log attempt to apply the entry to the log
        success = self.state.append_entries(req.prev_index, req.prev_term, entries)
        if entries:
            self.log(f"append_entries success={success} entries={entries}")

        if success:
            match_index = len(self.state.log) - 1
            if req.commit_index > self.state.commit_index:
                self.state.commit_index = min(req.commit_index, match_index)
                self.log(f"commit_index updated to {self.state.commit_index}")
        else:
            match_index = 0

        res = AppendEntriesResponse(
            self.node_id, self.state.current_term, success, match_index, self.state.life_time
        )
        self.network.send(req.sender, res)
        self.apply_any_commits()

    def handle_append_entries_response(self, res):
        if self.state.status == RaftState.FOLLOWER:
            return
        
        
        sender = res.sender
        if res.success:
            self.state.match_index[sender] = max(
                res.match_index, self.state.match_index[sender]
            )
            self.state.next_index[sender] = self.state.match_index[sender] + 1
            self.state.proxy_candidates[sender] = res.life_time
        else:
            self.state.next_index[sender] = max(0, self.state.next_index[sender] - 1)

        if self.state.match_index[sender] != len(self.state.log) - 1:
            append_entries_msg = AppendEntriesRequest.from_raft_state(
                self.node_id, sender, self.state
            )
            self.network.send(sender, append_entries_msg)

        consensus_check_idx = self.state.match_index[sender]
        if (
                self.has_consensus(consensus_check_idx)
                and consensus_check_idx > -1
                and self.state.log[consensus_check_idx].term == self.state.current_term
                and self.state.commit_index < consensus_check_idx
        ):
            self.state.commit_index = self.state.match_index[sender]
            self.log(
                f"consensus reached on {self.state.commit_index}: {self.state.log[self.state.commit_index]}"
            )

        self.apply_any_commits()

    def handle_vote_request(self, req):
        self.restart_election_timer()
        if req.life_time <= self.state.life_time:
            vote_msg = VoteResponse(self.node_id, self.state.current_term, False, self.state.life_time)
            self.log(f"vote request from {req.candidate}:{req.life_time} granted=False (candidate life_time lower than my self: {self.state.life_time})" )
            self.network.send(req.candidate, vote_msg)
            return

        if (req.life_time > self.state.life_time and 
            self.state.status != RaftState.FOLLOWER or self.state.status != RaftState.PROXY ):
            self.state.current_term = req.term
            self.demote()

        last_log_index = len(self.state.log) - 1
        last_log_term = (self.state.log[last_log_index].term if last_log_index >= 0 else -1 )
        # votedFor is null or candidateId, and candidate’s log is atleast as up-to-date
        # as receiver’s log, grant vote (§5.2, §5.4)
        if (self.state.voted_for is None  or self.state.voted_for == req.candidate
                and (req.life_time > self.state.life_time)):
            vote_msg = VoteResponse(self.node_id, self.state.current_term, True, self.state.life_time)
            self.state.voted_for = req.candidate
            self.log(f"vote request from {req.candidate} granted=True")
            self.network.send(req.candidate, vote_msg)
            return

        # is this ok to default to?
        self.log(
            f"vote request from {req.candidate} granted=False (vote already granted or life_time lower than self {self.state.life_time})"
        )
        vote_msg = VoteResponse(self.node_id, self.state.current_term, False, self.state.life_time)
        self.network.send(req.candidate, vote_msg)

    def handle_vote_response(self, res):
        if res.life_time > self.state.life_time:
            self.demote()

        if self.state.status != RaftState.CANDIDATE:
            # either already the leader or have been demoted
            return

        if res.vote_granted:
            self.state.votes.add(res.sender)

        if len(self.state.votes) > (len(self.peers) + 1) // 2:
            self.log(
                f"{bcolors.OKCYAN} majority of votes granted {self.state.votes}, transitoning to leader with {self.state.life_time} autonomy{bcolors.ENDC}"
            )
            self.promote()

    def handle_heartbeat_request(self, req):
        """
        HEARTBEAT garante que:
            A cada ciclo, os followers devem extender o mandato do lider.
            Caso um seguidor não receba o heartbeat dentro da tolerancia
            uma nova eleicao acontece.
            Isso acontece porque ele manda uma entrada simples vazia para
            para cada seguidor que por sua vez extende o prazo do lider.
        """    
        dest = self.peers[:]
        if self.proxy_id:
            dest = [self.proxy_id]
        elif self.state.status == RaftState.PROXY:   
            dest.remove(self.leader_id)
         
        for peer in dest:
            append_entries_msg = AppendEntriesRequest.from_raft_state(
                self.node_id, peer, self.state
            )

            if req.empty:
                append_entries_msg.entries = []
            self.network.send(peer, append_entries_msg)
        
        target = lambda addr: self.network.send(addr, HeartbeatRequest())    
        self.heartbeat_timer = Timer(
            self.heartbeat_interval, target, args=[self.node_id]
        )
        self.heartbeat_timer.start()
       
            
    def handle_heartbeat_update(self, req):   
        if req.mode:
            self.heartbeat_interval = self.network.config["heartbeat_interval"] + SLOWHEARTBEAT
        else:
            self.heartbeat_interval = self.network.config["heartbeat_interval"]       
        self.restart_election_timer()
        print(f"{bcolors.WARNING}Atualizei meu heartbeat-tolerancia para {self.heartbeat_interval}{bcolors.ENDC}")
            
    def advice_peers(self):
        senders = self.peers
        for peer in senders:
            print(f"mandando heatbeat para o peer {peer}")
            self.network.send(peer, HeartbeatUpdate(self.state.phase != RaftState.PHASE1))
                        
    def handle_election_request(self, req):
        self.log(
            f"haven't heard from leader or election failed; beginning election. Lifetime is: {self.state.life_time} and current phase is: {self.state.phase}")
        self.state.become_candidate(self.node_id, self.state.life_time)
        prev_index = len(self.state.log) - 1
        if prev_index >= 0:
            prev_term = self.state.log[prev_index].term
        else:
            prev_term = -1

        self.restart_election_timer()
        for peer in self.peers:
            vote_msg = VoteRequest(
                self.state.current_term, self.node_id, prev_index, prev_term, self.state.life_time
            )
            self.network.send(peer, vote_msg)

    def has_consensus(self, indx):
        """
        Assuming a 5 node cluster with a matched index like:
            [1, 3, 2, 3, 3]
        We sort it to get:
            [1, 2, 3, 3, 3]
        Next we get the middle value (3) which gives us an index guarenteed to
        be on a majority of the servers logs.
        """
        sorted_matched_idx = sorted(self.state.match_index.values())
        if self.proxy_id:
            sorted_matched_idx = sorted_matched_idx[-2:]
        
        commited_idx = sorted_matched_idx[(len(sorted_matched_idx) - 1) // 2]
        return commited_idx >= indx
    

    def apply_any_commits(self):
        # If commitIndex > lastApplied: increment lastApplied,
        # applylog[lastApplied] to state machine (§5.3)
        
        while self.state.commit_index > self.state.last_applied:
            log_entry = self.state.log[self.state.last_applied + 1]
            try:
                result = self.state_machine.apply(log_entry.item)
            except Exception as ex:
                result = repr(ex)
            self.state.last_applied += 1
            self.log(f"applied {log_entry.item} to state machine: {result}")

            # notify the client of the result
            if self.state.status != RaftState.LEADER:
                return
            if (
                    self.state.status == RaftState.LEADER
                    and self.client_callbacks.get(self.state.last_applied) is not None
            ):
                client_addr = self.client_callbacks.pop(self.state.last_applied)
                self.network.send(client_addr, ClientResponse(result))
                

    def promote(self):
        self.state.become_leader(self.peers + [self.node_id])
        heartbeat_request = HeartbeatRequest(empty=True)
        self.election_timer.cancel()
        # should we skip the send to ourself and just invoke?
        self.network.send(self.node_id, heartbeat_request)


    def demote(self):
        self.log("reverting to follower")
        if self.heartbeat_timer is not None:
            self.heartbeat_timer.cancel()
        self.state.become_follower()
        self.restart_election_timer()
        self.proxy_id = None
        
        
    def handle_proxy_election_response(self, res):
        self.proxy_id = res.candidate
        self.log(f"Novo Proxy escolhido! {res.candidate}") 
                   
            
    def handle_proxy_election_request(self, req):
        self.state.become_proxy()
  
        self.state.match_index = dict(req.state[0])
        self.state.next_index = dict(req.state[1])
        self.state.current_term = req.state[2]
        self.state.commit_index = req.state[3] 
        self.state.last_applied = req.state[4]
        
        
        heartbeat_request = HeartbeatRequest(empty=True)
        self.election_timer.cancel()
        # should we skip the send to ourself and just invoke?
        # heartbeat(proxy) 
        self.network.send(self.node_id, heartbeat_request)
       
        for peer in self.peers:
            msg = ProxyElectionResponse(self.node_id)
            self.network.send(peer, msg)
        
        
  
    def start_proxy_election(self):
        candidate = max(self.state.proxy_candidates, 
                        key=self.state.proxy_candidates.get)
        self.proxy_id = candidate
        self.heartbeat_timer.cancel()
        heartbeat_request = HeartbeatRequest(empty=True)
        self.network.send(self.node_id, heartbeat_request)
        # self.state.copy_state_proxy()
        self.network.send(candidate, ProxyElectionRequest(self.node_id, self.state.copy_state_proxy()))
              

    def restart_election_timer(self):
        if self.election_timer is not None:
            self.election_timer.cancel()

        target = lambda addr: self.network.send(addr, ElectionRequest())
        base_interval = self.heartbeat_interval * 50
        interval = base_interval + random.random() * base_interval

        self.election_timer = Timer(interval, target, args=[self.node_id])
        self.election_timer.start()

    def handle_destroy(self):
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        if self.election_timer:
            self.election_timer.cancel()

    def log(self, msg):
        logger.info(msg, extra={"node_id": self.node_id})
        
    
    def update_behavior(self):                 
        current_behavior = (self.state.status, self.state.phase)
        print(f'Name: {self.node_id} BEHAVIOR: {current_behavior}')
        self.execute_behavior(current_behavior)
        return current_behavior
    
    def execute_behavior(self, current_behavior):    
        role = current_behavior[0]
        match role:
            case RaftState.LEADER:
                if self.state.phase == RaftState.PHASE1:
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE2:    
                    # Reduzindo Heartbeats e Avisando Followers                
                    self.advice_peers()
                    pass
                if self.state.phase == RaftState.PHASE3:
                    ### Eleger proxy e passar a comunicar apenas com o proxy
                    self.start_proxy_election() 
                    print("Convocando um proxy")
                if self.state.phase == RaftState.PHASE4:
                    # Vai retornar para o estado de seguidor e se desligar.
                    self.demote()
                    print("Desligando")
        
                                   
            case RaftState.PROXY:
                print ("Aqui vai a logica de proxy")
                # self.advice_peers()
                if self.state.phase == RaftState.PHASE1:
                    # Enviar Heartbeat para nodes
                    # Reencaminhar mensagens Leader -> Proxy -> Followers
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE2:
                    # Enviar Heartbeat para nodes
                    # Reencaminhar mensagens Leader -> Proxy -> Followers
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE3:
                    # Enviar Heartbeat para nodes
                    # Reencaminhar mensagens Leader -> Proxy -> Followers
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE4:
                    # Avisar ao líder do seu desligamento (o líder deve designar um novo proxy), retornar para papel de seguidor e se desligar
                    print("desligando")
                    

            case RaftState.FOLLOWER:
                self.proxy_id = None
                print ("Aqui vai a logica de seguidor")
                if self.state.phase == RaftState.PHASE1:
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE2:
                    # Em operação normal
                    pass
                if self.state.phase == RaftState.PHASE3:
                    # Em modo de suspensão (líder ou proxy não envia heartbeat e appendEntries para seguidor suspenso, 
                    # Apenas quando a quantidade de nós ativos não é suficiente para obter consenso (PODE DEIXAR POR ÚLTIMO)
                    print("suspension mode")
                if self.state.phase == RaftState.PHASE4:
                    # Avisar ao líder do seu desligamento e se desligar
                    print("desligando")
                
            case _ : print("Não identificado")
          
          
        
       

    def __repr__(self):
        return f"""\
<RaftNode {self.node_id} [{self.state.status}]
    current_term: {self.state.current_term}
    voted_for: {self.state.voted_for}
    votes: {self.state.votes}
    commit_index: {self.state.commit_index}
    last_applies: {self.state.last_applied}
    match_index: {self.state.match_index}
    next_index: {self.state.next_index}
    log:{self.state.log}
    life_time: {self.state.life_time}
>"""
