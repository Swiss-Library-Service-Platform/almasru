import pandas as pd
import numpy as np
import unicodedata
import re
from Levenshtein import distance
import itertools
from sklearn.neural_network import MLPClassifier
from copy import deepcopy
from .briefrecord import BriefRecFactory

from typing import Callable, List, Tuple, Dict, Any, Optional


def handling_missing_values(fn: Callable) -> Callable:
    """Decorator to handle missing values."""
    def wrapper(val1, val2):

        if val1 is None or val2 is None:
            return np.nan
        if type(val1) is list or type(val2) is list:
            if len(val1) == 0 or len(val2) == 0:
                return np.nan

        return fn(val1, val2)

    wrapper.__doc__ = fn.__doc__

    return wrapper


def get_ascii(txt: str) -> str:
    """get_ascii(txt: str) -> str
    Return the ascii version of a string.

    :param txt: string to convert

    :return: ascii version of the string
    """
    return unicodedata.normalize('NFD', txt).encode('ascii', 'ignore').decode().upper()


@handling_missing_values
def evaluate_year(year1: int, year2: int) -> float:
    """evaluate_year(year1: int, year2: int) -> float
    Return the result of the evaluation of similarity of two years.

    :param year1: year to compare
    :param year2: year to compare

    :return: similarity score between two years as float
    """
    return 1 / ((abs(year1 - year2) * .5) ** 2 + 1)


@handling_missing_values
def evaluate_identifiers(ids1: str, ids2: str) -> float:
    """evaluate_identifiers(ids1: str, ids2: str) -> float
    Return the result of the evaluation of similarity of two lists of identifiers.

    :param ids1: list of identifiers to compare
    :param ids2: list of identifiers to compare

    :return: similarity score between two lists of identifiers as float
    """
    ids1 = set(ids1)
    ids2 = set(ids2)
    if len(set.union(ids1, ids2)) > 0:
        score = len(set.intersection(ids1, ids2)) / len(set.union(ids1, ids2))
        return score ** .05 if score > 0 else 0
    else:
        return np.nan


@handling_missing_values
def evaluate_sysnums(ids1: str, ids2: str) -> float:
    """evaluate_identifiers(ids1: str, ids2: str) -> float
    Return the result of the evaluation of similarity of two lists of system numbers.

    It considers only the system numbers with the same prefix.

    :param ids1: list of system numbers to compare
    :param ids2: list of system numbers to compare

    :return: similarity score between two lists of system numbers as float
    """

    def get_prefix(recid: str) -> Optional[str]:
        """Return the prefix of a recid if it exists, None otherwise

        :param recid: system number

        :return: prefix of the recid if it exists, None otherwise
        """
        prefix_m = re.search(r'^\(.+\)', recid)
        if prefix_m is not None:
            return prefix_m.group(0)

    ids1 = set(ids1)
    ids2 = set(ids2)
    prefixes_ids1 = set([get_prefix(recid) for recid in ids1 if get_prefix(recid) is not None])
    prefixes_ids2 = set([get_prefix(recid) for recid in ids2 if get_prefix(recid) is not None])
    if len(set.intersection(prefixes_ids1, prefixes_ids2)) == 0:
        # No common prefix: difference means nothing
        return np.nan

    elif len(set.union(ids1, ids2)) > 0:
        score = len(set.intersection(ids1, ids2)) / len(set.union(ids1, ids2))
        return score ** .05 if score > 0 else 0
    else:
        return np.nan


@handling_missing_values
def evaluate_language(lang1: str, lang2: str) -> float:
    """evaluate_language(lang1: str, lang2: str) -> float
    Return the result of the evaluation of similarity of two languages.

    :param lang1: language to compare
    :param lang2: language to compare

    :return: similarity score between two languages as float
    """
    if lang1 == lang2:
        return 1
    else:
        return 0


