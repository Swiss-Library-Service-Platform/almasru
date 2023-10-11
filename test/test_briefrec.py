from almasru.client import SruClient, SruRecord, SruRequest
from almasru.briefrecord import BriefRec
from almasru import config_log
import unittest
import shutil

config_log()
SruClient.set_base_url('https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')


class TestSruClient(unittest.TestCase):
    def test_create_brief_record(self):
        mms_id = '991068988579705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)

        self.assertEqual(brief_rec.data['rec_id'], '991068988579705501',
                         f'No brief record created for {mms_id}')

        self.assertEqual(len(brief_rec.data), 16,
                         f'Not all keys of data are present in brief record for {mms_id}')


if __name__ == '__main__':
    unittest.main()
