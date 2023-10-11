
import logging
import requests
from typing import Dict, List, Tuple, Optional, AnyStr, Literal, Set
import os
import re
import hashlib
from .common import check_error
import shutil
from lxml import etree


class SruRequest:
    """Class representing SRU request

    This class is used to make SruRequests and to fetch :class:`almasru.client.SruRecord` results.

    :ivar query: string containing the query for example 'alma.mms_id=991093571899705501'
    :ivar limit: int indicating the max number of returned records. If more records are
        available, a warning is raised
    :ivar error: boolean, is True in case of error
    :ivar error_messages: list of string with the error messages
    :ivar are_more_results_available: bool indicating if more records than the limit is available
    :ivar records: list of :class:`almasru.client.SruRecord`
    :ivar base_url: base url of the SRU server

    :example:

        SruRequest('alma.mms_id=991093571899705501')

    """

    def __init__(self, query: str, limit: int = 10, client: 'SruClient' = None) -> None:
        self.query = query
        self.limit = limit
        self.error = False
        self.error_messages = []
        self.are_more_results_available = False
        self.records = []
        self.base_url = client.base_url if client is not None else SruClient.base_url
        self._fetch_records()

    def __hash__(self) -> int:
        return int(hashlib.sha1(bytes(self._get_query_path(), 'utf-8')).hexdigest(), 16)

    def __eq__(self, other) -> bool:
        return self.query == other.query

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.query}', limit={self.limit})"

    def _get_query_path(self) -> str:
        return f'{self.query}__{self.limit}'

    @staticmethod
    def _build_sru_params(query: str, start_record: int = 1, maximum_records: int = 10) -> Dict[AnyStr, AnyStr]:
        return {'query': query,
                'version': '1.2',
                'operation': 'searchRetrieve',
                'startRecord': str(start_record),
                'maximumRecords': str(maximum_records)}

    def _fetch_data(self,
                    start_record: int = 1,
                    maximum_records: int = 10) -> Tuple[etree.Element, bool]:
        """Fetch raw XML data from an SRU query

        :param start_record: int indicating the rank of the first record to fetch
        :param maximum_records: int indicating the max number of records to fetch, default is 10

        :return: tuple containing `etree.Element` and a boolean with an error status
        """
        is_error = False

        filepath = f'requests/request_{hash(self)}_{start_record}.xml'
        if os.path.isfile(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
        else:
            params = self._build_sru_params(self.query, start_record, maximum_records)
            r = requests.get(self.base_url, params=params)
            if r.ok is True:
                logging.info(f'SRU data fetched: {r.url}')
                content = r.content
                # Save request on the disk
                with open(filepath, 'wb') as f:
                    f.write(content)
            else:
                self.error_messages.append(f'Error when fetching SRU data, query "{self.query}"')
                content = r.content
                logging.error(self.error_messages[-1])
                is_error = True

        xml = etree.fromstring(content, parser=SruClient.parser)

        if xml.find('.//diag:message', namespaces=SruClient.nsmap) is not None:
            self.error_messages.append(f'{xml.find(".//diag:message", namespaces=SruClient.nsmap).text} '
                                       f'when fetching SRU data, query "{self.query}"')
            logging.error(self.error_messages[-1])
            is_error = True

            xml = etree.fromstring(content, parser=SruClient.parser)

        return xml, is_error

    def _fetch_records(self) -> None:
        """Fetch a list of records from an SRU query
        """

        records = []
        is_error = False

        for i in range(self.limit // 50 + 1):
            start_record = i * 50 + 1
            maximum_records = self.limit - 50 * i if self.limit <= 50 * (i + 1) else 50

            xml, is_error = self._fetch_data(start_record, maximum_records)

            # Get all records
            if is_error is True:
                break

            rec_number_field = xml.find('.//srw:numberOfRecords', namespaces=SruClient.nsmap)

            if rec_number_field is not None:
                rec_number = int(rec_number_field.text)
            else:
                is_error = True
                logging.error('Field "numberOfRecords" is missing')
                break

            if rec_number > self.limit:
                logging.warning(f'{repr(self)}: number of available results exceed the limit provided')
                self.are_more_results_available = True

            new_records = [SruRecord(xml=record) for record
                           in xml.findall('.//m:record', namespaces=SruClient.nsmap)]
            if len(new_records) == 0:
                logging.warning(f'No record found for query {self.query}')
                break

            logging.info(f'Records {start_record} - {start_record + len(new_records) - 1} / {rec_number}'
                         f', "{self.query}": {len(new_records)}')
            records += new_records
            if len(records) == rec_number:
                break

        self.error = is_error
        self.records = records


class SruClient:
    """Class representing an SRU server

    This class is mostly used at the beginning of a process to set
    the base url of the SRU server.

    .. note :: it is possible to change the base url to connect to another SRU server,
        but the already fetched records and requests are stored at the class level. They
        need to be reset.

    :cvar nsmap: dict describing the name spaces used in records
    :cvar parser: `etree.XMLParser` used to parse records
    :cvar records: MMS ID as key and `etree.Element` of the Marc XML of the record as value
    :cvar requests: dict with query__limit pattern as key and :class:`almasru.client.SruRequest` as value
    :ivar base_url: base url of the SRU server
    """
    nsmap = namespaces = {'srw': 'http://www.loc.gov/zing/srw/',
                          'm': 'http://www.loc.gov/MARC21/slim',
                          'diag': 'http://www.loc.gov/zing/srw/diagnostic/'}

    # Clean blank text and help good display of the record when printed
    parser = etree.XMLParser(ns_clean=True, remove_blank_text=True)

    # Contains the SRU server url
    base_url = None

    # These class attributes are used to store results of previous queries
    requests = dict()
    records = dict()

    def __init__(self, base_url: Optional[str] = None) -> None:
        """Construct a new SRU client
        """
        if base_url is not None:
            self.base_url = base_url

        # Create the requests folder if it doesn't exist
        if os.path.isdir('./requests') is False:
            os.mkdir('./requests')

    @classmethod
    def clean_old_requests(cls) -> None:
        """Delete and recreate the requests folder and reset the requests and records attributes"""
        if os.path.isdir('./requests') is True:
            shutil.rmtree('./requests')
        os.mkdir('./requests')

        cls.requests = dict()
        cls.records = dict()

    @classmethod
    def set_base_url(cls, base_url: str) -> None:
        """Set the base url of the SRU client

        It is required to set this parameter before using the client

        :param base_url: base url of the SRU server
        """
        cls.base_url = base_url

    def fetch_records(self, query: str, limit: int = 10) -> 'SruRequest':
        """Fetch records with SRU

        :param query: string containing the sru query
        :param limit: int indicating the max number of records to fetch, 10 is the default value

        :return: :class:`almasru.client.SruRequest`
        """
        if f'{query}__{limit}' not in self.requests:
            req = SruRequest(query, limit, self)
            self.requests[f'{query}__{limit}'] = req

        return self.requests[f'{query}__{limit}']


class SruRecord:
    """Class representing a single XML record from SRU

    Either `xml` or `mms_id` must be provided. If mms_id is provided the constructor
    will fetch the record through SRU query.

    :ivar mms_id: mms_id of the record to fetch
    :ivar error: boolean, is True in case of error
    :ivar error_messages: list of string with the error messages
    :ivar warning: boolean, is True in case of warning
    :ivar warning_messages: list of string containing the warning messages
    """

    def __init__(self, mms_id: Optional[str] = None, xml: Optional[etree.Element] = None):
        """Constructor of SruRecord"""
        self.mms_id = mms_id
        self.error = False
        self.error_messages = []
        self.warning = False
        self.warning_messages = []
        self._child_rec_num_sys = None
        self._child_rec_std_num = None
        self._parent_rec = None

        if SruClient().base_url is None:
            self.error = True
            self.error_messages.append('Base url for SRU server not defined')
            logging.critical('Base url for SRU server not defined')
            exit()

        # MMS_ID provided, fetch record data with SRU
        if mms_id in SruClient().records:
            xml = SruClient().records[mms_id]

        elif mms_id is not None and self.error is False:
            r = SruClient().fetch_records(f'alma.mms_id={mms_id}')
            if r.error is True:
                self.error = True
                self.error_messages += r.error_messages
            else:
                if len(r.records) != 1:
                    self.error = True
                    self.error_messages.append(f'Number of records found: {len(r.records)}, should be only 1')
                    logging.error(f'{repr(self)}: number of records found: {len(r.records)}, should be only 1')
                else:
                    xml = r.records[0].data

        self.data = xml

        if self.error is False:
            self.mms_id = self.get_mms_id()
            SruClient().records[self.mms_id] = xml

    def __str__(self) -> str:
        if self.data is not None:
            return etree.tostring(self.data, pretty_print=True).decode()
        else:
            return ''

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.mms_id}')"

    def __hash__(self) -> int:
        return int(self.mms_id)

    def __eq__(self, other) -> bool:
        return self.mms_id == other.mms_id

    @check_error
    def get_mms_id(self) -> Optional[str]:
        """get_mms_id(self) -> Optional[str]
        Get MMS_ID of the current record

        :return: string containing the MMS_ID, None in case of error or no data available
        """
        if self.data is not None:
            return self.data.find('./m:controlfield[@tag="001"]', namespaces=SruClient.nsmap).text
        else:
            return None

    @check_error
    def get_035_fields(self, var: bool = False, slsp_only: bool = False) -> Set[str]:
        """get_035_fields(self, var: bool = False, slsp_only: bool = False) -> Set[str]
        Return a set of system numbers of 035 fields

        :param var: Parameters: flag indicating if truncated system numbers should be tested
        :param slsp_only: Parameters: flag indicating if only slsp system numbers should be returned

        :return: Set of strings with the system IDs of 035 fields
        """
        other_sys_ids = set([field.text for field in
                             self.data.findall('./m:datafield[@tag="035"]/m:subfield[@code="a"]',
                                               namespaces=SruClient.nsmap)])

        if var is True:
            # return truncated variant of the system numbers too
            var_sys_id = set()
            for sys_num in other_sys_ids:
                m = re.search(r'\d{6,}', sys_num)
                if m is not None:
                    var_sys_id.add(m.group(0))

            other_sys_ids.update(var_sys_id)

        if slsp_only is True:
            # return only SLSP related system ids
            prefixes = '|'.join(['RERO', 'IDSBB', 'IDSLU', 'IDSSG', 'NEBIS', 'SBT', 'ALEX', 'ABN', 'swissbib', 'HAN'])
            other_sys_ids = {sys_num for sys_num in other_sys_ids
                             if re.match(r'^\((?:{})\).+'.format(prefixes), sys_num)}
        return other_sys_ids

    @check_error
    def get_issn(self) -> Set[str]:
        """get_issn(self) -> Set[str]
        Fetch ISSN of the current record

        Fetch the content of all 022$$a

        :return: set of ISSN
        """
        return set([field.text for field in
                    self.data.findall('./m:datafield[@tag="022"]/m:subfield[@code="a"]',
                                      namespaces=SruClient.nsmap)])

    @check_error
    def get_isbn(self) -> Set[str]:
        """get_isbn(self) -> Set[str]
        Fetch ISBN of the current record

        Fetch the content of all 020$$a

        :return: set of ISBN
        """
        return set([field.text.replace('-', '') for field in
                    self.data.findall('./m:datafield[@tag="020"]/m:subfield[@code="a"]',
                                      namespaces=SruClient.nsmap)])

    @check_error
    def get_standard_numbers(self) -> Set[str]:
        """get_standard_numbers(self) -> Set[str]
        Fetch all ISSN and ISBN of the records

        :return: set of standard numbers
        """
        return set.union(self.get_isbn(), self.get_issn())

    @check_error
    def get_bib_level(self) -> Literal['a', 'b', 'c', 'd', 'i', 'm', 's']:
        """get_bib_level(self) -> Literal['a', 'b', 'c', 'd', 'i', 'm', 's']
        Get the bib level of the record

        Fetch the 7th position of the leader field.

        :return: str with the bib level
        """
        leader_field = self.data.find('./m:leader', namespaces=SruClient.nsmap)
        return leader_field.text[7]

    @check_error
    def get_child_rec(self) -> Dict:
        """get_child_rec(self) -> Dict
        check if the records appears in other records

        Check system numbers and standard numbers to find records that are linked
        to the current record.

        :return: dictionary describing the result of analysis. Keys are following:

            * 'MMS_ID':  current record ID
            * 'related_records_found':  boolean indicating if related records have been found
            * 'number_of_rel_recs': number of related records found
            * 'related_records': list of :class:`almasru.client.SruRecords`
            * 'fields_related_records': list of fields.
        """
        rel_rec_sys_num = self.get_child_rec_sys_num()
        rel_rec_std_num = self.get_child_rec_std_num()

        related_record_found = rel_rec_sys_num['related_records_found'] or rel_rec_std_num['related_records_found']
        records = set.union(rel_rec_sys_num['related_records'], rel_rec_std_num['related_records'])
        fields_related_records = rel_rec_sys_num['fields_related_records'] + rel_rec_std_num['fields_related_records']

        related_records = {'MMS_ID': self.mms_id,
                           'related_records_found': related_record_found,
                           'number_of_rel_recs': len(records),
                           'related_records': records,
                           'fields_related_records': fields_related_records,
                           }
        return related_records

    @check_error
    def get_child_rec_sys_num(self) -> Dict:
        """get_child_rec_sys_num(self) -> Dict
        Check if the given system number appears in other records.

        :Return: dictionary describing the result of analysis
        """
        if self._child_rec_num_sys is not None:
            return self._child_rec_num_sys

        # Fetch the system numbers, all 035 + 001 should be tested
        sys_numbers_to_test = self.get_035_fields(slsp_only=True)

        sys_numbers_to_test.add(self.mms_id)

        fields_related_records = []
        records = set()

        # Check the list of system numbers to fetch records
        for sys_num in sys_numbers_to_test:
            # Need two "==" if "_" or "-" in system number
            # https://developers.exlibrisgroup.com/blog/how-to-configure-sru-and-structure-sru-retrieval-queries/
            query = f'alma.other_system_number=={sys_num}' if '-' in sys_num or '_' in sys_num \
                else f'alma.other_system_number={sys_num}'
            req = SruClient().fetch_records(query, limit=500)

            if req.error is True:
                continue

            if req.are_more_results_available is True:
                self.warning = True
                self.warning_messages.append(f'{repr(req)}: not all available child records examined')

            # Filter records
            temp_records = [record for record in req.records
                            if record.error is False            # Suppress records with errors
                            and record.mms_id != self.mms_id    # Suppress the record if it is the source record
                            and len([other_sys_id for other_sys_id in record.get_035_fields()
                                     if other_sys_id.startswith('(CKB)')]) == 0    # Ignore CZ records
                            ]

            if len(temp_records) == 0:
                continue

            # Use to ignore records linked with 035 that are not real children
            temp_records_duplicates = set()

            for record in temp_records:
                temp_fields = record.data.xpath(f'./m:datafield/m:subfield[contains(text(), "{sys_num}")]',
                                                namespaces=SruClient.nsmap)

                if len(temp_fields) > 0:
                    for field in temp_fields:
                        code = field.attrib['code']
                        tag = field.getparent().attrib['tag']

                        if tag == '035':
                            temp_records_duplicates.add(record)
                            self.warning = True
                            self.warning_messages.append(f'More than one record with same 035, {self.mms_id} '
                                                         f'and {record.mms_id} are probably duplicated records')
                        else:
                            fields_related_records.append({'child_MMS_ID': record.mms_id,
                                                           'field': f'{tag}${code}',
                                                           'content': field.text})
                else:
                    logging.warning(f'{repr(self)} record {repr(record)} found with SRU but no linking field')
                    fields_related_records.append({'child_MMS_ID': record.mms_id,
                                                   'field': f'UNKNOWN',
                                                   'content': sys_num})
            # Use sets to avoid duplicated records
            records.update(set(temp_records) - temp_records_duplicates)

        if len(records) == 0:
            related_record_found = False
        else:
            related_record_found = True

        self._child_rec_num_sys = {'MMS_ID': self.mms_id,
                                   'related_records_found': related_record_found,
                                   'number_of_rel_recs': len(records),
                                   'related_records': records,
                                   'fields_related_records': fields_related_records,
                                   }

        return self._child_rec_num_sys

    @check_error
    def get_child_rec_std_num(self) -> Dict:
        """get_child_rec_std_num(self) -> Dict
        Check if the given system number appears in other records.

        :Return: dictionary describing the result of analysis
        """
        if self._child_rec_std_num is not None:
            return self._child_rec_std_num

        # Fetch the system numbers, all 035 + 001 should be tested
        stand_numbers_to_test = self.get_standard_numbers()

        fields_related_records = []
        records = set()

        # Check the list of system numbers to fetch records
        for std_num in stand_numbers_to_test:

            # Query cannot have "==" for standard_number, for this reason we need to remove the "-"
            query = f'alma.standard_number={std_num.replace("-", "")}'

            req = SruClient().fetch_records(query, limit=500)

            if req.error is True:
                continue

            if req.are_more_results_available is True:
                self.warning = True
                self.warning_messages.append(f'{repr(req)}: not all available child records examined')

            # Filter records
            temp_records = [record for record in req.records
                            if record.error is False
                            and record.mms_id != self.mms_id
                            and len(set.intersection(record.get_standard_numbers(), self.get_standard_numbers())) == 0
                            and len([other_sys_id for other_sys_id in record.get_035_fields()
                                     if other_sys_id.startswith('(CKB)')]) == 0
                            ]

            if len(temp_records) == 0:
                continue

            # Use to ignore records linked with 020 or 022 that are not real children
            temp_records_duplicates = set()

            for record in temp_records:
                temp_fields = record.data.xpath(f'./m:datafield/m:subfield[contains(text(), "{std_num}")]',
                                                namespaces=SruClient.nsmap)

                if len(temp_fields) > 0:
                    for field in temp_fields:
                        code = field.attrib['code']
                        tag = field.getparent().attrib['tag']
                        if tag in ['020', '022']:
                            self.warning = True
                            self.warning_messages.append(f'More than one record with same {tag}, {self.mms_id} '
                                                         f'and {record.mms_id} are probably duplicated records')
                        else:
                            fields_related_records.append({'child_MMS_ID': record.mms_id,
                                                           'field': f'{tag}${code}',
                                                           'content': field.text})
                else:
                    logging.warning(f'{repr(self)} record {repr(record)} found with SRU but no linking field')
                    fields_related_records.append({'child_MMS_ID': record.mms_id,
                                                   'field': f'UNKNOWN',
                                                   'content': std_num})
            # Use sets to avoid duplicated records
            records.update(set(temp_records) - temp_records_duplicates)

        if len(records) == 0:
            related_record_found = False
        else:
            related_record_found = True

        self._child_rec_std_num = {'MMS_ID': self.mms_id,
                                   'related_records_found': related_record_found,
                                   'number_of_rel_recs': len(records),
                                   'related_records': records,
                                   'fields_related_records': fields_related_records,
                                   }

        return self._child_rec_std_num

    @check_error
    def get_parent_rec(self) -> Dict:
        """get_parent_rec(self) -> Dict
        Get parents records of the current record

        Uses the content of fields 7xx and 8xx to get all parent records. the method checks standard numbers
        in subfields "x" or "z" and system numbers in "w" subfield.

        :return: dictionary describing the result of the analysis
        """
        if self._parent_rec is not None:
            return self._parent_rec

        # List of datafields to check
        fields_to_test = ['773', '774', '776', '777', '780', '785', '786', '787', '800', '810', '811', '830']

        fields_related_records = []
        records = set()

        # Parse the record to find links to parents
        for field in fields_to_test:
            xml_fields = self.data.findall(f'./m:datafield[@tag="{field}"]', namespaces=SruClient.nsmap)
            for xml_field in xml_fields:

                # In subfield "x" are ISSN and ISBN
                for subfield_code in ['x', 'z']:
                    subfield = xml_field.find(f'./m:subfield[@code="{subfield_code}"]', namespaces=SruClient.nsmap)
                    if subfield is not None:
                        break

                if subfield is not None:
                    std_num = subfield.text

                    # For the search, hyphen should be removed
                    query = f'alma.standard_number={std_num.replace("-", "")}'

                    req = SruClient().fetch_records(query, limit=500)
                    if req.error is True:
                        continue

                    if req.are_more_results_available is True:
                        self.warning = True
                        self.warning_messages.append(f'{repr(req)}: not all available parent records examined')

                    temp_records = [record for record in req.records
                                    if record.error is False
                                    and record.mms_id != self.mms_id
                                    and std_num in record.get_standard_numbers()
                                    and len([other_sys_id for other_sys_id in record.get_035_fields()
                                             if other_sys_id.startswith('(CKB)')]) == 0]

                    records.update(temp_records)

                    if len(temp_records) > 0:
                        fields_related_records.append({'parent_MMS_ID': f'{temp_records[0].mms_id}',
                                                       'field': f'{field}${subfield_code}',
                                                       'content': std_num})

                # In subfield "w" are system numbers
                subfield = xml_field.find('./m:subfield[@code="w"]', namespaces=SruClient.nsmap)
                if subfield is not None:
                    sys_num = subfield.text

                    if re.match(r'^99\d{5,}$', sys_num):
                        query = f'alma.mms_id={sys_num}'
                    else:
                        query = f'alma.other_system_number_active_035=={sys_num}' if '-' in sys_num or '_' in sys_num \
                            else f'alma.other_system_number_active_035={sys_num}'

                    req = SruClient().fetch_records(query, limit=500)
                    if req.error is True:
                        continue

                    if req.are_more_results_available is True:
                        self.warning = True
                        self.warning_messages.append(f'{repr(req)}: not all available parent records examined')

                    temp_records = [record for record in req.records
                                    if record.error is False
                                    and record.mms_id != self.mms_id
                                    and (record.mms_id == sys_num
                                         or sys_num in record.get_035_fields())
                                    and len([other_sys_id for other_sys_id in record.get_035_fields()
                                             if other_sys_id.startswith('(CKB)')]) == 0
                                    ]

                    records.update(temp_records)

                    if len(temp_records) > 0:
                        fields_related_records.append({'parent_MMS_ID': f'{temp_records[0].mms_id}',
                                                       'field': f'{field}$w',
                                                       'content': sys_num})

        self._parent_rec = {'MMS_ID': self.mms_id,
                            'related_records_found': len(records) > 0,
                            'number_of_rel_recs': len(records),
                            'related_records': records,
                            'fields_related_records': fields_related_records,
                            }
        return self._parent_rec

    @check_error
    def get_inventory_info(self) -> List[Dict]:
        """get_inventory_info(self) -> List[Dict]
        Get information about the record in the IZ

        The method analyse the 852 fields and returns a list with dictionaries containing:
        - "IZ": IZ code
        - "MMS ID": MMS ID of the record in the IZ
        - "format": format of the record, "P" for print, "E" for electronic, "D" for digital

        :return: list of records in the IZ linked to the NZ record
        """
        # Fetch 852 fields with inventory information
        fields852 = self.data.xpath(f'./m:datafield[@tag="852"]',
                                    namespaces=SruClient.nsmap)

        # $$a contains the IZ, $$6 contains the iz MMS ID, $$9 contains the format ("P", "E" or "D")
        inventory_info = [{'IZ': f.find('./m:subfield[@code="a"]', namespaces=SruClient.nsmap).text,
                           'MMS ID': f.find('./m:subfield[@code="6"]', namespaces=SruClient.nsmap).text,
                           'format': f.find('./m:subfield[@code="9"]', namespaces=SruClient.nsmap).text}
                          for f in fields852]
        logging.info(f'{repr(self)}: {len(inventory_info)} records in IZ found')
        return inventory_info

    @check_error
    def get_iz_using_rec(self) -> List[str]:
        """get_iz_using_rec(self) -> List[str]
        Get the list of IZ using this record

        This method analyses the 852 fields and returns the list of IZ using the current NZ record.

        :return: list of IZ using this record.
        """
        # Fetch 852 fields with inventory information
        fields852 = self.data.xpath(f'./m:datafield[@tag="852"]',
                                    namespaces=SruClient.nsmap)
        list_izs = [f.find('./m:subfield[@code="a"]', namespaces=SruClient.nsmap).text for f in fields852]
        if len(list_izs) > 0:
            logging.info(f'{repr(self)}: record used in other IZs: {", ".join(list_izs)}')
        else:
            logging.info(f'{repr(self)}: record not used in the IZs')

        return list_izs

    @check_error
    def get_child_analytical_records(self) -> List['SruRecord']:
        """get_child_analytical_records(self) -> List['SruRecord']
        Get the list of analytical records. Check only existing 773 fields and not leader.

        :return: list of :class:`almasru.client.SruRecord`
        """
        children_analysis = self.get_child_rec_sys_num()
        analytical_children = []
        for link in children_analysis['fields_related_records']:
            if link['field'] == '773$w':
                analytical_children.append(SruRecord(link['child_MMS_ID']))

        return analytical_children

    @check_error
    def get_reasons_preventing_deletion(self, removable_rec_mms_id: Optional[List[str]] = None) -> List[str]:
        """analyse(self, removable_rec_mms_id: Optional[List[str]] = None) => List[str]
        Analyse the record to find reasons preventing deletion

        :param removable_rec_mms_id: list of MMS_ID of records that are safe to be removed. This is used to avoid
            records of the list currently being processed to be considered as preventing deletion.

        :return: list of string with the reasons preventing deletion
        """
        # Set default value for removable_rec_mms_id
        if removable_rec_mms_id is None:
            removable_rec_mms_id = []
        messages = []

        # Check if record used by other IZ and has holdings
        list_izs = self.get_iz_using_rec()
        if len(list_izs) > 0:
            logging.info(f'{repr(self)} used in IZs: {", ".join(list_izs)}')
            messages.append(f'Used in IZs: {", ".join(list_izs)}')

        # Filter the list with the list of removable records.
        analytical_children = [rec for rec in self.get_child_analytical_records()
                               if rec.mms_id not in removable_rec_mms_id]

        if len(analytical_children) > 0:
            logging.info(f'{repr(self)} has at least one child '
                         f'analytical record: {repr(analytical_children[0])}')
            messages.append(f'Has child analytical records: {"|".join([rec.mms_id for rec in analytical_children])}')

        # Check if the record has children with inventory. The child must have be linked with a 8xx field
        # or 773. Normally analytical records linked with 773 should not have holdings anyway.
        children = self.get_child_removable_candidate_rec()
        for rec in children:
            used_by_iz = rec.get_iz_using_rec()

            if len(used_by_iz) > 0:
                logging.info(f'{repr(self)} has at least a child record with '
                             f'inventory: {repr(rec)} in '
                             f'{", ".join(used_by_iz)}')
                messages.append(f'Has child preventing deletion record with inventory: {rec.mms_id}')

        # Get the parent records. Only parent that are target of 773 field prevent deletion of the child
        # if the parent has inventory
        parents = self.get_parent_removable_candidate_rec()
        for rec in parents:
            used_by_iz = rec.get_iz_using_rec()
            if len(used_by_iz) > 0:
                logging.info(f'{repr(self)} has at least a parent record with '
                             f'inventory: {repr(rec)} in '
                             f'{", ".join(used_by_iz)}')
                messages.append(f'Has parent record preventing deletion with inventory: {rec.mms_id}')

        return messages

    @check_error
    def is_removable(self, removable_rec_mms_id: Optional[List[str]] = None) -> Tuple[bool, str]:
        """is_removable(self, removable_rec_mms_id: Optional[List[str]] = None) -> Tuple[bool, str]
        Check if a record is safe to be removed

        :param removable_rec_mms_id: list of MMS_ID of records that are safe to be removed. This is used to avoid
            records of the list currently being processed to be considered as preventing deletion.

        The method checks related records and inventory in other IZ.
        1. Test if the record has 852 fields. It would indicate existing holding in any IZ
        2. Test if record has analytical records children (children linked with 773 field)
        3. Test if the record is target of 8xx or 773 fields of other records
        4. Test if the record has a 773 field targeting a record with inventory

        :return: tuple containing bool indicating if the record can be safely removed and a message.
        """
        # Set default value for removable_rec_mms_id
        if removable_rec_mms_id is None:
            removable_rec_mms_id = []

        # Check if record used by other IZ and has holdings
        list_izs = self.get_iz_using_rec()
        if len(list_izs) > 0:
            logging.warning(f'{repr(self)} cannot be deleted: record used in IZs: {", ".join(list_izs)}')
            return False, 'Record used in at least one IZ'

        # No deletion if records has analytical records among children
        # Filter the list with the list of removable records.
        analytical_children = [rec for rec in self.get_child_analytical_records()
                               if rec.mms_id not in removable_rec_mms_id]

        if len(analytical_children) > 0:
            logging.warning(f'{repr(self)} cannot be deleted: record has at least one child '
                            f'analytical record: {repr(analytical_children[0])}')
            return False, 'Has analytical record as child'

        # Check if the record has children with inventory. The child must have be linked with a 8xx field
        # or 773. Normally analytical records linked with 773 should not have holdings anyway.
        children = self.get_child_removable_candidate_rec()
        for rec in children:
            used_by_iz = rec.get_iz_using_rec()

            if len(used_by_iz) > 0:
                logging.warning(f'{repr(self)} cannot be deleted: record has at least a child record with '
                                f'inventory: {repr(rec)} in '
                                f'{", ".join(used_by_iz)}')
                return False, 'Child record has inventory'

        # Get the parent records. Only parent that are target of 773 field prevent deletion of the child
        # if the parent has inventory
        parents = self.get_parent_removable_candidate_rec()
        for rec in parents:
            used_by_iz = rec.get_iz_using_rec()
            if len(used_by_iz) > 0:
                logging.warning(f'{repr(self)} cannot be deleted: record has at least a parent record with '
                                f'inventory: {repr(rec)} in '
                                f'{", ".join(used_by_iz)}')
                return False, 'Parent record has inventory'

        return True, 'REMOVABLE'

    @check_error
    def get_child_removable_candidate_rec(self) -> List['SruRecord']:
        """get_child_removable_candidate_rec(self) -> List['SruRecord']
        Get a list of child related records that are maybe removable

        Fetch records containing specific field with link to the current record. Considered fields
        are '773', '800', '810', '811', '830'.

        :return: list of :class:`almasru.client.SruRecord`
        """

        # Check if the record has children with inventory. The child must have be linked with a 8xx field
        # or 773. Normally analytical records linked with 773 should not have holdings anyway.
        children = self.get_child_rec()
        children_mms_id = set([field['child_MMS_ID'] for field in children['fields_related_records']
                              if field['field'][:3] in ['773', '800', '810', '811', '830']])

        # NOTE: le 773 empêche la suppression: code à corriger
        return [SruRecord(mms_id) for mms_id in children_mms_id]

    @check_error
    def get_parent_removable_candidate_rec(self) -> List['SruRecord']:
        """get_parent_removable_candidate_rec(self) -> List['SruRecord']
        Get a list of child related records that are maybe removable

        Check 773 of the current record and look for potential parent records.

        :return: list of :class:`almasru.client.SruRecord`
        """
        # Get the parent records. Only parent that are target of 773 field prevent deletion of the child
        # if the parent has inventory
        parents = self.get_parent_rec()
        parents_mms_id = set([field['parent_MMS_ID'] for field in parents['fields_related_records']
                              if field['field'][:3] == '773'])
        return [SruRecord(mms_id) for mms_id in parents_mms_id]

    @check_error
    def save(self) -> None:
        """save(self) -> None
        Save the xml data of the record in the `./records` folder. Filename
        is `rec_<mms_id>.xml`

        :return: None
        """

        # Create the directory if not already existing
        if os.path.isdir('./records') is False:
            os.mkdir('./records')

        with open(f'./records/rec_{self.mms_id}.xml', 'w') as f:
            f.write(str(self))
