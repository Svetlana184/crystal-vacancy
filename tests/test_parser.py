"""Тесты роли 2 (парсинг и данные). Запуск из корня репозитория:

    python -m unittest discover -s tests -v
"""
import json
import re
import unittest
from pathlib import Path

from src.parser.clean import (
    clean_field,
    clean_text,
    extract_vacancies,
    flatten,
    load_vacancies_file,
    normalize_many,
    normalize_to_dict,
    to_int,
)

ROOT = Path(__file__).resolve().parent.parent
MOCK = ROOT / "data" / "mock_vacancies.json"
EXPECTED = ROOT / "data" / "mock_expected_report.json"

TEXT_FIELDS = (
    "job_name", "duty", "requirements", "salary_text",
    "schedule", "employment", "work_place",
)


class CleanTextTests(unittest.TestCase):
    def test_strips_tags_and_entities(self):
        src = "<p>Работа&nbsp;с&laquo;клиентами&raquo;</p><ul><li>Первое</li><li>Второе</li></ul>"
        self.assertEqual(clean_text(src), "Работа с«клиентами» Первое Второе")

    def test_escaped_html(self):
        self.assertEqual(clean_text("&lt;p&gt;Текст&nbsp;тут&lt;/p&gt;"), "Текст тут")

    def test_less_than_sign_is_not_a_tag(self):
        self.assertEqual(clean_text("Зарплата <30000 руб."), "Зарплата <30000 руб.")

    def test_collapses_whitespace_and_invisible_chars(self):
        self.assertEqual(clean_text("  а\n\n б\t\u200bв  "), "а б в")

    def test_script_and_style_removed(self):
        self.assertEqual(clean_text("<style>p{}</style><p>Текст</p><script>x()</script>"), "Текст")

    def test_none_and_numbers(self):
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(5), "5")

    def test_placeholders_become_empty(self):
        for value in ("", "  ", "-", "—", "не указано", "Не указан.", "null", "N/A", None):
            self.assertEqual(clean_field(value), "", value)

    def test_real_text_kept(self):
        self.assertEqual(clean_field("Сменный график"), "Сменный график")


class NumberAndFlattenTests(unittest.TestCase):
    def test_to_int(self):
        self.assertIsNone(to_int(0))
        self.assertIsNone(to_int("0"))
        self.assertIsNone(to_int(None))
        self.assertIsNone(to_int(""))
        self.assertIsNone(to_int("abc"))
        self.assertIsNone(to_int(-5))
        self.assertEqual(to_int(30000), 30000)
        self.assertEqual(to_int("30 000"), 30000)
        self.assertEqual(to_int(30000.0), 30000)

    def test_requirement_dict(self):
        req = {"education": "Высшее", "experience": 3, "qualification": ""}
        self.assertEqual(flatten(req, {"education": "Образование", "experience": "Опыт работы (лет)"}),
                         "Образование: Высшее; Опыт работы (лет): 3")

    def test_empty_structures(self):
        self.assertEqual(flatten({}), "")
        self.assertEqual(flatten([]), "")
        self.assertEqual(flatten({"education": ""}), "")


class ExtractTests(unittest.TestCase):
    def test_full_api_response(self):
        data = {"results": {"vacancies": [{"vacancy": {"id": "1"}}, {"vacancy": {"id": "2"}}]}}
        self.assertEqual([v["id"] for v in extract_vacancies(data)], ["1", "2"])

    def test_list_wrapped_and_bare(self):
        self.assertEqual(len(extract_vacancies([{"vacancy": {"id": "1"}}, {"id": "2"}])), 2)

    def test_single_vacancy(self):
        self.assertEqual(len(extract_vacancies({"vacancy": {"id": "1"}})), 1)
        self.assertEqual(len(extract_vacancies({"id": "1"})), 1)

    def test_garbage(self):
        self.assertEqual(extract_vacancies("text"), [])
        self.assertEqual(extract_vacancies({"foo": 1}), [])
        self.assertEqual(extract_vacancies(None), [])


