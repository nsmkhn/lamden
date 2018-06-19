from unittest import TestCase
from unittest.mock import MagicMock
from .trafficlight import *
from cilantro.utils.test import MPTestCase, MPStateMachine
from .stumachine import *
import time


class IntegrationTestState(MPTestCase):

    def test_state_timeout(self):
        def assert_fn(sm):
            assert sm.state == ChillState
            assert sm.did_timeout

        stu = MPStateMachine(sm_class=StuMachine, assert_fn=assert_fn)

        stu.start()
        stu.transition('FactorioState')

        self.start()

    def test_state_timeout_interrupted(self):
        def assert_fn(sm):
            assert not sm.did_timeout

        stu = MPStateMachine(sm_class=StuMachine, assert_fn=assert_fn)

        stu.start()
        stu.transition('FactorioState')
        time.sleep(0.5)  # transition out before the timeout

        self.start()

