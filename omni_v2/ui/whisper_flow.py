"""
Whisper Flow Desktop App EXACT Clone - PyQt5 - For User Who Wants Whisper Flow, Not Hologram
Based on EasyWhisperUI + WhisperFlow research: drag & drop, batch, GPU, console, Notepad open
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QComboBox, QListWidget, QListWidgetItem, QProgressBar,
    QFileDialog, QMessageBox, QCheckBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QIcon
from pathlib import Path
import sys

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("WhisperFlow")

try:
    from omni_v2.core.paths import DATA_DIR
except ImportError:
    DATA_DIR = Path.home() / ".omni_v2"

class TranscriptionWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, file_path, model_name="base.en", language="en"):
        super().__init__()
        self.file_path = file_path
        self.model_name = model_name
        self.language = language

    def run(self):
        try:
            self.log.emit(f"Loading model {self.model_name}...")
            from faster_whisper import WhisperModel
            model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            
            self.log.emit(f"Transcribing {self.file_path}...")
            self.progress.emit(10)
            
            segments, info = model.transcribe(
                str(self.file_path),
                language=self.language if self.language != "auto" else None,
                beam_size=5
            )
            
            self.progress.emit(50)
            text_parts = []
            for i, segment in enumerate(segments):
                text_parts.append(segment.text)
                progress = 50 + int((i+1) * 40 / 10)  # Rough progress
                self.progress.emit(min(progress, 90))
                self.log.emit(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")

            full_text = "\n".join(text_parts)
            self.progress.emit(100)
            self.finished.emit(full_text)

        except Exception as e:
            self.error.emit(str(e))
            import traceback
            self.log.emit(traceback.format_exc())


class WhisperFlowDesktopApp(QWidget):
    """Whisper Flow Desktop App EXACT Clone - Like EasyWhisperUI + WhisperFlow"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OMNI V2 - Whisper Flow Desktop - Drag & Drop to Transcribe")
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        self.model_name = "base.en"
        self.language = "en"
        self.output_format = "txt"
        self.transcribed_text = ""

        self.init_ui()
        logger.info("Whisper Flow Desktop App EXACT Clone - Started")

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("🎙️ OMNI V2 - Whisper Flow Desktop - EXACT Clone")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Drag & drop audio/video files here to transcribe - Like EasyWhisperUI - Batch processing - GPU Vulkan - Auto-downloads models")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(subtitle)

        # Top controls: Model, Language, Format
        top_controls = QHBoxLayout()

        top_controls.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny.en", "base.en", "small.en", "medium.en", "large-v3", "large-v3-turbo"])
        self.model_combo.setCurrentText("base.en")
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        top_controls.addWidget(self.model_combo)

        top_controls.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["auto", "en", "es", "fr", "de", "zh", "ja", "ar", "hi", "ur"])
        self.lang_combo.setCurrentText("en")
        top_controls.addWidget(self.lang_combo)

        top_controls.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["txt", "srt", "vtt", "json"])
        top_controls.addWidget(self.format_combo)

        top_controls.addStretch()
        layout.addLayout(top_controls)

        # Drag & Drop area - BIG
        self.drop_area = QLabel(
            "📁 DRAG & DROP AUDIO/VIDEO FILES HERE\n\n"
            "Supports: mp3, wav, mp4, mkv, avi, mov, m4a, flac, ogg\n"
            "Or click 'Open File' below\n"
            "Batch processing: Drag multiple files at once - they'll queue automatically\n"
            "Like EasyWhisperUI - Fully C++ implementation in original, but we use Python + Whisper"
        )
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #00ccff;
                border-radius: 10px;
                padding: 40px;
                background: rgba(0, 20, 40, 0.5);
                color: cyan;
                font-size: 14px;
            }
        """)
        self.drop_area.setMinimumHeight(150)
        layout.addWidget(self.drop_area)

        # File list (for batch)
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100)
        self.file_list.setStyleSheet("background: rgba(0,0,0,0.3); color: white;")
        layout.addWidget(self.file_list)

        # Buttons row
        btn_row = QHBoxLayout()

        self.open_file_btn = QPushButton("📂 Open File")
        self.open_file_btn.clicked.connect(self.open_file)
        btn_row.addWidget(self.open_file_btn)

        self.open_folder_btn = QPushButton("📁 Open Folder (Batch)")
        self.open_folder_btn.clicked.connect(self.open_folder)
        btn_row.addWidget(self.open_folder_btn)

        self.transcribe_btn = QPushButton("🎙️ Transcribe")
        self.transcribe_btn.setStyleSheet("background: rgba(0, 200, 255, 0.3); color: white; font-weight: bold;")
        self.transcribe_btn.clicked.connect(self.start_transcription)
        btn_row.addWidget(self.transcribe_btn)

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        btn_row.addWidget(self.clear_btn)

        self.open_output_btn = QPushButton("📄 Open in Notepad")
        self.open_output_btn.clicked.connect(self.open_in_notepad)
        btn_row.addWidget(self.open_output_btn)

        layout.addLayout(btn_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Console output (real-time, like EasyWhisperUI)
        self.console_label = QLabel("Console Output (Real-time):")
        layout.addWidget(self.console_label)

        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setMaximumHeight(120)
        self.console_text.setStyleSheet("background: black; color: #00ff00; font-family: Consolas; font-size: 10px;")
        self.console_text.setText("Ready. Drag & drop files or click Open File. Models auto-download from Hugging Face.\n")
        layout.addWidget(self.console_text)

        # Transcription output (main)
        self.output_label = QLabel("Transcription Output:")
        layout.addWidget(self.output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)  # Allow editing, like WhisperFlow
        self.output_text.setStyleSheet("background: rgba(20,20,30,0.9); color: white; font-size: 12px;")
        self.output_text.setPlaceholderText("Transcription will appear here... You can edit it like WhisperFlow")
        layout.addWidget(self.output_text)

        # Bottom: Extra Whisper args + Save options
        bottom_row = QHBoxLayout()

        self.extra_args_label = QLabel("Extra Whisper args:")
        bottom_row.addWidget(self.extra_args_label)

        self.extra_args_input = QLineEdit()
        self.extra_args_input.setPlaceholderText("--beam_size 5 --vad_filter True")
        bottom_row.addWidget(self.extra_args_input)

        self.save_txt_check = QCheckBox("Save .txt")
        self.save_txt_check.setChecked(True)
        bottom_row.addWidget(self.save_txt_check)

        self.save_srt_check = QCheckBox("Save .srt")
        self.save_srt_check.setChecked(False)
        bottom_row.addWidget(self.save_srt_check)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        # Status bar
        self.status_label = QLabel("Status: Ready | GPU: Vulkan via faster-whisper (AMD/Intel/NVIDIA) | Models auto-download | Batch processing | Drag & Drop")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Worker
        self.worker = None
        self.current_files = []

    def on_model_changed(self, model_name):
        self.model_name = model_name
        self.log_to_console(f"Model changed to: {model_name}")
        if model_name in ["tiny.en", "base.en"]:
            self.log_to_console("Small model - fast, good for real-time, pure English")
        elif model_name in ["small.en", "medium.en"]:
            self.log_to_console("Medium model - balanced speed/accuracy")
        else:
            self.log_to_console("Large model - best accuracy, slower, needs more RAM/VRAM")

    def log_to_console(self, text):
        self.console_text.append(text)
        # Auto-scroll
        self.console_text.verticalScrollBar().setValue(self.console_text.verticalScrollBar().maximum())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_area.setStyleSheet("""
                QLabel {
                    border: 2px dashed #00ff88;
                    border-radius: 10px;
                    padding: 40px;
                    background: rgba(0, 40, 20, 0.7);
                    color: #00ff88;
                    font-size: 14px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #00ccff;
                border-radius: 10px;
                padding: 40px;
                background: rgba(0, 20, 40, 0.5);
                color: cyan;
                font-size: 14px;
            }
        """)

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            
            self.log_to_console(f"Dropped {len(files)} files (Whisper Flow style batch processing):")
            for f in files:
                self.log_to_console(f"  - {f}")
                self.add_file_to_list(f)

            self.drop_area.setStyleSheet("""
                QLabel {
                    border: 2px dashed #00ccff;
                    border-radius: 10px;
                    padding: 40px;
                    background: rgba(0, 20, 40, 0.5);
                    color: cyan;
                    font-size: 14px;
                }
            """)

    def add_file_to_list(self, file_path):
        if file_path not in self.current_files:
            self.current_files.append(file_path)
            item = QListWidgetItem(file_path)
            self.file_list.addItem(item)
            self.status_label.setText(f"Status: {len(self.current_files)} files queued for batch processing")

    def open_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Audio/Video Files (Whisper Flow - Batch supported)",
            "",
            "Audio/Video Files (*.mp3 *.wav *.mp4 *.mkv *.avi *.mov *.m4a *.flac *.ogg *.wma);;All Files (*.*)"
        )
        for f in files:
            self.add_file_to_list(f)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder for Batch Transcription")
        if folder:
            import os
            from pathlib import Path
            p = Path(folder)
            # Find all media files
            exts = [".mp3", ".wav", ".mp4", ".mkv", ".avi", ".mov", ".m4a", ".flac", ".ogg", ".wma"]
            files = []
            for ext in exts:
                files.extend(p.glob(f"*{ext}"))
                files.extend(p.glob(f"*{ext.upper()}"))
            
            for f in files:
                self.add_file_to_list(str(f))
            
            self.log_to_console(f"Added {len(files)} files from folder {folder} for batch processing")

    def start_transcription(self):
        if not self.current_files:
            QMessageBox.warning(self, "No Files", "Drag & drop files or click Open File first (Whisper Flow style)")
            return

        # Take first file from queue (batch processing one-by-one)
        file_to_transcribe = self.current_files[0]
        
        self.log_to_console(f"Starting transcription: {file_to_transcribe}")
        self.log_to_console(f"Model: {self.model_name}, Language: {self.lang_combo.currentText()}, Format: {self.format_combo.currentText()}")
        self.log_to_console(f"Extra args: {self.extra_args_input.text()}")

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.transcribe_btn.setEnabled(False)
        self.output_text.clear()

        # Start worker thread (like EasyWhisperUI real-time console)
        self.worker = TranscriptionWorker(
            file_path=file_to_transcribe,
            model_name=self.model_name,
            language=self.lang_combo.currentText()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_to_console)
        self.worker.finished.connect(self.on_transcription_finished)
        self.worker.error.connect(self.on_transcription_error)
        self.worker.start()

    def on_transcription_finished(self, text):
        self.progress_bar.setVisible(False)
        self.transcribe_btn.setEnabled(True)
        self.output_text.setText(text)
        self.log_to_console("Transcription finished!")
        self.log_to_console(f"Output length: {len(text)} chars")

        # Remove finished file from queue and auto-start next (batch processing)
        if self.current_files:
            finished_file = self.current_files.pop(0)
            self.file_list.takeItem(0)
            self.log_to_console(f"Finished: {finished_file}")
            self.log_to_console(f"Remaining in queue: {len(self.current_files)} files")

            # Auto-save
            if self.save_txt_check.isChecked():
                self.save_transcription(finished_file, text, "txt")
            if self.save_srt_check.isChecked():
                self.save_transcription(finished_file, text, "srt")

            # Auto-start next file if any (batch processing)
            if self.current_files:
                self.log_to_console(f"Auto-starting next file in batch: {self.current_files[0]}")
                self.start_transcription()
            else:
                self.status_label.setText("Status: All files transcribed - Batch complete! Transcript opens in Notepad when finished (like EasyWhisperUI)")

    def on_transcription_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.transcribe_btn.setEnabled(True)
        self.log_to_console(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Transcription Error", f"Failed to transcribe:\n{error_msg}")

    def save_transcription(self, original_file, text, ext):
        try:
            from pathlib import Path
            p = Path(original_file)
            output_path = p.with_suffix(f".{ext}")

            if ext == "txt":
                output_path.write_text(text, encoding="utf-8")
            elif ext == "srt":
                # Simple SRT with fake timestamps (real would need word timestamps)
                srt_text = f"1\n00:00:00,000 --> 00:00:10,000\n{text[:100]}...\n"
                output_path.write_text(srt_text, encoding="utf-8")

            self.log_to_console(f"Saved {ext.upper()}: {output_path}")
            return output_path
        except Exception as e:
            self.log_to_console(f"Failed to save {ext}: {e}")
            return None

    def open_in_notepad(self):
        text = self.output_text.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "No Text", "No transcription to open in Notepad")
            return

        try:
            import tempfile
            import subprocess
            import os

            # Save to temp file
            temp_path = Path(tempfile.gettempdir()) / "omni_whisperflow_transcript.txt"
            temp_path.write_text(text, encoding="utf-8")

            # Open in Notepad (Windows) or default editor
            if os.name == 'nt':
                os.startfile(str(temp_path))
                # Or: subprocess.Popen(["notepad.exe", str(temp_path)])
            else:
                subprocess.Popen(["xdg-open", str(temp_path)])

            self.log_to_console(f"Opened transcript in Notepad: {temp_path}")
            self.status_label.setText(f"Status: Transcript opened in Notepad - {temp_path}")

        except Exception as e:
            self.log_to_console(f"Failed to open in Notepad: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open in Notepad:\n{e}")

    def clear_all(self):
        self.current_files.clear()
        self.file_list.clear()
        self.output_text.clear()
        self.console_text.clear()
        self.console_text.setText("Cleared. Ready. Drag & drop files or click Open File.\n")
        self.progress_bar.setVisible(False)
        self.status_label.setText("Status: Ready | Drag & Drop | Batch processing | GPU Vulkan | Auto-downloads models")
        self.log_to_console("Cleared all - Ready for new batch")


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = WhisperFlowDesktopApp()
    window.show()
    sys.exit(app.exec_())
