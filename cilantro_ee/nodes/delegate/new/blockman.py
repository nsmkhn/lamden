from cilantro_ee.services.storage.vkbook import VKBook
from cilantro_ee.services.storage.state import MetaDataStorage
from cilantro_ee.core.networking.parameters import ServiceType, NetworkParameters
from cilantro_ee.core.sockets.services import AsyncInbox

from cilantro_ee.core.messages.message import Message
from cilantro_ee.core.messages.message_type import MessageType

from cilantro_ee.core.crypto.wallet import _verify

from contracting.client import ContractingClient
from contracting.stdlib.bridge.decimal import ContractingDecimal
from contracting.stdlib.bridge.time import Datetime

import time
import asyncio
import heapq
from datetime import datetime


class NBNInbox(AsyncInbox):
    def __init__(self, *args, **kwargs):
        self.q = []
        super().__init__(*args, **kwargs)

    def handle_msg(self, _id, msg):
        # Make sure it's legit

        # See if you can store it in the backend?
        pass

    async def wait_for_next_nbn(self):
        while len(self.q) <= 0:
            await asyncio.sleep(0)

        nbn = self.q.pop(0)
        self.q.clear()

        return nbn


class WorkInbox(AsyncInbox):
    def __init__(self, validity_timeout, *args, **kwargs):
        self.q = []
        self.validity_timeout = validity_timeout
        super().__init__(*args, **kwargs)

    def handle_msg(self, _id, msg):
        msg_type, msg_struct = Message.unpack_message_2(msg)

        # Ignore everything except TX Batches
        if msg_type != MessageType.TRANSACTION_BATCH:
            return

        # Ignore if the tx batch is too old
        if time.time() - msg_struct.timestamp > self.validity_timeout:
            return

        # Ignore if the tx batch is not signed by the right sender
        if not _verify(vk=msg_struct.sender,
                       signature=msg_struct.signature,
                       msg=msg_struct.inputHash):
            return

        self.q.append(msg_struct)

    async def wait_for_next_batch_of_work(self):
        # Wait for work from all masternodes that are currently online
        # How do we test if they are online? idk.
        while len(self.q) <= 0:
            await asyncio.sleep(0)

        work = self.q.pop(0)
        self.q.clear()

        return work


class BlockManager:
    def __init__(self, socket_base, ctx, network_parameters: NetworkParameters,
                  contacts: VKBook, validity_timeout=1000, parallelism=4, client=ContractingClient(), driver=MetaDataStorage()):

        # VKBook, essentially
        self.contacts = contacts

        # Number of core / processes we push to
        self.parallelism = parallelism
        self.network_parameters = network_parameters
        self.ctx = ctx

        # How long until a tx batch is 'stale' and no longer valid
        self.validity_timeout = validity_timeout

        self.client = client
        self.driver = driver

        self.nbn_inbox = NBNInbox(
            socket_id=self.network_parameters.resolve(socket_base, ServiceType.BLOCK_NOTIFICATIONS, bind=True)
        )
        self.work_inbox = WorkInbox(
            socket_id=self.network_parameters.resolve(socket_base, ServiceType.INCOMING_WORK, bind=True)
        )

        self.running = False

    async def run(self):
        while self.running:
            # wait for NBN
            block = await self.nbn_inbox.wait_for_next_nbn()
            # Catchup with block

            self.catchup_with_new_block(block, sender=b'')

            # Request work. Use async / dealers to block until it's done?
            # Refresh sockets here
            work = await self.work_inbox.wait_for_next_batch_of_work()

            filtered_work = []
            for tx_batch in work:
                # Filter out None responses
                if tx_batch is None:
                    continue

                # Add the rest to a priority queue based on their timestamp
                heapq.heappush(filtered_work, (tx_batch.timestamp, tx_batch))

            # Execute work
            output = await self.execute_work(filtered_work)

            # Package as SBCs
            # Send SBCs
            pass

    def catchup_with_new_block(self, block, sender: bytes):
        if block.blockNum < self.driver.latest_block_num + 1:
            return

        # If sender isnt a masternode, return
        if sender.hex() not in self.contacts.masternodes:
            return

        # if 2 / 3 didnt sign, return
        sub_blocks = [sb for sb in block.subBlocks]
        for sb in sub_blocks:
            if sb.inputHash in self.pending_subblock_hashes:
                # Commit partially? Don't think you can...
                continue

            if len(sb.signatures) < len(self.contacts.delegates) * 2 // 3:
                return

            # if you're not in the signatures, run catchup
            # if you are in the signatures, commit db

    async def execute_work(self, work):
        # Assume single threaded, single process for now.
        stamps_used = 0
        writes = {}
        deletes = set()

        while len(work) > 0:
            tx_batch = heapq.heappop(work)
            transactions = [tx for tx in tx_batch.transactions]

            now = Datetime._from_datetime(
                datetime.utcfromtimestamp(tx_batch.timestamp)
            )

            environment = {
                'block_hash': self.driver.latest_block_hash.hex(),
                'block_num': self.driver.latest_block_num,
                '__input_hash': tx_batch.inputHash, # Used for deterministic entropy for random games
                'now': now
            }

            for transaction in transactions:

                # Deserialize Kwargs. Kwargs should be serialized JSON moving into the future for DX.
                kwargs = {}
                for entry in transaction.payload.kwargs.entries:
                    if entry.value.which() == 'fixedPoint':
                        kwargs[entry.key] = ContractingDecimal(entry.value.fixedPoint) # ContractingDecimal!
                    else:
                        kwargs[entry.key] = getattr(entry.value, entry.value.which())

                output = self.client.executor.execute(
                    sender=transaction.payload.sender.hex(),
                    contract_name=transaction.payload.contractName,
                    function_name=transaction.payload.functionName,
                    stamps=transaction.payload.stampsSupplied,
                    kwargs=kwargs,
                    environment=environment,
                    auto_commit=False)

                stamps_used += output['stamps_used']
                writes.update(output['writes'])
                deletes.intersection(output['deletes'])

        return {
            'stamps_used': stamps_used,
            'writes': writes,
            'deletes': deletes
        }

    def build_sbc(self):
        writes, deletes = self.client.executor.driver.get_current_modifications()


    def send_sbc_to_master(self):
        pass

# struct TransactionBatch {
#     transactions @0 :List(Transaction);
#     timestamp @1: Float64;
#     signature @2: Data;
#     sender @3: Data;
#     inputHash @4: Data;  # hash of transactions + timestamp
# }

# struct MetaData {
#     proof @0 :Data;         # raghu - can be eliminated
#     signature @1 :Data;
#     timestamp @2 :Float32;
# }
#
# struct TransactionPayload {
#     sender @0 :Data;
#     processor @1: Data;
#     nonce @2 :UInt64;
#
#     stampsSupplied @3 :UInt64;
#
#     contractName @4 :Text;
#     functionName @5 :Text;
#     kwargs @6 :V.Map(Text, V.Value);
# }
#
# struct Transaction {
#     metadata @0: MetaData;
#     payload @1: TransactionPayload;
# }