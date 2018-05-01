"""
Reset ravel's underlying topology under onlydb mode.
"""
from distutils.util import strtobool
from ravel.app import AppConsole
import ravel.mndeps
from ravel.log import logger
import xml.etree.ElementTree as ET
import os
class ToporesetConsole(AppConsole):
    def init(self):
        self.asNumLst=[]
        pyPath = os.path.dirname(os.path.abspath(__file__))
        self.ISPTopoPath = os.path.join(pyPath, 'ISP_topo')
        try:
            asNumFile = open(os.path.join(self.ISPTopoPath, 'stat'))
            asNumFile.readline()
            for line in asNumFile:
                for word in line.split():
                    self.asNumLst.append(int(word))
                    break
        except Exception, e:
            logger.warning('unable to parse AS number file: %s', e)

    def __clear_database__(self):
        try:
            self.db.cursor.execute("truncate rm, cf, tp, hosts, switches, ports;")
            #clean nodes caches in network provider
            self.env.provider.cache_name = {}
            self.env.provider.cache_id = {}
            return True
        except Exception, e:
            logger.error(e)
            return False

    def addHost(self, hostID, hostName, **kwargs):
        try:
            self.db.cursor.execute("INSERT INTO hosts(hid, name) VALUES({0}, '{1}')".format(hostID,hostName))
        except Exception, e:
            logger.error(e)

    def addHosts(self, hostIDLst, hostNameLst):
        if len(hostIDLst) != len(hostNameLst):
            logger.error("host id list and host name list mush be of the same length!")
            return
        if len(hostIDLst) == 0:
            return
        sqlStr = "INSERT INTO hosts(hid, name) VALUES" 
        for i in range(len(hostIDLst)):
            sqlStr += "({0}, '{1}'),".format(hostIDLst[i], hostNameLst[i])
        try:
            self.db.cursor.execute(sqlStr[:-1])
            if len(hostIDLst)>1:
                logger.info("{0} hosts inserted.".format(len(hostIDLst)))
            else:
                logger.info("1 host inserted.")
            #cache nodes after switches inserted into database, otherwise, there might be inconsistency
            self.cacheNodes(hostIDLst, hostNameLst)
        except Exception, e:
            logger.error(e)

    def addSwitches(self, switchIDLst, switchNameLst):
        if len(switchIDLst) != len( switchNameLst):
            logger.error("switch id list and switch name list mush be of the same length!")
            return
        if len(switchIDLst) == 0:
            return
        sqlStr = "INSERT INTO switches(sid, name) VALUES" 
        for i in range(len(switchIDLst)):
            sqlStr += "({0}, '{1}'),".format(switchIDLst[i], switchNameLst[i])
        try:
            self.db.cursor.execute(sqlStr[:-1])
            if len(switchIDLst)>1:
                logger.info("{0} switches inserted.".format(len(switchIDLst)))
            else:
                logger.info("1 switch inserted.")
            #cache nodes after switches inserted into database, otherwise, there might be inconsistency
            self.cacheNodes(switchIDLst, switchNameLst)
        except Exception ,e:
            logger.error(e)

    def cacheNodes(self, nodeIdlst, nodeNmLst):
        if len(nodeIdlst) != len(nodeNmLst):
            logger.error("Failed to cache nodes, dimension of nodes' name and nodes' id unmatched.")
            return
        """Cache node-name mapping in memory from database"""
        for i in range(len(nodeIdlst)):
            self.env.provider.cache_name[nodeNmLst[i]] = nodeIdlst[i]
            self.env.provider.cache_id[nodeIdlst[i]] = nodeNmLst[i]
        
    def addlinks(self, sidLst, nidLst, isHostLst):
        if len(sidLst) != len( isHostLst) or len(nidLst) != len( isHostLst):
            logger.error("sid list, nid list and isHost list mush be of the same length!")
            return
        if len(isHostLst) == 0:
            return
        sqlStr = "INSERT INTO tp(sid, nid, ishost, isactive) VALUES" 
        for i in range(len(isHostLst)):
            sqlStr += " ({0}, {1}, {2}, 1),".format(sidLst[i], nidLst[i], isHostLst[i])
        try:
            self.db.cursor.execute(sqlStr[:-1])
            if len(isHostLst)>1:
                logger.info("{0} links inserted.".format(len(isHostLst)))
            else:
                logger.info("1 link inserted.")
        except Exception ,e:
            logger.error(e)

    def do_echo(self, line):
        "Test command, echo arguments"
        print "new ", self.__class__.__name__, "says:", line

    def do_resetTopo(self, line):
        if(not self.env.opts.onlydb):
            print "This application only runs under onlydb mode."
            return
        topo = ravel.mndeps.build(line)
        if(topo is None):
            print "Invalid mininet topology: ", topo
            return
        self.topo = topo
        self.env.stop()
        self.db.init()
        self.db.cleaned = True
        self.env.provider.topo = topo
        self.env.start()

