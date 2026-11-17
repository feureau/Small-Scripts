"""Preservation, matching, and validation regressions using local fixtures only."""

import copy
import json
from pathlib import Path
import sys
import tempfile
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt
from test_yt_upload_metadata import FakeService


class MetadataSafetyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.logger = self.patch("logger")
        self.media = self.patch("MediaFileUpload")
        self.move = self.patch("move_uploaded_files")
        self.service = FakeService()

    def patch(self, name):
        patcher = patch.object(yt, name)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def video(self, metadata=None, *, sidecar=False):
        video = yt.VideoData(
            "existing-video-id", "Remote title",
            {
                "title": "Remote title", "description": "Remote description\nwith chapters",
                "tags": ["Remote tag", "\u4e2d\u6587"], "categoryId": "27",
                "defaultLanguage": "zh", "defaultAudioLanguage": "zh",
                "channelId": "read-only", "thumbnails": {"default": {"url": "read-only"}},
            },
            {"privacyStatus": "private", "embeddable": True},
        )
        if metadata is not None:
            if sidecar:
                path = self.write_json("episode-youtube.json", metadata)
                video.description_file_path = str(path)
            else:
                video.main_json_dict = metadata
        return video

    def options(self, *videos, **changes):
        return {
            "videos": list(videos), "is_dry_run": False, "update_metadata": True,
            "update_schedule": False, "remove_schedule": False, "update_visibility": False,
            "visibility_to_set": "private", "description_override": "", "tags_override": "",
            "category_id": None, "public_stats_viewable": False, "allow_embedding": True,
            "made_for_kids": "dont_change", **changes,
        }

    def write_json(self, name, data):
        path = self.directory / name
        path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
        return path

    def upload_entry(self, data, *, name="episode-youtube.json"):
        path = self.directory / "episode.mp4"
        path.write_bytes(b"mocked media")
        self.write_json(name, data)
        return yt.VideoEntry(str(path))

    def test_missing_source_fields_preserve_remote_values_and_languages(self):
        for sidecar in (False, True):
            with self.subTest(sidecar=sidecar):
                video = self.video({"title": "New title"}, sidecar=sidecar)
                service = FakeService()
                yt.update_videos_on_youtube(service, self.options(video))
                snippet = service.resource.updates[0]["body"]["snippet"]
                self.assertEqual(snippet, {
                    "title": "New title", "description": "Remote description\nwith chapters",
                    "tags": ["Remote tag", "\u4e2d\u6587"], "categoryId": "27",
                    "defaultLanguage": "zh", "defaultAudioLanguage": "zh",
                })

    def test_explicit_empty_tags_clear_but_missing_tags_preserve(self):
        for metadata, expected in (({"title": "New"}, ["Remote tag", "\u4e2d\u6587"]), ({"tags": []}, [])):
            with self.subTest(metadata=metadata):
                service = FakeService()
                yt.update_videos_on_youtube(service, self.options(self.video(metadata)))
                self.assertEqual(service.resource.updates[0]["body"]["snippet"]["tags"], expected)

    def test_invalid_metadata_rejects_only_its_item_without_api_write(self):
        for invalid in (None, "tag", ["valid", 4]):
            with self.subTest(tags=invalid):
                service = FakeService()
                bad = self.video({"tags": invalid})
                good = self.video({"tags": ["Valid"]})
                good.video_id = "good-video-id"
                original = copy.deepcopy(bad.video_snippet)
                yt.update_videos_on_youtube(service, self.options(bad, good))
                self.assertEqual([r["body"]["id"] for r in service.resource.updates], ["good-video-id"])
                self.assertEqual(bad.video_snippet, original)

    def test_missing_required_remote_fields_do_not_use_display_defaults(self):
        for field in ("title", "categoryId"):
            with self.subTest(field=field):
                video = self.video({"tags": ["New tag"]})
                del video.video_snippet[field]
                service = FakeService()
                yt.update_videos_on_youtube(service, self.options(video))
                self.assertEqual(service.resource.updates, [])

    def test_empty_gui_override_preserves_and_nonempty_override_replaces_tags(self):
        for override, expected in (("  ", ["Remote tag", "\u4e2d\u6587"]), ("Stolas,Helluva Boss", ["Stolas", "Helluva Boss"])):
            with self.subTest(override=override):
                service = FakeService()
                yt.update_videos_on_youtube(service, self.options(self.video(), tags_override=override))
                self.assertEqual(service.resource.updates[0]["body"]["snippet"]["tags"], expected)

    def test_success_refreshes_preservation_snapshot_and_dry_run_does_not(self):
        video = self.video({"tags": ["First"]})
        original = copy.deepcopy(video.video_snippet)
        yt.update_videos_on_youtube(self.service, self.options(video, is_dry_run=True))
        self.assertEqual(video.video_snippet, original)
        self.assertEqual(self.service.resource.updates, [])
        yt.update_videos_on_youtube(self.service, self.options(video))
        video.main_json_dict = {"title": "Second title"}
        yt.update_videos_on_youtube(self.service, self.options(video))
        self.assertEqual(self.service.resource.updates[-1]["body"]["snippet"]["tags"], ["First"])

    def test_failed_api_update_does_not_change_the_preservation_snapshot(self):
        video = self.video({"tags": ["Replacement"]})
        original = copy.deepcopy(video.video_snippet)
        error = yt.HttpError(SimpleNamespace(status=500, reason="fixture failure"), b'{"error":{"message":"fixture failure"}}')
        self.service.resource.update = Mock(side_effect=error)
        yt.update_videos_on_youtube(self.service, self.options(video))
        self.assertEqual(video.video_snippet, original)
        self.assertEqual(video.current_tags, original["tags"])

    def test_status_only_ignores_bad_local_metadata_and_never_sends_snippet(self):
        video = self.video({"tags": None})
        video.metadata_error = "Ambiguous sidecar"
        yt.update_videos_on_youtube(self.service, self.options(video, update_metadata=False))
        request = self.service.resource.updates[0]
        self.assertEqual(request["part"], "status")
        self.assertNotIn("snippet", request["body"])

    def test_exact_upload_sidecar_beats_fuzzy_matches_and_timing_json(self):
        self.upload_entry({"title": "Wrong fallback"}, name="episode-top.json")
        self.write_json("episode-words.json", {"words": [{"text": "not metadata"}]})
        entry = self.upload_entry({"title": "Exact title", "tags": ["Exact"]})
        self.assertEqual(entry.title, "Exact title")
        self.assertEqual(entry.description_source, "episode-youtube.json")
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts[0]["body"]["snippet"]["tags"], ["Exact"])

    def test_fallback_only_accepts_metadata_shaped_json(self):
        self.upload_entry({"words": []}, name="episode-timing.json")
        entry = self.upload_entry({"title": "Legacy title"}, name="episode-legacy.json")
        self.assertEqual(entry.title, "Legacy title")
        self.assertEqual(entry.description_source, "episode-legacy.json")

    def test_tied_upload_fallbacks_are_reported_and_block_execution(self):
        self.upload_entry({"title": "Top"}, name="episode-top-youtube.json")
        entry = self.upload_entry({"title": "Bottom"}, name="episode-bottom-youtube.json")
        self.assertIn("Ambiguous", entry.metadata_error)
        for dry_run in (False, True):
            yt.upload_new_videos(self.service, [entry], True, True, dry_run=dry_run)
        self.media.assert_not_called()
        self.move.assert_not_called()
        self.assertEqual(self.service.resource.inserts, [])

    def test_invalid_exact_sidecar_blocks_fallback_instead_of_uploading_defaults(self):
        self.upload_entry({"title": "Fallback"}, name="episode-legacy.json")
        for invalid in ([], None, {"words": []}, {"tags": "string"}, {"tags": ["valid", 3]}):
            with self.subTest(invalid=invalid):
                entry = self.upload_entry(invalid)
                yt.upload_new_videos(self.service, [entry], True, False)
                self.assertEqual(self.service.resource.inserts, [])

    def test_explicit_batch_filename_wins_over_an_earlier_normalized_match(self):
        entry = self.upload_entry({"title": "Sidecar"})
        entry = yt.VideoEntry(entry.filepath, [
            {"filename": "episode!", "title": "Loose match"},
            {"filename": "episode.mp4", "title": "Explicit match"},
        ])
        self.assertEqual(entry.title, "Explicit match")

    def fetched_video(self, *, title="episode", main_json=None, filename="episode.mp4"):
        resource = self.service.resource
        resource.list = Mock(return_value=SimpleNamespace(execute=Mock(return_value={"items": [{
            "id": "existing-video-id", "snippet": {"title": title, "categoryId": "24", "tags": ["Remote"]},
            "status": {"privacyStatus": "private"}, "fileDetails": {"fileName": filename},
        }]})))
        playlist = SimpleNamespace(list=Mock(return_value=SimpleNamespace(execute=Mock(return_value={
            "items": [{"contentDetails": {"videoId": "existing-video-id"}}],
        }))))
        self.service.playlistItems = Mock(return_value=playlist)
        app = SimpleNamespace(service=self.service, main_json_data=main_json, update_status=Mock())
        app._match_video_to_main_json = MethodType(yt.MainApp._match_video_to_main_json, app)
        app._apply_main_json_to_video = MethodType(yt.MainApp._apply_main_json_to_video, app)
        with patch.object(yt.Path, "cwd", return_value=self.directory):
            videos = yt.MainApp.fetch_all_videos_from_api(app, playlist_id="fixture-playlist")
        self.assertEqual(len(videos), 1)
        return videos[0]

    def test_update_matching_prefers_original_filename_exact_sidecar(self):
        self.write_json("episode-top-youtube.json", {"title": "Wrong render"})
        exact = self.write_json("episode-youtube.json", {"title": "Exact render"})
        video = self.fetched_video(title="A different remote title")
        self.assertEqual(video.description_file_path, str(exact))

    def test_tied_update_sidecars_block_metadata_updates(self):
        self.write_json("episode-top-youtube.json", {"title": "Top"})
        self.write_json("episode-bottom-youtube.json", {"title": "Bottom"})
        video = self.fetched_video()
        self.assertIn("Ambiguous", video.metadata_error)
        yt.update_videos_on_youtube(self.service, self.options(video))
        self.assertEqual(self.service.resource.updates, [])

    def test_explicit_batch_video_id_precedes_filename_and_sidecar_matches(self):
        self.write_json("episode-youtube.json", {"title": "Sidecar"})
        video = self.fetched_video(main_json=[
            {"filename": "episode.mp4", "title": "Filename match"},
            {"video_id": "existing-video-id", "title": "ID match"},
        ])
        self.assertEqual(video.main_json_dict["title"], "ID match")

    def test_description_validates_utf8_bytes_without_truncating_copy(self):
        for text in ("x" * 5000, "\u4e2d" * 1666 + "ab"):
            with self.subTest(bytes=len(text.encode("utf-8"))):
                self.assertEqual(yt.sanitize_description(text), text)
                with self.assertRaisesRegex(ValueError, "5000.*bytes"):
                    yt.sanitize_description(text + "x")

    def test_description_assembly_appends_hashtags_once_and_checks_final_size(self):
        original = 'A "quotation"\n00:00 Beginning\nhttps://example.com/#Stolas'
        assembled = original + "\n\n#Stolas"
        self.assertEqual(yt.assemble_description(original, ["#Stolas"]), assembled)
        self.assertEqual(yt.assemble_description(assembled, ["#Stolas"]), assembled)
        suffix = "\n\n#Stolas"
        body = "x" * (5000 - len(suffix.encode("utf-8")))
        self.assertEqual(len(yt.assemble_description(body, ["#Stolas"]).encode("utf-8")), 5000)
        with self.assertRaisesRegex(ValueError, "5000.*bytes"):
            yt.assemble_description(body + "x", ["#Stolas"])

    def test_platform_tag_counter_has_independent_500_and_501_boundaries(self):
        self.assertEqual(yt.effective_tag_length(["a b", "c"]), 7)
        self.assertEqual(yt.effective_tag_length(["x" * 500]), 500)
        yt.validate_tag_budget(["x" * 500])
        with self.assertRaisesRegex(ValueError, "500"):
            yt.validate_tag_budget(["x" * 501])
        local_maximum = [f'{index:02d} ' + 'x' * 27 for index in range(15)]
        self.assertEqual(yt.effective_tag_length(yt.prepare_tags(local_maximum)), 494)

    def test_incompatible_tags_reject_upload_instead_of_silently_losing_keywords(self):
        for tags in (["Stolas!"], ["\u4e2d\u6587"], ["x" * 31], [""], ["same", "same"], [str(i) for i in range(16)]):
            with self.subTest(tags=tags):
                entry = self.upload_entry({"title": "Valid", "tags": tags})
                yt.upload_new_videos(self.service, [entry], True, True)
                self.assertEqual(self.service.resource.inserts, [])
        self.media.assert_not_called()
        self.move.assert_not_called()
        self.assertTrue(self.logger.error.called)

    def test_explicit_legacy_cleanup_reports_losses_and_is_idempotent(self):
        diagnostics = []
        tags = yt.sanitize_tags(["Stolas!", " \u4e2d\u6587 ", "x" * 31, "same", "same"], diagnostics=diagnostics)
        self.assertEqual(tags, ["Stolas", "x" * 30, "same"])
        self.assertTrue(diagnostics)
        again = []
        self.assertEqual(yt.sanitize_tags(tags, diagnostics=again), tags)
        self.assertEqual(again, [])

    def test_bad_title_description_or_hashtag_types_never_upload(self):
        for metadata in (
            {"title": None}, {"description": []}, {"hashtags": None}, {"hashtags": "#Stolas"},
            {"title": "x" * 101}, {"title": "Bad <title>"}, {"description": "Bad <copy>"},
            {"description": "\u4e2d" * 1667}, {"description": "copy", "hashtags": ["not-a-hashtag"]},
        ):
            with self.subTest(metadata=metadata):
                entry = self.upload_entry(metadata)
                yt.upload_new_videos(self.service, [entry], True, False, dry_run=True)
                yt.upload_new_videos(self.service, [entry], True, False)
                self.assertEqual(self.service.resource.inserts, [])
        self.media.assert_not_called()

    def test_update_validates_supplied_metadata_and_preserves_unicode_remote_tags(self):
        invalid = self.video({"tags": ["\u4e2d\u6587"]})
        valid = self.video({"description": "Approved \u4e2d\u6587\n00:00 Start", "hashtags": ["#Stolas"]})
        yt.update_videos_on_youtube(self.service, self.options(invalid, valid))
        self.assertEqual(len(self.service.resource.updates), 1)
        snippet = self.service.resource.updates[0]["body"]["snippet"]
        self.assertEqual(snippet["description"], "Approved \u4e2d\u6587\n00:00 Start\n\n#Stolas")
        self.assertEqual(snippet["tags"], ["Remote tag", "\u4e2d\u6587"])

    def test_metadata_updates_preserve_unedited_status_fields(self):
        video = self.video({"title": "New title"})
        video.video_status.update(license="creativeCommon", containsSyntheticMedia=True)
        yt.update_videos_on_youtube(self.service, self.options(video))
        status = self.service.resource.updates[0]["body"]["status"]
        self.assertEqual(status["license"], "creativeCommon")
        self.assertIs(status["containsSyntheticMedia"], True)

    def test_invalid_exact_update_sidecar_blocks_valid_fallback(self):
        self.write_json("episode-legacy.json", {"title": "Fallback"})
        for invalid in ({"tags": None}, {"words": []}, [], None):
            with self.subTest(invalid=invalid):
                self.write_json("episode-youtube.json", invalid)
                video = self.fetched_video()
                self.assertTrue(video.metadata_error)
                yt.update_videos_on_youtube(self.service, self.options(video))
                self.assertEqual(self.service.resource.updates, [])

    def test_duplicate_exact_sidecars_in_subfolders_are_ambiguous(self):
        for folder in ("top", "bottom"):
            (self.directory / folder).mkdir()
            self.write_json(f"{folder}/episode-youtube.json", {"title": folder})
        video = self.fetched_video()
        self.assertIn("Ambiguous", video.metadata_error)
        yt.update_videos_on_youtube(self.service, self.options(video))
        self.assertEqual(self.service.resource.updates, [])

    def test_duplicate_batch_mappings_reject_upload_without_falling_back(self):
        entry = self.upload_entry({"title": "Sidecar"})
        entry = yt.VideoEntry(entry.filepath, [
            {"filename": "episode.mp4", "title": "First"},
            {"filename": "episode.mp4", "title": "Second"},
        ])
        self.assertIn("Ambiguous", entry.metadata_error)
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts, [])

    def test_malformed_legacy_sidecar_rejects_upload_instead_of_using_defaults(self):
        entry = self.upload_entry({"tags": None}, name="episode-legacy.json")
        self.assertTrue(entry.metadata_error)
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts, [])

    def test_malformed_matching_update_sidecar_rejects_item(self):
        self.write_json("episode-legacy.json", {"tags": "not-an-array"})
        video = self.fetched_video()
        self.assertTrue(video.metadata_error)
        yt.update_videos_on_youtube(self.service, self.options(video))
        self.assertEqual(self.service.resource.updates, [])

    def test_timing_json_with_a_title_is_never_used_as_upload_metadata(self):
        entry = self.upload_entry({"title": "Timing export", "words": []}, name="episode-timing.json")
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts, [])

    def test_unselected_main_json_is_not_used_as_a_local_sidecar(self):
        self.write_json("main.json", {"title": "episode", "tags": ["Unselected"]})
        video = self.fetched_video()
        self.assertIsNone(video.description_file_path)

    def test_upload_fallback_never_crosses_top_bottom_render_markers(self):
        path = self.directory / "Marker 1 - top.mp4"
        path.write_bytes(b"mocked media")
        self.write_json("Marker 1 - bottom-youtube.json", {"title": "Wrong bottom render"})
        entry = yt.VideoEntry(str(path))
        self.assertIsNone(entry.description_file_path)
        self.assertEqual(entry.tags, [])

    def test_update_fallback_respects_render_marker_in_original_filename(self):
        self.write_json("episode-bottom-youtube.json", {"title": "Wrong bottom render"})
        video = self.fetched_video(filename="episode-top.mp4")
        self.assertIsNone(video.description_file_path)

    def test_explicit_legacy_cleanup_works_for_update_and_reports_changes(self):
        video = self.video({"tags": ["Stolas!", "Stolas!"]})
        yt.update_videos_on_youtube(self.service, self.options(video, legacy_tag_cleanup=True))
        self.assertEqual(self.service.resource.updates[0]["body"]["snippet"]["tags"], ["Stolas"])
        self.assertTrue(self.logger.warning.called)

    def test_prefilled_gui_values_are_not_mistaken_for_user_overrides(self):
        video = self.video({"title": "Source title"})
        app = SimpleNamespace(
            app_mode="update", videos_to_process=[video], tree=Mock(), process_button=Mock(),
            update_status=Mock(), run_update_processing=Mock(), dynamic_category_map={},
            desc_txt=Mock(), tags_ent=Mock(), category_cb=Mock(), metadata_lang_cb=Mock(), audio_lang_cb=Mock(),
        )
        values = {
            "schedule_order_var": "As is", "interval_hour_var": "1", "interval_minute_var": "0",
            "start_ent": "2030-01-01 00:00", "playlist_id_var": "", "dry_run_var": True,
            "update_metadata_var": True, "update_schedule_var": False, "remove_schedule_var": False,
            "update_visibility_var": False, "visibility_choice_var": "private", "notify_subscribers_var": False,
            "category_var": "Don't Change", "metadata_lang_var": "Chinese", "audio_lang_var": "Chinese",
            "recording_date_var": "", "allow_embedding_var": True, "public_stats_var": False,
            "made_for_kids_var": "dont_change",
        }
        for name, value in values.items():
            setattr(app, name, SimpleNamespace(get=Mock(return_value=value), set=Mock()))
        app.tree.selection.return_value = (video.video_id,)
        app.desc_txt.get.return_value = video.current_description
        app.tags_ent.get.return_value = ", ".join(video.current_tags)
        yt.MainApp.on_video_select_display_info(app, None)
        for changed_tags, expected in ((None, ""), ("New tag", "New tag")):
            with self.subTest(changed_tags=changed_tags):
                if changed_tags is not None:
                    app.tags_ent.get.return_value = changed_tags
                with patch.object(yt.threading, "Thread") as thread, patch.object(yt.tk, "BooleanVar"):
                    yt.MainApp.start_processing_thread(app)
                    options, = thread.call_args.kwargs["args"]
                self.assertEqual(options["description_override"], "")
                self.assertEqual(options["tags_override"], expected)


if __name__ == "__main__":
    unittest.main()