def evaluate_is_analytical(format1: str, format2: str) -> float:
    """evaluate_is_analytical(format1: str, format2: str) -> float
    Check if records are analytical records

    :param format1: format to compare
    :param format2: format to compare

    :return: 0 if no analytical, 1 if both analytical, 0.5 otherwise.
    """
    if format1[1] == 'a' and format2[1] == 'a':
        return 1
    elif format1[1] == 'a' or format2[1] == 'a':
        return 0.5
    else:
        return np.nan


def evaluate_is_series(format1: str, format2: str) -> Optional[float]:
    """evaluate_is_series(format1: str, format2: str) -> Optional[float]
    Check if records are series

    :param format1: format to compare
    :param format2: format to compare

    :return: nan if no series, 1 if both series, 0.5 otherwise.
    """

    if format1[1] == 's' and format2[1] == 's':
        return 1
    elif format1[1] == 's' or format2[1] == 's':
        return 0.5
    else:
        return np.nan


@handling_missing_values
def evaluate_extent(extent1: List[int], extent2: List[int]) -> float:
    """evaluate_extent(extent1: List[int], extent2: List[int]) -> float
    Return the result of the evaluation of similarity of two extents.

    :param extent1: list of extent to compare
    :param extent2: list of extent to compare

    :return: similarity score between two extents as float
    """
    extent1 = set(extent1)
    extent2 = set(extent2)
    score1 = len(set.intersection(extent1, extent2)) / len(set.union(extent1, extent2))
    extent1_bis = set()
    extent2_bis = set()
    for v in extent1:
        if v >= 20:
            extent1_bis.add(v // 10 * 10)
            extent1_bis.add((v // 10 - 1) * 10)
        else:
            extent1_bis.add(v)
    for v in extent2:
        if v >= 20:
            extent2_bis.add(v // 10 * 10)
            extent2_bis.add((v // 10 - 1) * 10)
        else:
            extent2_bis.add(v)

    score2 = len(set.intersection(extent1_bis, extent2_bis)) / len(set.union(extent1_bis, extent2_bis))
    # Score 3 is used to compare the sum of the extent its less pondered
    score3 = (1 - np.abs(sum(extent1) - sum(extent2)) / (sum(extent1) + sum(extent2)))\
        if sum(extent1) + sum(extent2) > 0 else 0
    return (score1 + score2 + score3) / 3


def get_unique_combinations(l1: List[str], l2: List[str]) -> List[List[Tuple]]:
    """get_unique_combinations(l1: List[str], l2: List[str]) -> List[List[Tuple]]
    Used to search the best match with names like authors or publishers.

    :param l1: list of names to compare
    :param l2: list of names to compare

    :return: list of unique combinations of names
    """
    if len(l1) < len(l2):
        l2, l1 = (l1, l2)

    unique_combinations = []
    permutations = itertools.permutations(l1, len(l2))

    # zip() is called to pair each permutation
    # and shorter list element into combination
    for permutation in permutations:
        zipped = zip(permutation, l2)
        unique_combinations.append(list(zipped))
    return unique_combinations


@handling_missing_values
def evaluate_lists_texts(texts1: List[str], texts2: List[str]) -> float:
    """evaluate_lists_texts(texts1: List[str], texts2: List[str]) -> float

    Return the result of the best pairing texts.

    :param texts1: list of texts to compare
    :param texts2: list of texts to compare

    :return: similarity score between two lists of texts as float
    """
    if len(texts1) < len(texts2):
        texts2, texts1 = (texts1, texts2)
    unique_combinations = get_unique_combinations(texts1, texts2)

    return max([np.mean([evaluate_texts(*p) for p in comb]) for comb in unique_combinations])


@handling_missing_values
def evaluate_lists_names(names1: List[str], names2: List[str]) -> float:
    """evaluate_lists_names(names1: List[str], names2: List[str]) -> float
    Return the result of the best pairing authors.

    The function test all possible pairings and return the max value.

    :param names1: list of names to compare
    :param names2: list of names to compare

    :return: similarity score between two lists of names as float
    """
    if len(names1) < len(names2):
        names2, names1 = (names1, names2)

    if len(names1) < 5:

        unique_combinations = get_unique_combinations(names1, names2)

        return max([np.mean([evaluate_names(*p) for p in comb]) for comb in unique_combinations])
    else:
        # When more than 4 names => not possible to test all combinations
        # Find only the best matches
        scores = []
        for n2 in names2:
            s_max = -1
            n1_temp = None
            for n1 in names1:
                s = evaluate_names(n1, n2)
                if s > s_max:
                    s_max = s
                    n1_temp = n1

            # Remove the best match to avoid to use it twice
            names1.remove(n1_temp)
            scores.append(s_max)

        # Return only the value of the 4 best matches
        return np.mean(sorted(scores, reverse=True)[:4])


@handling_missing_values
def evaluate_names(name1: str, name2: str) -> float:
    """evaluate_names(name1: str, name2: str) -> float
    Return the result of the evaluation of similarity of two names.

    :param name1: name to compare
    :param name2: name to compare

    :return: similarity score between two names as float
    """
    names1 = [get_ascii(re.sub(r'\W', '', n).lower())
              for n in name1.split()]
    names2 = [get_ascii(re.sub(r'\W', '', n).lower())
              for n in name2.split()]

    names1 = [n for n in names1 if n != '']
    names2 = [n for n in names2 if n != '']

    if len(names1) > len(names2):
        names1, names2 = (names2, names1)

    names1 += [''] * (len(names2) - len(names1))

    scores = []
    already_used_n2 = []
    for r1, n1 in enumerate(names1):
        temp_scores = []
        for r2, n2 in enumerate(names2):
            if r2 in already_used_n2:
                continue
            temp_n1, temp_n2 = (n1, n2) if len(n1) >= len(n2) else (n2, n1)
            if len(temp_n2) <= 2:
                temp_scores.append((
                    (distance(temp_n1[:len(temp_n2)], temp_n2, weights=(1, 1, 1)) * 4 + 0.2 * abs(r1 - r2) + len(
                        temp_n1) - len(temp_n2)) / max([len(n2), len(n1)]), r2)
                )
            else:
                temp_scores.append((
                    (distance(temp_n1, temp_n2, weights=(1, 1, 1)) * 4 + 0.2 * abs(r1 - r2) + len(temp_n1) - len(
                        temp_n2)) / max([len(n2), len(n1)]), r2)
                )
                # print(temp_n1, temp_n2, distance(temp_n1, temp_n2[:len(temp_n1)], weights=(1, 1, 1)) * 3)

        temp_scores = sorted(temp_scores, key=lambda x: x[0])
        if n1 == '':
            scores.append((n1, names2[temp_scores[0][1]], 0.2))
        else:
            scores.append((n1, names2[temp_scores[0][1]], temp_scores[0][0] ** 2))
        already_used_n2.append(temp_scores[0][1])

    return 1 / (sum([s[2] for s in scores]) + 1)


@handling_missing_values
def evaluate_texts(text1: str, text2: str) -> float:
    """evaluate_texts(text1: str, text2: str) -> float
    Return the result of the evaluation of similarity of two texts.

    :param text1: text to compare
    :param text2: text to compare

    :return: similarity score between two texts as float
    """
    if len(text1) < len(text2):
        text1, text2 = (text2, text1)
    coef = len(text1) - len(text2) + 1
    text1_ascii = get_ascii(text1)
    text2_ascii = get_ascii(text2)

    score = distance(text1, text2, weights=(1, 0, 1)) * coef
    score += distance(text1, text2, weights=(0, 1, 0))
    score += distance(text1_ascii, text2_ascii, weights=(1, 0, 1)) * coef * 4
    score += distance(text1_ascii, text2_ascii, weights=(0, 1, 0)) * 4

    sum_max = (coef * len(text2) + coef - 1) * 5

    return 1 - score / sum_max


@handling_missing_values
def evaluate_format(format1: str, format2: str) -> float:
    """evaluate_format(format1: str, format2: str) -> float
    Return the result of the evaluation of similarity of two formats

    If format is the same it returns 1, 0 otherwise

    :param format1: format to compare
    :param format2: format to compare

    :return: similarity score between two formats as float"""
    format1 = format1.split('/')
    format2 = format2.split('/')
    leader1 = format1[0].strip()
    leader2 = format2[0].strip()

    # Compare leader => 0.4 max
    score = 0.4 if leader1 == leader2 else 0

    # Compare fields 33X => 0.6 max for the 3 fields
    f33x_1 = format1[1].strip().split(';')
    f33x_2 = format2[1].strip().split(';')
    for i in range(len(f33x_1)):
        if len(f33x_2) > i:
            if f33x_1[i] == f33x_2[i]:
                score += 0.2
            elif f33x_1[i].strip() == '' or f33x_2[i].strip() == '':
                score += 0.1

    return score


@handling_missing_values
def evaluate_parents(parent1: Dict, parent2: Dict) -> float:
    """evaluate_parents(parent1: Dict, parent2: Dict) -> float
    Evaluate similarity based on the link to the parent

    Keys of the parent dictionary:
    - title: title of the parent
    - issn: content of $x
    - isbn: content of $z
    - number: content of $g no:<content>
    - year: content of $g yr:<content> or first 4 digits numbers in a $g
    - parts: longest list of numbers in a $g

    :param parent1: dictionary with parent information
    :param parent2: dictionary with parent information

    :return: similarity score between two parents
    """

    score_title = 0
    score_identifiers = None
    score_year = None
    score_no = None
    score_parts = None

    if 'title' in parent1 and 'title' in parent2:
        score_title = evaluate_texts(parent1['title'], parent2['title'])

    if 'issn' in parent1 and 'issn' in parent2:
        score_identifiers = evaluate_identifiers([parent1['issn']], [parent2['issn']])
    elif 'isbn' in parent1 and 'isbn' in parent2:
        score_identifiers = evaluate_identifiers([parent1['isbn']], [parent2['isbn']])

    if 'number' in parent1 and 'number' in parent2:
        score_no = int(BriefRecFactory.normalize_extent(parent1['number']) ==
                       BriefRecFactory.normalize_extent(parent2['number']))

    if 'year' in parent1 and 'year' in parent2:
        score_year = int(parent1['year'] == parent2['year'])

    for p in [parent1, parent2]:

        # Create parts field if not present => used to compare two records with parts fields
        if 'parts' not in p:
            parts = []
            if 'number' in p:
                parts += BriefRecFactory.normalize_extent(p['number'])
            if 'year' in p:
                parts.append(p['year'])
            if len(parts) > 0:
                p['parts'] = parts

    parent1 = deepcopy(parent1)
    parent2 = deepcopy(parent2)
    if 'parts' in parent1 and 'parts' in parent2:
        initial_nb = sum([len(parent1['parts']), len(parent2['parts'])])
        to_delete = []
        for e in parent1['parts']:
            if e in parent2['parts']:
                to_delete.append(e)
                parent2['parts'].remove(e)
        for e in to_delete:
            parent1['parts'].remove(e)

        to_delete = []
        for e in parent2['parts']:
            if e in parent1['parts']:
                to_delete.append(e)
                parent1['parts'].remove(e)
        for e in to_delete:
            parent2['parts'].remove(e)

        final_nb = sum([len(parent1['parts']), len(parent2['parts'])])
        score_parts = 1 - final_nb / initial_nb

    elif 'parts' in parent1 or 'parts' in parent2:
        # Case if part information is only in one record available
        score_parts = 0

    return score_title * np.mean([s for s in [score_title, score_no, score_year, score_identifiers, score_parts]
                                  if s is not None])


@handling_missing_values
def evaluate_completeness(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float:
    """evaluate_completeness(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float

    Return the result of the evaluation of similarity of two bib records in number
    of available fields.

    :param bib1: dict containing the data of a bib record
    :param bib2: dict containing the data of a bib record

    :return: similarity score between two bib records as float
    """
    nb_common_existing_fields = 0

    for k in bib1:
        if (bib1[k] is None) == (bib2[k] is None):
            nb_common_existing_fields += 1

    return 1 / (1 + (len(bib1) - nb_common_existing_fields))


def evaluate_similarity(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> Dict[str, float]:
    """evaluate_similarity(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> Dict[str, float]
    The function returns a dictionary with keys corresponding to the fields of the bib
    records and values corresponding to the similarity score of the fields.

    :param bib1: Dict[str, Any] containing the data of a bib record
    :param bib2: Dict[str, Any] containing the data of a bib record

    Return the result of the evaluation of similarity of two bib records."""
    results = {
        'format': evaluate_format(bib1['format'], bib2['format']),
        'title': evaluate_texts(bib1['title'], bib2['title']),
        'short_title': evaluate_texts(bib1['short_title'], bib2['short_title']),
        'editions': evaluate_lists_texts(bib1['editions'], bib2['editions']),
        'creators': evaluate_lists_names(bib1['creators'], bib2['creators']),
        'corp_creators': evaluate_lists_names(bib1['corp_creators'], bib2['corp_creators']),
        'language': evaluate_language(bib1['language'], bib2['language']),
        'date_1': evaluate_year(bib1['date_1'], bib2['date_1']),
        'date_2': evaluate_year(bib1['date_2'], bib2['date_2']),
        'publishers': evaluate_lists_texts(bib1['publishers'], bib2['publishers']),
        'series': evaluate_lists_texts(bib1['series'], bib2['series']),
        'extent': evaluate_extent(bib1['extent'], bib2['extent']),
        'isbns': evaluate_identifiers(bib1['isbns'], bib2['isbns']),
        'issns': evaluate_identifiers(bib1['issns'], bib2['issns']),
        'other_std_num': evaluate_identifiers(bib1['other_std_num'], bib2['other_std_num']),
        'parent': evaluate_parents(bib1['parent'], bib2['parent']),
        'sysnums': evaluate_sysnums(bib1['sysnums'], bib2['sysnums']),
        'same_fields_existing': evaluate_completeness(bib1, bib2),
        'are_analytical': evaluate_is_analytical(bib1['format'], bib2['format']),
        'are_series': evaluate_is_series(bib1['format'], bib2['format']),
    }
    return results


def get_similarity_score(bib1: Dict[str, Any],
                         bib2: Dict[str, Any],
                         clf: Optional[MLPClassifier] = None,
                         nan: Optional[float] = 0) -> float:
    """get_similarity_score(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float
    Get the similarity score between two bib records.

    With classifiers, the function returns the similarity score between two bib records. The threshold
    to determine if two records are similar or not is 0.5.

    :param bib1: Dict[str, Any] containing the data of a bib record
    :param bib2: Dict[str, Any] containing the data of a bib record
    :param clf: MLPClassifier used to predict the similarity score if none is given the function will
        calculate the mean of the similarity scores of the fields
    :param nan: value to use if the similarity score is NaN

    :return: similarity score between two bib records as float
    """
    results = evaluate_similarity(bib1, bib2)

    if clf is not None:
        # Columns used in BriefRec to analyse similarity
        columns = ['format',
                   'title',
                   'short_title',
                   'editions',
                   'creators',
                   'corp_creators',
                   'language',
                   'date_1',
                   'date_2',
                   'publishers',
                   'series',
                   'extent',
                   'isbns',
                   'issns',
                   'other_std_num',
                   'parent',
                   'sysnums',
                   'same_fields_existing',
                   'are_analytical',
                   'are_series']

        # Prepare DataFrame to save similarity evaluations
        df = pd.DataFrame(columns=columns)
        df.loc[0] = results
        df = df.fillna(nan)

        # Predict similarity score, first index to get the first row and second index to get probability of True.
        # 0.5 is the threshold to determine if two records are similar or not
        return clf.predict_proba(df)[0][1]
    else:
        return np.mean([results[k] for k in results if pd.isna(results[k]) is False])
