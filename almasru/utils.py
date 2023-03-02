from .client import SruRecord
import pandas as pd
import numpy as np
from typing import List, Optional
import logging


# def check_related_records(mms_ids: List[str], filepath: Optional[str] = None) -> pd.DataFrame:
#     """Check related records for a list of MMS ID
#
#     The function returns the results with a `:class:pandas.DataFrame` with the following columns:
#     - 'mms_id',
#     - 'is_related_record',
#     - 'related_records_mms_id',
#     - 'records_without_linking_field',
#     - 'fields_related_records'
#
#     :param mms_ids: List of MMS ID of records to check through SRU
#     :param filepath: Optional string with a path to an Excel file to save automatically each checked record
#     :return: `:class:pandas.DataFrame` containing the results of the analysis
#     """
#     df = pd.DataFrame(columns=['mms_id',
#                                'is_related_record',
#                                'related_records_mms_id',
#                                'records_without_linking_field',
#                                'fields_related_records'])
#     for mms_id in mms_ids:
#         rec = SruRecord(mms_id)
#         related_records = rec.get_child_rec()
#         df.loc[len(df)] = [related_records['MMS_ID'],
#                            related_records['related_records_found'],
#                            '|'.join(related_records['related_records']),
#                            '|'.join(related_records['records_without_linking_field']),
#                            '|'.join(related_records['fields_related_records'])]
#
#         if filepath is not None:
#             df.to_excel(filepath, index=False)
#
#     return df


def check_removable_records(mms_ids: List[str], filepath: Optional[str] = None) -> pd.DataFrame:
    """Check removable records for a list of MMS ID

    Not all parameters are always checked. The system stop to check once one parameter
    is found preventing the deletion.

    :param mms_ids: List of MMS ID of records to check through SRU
    :param filepath: Optional string with a path to an Excel file to save automatically each checked record

    :return: :class:`pandas.DataFrame` containing the results of the analysis
    """
    df = pd.DataFrame(columns=['removable',
                               'comment',
                               'bib_level',
                               'IZ_with_inventory',
                               'child_records',
                               'parent_records',
                               'fields_to_check',
                               'warning',
                               'error'])
    df.index.name = 'mms_id'

    # This set contains all processed records, useful to avoid to process twice the same record
    processed_records = set()

    # Fetch all records to analyse
    records = [SruRecord(mms_id) for mms_id in mms_ids]

    while len(records) > 0:
        rec = records.pop()
        logging.info(f'Processed: {len(processed_records)} / remaining: {len(records)} / current: {repr(rec)}')

        # Avoid to analyse the same record twice
        if rec in processed_records:
            continue

        # Check if the record is removable
        is_removable = rec.is_removable()

        # Add the record to the list of processed records to avoid twice analyses
        processed_records.add(rec)

        # Record encountered an error
        if rec.error is True:
            df.loc[rec.mms_id] = [False,
                                  'Not removable due to error',
                                  np.nan,
                                  np.nan,
                                  np.nan,
                                  np.nan,
                                  np.nan,
                                  np.nan,
                                  rec.error]
            continue

        # Record is removable, potential links of children are checked later
        if is_removable[0] is True:

            # Add children and parents that require to be checked
            records += rec.get_child_removable_candidate_rec()
            records += rec.get_parent_removable_candidate_rec()

        if is_removable[1] == 'Record used in other IZ':
            # No need to check parents if record has inventory
            children = []
            parents = []
        else:
            # Fetch parent and child records
            children = [child.mms_id for child in rec.get_child_rec()['related_records']]
            parents = [parent.mms_id for parent in rec.get_parent_rec()['related_records']]

        df.loc[rec.mms_id] = [is_removable[0],
                              is_removable[1],
                              rec.get_bib_level(),
                              '|'.join(rec.get_iz_using_rec()),
                              '|'.join(children),
                              '|'.join(parents),
                              np.nan,
                              np.nan if rec.warning is False else rec.warning_messages[-1],
                              rec.error]

    df['additional_mms_id'] = ~df.index.isin(mms_ids)

    # Check the children, if some links exist that will be broken if the record is removed.
    removable_rec_mms_ids = df.loc[df.removable].index.values

    # Get the list of removable records, check of links is only meaningful for removable records
    removable_records = [SruRecord(mms_id) for mms_id in removable_rec_mms_ids]

    for rec in removable_records:

        # Links of child records need to be updated before removing the parent
        links = rec.get_child_rec()['fields_related_records']

        # No change is required if the child will be removed too
        str_links = [f'{link["child_MMS_ID"]}: {link["field"]} {link["content"]}'
                     for link in links if link['child_MMS_ID'] not in removable_rec_mms_ids]

        if len(str_links) > 0:
            logging.warning(f'{repr(rec)}: links need to be checked: {"|".join(str_links)}')
            str_links = '\n'.join(str_links)
            df.loc[rec.mms_id, 'fields_to_check'] = str_links
            df.loc[rec.mms_id, 'comment'] = 'REMOVABLE after child record update'

    if filepath is not None:
        df.to_excel(filepath)

    return df


# def get_related_records(mms_id: str, limit: int = 1000):
#     """
#
#     :param mms_id:
#     :type mms_id:
#     :param limit:
#     :type limit:
#     :return:
#     :rtype:
#     """
#     starting_rec = SruRecord(mms_id)
#     records_to_check = []
#     records_checked = set()
#     if starting_rec.error is False:
#         records_to_check.append(starting_rec)
#
#     while len(records_to_check) > 0 and len(records_checked) < limit:
#         record = records_to_check.pop()
#         children = record.get_child_rec()['related_records']
#         records_to_check = set.union(set(records_to_check), (children-records_checked))
#
#         parents = record.get_parent_rec()['related_records']
#         records_to_check = list(set.union(set(records_to_check), (parents - records_checked)))
#
#         records_checked.add(record)
#
#     if len(records_to_check) >= 0:
#         logging.warning(f'{repr(starting_rec)}: limit {limit} of related records reached')
#
#     return records_checked
