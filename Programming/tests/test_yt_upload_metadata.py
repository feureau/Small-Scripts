"""Request-level uploader regressions; no GUI, authentication, or network calls."""

import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt


TAGS = ["Stolas", "Helluva Boss", "Stolas analysis"]


class FakeVideos:
    def __init__(self, *, upload_error=None):
        self.inserts = []
        self.updates = []
        self.events = []
        self.upload_error = upload_error
        self.chunks = iter([(None, None), (None, {"id": "fixture-video-id"})])
        self.request = SimpleNamespace(next_chunk=Mock(side_effect=self.next_chunk))

    def insert(self, *, part, body, media_body):
        self.events.append("insert")
        self.inserts.append({"part": part, "body": copy.deepcopy(body), "media_body": media_body})
        return self.request

    def next_chunk(self):
        self.events.append("next_chunk")
        if self.upload_error:
            raise self.upload_error
        result = next(self.chunks)
        if result[1] is not None:
            self.events.append("upload_succeeded")
        return result

    def update(self, *, part, body):
        self.updates.append({"part": part, "body": copy.deepcopy(body)})
        return SimpleNamespace(execute=Mock(return_value={"id": "existing-video-id"}))


class FakeService:
    def __init__(self, **kwargs):
        self.resource = FakeVideos(**kwargs)
        self.videos = Mock(return_value=self.resource)


class UploadMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.logger = self.patch("logger")
        self.media = self.patch("MediaFileUpload")
        self.move = self.patch("move_uploaded_files")
        self.authenticate = self.patch("get_authenticated_service")
        self.authenticate.side_effect = AssertionError("Tests must never authenticate")
        self.service = FakeService()

    def patch(self, name):
        patcher = patch.object(yt, name)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def entry(self, stem="episode", tags=TAGS, *, main_json=False):
        video = self.directory / f"{stem}.mp4"
        video.write_bytes(b"fake media; MediaFileUpload is mocked")
        metadata = {
            "title": "Stolas and Helluva Boss",
            "description": 'Approved copy.\nA "quotation" and a link: https://example.com/#chapter',
            "hashtags": ["#Stolas", "#HelluvaBoss"],
            "tags": list(tags),
        }
        sidecar = video.with_name(f"{stem}-youtube.json")
        if main_json:
            # An explicit mapping must win over adjacent metadata.
            sidecar.write_text(json.dumps({**metadata, "tags": ["Wrong sidecar"]}), encoding="utf-8")
            mapping = self.directory / "main.json"
            mapping.write_text(json.dumps([{**metadata, "filename": video.name}]), encoding="utf-8")
            return yt.VideoEntry(str(video), json.loads(mapping.read_text(encoding="utf-8")))
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        return yt.VideoEntry(str(video))

    def messages(self, level="info"):
        messages = []
        for call in getattr(self.logger, level).call_args_list:
            message, *args = call.args
            messages.append(message % tuple(args) if args else message)
        return "\n".join(messages)

    def test_local_sidecar_tags_reach_insert_in_order_for_long_and_short_uploads(self):
        # Uploading uses the same entry contract for regular videos and Shorts.
        for stem in ("long-video", "shorts-video"):
            with self.subTest(stem=stem):
                entry = self.entry(stem)
                service = FakeService()
                yt.upload_new_videos(service, [entry], True, False)
                self.assertEqual(service.resource.inserts[0]["body"]["snippet"]["tags"], TAGS)

    def test_explicit_main_json_tags_reach_insert(self):
        entry = self.entry(main_json=True)
        self.assertEqual(entry.description_source, "main.json")
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts[0]["body"]["snippet"]["tags"], TAGS)

    def test_empty_tags_are_an_empty_list(self):
        entry = self.entry(tags=[])
        yt.upload_new_videos(self.service, [entry], True, False)
        self.assertEqual(self.service.resource.inserts[0]["body"]["snippet"]["tags"], [])

    def test_legacy_cleanup_is_preserved_in_request(self):
        entry = self.entry(tags=["  Stolas! ", "Helluva/Boss", "x" * 35, "", "中文", "same", "same"])
        yt.upload_new_videos(self.service, [entry], True, False, legacy_tag_cleanup=True)
        self.assertEqual(
            self.service.resource.inserts[0]["body"]["snippet"]["tags"],
            ["Stolas", "HelluvaBoss", "x" * 30, "same"],
        )

    def test_existing_status_metadata_and_resumable_settings_are_preserved(self):
        for scheduled, made_for_kids in ((None, False), ("2030-01-02T03:04:05Z", True)):
            with self.subTest(scheduled=scheduled):
                entry = self.entry()
                entry.publishAt = scheduled
                entry.madeForKids = made_for_kids
                entry.categoryId = "27"
                service = FakeService()
                yt.upload_new_videos(service, [entry], False, False)
                request = service.resource.inserts[0]
                self.assertEqual(request["part"], "snippet,status")
                self.assertEqual(request["body"], {
                    "snippet": {
                        "title": entry.title,
                        "description": entry.description,
                        "categoryId": "27",
                        "tags": TAGS,
                    },
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": scheduled,
                        "selfDeclaredMadeForKids": made_for_kids,
                    },
                })
                self.media.assert_called_with(entry.filepath, chunksize=-1, resumable=True)
                self.assertIs(request["media_body"], self.media.return_value)
                self.assertEqual(service.resource.request.next_chunk.call_count, 2)
                self.assertEqual(service.resource.updates, [])

    def test_upload_failure_retains_sources_and_reports_no_success(self):
        entry = self.entry()
        service = FakeService(upload_error=RuntimeError("fixture upload failure"))
        yt.upload_new_videos(service, [entry], True)
        self.move.assert_not_called()
        self.assertTrue(Path(entry.filepath).is_file())
        self.assertTrue(Path(entry.description_file_path).is_file())
        self.assertIn("Successfully uploaded: 0", self.messages())
        self.assertNotIn("https://youtu.be/", self.messages())
        self.assertIn("fixture upload failure", self.messages("error"))

    def test_file_movement_follows_success_only_when_enabled(self):
        entry = self.entry()
        self.move.side_effect = lambda *args: self.service.resource.events.append("move")
        yt.upload_new_videos(self.service, [entry], True)
        self.move.assert_called_once()
        self.assertIs(self.move.call_args.args[0], entry)
        self.assertTrue(self.move.call_args.args[2])
        self.assertEqual(self.service.resource.events[-2:], ["upload_succeeded", "move"])
        self.assertIn("Successfully uploaded: 1", self.messages())
        self.move.reset_mock()
        yt.upload_new_videos(FakeService(), [entry], True, False)
        self.move.assert_not_called()

    def test_dry_run_never_constructs_media_calls_api_or_moves_files(self):
        entry = self.entry()
        yt.upload_new_videos(self.service, [entry], False, True, dry_run=True)
        self.media.assert_not_called()
        self.service.videos.assert_not_called()
        self.service.resource.request.next_chunk.assert_not_called()
        self.move.assert_not_called()
        self.authenticate.assert_not_called()
        self.assertTrue(Path(entry.filepath).is_file())
        self.assertTrue(Path(entry.description_file_path).is_file())
        self.assertIn("Planned uploads (Dry Run): 1", self.messages())
        self.assertIn("Successfully uploaded: 0", self.messages())
        self.assertNotIn("https://youtu.be/", self.messages())

    def test_dry_run_without_service_prepares_the_exact_execution_body(self):
        for main_json in (False, True):
            with self.subTest(main_json=main_json):
                entry = self.entry(tags=["Stolas", "Helluva Boss"], main_json=main_json)
                entry.description += "\n\u4e2d\u6587"
                entry.publishAt = "2030-01-02T03:04:05Z"
                yt.upload_new_videos(None, [entry], True, True, dry_run=True)
                # DEBUG output exposes the full prepared body without verbose ordinary logs.
                prepared_body = self.logger.debug.call_args.args[-1]
                self.assertIsInstance(prepared_body, dict)
                self.assertIn(entry.filepath, self.messages())
                self.assertIn(entry.description_source, self.messages())
                self.assertIn("Stolas", self.messages())
                self.assertIn("snippet,status", self.messages())
                self.assertIn("2030-01-02T03:04:05Z", self.messages())
                self.media.assert_not_called()
                service = FakeService()
                yt.upload_new_videos(service, [entry], True, False)
                self.assertEqual(prepared_body, service.resource.inserts[0]["body"])
                self.media.reset_mock()

    def test_actual_upload_requires_service_before_constructing_media(self):
        with self.assertRaisesRegex(ValueError, "authenticated"):
            yt.upload_new_videos(None, [self.entry()], True)
        self.media.assert_not_called()
        self.authenticate.assert_not_called()
        self.move.assert_not_called()

    def test_blank_metadata_is_skipped_for_preview_and_execution(self):
        entry = self.entry()
        Path(entry.description_file_path).write_text("", encoding="utf-8")
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                yt.upload_new_videos(self.service, [entry], True, True, dry_run=dry_run)
                self.assertIn("Skipped (blank metadata): 1", self.messages())
        self.media.assert_not_called()
        self.service.videos.assert_not_called()
        self.move.assert_not_called()

    def app_stub(self, entry, *, dry_run=False, service=None):
        # Call controller methods on a stub without constructing MainApp or Tk.
        app = SimpleNamespace(
            app_mode="upload", service=service, videos_to_process=[entry],
            tree=Mock(), process_button=Mock(), root=Mock(), update_status=Mock(),
            schedule_order_var=Mock(), skip_subs_var=Mock(),
            move_files_var=Mock(), dry_run_var=Mock(), run_upload_processing=Mock(),
        )
        app.tree.selection.return_value = (entry.filepath,)
        app.schedule_order_var.get.return_value = "As is"
        app.skip_subs_var.get.return_value = False
        app.move_files_var.get.return_value = True
        app.dry_run_var.get.return_value = dry_run
        app.root.after.side_effect = lambda delay, callback: callback()
        return app

    def test_gui_snapshots_selected_entries_and_options_before_worker_starts(self):
        for dry_run in (False, True):
            with self.subTest(dry_run=dry_run):
                entry = self.entry()
                app = self.app_stub(entry, dry_run=dry_run, service=self.service)
                with patch.object(yt.threading, "Thread") as thread:
                    yt.MainApp.start_processing_thread(app)
                    thread.return_value.start.assert_called_once()
                    options, = thread.call_args.kwargs["args"]
                self.assertEqual(options.video_entries, (entry,))
                self.assertIs(options.dry_run, dry_run)
                with self.assertRaises(AttributeError):
                    options.dry_run = not dry_run
                app.videos_to_process.clear()
                for variable in (app.skip_subs_var, app.move_files_var, app.dry_run_var):
                    variable.get.side_effect = AssertionError("Worker read a GUI variable")
                with patch.object(yt, "upload_new_videos") as upload:
                    yt.MainApp.run_upload_processing(app, options)
                    upload.assert_called_once_with(self.service, (entry,), False, True, dry_run=dry_run)
                for variable in (app.skip_subs_var, app.move_files_var, app.dry_run_var):
                    variable.get.assert_called_once()

    def test_worker_allows_preview_without_authentication(self):
        entry = self.entry()
        app = self.app_stub(entry, dry_run=True)
        options = yt.UploadJobOptions((entry,), False, True, True)
        yt.MainApp.run_upload_processing(app, options)
        self.authenticate.assert_not_called()
        self.media.assert_not_called()
        self.move.assert_not_called()
        app.update_status.assert_called_with("Upload preview complete.")

    def test_worker_requires_authentication_for_actual_upload(self):
        entry = self.entry()
        app = self.app_stub(entry)
        options = yt.UploadJobOptions((entry,), False, True, False)
        with patch.object(yt, "upload_new_videos") as upload:
            yt.MainApp.run_upload_processing(app, options)
            upload.assert_not_called()
        app.update_status.assert_called_with("Error: Not authenticated.")
        app.process_button.config.assert_called_with(state=yt.tk.NORMAL)

    def update_options(self, entry, *, metadata):
        video = yt.VideoData(
            "existing-video-id", "Existing title",
            {"title": "Existing title", "description": "Existing copy", "tags": ["Existing tag"], "categoryId": "24"},
            {"privacyStatus": "private", "embeddable": True, "selfDeclaredMadeForKids": False},
        )
        video.description_file_path = entry.description_file_path
        return {
            "videos": [video], "is_dry_run": False, "update_metadata": metadata,
            "update_schedule": False, "remove_schedule": False,
            "update_visibility": not metadata, "visibility_to_set": "unlisted",
            "description_override": "", "tags_override": "", "category_id": None,
            "public_stats_viewable": False, "allow_embedding": True, "made_for_kids": "no",
        }

    def test_update_still_sends_tags_in_snippet(self):
        yt.update_videos_on_youtube(self.service, self.update_options(self.entry(), metadata=True))
        self.assertEqual(self.service.resource.updates[0]["body"]["snippet"]["tags"], TAGS)

    def test_status_only_update_omits_snippet(self):
        yt.update_videos_on_youtube(self.service, self.update_options(self.entry(), metadata=False))
        request = self.service.resource.updates[0]
        self.assertEqual(request["part"], "status")
        self.assertNotIn("snippet", request["body"])
        self.assertEqual(request["body"]["status"]["privacyStatus"], "unlisted")


if __name__ == "__main__":
    unittest.main()
