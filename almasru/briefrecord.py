from lxml import etree
import logging
import requests
from typing import Dict, List, Tuple, Optional, Callable, Set, AnyStr, Literal, Union, Set
import os
import re
import hashlib
import json
from .utils import roman_to_int, remove_ns
from .common import check_error
from .client import SruRecord


class BriefRec:
    """Class representing a brief record object

    You can create a brief record object from a :class:`SruRecord` object or
    from the XML data of a MARCXML record using an Etree Element object.

    The namespaces are removed from the XML data.

    :ivar error: boolean, is True in case of error
    :ivar error_messages: list of string with the error messages
    :ivar data: json object with brief record information
    :ivar src_data: XML data of the record
    :ivar record: :class:`SruRecord` object if available
    """
    def __init__(self, rec: Union[etree.Element, 'SruRecord']) -> None:
        """Brief record object

        :param rec: XML data of the record or :class:`SruRecord` object
        """
        self.error = False
        self.error_messages = []
        self.data = None
        self.record = None
        if type(rec) is SruRecord:
            self.record = rec
            self.src_data = remove_ns(self.record.data)
            self.data = self.data = self._get_bib_info()
        elif type(rec) is etree._Element:
            self.src_data = remove_ns(rec)
            self.data = self._get_bib_info()
        else:
            self.error = True
            self.error.append(f'Wrong type of data provided: {type(rec)}')
            logging.error(f'BriefRec: wrong type of data provided: {type(rec)}')

    def __str__(self) -> str:
        if self.data is not None:
            return json.dumps(self.data, indent=4)
        else:
            return ''

    def __repr__(self) -> str:
        if self.record is not None:
            return f"{self.__class__.__name__}({repr(self.record)})"
        elif self.data is not None:
            return f"{self.__class__.__name__}(<'{self.data['rec_id']}'>)"
        else:
            return f"{self.__class__.__name__}(<No ID available>)"

    def __hash__(self) -> int:
        return hash(self.data['rec_id'])

    def __eq__(self, other) -> bool:
        return self.data['recid'] == other.data['recid']

    # @check_error
    def _get_bib_info(self):
        bib_info = BriefRecFactory.get_bib_info(self.src_data)
        return bib_info


