from almasru.client import SruClient, SruRecord, SruRequest
from almasru.briefrecord import BriefRec
from almasru import config_log, dedup
import unittest
import numpy as np
import pandas as pd
import pickle
import shutil

config_log()
SruClient.set_base_url('https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')


class TestDedup(unittest.TestCase):
    def test_evaluate_texts(self):
        self.assertGreater(dedup.evaluate_texts('Introduction à Python', 'Introduction à python'),
                           0.95,
                           'Similarity must be greater than 0.95')

    def test_evaluate_names(self):
        self.assertLess(dedup.evaluate_names('André Surnom', 'André Surmon'),
                           0.5,
                           'Similarity must be less than 0.5')

        self.assertGreater(dedup.evaluate_names('Surnom, A.', 'Surnom, André'),
                           0.5,
                           'Similarity must be less than 0.5')

    def test_evaluate_extent(self):
        self.assertGreater(dedup.evaluate_extent([200, 300], [200, 300]),
                           0.95,
                           'Similarity must be greater than 0.95')

        self.assertLess(dedup.evaluate_extent([202, 311], [200, 300]),
                           0.6,
                           'Similarity must be less than 0.6')

    def test_evaluate_parents(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)

        score = dedup.evaluate_parents(brief_rec.data['parent'], brief_rec.data['parent'])
        self.assertEqual(score, 1, 'Score should be 1 for parent when comparing same record (with parent)')

        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        score = dedup.evaluate_parents(brief_rec.data['parent'], brief_rec.data['parent'])
        self.assertEqual(score, 1, 'Score should be 1 for parent when comparing same record (without parent)')

    def test_evaluate_parents_2(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec1 = BriefRec(rec)
        brief_rec2 = BriefRec(rec)

        brief_rec1.data['parent']['parts'] = brief_rec1.data['parent']['parts'][:1]
        del brief_rec1.data['parent']['year']
        score = dedup.evaluate_parents(brief_rec1.data['parent'], brief_rec2.data['parent'])
        self.assertGreater(score, 0.3, 'Score should be above 0.3 with minor changes')
        self.assertLess(score, 0.99, 'Score should be below 0.7 with minor changes')

    def test_evaluate_parents_3(self):
        mms_id = '991171637529805501'
        rec = SruRecord(mms_id)
        brief_rec1 = BriefRec(rec)
        brief_rec2 = BriefRec(rec)

        brief_rec1.data['parent']['parts'] = brief_rec1.data['parent']['parts'][:2]
        del brief_rec1.data['parent']['year']
        brief_rec1.data['parent']['title'] = brief_rec1.data['parent']['title'] + ' publication'
        score = dedup.evaluate_parents(brief_rec1.data['parent'], brief_rec2.data['parent'])
        self.assertGreater(score, 0.5, 'Score should be above 0.5 with minor changes')
        self.assertLess(score, 0.99, 'Score should be below 0.7 with minor changes')

    def test_evaluate_parents_4(self):
        mms_id1 = '991004153419705501'
        rec1 = SruRecord(mms_id1)
        brief_rec1 = BriefRec(rec1)
        mms_id2 = '991152762959705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)

        score1 = dedup.evaluate_parents(brief_rec1.data['parent'], brief_rec2.data['parent'])
        self.assertGreater(score1, 0.4, 'Score should be above 0.5 with minor changes')
        self.assertLess(score1, 0.99, 'Score should be below 0.7 with minor changes')

        mms_id1 = '991004153419705501'
        rec1 = SruRecord(mms_id1)
        brief_rec1 = BriefRec(rec1)
        mms_id2 = '991152762959705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)

        brief_rec2.data['parent']['number'] = '15/14'
        brief_rec1.data['parent']['number'] = '15/14'

        score2 = dedup.evaluate_parents(brief_rec1.data['parent'], brief_rec2.data['parent'])
        self.assertGreater(score2, score1, 'With same number key, the result should be higher')

    def test_evaluate_format(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842549705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.evaluate_format(brief_rec.data['format'], brief_rec2.data['format'])

        self.assertEqual(result, 1.0, f'format should be the same when comparison with identical record')

        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842649705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.evaluate_format(brief_rec.data['format'], brief_rec2.data['format'])
        self.assertLess(result, 0.5, f'Score should be less than 0.5, returned {result}')
        self.assertGreater(result, 0.2, f'Score should be less than 0.2, returned {result}')

    def test_evaluate_similarity(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842549705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.evaluate_similarity(brief_rec.data, brief_rec2.data)

        mean = np.mean([result[k] for k in result if pd.isna(result[k]) is False])

        self.assertEqual(mean, 1.0, f'Mean should be 1.0 when comparing same records, returned {mean}')

    def test_evaluate_similarity_score(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842549705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.get_similarity_score(brief_rec.data, brief_rec2.data)

        self.assertEqual(result, 1.0, f'Mean should be 1.0 when comparing same records, returned {result}')

        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842649705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.get_similarity_score(brief_rec.data, brief_rec2.data)
        self.assertLess(result, 0.5, f'Mean should be less than 0.5 when comparing "{mms_id}" and "{mms_id2}", returned {result}')

    def test_evaluate_similarity_score_2(self):
        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842549705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        with open('classifiers/clf_MLPClassifier_mono2.pickle', 'rb') as f:
            clf = pickle.load(f)

        result = dedup.get_similarity_score(brief_rec.data, brief_rec2.data, clf)

        self.assertGreater(result,
                           0.99,
                           f'Result should near to 1.0 when comparing same records, returned {result}')

        mms_id = '991159842549705501'
        rec = SruRecord(mms_id)
        brief_rec = BriefRec(rec)
        mms_id2 = '991159842649705501'
        rec2 = SruRecord(mms_id2)
        brief_rec2 = BriefRec(rec2)
        result = dedup.get_similarity_score(brief_rec.data, brief_rec2.data, clf)
        self.assertLess(result,
                        0.5,
                        f'Result should be less than 0.5 when comparing "{mms_id}" and "{mms_id2}", returned {result}')


if __name__ == '__main__':
    unittest.main()
