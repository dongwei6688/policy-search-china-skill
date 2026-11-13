#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chain_runner CLI 回归测试（stdlib unittest，无第三方依赖）

运行：python3 tests/test_chain_runner.py

覆盖的都是"参数声明了但没接线""边界只修了一个方向"这类只有真实调用才暴露的缺陷：
  - locate 去重、文号变体归一、短文号不误命中长文号
  - 文号未命中不静默降级；给了 --title-keyword 才降级
  - 年/月精度日期在 --start 与 --end 两个方向都不误剔
  - --exclude 真正生效、空串不会剔光
  - 0 条时区分「没搜到」与「被过滤掉」，trace 不得误报过滤

隔离：系统缓存与用户缓存都指向临时目录（POLICY_SEARCH_CHINA_SYSTEM_CACHE /
POLICY_SEARCH_CHINA_DATA_DIR），不读真实政策库——否则断言会被真实数据带偏。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "scripts" / "chain_runner.py"

CACHE = [
    {"title": "甲政策关于量子计算", "doc_number": "测发〔2026〕11号", "date": "2026-03-01",
     "issuer": "测试部", "local_path": ""},
    {"title": "乙政策只精确到年", "doc_number": "", "date": "2025",
     "issuer": "财政部", "local_path": ""},
    {"title": "丁政策完整日期在二五年", "doc_number": "", "date": "2025-07-01",
     "issuer": "财政部", "local_path": ""},
    {"title": "丙政策旧年份", "doc_number": "", "date": "2019-06-01",
     "issuer": "财政部", "local_path": ""},
]
# 同一政策出现在另一个信源文件里（真实库里确有这种重复）
DUP = {"title": "甲政策关于量子计算", "doc_number": "测发〔2026〕11号", "date": "2026-03-01",
       "issuer": "测试部", "local_path": ""}


class ChainRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="policy-test-")
        cls.user = Path(cls.tmp) / "user"
        cls.sysc = Path(cls.tmp) / "sys"
        (cls.user / "cache").mkdir(parents=True)
        cls.sysc.mkdir(parents=True)
        (cls.user / "cache" / "gov.json").write_text(
            json.dumps(CACHE, ensure_ascii=False), encoding="utf-8")
        (cls.user / "cache" / "sasac.json").write_text(
            json.dumps([DUP], ensure_ascii=False), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_cli(self, *args):
        env = dict(os.environ)
        env["POLICY_SEARCH_CHINA_DATA_DIR"] = str(self.user)
        env["POLICY_SEARCH_CHINA_SYSTEM_CACHE"] = str(self.sysc)
        env.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, str(CLI), *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def count(self, out):
        for line in out.splitlines():
            if line.startswith("结果数:"):
                return int(line.split(":", 1)[1].strip())
        self.fail(f"输出里没有「结果数」行：{out!r}")

    # ── 文号定位 ────────────────────────────────────────────
    def test_locate_dedup_same_policy_in_two_files(self):
        p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                         "--doc-number", "测发〔2026〕11号")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.count(p.stdout), 1)

    def test_doc_number_variants(self):
        for variant in ("测发[2026]11号", "测发（2026）第11号", "测发2026 11号",
                        "测发〔２０２６〕１１号"):
            p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                             "--doc-number", variant)
            self.assertEqual(self.count(p.stdout), 1, f"{variant} 未命中")

    def test_short_doc_number_does_not_match_longer(self):
        p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                         "--doc-number", "1号")
        self.assertEqual(self.count(p.stdout), 0)

    def test_doc_number_miss_without_title_returns_zero(self):
        p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                         "--doc-number", "测发〔2099〕99号")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("文号在缓存中没有对应条目", p.stdout)
        self.assertNotIn("甲政策关于量子计算", p.stdout)

    def test_doc_number_miss_with_explicit_title_keyword_falls_back(self):
        p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                         "--doc-number", "测发〔2099〕99号",
                         "--title-keyword", "量子计算")
        self.assertEqual(self.count(p.stdout), 1)
        self.assertIn("降级", p.stdout)

    def test_blank_doc_number_rejected(self):
        for bad in ("  ", "〔〕"):
            p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                             "--doc-number", bad)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("--doc-number", p.stderr)

    # ── 日期过滤 ────────────────────────────────────────────
    def test_year_precision_kept_on_start(self):
        p = self.run_cli("--chain", "broad", "--keywords", "只精确到年",
                         "--start", "2025-01-01")
        self.assertEqual(self.count(p.stdout), 1)

    def test_year_precision_kept_on_end(self):
        p = self.run_cli("--chain", "broad", "--keywords", "只精确到年",
                         "--end", "2025")
        self.assertEqual(self.count(p.stdout), 1)

    def test_end_year_keeps_full_date_entries(self):
        # 旧实现在 --end 2025 下会把 "2025-07-01" 判成大于 "2025" 而剔掉（整年清空的原症状）
        p = self.run_cli("--chain", "broad", "--keywords", "完整日期",
                         "--end", "2025")
        self.assertEqual(self.count(p.stdout), 1)

    def test_month_precision_bounds(self):
        p = self.run_cli("--chain", "broad", "--keywords", "旧年份",
                         "--start", "2019-06", "--end", "2019-06")
        self.assertEqual(self.count(p.stdout), 1)

    def test_bad_date_rejected(self):
        for bad in ("2024/1/1", "2025-13", "2025-02-30"):
            p = self.run_cli("--chain", "broad", "--keywords", "政策", "--start", bad)
            self.assertNotEqual(p.returncode, 0, bad)

    # ── 排除与 0 条归因 ────────────────────────────────────
    def test_exclude_takes_effect(self):
        p = self.run_cli("--chain", "broad", "--keywords", "政策", "--exclude", "旧年份")
        self.assertEqual(self.count(p.stdout), 3)

    def test_empty_exclude_does_not_drop_everything(self):
        p = self.run_cli("--chain", "broad", "--keywords", "政策", "--exclude", "")
        self.assertEqual(self.count(p.stdout), 4)

    def test_zero_result_attribution_when_filtered(self):
        p = self.run_cli("--chain", "broad", "--keywords", "政策",
                         "--issuer", "不存在的机关")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("被过滤条件", p.stdout)

    def test_trace_zero_result_does_not_blame_filters(self):
        p = self.run_cli("--chain", "trace", "--keywords", "这句话根本不存在")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("都没有这句话", p.stdout)
        self.assertNotIn("被过滤条件", p.stdout)

    def test_trace_reports_filters_when_all_candidates_are_excluded(self):
        # 带过滤参数把候选全部排除时，必须说「被过滤条件排除」而不是「都没有这句话」
        p = self.run_cli("--chain", "trace", "--keywords", "量子计算",
                         "--issuer", "不存在的机关")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("被过滤条件", p.stdout)

    # ── 过滤先于段落提取 ───────────────────────────────────
    def test_filter_applies_before_extraction(self):
        p = self.run_cli("--chain", "locate", "--keywords", "量子计算",
                         "--title-keyword", "政策", "--issuer", "财政部")
        self.assertEqual(self.count(p.stdout), 3)

    # ── 其余链的 0 条归因 ─────────────────────────────────
    def test_broad_zero_attribution_when_date_filters_everything(self):
        p = self.run_cli("--chain", "broad", "--keywords", "政策", "--end", "1990")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("被过滤条件", p.stdout)

    def test_cross_zero_attribution_when_filters_exclude_everything(self):
        p = self.run_cli("--chain", "cross", "--keywords", "政策", "旧年份",
                         "--start", "2030-01-01")
        self.assertEqual(self.count(p.stdout), 0)
        self.assertIn("被过滤条件", p.stdout)


