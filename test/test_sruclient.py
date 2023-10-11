from almasru.client import SruClient, SruRecord, SruRequest
from almasru import config_log
import unittest
import shutil

config_log()
SruClient.set_base_url('https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')


class TestSruClient(unittest.TestCase):
    def test_fetch_records(self):
        req = SruClient().fetch_records('alma.mms_id=991093571899705501')

        self.assertFalse(req.error, 'not able to fetch SRU data')

        self.assertEqual(len(req.records), 1, f'should be one record found, found: {len(req.records)}')

    def test_sru_request(self):
        req = SruRequest('alma.mms_id=991093571899705501')

        self.assertFalse(req.error, 'not able to fetch SRU data')

        self.assertEqual(len(req.records), 1, f'should be one record found, found: {len(req.records)}')

    def test_limit_fetch_records(self):
        req = SruClient().fetch_records('alma.title=python', 30)
        self.assertEqual(len(req.records), 30, f'Should be 30 records, returned {len(req.records)}')

        req = SruClient().fetch_records('alma.title=python', 60)
        self.assertEqual(len(req.records), 60, f'Should be 60 records, returned {len(req.records)}')

        req = SruClient().fetch_records('alma.title=python_NOT_EXISTING_TITLE', 110)
        self.assertEqual(len(req.records), 0, f'Should be 0 records, returned {len(req.records)}')

    def test_get_mms_id(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)

        self.assertEqual(rec.get_mms_id(),
                         '991159842549705501',
                         f'MMS ID should be "991159842549705501", it is {rec.get_mms_id()}')

    def test_get_035_field_1(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)

        self.assertEqual(rec.get_035_fields(),
                         {'142079855', '(swissbib)142079855-41slsp_network', '(NEBIS)001807691EBI01'},
                         f'It should be: "142079855", "(swissbib)142079855-41slsp_network", "(NEBIS)001807691EBI01"')

    def test_get_035_field_2(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)

        self.assertEqual(rec.get_035_fields(slsp_only=True),
                         {'(swissbib)142079855-41slsp_network', '(NEBIS)001807691EBI01'},
                         f'It should be: "(swissbib)142079855-41slsp_network", "(NEBIS)001807691EBI01"')

    def test_exist_analytical_records_children_1(self):
        mms_id = '991068988579705501'
        rec = SruRecord(mms_id)
        analytical_records = rec.get_child_analytical_records()
        self.assertGreater(len(analytical_records), 35)

    def test_exist_analytical_records_children_2(self):
        mms_id = '991156231809705501'
        rec = SruRecord(mms_id)
        analytical_records = rec.get_child_analytical_records()
        self.assertEqual(len(analytical_records), 0)

    def test_get_rel_rec(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        analysis = rec.get_child_rec()
        self.assertEqual(analysis['related_records_found'], True, 'Related records for "991159842549705501"'
                                                                  ' should have been found')
        self.assertEqual(analysis['number_of_rel_recs'], 8, 'It should be 8 related records for "991159842549705501"')
        self.assertTrue(SruRecord('991171058106405501') in analysis['related_records'],
                        'Record "991171058106405501" should be in related records set')
        self.assertTrue({'child_MMS_ID': '991171058106405501',
                         'field': '773$w',
                         'content': '991159842549705501'} in analysis['fields_related_records'],
                        'Field "991171058106405501: 773$w 991159842549705501" should be in "fields_related_records"')

    def test_get_parent_rec(self):
        mms_id = '991170891086405501'
        analysis = SruRecord(mms_id).get_parent_rec()
        self.assertEqual(analysis['number_of_rel_recs'], 1, 'It should be 1 parent record for "991170891086405501"')
        self.assertTrue(SruRecord('991170949772005501') in analysis['related_records'],
                        f'{repr(SruRecord("991170949772005501"))} should be in related records')

    def test_get_used_by_iz(self):
        mms_id = '991082448539705501'
        rec = SruRecord(mms_id)
        izs = rec.get_iz_using_rec()
        self.assertEqual(izs, ['41SLSP_UZB', '41BIG_INST'], f'IZs for {repr(rec)} should be "41SLSP_UZB" and '
                                                            f'"41BIG_INST", it is {izs}')

    def test_get_inventory_info(self):
        mms_id = '991082448539705501'
        rec = SruRecord(mms_id)
        inv = rec.get_inventory_info()
        self.assertEqual(len(inv), 2, f'Inventory info for {repr(rec)} should be related to 2 IZ, '
                                      f'"{len(inv)} have been found')

    def test_get_bib_level(self):
        mms_id = '991082448539705501'
        rec = SruRecord(mms_id)
        self.assertEqual(rec.get_bib_level(), 'm', f'Bib level should be "m", it is "{rec.get_bib_level()}"')

    def test_get_issn(self):
        mms_id = '991171145315105501'
        rec = SruRecord(mms_id)
        self.assertEqual(rec.get_issn(), {'2558-2062'}, f'ISSN should be "2558-2062", it is:"{rec.get_issn()}"')

    def test_get_isbn(self):
        mms_id = '991171145315105501'
        rec = SruRecord(mms_id)
        self.assertEqual(rec.get_isbn(), {'9791095991052'}, f'ISBN should be "9791095991052", it is:"{rec.get_isbn()}"')

    def test_get_standard_numbers(self):
        mms_id = '991171145315105501'
        rec = SruRecord(mms_id)
        self.assertEqual(rec.get_standard_numbers(),
                         {'2558-2062', '9791095991052'},
                         f'Standard numbers should be 25582062 and 9791095991052, it is:"{rec.get_standard_numbers()}"')

    def test_is_removable_1(self):
        r = SruRecord('991133645269705501')
        self.assertEqual(r.is_removable(),
                         (False, 'Parent record has inventory'),
                         f'{repr(r)} is not removable and parent has inventory')

    def test_is_removable_2(self):
        r = SruRecord('991136844579705501')
        self.assertEqual(r.is_removable(),
                         (False, 'Child record has inventory'),
                         f'{repr(r)} is not removable and child has inventory')

    def test_error_on_mms_id(self):
        r = SruRecord('24234234542542354325454')
        self.assertTrue(r.error, 'An error should be generated with bad mms_id')

    def test_save(self):
        shutil.rmtree('./records/', ignore_errors=True)
        r = SruRecord('991133645239705501')
        r.save()
        with open('./records/rec_991133645239705501.xml') as f:
            xml = f.read()

        self.assertTrue('991133645239705501' in xml)

    def test_get_reasons_preventing_deletion(self):
        msg = SruRecord('991133645269705501').get_reasons_preventing_deletion()
        self.assertEqual(len(msg), 1, 'Should be one message')
        self.assertEqual(msg[0],
                         'Has parent record preventing deletion with inventory: 991015678889705501',
                         'Message should be "Has parent record preventing deletion with inventory: 991015678889705501"')

    def test_client_other_client(self):

        client = SruClient(base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_ABN')
        req = client.fetch_records('alma.isbn=389721511X')

        self.assertFalse(req.error, 'not able to fetch SRU data')

        self.assertEqual(len(req.records), 1, f'should be one record found, found: {len(req.records)}')


if __name__ == '__main__':
    unittest.main()
