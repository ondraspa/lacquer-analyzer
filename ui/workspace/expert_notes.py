"""Widget de notas de conocimiento experto y conversación — todo editable desde la GUI."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QTreeWidget, QTreeWidgetItem, QSplitter, QGroupBox,
    QMessageBox, QComboBox, QLineEdit, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


CUSTOM_KNOWLEDGE_PATH = str(Path(__file__).parent.parent / "data" / "custom_knowledge.json")


def _load_custom_knowledge() -> dict:
    p = Path(CUSTOM_KNOWLEDGE_PATH)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def _save_custom_knowledge(data: dict):
    p = Path(CUSTOM_KNOWLEDGE_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


BUILTIN_KNOWLEDGE = {
    "curtain_coating": {
        "title": "Directrices de la Cortina Burkle",
        "content": "## Cortina Burkle - Aplicación de Laca\n\nParámetros Clave:\n- Rango de viscosidad: 300-1500 mPa·s (óptimo 500-800)\n- Altura de cortina: 100-300 mm\n- Velocidad de transportador: 80-200 m/min\n- Espesor de película húmeda: 50-200 μm\n- Evaporación de solvente: 5-15% entre cortina y sustrato\n\nFactores Críticos de Formulación:\n1. La tensión superficial debe ser 25-35 mN/m para una cortina estable\n2. Solventes cola de evaporación lenta (Butyl Cellosolve, MAK) ayudan a prevenir la formación de piel\n3. Aditivos niveladores (BYK-307) esenciales para una película uniforme\n4. Antiespumante crítico para prevenir burbujas en la cortina\n\nConsideraciones de Recubrimiento:\n- Solvente residual < 0.1% antes del recubrimiento\n- Promotor de adhesión (Silano A-187) requerido para adhesión metálica\n- El programa de curado afecta el resultado del recubrimiento"
    },
    "silvering_compat": {
        "title": "Compatibilidad del Proceso de Plateado",
        "content": "## Compatibilidad del Plateado con Plata\n\nEl plateado con plata requiere superficies limpias y libres de contaminantes:\n\nContaminantes Críticos a Evitar:\n1. MEK y Acetona - atacan la plata y causan picaduras\n2. Siliconas - causan fallo severo de adhesión\n3. Compuestos de azufre - causan deslustre\n4. Cloruros - riesgo de corrosión\n\nEnfoque de Formulación Recomendado:\n- Usar Acetato de Butilo como solvente principal\n- Mantener contenido de amina < 0.1%\n- Añadir inhibidor de corrosión (benzotriazol 0.1-0.5%)\n- Curado completo a 80 °C durante mínimo 2 horas\n\nSecuencia del Proceso:\nLaca -> (Curado) -> Plateado con Plata -> (Proteger) -> Laca"
    },
    "nickel_sulfamate": {
        "title": "Compatibilidad del Sulfamato de Níquel",
        "content": "## Compatibilidad del Recubrimiento con Sulfamato de Níquel\n\nLos baños de sulfamato de níquel son sensibles a la contaminación orgánica:\n\nPrincipales Preocupaciones:\n1. Siliconas causan picaduras y tensión\n2. Fosfonatos/fosfatos > 0.2% contaminan el baño\n3. Agentes niveladores excesivos (> 0.5%) causan rugosidad\n4. Ácidos orgánicos atacan el depósito de níquel\n\nMejores Prácticas:\n- Usar aditivos mínimos en la laca\n- Activación ácida previa al recubrimiento (H2SO4 10%, 30 seg)\n- Filtrar con carbón el baño de níquel semanalmente\n- Probar adhesión según ASTM B571\n\nPropiedades Óptimas de la Laca:\n- Sistemas reticulados preferidos (melamina, isocianato)\n- Retención máxima de solvente 0.05%\n- Temperatura de transición vítrea > 60 °C"
    },
    "ingredient_swaps": {
        "title": "Sustituciones Comunes de Ingredientes",
        "content": "## Sustituciones de Ingredientes Compatibles\n\nSi un ingrediente falla la compatibilidad de recubrimiento, pruebe:\n\nSolventes:\n- MEK (incompatible con plata) -> Acetato de Butilo o MAK\n- Acetona (incompatible) -> Acetato de Etilo\n\nResinas:\n- CAB-381-0.5 (baja compatibilidad con Ni) -> NC RS 1/2 seg\n- Acrílico estándar -> Acrílico modificado con grupos de adhesión\n\nAditivos:\n- Antiespumante de silicona -> Sin silicona (BYK-024)\n- Humectante estándar -> Humectante sin fosfato\n\nRegla General:\nAnte la duda, pruebe primero un lote pequeño en chatarra con ambos procesos de recubrimiento."
    }
}


def _get_merged_knowledge() -> dict:
    merged = dict(BUILTIN_KNOWLEDGE)
    custom = _load_custom_knowledge()
    merged.update(custom)
    return merged


class ExpertNotesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.custom_notes_path = Path(__file__).parent.parent / "data" / "custom_notes.json"
        self._init_ui()
        self._load_custom_notes()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        ref_widget = QWidget()
        ref_layout = QVBoxLayout(ref_widget)

        self.topic_selector = QComboBox()
        self._rebuild_topic_selector()
        self.topic_selector.currentIndexChanged.connect(self._show_topic)
        self.topic_selector.setToolTip("Selecciona un tema de referencia de experto para ver su contenido")
        ref_layout.addWidget(QLabel("Temas de Experto:"))
        ref_layout.addWidget(self.topic_selector)

        self.ref_content = QTextEdit()
        self.ref_content.setReadOnly(False)
        self.ref_content.setToolTip("Contenido del tema de referencia seleccionado. Puedes editarlo y guardarlo")
        ref_layout.addWidget(self.ref_content)

        edit_row = QHBoxLayout()
        self.save_topic_btn = QPushButton("Guardar Tema")
        self.save_topic_btn.clicked.connect(self._save_topic)
        self.save_topic_btn.setToolTip("Guarda los cambios realizados en el contenido del tema")
        self.add_topic_btn = QPushButton("Añadir Tema")
        self.add_topic_btn.clicked.connect(self._add_topic)
        self.add_topic_btn.setToolTip("Añade un nuevo tema de referencia")
        self.delete_topic_btn = QPushButton("Eliminar Tema")
        self.delete_topic_btn.setStyleSheet("color: red;")
        self.delete_topic_btn.clicked.connect(self._delete_topic)
        self.delete_topic_btn.setToolTip("Elimina el tema de referencia seleccionado")
        edit_row.addWidget(self.save_topic_btn)
        edit_row.addWidget(self.add_topic_btn)
        edit_row.addWidget(self.delete_topic_btn)
        edit_row.addStretch()
        ref_layout.addLayout(edit_row)

        tabs.addTab(ref_widget, "Referencia")

        custom_widget = QWidget()
        custom_layout = QVBoxLayout(custom_widget)

        self.notes_title_input = QLineEdit()
        self.notes_title_input.setPlaceholderText("Título de la nota...")
        self.notes_title_input.setToolTip("Título de la nota personal o conversación")
        custom_layout.addWidget(self.notes_title_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText(
            "Escriba sus notas de experto aquí...\n"
            "Ejemplo: 'Encontramos que Butyl Cellosolve al 5% mejora la estabilidad de la cortina'\n"
            "Formato: Use - para listas, ** para negrita"
        )
        self.notes_input.setToolTip("Contenido de la nota personal")
        custom_layout.addWidget(self.notes_input)

        note_btn_row = QHBoxLayout()
        save_note = QPushButton("Guardar Nota")
        save_note.clicked.connect(self._save_note)
        save_note.setToolTip("Guarda la nota personal")
        toggle_conversation = QPushButton("Alternar Modo Conversación")
        toggle_conversation.clicked.connect(self._toggle_conversation)
        toggle_conversation.setToolTip("Alterna entre vista de notas y vista de conversación con el LLM")
        note_btn_row.addWidget(save_note)
        note_btn_row.addWidget(toggle_conversation)
        custom_layout.addLayout(note_btn_row)

        self.conversation_log = QTextEdit()
        self.conversation_log.setReadOnly(True)
        self.conversation_log.setPlaceholderText(
            "Registro de conversación - aquí aparecerán las discusiones sobre cambios de formulación"
        )
        self.conversation_log.setToolTip("Historial de la conversación con el LLM sobre este tema")
        custom_layout.addWidget(self.conversation_log)

        tabs.addTab(custom_widget, "Notas Personalizadas / Conversación")

        layout.addWidget(tabs)
        self._show_topic(0)

    def _rebuild_topic_selector(self):
        self.topic_selector.clear()
        knowledge = _get_merged_knowledge()
        for key, info in knowledge.items():
            self.topic_selector.addItem(info.get("title", key), key)

    def _show_topic(self, index):
        key = self.topic_selector.currentData()
        if not key:
            return
        knowledge = _get_merged_knowledge()
        info = knowledge.get(key)
        if info:
            self.ref_content.setPlainText(info.get("content", ""))

    def _save_topic(self):
        key = self.topic_selector.currentData()
        if not key:
            return
        content = self.ref_content.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Guardar Tema", "El contenido no puede estar vacío")
            return
        custom = _load_custom_knowledge()
        custom[key] = {
            "title": self.topic_selector.currentText(),
            "content": content,
        }
        _save_custom_knowledge(custom)
        self._rebuild_topic_selector()
        QMessageBox.information(self, "Guardado", f"Tema '{key}' guardado en custom_knowledge.json")

    def _add_topic(self):
        from PySide6.QtWidgets import QInputDialog
        key, ok = QInputDialog.getText(self, "Añadir Tema", "Clave del tema (ej. mi_nuevo_tema):")
        if not ok or not key.strip():
            return
        title, ok2 = QInputDialog.getText(self, "Añadir Tema", "Título mostrado:")
        if not ok2 or not title.strip():
            return
        custom = _load_custom_knowledge()
        custom[key.strip()] = {"title": title.strip(), "content": ""}
        _save_custom_knowledge(custom)
        self._rebuild_topic_selector()
        idx = self.topic_selector.findData(key.strip())
        if idx >= 0:
            self.topic_selector.setCurrentIndex(idx)

    def _delete_topic(self):
        key = self.topic_selector.currentData()
        if not key:
            return
        if key in BUILTIN_KNOWLEDGE:
            QMessageBox.warning(self, "Eliminar Tema", "No se pueden eliminar temas incorporados")
            return
        reply = QMessageBox.question(self, "Eliminar", f"¿Eliminar tema '{key}'?",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            custom = _load_custom_knowledge()
            custom.pop(key, None)
            _save_custom_knowledge(custom)
            self._rebuild_topic_selector()

    def _toggle_conversation(self):
        self.conversation_log.setVisible(
            not self.conversation_log.isVisible()
        )

    def _save_note(self):
        title = self.notes_title_input.text().strip()
        content = self.notes_input.toPlainText().strip()
        if not title or not content:
            QMessageBox.warning(self, "Guardar Nota", "Se requieren título y contenido")
            return

        self.custom_notes_path.parent.mkdir(parents=True, exist_ok=True)

        notes = {}
        if self.custom_notes_path.exists():
            with open(self.custom_notes_path) as f:
                notes = json.load(f)

        timestamp = datetime.now().isoformat()
        notes[timestamp] = {
            "title": title,
            "content": content
        }

        with open(self.custom_notes_path, "w") as f:
            json.dump(notes, f, indent=2)

        conversation_keywords = ["think", "try", "maybe", "problem", "fix", "change", "observe"]
        if any(kw in content.lower() for kw in conversation_keywords):
            self.conversation_log.append(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {title}: {content[:200]}..."
            )

        self.notes_input.clear()
        self.notes_title_input.clear()
        QMessageBox.information(self, "Guardado", f"Nota '{title}' guardada")

    def _load_custom_notes(self):
        if self.custom_notes_path.exists():
            with open(self.custom_notes_path) as f:
                notes = json.load(f)
            for ts, note in notes.items():
                dt = datetime.fromisoformat(ts)
                self.conversation_log.append(
                    f"[{dt.strftime('%Y-%m-%d %H:%M')}] {note['title']}: {note['content'][:200]}..."
                )
