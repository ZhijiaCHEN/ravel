from mininet.topo import Topo
from ravel.log import logger
import os, sys

class FattreeTopo( Topo ):
    "Fat tree topology with k pods."

    def build( self, k=4, **_opts ):
        try:
            self.size = int(k)
            if self.size <= 0 or self.size%2 != 0:
                raise ValueError
        except ValueError:
            print('The pod number of fat tree must be a positive even number!')
            return

        cores = (self.size/2)**2
        aggs = (self.size/2) * self.size
        edges = (self.size/2) * self.size
        hosts = (self.size/2)**2 * self.size

        switches = {}

        for pod in range(0, self.size):
            agg_offset = cores + self.size/2 * pod
            edge_offset = cores + aggs + self.size/2 * pod
            host_offset = cores + aggs + edges + (self.size/2)**2 * pod

            for agg in range(0, self.size/2):
                core_offset = agg * self.size/2
                aggname = "s{0}".format(agg_offset + agg)
                agg_sw = self.addSwitch(aggname)
                switches[aggname] = agg_sw

                # connect core and aggregate switches
                for core in range(0, self.size/2):
                    corename = "s{0}".format(core_offset + core)
                    core_sw = self.addSwitch(corename)
                    switches[corename] = core_sw
                    self.addLink(agg_sw, core_sw)

                # connect aggregate and edge switches
                for edge in range(0, self.size/2):
                    edgename = "s{0}".format(edge_offset + edge)
                    edge_sw = self.addSwitch(edgename)
                    switches[edgename] = edge_sw
                    self.addLink(agg_sw, edge_sw)

            # connect edge switches with hosts
            for edge in range(0, self.size/2):
                edgename = "s{0}".format(edge_offset + edge)
                edge_sw = switches[edgename]

                for h in range(0, self.size/2):
                    hostname = "h{0}".format(host_offset + self.size/2 * edge + h)
                    hostobj = self.addHost(hostname)
                    self.addLink(edge_sw, hostobj)


class ISPTopo( Topo ):
    "ISP topology identified by its AS number"

    def build( self, k, **_opts ):
        self.asNumLst=[]
        pyPath = os.path.dirname(os.path.abspath(__file__))
        self.ISPTopoPath = os.path.join(pyPath, 'ISP_topo')
        try:
            asNumFile = open(os.path.join(self.ISPTopoPath, 'stat.txt'))
            asNumFile.readline()
            for line in asNumFile:
                for word in line.split():
                    self.asNumLst.append(int(word))
                    break
        except Exception, e:
            logger.error('unable to parse stat file: %s', e)
            return

        self.asNum = int(k)
        if self.asNum not in self.asNumLst:
            print('Invalid AS number: {0}!'.format(self.asNum))
            print('Please use the following available AS number:')
            for i in self.asNumLst:
                print(i)
            raise Exception

        switches = {}
        nodeMp = {}
        sidLst = []
        nidLst = []
        nodeNmLst = []

        nodeFileNm = '{0}_nodes.txt'.format(self.asNum)
        edgeFileNm = '{0}_edges.txt'.format(self.asNum)
        try:
            nodeFile = open(os.path.join(self.ISPTopoPath, nodeFileNm))
        except Exception, e:
            logger.error('Unable to open nodes file: %s', e)
            return
        try:
            edgeFile = open(os.path.join(self.ISPTopoPath, edgeFileNm))
        except Exception, e:
            logger.error('Unable to open edges file: %s', e)
            return

        for line in nodeFile:
            for word in line.split():
                try:
                    nodeMp[int(word)] = 's{0}'.format(word)
                    nodeNmLst.append('s{0}'.format(word))
                except Exception, e:
                    logger.error("Unable to parse node number '{0}': ".format(word))
                    return
                break 

        for line in edgeFile:
            line=line.rstrip()
            words = line.split()
            if len(words) != 2:
                logger.error("Unrecognized format of edges file!")
                raise Exception
            try:
                if int(words[0]) not in nodeMp.keys():
                    logger.error("An edge connects to a nonexist switch {0} that is not exist!".format(words[0]))
                    raise Exception
                if int(words[1]) not in nodeMp.keys():
                    logger.error("An edge connects to a nonexist switch {0} that is not exist!".format(words[1]))
                    raise Exception
                sidLst.append(int(words[0]))
                nidLst.append(int(words[1]))
            except ValueError, e:
                logger.error("Unable to parse edge from switch '{0}' to switch '{1}'".format(words[0],words[1]))
                return None
        
        for sw in nodeNmLst:
            switches[sw] = self.addSwitch(sw)

        for i in range(len(sidLst)):
            self.addLink(switches[nodeMp[sidLst[i]]], switches[nodeMp[nidLst[i]]])

topos = { 'fattree' : FattreeTopo, 'isp': ISPTopo}