class NormalizeTests(unittest.TestCase):
    def test_minimal_vacancy_does_not_crash(self):
        d = normalize_to_dict({"id": "x"})
        self.assertEqual(d["id"], "x")
        self.assertIsNone(d["url"])
        self.assertIsNone(d["salary_min"])
        for field in TEXT_FIELDS:
            self.assertEqual(d[field], "")

    def test_no_id_raises(self):
        with self.assertRaises(ValueError):
            normalize_to_dict({"job-name": "Без id"})

    def test_work_place_skips_coordinates_and_dedups(self):
        vac = {"id": "1", "addresses": {"address": [
            {"location": "г. Калининград, ул. А, 1", "lat": 1, "lng": 2},
            {"location": "г. Калининград, ул. А, 1", "lat": 1, "lng": 2},
        ]}}
        self.assertEqual(normalize_to_dict(vac)["work_place"], "г. Калининград, ул. А, 1")

    def test_raw_fields_keep_original(self):
        vac = {"id": "1", "duty": "<p>Текст</p>", "salary_min": 0, "schedule": "не указано"}
        d = normalize_to_dict(vac)
        self.assertEqual(d["raw_fields"]["duty"], "<p>Текст</p>")
        self.assertEqual(d["raw_fields"]["salary_min"], 0)
        self.assertEqual(d["raw_fields"]["schedule"], "не указано")
        self.assertEqual(d["duty"], "Текст")
        self.assertEqual(d["schedule"], "")

    def test_many_dedup_skip_and_limit(self):
        items = [{"id": "1"}, {"id": "1"}, {"name": "нет id"}, {"id": "2"}, {"id": "3"}]
        self.assertEqual([v["id"] for v in normalize_many(items, as_dict=True)], ["1", "2", "3"])
        self.assertEqual([v["id"] for v in normalize_many(items, max_vacancies=2, as_dict=True)], ["1", "2"])


class MockDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = {v["id"]: v for v in normalize_many(load_vacancies_file(MOCK), as_dict=True)}

    def test_all_loaded(self):
        self.assertEqual(len(self.items), 8)

    def test_missing_pay_and_place(self):
        v = self.items["mock-002"]
        self.assertIsNone(v["salary_min"])
        self.assertIsNone(v["salary_max"])
        self.assertEqual(v["salary_text"], "")
        self.assertEqual(v["work_place"], "")

    def test_empty_duty_and_requirements(self):
        v = self.items["mock-005"]
        self.assertEqual(v["duty"], "")
        self.assertEqual(v["requirements"], "")

    def test_placeholder_schedule_and_escaped_html(self):
        v = self.items["mock-007"]
        self.assertEqual(v["schedule"], "")
        self.assertIsNone(v["salary_max"])
        self.assertEqual(v["salary_min"], 50000)
        self.assertNotIn("<", v["duty"])
        self.assertNotIn("&", v["duty"])
        self.assertIn("графику 2/2", v["duty"])

    def test_html_cleaned_everywhere(self):
        for v in self.items.values():
            for field in TEXT_FIELDS:
                self.assertNotRegex(v[field], r"<[a-zA-Z/]|&[a-z]+;|\s{2}", f'{v["id"]}.{field}')

    def test_requirements_text(self):
        self.assertEqual(
            self.items["mock-001"]["requirements"],
            "Образование: Высшее; Опыт работы (лет): 3; "
            "Квалификация: Знание 1С: Бухгалтерия государственного учреждения",
        )