class UnitsTest(unittest.TestCase):
    """纯函数级用例：不启子进程，钉住口径细节"""

    @classmethod
    def setUpClass(cls):
        if str(REPO / "scripts") not in sys.path:
            sys.path.insert(0, str(REPO / "scripts"))

    def test_short_doc_number_boundaries(self):
        import chain_runner as cr
        self.assertTrue(cr._dn_match(cr._norm_doc_number("40号"), "人社部发〔2026〕40号"))
        self.assertTrue(cr._dn_match(cr._norm_doc_number("11号"), "交通运输部令2026年第11号"))
        self.assertFalse(cr._dn_match(cr._norm_doc_number("5号"), "国务院令第745号"))
        self.assertFalse(cr._dn_match(cr._norm_doc_number("1号"), "主席令第91号"))

    def test_merge_keeps_cross_year_and_same_year_revisions(self):
        import chain_runner as cr
        cache = [{"title": "年度检查通知", "date": "2025-03-01", "doc_number": "甲〔2025〕1号"}]
        web = [
            {"title": "年度检查通知", "date": "2026-03-01", "doc_number": "甲〔2026〕1号"},
            {"title": "年度检查通知", "date": "2025-09-01", "doc_number": "甲〔2025〕9号"},
            {"title": "年度检查通知", "date": "2025-03-01", "doc_number": "甲〔2025〕1号"},
        ]
        merged = cr._merge_search_results(cache, web)
        self.assertEqual(len(merged), 3)  # 原版 + 2026 版 + 2025 修订版；完全重复项被合并

    def test_non_iso_dates_are_understood(self):
        from atoms import filter_date_range as f
        e = [{"date": "2025.07.01", "t": "dot"}, {"date": "2025年7月1日", "t": "cn"},
             {"date": "2025-7-1", "t": "short"}]
        self.assertEqual(len(f(e, None, "2025")), 3)
        self.assertEqual(len(f(e, "2025-07-02", None)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
