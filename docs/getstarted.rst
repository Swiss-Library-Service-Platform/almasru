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
