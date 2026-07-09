"""
OMNI Settings Dialog
====================
Comprehensive settings UI with proper categorization.

Categories:
  - Voice I/O: PTT key, microphone
  - TTS: Engine, voice, speed, test
  - STT: Whisper model, language
  - Accessibility: Status announcements, visual
  - System: Auto-start, debug mode

All changes save to ~/.omni/config.json immediately on Save.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QPushButton, QGroupBox, QLineEdit, QSlider, QTabWidget, QWidget,
    QTextEdit, QListWidget, QListWidgetItem, QProgressBar, QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from loguru import logger

from omni.tts.kokoro_tts import VOICE_CATALOG, KokoroTTS


class SettingsDialog(QDialog):
    """OMNI Settings dialog — full configuration UI."""

    def __init__(self, parent_app):
        super().__init__(None)
        self.parent_app = parent_app
        self.config = parent_app.config

        self.setWindowTitle("OMNI Settings")
        self.setMinimumSize(520, 420)
        self.setModal(True)

        self._preview_in_progress = False
        self._tts_status_cache = None

        self.init_ui()
        self.load_settings()
        self._refresh_tts_status()

    # ── UI Construction ─────────────────────────────────────────────────────

    def init_ui(self) -> None:
        """Build the settings UI with tabbed layout."""
        layout = QVBoxLayout()

        # Title bar
        title_layout = QHBoxLayout()
        title = QLabel("⚙️  OMNI Settings")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        title_layout.addWidget(title)
        title_layout.addStretch()
        version = QLabel("v1.0.0")
        version.setStyleSheet("color: gray; font-size: 11px;")
        title_layout.addWidget(version)
        layout.addLayout(title_layout)

        # Separator
        layout.addWidget(self._hrule())

        # Tabbed interface
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_voice_io_tab(), "🎤 Voice I/O")
        self.tabs.addTab(self._build_tts_tab(),      "🔊 TTS")
        self.tabs.addTab(self._build_stt_tab(),      "🎙️ STT")
        self.tabs.addTab(self._build_access_tab(),   "♿ Accessibility")
        self.tabs.addTab(self._build_system_tab(),   "⚡ System")

        layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("↺ Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("💾  Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌  Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _build_voice_io_tab(self) -> QWidget:
        """Voice I/O tab: PTT key, microphone, VAD settings."""
        tab = QWidget()
        layout = QVBoxLayout()

        # ── PTT Key ───────────────────────────────────────────────────────
        ptt_group = QGroupBox("Push-to-Talk")
        ptt_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Toggle Key:"))
        self._ptt_combo = QComboBox()
        self._ptt_combo.addItems(["v", "b", "space", "left_ctrl", "right_ctrl", "caps_lock"])
        row1.addWidget(self._ptt_combo)
        row1.addStretch()
        ptt_layout.addLayout(row1)

        hint = QLabel("Press this key to toggle listening ON/OFF. Hold not needed.")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        ptt_layout.addWidget(hint)
        ptt_group.setLayout(ptt_layout)
        layout.addWidget(ptt_group)

        # ── Audio Devices ─────────────────────────────────────────────────
        audio_group = QGroupBox("Audio Devices")
        audio_layout = QVBoxLayout()

        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Microphone:"))
        self._mic_combo = QComboBox()
        self._mic_combo.addItems(self._detect_microphones())
        mic_row.addWidget(self._mic_combo)
        mic_row.addStretch()
        audio_layout.addLayout(mic_row)

        refresh_btn = QPushButton("🔄 Refresh Devices")
        refresh_btn.clicked.connect(self._refresh_audio_devices)
        audio_layout.addWidget(refresh_btn)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # ── VAD Settings ─────────────────────────────────────────────────
        vad_group = QGroupBox("Speech Detection (VAD)")
        vad_layout = QVBoxLayout()

        # Threshold slider
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("Sensitivity:"))
        self._vad_slider = QSlider(Qt.Horizontal)
        self._vad_slider.setMinimum(1)
        self._vad_slider.setMaximum(100)
        self._vad_slider.setValue(80)
        self._vad_slider.setTickPosition(QSlider.TicksBelow)
        self._vad_slider.setTickInterval(20)
        thresh_row.addWidget(self._vad_slider)
        thresh_row.addWidget(QLabel("Low"))
        vad_layout.addLayout(thresh_row)

        vad_hint = QLabel("Higher = more sensitive to quiet speech. Adjust for your mic volume.")
        vad_hint.setStyleSheet("color: gray; font-size: 11px;")
        vad_layout.addWidget(vad_hint)
        vad_group.setLayout(vad_layout)
        layout.addWidget(vad_group)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_tts_tab(self) -> QWidget:
        """TTS tab: engine status, voice selection, speed, preview."""
        tab = QWidget()
        layout = QVBoxLayout()

        # ── TTS Engine Status ─────────────────────────────────────────────
        status_group = QGroupBox("TTS Engine Status")
        status_layout = QVBoxLayout()

        self._tts_status_label = QLabel("Loading...")
        self._tts_status_label.setWordWrap(True)
        self._tts_status_label.setStyleSheet("font-family: monospace; padding: 4px;")
        status_layout.addWidget(self._tts_status_label)

        refresh_status_btn = QPushButton("🔄 Refresh Status")
        refresh_status_btn.clicked.connect(self._refresh_tts_status)
        status_layout.addWidget(refresh_status_btn)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # ── Voice Selection ───────────────────────────────────────────────
        voice_group = QGroupBox("Voice Selection")
        voice_layout = QVBoxLayout()

        # Voice category filter
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category:"))
        self._voice_cat_combo = QComboBox()
        self._voice_cat_combo.addItems([
            "All Voices", "🇺🇸 American Female", "🇺🇸 American Male",
            "🇬🇧 British Female", "🇬🇧 British Male", "🌏 Half Accent", "🎨 Special",
        ])
        self._voice_cat_combo.currentTextChanged.connect(self._on_category_changed)
        cat_row.addWidget(self._voice_cat_combo)
        cat_row.addStretch()
        voice_layout.addLayout(cat_row)

        # Voice list
        self._voice_list = QListWidget()
        self._voice_list.setMaximumHeight(140)
        self._populate_voice_list("All Voices")
        self._voice_list.itemDoubleClicked.connect(self._preview_selected_voice)
        voice_layout.addWidget(self._voice_list)

        # Preview button row
        preview_row = QHBoxLayout()
        preview_btn = QPushButton("▶  Preview Voice")
        preview_btn.clicked.connect(self._preview_selected_voice)
        preview_row.addWidget(preview_btn)

        # Stop preview button
        stop_btn = QPushButton("⏹ Stop")
        stop_btn.clicked.connect(self._stop_preview)
        preview_row.addWidget(stop_btn)
        preview_row.addStretch()

        voice_layout.addLayout(preview_row)

        hint = QLabel("Double-click a voice to preview. Uses current speed setting.")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        voice_layout.addWidget(hint)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)

        # ── Speed Control ─────────────────────────────────────────────────
        speed_group = QGroupBox("Speech Speed")
        speed_layout = QVBoxLayout()

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setMinimum(50)   # 0.5x = 50
        self._speed_slider.setMaximum(200)  # 2.0x = 200
        self._speed_slider.setValue(100)    # 1.0x
        self._speed_slider.setTickPosition(QSlider.TicksBelow)
        self._speed_slider.setTickInterval(25)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self._speed_slider)
        self._speed_value_label = QLabel("1.0x")
        speed_row.addWidget(self._speed_value_label)
        speed_layout.addLayout(speed_row)

        speed_hint = QLabel("0.5x = slow & clear (accessibility) | 1.0x = normal | 2.0x = fast")
        speed_hint.setStyleSheet("color: gray; font-size: 11px;")
        speed_layout.addWidget(speed_hint)
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)

        # ── TTS Enable/Disable ─────────────────────────────────────────────
        enable_row = QHBoxLayout()
        self._tts_enabled_check = QCheckBox("Enable voice feedback (TTS)")
        enable_row.addWidget(self._tts_enabled_check)
        enable_row.addStretch()
        layout.addLayout(enable_row)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_stt_tab(self) -> QWidget:
        """STT tab: Whisper model, language, device settings."""
        tab = QWidget()
        layout = QVBoxLayout()

        # ── Whisper Model ─────────────────────────────────────────────────
        model_group = QGroupBox("Whisper Model")
        model_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["tiny.en", "base.en", "small.en"])
        row1.addWidget(self._model_combo)
        row1.addStretch()
        model_layout.addLayout(row1)

        model_hint = QLabel(
            "tiny.en = fast, lower accuracy | base.en = balanced | "
            "small.en = slower, higher accuracy"
        )
        model_hint.setStyleSheet("color: gray; font-size: 11px;")
        model_hint.setWordWrap(True)
        model_layout.addWidget(model_hint)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # ── Language ──────────────────────────────────────────────────────
        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout()
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language:"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["auto", "en", "es", "fr", "de", "zh", "ja", "ar", "hi"])
        lang_row.addWidget(self._lang_combo)
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        lang_hint = QLabel("'auto' auto-detects language from your speech.")
        lang_hint.setStyleSheet("color: gray; font-size: 11px;")
        lang_layout.addWidget(lang_hint)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # ── Device ────────────────────────────────────────────────────────
        device_group = QGroupBox("Compute Device")
        device_layout = QVBoxLayout()
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("Device:"))
        self._device_combo = QComboBox()
        self._device_combo.addItems(["cuda (GPU)", "cpu (no GPU)"])
        device_row.addWidget(self._device_combo)
        device_row.addStretch()
        device_layout.addLayout(device_row)
        device_hint = QLabel(
            "CUDA = GPU (faster) | CPU = no GPU needed (slower but works on any PC)"
        )
        device_hint.setStyleSheet("color: gray; font-size: 11px;")
        device_layout.addWidget(device_hint)
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_access_tab(self) -> QWidget:
        """Accessibility tab: screen reader, announcements, visual settings."""
        tab = QWidget()
        layout = QVBoxLayout()

        # ── Status Announcements ─────────────────────────────────────────
        announce_group = QGroupBox("Status Announcements")
        announce_layout = QVBoxLayout()

        self._announce_recording = QCheckBox("Announce when recording starts")
        announce_layout.addWidget(self._announce_recording)

        self._announce_processing = QCheckBox("Announce when processing command")
        announce_layout.addWidget(self._announce_processing)

        self._announce_error = QCheckBox("Speak error messages")
        announce_layout.addWidget(self._announce_error)

        announce_group.setLayout(announce_layout)
        layout.addWidget(announce_group)

        # ── Visual Settings ───────────────────────────────────────────────
        visual_group = QGroupBox("Visual")
        visual_layout = QVBoxLayout()

        self._high_contrast = QCheckBox("High contrast mode")
        visual_layout.addWidget(self._high_contrast)

        self._large_text = QCheckBox("Large text in settings")
        visual_layout.addWidget(self._large_text)

        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)

        # ── Keyboard Navigation ───────────────────────────────────────────
        kb_group = QGroupBox("Keyboard")
        kb_layout = QVBoxLayout()
        kb_hint = QLabel("Full keyboard navigation of OMNI UI is always enabled.")
        kb_hint.setStyleSheet("color: gray; font-size: 11px;")
        kb_layout.addWidget(kb_hint)
        kb_group.setLayout(kb_layout)
        layout.addWidget(kb_group)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_system_tab(self) -> QWidget:
        """System tab: startup, debug, logging."""
        tab = QWidget()
        layout = QVBoxLayout()

        # ── Startup ───────────────────────────────────────────────────────
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout()

        self._start_with_windows = QCheckBox("Start OMNI when Windows starts")
        startup_layout.addWidget(self._start_with_windows)

        self._minimize_to_tray = QCheckBox("Minimize to system tray on close")
        startup_layout.addWidget(self._minimize_to_tray)

        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)

        # ── Debug ─────────────────────────────────────────────────────────
        debug_group = QGroupBox("Debugging")
        debug_layout = QVBoxLayout()

        self._debug_mode = QCheckBox("Debug mode (verbose logging)")
        debug_layout.addWidget(self._debug_mode)

        debug_hint = QLabel("Logs saved to: C:\\Users\\<you>\\.omni\\omni.log")
        debug_hint.setStyleSheet("color: gray; font-size: 11px;")
        debug_layout.addWidget(debug_hint)

        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)

        # ── Browser ───────────────────────────────────────────────────────
        browser_group = QGroupBox("Browser Control")
        browser_layout = QHBoxLayout()
        browser_layout.addWidget(QLabel("CDP Port:"))
        self._port_input = QLineEdit()
        self._port_input.setPlaceholderText("9222")
        browser_layout.addWidget(self._port_input)
        browser_layout.addStretch()
        browser_group.setLayout(browser_layout)
        layout.addWidget(browser_group)

        # ── About ─────────────────────────────────────────────────────────
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()
        about_layout.addWidget(QLabel("OMNI v1.0.0 — Agentic AI Innovation Challenge 2026"))
        about_layout.addWidget(QLabel("Local-first, privacy-safe, GPU-efficient AI agent"))
        about_layout.addWidget(QLabel("Hardware: GTX 1050 Ti | i7 7700HQ | 8GB RAM"))
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()
        tab.setLayout(layout)
        return tab

    # ── TTS Helpers ─────────────────────────────────────────────────────────

    def _refresh_tts_status(self) -> None:
        """Query the TTS engine and display its status."""
        try:
            tts = KokoroTTS.get_instance()
            if tts is None:
                from omni.tts.kokoro_tts import KokoroTTS as KT
                tts = KT()

            status = tts.get_status()
            lines = [
                f"Engine:     {status['engine_type']}",
                f"Voice:      {status['voice']} ({status['speed']}x speed)",
                f"Model dir:  {status['model_dir']}",
                f"Model file: {'✓ present' if status['model_present'] else '✗ missing'}",
                f"Voices file:{'✓ present' if status['voices_present'] else '✗ missing'}",
                f"Speaking:   {status['is_speaking']}",
                f"Voices:     {status['available_voices_count']} available",
            ]

            # Color-code engine type
            engine = status['engine_type']
            if engine == 'kokoro-onnx':
                engine_colored = f"🟢 {engine}"
            elif engine == 'pyttsx3':
                engine_colored = f"🟡 {engine}"
            else:
                engine_colored = f"🔴 {engine}"

            lines[0] = f"Engine:     {engine_colored}"
            self._tts_status_label.setText("\n".join(lines))

        except Exception as e:
            self._tts_status_label.setText(f"Error loading TTS status: {e}")
            logger.warning(f"TTS status refresh failed: {e}")

    def _populate_voice_list(self, category: str) -> None:
        """Populate the voice list with voices from the given category."""
        self._voice_list.clear()

        for voice_id, (cat, desc) in VOICE_CATALOG.items():
            if category == "All Voices" or category.startswith(cat[:2]):
                item = QListWidgetItem(f"{voice_id}  —  {desc}")
                item.setData(Qt.UserRole, voice_id)
                self._voice_list.addItem(item)

    def _on_category_changed(self, category: str) -> None:
        self._populate_voice_list(category)

    def _on_speed_changed(self, value: int) -> None:
        """Update speed label when slider moves."""
        speed = value / 100.0
        self._speed_value_label.setText(f"{speed:.2f}x")

    def _preview_selected_voice(self) -> None:
        """Preview the currently selected voice."""
        if self._preview_in_progress:
            self._stop_preview()
            return

        current_item = self._voice_list.currentItem()
        if current_item is None:
            return

        voice_id = current_item.data(Qt.UserRole)
        speed = self._speed_slider.value() / 100.0

        try:
            tts = KokoroTTS.get_instance()
            if tts is None:
                from omni.tts.kokoro_tts import KokoroTTS as KT
                tts = KT()

            # Temporarily change voice and speed for preview
            tts._voice = voice_id
            tts._speed = speed

            self._preview_in_progress = True
            self._tts_status_label.setText(f"🔊 Previewing: {voice_id} @ {speed}x ... (click Stop to interrupt)")

            tts.speak(
                f"Hello! I'm {voice_id}. This is how I sound.",
                callback=self._on_preview_complete,
            )
        except Exception as e:
            logger.error(f"Voice preview failed: {e}")
            self._tts_status_label.setText(f"Preview failed: {e}")
            self._preview_in_progress = False

    def _on_preview_complete(self) -> None:
        """Called when the preview speech finishes."""
        self._preview_in_progress = False
        self._refresh_tts_status()

    def _stop_preview(self) -> None:
        """Stop any ongoing preview."""
        try:
            tts = KokoroTTS.get_instance()
            if tts:
                tts.stop()
        except Exception:
            pass
        self._preview_in_progress = False
        self._refresh_tts_status()

    # ── Audio Device Helpers ────────────────────────────────────────────────

    def _detect_microphones(self) -> list[str]:
        """Detect available microphone devices."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            mics = []
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    name = info['name']
                    # Truncate very long names
                    if len(name) > 50:
                        name = name[:47] + "..."
                    mics.append(name)
            pa.terminate()
            if not mics:
                return ["Default Microphone"]
            return mics
        except Exception:
            return ["Default Microphone"]

    def _refresh_audio_devices(self) -> None:
        """Re-scan and update the microphone list."""
        mics = self._detect_microphones()
        current = self._mic_combo.currentText()
        self._mic_combo.clear()
        self._mic_combo.addItems(mics)
        if current in mics:
            self._mic_combo.setCurrentText(current)

    # ── Settings Load/Save ─────────────────────────────────────────────────

    def load_settings(self) -> None:
        """Load current settings from ConfigManager into UI controls."""
        s = self.config.settings

        # Voice I/O
        if hasattr(self, '_ptt_combo'):
            self._ptt_combo.setCurrentText(s.ptt_key)

        # TTS
        if hasattr(self, '_tts_enabled_check'):
            self._tts_enabled_check.setChecked(s.tts_enabled)

        if hasattr(self, '_voice_list'):
            # Select the current voice in the list
            for i in range(self._voice_list.count()):
                item = self._voice_list.item(i)
                if item.data(Qt.UserRole) == s.tts_voice:
                    self._voice_list.setCurrentItem(item)
                    break

        if hasattr(self, '_speed_slider'):
            self._speed_slider.setValue(int(s.tts_speed * 100))

        # STT
        if hasattr(self, '_model_combo'):
            self._model_combo.setCurrentText(s.whisper_model)

        # System
        if hasattr(self, '_debug_mode'):
            self._debug_mode.setChecked(s.debug_mode)

        if hasattr(self, '_port_input'):
            self._port_input.setText(str(s.browser_port))

    def _save_and_close(self) -> None:
        """Save all settings and close the dialog."""
        try:
            updates = {}

            # Voice I/O
            if hasattr(self, '_ptt_combo'):
                updates["ptt_key"] = self._ptt_combo.currentText()

            # TTS
            if hasattr(self, '_tts_enabled_check'):
                updates["tts_enabled"] = self._tts_enabled_check.isChecked()

            if hasattr(self, '_voice_list'):
                current = self._voice_list.currentItem()
                if current:
                    updates["tts_voice"] = current.data(Qt.UserRole)

            if hasattr(self, '_speed_slider'):
                updates["tts_speed"] = self._speed_slider.value() / 100.0

            # STT
            if hasattr(self, '_model_combo'):
                updates["whisper_model"] = self._model_combo.currentText()

            # System
            if hasattr(self, '_debug_mode'):
                updates["debug_mode"] = self._debug_mode.isChecked()

            if hasattr(self, '_port_input'):
                try:
                    updates["browser_port"] = int(self._port_input.text() or "9222")
                except ValueError:
                    updates["browser_port"] = 9222

            self.config.update(updates)
            saved = self.config.save()

            if saved:
                logger.info(f"Settings saved: {list(updates.keys())}")

                # Apply PTT key change immediately
                if "ptt_key" in updates and hasattr(self.parent_app, 'ptt'):
                    self.parent_app.ptt.key_name = updates["ptt_key"]
                    self.parent_app.ptt.vk_code = self.parent_app.ptt.VK_MAP.get(
                        updates["ptt_key"], 0x56
                    )
                    logger.info(f"PTT key updated to: {updates['ptt_key']}")

                # Apply TTS voice/speed change immediately
                if hasattr(self.parent_app, 'tts') and self.parent_app.tts:
                    if "tts_voice" in updates:
                        self.parent_app.tts.voice = updates["tts_voice"]
                    if "tts_speed" in updates:
                        self.parent_app.tts.speed = updates["tts_speed"]

                self.accept()
            else:
                logger.error("Failed to save settings")

        except Exception as e:
            logger.error(f"Settings save error: {e}")

    def _reset_defaults(self) -> None:
        """Reset all settings to defaults."""
        from omni.core.config_manager import OMNISettings
        defaults = OMNISettings()
        self.config.settings = defaults
        self.config.save()
        self.load_settings()
        logger.info("Settings reset to defaults")

    # ── Utility ─────────────────────────────────────────────────────────────

    @staticmethod
    def _hrule() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        return line