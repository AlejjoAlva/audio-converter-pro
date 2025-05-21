# Audio Converter Pro

![Audio Converter Pro Logo](https://via.placeholder.com/800x200/673AB7/FFFFFF?text=Audio+Converter+Pro)

## Descripción

Audio Converter Pro es una aplicación moderna de escritorio para convertir archivos de audio a formato MP4 con una interfaz minimalista y elegante. Diseñada para ser simple pero potente, esta aplicación permite a los usuarios convertir diferentes formatos de audio como MP3, M4A, WAV, FLAC, OGG, AAC y WMA a archivos MP4 manteniendo la calidad original.

## Características principales

- ✨ Interfaz gráfica moderna y minimalista
- 🎵 Soporte para múltiples formatos de audio (M4A, MP3, WAV, FLAC, OGG, AAC, WMA)
- 🎬 Conversión rápida a formato MP4 
- 📊 Historial de conversiones
- ⚙️ Configuración personalizable
- 🚀 Motor de conversión optimizado con FFmpeg

## Requisitos previos

- Python 3.7 o superior
- PyQt5
- FFmpeg instalado en el sistema
- Mutagen

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/AlejjoAlva/audio-converter-pro.git
cd audio-converter-pro
```

### 2. Crear un entorno virtual (opcional pero recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/MacOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install PyQt5 mutagen
```

### 4. Instalar FFmpeg

#### Windows
1. Descarga FFmpeg desde [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extrae el archivo y coloca el contenido de la carpeta 'bin' en alguna ubicación
3. Añade esa ubicación a la variable de entorno PATH

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

#### MacOS
```bash
# Con Homebrew
brew install ffmpeg
```

### 5. Ejecutar la aplicación

```bash
python audio_converter_pro.py
```

## Cómo usar

1. **Seleccionar formato**: Elige el formato de audio de entrada desde el menú desplegable
2. **Examinar**: Haz clic en el botón "Examinar" para seleccionar el archivo de audio
3. **Convertir**: Presiona el botón "Convertir" para iniciar la conversión
4. **Monitorear progreso**: Observa la barra de progreso y los registros de actividad

## Secciones de la aplicación

### Panel Principal
La página principal donde puedes seleccionar archivos y realizar conversiones.

### Configuración
Personaliza la carpeta de salida y los parámetros de conversión como el preset de velocidad y la aceleración por hardware.

### Historial
Visualiza y gestiona un registro de tus conversiones anteriores con detalles como fecha, archivo original y resultado.

### Acerca de
Información sobre la aplicación, detalles técnicos y licencia.

## Captura de pantalla

![Interfaz de Audio Converter Pro](https://via.placeholder.com/800x500/f5f5f5/333333?text=Audio+Converter+Pro+Screenshot)

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, lee las guías de contribución antes de enviar un pull request.

---

Desarrollado con ❤️ usando Python y PyQt5.