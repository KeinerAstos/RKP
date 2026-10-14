"""Cliente comun para consultas MySQL."""

import socket
from ipaddress import ip_address
from typing import Any

import mysql.connector
from mysql.connector import Error
from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import InterfaceError
from mysql.connector.network import MySQLTCPSocket

from .config import settings


class SocketMySQLConOrigen(MySQLTCPSocket):
    def __init__(self, source_address: str, **kwargs):
        super().__init__(**kwargs)
        self.source_address = source_address

    def open_connection(self) -> None:
        try:
            self.sock = socket.create_connection(
                (self.server_host, self.server_port),
                timeout=self._connection_timeout,
                source_address=(self.source_address, 0),
            )
            self._family = self.sock.family
        except OSError as exc:
            raise InterfaceError(
                f"No se pudo conectar a MySQL "
                f"{self.server_host}:{self.server_port} "
                f"desde {self.source_address}: {exc}"
            ) from exc


class ConexionMySQLConOrigen(MySQLConnection):
    def __init__(self, source_address: str, **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def _get_connection(self):
        conexion_socket = SocketMySQLConOrigen(
            source_address=self.source_address,
            host=self.server_host,
            port=self.server_port,
            force_ipv6=self._force_ipv6,
        )
        conexion_socket.set_connection_timeout(
            self._connection_timeout
        )
        return conexion_socket


def crear_conexion():
    kwargs = {
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "database": settings.mysql_database,
        "connection_timeout": settings.mysql_connect_timeout,
    }

    if settings.mysql_unix_socket:
        kwargs["unix_socket"] = settings.mysql_unix_socket
        return mysql.connector.connect(**kwargs)

    kwargs["host"] = settings.mysql_host
    kwargs["port"] = settings.mysql_port

    source_address = settings.mysql_source_address.strip()
    if settings.mysql_source_required and not source_address:
        raise RuntimeError('Falta MYSQL_SOURCE_ADDRESS requerido por este equipo')
    if source_address: ip_address(source_address)
    if source_address:
        return ConexionMySQLConOrigen(
            source_address=source_address,
            **kwargs,
        )

    return mysql.connector.connect(**kwargs)

def consultar_mysql(
    consulta: str,
    parametros: tuple | None = None,
) -> list[dict[str, Any]]:
    conexion = None
    cursor = None

    try:
        conexion = crear_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            consulta,
            parametros or (),
        )

        return cursor.fetchall()

    except Error as exc:
        raise RuntimeError(f"La consulta a MySQL fallo: {exc}") from exc

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()
