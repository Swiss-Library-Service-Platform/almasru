import pandas as pd
import numpy as np
import unicodedata
import re
from Levenshtein import distance
import itertools
from lxml import etree

from typing import Callable, List, Tuple, Dict, Any


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

    Return the ascii version of a string."""
    return unicodedata.normalize('NFD', txt).encode('ascii', 'ignore').decode().upper()


@handling_missing_values
def evaluate_year(year1: int, year2: int) -> float:
    """evaluate_year(year1: int, year2: int) -> float

    Return the result of the evaluation of similarity of two years."""
    return 1 / ((abs(year1 - year2) * .5) ** 2 + 1)


@handling_missing_values
def evaluate_identifiers(ids1: str, ids2: str) -> float:
    """evaluate_identifiers(ids1: str, ids2: str) -> float

    Return the result of the evaluation of similarity of two lists of identifiers."""
    ids1 = set(ids1)
    ids2 = set(ids2)
    if len(set.union(ids1, ids2)) > 0:
        score = len(set.intersection(ids1, ids2)) / len(set.union(ids1, ids2))
        return score ** .05 if score > 0 else 0
    else:
        return np.nan


@handling_missing_values
def evaluate_extent(extent1: List[int], extent2: List[int]) -> float:
    """evaluate_extent(extent1: List[int], extent2: List[int]) -> float

    Return the result of the evaluation of similarity of two extents."""
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
    return (score1 + score2 + score3 / 2) / 2.5


def get_unique_combinations(l1: List[str], l2: List[str]) -> List[List[Tuple]]:
    """get_unique_combinations(l1: List[str], l2: List[str]) -> List[List[Tuple]]

    Used to search the best match with names like authors or publishers."""
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

    Return the result of the best pairing texts."""
    if len(texts1) < len(texts2):
        texts2, texts1 = (texts1, texts2)
    unique_combinations = get_unique_combinations(texts1, texts2)

    return max([np.mean([evaluate_texts(*p) for p in comb]) for comb in unique_combinations])


@handling_missing_values
def evaluate_lists_names(names1: List[str], names2: List[str]) -> float:
    """evaluate_lists_names(names1: List[str], names2: List[str]) -> float

    Return the result of the best pairing authors.

    The function test all possible pairings and return the max value.
    """
    if len(names1) < len(names2):
        names2, names1 = (names1, names2)

    unique_combinations = get_unique_combinations(names1, names2)

    return max([np.mean([evaluate_names(*p) for p in comb]) for comb in unique_combinations])


@handling_missing_values
def evaluate_names(name1: str, name2: str) -> float:
    """evaluate_names(name1: str, name2: str) -> float

    Return the result of the evaluation of similarity of two names."""
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

    Return the result of the evaluation of similarity of two texts."""
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

    Return the result of the evaluation of similarity of two formats"""
    return float(format1 == format2)


@handling_missing_values
def evaluate_completeness(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float:
    """evaluate_completeness(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float

    Return the result of the evaluation of similarity of two bib records in number
    of available fields."""
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
        'date_1': evaluate_year(bib1['date_1'], bib2['date_1']),
        'date_2': evaluate_year(bib1['date_2'], bib2['date_2']),
        'publishers': evaluate_lists_texts(bib1['publishers'], bib2['publishers']),
        'series': evaluate_lists_texts(bib1['series'], bib2['series']),
        'extent': evaluate_extent(bib1['extent'], bib2['extent']),
        'isbns': evaluate_identifiers(bib1['isbns'], bib2['isbns']),
        'issns': evaluate_identifiers(bib1['issns'], bib2['issns']),
        'other_std_num': evaluate_identifiers(bib1['other_std_num'], bib2['other_std_num']),
        'sysnums': evaluate_identifiers(bib1['sysnums'], bib2['sysnums']),
        'same_fields_existing': evaluate_completeness(bib1, bib2)
    }
    return results


def get_similarity_score(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float:
    """get_similarity_score(bib1: Dict[str, Any], bib2: Dict[str, Any]) -> float

    :param bib1: Dict[str, Any] containing the data of a bib record
    :param bib2: Dict[str, Any] containing the data of a bib record

    :return: similarity score between two bib records as float"""
    results = evaluate_similarity(bib1, bib2)
    return np.mean([results[k] for k in results if pd.isna(results[k]) is False])
