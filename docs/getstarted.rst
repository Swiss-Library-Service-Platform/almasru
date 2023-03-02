Get started
===========

Installation
------------

.. code-block:: bash

    pip install almasru

Logs
----
It is possible to configure the logs. The log files are stored in the
`./log` folder.

.. code-block:: python

    from almasru import config_log

    # Will store the logs in the `./log/test.log` file
    config_log("test.log")

Records backups
---------------
The `save` method of all records creates a backup of the record in the
`./records` folder.

Check if records are removable
------------------------------
The library can check if a record is removable. It checks if inventory
exists or related records. Cannot be deleted:

* Record with inventory in any IZ (electronic, digital or print)
* Child record linked with 773 field if the parent has inventory
* Parent records with children having inventory (linked with 8XX)

Orphan children or parents are also tested.

.. code-block:: python

    # Import libraries
    from almasru.client import SruClient, SruRecord, SruRequest
    from almasru.utils import check_removable_records
    from almasru import config_log
    import pandas as pd

    SruClient.set_base_url('https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK')

    # Config logs
    config_log()

    df = check_removable_records(['991089939809705501', '991130348859705501'])
    df.to_excel('report.xlsx')
