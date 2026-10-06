"""
File: test_ldap.py
Purpose: Minimal pure-Python LDAP connectivity experiment.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from ldap3 import (
    ALL,
    Connection,
    Server,
)

LDAP_SERVER = "user.ADXRT.com"

server = Server(
    LDAP_SERVER,
    get_info=ALL,
)

print("LDAP server:", LDAP_SERVER)
print("Connecting...")

connection = Connection(
    server,
    auto_bind=False,
)

try:
    connected = connection.open()

    print("Connection opened:", connected)
    print("Bound:", connection.bound)

    if connection.server.info:
        print("\nServer information:")
        print(connection.server.info)

except Exception as error:
    print("\nLDAP connection failed:")
    print(type(error).__name__)
    print(str(error))

finally:
    connection.unbind()
    print("\nConnection closed.")
