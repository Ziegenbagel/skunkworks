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

    SoundEffect {
        id: buttonEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/button/soft-ui-button-click.ogg")
        volume: root.effectsEnabled ? root.effectsVolume * 0.72 : 0
    }
    MediaPlayer {
        id: confirmEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/chimey/Chime_Confirm.mp3")
        audioOutput: effectsOutput
    }
    MediaPlayer {
        id: cancelEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/chimey/Chime_Cancel.mp3")
        audioOutput: effectsOutput
    }
    MediaPlayer {
        id: loadEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/chimey/Chime_Load.mp3")
        audioOutput: effectsOutput
    }
    MediaPlayer {
        id: saveEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/chimey/Chime_Save.mp3")
        audioOutput: effectsOutput
    }
    MediaPlayer {
        id: discoveryEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/chimey/Chime_LevelUp.mp3")
        audioOutput: effectsOutput
    }
    SoundEffect {
        id: errorEffect
        source: Qt.resolvedUrl("../../assets/audio/sfx/alerts/Wrong Error.wav")
        volume: root.effectsEnabled ? root.effectsVolume : 0
    }

    function startMusic() {
        if (musicEnabled && musicPlayer.playbackState !== MediaPlayer.PlayingState)
            musicPlayer.play();
    }
    function stopMusic() { musicPlayer.stop(); }
    function play(eventName) {
        if (!effectsEnabled)
            return;
        const effects = {
            "press": buttonEffect,
            "navigate": buttonEffect,
            "select": buttonEffect,
            "confirm": confirmEffect,
            "cancel": cancelEffect,
            "load": loadEffect,
            "save": saveEffect,
            "discovery": discoveryEffect,
            "warning": errorEffect,
            "error": errorEffect
        };
        const effect = effects[eventName] || buttonEffect;
        effect.stop();
        effect.play();
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