class BriefRecFactory:
    """Class to create a brief record from a MARCXML record

    The class can parse several fields of the MARCXML record. It can also
    summarize the result in a json object.
    """

    @staticmethod
    def normalize_title(title: str) -> str:
        """normalize_title(title: str) -> str
        Normalize title string

        Idea is to remove "<<" and ">>" of the title and remove
        all non-alphanumeric characters.

        :param title: title to normalize

        :return: string with normalized title
        """
        title = title.upper().replace('<<', '').replace('>>', '')
        title = re.sub(r'\W', ' ', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    @staticmethod
    def normalize_extent(extent: str) -> List[int]:
        """normalize_extent(extent: str) -> List[int]
        Normalize extent string into list of ints

        :param extent: extent to normalize

        :return: list of ints
        """
        extent_lower = extent.lower()
        extent_list = [int(f) for f in re.findall(r'\d+', extent_lower)]
        extent_list += [roman_to_int(f) for f in re.findall(r'\b[ivxlcdm]+\b', extent_lower)]
        return extent_list

    @staticmethod
    def get_rec_id(bib: etree.Element) -> Optional[str]:
        """get_rec_id(bib: etree.Element) -> Optional[str]
        get_rec_id(bib) -> Optional[str]
        Get the record ID

        :param bib: :class:`etree.Element`

        :return: record ID or None if not found
        """
        controlfield001 = bib.find('.//controlfield[@tag="001"]')
        if controlfield001 is None:
            return None
        return controlfield001.text

    @staticmethod
    def get_isbns(bib: etree.Element) -> Optional[List[str]]:
        """get_isbns(bib: etree.Element) -> Optional[List[str]]
        Get a set of ISBNs

        :param bib: :class:`etree.Element`

        :return: set of ISBNs
        """
        # Get isbn fields
        fields = bib.findall('.//datafield[@tag="020"]/subfield[@code="a"]')
        raw_isbns = set([field.text for field in fields])
        isbns = set()

        for isbn in raw_isbns:

            # Remove hyphens and all textual information about isbn
            m = re.search(r'\d{8,}[\dxX]', isbn.replace('-', ''))
            if m is not None:
                isbns.add(m.group())
        if len(isbns) == 0:
            return None
        return list(isbns)

    @staticmethod
    def get_issns(bib: etree.Element) -> Optional[List[str]]:
        """get_issns(bib: etree.Element) -> Optional[List[str]]
        Get a set of issns

        :param bib: :class:`etree.Element`

        :return: set of ISSNs
        """
        fields = bib.findall('.//datafield[@tag="022"]/subfield[@code="a"]')
        raw_issns = set([field.text for field in fields])
        issns = set()

        for isbn in raw_issns:
            # Remove hyphens and all textual information about issn
            m = re.search(r'\d{7}[\dxX]', isbn.replace('-', ''))
            if m is not None:
                issns.add(m.group())
        if len(issns) == 0:
            return None
        return list(issns)

    @staticmethod
    def get_other_std_num(bib: etree.Element) -> Optional[List[str]]:
        """get_other_std_num(bib: etree.Element) -> Optional[List[str]]
        Get a list of standardized numbers like DOI

        :param bib: :class:`etree.Element`

        :return: set of standardized numbers
        """
        fields = bib.findall('.//datafield[@tag="024"]/subfield[@code="a"]')
        raw_std_nums = set([field.text for field in fields])
        std_nums = set()

        if len(raw_std_nums) == 0:
            return None
        return list(raw_std_nums)

    @staticmethod
    def get_leader_pos67(bib: etree.Element) -> Optional[str]:
        """get_leader_pos67(bib: etree.Element) -> Optional[str]
        Get the leader position 6 and 7

        Used to determine the format of the record

        :param bib: :class:`etree.Element`

        :return: leader position 6 and 7 or None if not found
        """

        leader = bib.find('.//leader')
        if leader is not None:
            return leader.text[6:8]

    @staticmethod
    def get_sysnums(bib: etree.Element) -> Optional[List[str]]:
        """get_sysnums(bib: etree.Element) -> Optional[List[str]]
        Get a set of system numbers

        :param bib: :class:`etree.Element`

        :return: set of system numbers
        """
        fields = bib.findall('.//datafield[@tag="035"]/subfield[@code="a"]')
        sysnums = set([field.text for field in fields])
        if len(sysnums) == 0:
            return None

        return list(sysnums)

    @staticmethod
    def get_title(bib: etree.Element) -> Optional[str]:
        """get_title(bib: etree.Element) -> Optional[str]
        Get normalized content of 245$a

        :param bib: :class:`etree.Element`

        :return: normalized content of field 245$a
        """
        title_field = bib.find('.//datafield[@tag="245"]/subfield[@code="a"]')
        if title_field is not None:
            return BriefRecFactory.normalize_title(title_field.text)

    @staticmethod
    def get_subtitle(bib: etree.Element) -> Optional[str]:
        """get_subtitle(bib: etree.Element) -> Optional[str]
        Get normalized content of 245$b

        :param bib: :class:`etree.Element`

        :return: normalized content of field 245$b or None if not found
        """

        sub_title_field = bib.find('.//datafield[@tag="245"]/subfield[@code="b"]')
        if sub_title_field is not None:
            return BriefRecFactory.normalize_title(sub_title_field.text)

    @staticmethod
    def get_part_title(bib: etree.Element) -> Optional[str]:
        """get_part_title(bib: etree.Element) -> Optional[str]

        :param bib: :class:`etree.Element`

        :return: content of 245$p or None if not found
        """
        part_title_field = bib.find('.//datafield[@tag="245"]/subfield[@code="p"]')
        if part_title_field is not None:
            return BriefRecFactory.normalize_title(part_title_field.text)

    @staticmethod
    def get_complete_title(bib: etree.Element) -> Optional[str]:
        title = ' '.join([t for t in [BriefRecFactory.get_title(bib),
                                      BriefRecFactory.get_subtitle(bib),
                                      BriefRecFactory.get_part_title(bib)] if t is not None])
        return title if len(title) > 0 else None

    @staticmethod
    def get_date_1(bib: etree.Element) -> Optional[int]:
        """get_date_1(bib: etree.Element) -> Optional[int]
        Get the first date of publication from 008 field

        :param bib: :class:`etree.Element`

        :return: Year of publication or None if not found
        """
        controlfield008 = bib.find('.//controlfield[@tag="008"]')
        if controlfield008 is None:
            return None

        date_1 = controlfield008.text[7:11]
        m = re.match(r'\d{4}', date_1)
        if m is not None:
            return int(m.group())

    @staticmethod
    def get_date_2(bib: etree.Element) -> Optional[int]:
        """get_date_2(bib: etree.Element) -> Optional[int]
        Get the second date of publication from 008 field

        :param bib: :class:`etree.Element`

        :return: Year of end of publication or None if not found
        """
        controlfield008 = bib.find('.//controlfield[@tag="008"]')
        if controlfield008 is None:
            return None

        date_2 = controlfield008.text[12:15]
        m = re.match(r'\d{4}', date_2)
        if m is not None:
            return int(m.group())

    @staticmethod
    def get_format(bib: etree.Element) -> Optional[Literal['book', 'analytical', 'series', 'map', 'projected']]:
        """get_format(bib: etree.Element) -> Optional[Literal['book', 'analytical', 'series']]
        Get the format of the record from leader field position 6 and 7

        :param bib: :class:`etree.Element`

        :return: format of the record
        """
        if BriefRecFactory.get_leader_pos67(bib) == 'am':
            return 'book'
        elif BriefRecFactory.get_leader_pos67(bib) == 'aa':
            return 'analytical'
        elif BriefRecFactory.get_leader_pos67(bib) == 'as':
            return 'series'
        elif BriefRecFactory.get_leader_pos67(bib) == 'em':
            return 'map'
        elif BriefRecFactory.get_leader_pos67(bib) == 'gm':
            return 'projected'
        else:
            logging.error(f'Unknown format: {BriefRecFactory.get_leader_pos67(bib)}')
            return None

    @staticmethod
    def get_creators(bib: etree.Element) -> Optional[List[str]]:
        """get_authors(bib: etree.Element) -> Option.al[List[str]]
        Get the list of authors from 100$a, 700$a

        :param bib: :class:`etree.Element`

        :return: list of authors and None if not found
        """
        fields = []
        for tag in ['100', '700']:
            fields += bib.findall(f'.//datafield[@tag="{tag}"]/subfield[@code="a"]')
        fields = [f.text for f in fields]
        if len(fields) == 0:
            return None
        else:
            return fields

    @staticmethod
    def get_corp_creators(bib: etree.Element) -> Optional[List[str]]:
        """get_authors(bib: etree.Element) -> Option.al[List[str]]
        Get the list of authors from 110$a, 111$a, 710$a and 711$a

        :param bib: :class:`etree.Element`

        :return: list of authors and None if not found
        """
        fields = []
        for tag in ['110', '111', '710', '711']:
            fields += bib.findall(f'.//datafield[@tag="{tag}"]/subfield[@code="a"]')
        fields = [f.text for f in fields]
        if len(fields) == 0:
            return None
        else:
            return fields

    @staticmethod
    def get_extent(bib: etree.Element):
        """get_extent(bib: etree.Element)
        Return extent from field 300$a

        :param bib: :class:`etree.Element`
        :return: list of extent or None if not found
        """
        extent_field = bib.find('.//datafield[@tag="300"]/subfield[@code="a"]')
        extent = None
        if extent_field is not None:
            extent = BriefRecFactory.normalize_extent(extent_field.text)

        return extent

    @staticmethod
    def get_publishers(bib: etree.Element):
        """get_publishers(bib: etree.Element)
        Return publishers from field 264$b

        :param bib: :class:`etree.Element`
        :return: list of publishers or None if not found
        """
        publisher_fields = bib.findall('.//datafield[@tag="264"]/subfield[@code="b"]')
        publishers = None
        if len(publisher_fields) > 0:
            publishers = [field.text for field in publisher_fields]

        return publishers

    @staticmethod
    def get_series(bib: etree.Element):
        """get_series(bib: etree.Element)
        Return series title from field 490$a

        :param bib: :class:`etree.Element`
        :return: list of titles of related series or None if not found
        """
        series_fields = bib.findall('.//datafield[@tag="490"]/subfield[@code="a"]')
        series = None
        if len(series_fields) > 0:
            series = [BriefRecFactory.normalize_title(field.text) for field in series_fields]

        return series

    @staticmethod
    def get_editions(bib: etree.Element):
        """get_editions(bib: etree.Element)
        Returns a list of editions (fields 250$a and 250$b)

        :param bib: :class:`etree.Element`

        :return: list of editions or None if not found
        """
        edition_fields = bib.findall('.//datafield[@tag="250"]/subfield[@code="a"]')
        editions = None
        if len(edition_fields) > 0:
            editions = []
            for edition_field in edition_fields:
                subfield_b = edition_field.getparent().find('subfield[@code="b"]')
                if subfield_b is not None:
                    editions.append(f'{edition_field.text} {subfield_b.text}')
                else:
                    editions.append(edition_field.text)

        return editions

    @staticmethod
    def get_bib_info(bib: etree.Element):
        """get_bib_info(bib: etree.Element)
        Return a json object with the brief record information

        :param bib: :class:`etree.Element`
        :return: json object with brief record information
        """
        bib_info = {'rec_id': BriefRecFactory.get_rec_id(bib),
                    'format': BriefRecFactory.get_format(bib),
                    'title': BriefRecFactory.get_complete_title(bib),
                    'short_title': BriefRecFactory.get_title(bib),
                    'editions': BriefRecFactory.get_editions(bib),
                    'creators': BriefRecFactory.get_creators(bib),
                    'corp_creators': BriefRecFactory.get_corp_creators(bib),
                    'date_1': BriefRecFactory.get_date_1(bib),
                    'date_2': BriefRecFactory.get_date_2(bib),
                    'publishers': BriefRecFactory.get_publishers(bib),
                    'series': BriefRecFactory.get_series(bib),
                    'extent': BriefRecFactory.get_extent(bib),
                    'isbns': BriefRecFactory.get_isbns(bib),
                    'issns': BriefRecFactory.get_issns(bib),
                    'other_std_num': BriefRecFactory.get_other_std_num(bib),
                    'sysnums': BriefRecFactory.get_sysnums(bib)}
        return bib_info