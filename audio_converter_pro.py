import os
import sys
import subprocess
import re
import datetime
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QFileDialog, QProgressBar, QTextEdit, 
                           QLineEdit, QMessageBox, QGroupBox, QFormLayout, QComboBox,
                           QFrame, QSplitter, QTabWidget, QSizePolicy, QScrollArea,
                           QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSize, QPropertyAnimation, QEasingCurve, QDate
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QCursor

class ConversionThread(QThread):
    progress_update = pyqtSignal(int)
    log_update = pyqtSignal(str)
    conversion_finished = pyqtSignal(bool, str, str, str)  # success, message, input_file, output_file
    
    def __init__(self, input_file, output_file):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.is_cancelled = False
        # Valores predeterminados fijos
        self.preset = "ultrafast"
        self.use_hwaccel = True
        
    def run(self):
        try:
            # Obtener el número de núcleos del CPU
            cpu_count = os.cpu_count() or 4
            
            # Configuración básica de FFmpeg
            cmd = [
                'ffmpeg',
                '-y'  # Sobrescribir archivo de salida sin preguntar
            ]
            
            # Añadir aceleración por hardware (siempre activada)
            cmd.extend(['-hwaccel', 'auto'])
            
            # Configuración de entrada y filtros optimizados
            cmd.extend([
                '-i', self.input_file,
                '-f', 'lavfi',
                '-i', 'color=c=black:s=1280x720:r=30',
                '-shortest',
                '-c:a', 'copy',  # Copiar audio sin recodificar
                '-c:v', 'libx264',
                '-preset', 'ultrafast',  # Siempre usando preset ultrafast
                '-tune', 'fastdecode',  # Optimizar para decodificación rápida
                '-pix_fmt', 'yuv420p',
                '-threads', str(cpu_count),
                self.output_file
            ])
            
            self.log_update.emit(f"Iniciando conversión de {os.path.basename(self.input_file)}")
            self.log_update.emit(f"Usando preset: ultrafast con {cpu_count} threads")
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True,
                bufsize=1  # Line buffered para mejor respuesta
            )
            
            duration = self._get_duration(self.input_file)
            if not duration or duration <= 0:
                self.log_update.emit("Usando duración predeterminada: 100 segundos")
                duration = 100
            
            line_count = 0    
            for line in process.stderr:
                line_count += 1
                
                if self.is_cancelled:
                    process.terminate()
                    self.log_update.emit("Conversión cancelada")
                    self.conversion_finished.emit(False, "Conversión cancelada por el usuario", self.input_file, "")
                    return
                
                # Reducir la frecuencia de actualizaciones del log para mejor rendimiento
                if line_count % 30 == 0:
                    self.log_update.emit(line.strip())
                
                time_match = re.search(r'time=(\S+)', line)
                if time_match:
                    try:
                        time_str = time_match.group(1)
                        current_time = self._time_to_seconds(time_str)
                        progress = min(int(current_time / duration * 100), 100)
                        self.progress_update.emit(progress)
                    except Exception as e:
                        pass  # Ignorar errores de procesamiento de tiempo para no saturar el log
            
            process.wait()
            
            if process.returncode == 0:
                self.progress_update.emit(100)
                self.log_update.emit(f"Archivo guardado en: {self.output_file}")
                self.conversion_finished.emit(True, "Conversión exitosa", self.input_file, self.output_file)
            else:
                error_msg = f"Error en la conversión. Código: {process.returncode}"
                self.log_update.emit(error_msg)
                self.conversion_finished.emit(False, error_msg, self.input_file, "")
                
        except Exception as e:
            self.log_update.emit(f"Error crítico: {str(e)}")
            self.conversion_finished.emit(False, str(e), self.input_file, "")
    
    def cancel(self):
        self.is_cancelled = True
    
    def _get_duration(self, file_path):
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                  '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except:
            return None
    
    def _time_to_seconds(self, time_str):
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s.split('.')[0])
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s.split('.')[0])
            return float(time_str)
        except:
            return 0

