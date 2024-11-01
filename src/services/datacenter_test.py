import unittest
import datacenter

class DataCenterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dataCenter = datacenter.DataCenter()

    def test_get_config(self) -> None:
        config = self.dataCenter.get_config()
        self.assertNotEqual(config, None) 
    