#We should unify the way to build a topology. The following two methods should be made as available topologies for mndeps module to build.
"""
    def do_load_fattree(self, line):
        size = int(line)
        self.__clear_database__()
        cores = (size/2)**2
        aggs = (size/2) * size
        edges = (size/2) * size
        hosts = (size/2)**2 * size
        swIDLst = range((size/2)**2+size**2)
        swNmLst = [None]*len(swIDLst)
        hostIDLst = range((size/2)**2+size**2,(size/2)**2+size**2+size*(size/2)**2)
        hostNmLst = [None]*len(hostIDLst)
        swNmOffset = -1
        hostNmOffset =(size/2)**2+size**2-1
        sidLst = []
        nidLst = []
        isHostLst = [] 
        for pod in range(0, size):
            agg_offset = cores + size/2 * pod
            edge_offset = cores + aggs + size/2 * pod
            host_offset = cores + aggs + edges + (size/2)**2 * pod
            for agg in range(0, size/2):
                core_offset = agg * size/2
                aggID = agg_offset + agg
                aggname = "s{0}".format(aggID + 1)
                swNmLst[aggID] = aggname
                for core in range(0, size/2):
                    coreID = core_offset+core
                    corename = "s{0}".format(coreID+1)
                    swNmLst[coreID]=corename
                    #core_sw = addSwitd2dch(corename)
                    #switches[corename] = core_sw
                    sidLst.append(aggID)
                    nidLst.append(coreID)
                    isHostLst.append(0)
                    #print "addLink({0},{1})".format(aggname, corename)
                    #linknum += 1

                # connect aggregate and edge switches
                for edge in range(0, size/2):
                    edgeID = edge_offset+edge
                    edgename = "s{0}".format(edgeID+1)
                    swNmLst[edgeID]=edgename
                    #edge_sw = addSwitch(edgename)
                    #switches[edgename] = edge_sw
                    sidLst.append(aggID)
                    nidLst.append(edgeID)
                    isHostLst.append(0)
                    #print "addLink({0},{1})".format(aggname, edgename)
                    #linknum += 1
            # connect edge switches with hosts
            for edge in range(0, size/2):
                edgeID = edge_offset+edge
                edgename = "s{0}".format(edgeID+1)
                #edge_sw = switches[edgename]
                for h in range(0, size/2):
                    hostID = host_offset+size/2*edge+h
                    hostname = "h{0}".format(hostID-hostNmOffset)
                    hostNmLst[hostID-hostNmOffset-1]=hostname
                    #hostobj = addHost(hostname)
                    #addLink(edge_sw, hostobj)
                    sidLst.append(edgeID)
                    nidLst.append(hostID)
                    isHostLst.append(1)
                    #print "addLink({0},{1})".format(edgename, hostname)
                    #linknum += 1
        self.addHosts(hostIDLst, hostNmLst)
        self.addSwitches(swIDLst, swNmLst)
        self.addlinks(sidLst, nidLst, isHostLst)

    def do_load_ISPTopo(self, line):
        self.__clear_database__()
        self.init()
        if len(self.asNumLst) == 0:
            print 'entering if statement'
            logger.warning('No AS number exist.')
            return
        try:
            asNum = int(line)
        except:
            logger.info('Please enter a number of the available AS number list: '+str(self.asNumLst))
            return
        if asNum not in self.asNumLst:
            logger.info('Please enter a number of the available AS number list: '+str(self.asNumLst))
            return
        nodeLst=[]
        nodeNmLst=[]
        sidLst=[]
        nidLst=[]

        nodeFileNm = '{0}_nodes.txt'.format(asNum)
        edgeFileNm = '{0}_edges.txt'.format(asNum)
        try:
            nodeFile = open(os.path.join(self.ISPTopoPath, nodeFileNm))
        except Exception, e:
            logger.error('Unable to open nodes file: ', e)
            return
        try:
            edgeFile = open(os.path.join(self.ISPTopoPath, edgeFileNm))
        except Exception, e:
            logger.error('Unable to open edges file: ', e)
            return
        for line in nodeFile:
            for word in line.split():
                try:
                    nodeLst.append(int(word))
                    nodeNmLst.append('s{0}'.format(word))
                except Exception, e:
                    logger.warning("Unable to parse node number '{0}': ".format(word), e)
                break 
        for line in edgeFile:
            line=line.rstrip()
            words = line.split()
            if len(words) < 2:
                logger.error("Unrecognized format of edges file!")
                return
            try:
                sidLst.append(int(words[0]))
                nidLst.append(int(words[1]))
            except Exception, e:
                logger.warning("Unable to parse '{0}' and '{1}' as sid and nid: ".format(words[0],words[1]), e)
        self.addSwitches(nodeLst, nodeNmLst)
        self.addlinks(sidLst, nidLst, [0]*len(sidLst))
"""
shortcut = "tprst"
description = "Reset ravel's underlying topology under onlydb mode."
console = ToporesetConsole




