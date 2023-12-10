from .client import SruRecord
import pandas as pd
import numpy as np
from typing import List, Optional
import logging
from lxml import etree
import re


def analyse_records(mms_ids: List[str], filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Use a list of MMS ID to analyse the records and return a :class:`pandas.DataFrame` with the results.

    Main difference with :func:`check_removable_records` is that this function will check all parameters.

    :param mms_ids: list of MMS ID to analyse
    :param filepath: Optional string with a path to an Excel file to save automatically each checked record
    :return: :class:`pandas.DataFrame` containing the results of the analysis
    """
    df = pd.DataFrame(columns=['removable',
                               'bib_level',
                               'error',
                               'IZ_with_inventory',
                               'child_records',
                               'parent_records',
                               'messages'])
    df.index.name = 'mms_id'

    # This set contains all processed records, useful to avoid to process twice the same record
    processed_records = set()

    # Fetch all records to analyse
    records = [SruRecord(mms_id) for mms_id in mms_ids]

    while len(records) > 0:
        rec = records.pop(0)
        logging.info(f'Processed: {len(processed_records)} / remaining: {len(records)} / current: {repr(rec)}')

        # Avoid to analyse the same record twice
        if rec in processed_records:
            continue
        messages = rec.get_reasons_preventing_deletion()

        # Add the record to the list of processed records to avoid twice analyses
        processed_records.add(rec)

        # Record encountered an error
        if rec.error is True:
            df.loc[rec.mms_id] = [False,
                                  np.nan,
                                  rec.error,
                                  np.nan,
                                  np.nan,
                                  np.nan,
                                  np.nan]
            continue

        # Fetch parent and child records
        children = [child.mms_id for child in rec.get_child_rec()['related_records']]
        parents = [parent.mms_id for parent in rec.get_parent_rec()['related_records']]

        df.loc[rec.mms_id] = [len(messages) == 0,
                              rec.get_bib_level(),
                              rec.error,
                              '|'.join(rec.get_iz_using_rec()),
                              '|'.join(children),
                              '|'.join(parents),
                              '|'.join(messages)]

    if filepath is not None:
        df.to_excel(filepath)

    return df


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

    removable_rec_mms_ids = []

    while len(records) > 0:
        rec = records.pop(0)
        logging.info(f'Processed: {len(processed_records)} / remaining: {len(records)} / current: {repr(rec)}')

        # Avoid to analyse the same record twice
        if rec in processed_records:
            continue

        # Check if the record is removable
        is_removable = rec.is_removable(removable_rec_mms_ids)

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

        if is_removable[1] == 'Record used in at least one IZ':
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

        # Get list of mms_id to ignore when checking for existing child analytical records
        removable_rec_mms_ids = df.loc[df.removable].index.values

    # Add a column with boolean indicating which mms_id were in the starting list of mms_id to check
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


def roman_to_int(roman_number: str) -> int:
    """Transform roman number to integer
    :param roman_number: roman number
    :return: int value of the number
    """
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000, 'IV': 4, 'IX': 9, 'XL': 40, 'XC': 90,
             'CD': 400, 'CM': 900}
    i = 0
    num = 0

    # Only capitals
    roman_number = roman_number.upper()

    while i < len(roman_number):
        # Check if a digramme like IV is in the number
        if i + 1 < len(roman_number) and roman_number[i:i + 2] in roman:
            num += roman[roman_number[i:i + 2]]
            i += 2

        elif roman_number[i] in roman:
            num += roman[roman_number[i]]
            i += 1

    return num


def remove_ns(data: etree.Element) -> etree.Element:
    """Remove namespace from XML data
    :param data: `etree.Element` object with xml data
    :return: `etree.Element` without namespace information
    :rtype:
    """
    temp_data = etree.tostring(data).decode()
    temp_data = re.sub(r'\s?xmlns="[^"]+"', '', temp_data).encode()
    return etree.fromstring(temp_data)

