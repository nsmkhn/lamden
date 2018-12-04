from unittest import TestCase
import unittest
from seneca.engine.interface import SenecaInterface
from cilantro.storage.state import StateDriver
from cilantro.messages.block_data.block_data import BlockDataBuilder
from cilantro.messages.block_data.block_data import GENESIS_BLOCK_HASH


class TestStateDriver(TestCase):

    def setUp(self):
        StateDriver.r.flushdb()
        tx_count = 5
        sub_block_count = 2
        states = [
            'SET hello world;SET goodbye world;',
            'SET entropy regression;',
            'SET land sea;',
            'SET xxx holic;',
            'SET beyonce sings;',

            'SET cow poo;',
            'SET anthropologist discovers;',
            'SET cranberry juice;',
            'SET optic fiber;',
            'SET before after;'
        ]
        self.block = BlockDataBuilder.create_block(sub_block_count=sub_block_count, tx_count=tx_count, states=states, all_transactions=[])

    def test_state_updated(self):
        StateDriver.update_with_block(self.block)
        self.assertEqual(StateDriver.r.get('hello'), b'world')
        self.assertEqual(StateDriver.r.get('goodbye'), b'world')
        self.assertEqual(StateDriver.r.get('entropy'), b'regression')
        self.assertEqual(StateDriver.r.get('land'), b'sea')
        self.assertEqual(StateDriver.r.get('xxx'), b'holic')
        self.assertEqual(StateDriver.r.get('beyonce'), b'sings')
        self.assertEqual(StateDriver.r.get('cow'), b'poo')
        self.assertEqual(StateDriver.r.get('anthropologist'), b'discovers')
        self.assertEqual(StateDriver.r.get('cranberry'), b'juice')
        self.assertEqual(StateDriver.r.get('optic'), b'fiber')
        self.assertEqual(StateDriver.r.get('before'), b'after')

    # TODO test this with publish transactions

    def test_get_latest_block_hash_with_none_set(self):
        b_hash = StateDriver.get_latest_block_hash()
        self.assertEqual(GENESIS_BLOCK_HASH, b_hash)

    def test_set_get_latest_block_hash(self):
        b_hash = 'ABCD' * 16
        StateDriver.set_latest_block_hash(b_hash)

        self.assertEqual(StateDriver.get_latest_block_hash(), b_hash)


if __name__ == '__main__':
    unittest.main()
