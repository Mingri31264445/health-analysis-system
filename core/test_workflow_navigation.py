from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import BFSTest, MeridianTest, Questionnaire


class WorkflowNavigationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.subject = user_model.objects.create_user(username="0911111111", password="pass")
        self.staff = user_model.objects.create_user(
            username="0922222222", password="pass", is_staff=True
        )
        self.bfs = BFSTest.objects.create(user=self.subject, patient_name="王小明")
        self.meridian = MeridianTest.objects.create(
            user=self.subject, patient_name="王小明"
        )
        self.questionnaire = Questionnaire.objects.create(
            user=self.subject, name="王小明", gender="M", blood_type="O",
            height=170, weight=65, birth_date=date(2000, 1, 1), sleep_hours=7,
        )

    def test_four_module_page_shows_record_counts_and_direct_actions(self):
        self.client.force_login(self.subject)

        response = self.client.get(reverse("start_analysis"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "已有 1 筆紀錄", count=2)
        self.assertContains(response, "面診影像自助上傳尚未開放")
        self.assertContains(response, f'href="{reverse("upload_bfs_test")}"')
        self.assertContains(response, f'href="{reverse("upload_meridian_result")}"')
        self.assertContains(response, f'href="{reverse("bfs_list")}"')
        self.assertContains(response, f'href="{reverse("meridian_list")}"')
        self.assertContains(response, 'class="workflow-back"')

    def test_subject_report_returns_to_four_modules_and_staff_to_subject(self):
        result_url = reverse("analysis_report", args=[self.subject.pk])
        self.client.force_login(self.subject)
        response = self.client.get(result_url)
        self.assertContains(response, f'href="{reverse("start_analysis")}"')

        self.client.force_login(self.staff)
        response = self.client.get(result_url)
        self.assertContains(
            response,
            f'href="{reverse("subject_detail", args=[self.subject.pk])}"',
        )

    def test_hub_subject_and_auth_pages_have_clear_return_targets(self):
        self.client.force_login(self.staff)
        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, f'href="{reverse("home")}"')

        detail = self.client.get(reverse("subject_detail", args=[self.subject.pk]))
        self.assertContains(detail, f'?subject={self.subject.pk}#subject-list')
        self.assertContains(detail, "返回受測者清單")
        self.assertContains(detail, 'class="workflow-back-label"')

        dashboard = self.client.get(reverse("dashboard") + f"?subject={self.subject.pk}")
        self.assertEqual(dashboard.context["subject_overviews"][0]["id"], self.subject.pk)
        self.assertContains(dashboard, 'id="subject-list"')

        self.client.force_login(self.subject)
        detail = self.client.get(reverse("subject_detail", args=[self.subject.pk]))
        self.assertContains(detail, f'href="{reverse("start_analysis")}"')
        self.assertContains(detail, "查看面診說明")
        self.assertNotContains(detail, "新增面診")
        self.assertContains(detail, f'href="{reverse("bfs_list")}"')
        self.assertContains(detail, f'href="{reverse("meridian_list")}"')

        self.client.logout()
        for name in ("login", "register", "forgot_password"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, "返回首頁")
                self.assertContains(response, f'href="{reverse("home")}"')

    def test_staff_viewing_own_subject_returns_to_four_modules(self):
        Questionnaire.objects.create(
            user=self.staff, name="測試人員", gender="F", blood_type="A",
            height=160, weight=55, birth_date=date(2000, 1, 1), sleep_hours=7,
        )
        self.client.force_login(self.staff)

        detail = self.client.get(reverse("subject_detail", args=[self.staff.pk]))

        self.assertContains(detail, f'href="{reverse("start_analysis")}"')
        self.assertContains(detail, "返回四項檢測")
        self.assertNotContains(detail, "返回受測者清單")
        self.assertEqual(self.client.get(reverse("start_analysis")).status_code, 200)

    def test_admin_has_return_to_site_workbench(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("admin:index"))

        self.assertContains(response, "返回網站工作台")
        self.assertContains(response, f'href="{reverse("dashboard")}"')

    def test_questionnaire_edit_returns_to_four_modules(self):
        self.client.force_login(self.subject)

        response = self.client.get(reverse("questionnaire"))

        self.assertContains(response, f'href="{reverse("start_analysis")}"')
        self.assertContains(response, "返回四項檢測")

    def test_subject_can_return_to_four_modules_from_upload_and_results(self):
        self.client.force_login(self.subject)
        workflow_url = reverse("start_analysis")
        for name, args in (
            ("upload_bfs_test", []),
            ("bfs_list", []),
            ("bfs_detail", [self.bfs.pk]),
            ("bfs_update", [self.bfs.pk]),
            ("upload_meridian_result", []),
            ("meridian_list", []),
            ("meridian_detail", [self.meridian.pk]),
            ("meridian_update", [self.meridian.pk]),
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'href="{workflow_url}"')
                self.assertContains(response, "返回四項檢測")
                self.assertContains(response, 'class="workflow-back"')
                if name not in ("bfs_list", "meridian_list"):
                    list_name = "bfs_list" if "bfs" in name else "meridian_list"
                    self.assertContains(
                        response,
                        f'href="{reverse(list_name)}#records"',
                    )

    def test_staff_remains_with_selected_subject_across_record_pages(self):
        self.client.force_login(self.staff)
        subject_query = f"?subject={self.subject.pk}"
        workspace_url = reverse("subject_detail", args=[self.subject.pk])
        for name, args, query in (
            ("upload_bfs_test", [], subject_query),
            ("bfs_list", [], subject_query),
            ("bfs_detail", [self.bfs.pk], ""),
            ("upload_meridian_result", [], subject_query),
            ("meridian_list", [], subject_query),
            ("meridian_detail", [self.meridian.pk], ""),
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=args) + query)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'href="{workspace_url}"')
                self.assertContains(response, "返回受測者工作台")

        for name, pk, list_name in (
            ("bfs_detail", self.bfs.pk, "bfs_list"),
            ("meridian_detail", self.meridian.pk, "meridian_list"),
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name, args=[pk]))
                self.assertContains(
                    response,
                    f'href="{reverse(list_name)}?subject={self.subject.pk}#records"',
                )

    def test_delete_returns_to_selected_subject_records(self):
        self.client.force_login(self.staff)
        for name, pk, list_name in (
            ("bfs_delete", self.bfs.pk, "bfs_list"),
            ("meridian_delete", self.meridian.pk, "meridian_list"),
        ):
            with self.subTest(page=name):
                response = self.client.post(reverse(name, args=[pk]))
                self.assertRedirects(
                    response,
                    f"{reverse(list_name)}?subject={self.subject.pk}",
                )

    def test_trends_offer_subject_filtered_list_and_workbench(self):
        another_bfs = BFSTest.objects.create(user=self.subject, patient_name="王小明")
        another_meridian = MeridianTest.objects.create(
            user=self.subject, patient_name="王小明"
        )
        self.client.force_login(self.staff)
        for name, ids, list_name in (
            ("bfs_trend", (self.bfs.pk, another_bfs.pk), "bfs_list"),
            ("meridian_trend", (self.meridian.pk, another_meridian.pk), "meridian_list"),
        ):
            with self.subTest(page=name):
                response = self.client.get(
                    reverse(name) + f"?ids={ids[0]},{ids[1]}"
                )
                self.assertEqual(response.status_code, 200)
                return_url = response.context["record_return_url"]
                self.assertEqual(
                    return_url,
                    f"{reverse(list_name)}?subject={self.subject.pk}"
                    f"&selected={ids[0]}%2C{ids[1]}#records",
                )
                self.assertContains(response, "返回 BFS 紀錄" if list_name == "bfs_list" else "返回經絡儀紀錄")
                self.assertContains(
                    response,
                    f'href="{reverse("subject_detail", args=[self.subject.pk])}"',
                )

    def test_record_lists_have_return_anchor_and_state_restoration_script(self):
        self.client.force_login(self.subject)
        for name in ("bfs_list", "meridian_list"):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertContains(response, 'id="records"')
                self.assertContains(response, "record_list_navigation.js")
                self.assertContains(response, f'data-list-user="{self.subject.pk}"')

    def test_staff_all_records_and_unlinked_record_return_to_dashboard(self):
        self.client.force_login(self.staff)
        unlinked = BFSTest.objects.create(patient_name="舊資料")
        for url in (reverse("bfs_list"), reverse("bfs_detail", args=[unlinked.pk])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, f'href="{reverse("dashboard")}"')
                self.assertContains(response, "返回管理後台")
