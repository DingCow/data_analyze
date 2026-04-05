import unittest

from src import db


class TestDB(unittest.TestCase):
    """验证数据库访问层的最小回归行为。"""

    def test_get_schema_returns_non_empty_text(self):
        schema = db.get_schema()
        self.assertIsInstance(schema, str)
        self.assertTrue(schema.strip())

    def test_run_query_allows_select(self):
        columns, rows = db.run_query("SELECT 1 AS value")
        self.assertEqual(columns, ["value"])
        self.assertEqual(rows, [(1,)])

    def test_get_schema_explains_city_dimension_comes_from_taizhang(self):
        schema = db.get_schema()

        self.assertIn("orders_all [", schema)
        self.assertIn("不直接包含省份/城市字段", schema)
        self.assertIn("优先考虑 orders_all JOIN taizhang", schema)
        self.assertIn("taizhang [", schema)
        self.assertIn("包含电站名称、地址、省份、城市", schema)

    def test_validate_readonly_sql_rejects_write_statement(self):
        with self.assertRaisesRegex(ValueError, "只允许执行只读查询"):
            db.run_query("DELETE FROM orders_all WHERE 1=0")

    def test_validate_readonly_sql_rejects_multiple_statements(self):
        with self.assertRaisesRegex(ValueError, "只允许执行单条 SQL 查询"):
            db.run_query("SELECT 1; SELECT 2")


if __name__ == "__main__":
    unittest.main()