class Card(QFrame):
    """Widget personalizado para crear tarjetas con estilo minimalista"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet("""
            #card {
                background-color: white;
                border-radius: 8px;
                border: none;
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            title_label.setStyleSheet("""
                #cardTitle {
                    color: #333;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.layout.addWidget(title_label)
            
    def addWidget(self, widget):
        self.layout.addWidget(widget)
        
    def addLayout(self, layout):
        self.layout.addLayout(layout)

class SidebarButton(QPushButton):
    """Botón personalizado para la barra lateral"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("sidebarButton")
        self.setStyleSheet("""
            #sidebarButton {
                background-color: transparent;
                color: #b3b3b3;
                border: none;
                text-align: left;
                padding: 10px 15px;
                font-size: 14px;
                border-radius: 0px;
            }
            #sidebarButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
            }
            #sidebarButton:checked {
                background-color: rgba(103, 58, 183, 0.3);
                color: white;
                border-left: 3px solid #673AB7;
            }
        """)
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(40)

class PrimaryButton(QPushButton):
    """Botón primario con estilo moderno"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setStyleSheet("""
            #primaryButton {
                background-color: #673AB7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            #primaryButton:hover {
                background-color: #7E57C2;
            }
            #primaryButton:pressed {
                background-color: #5E35B1;
            }
            #primaryButton:disabled {
                background-color: #D1C4E9;
                color: #BDBDBD;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(36)

class SecondaryButton(QPushButton):
    """Botón secundario con estilo moderno"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setStyleSheet("""
            #secondaryButton {
                background-color: white;
                color: #673AB7;
                border: 1px solid #673AB7;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            #secondaryButton:hover {
                background-color: #EDE7F6;
            }
            #secondaryButton:pressed {
                background-color: #D1C4E9;
            }
            #secondaryButton:disabled {
                border-color: #BDBDBD;
                color: #BDBDBD;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(36)

