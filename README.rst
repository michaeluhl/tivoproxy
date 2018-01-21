tivoproxy
=========

A small server that handles the listens for commands from the
`tivoskill <https://github.com/michaeluhl/tivoskill>`__ Alexa
skill, executes those commands using
`libtivomind <https://github.com/michaeluhl/libtivomind>`__, and
returns the results to the skill.  `pubnub <https://www.pubnub.com/>`__
is used to facilitate communication between ``tivoskill`` and
``tivoproxy``.

Requires a configuration file (.ini format) that contains the
following keys:

.. code:: ini

    [PNObjectServer]
    PUBKEY=pub-c-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    SUBKEY=sub-c-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    CLIENT_ID=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    SUBSCRIBE_CHANNEL=C_QUERY
    PUBLISH_CHANNEL=C_RESP

    [TiVoProxy]
    CERT_PWD=XXXXXXXXX
    CERT_PATH=./support/cdata.pem
    TIVO_ADDR=XXX.XXX.XXX.XXX
    TIVO_MAK=XXXXXXXXX
    TIVO_TZ=US/Eastern

Where ``PUBKEY`` and ``SUBKEY`` are a PubNub pub/sub key pair.  
``CLIENT_ID`` is a UUID representing this client to PubNub.  
``SUBSCRIBE_CHANNEL`` is the PubNub channel on which ``tivoskill``
will listen for commands and ``PUBLISH_CHANNEL`` is the channel
on which it will return its results.

``CERT_PWD`` is the encryption password for the certificate specified
by ``CERT_PATH`` that is used for the connection to the TiVo.
``TIVO_ADDR`` is the IP address of the TiVo unit to be controlled by
the skill.  ``TIVO_MAK`` is the media access key of that TiVo unit.

