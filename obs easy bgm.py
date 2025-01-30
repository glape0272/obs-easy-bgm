import obspython as obs
import os
import random

# 設定用変数
audio_folder = ""
media_source_name = "BGM"
playlist = []  # シャッフルリスト
shuffle_enabled = True  # シャッフルの有無
default_volume = -30.0  # 初期音量（デシベル）
volume_set = False

def script_description():
    return "BGMをシャッフル再生するOBSスクリプト。BGMソースを作成するには、[BGMソースを作成] ボタンを押してください。"

def script_defaults(settings):
    obs.obs_data_set_default_string(settings, "audio_folder", "")
    obs.obs_data_set_default_bool(settings, "shuffle_enabled", True)
    obs.obs_data_set_default_double(settings, "default_volume", -30.0)

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(props, "audio_folder", "BGMフォルダ", obs.OBS_PATH_DIRECTORY, "", "")
    obs.obs_properties_add_bool(props, "shuffle_enabled", "シャッフルを有効にする")
    obs.obs_properties_add_float_slider(props, "default_volume", "デフォルト音量 (dB)", -60.0, 0.0, 0.1)
    obs.obs_properties_add_button(props, "create_bgm_source_button", "BGMソースを作成", create_bgm_source_callback)
    return props

def create_bgm_source_callback(props, prop):
    create_bgm_source()

def script_update(settings):
    global audio_folder, shuffle_enabled, default_volume, volume_set
    audio_folder = obs.obs_data_get_string(settings, "audio_folder")
    shuffle_enabled = obs.obs_data_get_bool(settings, "shuffle_enabled")
    default_volume = obs.obs_data_get_double(settings, "default_volume")
    volume_set = False  # 設定更新時に再適用可能にする
    create_bgm_source()
    generate_playlist()
    play_next_audio()
    obs.timer_add(check_media_state, 1000)

def create_bgm_source():
    global volume_set
    scene_source = obs.obs_frontend_get_current_scene()
    if scene_source is None:
        print("[OBS BGM] 現在のシーンを取得できませんでした。")
        return

    scene = obs.obs_scene_from_source(scene_source)
    if scene is None:
        print("[OBS BGM] シーンの変換に失敗しました。")
        return

    # シーン内のBGMソースをチェック
    scene_items = obs.obs_scene_enum_items(scene)
    for item in scene_items:
        source = obs.obs_sceneitem_get_source(item)
        if source and obs.obs_source_get_name(source) == media_source_name:
            print(f"[OBS BGM] メディアソース '{media_source_name}' はすでに存在します。")
            if not volume_set:
                set_audio_volume(source, default_volume)
                volume_set = True
            return

    # 既存のBGMソースを復元（削除された場合の対策）
    bgm_source = obs.obs_get_source_by_name(media_source_name)
    if bgm_source:
        obs.obs_scene_add(scene, bgm_source)
        print(f"[OBS BGM] メディアソース '{media_source_name}' を復元しました。")
        if not volume_set:
            set_audio_volume(bgm_source, default_volume)
            volume_set = True
        return

    # BGM ソースを新規作成
    settings = obs.obs_data_create()
    obs.obs_data_set_string(settings, "local_file", "")
    source = obs.obs_source_create("ffmpeg_source", media_source_name, settings, None)
    
    if source:
        obs.obs_scene_add(scene, source)
        print(f"[OBS BGM] メディアソース '{media_source_name}' を追加しました。")
        set_audio_volume(source, default_volume)
        volume_set = True
    
    obs.obs_data_release(settings)

def set_audio_volume(source, volume_db):
    linear_volume = 10 ** (volume_db / 20)  # dB をリニア音量に変換
    obs.obs_source_set_volume(source, linear_volume)  # ミキサー音量を設定
    print(f"[OBS BGM] 音量を {volume_db} dB に設定しました。")

def generate_playlist():
    global playlist
    if not audio_folder or not os.path.isdir(audio_folder):
        return
    
    files = [f for f in os.listdir(audio_folder) if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac"))]
    if not files:
        return
    
    if shuffle_enabled:
        random.shuffle(files)
    
    playlist = files

def play_next_audio():
    global playlist
    if not playlist:
        generate_playlist()
    
    if playlist:
        file_path = os.path.join(audio_folder, playlist.pop(0))
        source = obs.obs_get_source_by_name(media_source_name)
        if source:
            settings = obs.obs_source_get_settings(source)
            obs.obs_data_set_string(settings, "local_file", file_path)
            obs.obs_source_update(source, settings)
            obs.obs_data_release(settings)

def check_media_state():
    source = obs.obs_get_source_by_name(media_source_name)
    if source:
        if obs.obs_source_media_get_state(source) == obs.OBS_MEDIA_STATE_ENDED:
            play_next_audio()

def script_load(settings):
    create_bgm_source()
    obs.timer_add(check_media_state, 1000)
