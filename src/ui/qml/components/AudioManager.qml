pragma Singleton
import QtQuick
import QtMultimedia
import QtCore

Item {
    id: root
    visible: false
    width: 0
    height: 0

    property alias musicEnabled: preferences.musicEnabled
    property alias effectsEnabled: preferences.effectsEnabled
    property alias musicVolume: preferences.musicVolume
    property alias effectsVolume: preferences.effectsVolume
    property alias hoverEnabled: preferences.hoverEnabled
    readonly property bool musicPlaying: musicPlayer.playbackState === MediaPlayer.PlayingState

    Settings {
        id: preferences
        category: "audio"
        property bool musicEnabled: true
        property bool effectsEnabled: true
        property bool hoverEnabled: false
        property real musicVolume: 0.22
        property real effectsVolume: 0.55
    }

    AudioOutput {
        id: musicOutput
        volume: root.musicEnabled ? root.musicVolume : 0
    }
    AudioOutput {
        id: effectsOutput
        volume: root.effectsEnabled ? root.effectsVolume : 0
    }
    MediaPlayer {
        id: musicPlayer
        source: Qt.resolvedUrl("../../assets/audio/music/space-ambient-cinematic-music.mp3")
        audioOutput: musicOutput
        loops: MediaPlayer.Infinite
    }

    MediaPlayer {
        // A single player/output pair is deliberate. Multiple players sharing an
        // AudioOutput were silent on the macOS AVFoundation backend.
        id: effectPlayer
        audioOutput: effectsOutput
    }

    function startMusic() {
        if (musicEnabled && musicPlayer.playbackState !== MediaPlayer.PlayingState)
            musicPlayer.play();
    }
    function stopMusic() { musicPlayer.stop(); }
    function play(eventName) {
        if (!effectsEnabled)
            return;
        const sources = {
            "press": "../../assets/audio/sfx/button/soft-ui-button-click.ogg",
            "navigate": "../../assets/audio/sfx/button/soft-ui-button-click.ogg",
            "select": "../../assets/audio/sfx/button/soft-ui-button-click.ogg",
            "hover": "../../assets/audio/sfx/button/soft-ui-button-click.ogg",
            "confirm": "../../assets/audio/sfx/chimey/Chime_Confirm.mp3",
            "cancel": "../../assets/audio/sfx/chimey/Chime_Cancel.mp3",
            "load": "../../assets/audio/sfx/chimey/Chime_Load.mp3",
            "save": "../../assets/audio/sfx/chimey/Chime_Save.mp3",
            "discovery": "../../assets/audio/sfx/chimey/Chime_LevelUp.mp3",
            "warning": "../../assets/audio/sfx/alerts/Wrong Error.wav",
            "error": "../../assets/audio/sfx/alerts/Wrong Error.wav"
        };
        const nextSource = Qt.resolvedUrl(sources[eventName] || sources.press);
        effectPlayer.stop();
        effectPlayer.source = nextSource;
        effectPlayer.play();
    }
    function hover() {
        if (hoverEnabled)
            play("hover");
    }
    function previewMusic() {
        if (musicPlayer.playbackState === MediaPlayer.PlayingState)
            musicPlayer.pause();
        else
            musicPlayer.play();
    }

    onMusicEnabledChanged: {
        if (musicEnabled)
            startMusic();
        else
            musicPlayer.pause();
    }
    Component.onCompleted: startMusic()
}
