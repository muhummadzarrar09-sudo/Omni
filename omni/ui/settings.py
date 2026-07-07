"""Settings Dialog - OMNI configuration UI"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, QGroupBox, QLineEdit
from PyQt5.QtCore import Qt
from loguru import logger

class SettingsDialog(QDialog):
    """Settings dialog for OMNI configuration"""
    
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.config = parent_app.config
        self.setWindowTitle("OMNI Settings")
        self.setFixedSize(400, 300)
        self.setModal(True)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self) -> None:
        layout = QVBoxLayout()
        
        # Voice
        voice_group = QGroupBox("Voice")
        voice_layout = QVBoxLayout()
        
        ptt_row = QHBoxLayout()
        ptt_row.addWidget(QLabel("PTT Key:"))
        self.ptt_combo = QComboBox()
        self.ptt_combo.addItems(["caps_lock", "left_ctrl", "right_ctrl", "space"])
        ptt_row.addWidget(self.ptt_combo)
        ptt_row.addStretch()
        voice_layout.addLayout(ptt_row)
        
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny.en", "base.en", "small.en"])
        model_row.addWidget(self.model_combo)
        model_row.addStretch()
        voice_layout.addLayout(model_row)
        
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # TTS
        tts_group = QGroupBox("Audio")
        tts_layout = QVBoxLayout()
        self.tts_enabled = QCheckBox("Enable voice feedback (TTS)")
        tts_layout.addWidget(self.tts_enabled)
        
        voice_sel_row = QHBoxLayout()
        voice_sel_row.addWidget(QLabel("Voice:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["af_sarah", "af_bella", "am_michael"])
        voice_sel_row.addWidget(self.voice_combo)
        voice_sel_row.addStretch()
        tts_layout.addLayout(voice_sel_row)
        
        tts_group.setLayout(tts_layout)
        layout.addWidget(tts_group)
        
        # Browser
        browser_group = QGroupBox("Browser")
        browser_layout = QHBoxLayout()
        browser_layout.addWidget(QLabel("CDP Port:"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("9222")
        browser_layout.addWidget(self.port_input)
        browser_layout.addStretch()
        browser_group.setLayout(browser_layout)
        layout.addWidget(browser_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_settings(self) -> None:
        s = self.config.settings
        self.ptt_combo.setCurrentText(s.ptt_key)
        self.model_combo.setCurrentText(s.whisper_model)
        self.tts_enabled.setChecked(s.tts_enabled)
        self.voice_combo.setCurrentText(s.tts_voice)
        self.port_input.setText(str(s.browser_port))
    
    def save_settings(self) -> None:
        updates = {
            "ptt_key": self.ptt_combo.currentText(),
            "whisper_model": self.model_combo.currentText(),
            "tts_enabled": self.tts_enabled.isChecked(),
            "tts_voice": self.voice_combo.currentText(),
            "browser_port": int(self.port_input.text() or 9222),
        }
        self.config.update(updates)
        self.config.save()
        logger.info("Settings saved")
        self.accept()
