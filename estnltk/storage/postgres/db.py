import os
import re
import json
import logging
import operator as op
from functools import reduce
from itertools import chain

import psycopg2
from psycopg2.extensions import STATUS_BEGIN
from psycopg2.sql import SQL, Identifier, Literal

from estnltk.converters.dict_importer import dict_to_layer
from estnltk.converters.dict_exporter import layer_to_dict
from estnltk.converters import dict_to_text, text_to_json
from estnltk.layer_operations import create_ngram_fingerprint_index
from .query import Query

log = logging.getLogger(__name__)


class PgStorageException(Exception):
    pass


class PgCollection:
    """Convenience wrapper over PostgresStorage"""

    def __init__(self, name, storage):
        self.table_name = name
        self.storage = storage

    def create(self, description=None):
        """Creates a database table for the collection"""
        return self.storage.create_table(self.table_name, description)

    def insert(self, text, key=None):
        """Inserts text object as a table row with a given key"""
        return self.storage.insert(self.table_name, text, key)

    def exists(self):
        """Returns true if table exists"""
        return self.storage.table_exists(self.table_name)

    def select_fragment_raw(self, fragment_name, parent_layer_name, query=None, ngram_query=None):
        return self.storage.select_fragment_raw(
            fragment_table=self.fragment_name_to_table_name(fragment_name),
            text_table=self.table_name,
            parent_layer_table=self.layer_name_to_table_name(parent_layer_name),
            query=query,
            ngram_query=ngram_query)

    def select(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None, order_by_key=False):
        """See PostgresStorage.select()"""
        return self.storage.select(self.table_name, query, layer_query, layer_ngram_query, layers, keys=keys,
                                   order_by_key=order_by_key)

    def select_raw(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None,
                   order_by_key=False):
        """See PostgresStorage.select_raw()"""
        return self.storage.select_raw(self.table_name, query, layer_query, layer_ngram_query, layers, keys,
                                       order_by_key)

    def select_by_key(self, key, return_as_dict=False):
        """See PostgresStorage.select_by_key()"""
        return self.storage.select_by_key(self.table_name, key, return_as_dict)

    def find_fingerprint(self, query=None, layer_query=None, layer_ngram_query=None, layers=None, order_by_key=False):
        """See PostgresStorage.find_fingerprint()"""
        return self.storage.find_fingerprint(self.table_name, query, layer_query, layer_ngram_query, layers,
                                             order_by_key)

    def layer_name_to_table_name(self, layer_name):
        return self.storage.layer_name_to_table_name(self.table_name, layer_name)

    def fragment_name_to_table_name(self, fragment_name):
        return self.storage.fragment_name_to_table_name(self.table_name, fragment_name)

    def create_fragment(self, fragment_name, data_iterator, row_mapper,
                        create_index=False, ngram_index=None):
        """
        Creates and fills a fragment table.

        Args:
            fragment_name: str
            data_iterator: iterator
                Produces tuples (text_id, text, parent_layer_id, *payload),
                where *payload is a variable number of values to be passed to the `row_mapper`
                See method `PgCollection.select_raw`
            row_mapper: callable
                It takes as input a full row produced by `data_iterator`
                and returns a list of Layer objects.
            create_index:
            ngram_index:

        """
        conn = self.storage.conn
        with conn.cursor() as c:
            try:
                conn.autocommit = False
                # create fragment table and indices
                self.create_fragment_table(c, fragment_name,
                                           create_index=create_index,
                                           ngram_index=ngram_index)
                # insert data
                fragment_table = self.fragment_name_to_table_name(fragment_name)
                id_ = 0
                for row in data_iterator:
                    text_id, text, parent_layer_id = row[0], row[1], row[2]
                    for fragment_layer in row_mapper(row):
                        fragment_dict = layer_to_dict(fragment_layer, text)
                        if ngram_index is not None:
                            ngram_values = [create_ngram_fingerprint_index(fragment_layer, attr, size)
                                            for attr, size in ngram_index.items()]
                        else:
                            ngram_values = None
                        layer_json = json.dumps(fragment_dict, ensure_ascii=False)
                        ngram_values = ngram_values or []
                        q = "INSERT INTO {}.{} VALUES (%s);" % ", ".join(['%s'] * (4 + len(ngram_values)))
                        q = SQL(q).format(Identifier(self.storage.schema), Identifier(fragment_table))
                        c.execute(q, (id_, parent_layer_id, text_id, layer_json, *ngram_values))
                        id_ += 1
            except:
                conn.rollback()
                raise
            finally:
                if conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    conn.commit()
                conn.autocommit = True

    def create_layer(self, layer_name, data_iterator, row_mapper,
                     create_index=False, ngram_index=None, overwrite=False):
        """
        Creates layer

        Args:
            layer_name:
            data_iterator: iterator
                Iterator over Text collection which generates tuples (`text_id`, `text`).
                See method `PgCollection.select`.
            row_mapper: function
            create_index:
            ngram_index:
            overwrite: bool
                If True and layer table exists, table is overwritten.
                If False and layer table exists, error is raised.
        """
        conn = self.storage.conn
        with conn.cursor() as c:
            try:
                conn.autocommit = False
                # create table and indices
                self.create_layer_table(c, layer_name,
                                        create_index=create_index,
                                        ngram_index=ngram_index,
                                        overwrite=overwrite)
                # insert data
                layer_table = self.layer_name_to_table_name(layer_name)
                id_ = 0
                for row in data_iterator:
                    text_id, text = row[0], row[1]
                    for layer in row_mapper(row):
                        layer_dict = layer_to_dict(layer, text)
                        if ngram_index is not None:
                            ngram_values = [create_ngram_fingerprint_index(layer, attr, size)
                                            for attr, size in ngram_index.items()]
                        else:
                            ngram_values = None
                        layer_json = json.dumps(layer_dict, ensure_ascii=False)
                        ngram_values = ngram_values or []
                        q = "INSERT INTO {}.{} VALUES (%s);" % ", ".join(['%s'] * (3 + len(ngram_values)))
                        q = SQL(q).format(Identifier(self.storage.schema), Identifier(layer_table))
                        c.execute(q, (id_, text_id, layer_json, *ngram_values))
                        id_ += 1
            except:
                conn.rollback()
                raise
            finally:
                if conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    conn.commit()
                conn.autocommit = True

    def create_layer_table(self, cursor, layer_name, create_index=True, ngram_index=None, overwrite=False):
        is_fragment = False
        table_name = self.layer_name_to_table_name(layer_name)
        return self._create_layer_table(cursor, table_name, layer_name, is_fragment, create_index, ngram_index,
                                        overwrite=overwrite)

    def create_fragment_table(self, cursor, fragment_name, create_index=True, ngram_index=None):
        is_fragment = True
        table_name = self.fragment_name_to_table_name(fragment_name)
        return self._create_layer_table(cursor, table_name, fragment_name, is_fragment, create_index, ngram_index)

    def _create_layer_table(self, cursor, layer_table, layer_name, is_fragment=False, create_index=True,
                            ngram_index=None, overwrite=False):
        if overwrite:
            self.storage.drop_table_if_exists(layer_table)
        elif self.storage.table_exists(layer_table):
            raise PgStorageException("Table '{}' for layer '{}' already exists.".format(layer_table, layer_name))
        if ngram_index is not None:
            ngram_index_cols = ngram_index.keys()
            ngram_cols_sql = ", %s" % ",".join(["%s text[]" % Identifier(column).as_string(self.storage.conn)
                                                for column in ngram_index])
        else:
            ngram_cols_sql = ""
        # create layer table and index
        if is_fragment is False:
            q = "CREATE TABLE {}.{} (id serial PRIMARY KEY, text_id int NOT NULL, data jsonb %s)" % ngram_cols_sql
        else:
            q = "CREATE TABLE {}.{} (id serial PRIMARY KEY, parent_id int NOT NULL, text_id int NOT NULL, data jsonb %s)" % ngram_cols_sql
        q = SQL(q).format(Identifier(self.storage.schema), Identifier(layer_table))
        cursor.execute(q)

        q = SQL("COMMENT ON TABLE {}.{} IS {}").format(
            Identifier(self.storage.schema), Identifier(layer_table),
            Literal("%s %s layer" % (self.table_name, layer_name)))
        cursor.execute(q)

        # create jsonb index
        if create_index is True:
            cursor.execute(SQL(
                "CREATE INDEX {index} ON {schema}.{table} USING gin ((data->'layers') jsonb_path_ops)").format(
                schema=Identifier(self.storage.schema),
                index=Identifier('idx_%s_data' % layer_table),
                table=Identifier(layer_table)))

        # create ngram array index
        if ngram_index is not None:
            for column in ngram_index_cols:
                cursor.execute(SQL(
                    "CREATE INDEX {index} ON {schema}.{table} USING gin ({column})").format(
                    schema=Identifier(self.storage.schema),
                    index=Identifier('idx_%s_%s' % (layer_table, column)),
                    table=Identifier(layer_table),
                    column=Identifier(column)))

        cursor.execute(SQL(
            "CREATE INDEX {index} ON {schema}.{table} (text_id)").format(
            index=Identifier('idx_%s__text_id' % layer_table),
            schema=Identifier(self.storage.schema),
            table=Identifier(layer_table)))

    def delete_layer(self, layer_name):
        layer_table = self.layer_name_to_table_name(layer_name)
        if layer_name not in self.get_layer_names():
            raise PgStorageException("Collection does not have a layer '%s'." % layer_name)
        if not self.storage.table_exists(layer_table):
            raise PgStorageException("Layer table '%s' does not exist." % layer_table)
        self.storage.drop_table(layer_table)

    def delete_fragment(self, fragment_name):
        fragment_table = self.fragment_name_to_table_name(fragment_name)
        if fragment_name not in self.get_fragment_names():
            raise PgStorageException("Collection does not have a layer fragment '%s'." % fragment_name)
        if not self.storage.table_exists(fragment_table):
            raise PgStorageException("Layer fragment table '%s' does not exist." % fragment_table)
        self.storage.drop_table(fragment_table)

    def delete_layer_fragment(self, layer_fragment_name):
        lf_table = self.layer_fragment_name_to_table_name(layer_fragment_name)
        if layer_fragment_name not in self.get_layer_fragment_names():
            raise PgStorageException("Collection does not have a layer fragment '%s'." % layer_fragment_name)
        if not self.storage.table_exists(lf_table):
            raise PgStorageException("Layer fragment table '%s' does not exist." % lf_table)
        self.storage.drop_table(lf_table)

    def delete(self):
        """Removes collection and all related layers."""
        conn = self.storage.conn
        conn.autocommit = False
        try:
            for layer_table in self.get_layer_tables():
                self.storage.drop_table(layer_table)
            self.storage.drop_table(self.table_name)
        except:
            conn.rollback()
            raise
        finally:
            if conn.status == STATUS_BEGIN:
                # no exception, transaction in progress
                conn.commit()
            conn.autocommit = True

    def has_layer(self, layer_name):
        return layer_name in self.get_layer_names()

    def has_fragment(self, fragment_name):
        return fragment_name in self.get_fragment_names()

    def get_fragment_names(self):
        lf_names = []
        for tbl in self.get_fragment_tables():
            layer = re.sub("^%s__" % self.table_name, "", tbl)
            layer = re.sub("__fragment$", "", layer)
            lf_names.append(layer)
        return lf_names

    def get_layer_names(self):
        layer_names = []
        for tbl in self.get_layer_tables():
            layer = re.sub("^%s__" % self.table_name, "", tbl)
            layer = re.sub("__layer$", "", layer)
            layer_names.append(layer)
        return layer_names

    def get_fragment_tables(self):
        fragment_tables = []
        for tbl in self.storage.get_all_table_names():
            if tbl.startswith("%s__" % self.table_name) and tbl.endswith("__fragment"):
                fragment_tables.append(tbl)
        return fragment_tables

    def get_layer_tables(self):
        layer_tables = []
        for tbl in self.storage.get_all_table_names():
            if tbl.startswith("%s__" % self.table_name) and tbl.endswith("__layer"):
                layer_tables.append(tbl)
        return layer_tables


