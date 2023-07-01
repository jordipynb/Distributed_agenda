import zmq
import channel #-
import random, math #-
from constChord import * #-
from utils import *
import json 
import threading
import time

class ChordNode:

    def __init__(self,chan_address,address:Address):
        self.address=address
        self.chan_address = chan_address
        self.nodeSet = []                           # Nodes discovered so far
        self.nodeID = 0
        self.nBits = 0
        self.FT = None
        self.MAXPROC = 0 
        self.node_address = {}
    
    def inbetween(self, key, lwb, upb):                                         
        if lwb <= upb:                                                            
            return lwb <= key < upb                                                                                                         
        return (lwb <= key and key < upb + self.MAXPROC) or (lwb <= key + self.MAXPROC and key < upb)                        
    
    def addNode(self, nodeID):                                                  
        self.nodeSet.append(int(nodeID))                                         
        self.nodeSet = list(set(self.nodeSet))                                    
        self.nodeSet.sort()     
        self.FT = []    

    def delNode(self, nodeID):                                                  
        assert nodeID in self.nodeSet, ''                                         
        del self.nodeSet[self.nodeSet.index(nodeID)]                              
        self.nodeSet.sort() 

    def finger(self, i):
        succ = (self.nodeID + pow(2, i-1)) % self.MAXPROC    # succ(p+2^(i-1))
        lwbi = self.nodeSet.index(self.nodeID)               # own index in nodeset
        upbi = (lwbi + 1) % len(self.nodeSet)                # index next neighbor
        for k in range(len(self.nodeSet)):                   # go through all segments
            if self.inbetween(succ, self.nodeSet[lwbi]+1, self.nodeSet[upbi]+1):
                return self.nodeSet[upbi]                        # found successor
            (lwbi,upbi) = (upbi, (upbi+1) % len(self.nodeSet)) # go to next segment
        return None                                                                
    
    def recomputeFingerTable(self):
        self.FT[0]  = self.nodeSet[self.nodeSet.index(self.nodeID)-1] # Predecessor
        self.FT[1:] = [self.finger(i) for i in range(1,self.nBits+1)] # Successors

    def localSuccNode(self, key): 
        if self.inbetween(key, self.FT[0]+1, self.nodeID+1): # key in (FT[0],self]
            return self.nodeID                                 # node is responsible
        elif self.inbetween(key, self.nodeID+1, self.FT[1]): # key in (self,FT[1]]
            return self.FT[1]                                  # successor responsible
        for i in range(1, self.nBits+1):                     # go through rest of FT
            if self.inbetween(key, self.FT[i], self.FT[(i+1) % self.nBits]):
                return self.FT[i]                                # key in [FT[i],FT[i+1])
    

    def join(self):

        print("Connecting to Channel Server")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        #self.socket.bind(str(self.address))
        socket.connect(str(self.chan_address))
        
        #Send a message to join to the network
        print("Sending Message")
        data = {"message": JOIN, "ip": self.address.ip , "port": self.address.port}
        message = json.dumps(data).encode("utf-8")
        socket.send(message)

        #  Get the reply.
        message = socket.recv()
        data=json.loads(message.decode("utf-8"))

        #unpacking data
        self.nodeID =data["nodeID"]
        self.nBits = data["nBits"]
        addresses = data["addresses"]
        self.nodeSet = data["nodes_ID"]

        #notify data
        print("Joined to an %s chord network as node %s" % (self.nBits,self.nodeID))
        print("Discovered nodes %s" % (self.nodeSet))

        #building node_address dict
        self.node_address = {self.nodeSet[i]:Address(addresses[i][0],addresses[i][1]) for i in range(len(self.nodeSet))}


        self.MAXPROC = pow(2, self.nBits)

        #Inicializing Finger Table
        self.FT = [None for i in range(self.nBits+1)]
        
        #Computing Finger Table
        self.recomputeFingerTable()
        print("Finger Table %s " % (self.FT))

        #Notify other nodes
    
    def run(self):
        #Receiving requests
        while True:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            message = socket.recv()
            data=json.loads(message.decode("utf-8"))
            request = data["message"]
            ip = data["ip"]
            port = data["port"]
            if request[0] == STOP: 
                break 
            if request[0] == LOOKUP_REQ:                       # A lookup request #-
                nextID = self.localSuccNode(request[1])          # look up next node #-
                socket = context.socket(zmq.REQ)
                socket.connect(str(self.chan_address))
                data = {"message": (LOOKUP_REQ,request[1]), "address": str(self.node_address[nextID])} # send to succ #-
                if not self.chan.exists(nextID):
                    self.delNode(nextID) 


node= ChordNode(Address("localhost","5555"),Address("localhost","5270"))
mi_hilo = threading.Thread(target=node.join())

time.sleep(2)
node= ChordNode(Address("localhost","5555"),Address("localhost","8888"))
mi_hilo = threading.Thread(target=node.join())

time.sleep(2)
node= ChordNode(Address("localhost","5555"),Address("localhost","49152"))
mi_hilo = threading.Thread(target=node.join())

time.sleep(2)
node= ChordNode(Address("localhost","5555"),Address("localhost","8000"))
mi_hilo = threading.Thread(target=node.join())

