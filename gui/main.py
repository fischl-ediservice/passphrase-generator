import sys
import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QTextEdit, QCheckBox,
    QGroupBox, QMessageBox, QStatusBar, QTabWidget, QListWidget
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

from core.generator import GeneratorConfig, generate_passphrase


class PassphraseGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔑 Passphrase Generator – fischl-ediservice")
        self.resize(980, 720)
        self.settings = QSettings("fischl-ediservice", "PassphraseGenerator")
        self.history = []
        self._setup_ui()

    def _setup_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        # Tab 1: Generator
        gen_tab = QWidget()
        gen_layout = QVBoxLayout(gen_tab)

        # Wortliste
        wl_box = QGroupBox("Wortliste")
        wl_l = QHBoxLayout()
        self.wordlist_combo = QComboBox()
        self.wordlist_combo.addItems(["de_standard", "de_extended"])
        wl_l.addWidget(QLabel("Wortliste:"))
        wl_l.addWidget(self.wordlist_combo)
        wl_box.setLayout(wl_l)
        gen_layout.addWidget(wl_box)

        # Konfiguration
        config_box = QGroupBox("Konfiguration")
        cl = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Wörter:"))
        self.num_words = QSpinBox()
        self.num_words.setRange(4, 12)
        self.num_words.setValue(6)
        row.addWidget(self.num_words)

        row.addWidget(QLabel("Separator:"))
        self.separator = QComboBox()
        self.separator.addItems(["-", "_", ".", " ", "•", "/"])
        self.separator.setCurrentText("-")
        row.addWidget(self.separator)
        cl.addLayout(row)
        config_box.setLayout(cl)
        gen_layout.addWidget(config_box)

        # Transformationen
        trans_box = QGroupBox("Transformationen")
        tl = QVBoxLayout()
        self.chk_syllable = QCheckBox("Silben shuffeln"); self.chk_syllable.setChecked(True)
        self.chk_digits = QCheckBox("Ziffern hinzufügen"); self.chk_digits.setChecked(True)
        self.chk_case = QCheckBox("Case variieren"); self.chk_case.setChecked(True)
        self.chk_special = QCheckBox("Sonderzeichen"); self.chk_special.setChecked(True)
        for cb in (self.chk_syllable, self.chk_digits, self.chk_case, self.chk_special):
            tl.addWidget(cb)
        trans_box.setLayout(tl)
        gen_layout.addWidget(trans_box)

        # Generate
        self.btn_generate = QPushButton("🚀 Passphrase generieren")
        self.btn_generate.setFont(QFont("", 14, QFont.Weight.Bold))
        self.btn_generate.clicked.connect(self.generate)
        gen_layout.addWidget(self.btn_generate)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setFont(QFont("Consolas", 14))
        gen_layout.addWidget(self.result)

        bottom = QHBoxLayout()
        self.entropy_label = QLabel("Entropie: — Bit")
        self.btn_copy = QPushButton("📋 Kopieren")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        bottom.addWidget(self.entropy_label)
        bottom.addWidget(self.btn_copy)
        gen_layout.addLayout(bottom)

        tabs.addTab(gen_tab, "Generator")

        # Tab 2: History
        history_tab = QWidget()
        h_layout = QVBoxLayout(history_tab)
        self.history_list = QListWidget()
        h_layout.addWidget(self.history_list)
        tabs.addTab(history_tab, "Verlauf")

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def generate(self):
        try:
            config = GeneratorConfig(
                num_words=self.num_words.value(),
                separator=self.separator.currentText(),
                wordlist=self.wordlist_combo.currentText(),
                use_syllable_shuffle=self.chk_syllable.isChecked(),
                add_digits=self.chk_digits.isChecked(),
            )

            passphrase, entropy = generate_passphrase(config)

            self.result.setText(passphrase)
            self.entropy_label.setText(f"Entropie: ~{entropy:.1f} Bit")

            self.history.append(passphrase)
            self.history_list.insertItem(0, passphrase[:80] + "..." if len(passphrase) > 80 else passphrase)

            self.copy_to_clipboard()
            self.statusBar.showMessage("✅ Generiert & kopiert", 3000)

        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))

    def copy_to_clipboard(self):
        text = self.result.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar.showMessage("📋 In die Zwischenablage kopiert", 2000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PassphraseGeneratorApp()
    window.show()
    sys.exit(app.exec())
