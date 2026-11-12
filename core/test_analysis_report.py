from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AnalysisReport, BFSTest, BFSTestFile, MeridianReading, MeridianTest, Questionnaire
from .services.analysis_report import (
    bfs_result, bfs_systems, build_system_rows, face_systems, meridian_result,
    meridian_systems, overall_from_states, questionnaire_result, questionnaire_systems,
)
from .services.system_mapping import SYSTEM_KEYS, bfs_quadrant_systems
from .views.permissions import RESEARCHER_GROUP_NAME


class AnalysisReportTests(TestCase):
    def setUp(self):
        self.subject = User.objects.create_user(username="0911111111", password="pass")
        self.other = User.objects.create_user(username="0922222222", password="pass")
        self.staff = User.objects.create_user(
            username="0933333333", password="pass", is_staff=True
        )
        self.questionnaire = Questionnaire.objects.create(
            user=self.subject, name="王小明", gender="M", blood_type="O",
            height=170, weight=65, birth_date=date(2000, 1, 1), sleep_hours=7,
        )
        self.url = reverse("analysis_report", args=[self.subject.pk])

    def test_latest_record_is_preselected(self):
        old = BFSTest.objects.create(
            user=self.subject, patient_name="王小明",
            test_date=timezone.now() - timedelta(days=4),
        )
        latest = BFSTest.objects.create(
            user=self.subject, patient_name="王小明", test_date=timezone.now(),
        )
        self.client.force_login(self.subject)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["bfs"], latest)
        self.assertEqual(response.context["overall"], "")
        self.assertContains(response, "尚無分析結果")
        self.assertNotEqual(old.pk, latest.pk)

    def test_entry_links_and_distant_dates_are_visible(self):
        BFSTest.objects.create(
            user=self.subject, patient_name="王小明",
            test_date=timezone.now() - timedelta(days=45),
        )
        self.client.force_login(self.subject)

        self.assertContains(self.client.get(reverse("start_analysis")), self.url)
        self.assertContains(
            self.client.get(reverse("subject_detail", args=[self.subject.pk])),
            self.url,
        )
        self.assertContains(self.client.get(self.url), "日期相隔超過 30 天")

    def test_unlinked_records_are_not_offered_as_subject_choices(self):
        BFSTest.objects.create(patient_name="舊資料")
        self.client.force_login(self.subject)

        response = self.client.get(self.url)

        self.assertContains(response, "此受測者尚無已綁定的 BFS 紀錄")
        self.assertContains(response, "此帳號尚無 BFS 檢測紀錄")
        self.assertContains(response, "查看 BFS 紀錄／比較趨勢")
        self.assertFalse(response.context["has_bfs"])

    def test_manual_choice_is_saved_and_new_upload_does_not_change_it(self):
        chosen = BFSTest.objects.create(
            user=self.subject, patient_name="王小明",
            test_date=timezone.now() - timedelta(days=2),
        )
        BFSTest.objects.create(
            user=self.subject, patient_name="王小明", test_date=timezone.now(),
        )
        self.client.force_login(self.subject)

        response = self.client.post(self.url, {
            "questionnaire": self.questionnaire.pk,
            "face": "", "bfs": chosen.pk, "meridian": "",
        })

        self.assertEqual(response.status_code, 302)
        report = AnalysisReport.objects.get()
        self.assertEqual(report.bfs_id, chosen.pk)
        self.assertEqual(report.selected_records["bfs"]["id"], chosen.pk)
        self.assertEqual(report.module_results["questionnaire"]["state"], "no")
        self.assertEqual(report.module_results["face"]["state"], "pending")
        self.assertEqual(report.overall_result, "")

        self.questionnaire.autoimmune_disease = True
        self.questionnaire.save()
        BFSTest.objects.create(
            user=self.subject, patient_name="王小明",
            test_date=timezone.now() + timedelta(days=1),
        )
        saved = self.client.get(f"{self.url}?report={report.pk}")
        self.assertEqual(saved.context["report"].bfs_id, chosen.pk)
        self.assertEqual(saved.context["rows"][0]["result"]["state"], "no")

    def test_changing_selection_previews_without_saving(self):
        older = BFSTest.objects.create(
            user=self.subject, patient_name="王小明",
            test_date=timezone.now() - timedelta(days=2),
        )
        BFSTest.objects.create(
            user=self.subject, patient_name="王小明", test_date=timezone.now(),
        )
        self.client.force_login(self.subject)

        response = self.client.get(self.url, {
            "questionnaire": "", "face": "", "bfs": older.pk, "meridian": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_preview"])
        rows = {row["key"]: row for row in response.context["rows"]}
        self.assertEqual(rows["bfs"]["record"]["id"], older.pk)
        self.assertEqual(rows["questionnaire"]["result"]["state"], "pending")
        self.assertEqual(AnalysisReport.objects.count(), 0)

    def test_preview_with_foreign_record_is_rejected(self):
        foreign = BFSTest.objects.create(user=self.other, patient_name="別人")
        self.client.force_login(self.subject)
        response = self.client.get(self.url, {"bfs": foreign.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["overall"], "")
        self.assertEqual(AnalysisReport.objects.count(), 0)

    def test_foreign_record_cannot_be_selected(self):
        foreign = BFSTest.objects.create(user=self.other, patient_name="他人")
        self.client.force_login(self.subject)

        response = self.client.post(self.url, {
            "questionnaire": self.questionnaire.pk,
            "face": "", "bfs": foreign.pk, "meridian": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn("bfs", response.context["form"].errors)
        self.assertFalse(AnalysisReport.objects.exists())

    def test_subject_access_and_researcher_write_permissions(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        researcher = User.objects.create_user(username="0944444444", password="pass")
        group, _ = Group.objects.get_or_create(name=RESEARCHER_GROUP_NAME)
        researcher.groups.add(group)
        self.client.force_login(researcher)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)

    def test_report_rules_do_not_treat_missing_data_as_no(self):
        self.assertEqual(overall_from_states(["no"] * 4), "green")
        self.assertEqual(overall_from_states(["yes", "no", "no", "no"]), "yellow")
        self.assertEqual(overall_from_states(["yes", "yes", "yes", "no"]), "red")
        self.assertEqual(overall_from_states(["no", "no", "no", "pending"]), "")

    def test_existing_module_rules_only_accept_complete_source_data(self):
        self.assertEqual(questionnaire_result(self.questionnaire)["state"], "no")
        self.questionnaire.autoimmune_disease = True
        self.assertEqual(questionnaire_result(self.questionnaire)["state"], "yes")

        bfs = BFSTest.objects.create(user=self.subject, patient_name="王小明")
        self.assertEqual(bfs_result(bfs)["state"], "pending")
        BFSTestFile.objects.create(
            bfs_test=bfs, file_number=1, pdf_file="bfs_tests/test.pdf",
            analysis_status="success",
            analysis_result={"color_analysis": {
                "total_all": 2, "quadrant_counts": {"左上": {"5": 1, "6": 0}},
            }},
        )
        self.assertEqual(bfs_result(bfs)["state"], "yes")

        meridian = MeridianTest.objects.create(
            user=self.subject, patient_name="王小明", result_pdf="meridian_tests/test.pdf",
            threshold_toohigh=90, threshold_toolow=10,
        )
        self.assertEqual(meridian_result(meridian)["state"], "pending")
        MeridianReading.objects.bulk_create([
            MeridianReading(
                meridian_test=meridian, meridian=f"經絡{index}",
                left_org=50, left_cmp=50, right_org=50, right_cmp=50,
            ) for index in range(12)
        ])
        self.assertEqual(meridian_result(meridian)["state"], "no")
        reading = meridian.readings.first()
        reading.left_org = 95
        reading.save()
        self.assertEqual(meridian_result(meridian)["state"], "yes")

    def test_three_line_meridian_report_never_counts_as_yes(self):
        """只有高、均、低三條線的報告沒有過高／過低線，讀數再極端也判「無」。"""
        meridian = MeridianTest.objects.create(
            user=self.subject, patient_name="王小明", result_pdf="meridian_tests/test.pdf",
            threshold_high=70, threshold_average=50, threshold_low=30,
        )
        self.assertEqual(meridian_result(meridian)["state"], "pending")
        MeridianReading.objects.bulk_create([
            MeridianReading(
                meridian_test=meridian, meridian=f"經絡{index}",
                left_org=99, left_cmp=1, right_org=99, right_cmp=1,
            ) for index in range(12)
        ])
        result = meridian_result(meridian)
        self.assertEqual(result["state"], "no")
        self.assertIn("過旺／過低的門檻值內", result["reason"])

    def test_trends_reject_records_without_verified_subject(self):
        bfs_a = BFSTest.objects.create(patient_name="舊資料 A")
        bfs_b = BFSTest.objects.create(patient_name="舊資料 B")
        meridian_a = MeridianTest.objects.create(
            patient_name="舊資料 A", result_pdf="meridian_tests/a.pdf"
        )
        meridian_b = MeridianTest.objects.create(
            patient_name="舊資料 B", result_pdf="meridian_tests/b.pdf"
        )
        self.client.force_login(self.staff)

        bfs_list = self.client.get(reverse("bfs_list"))
        self.assertNotContains(bfs_list, 'class="bfs-compare-checkbox"')
        self.assertEqual(
            self.client.get(f"{reverse('bfs_trend')}?ids={bfs_a.pk},{bfs_b.pk}").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                f"{reverse('meridian_trend')}?ids={meridian_a.pk},{meridian_b.pk}"
            ).status_code,
            400,
        )


class SystemTableTests(TestCase):
    def setUp(self):
        self.subject = User.objects.create_user(username="0955555555", password="pass")

    def _questionnaire(self, **flags):
        return Questionnaire.objects.create(
            user=self.subject, name="王小明", gender="M", blood_type="O",
            height=170, weight=65, birth_date=date(2000, 1, 1), sleep_hours=7, **flags,
        )

    def test_questionnaire_fields_light_only_their_own_system(self):
        cells = questionnaire_systems(self._questionnaire(diabetes=True, lung_asthma=True))
        self.assertEqual(cells["endocrine"]["state"], "yes")
        self.assertEqual(cells["respiratory"]["state"], "yes")
        self.assertEqual(cells["cardio"]["state"], "no")
        self.assertEqual(set(cells), set(SYSTEM_KEYS))

    def test_missing_module_is_pending_for_every_system(self):
        for evaluator in (questionnaire_systems, face_systems, bfs_systems, meridian_systems):
            self.assertEqual({c["state"] for c in evaluator(None).values()}, {"pending"})

    def test_every_system_is_reachable_from_bfs_templates(self):
        from .services.system_mapping import _bfs_templates
        covered = set()
        for template in _bfs_templates():
            for systems in bfs_quadrant_systems(template).values():
                covered.update(systems)
        self.assertEqual(covered, set(SYSTEM_KEYS))
        self.assertEqual(
            bfs_quadrant_systems("bfs1")["左下"], {"digestive", "endocrine", "immune"},
        )

    def test_bfs_lights_systems_of_severe_quadrant_and_leaves_missing_files_pending(self):
        bfs = BFSTest.objects.create(user=self.subject, patient_name="王小明")
        BFSTestFile.objects.create(
            bfs_test=bfs, file_number=1, pdf_file="bfs_tests/a.pdf",
            analysis_status="success", detected_template="bfs3",
            analysis_result={"color_analysis": {
                "total_all": 4,
                "quadrant_counts": {
                    "左上": {"5": 1, "6": 0}, "右上": {"5": 0, "6": 0},
                    "左下": {"5": 0, "6": 0}, "右下": {"5": 0, "6": 0},
                },
            }},
        )
        cells = bfs_systems(bfs)
        self.assertEqual(cells["respiratory"]["state"], "yes")
        self.assertEqual(cells["urinary"]["state"], "no")
        self.assertEqual(cells["cardio"]["state"], "pending")

    def test_meridian_maps_real_meridian_names_to_systems(self):
        meridian = MeridianTest.objects.create(
            user=self.subject, patient_name="王小明", result_pdf="meridian_tests/t.pdf",
            threshold_toohigh=90, threshold_toolow=10,
        )
        names = ["肺經", "心包", "心經", "小腸", "三焦", "大腸", "脾經", "肝經", "腎經", "膀胱", "膽經", "胃經"]
        MeridianReading.objects.bulk_create([
            MeridianReading(
                meridian_test=meridian, meridian=name,
                left_org=95 if name == "三焦" else 50, left_cmp=50, right_org=50, right_cmp=50,
            ) for name in names
        ])
        cells = meridian_systems(meridian)
        self.assertEqual(cells["endocrine"]["state"], "yes")
        self.assertEqual(cells["respiratory"]["state"], "no")
        self.assertEqual(set(cells), set(SYSTEM_KEYS))

    def test_face_zones_map_to_systems(self):
        from .models import FaceDiagnosis
        face = FaceDiagnosis.objects.create(
            user=self.subject, patient_name="王小明", front_image="face_diagnosis/t.png",
            analysis_status="done",
            analysis_report={"total": 2, "zones": {"hit_zones": [
                {"id": "pancreas_L", "organ": "胰", "count": 1},
                {"id": "temple_R", "organ": "—", "count": 1},
            ]}},
        )
        cells = face_systems(face)
        self.assertEqual(cells["endocrine"]["state"], "yes")
        self.assertEqual(cells["digestive"]["state"], "yes")
        self.assertEqual(cells["neuro"]["state"], "yes")
        self.assertEqual(cells["respiratory"]["state"], "no")

    def test_system_overall_requires_all_four_modules(self):
        rows = build_system_rows({"questionnaire": self._questionnaire()})
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["overall"] == "" for row in rows))
        self.assertEqual(rows[0]["cells"][0]["state"], "no")
        self.assertEqual(rows[0]["cells"][1]["state"], "pending")
