"""
db_connector.py
===============
Kết nối PostgreSQL, đọc dữ liệu địa chỉ thô và ghi kết quả chuẩn hóa
trở lại database vào các cột mới.

Tính năng:
- Hỗ trợ schema (search_path)
- Auto-reconnect khi SSL/connection timeout
- Batch commit sau mỗi N dòng (tránh mất dữ liệu nếu crash giữa chừng)
- Fallback ctid khi bảng không có cột 'id'
"""

import logging
import time
from contextlib import contextmanager
from typing import Iterator, List, Optional, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2 import sql

logger = logging.getLogger(__name__)

# Số lần retry khi connection bị drop
_MAX_RECONNECT = 3
_RECONNECT_DELAY = 2  # giây


class DBConnector:
    """Quản lý kết nối và thao tác với PostgreSQL."""

    def __init__(self, cfg: dict):
        self.host     = cfg["host"]
        self.port     = cfg["port"]
        self.dbname   = cfg["dbname"]
        self.user     = cfg["user"]
        self.password = cfg["password"]
        self.schema   = cfg.get("schema", "public") or "public"
        self.id_col   = cfg.get("id_column", "id")
        self._cfg     = cfg          # giữ lại để reconnect
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._use_ctid: bool = False  # set sau khi load_addresses()

    # ──────────────────────────────────────────────────────────────────────
    # Connection / Reconnect
    # ──────────────────────────────────────────────────────────────────────
    def connect(self):
        """Mở kết nối mới và set search_path."""
        self._conn = psycopg2.connect(
            host=self.host, port=self.port,
            dbname=self.dbname, user=self.user, password=self.password,
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        self._conn.autocommit = False
        with self._conn.cursor() as cur:
            cur.execute(
                sql.SQL("SET search_path TO {schema}, public").format(
                    schema=sql.Identifier(self.schema)
                )
            )
        self._conn.commit()
        logger.info(
            " Kết nối PostgreSQL: %s@%s/%s (schema=%s)",
            self.user, self.host, self.dbname, self.schema,
        )

    def _reconnect(self):
        """Đóng connection cũ, mở lại mới — retry nếu thất bại."""
        logger.warning(" Đang reconnect PostgreSQL...")
        try:
            if self._conn and not self._conn.closed:
                self._conn.close()
        except Exception:
            pass

        for attempt in range(1, _MAX_RECONNECT + 1):
            try:
                self.connect()
                logger.info(" Reconnect thành công (lần %d).", attempt)
                return
            except Exception as exc:
                logger.error(" Reconnect lần %d thất bại: %s", attempt, exc)
                if attempt < _MAX_RECONNECT:
                    time.sleep(_RECONNECT_DELAY)
        raise RuntimeError("Không thể reconnect PostgreSQL sau nhiều lần thử.")

    def _ensure_connection(self):
        """Kiểm tra connection, reconnect nếu cần."""
        if self._conn is None or self._conn.closed:
            self._reconnect()
            return
        try:
            # ping nhẹ để phát hiện connection chết
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            self._reconnect()

    def disconnect(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info(" Đã ngắt kết nối PostgreSQL.")

    # ──────────────────────────────────────────────────────────────────────
    # Cursor context manager (có auto-reconnect)
    # ──────────────────────────────────────────────────────────────────────
    @contextmanager
    def cursor(self) -> Iterator[psycopg2.extras.RealDictCursor]:
        self._ensure_connection()
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
            self._conn.commit()
        except psycopg2.OperationalError:
            # Connection drop trong khi thực thi → rollback rồi reconnect
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._reconnect()
            raise
        except Exception:
            try:
                self._conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────────────────
    # Qualified table helpers
    # ──────────────────────────────────────────────────────────────────────
    def _qualified(self, table: str) -> sql.Composed:
        return sql.SQL("{}.{}").format(
            sql.Identifier(self.schema), sql.Identifier(table)
        )

    def _qualified_ext(self, schema: str, table: str) -> sql.Composed:
        s = schema or self.schema
        return sql.SQL("{}.{}").format(sql.Identifier(s), sql.Identifier(table))

    def _has_column(self, table: str, column: str) -> bool:
        with self.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s AND column_name=%s",
                (self.schema, table, column),
            )
            return cur.fetchone() is not None

    # ──────────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────────
    def load_addresses(
        self,
        table: str,
        input_col: str,
        gt_col: str = "",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Đọc địa chỉ thô từ bảng.
        """
        # Xác định ID column: ưu tiên config → tự kiểm tra id → fallback ctid
        has_id_col = self._has_column(table, self.id_col)
        
        if has_id_col:
            id_expr = sql.Identifier(self.id_col)
            self._use_ctid = False
            self._actual_id_col = self.id_col
        else:
            id_expr = sql.SQL("ctid::text AS id")
            self._use_ctid = True
            self._actual_id_col = "ctid"

        select_parts = [id_expr, sql.Identifier(input_col)]
        if gt_col:
            select_parts.append(sql.Identifier(gt_col))

        query = sql.SQL("SELECT {cols} FROM {tbl}").format(
            cols=sql.SQL(", ").join(select_parts),
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

        logger.info(
            " Đã đọc %d dòng từ %s.%s (id_col=%s).",
            len(df), self.schema, table, self._actual_id_col,
        )
        return df

    def load_standard_addresses(
        self,
        table: str,
        col: str,
        schema: str = "",
        limit: Optional[int] = None,
    ) -> List[str]:
        """Đọc corpus địa chỉ chuẩn."""
        tbl   = self._qualified_ext(schema, table)
        query = sql.SQL(
            "SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL"
        ).format(col=sql.Identifier(col), tbl=tbl)
        if limit:
            query = sql.SQL("{q} LIMIT {lim}").format(
                q=query, lim=sql.Literal(limit)
            )
        with self.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        addresses = [r[col] for r in rows if r[col]]
        logger.info(
            " Đã đọc %d địa chỉ corpus từ %s.%s.",
            len(addresses), schema or self.schema, table,
        )
        return addresses

    def load_hierarchical_corpus(self) -> List[str]:
        """
        Gộp mat.province, mat.district, mat.ward thành danh mục địa chỉ chuẩn:
        'Xã/Phường, Quận/Huyện, Tỉnh/Thành phố'
        """
        query = """
            SELECT 
                CASE 
                    WHEN w.admin_version = 2 THEN
                        -- Version 2: ward + province only (cleaned names)
                        REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                        REPLACE(p.province_name, p.type_name || ' ', '')
                    ELSE
                        -- Version 1: ward + district + province (cleaned names)
                        REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                        REPLACE(d.district_name, d.type_name || ' ', '') || ', ' ||
                        REPLACE(p.province_name, p.type_name || ' ', '')
                END as full_address
            FROM mat.ward w
            JOIN mat.district d ON w.district_id = d.district_id 
                AND d.admin_version = w.admin_version
            JOIN mat.province p ON d.province_id = p.province_id 
                AND p.admin_version = d.admin_version
            WHERE w.is_deleted = false 
              AND d.is_deleted = false 
              AND p.is_deleted = false
        """
        with self.cursor() as cur:
            # bypass RealDictCursor cho query này để lấy list string nhanh
            cur.execute(query)
            rows = cur.fetchall()
        
        # rows đang là RealDict hoặc tuple tùy cursor, xử lý an toàn
        addresses = []
        for r in rows:
            val = r['full_address'] if isinstance(r, dict) else r[0]
            addresses.append(val)
            
        logger.info(" Đã tạo danh mục chuẩn với %d địa chỉ (cleaned names, version-aware).", len(addresses))
        return addresses

    def load_clean_corpus(
        self,
        admin_epoch: str = "2025",
        source_types: Optional[List[str]] = None,
        min_quality_score: float = 0.5,
        limit: Optional[int] = None,
        active_only: bool = True
    ) -> List[str]:
        """
        Load corpus từ bảng prq.address_clean_corpus với filtering options.
        
        Args:
            admin_epoch: Kỳ cải cách hành chính (default: "2025")
            source_types: Danh sách source types cần load (None = all)
            min_quality_score: Điểm chất lượng tối thiểu 
            limit: Giới hạn số lượng records
            active_only: Chỉ load records đang active
            
        Returns:
            List[str]: Danh sách standardized addresses
        """
        conditions = ["admin_epoch = %s"]
        params = [admin_epoch]
        
        if active_only:
            conditions.append("is_active = true")
            
        if source_types:
            placeholders = ",".join(["%s"] * len(source_types))
            conditions.append(f"source_type IN ({placeholders})")
            params.extend(source_types)
            
        if min_quality_score > 0:
            conditions.append("quality_score >= %s")
            params.append(min_quality_score)
        
        # Standardized address not null and not empty
        conditions.append("standardized_address IS NOT NULL")
        conditions.append("LENGTH(standardized_address) > 5")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT standardized_address 
            FROM prq.address_clean_corpus
            WHERE {where_clause}
            ORDER BY quality_score DESC, usage_count DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        with self.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            
        addresses = []
        for r in rows:
            val = r['standardized_address'] if isinstance(r, dict) else r[0]
            if val:
                addresses.append(val)
        
        logger.info(
            " Đã đọc %d địa chỉ từ address_clean_corpus (epoch=%s, min_quality=%.2f)",
            len(addresses), admin_epoch, min_quality_score
        )
        return addresses

    def load_clean_corpus_with_metadata(
        self,
        admin_epoch: str = "2025",
        source_types: Optional[List[str]] = None,
        min_quality_score: float = 0.5,
        limit: Optional[int] = None
    ) -> tuple[List[str], List[dict]]:
        """
        Load corpus kèm metadata cho temporal-aware matching.
        
        Returns:
            tuple: (addresses, metadata_list)
                - addresses: List[str] - standardized addresses
                - metadata_list: List[dict] - metadata cho từng address
        """
        conditions = ["admin_epoch = %s", "is_active = true"]
        params = [admin_epoch]
        
        if source_types:
            placeholders = ",".join(["%s"] * len(source_types))
            conditions.append(f"source_type IN ({placeholders})")
            params.extend(source_types)
            
        if min_quality_score > 0:
            conditions.append("quality_score >= %s")
            params.append(min_quality_score)
            
        conditions.append("standardized_address IS NOT NULL")
        conditions.append("LENGTH(standardized_address) > 5")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT 
                id,
                standardized_address,
                source_type, 
                quality_score,
                admin_epoch,
                admin_version,
                province_id,
                district_id,
                ward_id,
                effective_date
            FROM prq.address_clean_corpus
            WHERE {where_clause}
            ORDER BY quality_score DESC, usage_count DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        with self.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            
        addresses = []
        metadata_list = []
        
        for r in rows:
            if isinstance(r, dict):
                addr = r['standardized_address']
                meta = {
                    'id': r['id'],
                    'source_type': r['source_type'],
                    'quality_score': float(r['quality_score']) if r['quality_score'] else 0.0,
                    'admin_epoch': r['admin_epoch'],
                    'admin_version': r['admin_version'],
                    'province_id': r['province_id'],
                    'district_id': r['district_id'], 
                    'ward_id': r['ward_id'],
                    'effective_date': r['effective_date'].isoformat() if r['effective_date'] else None
                }
            else:
                # Fallback for tuple cursor
                addr = r[1]
                meta = {
                    'id': r[0],
                    'source_type': r[2],
                    'quality_score': float(r[3]) if r[3] else 0.0,
                    'admin_epoch': r[4],
                    'admin_version': r[5],
                    'province_id': r[6],
                    'district_id': r[7],
                    'ward_id': r[8],
                    'effective_date': r[9].isoformat() if r[9] else None
                }
                
            if addr:
                addresses.append(addr)
                metadata_list.append(meta)
        
        logger.info(
            " Đã đọc %d địa chỉ kèm metadata từ address_clean_corpus (epoch=%s)",
            len(addresses), admin_epoch
        )
        return addresses, metadata_list

    def update_corpus_usage_stats(self, corpus_ids: List[int]):
        """
        Cập nhật usage statistics cho corpus entries được sử dụng trong retrieval.
        
        Args:
            corpus_ids: List ID của corpus entries được retrieve
        """
        if not corpus_ids:
            return
            
        placeholders = ",".join(["%s"] * len(corpus_ids))
        query = f"""
            UPDATE prq.address_clean_corpus 
            SET usage_count = usage_count + 1,
                last_used_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """
        
        with self.cursor() as cur:
            cur.execute(query, corpus_ids)
            affected = cur.rowcount
            
        logger.debug(" Cập nhật usage stats cho %d corpus entries", affected)

    # ──────────────────────────────────────────────────────────────────────
    # Write — batch commit
    # ──────────────────────────────────────────────────────────────────────
    def ensure_column(self, table: str, column: str):
        """Tạo cột TEXT mới nếu chưa tồn tại (idempotent)."""
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
        logger.info("  Cột '%s' đã sẵn sàng trong %s.%s.", column, self.schema, table)

    def save_batch(
        self,
        table: str,
        column: str,
        id_values: list,
        result_values: list,
    ) -> int:
        """
        Ghi một batch kết quả vào DB và commit ngay lập tức.

        Parameters
        ----------
        table          : tên bảng
        column         : tên cột kết quả (sẽ tạo nếu chưa có)
        id_values      : list id hoặc ctid string
        result_values  : list địa chỉ đã chuẩn hóa

        Returns
        -------
        Số dòng đã ghi
        """
        if not id_values:
            return 0

        # Đảm bảo cột tồn tại (idempotent, chỉ thực hiện ở batch đầu tiên)
        self.ensure_column(table, column)

        use_ctid = getattr(self, "_use_ctid", False)
        actual_col = getattr(self, "_actual_id_col", self.id_col)

        if use_ctid:
            query = sql.SQL(
                "UPDATE {tbl} SET {col} = %s WHERE ctid = %s::tid"
            ).format(tbl=self._qualified(table), col=sql.Identifier(column))
        else:
            query = sql.SQL(
                "UPDATE {tbl} SET {col} = %s WHERE {idcol} = %s"
            ).format(
                tbl=self._qualified(table), 
                col=sql.Identifier(column),
                idcol=sql.Identifier(actual_col)
            )

        pairs = list(zip(result_values, id_values))
        with self.cursor() as cur:
            psycopg2.extras.execute_batch(cur, query, pairs, page_size=200)

        logger.info(" Batch commit: %d dòng → cột '%s'.", len(pairs), column)
        return len(pairs)

    def save_results(
        self,
        table: str,
        column: str,
        id_values: list,
        result_values: list,
        batch_size: int = 100,
    ) -> int:
        """
        Ghi toàn bộ kết quả vào DB theo từng batch, commit sau mỗi batch.
        Khi một batch thất bại (ví dụ connection drop), tự động reconnect
        và retry batch đó trước khi tiếp tục.

        Parameters
        ----------
        batch_size : số dòng mỗi lần commit (default 100)

        Returns
        -------
        Tổng số dòng đã ghi thành công
        """
        if not id_values:
            return 0

        total      = len(id_values)
        saved      = 0
        failed     = 0

        for start in range(0, total, batch_size):
            end        = min(start + batch_size, total)
            batch_ids  = id_values[start:end]
            batch_vals = result_values[start:end]

            # Retry tối đa _MAX_RECONNECT lần cho mỗi batch
            for attempt in range(1, _MAX_RECONNECT + 1):
                try:
                    self.save_batch(table, column, batch_ids, batch_vals)
                    saved += len(batch_ids)
                    logger.info(
                        " Batch %d–%d/%d saved (attempt %d).",
                        start + 1, end, total, attempt,
                    )
                    break
                except psycopg2.OperationalError as exc:
                    logger.warning(
                        "️  Batch %d–%d thất bại (attempt %d): %s — reconnecting...",
                        start + 1, end, attempt, exc,
                    )
                    if attempt < _MAX_RECONNECT:
                        time.sleep(_RECONNECT_DELAY)
                        self._reconnect()
                    else:
                        logger.error(
                            " Batch %d–%d bị bỏ qua sau %d lần thử.",
                            start + 1, end, _MAX_RECONNECT,
                        )
                        failed += len(batch_ids)

        logger.info(
            " save_results hoàn tất: %d/%d dòng saved, %d failed.",
            saved, total, failed,
        )
        return saved
