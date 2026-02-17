# 📘 Guía de Git para el Sistema OSINT EMI

## ✅ Sistema de Control de Versiones Configurado

El archivo `.gitignore` ya está configurado para proteger:
- ❌ Credenciales (`.env`, cookies de sesión)
- ❌ Base de datos (`data/*.db`)
- ❌ Archivos de caché (`__pycache__/`, `.vite/`)
- ❌ Dependencias (`node_modules/`, `venv/`)
- ❌ Logs (`*.log`)

---

## 🚀 Comandos Básicos de Git

### **Iniciar Git (solo primera vez)**
```bash
cd ~/Desktop/SISTEMA_ANALÍTICA_EMI/osint_vicerrectorado
git init
git add .
git commit -m "Initial commit: Sistema OSINT EMI v1.0"
```

### **Guardar Cambios**
```bash
# Ver qué archivos cambiaron
git status

# Agregar archivos modificados
git add .

# Guardar con mensaje descriptivo
git commit -m "Descripción del cambio"
```

### **Ver Historial**
```bash
# Ver últimos commits
git log --oneline

# Ver cambios específicos
git diff
```

### **Conectar con GitHub/GitLab**
```bash
# Agregar repositorio remoto
git remote add origin https://github.com/TU_USUARIO/osint-emi.git

# Subir cambios
git push -u origin main

# Descargar cambios
git pull origin main
```

---

## ⚠️ Archivos que NO se suben al repositorio

Estos archivos están excluidos por `.gitignore`:

| Archivo/Carpeta | Razón |
|-----------------|-------|
| `.env` | Contiene credenciales sensibles |
| `data/*.db` | Base de datos con información privada |
| `*_cookies.json` | Sesiones de redes sociales |
| `venv/` | Entorno virtual (se recrea con requirements.txt) |
| `node_modules/` | Dependencias (se reinstalan con npm install) |
| `__pycache__/` | Archivos compilados de Python |
| `*.log` | Archivos de registro |

---

## 🔒 Configurar Credenciales para el Proyecto

### **1. Copiar archivos de ejemplo**
```bash
cp .env.example .env
cp config/tiktok_cookies.json.example config/tiktok_cookies.json
```

### **2. Editar con tus credenciales**
Edita `.env` y los archivos de cookies con tus datos reales.

---

## 📝 Buenas Prácticas

### **Mensajes de Commit Claros**
```bash
# ✅ Bueno
git commit -m "Agregar modal de scraping TikTok con SSE"
git commit -m "Corregir extracción de comentarios duplicados"

# ❌ Malo
git commit -m "fix"
git commit -m "cambios"
```

### **Commits Frecuentes**
- Haz commits pequeños y frecuentes
- Un commit = Una funcionalidad o corrección
- No acumules muchos cambios en un solo commit

### **Antes de hacer Push**
```bash
# Verificar que no subes archivos sensibles
git status

# Ver qué se va a subir
git diff --cached
```

---

## 🆘 Comandos de Emergencia

### **Deshacer cambios no guardados**
```bash
# Descartar cambios en un archivo
git checkout -- archivo.py

# Descartar todos los cambios
git reset --hard HEAD
```

### **Sacar archivo del staging**
```bash
git reset HEAD archivo.py
```

### **Cambiar mensaje del último commit**
```bash
git commit --amend -m "Nuevo mensaje"
```

---

## 📦 Clonar el Proyecto (Para otros desarrolladores)

```bash
# 1. Clonar repositorio
git clone https://github.com/TU_USUARIO/osint-emi.git
cd osint-emi

# 2. Configurar archivos de entorno
cp .env.example .env
cp config/tiktok_cookies.json.example config/tiktok_cookies.json

# 3. Instalar dependencias Python
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
pip install -r requirements.txt

# 4. Instalar dependencias Frontend
cd frontend
npm install
cd ..

# 5. Iniciar sistema
./iniciar_sistema.sh
```

---

## 🌿 Ramas (Branches)

Para trabajar en nuevas funcionalidades sin afectar el código principal:

```bash
# Crear y cambiar a nueva rama
git checkout -b feature/nueva-funcionalidad

# Trabajar normalmente...
git add .
git commit -m "Implementar nueva funcionalidad"

# Volver a rama principal
git checkout main

# Fusionar cambios
git merge feature/nueva-funcionalidad
```

---

## 📚 Recursos Adicionales

- [Git Cheatsheet](https://education.github.com/git-cheat-sheet-education.pdf)
- [GitHub Guides](https://guides.github.com/)
- [Git Visualizer](https://git-school.github.io/visualizing-git/)

---

**Último Actualizado:** Febrero 2026  
**Proyecto:** Sistema de Analítica OSINT - EMI Bolivia
