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
