from lamden.logger.base import get_logger
from lamden import router, storage
from lamden.crypto.wallet import verify
from lamden.crypto import transaction
from contracting.client import ContractingClient
from lamden.crypto.transaction import TransactionException

class WorkValidator(router.Processor):
    def __init__(self, hlc_clock, wallet, add_to_main_processing_queue, get_masters, debug=True, expired_batch=5,
                 tx_timeout=5):

        self.tx_expiry_sec = 1

        self.log = get_logger('Work Inbox')
        self.log.propagate = debug

        self.masters = []
        self.tx_timeout = tx_timeout

        self.add_to_main_processing_queue = add_to_main_processing_queue
        self.get_masters = get_masters

        self.wallet = wallet
        self.hlc_clock = hlc_clock


    async def process_message(self, msg):

        self.log.info(f'Received work from {msg["sender"][:8]} {msg["hlc_timestamp"]} {msg["tx"]["metadata"]["signature"][:12] }')
        ## self.log.info(msg)

        #if msg["sender"] == self.wallet.verifying_key:
        #    return

        self.masters = self.get_masters()

        if msg['sender'] not in self.masters:
            self.log.error(f'TX Batch received from non-master {msg["sender"][:8]}')
            return

        if not verify(vk=msg['sender'], msg=msg['input_hash'], signature=msg['signature']):
            self.log.error(f'Invalidly signed TX received from master {msg["sender"][:8]}')

        ''' # Removed for testing
        if await self.hlc_clock.check_expired(timestamp=msg['hlc_timestamp']):
            self.log.error(f'Expired TX from master {msg["sender"][:8]}')
            return
        '''

        self.hlc_clock.merge_hlc_timestamp(event_timestamp=msg['hlc_timestamp'])
        self.add_to_main_processing_queue(msg)

        #self.log.info(f'Received new work from {msg["sender"][:8]} to my queue.')