class ExpectedReportTests(unittest.TestCase):
    """Эталонный отчёт должен быть согласован с нормализованными данными:
    каждая цитата реально лежит в поле, на которое ссылается замечание."""

    @classmethod
    def setUpClass(cls):
        cls.items = {v["id"]: v for v in normalize_many(load_vacancies_file(MOCK), as_dict=True)}
        with open(EXPECTED, encoding="utf-8") as fh:
            cls.report = json.load(fh)

    def test_ids_match(self):
        self.assertEqual({r["id"] for r in self.report}, set(self.items))

    def test_contract_keys(self):
        for r in self.report:
            self.assertEqual(set(r), {"id", "url", "issues"})
            for i in r["issues"]:
                self.assertEqual(set(i), {"topic", "field", "quote", "issue", "recommendation"})

    def test_quotes_are_in_fields(self):
        for r in self.report:
            vac = self.items[r["id"]]
            for i in r["issues"]:
                if not i["quote"]:
                    continue
                fields = [f.strip() for f in re.split(r"\s+vs\s+|,|/", i["field"]) if f.strip()]
                haystack = " ".join(str(vac[f]) for f in fields)
                for part in i["quote"].split(" | "):
                    self.assertIn(part, haystack, f'{r["id"]}: «{part}» нет в {fields}')

    def test_clean_vacancies_have_no_issues(self):
        by_id = {r["id"]: r for r in self.report}
        self.assertEqual(by_id["mock-001"]["issues"], [])
        self.assertEqual(by_id["mock-007"]["issues"], [])


class RepoFormatTests(unittest.TestCase):
    """Формат учебных файлов репозитория (data/test_vacancies.json): requirements строкой, salary без валюты."""

    def test_requirements_string_and_object(self):
        self.assertEqual(normalize_to_dict({"id": "1", "requirements": "Высшее образование."})["requirements"],
                         "Высшее образование.")
        self.assertEqual(normalize_to_dict({"id": "1", "requirement": {"education": "Высшее"}})["requirements"],
                         "Образование: Высшее")

    def test_salary_currency_only_when_there_is_a_number(self):
        self.assertEqual(normalize_to_dict({"id": "1", "salary": "от 45000 до 66000", "currency": "руб."})["salary_text"],
                         "от 45000 до 66000 руб.")
        self.assertEqual(normalize_to_dict({"id": "1", "salary": "от 20000 до 25000 руб.", "currency": "руб."})["salary_text"],
                         "от 20000 до 25000 руб.")
        self.assertEqual(normalize_to_dict({"id": "1", "salary": "достойная оплата", "currency": "руб."})["salary_text"],
                         "достойная оплата")

    def test_shift_is_added_to_schedule(self):
        d = normalize_to_dict({"id": "1", "schedule": "Сменная работа", "shift": ["2/2", "день"]})
        self.assertEqual(d["schedule"], "Сменная работа, 2/2, день")

    def test_url_is_none_when_missing(self):
        self.assertIsNone(normalize_to_dict({"id": "1", "vac_url": ""})["url"])

    def test_repo_test_vacancies_file(self):
        path = ROOT / "data" / "test_vacancies.json"
        if not path.exists():
            self.skipTest("нет data/test_vacancies.json")
        items = {v["id"]: v for v in normalize_many(load_vacancies_file(path), as_dict=True)}
        self.assertEqual(len(items), 4)
        self.assertIsNone(items["test-002-missing"]["salary_min"])
        self.assertEqual(items["test-002-missing"]["requirements"], "")
        self.assertEqual(items["test-002-missing"]["work_place"], "")
        self.assertEqual(items["test-003-ambiguous"]["salary_text"], "достойная оплата")
        self.assertEqual(items["test-001-ideal"]["salary_text"], "от 45000 до 66000 руб.")


class PydanticWrapperTests(unittest.TestCase):
    def test_model(self):
        try:
            import pydantic  # noqa: F401
        except ImportError:
            self.skipTest("pydantic не установлен")
        from src.parser.clean import normalize_vacancy
        model = normalize_vacancy({"id": "1", "job-name": "Тест"})
        self.assertEqual(model.id, "1")
        self.assertEqual(model.job_name, "Тест")


if __name__ == "__main__":
    unittest.main()
