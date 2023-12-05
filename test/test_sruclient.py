from almasru.client import SruClient, SruRecord, SruRequest, IzSruRecord
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

    def test_multiple_clients(self):
        r1 = SruRecord('990009063790108281', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        self.assertTrue(r1.error, 'Record should be in error')

        r2 = SruRecord('990009063790108281', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_ABN')
        self.assertFalse(r2.error, 'Record should be ok')

        r3 = SruRecord('991159842549705501', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        self.assertFalse(r3.error, 'Record should be ok')

        r4 = SruRecord('991159842549705501')
        self.assertFalse(r4.error, 'Record should be ok')

        r5 = SruRecord('990009063790108281')
        self.assertTrue(r5.error, 'Record should be in error')

    def test_iz_get_inventory(self):
        r = IzSruRecord('9963486250105504', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_UBS')
        holdings_id = set([i['holding'] for i in r.get_inventory_info()])
        self.assertEqual(holdings_id,
                         {'22314215800005504', '22314215780005504'},
                         'Holdings IDs should be 22314215800005504 and 22314215780005504')

    def test_iz_get_035_field(self):
        r = IzSruRecord('9963486250105504', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_UBS')
        fields035 = r.get_035_fields()
        self.assertIn('991125596919705501', fields035, '991125596919705501 should be among 035 to check')

    def test_IZ_is_removable_1(self):
        r = IzSruRecord('9963486250105504', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_UBS')
        is_removable, msg = r.is_removable()
        self.assertFalse(is_removable, 'record has inventory and is not removable')
        self.assertEqual(msg, 'Record has inventory in the IZ', 'message should be: ""')

    def test_IZ_is_removable_2(self):
        r = IzSruRecord('9914811354101791', base_url='https://eu03.alma.exlibrisgroup.com/view/sru/41BIG_INST',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        self.assertFalse(r.is_removable()[0], '9914811354101791 has inventory and cannot be removed')

    def test_IZ_is_removable_3(self):

        # Test series
        r = IzSruRecord('990058695800205516',
                        base_url='https://eu03.alma.exlibrisgroup.com/view/sru/41SLSP_EPF',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        self.assertFalse(r.is_removable()[0],
                         '990058695800205516 has children with inventory and cannot be removed')

        self.assertEqual(r.is_removable()[1], 'Child record has inventory',
                         '990058695800205516 has children with inventory and cannot be removed')

    def test_IZ_is_removable_4(self):

        # Test analytical record
        r = IzSruRecord('990065787410205516',
                        base_url='https://eu03.alma.exlibrisgroup.com/view/sru/41SLSP_EPF',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')

        self.assertFalse(r.is_removable()[0],
                         '990065787410205516 has parent with inventory and cannot be removed')

    def test_IZ_nz_sru_client(self):
        r = IzSruRecord('9963486250105504',
                        base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_UBS',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        self.assertEqual(r.nz_sru_client.base_url,
                         'https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK',
                         'Url is not related to network')
        self.assertEqual(r.sru_client.base_url,
                         'https://swisscovery.slsp.ch/view/sru/41SLSP_UBS',
                         'Url is not related to UBS')

    def test_get_IzSruRecord_with_get_child_rec_sys_num(self):
        r = IzSruRecord('990001009520108281',
                        base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_ABN',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        related_records = r.get_child_rec_sys_num()
        rec = list(related_records['related_records'])[0]
        self.assertEqual(type(rec).__name__, 'IzSruRecord', 'Type of record should be IzSruRecord')

    def test_get_parent_IZ_rec(self):
        r = IzSruRecord('990003537470108281', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_ABN',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        parents = r.get_parent_rec()
        self.assertEqual(type(list(parents['related_records'])[0]).__name__,
                         'SruRecord',
                         'Type must be SruRecord')

        r = IzSruRecord('9972692445905504', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_UBS',
                        nz_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        parents = r.get_parent_rec()
        self.assertEqual(type(list(parents['related_records'])[0]).__name__,
                         'IzSruRecord',
                         'Type must be SruRecord')

        self.assertEqual(list(parents['related_records'])[0].mms_id,
                         '9958366340105504',
                         'MMS ID must be "9958366340105504"')

    def test_get_nz_mms_id(self):
        r_nz = SruRecord('991120755789705501', base_url='https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')
        r_iz = r_nz.get_iz_record('https://swisscovery.slsp.ch/view/sru/41SLSP_ABN')
        self.assertEqual(r_iz.get_nz_mms_id(), '991120755789705501')


if __name__ == '__main__':
    unittest.main()
