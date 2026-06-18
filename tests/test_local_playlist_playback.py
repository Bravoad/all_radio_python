from main import MainWindow


def test_local_m3u_is_loaded_as_full_playback_queue(tmp_path) -> None:
    first_track = tmp_path / "first.mp3"
    second_track = tmp_path / "second.mp3"
    first_track.write_bytes(b"")
    second_track.write_bytes(b"")

    playlist = tmp_path / "my-radio.m3u"
    playlist.write_text(
        "\n".join(
            [
                "#EXTM3U",
                "#EXTINF:-1,First",
                first_track.resolve().as_uri(),
                "#EXTINF:-1,Second",
                second_track.resolve().as_uri(),
                "",
            ]
        ),
        encoding="utf-8-sig",
    )

    assert MainWindow._playlist_items(playlist.resolve().as_uri()) == [
        str(first_track.resolve()),
        str(second_track.resolve()),
    ]