class DangerButton(QPushButton):
    """Botón de peligro con estilo moderno"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("dangerButton")
        self.setStyleSheet("""
            #dangerButton {
                background-color: white;
                color: #f44336;
                border: 1px solid #f44336;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            #dangerButton:hover {
                background-color: #ffebee;
            }
            #dangerButton:pressed {
                background-color: #ffcdd2;
            }
            #dangerButton:disabled {
                border-color: #BDBDBD;
                color: #BDBDBD;
            }
        """)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(36)

class ModernProgressBar(QProgressBar):
    """Barra de progreso con estilo moderno"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #E0E0E0;
                border-radius: 10px;
                text-align: center;
                color: #333;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #673AB7;
                border-radius: 10px;
            }
        """)
        self.setFixedHeight(20)
        self.setTextVisible(True)

class AudioConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Definir la ruta de salida como atributo de clase
        self.output_folder = os.path.join(os.path.expanduser("~"), "AudioConverterPro_Output")
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Historial de conversiones (lista de diccionarios con información)
        self.conversion_history = []
        self.load_history()  # Cargar historial desde archivo
        
        self.init_ui()
        self.conversion_thread = None
        self.setWindowTitle("Audio Converter Pro")
        
    def init_ui(self):
        # Configuración básica de la ventana
        self.setMinimumSize(1100, 700)
        
        # Aplicar estilos globales
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QLineEdit, QComboBox, QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                background: white;
                selection-background-color: #673AB7;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #BDBDBD;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #673AB7;
                color: white;
                font-weight: bold;
                padding: 5px;
                border: none;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal horizontal (sidebar + contenido principal)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ----- SIDEBAR IZQUIERDO -----
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("""
            #sidebar {
                background-color: #212121;
                min-width: 220px;
                max-width: 220px;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 30, 0, 30)
        sidebar_layout.setSpacing(5)
        
        # Título en el sidebar
        app_title = QLabel("Audio Converter")
        app_title.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding-left: 20px;
            padding-bottom: 20px;
        """)
        sidebar_layout.addWidget(app_title)
        
        # Botones del sidebar
        self.btn_dashboard = SidebarButton("Panel Principal")
        self.btn_dashboard.setChecked(True)
        self.btn_settings = SidebarButton("Configuración")
        self.btn_history = SidebarButton("Historial")
        self.btn_about = SidebarButton("Acerca de")
        
        # Conectar señales de botones
        self.btn_dashboard.clicked.connect(lambda: self.change_page(0))
        self.btn_settings.clicked.connect(lambda: self.change_page(1))
        self.btn_history.clicked.connect(lambda: self.change_page(2))
        self.btn_about.clicked.connect(lambda: self.change_page(3))
        
        sidebar_layout.addWidget(self.btn_dashboard)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addWidget(self.btn_history)
        sidebar_layout.addWidget(self.btn_about)
        
        # Espacio flexible
        sidebar_layout.addStretch()
        
        # Versión en el sidebar
        version_label = QLabel("v2.0 Pro")
        version_label.setStyleSheet("""
            color: #757575;
            font-size: 12px;
            padding-left: 20px;
        """)
        sidebar_layout.addWidget(version_label)
        
        # Añadir sidebar al layout principal
        main_layout.addWidget(sidebar)
        
        # ----- CONTENIDO PRINCIPAL -----
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        self.content_stack.setStyleSheet("""
            #contentStack {
                background-color: #f5f5f5;
            }
        """)
        
        # Añadir páginas al stack
        self.init_dashboard_page()     # Página 0: Panel Principal
        self.init_settings_page()      # Página 1: Configuración
        self.init_history_page()       # Página 2: Historial
        self.init_about_page()         # Página 3: Acerca de
        
        # Añadir stack al layout principal
        main_layout.addWidget(self.content_stack)
        
        # Mensaje inicial
        self.log.append("Bienvenido a Audio Converter Pro")
        self.log.append("Seleccione un archivo de audio para comenzar")
    
    # ----- PÁGINAS DEL CONTENIDO -----
    def init_dashboard_page(self):
        # Página principal de conversión
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)
        dashboard_layout.setContentsMargins(30, 30, 30, 30)
        dashboard_layout.setSpacing(20)
        
        # Encabezado
        header_layout = QHBoxLayout()
        page_title = QLabel("Conversor de Audio")
        page_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
        """)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        dashboard_layout.addLayout(header_layout)
        
        # Card de selección de archivo
        file_card = Card("Selección de Archivo")
        file_layout = QVBoxLayout()
        
        format_layout = QHBoxLayout()
        format_label = QLabel("Formato:")
        format_label.setStyleSheet("font-weight: bold; color: #555;")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["M4A", "MP3", "WAV", "FLAC", "OGG", "AAC", "WMA"])
        self.format_combo.setFixedWidth(150)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        file_layout.addLayout(format_layout)
        
        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setReadOnly(True)
        self.input_path.setPlaceholderText("Seleccione un archivo para convertir...")
        self.btn_browse = PrimaryButton("Examinar")
        self.btn_browse.setFixedWidth(120)
        self.btn_browse.clicked.connect(self.browse_file)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.btn_browse)
        file_layout.addLayout(input_layout)
        
        file_card.addLayout(file_layout)
        dashboard_layout.addWidget(file_card)
        
        # Card de detalles del archivo
        details_card = Card("Detalles del Archivo")
        details_layout = QHBoxLayout()
        
        # Columna izquierda (info)
        info_layout = QFormLayout()
        info_layout.setLabelAlignment(Qt.AlignRight)
        info_layout.setSpacing(10)
        self.file_name = QLabel("No seleccionado")
        self.file_size = QLabel("-")
        
        self.file_name.setStyleSheet("color: #555;")
        self.file_size.setStyleSheet("color: #555;")
        
        info_layout.addRow(QLabel("<b>Nombre:</b>"), self.file_name)
        info_layout.addRow(QLabel("<b>Tamaño:</b>"), self.file_size)
        details_layout.addLayout(info_layout)
        
        # Columna derecha (botones)
        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.btn_convert = PrimaryButton("Convertir")
        self.btn_convert.setFixedWidth(150)
        self.btn_convert.clicked.connect(self.start_conversion)
        
        self.btn_cancel = DangerButton("Cancelar")
        self.btn_cancel.setFixedWidth(150)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        
        self.btn_clear = SecondaryButton("Nueva Conversión")
        self.btn_clear.setFixedWidth(150)
        self.btn_clear.clicked.connect(self.reset_ui)
        
        buttons_layout.addWidget(self.btn_convert)
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_clear)
        
        details_layout.addStretch()
        details_layout.addLayout(buttons_layout)
        
        details_card.addLayout(details_layout)
        dashboard_layout.addWidget(details_card)
        
        # Card de progreso
        progress_card = Card("Progreso de Conversión")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = ModernProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        progress_card.addLayout(progress_layout)
        dashboard_layout.addWidget(progress_card)
        
        # Card de log
        log_card = Card("Registro de Actividad")
        log_layout = QVBoxLayout()
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("""
            border: 1px solid #E0E0E0;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
        """)
        self.log.setMinimumHeight(150)
        log_layout.addWidget(self.log)
        
        log_card.addLayout(log_layout)
        dashboard_layout.addWidget(log_card)
        
        # Agregar espacio al final
        dashboard_layout.addStretch()
        
        # Añadir la página al stack
        self.content_stack.addWidget(dashboard_page)
    
    def init_settings_page(self):
        # Página de configuración
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(30, 30, 30, 30)
        settings_layout.setSpacing(20)
        
        # Encabezado
        header_layout = QHBoxLayout()
        page_title = QLabel("Configuración")
        page_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
        """)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        settings_layout.addLayout(header_layout)
        
        # Card de configuración general
        general_card = Card("Configuración General")
        general_layout = QVBoxLayout()
        
        # Ruta de salida
        output_layout = QHBoxLayout()
        output_label = QLabel("Carpeta de salida:")
        output_label.setStyleSheet("font-weight: bold; color: #555;")
        
        self.output_path = QLineEdit(self.output_folder)
        self.output_path.setReadOnly(True)
        
        self.btn_output_browse = PrimaryButton("Cambiar")
        self.btn_output_browse.setFixedWidth(120)
        self.btn_output_browse.clicked.connect(self.change_output_folder)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.btn_output_browse)
        
        general_layout.addLayout(output_layout)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #E0E0E0;")
        general_layout.addWidget(separator)
        
        # Opciones de conversión
        options_form = QFormLayout()
        options_form.setLabelAlignment(Qt.AlignRight)
        options_form.setSpacing(15)
        
        # Preset de conversión
        preset_label = QLabel("Preset de conversión:")
        preset_label.setStyleSheet("font-weight: bold; color: #555;")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Ultrafast", "Fast", "Medium", "Slow"])
        self.preset_combo.setCurrentIndex(0)  # Ultrafast por defecto
        options_form.addRow(preset_label, self.preset_combo)
        
        # Aceleración por hardware
        hwaccel_label = QLabel("Aceleración por hardware:")
        hwaccel_label.setStyleSheet("font-weight: bold; color: #555;")
        self.hwaccel_combo = QComboBox()
        self.hwaccel_combo.addItems(["Activada", "Desactivada"])
        self.hwaccel_combo.setCurrentIndex(0)  # Activada por defecto
        options_form.addRow(hwaccel_label, self.hwaccel_combo)
        
        general_layout.addLayout(options_form)
        
        # Botón para guardar configuración
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.btn_save_settings = PrimaryButton("Guardar Configuración")
        self.btn_save_settings.clicked.connect(self.save_settings)
        save_layout.addWidget(self.btn_save_settings)
        
        general_layout.addLayout(save_layout)
        
        general_card.addLayout(general_layout)
        settings_layout.addWidget(general_card)
        
        # Añadir espacio al final
        settings_layout.addStretch()
        
        # Añadir la página al stack
        self.content_stack.addWidget(settings_page)
    
    def init_history_page(self):
        # Página de historial
        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_layout.setContentsMargins(30, 30, 30, 30)
        history_layout.setSpacing(20)
        
        # Encabezado
        header_layout = QHBoxLayout()
        page_title = QLabel("Historial de Conversiones")
        page_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
        """)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        history_layout.addLayout(header_layout)
        
        # Card de historial
        history_card = Card("Conversiones Recientes")
        history_card_layout = QVBoxLayout()
        
        # Tabla de historial
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Fecha", "Archivo Original", "Formato", "Resultado", "Acciones"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #F5F5F5;
            }
        """)
        
        # Actualizar tabla con datos del historial
        self.update_history_table()
        
        history_card_layout.addWidget(self.history_table)
        
        # Botones de acción
        history_buttons_layout = QHBoxLayout()
        history_buttons_layout.addStretch()
        
        self.btn_clear_history = DangerButton("Borrar Historial")
        self.btn_clear_history.clicked.connect(self.clear_history)
        
        self.btn_refresh_history = SecondaryButton("Actualizar")
        self.btn_refresh_history.clicked.connect(self.update_history_table)
        
        history_buttons_layout.addWidget(self.btn_refresh_history)
        history_buttons_layout.addWidget(self.btn_clear_history)
        
        history_card_layout.addLayout(history_buttons_layout)
        
        history_card.addLayout(history_card_layout)
        history_layout.addWidget(history_card)
        
        # Gráfico o estadísticas (Simulado)
        stats_card = Card("Estadísticas de Conversión")
        stats_layout = QVBoxLayout()
        
        stats_label = QLabel("Este mes has convertido 12 archivos con un tamaño total de 250 MB")
        stats_label.setStyleSheet("color: #555; font-size: 14px;")
        stats_label.setAlignment(Qt.AlignCenter)
        
        stats_layout.addWidget(stats_label)
        
        # Añadir un gráfico simulado (solo una imagen simulada)
        chart_placeholder = QLabel()
        chart_placeholder.setStyleSheet("""
            background-color: #EDE7F6;
            border-radius: 5px;
            min-height: 150px;
        """)
        stats_layout.addWidget(chart_placeholder)
        
        stats_card.addLayout(stats_layout)
        history_layout.addWidget(stats_card)
        
        # Añadir espacio al final
        history_layout.addStretch()
        
        # Añadir la página al stack
        self.content_stack.addWidget(history_page)
    
    def init_about_page(self):
        # Página de acerca de
        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)
        about_layout.setContentsMargins(30, 30, 30, 30)
        about_layout.setSpacing(20)
        
        # Encabezado
        header_layout = QHBoxLayout()
        page_title = QLabel("Acerca de")
        page_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
        """)
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        about_layout.addLayout(header_layout)
        
        # Card de información
        about_card = Card("Audio Converter Pro")
        about_layout_card = QVBoxLayout()
        
        # Logo (simulado)
        logo_label = QLabel("Audio Converter Pro")
        logo_label.setStyleSheet("""
            color: #673AB7;
            font-size: 28px;
            font-weight: bold;
            qproperty-alignment: AlignCenter;
            margin: 20px;
        """)
        
        # Descripción
        description = QLabel(
            "Audio Converter Pro es una aplicación profesional para convertir archivos de audio "
            "a formato MP4 con una interfaz minimalista y moderna. Utiliza FFmpeg para proporcionar "
            "conversiones rápidas y de alta calidad."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #555; font-size: 14px; qproperty-alignment: AlignCenter;")
        description.setContentsMargins(20, 10, 20, 10)
        
        # Versión
        version_label = QLabel("Versión 2.0 Pro")
        version_label.setStyleSheet("color: #673AB7; font-size: 16px; font-weight: bold; qproperty-alignment: AlignCenter;")
        
        # Desarrollador
        developer_label = QLabel("Desarrollado por: Audio Team")
        developer_label.setStyleSheet("color: #555; font-size: 14px; qproperty-alignment: AlignCenter;")
        
        # Año
        year_label = QLabel("© 2025 Todos los derechos reservados")
        year_label.setStyleSheet("color: #555; font-size: 14px; qproperty-alignment: AlignCenter;")
        
        about_layout_card.addWidget(logo_label)
        about_layout_card.addWidget(description)
        about_layout_card.addWidget(version_label)
        about_layout_card.addWidget(developer_label)
        about_layout_card.addWidget(year_label)
        
        about_card.addLayout(about_layout_card)
        about_layout.addWidget(about_card)
        
        # Card de información técnica
        tech_card = Card("Información Técnica")
        tech_layout = QVBoxLayout()
        
        tech_info = QLabel(
            "<b>Tecnologías utilizadas:</b><br>"
            "- Python 3.9+<br>"
            "- PyQt5 para la interfaz gráfica<br>"
            "- FFmpeg para la conversión de audio<br>"
            "- Mutagen para el manejo de metadatos<br><br>"
            
            "<b>Requisitos del sistema:</b><br>"
            "- Windows 10 o superior<br>"
            "- 4GB de RAM<br>"
            "- 500MB de espacio en disco<br>"
            "- FFmpeg instalado en el sistema"
        )
        tech_info.setStyleSheet("color: #555; font-size: 14px;")
        tech_info.setContentsMargins(20, 10, 20, 10)
        
        tech_layout.addWidget(tech_info)
        
        tech_card.addLayout(tech_layout)
        about_layout.addWidget(tech_card)
        
        # Card de licencia
        license_card = Card("Licencia")
        license_layout = QVBoxLayout()
        
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setHtml(
            "Este software se distribuye bajo la licencia MIT.<br><br>"
            
            "Copyright (c) 2025 Audio Team<br><br>"
            
            "Por la presente se concede permiso, libre de cargos, a cualquier persona que obtenga una copia "
            "de este software y de los archivos de documentación asociados (el \"Software\"), a utilizar "
            "el Software sin restricción, incluyendo sin limitación los derechos a usar, copiar, modificar, "
            "fusionar, publicar, distribuir, sublicenciar, y/o vender copias del Software, y a permitir a las "
            "personas a las que se les proporcione el Software a hacer lo mismo, sujeto a las siguientes condiciones:<br><br>"
            
            "El aviso de copyright anterior y este aviso de permiso se incluirán en todas las copias o partes "
            "sustanciales del Software.<br><br>"
            
            "EL SOFTWARE SE PROPORCIONA \"COMO ESTÁ\", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O IMPLÍCITA, "
            "INCLUYENDO PERO NO LIMITADO A GARANTÍAS DE COMERCIALIZACIÓN, IDONEIDAD PARA UN PROPÓSITO PARTICULAR "
            "Y NO INFRACCIÓN. EN NINGÚN CASO LOS AUTORES O TITULARES DEL COPYRIGHT SERÁN RESPONSABLES DE NINGUNA "
            "RECLAMACIÓN, DAÑOS U OTRAS RESPONSABILIDADES, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O CUALQUIER "
            "OTRO MOTIVO, DERIVADAS DE, FUERA DE O EN CONEXIÓN CON EL SOFTWARE O SU USO U OTRO TIPO DE ACCIONES "
            "EN EL SOFTWARE."
        )
        
        license_layout.addWidget(license_text)
        
        license_card.addLayout(license_layout)
        about_layout.addWidget(license_card)
        
        # Añadir la página al stack
        self.content_stack.addWidget(about_page)
    
    # ----- FUNCIONES DE NAVEGACIÓN -----
    def change_page(self, index):
        # Cambiar a la página seleccionada
        self.content_stack.setCurrentIndex(index)
        
        # Actualizar estado de los botones
        self.btn_dashboard.setChecked(index == 0)
        self.btn_settings.setChecked(index == 1)
        self.btn_history.setChecked(index == 2)
        self.btn_about.setChecked(index == 3)
        
        # Acciones específicas por página
        if index == 2:  # Historial
            self.update_history_table()
    
    # ----- FUNCIONES DE LA PÁGINA DE CONFIGURACIÓN -----
    def change_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Seleccionar carpeta de salida", 
            self.output_folder
        )
        
        if folder:
            self.output_folder = folder
            self.output_path.setText(folder)
    
    def save_settings(self):
        # Aquí puedes guardar la configuración en un archivo
        # Por ahora solo mostraremos un mensaje
        QMessageBox.information(
            self, 
            "Configuración guardada", 
            "La configuración ha sido guardada exitosamente."
        )
    
    # ----- FUNCIONES DE LA PÁGINA DE HISTORIAL -----
    def load_history(self):
        # Intentar cargar historial desde archivo
        history_file = os.path.join(self.output_folder, "conversion_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    self.conversion_history = json.load(f)
            except:
                self.conversion_history = []
    
    def save_history(self):
        # Guardar historial en archivo
        history_file = os.path.join(self.output_folder, "conversion_history.json")
        try:
            with open(history_file, 'w') as f:
                json.dump(self.conversion_history, f)
        except:
            pass
    
    def add_to_history(self, input_file, output_file, success):
        # Añadir nueva conversión al historial
        now = datetime.datetime.now()
        
        self.conversion_history.append({
            "date": now.strftime("%Y-%m-%d %H:%M"),
            "input_file": input_file,
            "output_file": output_file,
            "format": os.path.splitext(input_file)[1][1:].upper(),
            "success": success
        })
        
        # Guardar historial actualizado
        self.save_history()
    
    def update_history_table(self):
        # Limpiar tabla
        self.history_table.setRowCount(0)
        
        # Rellenar con datos del historial
        for i, item in enumerate(reversed(self.conversion_history)):
            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)
            
            # Fecha
            self.history_table.setItem(row_position, 0, QTableWidgetItem(item["date"]))
            
            # Archivo original
            original_file = os.path.basename(item["input_file"])
            self.history_table.setItem(row_position, 1, QTableWidgetItem(original_file))
            
            # Formato
            self.history_table.setItem(row_position, 2, QTableWidgetItem(item["format"]))
            
            # Resultado
            result_item = QTableWidgetItem("Éxito" if item["success"] else "Error")
            result_item.setForeground(QColor("#4CAF50" if item["success"] else "#F44336"))
            self.history_table.setItem(row_position, 3, result_item)
            
            # Botón de acción
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_view = QPushButton("Ver")
            btn_view.setStyleSheet("""
                QPushButton {
                    background-color: #673AB7;
                    color: white;
                    border-radius: 3px;
                    padding: 3px 8px;
                }
                QPushButton:hover {
                    background-color: #7E57C2;
                }
            """)
            
            def create_open_folder_function(file_path):
                return lambda: os.startfile(os.path.dirname(file_path)) if os.path.exists(os.path.dirname(file_path)) else None
            
            # Solo habilitar botón si la conversión fue exitosa
            if item["success"] and os.path.exists(os.path.dirname(item["output_file"])):
                btn_view.clicked.connect(create_open_folder_function(item["output_file"]))
            else:
                btn_view.setEnabled(False)
            
            action_layout.addWidget(btn_view)
            action_layout.setAlignment(Qt.AlignCenter)
            
            self.history_table.setCellWidget(row_position, 4, action_widget)
    
    def clear_history(self):
        # Pedir confirmación
        reply = QMessageBox.question(
            self, 
            "Confirmar borrado", 
            "¿Estás seguro de que deseas borrar todo el historial de conversiones?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.conversion_history = []
            self.update_history_table()
            self.save_history()
            QMessageBox.information(self, "Historial borrado", "El historial ha sido borrado exitosamente.")
    
    # ----- FUNCIONES DE CONVERSIÓN (PÁGINA PRINCIPAL) -----
    def browse_file(self):
        # Determinar filtros de archivos basados en el formato seleccionado
        selected_format = self.format_combo.currentText().lower()
        all_formats = "Archivos de Audio (*.m4a *.mp3 *.wav *.flac *.ogg *.aac *.wma)"
        specific_format = f"Archivos {selected_format.upper()} (*.{selected_format})"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar archivo de audio", 
            "", 
            f"{specific_format};;{all_formats};;Todos los archivos (*.*)"
        )
        
        if file_path:
            self.input_path.setText(file_path)
            self.load_file_info(file_path)
    
    def load_file_info(self, file_path):
        try:
            self.file_name.setText(os.path.basename(file_path))
            
            size = os.path.getsize(file_path)
            self.file_size.setText(f"{size/1024/1024:.2f} MB")
            
            # Mostrar mensaje en el log
            self.log.append(f"Archivo cargado: {os.path.basename(file_path)}")
            self.log.append(f"Ruta: {file_path}")
            self.log.append(f"Tamaño: {size/1024/1024:.2f} MB")
            
        except Exception as e:
            self.log.append(f"Error cargando metadatos: {str(e)}")
    
    def start_conversion(self):
        input_file = self.input_path.text()
        if not input_file:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de entrada")
            return
        
        output_name = os.path.splitext(os.path.basename(input_file))[0] + ".mp4"
        output_file = os.path.join(self.output_folder, output_name)
        
        self.conversion_thread = ConversionThread(input_file, output_file)
        self.conversion_thread.progress_update.connect(self.progress_bar.setValue)
        self.conversion_thread.log_update.connect(self.log.append)
        self.conversion_thread.conversion_finished.connect(self.conversion_done)
        
        self.btn_convert.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log.append("Iniciando proceso de conversión...")
        self.conversion_thread.start()
    
    def cancel_conversion(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self.log.append("Solicitando cancelación de la conversión...")
            self.btn_cancel.setEnabled(False)
    
    def conversion_done(self, success, message, input_file, output_file):
        self.btn_convert.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        # Añadir al historial
        self.add_to_history(input_file, output_file, success)
        
        if success:
            self.log.append("¡Conversión completada exitosamente!")
            QMessageBox.information(self, "Éxito", 
                                 "Conversión completada con éxito.\n\n"
                                 f"El archivo ha sido guardado en:\n{self.output_folder}")
        else:
            self.log.append(f"Error en la conversión: {message}")
            QMessageBox.critical(self, "Error", message)
    
    def reset_ui(self):
        # Limpiar campos
        self.input_path.clear()
        self.file_name.setText("No seleccionado")
        self.file_size.setText("-")
        self.progress_bar.setValue(0)
        
        # Limpiar log o agregar separador
        self.log.clear()
        self.log.append("Interfaz reiniciada - Lista para nueva conversión")
        
        # Habilitar/deshabilitar botones apropiados
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Establecer fuente predeterminada
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = AudioConverterApp()
    window.show()
    sys.exit(app.exec_())