from mininet.topo import Topo
from ravel.log import logger

class FattreeTopo( Topo ):
    "Fat tree topology with k pods."

    def build( self, k=4, **_opts ):
        try:
            self.size = int(k)
            if self.size <= 0 or self.size%2 != 0:
                raise ValueError
        except ValueError:
            logger.error('The pod number of fat tree must be a positive even number!')

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
topos = { 'fattree' : FattreeTopo }