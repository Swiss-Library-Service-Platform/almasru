from almasru.client import SruClient, SruRecord, SruRequest
from almasru.briefrecord import BriefRec, BriefRecFactory
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

        self.assertEqual(len(brief_rec.data), 18,
                         f'Not all keys of data are present in brief record for {mms_id}')

    def test_eq_brief_record(self):
        mms_id = '991068988579705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)

        self.assertEqual(brief_rec, brief_rec,
                         f'Equality test of brief record failed for {mms_id}')

    def test_get_parent(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['parent']['parts'], [2001, 111, 115, 164],
                         f'parts must be [2001, 111, 115, 164]')

        self.assertEqual(brief_rec.data['parent']['year'], 2001, 'Year should be 2001')

    def test_get_format(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['format'], 'aa / txt;n;nc / p', 'Format should be "aa / txt;n;nc"')

    def test_get_language(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['language'], 'ger', 'Language should be "ger"')

    def test_check_is_online_1(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['format'].split('/')[-1].strip(), 'p', 'Format should be "p"')

    def test_check_is_online_2(self):
        mms_id = '991171016126905501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['format'].split('/')[-1].strip(), 'e', 'Format should be "e"')

    def test_check_is_online_3(self):
        mms_id = '991171022315005501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        self.assertEqual(brief_rec.data['format'].split('/')[-1].strip(), 'e', 'Format should be "e"')


if __name__ == '__main__':
    unittest.main()
