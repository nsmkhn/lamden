from cilantro.protocol.overlay.kademlia.network import Network
from cilantro.protocol.overlay.auth import Auth
from cilantro.protocol.overlay.discovery import Discovery
from cilantro.protocol.overlay.handshake import Handshake
from cilantro.protocol.overlay.ip import *
from cilantro.protocol.overlay.kademlia.utils import digest
from cilantro.protocol.overlay.ip import get_public_ip
from cilantro.constants.overlay_network import *
from cilantro.logger.base import get_logger
from cilantro.storage.db import VKBook
from cilantro.protocol.overlay.kademlia.node import Node
import asyncio, os
from enum import Enum, auto

class OverlayInterface:
    def __init__(self, sk_hex):
        self.log = get_logger('OverlayInterface')
        Auth.setup_certs_dirs(sk_hex=sk_hex)
        self.loop = asyncio.get_event_loop()
        self.network = Network(storage=None)
        self.loop.run_until_complete(asyncio.gather(
            Discovery.listen(),
            Handshake.listen(),
            self.network.listen(),
            self.run_tasks()
        ))

    @property
    def neighbors(self):
        return {item[2]: Node(node_id=digest(item[2]), ip=item[0], port=item[1], vk=item[2]) \
            for item in self.network.bootstrappableNeighbors()}

    @property
    def authorized_nodes(self):
        return Handshake.authorized_nodes

    async def run_tasks(self):
        await self.discover()
        self.log.success('''
###########################################################################
#   DISCOVERY COMPLETE
###########################################################################\
        ''')
        await self.bootstrap()
        self.log.success('''
###########################################################################
#   BOOTSTRAP COMPLETE
###########################################################################\
        ''')
        await asyncio.sleep(5) # TODO Change this
        await asyncio.gather(*[
            self.authenticate(vk) for vk in VKBook.get_all()
        ])
        self.log.success('''
###########################################################################
#   AUTHENTICATION COMPLETE
###########################################################################\
        ''')

    async def discover(self):
        while True:
            if await Discovery.discover_nodes(Discovery.host_ip):
                break
            else:
                self.log.critical('''
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
x   DISCOVERY FAILED: Cannot find enough nodes ({}/{}) and not a masternode
x       Retrying...
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                '''.format(len(Discovery.discovered_nodes), MIN_BOOTSTRAP_NODES))

    async def bootstrap(self):
        addrs = [(Discovery.discovered_nodes[vk], self.network.port) \
            for vk in Discovery.discovered_nodes]
        await self.network.bootstrap(addrs)
        self.network.cached_vks.update(self.neighbors)

    async def authenticate(self, vk, domain='all'):
        ip = await self.lookup_ip(vk)
        if not ip:
            self.log.critical('Authentication Failed: Cannot find ip for vk={}'.format(vk))
            return
        return await asyncio.gather(*[
            Handshake.initiate_handshake(ip, vk, domain)
        ])

    async def lookup_ip(self, vk):
        return await self.network.lookup_ip(vk)
