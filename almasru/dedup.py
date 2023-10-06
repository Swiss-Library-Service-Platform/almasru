import pandas as pd
import numpy as np
import unicodedata
import re
from Levenshtein import distance
import itertools
from lxml import etree

from typing import Callable


def handling_missing_values(fn: Callable) -> Callable:
    def wrapper(val1, val2):

        if val1 is None or val2 is None:
            return np.nan
        if type(val1) is list or type(val2) is list:
            if len(val1) == 0 or len(val2) == 0:
                return np.nan

        return fn(val1, val2)

    return wrapper


def get_ascii(txt):
    return unicodedata.normalize('NFD', txt).encode('ascii', 'ignore').decode().upper()


@handling_missing_values
def evaluate_year(year1, year2):
    return 1 / ((abs(year1 - year2) * .5) ** 2 + 1)


@handling_missing_values
def evaluate_identifiers(ids1, ids2):
    ids1 = set(ids1)
    ids2 = set(ids2)
    if len(set.union(ids1, ids2)) > 0:
        score = len(set.intersection(ids1, ids2)) / len(set.union(ids1, ids2))
        return score ** .05 if score > 0 else 0
    else:
        np.nan


@handling_missing_values
def evaluate_extent(extent1, extent2):
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
    return (score1 + score2) / 2


def get_unique_combinations(l1, l2):
    if len(l1) < len(l2):
        l2, l1 = (l1, l2)

    unique_combinations = []
    permut = itertools.permutations(l1, len(l2))

    # zip() is called to pair each permutation
    # and shorter list element into combination
    for comb in permut:
        zipped = zip(comb, l2)
        unique_combinations.append(list(zipped))
    return unique_combinations


@handling_missing_values
def evaluate_lists_texts(texts1, texts2):
    if len(texts1) < len(texts2):
        texts2, texts1 = (texts1, texts2)
    unique_combinations = get_unique_combinations(texts1, texts2)

    return max([np.mean([evaluate_texts(*p) for p in comb]) for comb in unique_combinations])


@handling_missing_values
def evaluate_lists_names(names1, names2):
    """Return the result of the best pairing authors.

    The function test all possible pairings and return the max value.
    """
    if len(names1) < len(names2):
        names2, names1 = (names1, names2)

    unique_combinations = get_unique_combinations(names1, names2)

    return max([np.mean([evaluate_names(*p) for p in comb]) for comb in unique_combinations])


@handling_missing_values
def evaluate_names(name1, name2):
    names1 = [get_ascii(re.sub(r'\W', '', n).lower()) for n in name1.split()]
    names2 = [get_ascii(re.sub(r'\W', '', n).lower()) for n in name2.split()]

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
def evaluate_texts(text1, text2):
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
def evaluate_format(format1, format2):
    return int(format1 == format2)


@handling_missing_values
def evaluate_completeness(b1, b2):
    nb_common_existing_fields = 0
    for k in b1:
        if (b1[k] is None) == (b2[k] is None):
            nb_common_existing_fields += 1
    return 1 / (1 + (len(b1) - nb_common_existing_fields))


def evaluate_similarity(bib1, bib2):
    results = {
        'format': evaluate_format(bib1['format'], bib2['format']),
        'title': evaluate_texts(bib1['title'], bib2['title']),
        'short_title': evaluate_texts(bib1['short_title'], bib2['short_title']),
        'editions': evaluate_lists_texts(bib1['editions'], bib2['editions']),
        'authors': evaluate_lists_names(bib1['authors'], bib2['authors']),
        'date_1': evaluate_year(bib1['date_1'], bib2['date_1']),
        'date_2': evaluate_year(bib1['date_2'], bib2['date_2']),
        'publishers': evaluate_lists_texts(bib1['publishers'], bib2['publishers']),
        'series': evaluate_lists_texts(bib1['series'], bib2['series']),
        'extent': evaluate_extent(bib1['extent'], bib2['extent']),
        'isbns': evaluate_identifiers(bib1['isbns'], bib2['isbns']),
        'issns': evaluate_identifiers(bib1['issns'], bib2['issns']),
        'sysnums': evaluate_identifiers(bib1['sysnums'], bib2['sysnums']),
        'same_fields_existing': evaluate_completeness(bib1, bib2)
    }
    return results