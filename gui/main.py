# gui/main.py
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QTextEdit, QCheckBox,
    QGroupBox, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

from core.generator import GeneratorConfig, generate_passphrase


class PassphraseGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔑 Passphrase Generator – fischl-ediservice")
        self.resize(920, 700)
        self.settings = QSettings("fischl-ediservice", "PassphraseGenerator")
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(18)

        # Konfiguration
        config_box = QGroupBox("Konfiguration")
        cl = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Anzahl Wörter:"))
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
        layout.addWidget(config_box)

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
        layout.addWidget(trans_box)

        # Generate
        self.btn = QPushButton("🚀 Passphrase generieren")
        self.btn.setFont(QFont("", 14, QFont.Weight.Bold))
        self.btn.clicked.connect(self.generate)
        layout.addWidget(self.btn)

        self.result = QTextEdit()
        self.result.setReadOnly(True)
        self.result.setFont(QFont("Consolas", 13))
        layout.addWidget(self.result)

        # Bottom bar
        bottom = QHBoxLayout()
        self.entropy = QLabel("Entropie: — Bit")
        self.btn_copy = QPushButton("📋 Kopieren")
        self.btn_copy.clicked.connect(self.copy)
        bottom.addWidget(self.entropy)
        bottom.addWidget(self.btn_copy)
        layout.addLayout(bottom)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def generate(self):
        try:
            config = GeneratorConfig(
                num_words=self.num_words.value(),
                separator=self.separator.currentText(),
                use_syllable_shuffle=self.chk_syllable.isChecked(),
                add_digits=self.chk_digits.isChecked(),
                # weitere Parameter nach Bedarf
            )
            pw, ent = generate_passphrase(config)
            self.result.setText(pw)
            self.entropy.setText(f"Entropie: ~{ent:.1f} Bit")
            self.copy()
            self.statusBar.showMessage("✅ Generiert & kopiert", 2500)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))

    def copy(self):
        if text := self.result.toPlainText():
            QApplication.clipboard().setText(text)
            self.statusBar.showMessage("📋 In Zwischenablage kopiert", 1500)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = PassphraseGeneratorApp()
    win.show()
    sys.exit(app.exec())
