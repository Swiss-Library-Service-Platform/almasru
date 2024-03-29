***************************
almasru documentation |doc|
***************************

.. |doc| image:: https://readthedocs.org/projects/almasru/badge/?version=latest
    :target: https://almasru.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

How to import modules
---------------------

.. code-block:: python

    # Import libraries
    from almasru.client import SruClient, SruRecord, IzSruRecord, SruRequest
    from almasru.utils import check_removable_records, analyse_records
    from almasru import dedup
    from almasru.briefrecord import BriefRecFactory, BriefRec
    from almasru import config_log

    # Config logs
    config_log()

Contents
--------

.. toctree::
   :maxdepth: 1

   getstarted
   configlog
   sruclient
   srurequest
   srurecord
   izsrurecord
   briefrec
   dedup
   utils

Indices and tables
==================

* :ref:`genindex`

