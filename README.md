# Chat multiproveedor con Skills

Chat de terminal para Anthropic y OpenAI, con historial de conversación y **skills** locales que se usan como instrucciones de sistema. También permite consultas puntuales con una skill.

---

## 📋 Requisitos y Configuración

1. **Activar el entorno virtual:**
   ```bash
   source .venv/bin/activate
   ```

   Si el entorno no tiene el ejecutable `python` porque fue creado con una versión de Python que ya no está instalada, consérvalo como respaldo y crea uno nuevo antes de instalar dependencias:
   ```bash
   mv .venv .venv-respaldo
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Variables de entorno:**
   Copia [`.env.example`](.env.example) a `.env` y configura al menos un proveedor:
   ```env
   CHAT_PROVIDER=anthropic
   ANTHROPIC_API_KEY=tu-api-key
   ANTHROPIC_BASE_URL=http://localhost:20128
   ```

   Para OpenAI usa `OPENAI_API_KEY` y, si corresponde, `OPENAI_BASE_URL`. Una URL base de OpenAI puede tener `/v1` o no; el programa la normaliza. `ANTHROPIC_BASE_URL` puede apuntar a un gateway compatible con Anthropic. Define `ANTHROPIC_MODEL` u `OPENAI_MODEL` si quieres fijar un modelo por proveedor; `CHAT_MODEL` solo determina el modelo de inicio del chat.

3. **Dependencias:**
   Registradas en [requirements.txt](requirements.txt). Si necesitas reinstalarlas en un entorno limpio:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Uso Rápido

### 1. Chat interactivo

```bash
python main.py
```

Durante el chat puedes usar `/help`, `/provider openai`, `/model <modelo>`, `/skill <nombre>`, `/new` y `/exit`. El historial se conserva durante la sesión y mantiene hasta 20 mensajes recientes como contexto.

Para iniciar con otro proveedor, modelo o skill:

```bash
python main.py --provider openai --model gpt-4o-mini --skill python-helper
```

### 2. Listar Skills Disponibles
```bash
python run_skill.py --list
```

### 3. Ejecutar una Consulta con una Skill
```bash
python run_skill.py --skill python-helper --prompt "Cómo hacer un generador en Python"
```
También puede elegir proveedor y modelo:

```bash
python run_skill.py --provider openai --model gpt-4o-mini --max-tokens 800 --skill python-helper --prompt "Cómo hacer un generador en Python"
```
O de forma interactiva (te mostrará el menú para elegir la skill y escribir tu pregunta):
```bash
python run_skill.py
```

---

## 🛠️ Cómo Crear Nuevas Skills

Puedes crear nuevas skills de dos formas:

### Opción A: Modo Interactivo
```bash
python create_skill.py
```
Te solicitará paso a paso:
* Nombre (kebab-case, ej: `api-designer`)
* Descripción breve
* Objetivo principal
* Lista de reglas numeradas

### Opción B: Mediante Línea de Comandos
```bash
python create_skill.py \
  --name "docker-expert" \
  --desc "Especialista en contenedores Docker y Docker Compose" \
  --objective "Ayudar a crear Dockerfiles y orquestación multi-contenedor" \
  --rule "Usa siempre imágenes base oficiales y ligeras (alpine/slim)" \
  --rule "Aplica multi-stage builds para optimizar el tamaño final" \
  --rule "Muestra el Dockerfile o docker-compose.yml completo al inicio"
```

### Opción C: Creación Manual
Crea una carpeta en `skills/<nombre-de-tu-skill>/` con un archivo `SKILL.md`:
```markdown
---
name: mi-skill
description: Breve descripción de qué hace y cuándo usarla
---

# Mi Skill

## Objetivo
Objetivo principal de la skill.

## Instrucciones
1. Regla o directriz 1.
2. Regla o directriz 2.
```

Los nombres de skills usan `kebab-case` y no se sobrescriben por accidente: elige un nombre distinto si ya existe una carpeta con esa skill.

---

## 🧱 Arquitectura

El código de aplicación está organizado con **Clean Architecture**. Las dependencias apuntan hacia el núcleo: dominio y casos de uso no dependen de SDKs, terminal ni sistema de archivos. `presentation/composition.py` conecta los puertos con sus adaptadores concretos.

```text
chat_app/
├── domain/
│   ├── models.py                 # Tipos del dominio y configuración común
│   └── ports.py                  # Contrato del proveedor y tipos de conexión
├── application/
│   ├── chat_session.py           # Caso de uso del chat e historial
│   ├── prompt_design.py          # Diseño adaptativo del prompt de sistema
│   └── skill_query.py            # Caso de uso de consulta puntual
├── infrastructure/
│   ├── config.py                 # Variables de entorno y configuración
│   ├── providers.py              # Adaptadores Anthropic y OpenAI
│   └── skill_manager.py         # Lectura y creación de skills en disco
└── presentation/
      ├── chat_cli.py               # Interfaz interactiva del chat
      ├── skill_cli.py              # Interfaz de consulta puntual
      ├── create_skill_cli.py       # Interfaz para crear skills
      ├── setup_skill_cli.py        # Inspección de skills instaladas
      └── composition.py            # Ensamblado de dependencias

main.py, run_skill.py, create_skill.py y setup_skill.py son los puntos de entrada existentes. Los módulos de raíz `chat.py`, `config.py`, `providers.py` y `skill_manager.py` se conservan como fachadas para no romper imports previos.

## 🧠 Prompt Design adaptativo (PD)

`AdaptivePromptDesigner` genera las instrucciones de sistema según el contexto de ejecución:

* **Modo general:** orienta al modelo para identificar la intención y responder con una profundidad proporcional, sin forzar una especialidad.
* **Modo especializado:** combina esas pautas con las instrucciones de la skill activa.
* En ambos modos solicita respetar el formato indicado, distinguir preguntas directas de tareas de análisis o código, y pedir aclaraciones cuando falte información imprescindible.

El modo especializado se activa con `--skill <nombre>` al iniciar el chat, con `/skill <nombre>` durante la sesión o mediante `run_skill.py`. No se añade una llamada extra al modelo para clasificar la petición; el proveedor recibe un único prompt de sistema compuesto por la aplicación.

## 📂 Recursos

* [main.py](main.py) — Punto de entrada del chat interactivo.
* [skills/](skills/) — Skills locales cargadas por el adaptador de infraestructura:
   * [skills/python-helper/SKILL.md](skills/python-helper/SKILL.md) — Asistente de Python para explicaciones claras y código limpio.
   * [skills/sql-expert/SKILL.md](skills/sql-expert/SKILL.md) — Especialista en SQL, consultas optimizadas e índices.