class PostgresStorage:
    """`PostgresStorage` instance wraps a database connection and
    exposes interface to conveniently search/save json data.
    """

    def __init__(self, dbname=None, user=None, password=None, host='localhost', port=5432,
                 pgpass_file="~/.pgpass", schema="public", **kwargs):
        """
        Connects to database either using connection parameters if specified, or ~/.pgpass file.

            ~/.pgpass file format: hostname:port:database:username:password

        """
        if dbname is None:
            log.debug("Database name not specified. Loading connection settings from '%s'" % pgpass_file)
            pgpass = os.path.expanduser(pgpass_file)
            if not os.path.exists(pgpass):
                raise PgStorageException("Configuration file '%s' not found." % pgpass)
            else:
                with open(pgpass, encoding="utf-8") as f:
                    host, port, dbname, user, password = f.readline().rstrip().split(":")
        self.conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port, **kwargs)
        self.conn.autocommit = True
        self.schema = schema

    def close(self):
        """Closes database connection"""
        self.conn.close()

    def create_schema(self):
        with self.conn.cursor() as c:
            c.execute(SQL("CREATE SCHEMA {};").format(Identifier(self.schema)))

    def delete_schema(self):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP SCHEMA {} CASCADE;").format(Identifier(self.schema)))

    def create_table(self, table, description=None):
        """Creates a new table to store jsonb data:

            CREATE TABLE table(
                id serial PRIMARY KEY,
                data jsonb
            );

        and automatically adds a GIN index for the jsonb column:

            CREATE INDEX idx_table_data ON table USING gin ((data -> 'layers') jsonb_path_ops);
        """
        self.conn.autocommit = False
        with self.conn.cursor() as c:
            try:
                c.execute(SQL("CREATE TABLE {}.{} (id serial PRIMARY KEY, data jsonb)").format(
                    Identifier(self.schema), Identifier(table)))
                c.execute(
                    SQL("CREATE INDEX {index} ON {schema}.{table} USING gin ((data->'layers') jsonb_path_ops)").format(
                        index=Identifier('idx_%s_data' % table),
                        schema=Identifier(self.schema),
                        table=Identifier(table)))
                if isinstance(description, str):
                    c.execute(SQL("COMMENT ON TABLE {}.{} IS {}").format(
                        Identifier(self.schema), Identifier(table), Literal(description)))
            except:
                self.conn.rollback()
                raise
            finally:
                if self.conn.status == STATUS_BEGIN:
                    # no exception, transaction in progress
                    self.conn.commit()
                self.conn.autocommit = True

    @staticmethod
    def fragment_name_to_table_name(collection_table, fragment_name):
        """
        Constructs table name for a fragment.

        Args:
            collection_table: str
                parent collection table
            fragment_name: str
                fragment name
        Returns:
            str: fragment table name

        """
        return "%s__%s__fragment" % (collection_table, fragment_name)

    @staticmethod
    def layer_name_to_table_name(collection_table, layer_name):
        """
        Constructs layer table name.

        Args:
            collection_table: str
                parent collection table
            layer_name: str
                layer name
        Returns:
            str: layer table name

        """
        return "%s__%s__layer" % (collection_table, layer_name)

    def drop_table(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP TABLE {}.{}").format(Identifier(self.schema), Identifier(table)))

    def drop_table_if_exists(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("DROP TABLE IF EXISTS {}.{}").format(Identifier(self.schema), Identifier(table)))

    def insert_layer_row(self, layer_table, layer_dict, row_id, text_id, ngram_values=None):
        layer_json = json.dumps(layer_dict, ensure_ascii=False)
        ngram_values = ngram_values or []
        with self.conn.cursor() as c:
            sql = "INSERT INTO {}.{} VALUES (%s) RETURNING id;" % ", ".join(['%s'] * (3 + len(ngram_values)))
            c.execute(SQL(sql).format(Identifier(self.schema), Identifier(layer_table)),
                      (row_id, text_id, layer_json, *ngram_values))
            row_key = c.fetchone()[0]
            return row_key

    def insert(self, table, text, key=None):
        """
        Saves a given `text` object into a given `table`..
        Args:
            table: str
            text: text
            key: int

        Returns:
            int: row key (id)
        """
        text = text_to_json(text)
        with self.conn.cursor() as c:
            if key is not None:
                c.execute(SQL("INSERT INTO {}.{} VALUES (%s, %s) RETURNING id;").format(
                    Identifier(self.schema), Identifier(table)), (key, text))
            else:
                c.execute(SQL("INSERT INTO {}.{} (data) VALUES (%s) RETURNING id;").format(
                    Identifier(self.schema), Identifier(table)), (text,))
            row_key = c.fetchone()[0]
            return row_key

    def table_exists(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE  schemaname = %s AND tablename = %s);"),
                      [self.schema, table])
            return c.fetchone()[0]

    def count_rows(self, table):
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT count(*) FROM {}.{}").format(Identifier(self.schema), Identifier(table)))
            nrows = c.fetchone()[0]
            return nrows

    def select_by_key(self, table, key, return_as_dict=False):
        """Loads text object by `key`. If `return_as_dict` is True, returns a text object as dict"""
        with self.conn.cursor() as c:
            c.execute(SQL("SELECT * FROM {}.{} WHERE id = %s").format(Identifier(self.schema), Identifier(table)),
                      (key,))
            res = c.fetchone()
            if res is None:
                raise PgStorageException("Key %s not not found." % key)
            key, text_dict = res
            text = text_dict if return_as_dict is True else dict_to_text(text_dict)
            return text

    def get_all_table_names(self):
        with self.conn.cursor() as c:
            c.execute(SQL(
                "SELECT table_name FROM information_schema.tables WHERE table_schema=%s AND table_type='BASE TABLE'"),
                [self.schema])
            table_names = [row[0] for row in c.fetchall()]
            return table_names

    def select_fragment_raw(self, fragment_table, text_table, parent_layer_table, query=None, ngram_query=None):
        """

        Args:
            fragment_table:
            text_table:
            parent_layer_table:
            query:
            ngram_query:

        Returns:
            Iterator of tuples.
            Each tuple has 6 elements:
                text_id
                text
                parent_id
                parent_layer
                fragment_id
                fragment_layer
        """
        # 1. Build query
        q = """
            SELECT
              {text_table}.id, {text_table}.data, {parent_table}.id, {parent_table}.data,
              {fragment_table}.id, {fragment_table}.data
            FROM
              {text_table}, {parent_table}, {fragment_table}
            WHERE
              {fragment_table}.parent_id = {parent_table}.id AND {parent_table}.text_id = {text_table}.id
            """

        format_table = lambda tbl: SQL("{}.{}").format(Identifier(self.schema), Identifier(tbl)).as_string(
            self.conn)

        q = q.format(
            text_table=format_table(text_table),
            parent_table=format_table(parent_layer_table),
            fragment_table=format_table(fragment_table))

        if query is not None:
            # build constraint on fragment's data column
            q = "%s AND %s" % (q, query.eval())

        if ngram_query is not None:
            # build constraint on fragment's ngram index
            ngram_q = " AND ".join([self._build_column_ngram_query(q, col, fragment_table)
                                    for col, q in ngram_query])
            q = "%s AND %s" % (q, ngram_q)

        # 2. Execute query
        with self.conn.cursor() as c:
            c.execute(q)
            for row in c.fetchall():
                text_id, text_dict, parent_id, parent_dict, fragment_id, fragment_dict = row
                text = dict_to_text(text_dict)
                parent_layer = dict_to_layer(parent_dict, text)
                fragment_layer = dict_to_layer(fragment_dict, text)
                yield text_id, text, parent_id, parent_layer, fragment_id, fragment_layer

    def select_raw(self,
                   table: str,
                   query: str = None,
                   layer_query: 'JsonbLayerQuery' = None,
                   layer_ngram_query: dict = None,
                   layers: list = None,
                   keys: list = None,
                   order_by_key: bool = False):
        """
        Select from collection table with possible search constraints.

        Args:
            table: str
                collection table
            query: JsonbTextQuery
                collection table query
            layer_query: JsonbLayerQuery
                layer query
            keys: list
                List of id-s.
            order_by_key: bool
            layers: list
                Layers to fetch. Specified layers will be merged into returned text object and
                become accessible via `text["layer_name"]`.

        Returns:
            iterator of (key, text) pairs

        Example:

            q = JsonbTextQuery('morph_analysis', lemma='laulma')
            for key, txt in storage.select(table, query=q):
                print(key, txt)


        """
        with self.conn.cursor() as c:
            # 1. Build query

            where = False
            sql_parts = []
            table_escaped = SQL("{}.{}").format(Identifier(self.schema), Identifier(table)).as_string(self.conn)
            if layers is None and layer_query is None and layer_ngram_query is None:
                # select only text table
                q = SQL("SELECT * FROM {}.{}").format(Identifier(self.schema), Identifier(table)).as_string(self.conn)
                sql_parts.append(q)
            else:
                # need to join text and all layer tables
                layers = layers or []
                layer_query = layer_query or {}
                layer_ngram_query = layer_ngram_query or {}

                layers_select = []
                for layer in chain(layers):
                    layer = self.layer_name_to_table_name(table, layer)
                    layer = SQL("{}.{}").format(Identifier(self.schema), Identifier(layer)).as_string(self.conn)
                    layers_select.append(layer)

                layers_join = set()
                for layer in chain(layers, layer_query.keys(), layer_ngram_query.keys()):
                    layer = self.layer_name_to_table_name(table, layer)
                    layer = SQL("{}.{}").format(Identifier(self.schema), Identifier(layer)).as_string(self.conn)
                    layers_join.add(layer)

                q = "SELECT {table}.id, {table}.data {select} FROM {table}, {layers_join} where {where}".format(
                    schema=Identifier(self.schema),
                    table=table_escaped,
                    select=", %s" % ", ".join(
                        "{0}.id, {0}.data".format(layer) for layer in layers_select) if layers_select else "",
                    layers_join=", ".join(layer for layer in layers_join),
                    where=" AND ".join("%s.id = %s.text_id" % (table_escaped, layer) for layer in layers_join))
                sql_parts.append(q)
                where = True
            if query is not None:
                # build constraint on the main text table
                sql_parts.append("%s %s" % ("and" if where else "where", query.eval()))
                where = True
            if layer_query:
                # build constraint on related layer tables
                q = " AND ".join(query.eval() for layer, query in layer_query.items())
                sql_parts.append("%s %s" % ("and" if where else "where", q))
                where = True
            if keys is None:
                keys = []
            else:
                keys = list(keys)
                # build constraint on id-s
                sql_parts.extend(("AND" if where else "WHERE", "id = ANY(%(keys)s)"))
                where = True
            if layer_ngram_query:
                # build constraint on related layer's ngram index
                q = self.build_layer_ngram_query(layer_ngram_query, table)
                if where is True:
                    q = "AND %s" % q
                sql_parts.append(q)
                where = True
            if order_by_key is True:
                sql_parts.append("order by id")

            sql = " ".join(sql_parts)  # bad, bad string concatenation, but we can't avoid it here, right?

            # 2. Execute query
            c.execute(sql, {'keys': keys})
            for row in c.fetchall():
                text_id = row[0]
                text_dict = row[1]
                text = dict_to_text(text_dict)
                layers = []
                if len(row) > 2:
                    for i in range(2, len(row), 2):
                        layer_id = row[i]
                        layer_dict = row[i + 1]
                        layer = dict_to_layer(layer_dict, text)
                        layers.append(layer_id)
                        layers.append(layer)
                result = text_id, text, *layers
                yield result

    def select(self, table, query=None, layer_query=None, layer_ngram_query=None, layers=None, keys=None,
               order_by_key=False):
        for row in self.select_raw(table, query, layer_query, layer_ngram_query, layers, keys=keys,
                                   order_by_key=order_by_key):
            text_id = row[0]
            text = row[1]
            if len(row) > 2:
                for i, layer_name in zip(range(3, len(row), 2), layers):
                    layer = row[i]
                    text[layer_name] = layer
            yield text_id, text

    def build_layer_ngram_query(self, ngram_query, collection_table):
        sql_parts = []
        for layer in ngram_query:
            for column, q in ngram_query[layer].items():
                layer_table = self.layer_name_to_table_name(collection_table, layer)
                col_query = self._build_column_ngram_query(q, column, layer_table)
                sql_parts.append(col_query)
        q = " AND ".join(sql_parts)
        return q

    def _build_column_ngram_query(self, query, column, table_name):
        print(table_name, column)
        if not isinstance(query, list):
            query = list(query)
        if isinstance(query[0], list):
            # case: [[(a),(b)], [(c)]] -> a AND b OR c
            or_terms = [["-".join(e) for e in and_term] for and_term in query]
        elif isinstance(query[0], tuple):
            # case: [(a), (b)] -> a OR b
            or_terms = [["-".join(e)] for e in query]
        elif isinstance(query[0], str):
            # case: [a, b] -> "a-b"
            or_terms = [["-".join(query)]]
        else:
            raise ValueError("Invalid ngram query format: {}".format(query))

        or_parts = []
        for and_term in or_terms:
            arr = ",".join("'%s'" % v for v in and_term)
            p = SQL("{schema}.{table}.{column} @> ARRAY[%s]" % arr).format(
                schema=Identifier(self.schema),
                table=Identifier(table_name),
                column=Identifier(column)).as_string(self.conn)
            or_parts.append(p)
        column_ngram_query = "(%s)" % " OR ".join(or_parts)
        return column_ngram_query

    def find_fingerprint(self, table, query=None, layer_query=None, layer_ngram_query=None, layers=None,
                         order_by_key=False):
        """
        A wrapper over `select` method, which enables to conveniently build composite AND/OR queries.

        Args:
            table: str
                collection table name
            query: dict
                Query applied to collection table
            layer_query: dict
                Query applied to layer table
            order_by_key: bool
                Sort results by key in ascending order
        Returns:
            iterator of tuples (key, text)

        Example `layer_ngramm_query`:

            Search ("üks,kaks" AND "kolm,neli") OR "viis,kuus":

            q = {
                "some_layer": {
                     "field": "some_field",
                     "query": [[("üks", "kaks"), ("kolm", "neli")], [("viis", "kuus")]],
                },
                ...

        Example `query`:

            q = {
                 "layer": "morph_analysis",
                 "field": "lemma",
                 "ambiguous": True,
                 "query": ["mis", "palju"],  # mis OR palju
                 }

        Example `layer_query`:

            q = {
                layer1: {
                    "field": "lemma",
                    "query": ["ööbik"],
                    "ambiguous": True
                },
                layer2: {
                    "field": "lemma",
                    "query": ["ööbik"],
                    "ambiguous": True
                }}
        """
        if query is None and layer_query is None and layer_ngram_query is None:
            raise PgStorageException("One of 'query', 'layer_query' or 'layer_ngramm_query' should be specified.")

        def build_text_query(q):
            or_query_list = []
            for and_terms in q["query"]:
                if not isinstance(and_terms, (list, tuple, set)):
                    and_terms = [and_terms]
                if and_terms:
                    and_query = reduce(op.__and__, (JsonbTextQuery(q["layer"], q["ambiguous"], **{q["field"]: term})
                                                    for term in and_terms))
                    or_query_list.append(and_query)
            if len(or_query_list) > 0:
                jsonb_query = reduce(op.__or__, or_query_list)
            else:
                jsonb_query = None
            return jsonb_query

        def build_layer_query(layer, q):
            or_query_list = []
            layer_table = self.layer_name_to_table_name(table, layer)
            for and_terms in q["query"]:
                if not isinstance(and_terms, (list, tuple, set)):
                    and_terms = [and_terms]
                if and_terms:
                    and_query = reduce(op.__and__,
                                       (JsonbLayerQuery(layer_table, q["ambiguous"], **{q["field"]: term})
                                        for term in and_terms))
                    or_query_list.append(and_query)
            if len(or_query_list) > 0:
                jsonb_query = reduce(op.__or__, or_query_list)
            else:
                jsonb_query = None
            return jsonb_query

        jsonb_text_query = build_text_query(query) if query is not None else None
        jsonb_layer_query = {layer: build_layer_query(layer, q) for layer, q in
                             layer_query.items()} if layer_query is not None else None

        return self.select(table, jsonb_text_query, jsonb_layer_query, layer_ngram_query, layers,
                           order_by_key=order_by_key)

    def get_collection(self, table_name):
        """Returns a new instance of `PgCollection` without physically creating it."""
        return PgCollection(table_name, self)


