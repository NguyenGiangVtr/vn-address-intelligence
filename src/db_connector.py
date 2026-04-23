"""
db_connector.py
===============
Kết nối PostgreSQL, đọc dữ liệu địa chỉ thô và ghi kết quả chuẩn hóa
trở lại database vào các cột mới.

Hỗ trợ schema (search_path), tránh lỗi UndefinedTable khi bảng
không nằm trong schema public.
"""

import logging
from contextlib import contextmanager
from typing import List, Optional

import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2 import sql

logger = logging.getLogger(__name__)


class DBConnector:
    """Quản lý kết nối và thao tác với PostgreSQL."""

    def __init__(self, cfg: dict):
        self.host     = cfg["host"]
        self.port     = cfg["port"]
        self.dbname   = cfg["dbname"]
        self.user     = cfg["user"]
        self.password = cfg["password"]
        # schema: "scm", "public", ... — mặc định public nếu không khai báo
        self.schema   = cfg.get("schema", "public") or "public"
        self._conn: Optional[psycopg2.extensions.connection] = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def connect(self):
        self._conn = psycopg2.connect(
            host=self.host, port=self.port,
            dbname=self.dbname, user=self.user, password=self.password,
        )
        self._conn.autocommit = False

        # Set search_path → PostgreSQL sẽ tìm bảng trong schema này trước
        with self._conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {schema}, public").format(
                    schema=sql.Identifier(self.schema)
                )
            )
        self._conn.commit()

        logger.info(
            "✅ Kết nối PostgreSQL thành công: %s@%s/%s  (schema=%s)",
            self.user, self.host, self.dbname, self.schema,
        )

    def disconnect(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("🔌 Đã ngắt kết nối PostgreSQL.")

    @contextmanager
    def cursor(self):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    # ------------------------------------------------------------------
    # Helper: tạo qualified table identifier  schema.table
    # ------------------------------------------------------------------
    def _qualified(self, table: str) -> sql.Composed:
        return sql.SQL("{}.{}").format(
            sql.Identifier(self.schema),
            sql.Identifier(table),
        )

    def _qualified_ext(self, schema: str, table: str) -> sql.Composed:
        """Dùng khi schema khác với self.schema (ví dụ bảng corpus riêng)."""
        s = schema or self.schema
        return sql.SQL("{}.{}").format(sql.Identifier(s), sql.Identifier(table))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def load_addresses(
        self,
        table: str,
        input_col: str,
        gt_col: str = "",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Đọc địa chỉ thô (và ground-truth nếu có) từ bảng.
        Trả về DataFrame với ít nhất cột: id, raw_address, [standard_address].
        """
        select_cols = [sql.Identifier("id"), sql.Identifier(input_col)]
        if gt_col:
            select_cols.append(sql.Identifier(gt_col))

        query = sql.SQL("SELECT {cols} FROM {tbl}").format(
            cols=sql.SQL(", ").join(select_cols),
            tbl=self._qualified(table),
        )
        if limit:
            query = sql.SQL("{q} LIMIT {lim}").format(
                q=query, lim=sql.Literal(limit)
            )

        with self.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

        df = pd.DataFrame(rows)
        df.rename(columns={input_col: "raw_address"}, inplace=True)
        if gt_col and gt_col in df.columns:
            df.rename(columns={gt_col: "standard_address"}, inplace=True)

        logger.info("📥 Đã đọc %d dòng từ %s.%s.", len(df), self.schema, table)
        return df

    def load_standard_addresses(
        self,
        table: str,
        col: str,
        schema: str = "",
    ) -> List[str]:
        """Đọc toàn bộ địa chỉ chuẩn dùng làm corpus tìm kiếm."""
        tbl = self._qualified_ext(schema, table)
        query = sql.SQL("SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL").format(
            col=sql.Identifier(col),
            tbl=tbl,
        )
        with self.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        addresses = [r[col] for r in rows if r[col]]
        logger.info(
            "📚 Đã đọc %d địa chỉ corpus từ %s.%s.",
            len(addresses), schema or self.schema, table,
        )
        return addresses

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def ensure_column(self, table: str, column: str, dtype: str = "TEXT"):
        """Tạo cột mới nếu chưa tồn tại (idempotent)."""
        stmt = sql.SQL("""
            DO $body$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = {schema}
                      AND table_name   = {tname}
                      AND column_name  = {col}
                ) THEN
                    ALTER TABLE {qtbl} ADD COLUMN {qcol} TEXT;
                END IF;
            END
            $body$;
        """).format(
            schema=sql.Literal(self.schema),
            tname=sql.Literal(table),
            col=sql.Literal(column),
            qtbl=self._qualified(table),
            qcol=sql.Identifier(column),
        )
        with self.cursor() as cur:
            cur.execute(stmt)
        logger.info("🏗  Đã đảm bảo cột '%s' tồn tại trong %s.%s.", column, self.schema, table)

    def save_results(self, table: str, column: str, id_values: list, result_values: list):
        """
        Cập nhật giá trị vào cột `column` theo từng `id`.
        """
        if not id_values:
            return
        self.ensure_column(table, column)
        query = sql.SQL(
            "UPDATE {tbl} SET {col} = %s WHERE id = %s"
        ).format(
            tbl=self._qualified(table),
            col=sql.Identifier(column),
        )
        pairs = list(zip(result_values, id_values))
        with self.cursor() as cur:
            psycopg2.extras.execute_batch(cur, query, pairs, page_size=200)
        logger.info("💾 Đã lưu %d kết quả vào cột '%s'.", len(pairs), column)
