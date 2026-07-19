import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.rag.legal_structure import LegalStructureParser, SourcePage


class LegalStructureParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LegalStructureParser()

    def test_short_article_is_kept_as_one_atomic_chunk(self) -> None:
        chunks = self.parser.parse_pages([
            SourcePage(1, "THÔNG TƯ\nCăn cứ Luật...\nĐiều 1. Phạm vi điều chỉnh\nThông tư này quy định về hoạt động thử nghiệm."),
        ])
        self.assertEqual(["PREAMBLE", "ARTICLE"], [chunk.section_type for chunk in chunks])
        article = chunks[1]
        self.assertEqual("Điều 1", article.article)
        self.assertEqual("Phạm vi điều chỉnh", article.article_title)
        self.assertEqual("Thông tư này quy định về hoạt động thử nghiệm.", article.source_text)
        self.assertIn("Điều 1. Phạm vi điều chỉnh", article.content)

    def test_article_is_split_on_complete_clauses_and_points(self) -> None:
        chunks = self.parser.parse_pages([
            SourcePage(1, """Chương II. QUY ĐỊNH CỤ THỂ
Điều 8. Nghĩa vụ báo cáo
1. Tổ chức báo cáo thực hiện các nghĩa vụ sau:
a) Thu thập thông tin khách hàng đầy đủ;
b) Lưu trữ hồ sơ theo thời hạn quy định.
2. Báo cáo phải được gửi đúng thời hạn."""),
        ])
        self.assertEqual(["CLAUSE_INTRO", "POINT", "POINT", "CLAUSE"], [chunk.section_type for chunk in chunks])
        self.assertEqual(["a", "b"], [chunk.point for chunk in chunks if chunk.section_type == "POINT"])
        first_point = next(chunk for chunk in chunks if chunk.point == "a")
        self.assertIn("Khoản 1", first_point.heading_path)
        self.assertIn("Điểm a", first_point.heading_path)
        self.assertIn("1. Tổ chức báo cáo thực hiện các nghĩa vụ sau:", first_point.content)
        self.assertEqual(1, first_point.content.count("a) Thu thập thông tin khách hàng đầy đủ;"))
        self.assertEqual("2", chunks[-1].clause)
        self.assertIn("Điều 8. Nghĩa vụ báo cáo", chunks[-1].heading_path)
        self.assertIn("2. Báo cáo phải được gửi đúng thời hạn.", chunks[-1].source_text)

    def test_clause_continues_across_page_boundary(self) -> None:
        chunks = self.parser.parse_pages([
            SourcePage(10, "Điều 4. Hồ sơ\n1. Hồ sơ phải có tài liệu nhận diện và"),
            SourcePage(11, "tài liệu chứng minh mục đích giao dịch.\n2. Tổ chức lưu hồ sơ."),
        ])
        first_clause = chunks[0]
        self.assertEqual("CLAUSE", first_clause.section_type)
        self.assertEqual(10, first_clause.page_from)
        self.assertEqual(11, first_clause.page_to)
        self.assertIn("tài liệu chứng minh mục đích giao dịch.", first_clause.source_text)

    def test_preamble_without_article_is_not_mislabeled(self) -> None:
        chunks = self.parser.parse_pages([SourcePage(1, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc")])
        self.assertEqual(1, len(chunks))
        self.assertEqual("PREAMBLE", chunks[0].section_type)
        self.assertIsNone(chunks[0].article)

    def test_appendix_is_kept_separate_from_articles(self) -> None:
        chunks = self.parser.parse_pages([
            SourcePage(1, "PHỤ LỤC I\nDANH MỤC BIỂU MẪU\n1. Biểu mẫu nhận diện khách hàng"),
        ])
        self.assertEqual(1, len(chunks))
        self.assertEqual("APPENDIX", chunks[0].section_type)
        self.assertIsNone(chunks[0].article)

    def test_atomic_unit_is_not_split_by_size(self) -> None:
        body = "Nội dung rất dài. " * 400
        chunks = self.parser.parse_pages([SourcePage(1, f"Điều 9. Điều khoản dài\n1. {body}")])
        self.assertEqual(1, len(chunks))
        self.assertEqual("CLAUSE", chunks[0].section_type)
        self.assertIn("OVERSIZED_ATOMIC_UNIT", chunks[0].warnings)

    def test_currency_value_is_not_mistaken_for_a_new_clause(self) -> None:
        chunks = self.parser.parse_pages([
            SourcePage(1, "Điều 10. Hạn mức\n1. Hạn mức tối thiểu là\n2.000.000 đồng cho mỗi giao dịch."),
        ])
        self.assertEqual(1, len(chunks))
        self.assertEqual("1", chunks[0].clause)
        self.assertIn("2.000.000 đồng", chunks[0].source_text)


if __name__ == "__main__":
    unittest.main()