class JsonbTextQuery(Query):
    """
    Constructs database query to search `text` objects stored in jsonb format.
    """

    def __init__(self, layer, ambiguous=True, **kwargs):
        if not kwargs:
            raise ValueError('At least one layer attribute is required.')
        self.layer = layer
        self.ambiguous = ambiguous
        self.kwargs = kwargs

    def eval(self):
        if self.ambiguous is True:
            pat = """data->'layers' @> '[{"name": "%s", "spans": [[%s]]}]'"""
        else:
            pat = """data->'layers' @> '[{"name": "%s", "spans": [%s]}]'"""
        return pat % (self.layer, json.dumps(self.kwargs))


class JsonbLayerQuery(Query):
    """
    Constructs database query to search `layer` objects stored in jsonb format.
    """

    def __init__(self, layer_table, ambiguous=True, **kwargs):
        if not kwargs:
            raise ValueError('At least one layer attribute is required.')
        self.layer_table = layer_table
        self.ambiguous = ambiguous
        self.kwargs = kwargs

    def eval(self):
        if self.ambiguous is True:
            pat = """%s.data @> '{"spans": [[%s]]}'"""
        else:
            pat = """%s.data @> '{"spans": [%s]}'"""
        return pat % (self.layer_table, json.dumps(self.kwargs))
