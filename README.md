# 🥗 DeficitTracker - App de Control de Déficit Calórico y Comidas

Aplicación web desarrollada en **Django** para el registro diario de comidas, cálculo de macronutrientes y control estricto de déficit calórico para pérdida de grasa. Diseñada para desplegarse fácilmente en **Coolify** conectada a **PostgreSQL** y servida a través del dominio `dieta.dario10.pw` mediante **Cloudflare**.

---

## 🚀 Características Principales

- 📊 **Panel de Control Diario (Dashboard):**
  - Balance calórico diario en tiempo real (calorías consumidas vs objetivo de déficit).
  - Cálculo automático del déficit real frente a tus calorías estimadas de mantenimiento (TDEE).
  - Seguimiento de macronutrientes: Proteínas, Carbohidratos y Grasas con barras de progreso relativas.
  - Navegador de fechas para registrar o auditar días anteriores y posteriores.
- 🍽️ **Registro de Comidas por Tiempo del Día:**
  - Desayuno, Almuerzo, Merienda, Cena, Snacks/Colaciones.
  - Modal interactivo con buscador instantáneo y recálculo en vivo de macros al ingresar los gramos.
  - Subtotales automáticos de calorías y macros por comida.
- 🥑 **Biblioteca de Alimentos:**
  - Más de 25 alimentos saludables iniciales precargados (pechuga de pollo, huevos, avena, atún, arroz, palta, frutos secos, etc.).
  - Posibilidad de crear y editar alimentos personalizados por porción.
- ⚖️ **Seguimiento de Peso y Evolución:**
  - Registro de pesaje diario con notas (ayunas, post-entreno, etc.).
  - Gráfico interactivo de tendencia de peso con Chart.js.
- 🎯 **Configuración de Metas Personalizadas:**
  - Meta de calorías en déficit, calorías de mantenimiento, macros diarios y peso objetivo.
- 🔒 **Autenticación Completa:** Registro de usuario, inicio de sesión y perfiles independientes.
- ⚡ **Producción Lista:** Gunicorn + WhiteNoise para servir archivos estáticos con compresión.

---

## 🗄️ Conexión con PostgreSQL en Coolify

En tu servidor Coolify (`192.168.1.25:8000`), la base de datos PostgreSQL ya se encuentra en ejecución:

| Parámetro | Valor en Coolify |
| :--- | :--- |
| **Host Interno (Docker)** | `u0400w8wco8okgs08sco8g8g` (o nombre del contenedor postgres en Coolify) |
| **Host Externo / LAN** | `192.168.1.25` |
| **Puerto** | `5432` |
| **Usuario** | `postgres` |
| **Base de datos** | `postgres` |
| **Password** | `6Ic19aZIVRd8nSTyPtsRx7L1tbjzyp08jTNRQFM1fJ1o3lfFIngjrZemRfdPzSHX` |

### URLs de Conexión:

- **Red interna de Coolify (cuando el contenedor de Django corre dentro de Coolify):**
  ```env
  DATABASE_URL=postgres://postgres:6Ic19aZIVRd8nSTyPtsRx7L1tbjzyp08jTNRQFM1fJ1o3lfFIngjrZemRfdPzSHX@u0400w8wco8okgs08sco8g8g:5432/postgres
  ```

- **Red local / Fuera de Docker (para correr Django en tu PC):**
  ```env
  DATABASE_URL=postgres://postgres:6Ic19aZIVRd8nSTyPtsRx7L1tbjzyp08jTNRQFM1fJ1o3lfFIngjrZemRfdPzSHX@192.168.1.25:5432/postgres
  ```

---

## 🛠️ Cómo Desplegar en Coolify desde GitHub

1. **Subir los cambios a GitHub:**
   ```bash
   git add .
   git commit -m "Inicializar proyecto Django DeficitTracker con Docker y PostgreSQL"
   git push origin main
   ```

2. **Crear la Aplicación en Coolify:**
   - Ingresa a tu panel de Coolify: `http://192.168.1.25:8000/`.
   - Ve a tu proyecto (por ejemplo `postgreeDB` o crea uno nuevo).
   - Haz clic en **+ New Resource** -> **Public Repository** (o Private si tienes la GitHub App vinculada).
   - Ingresa el repositorio: `https://github.com/orquera10/proyecto_dieta`.
   - Rama (Branch): `main`.
   - Build Pack: **Dockerfile** (Coolify detectará el `Dockerfile` en la raíz).

3. **Configurar las Variables de Entorno en Coolify:**
   En la pestaña **Environment Variables** de la aplicación en Coolify, agrega:

   ```env
   DEBUG=False
   SECRET_KEY=clave_segura_de_produccion_aleatoria
   ALLOWED_HOSTS=dieta.dario10.pw,192.168.1.25,localhost
   CSRF_TRUSTED_ORIGINS=https://dieta.dario10.pw,http://dieta.dario10.pw
   DATABASE_URL=postgres://postgres:6Ic19aZIVRd8nSTyPtsRx7L1tbjzyp08jTNRQFM1fJ1o3lfFIngjrZemRfdPzSHX@u0400w8wco8okgs08sco8g8g:5432/postgres
   TIME_ZONE=America/Argentina/Buenos_Aires
   ```

4. **Configurar el Dominio en Coolify:**
   - En el campo **Domains (FQDN)** de la aplicación en Coolify, escribe:
     `https://dieta.dario10.pw`
   - Puerto de la aplicación: `8000`.

5. **Haz clic en Deploy:**
   Coolify construirá la imagen Docker, ejecutará las migraciones automáticamente con `entrypoint.sh` y precargará los alimentos iniciales.

---

## 🌐 Configuración con Cloudflare (`dieta.dario10.pw`)

1. En el panel de control de tu cuenta de **Cloudflare**:
   - Selecciona tu zona `dario10.pw`.
   - Ve a **DNS** -> **Records**.
   - Añade un registro tipo **A**:
     - **Name:** `dieta`
     - **IPv4 Address:** Tu IP pública de internet donde apunta tu router / servidor Coolify (con el puerto 80/443 redirigido a la IP del servidor `192.168.1.25`, o mediante un **Cloudflare Tunnel**).
     - **Proxy status:** Proxied (nube naranja activada).
   - *(Alternativa recomendada)*: Si usas **Cloudflare Tunnels** (`cloudflared`), crea un túnel apuntando el hostname `dieta.dario10.pw` a `http://192.168.1.25:8000` (o al puerto de Traefik de Coolify).

2. En **SSL/TLS**:
   - Modo de encriptación: **Full** o **Full (Strict)**.

3. Gracias a las directivas configuradas en `settings.py`:
   - `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`
   - `USE_X_FORWARDED_HOST = True`
   - `CSRF_TRUSTED_ORIGINS = ['https://dieta.dario10.pw', ...]`
   Las peticiones HTTPS proxificadas por Cloudflare funcionarán sin bucles de redirección ni bloqueos por token CSRF.

---

## 💻 Desarrollo Local

Para correr la aplicación localmente en tu máquina:

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Aplicar migraciones a la BD PostgreSQL
python manage.py migrate

# 3. Precargar alimentos si aún no están
python manage.py seed_foods

# 4. Crear superusuario administrador
python manage.py createsuperuser

# 5. Iniciar servidor de pruebas
python manage.py runserver 0.0.0.0:8000
```
Accede desde tu navegador en `http://localhost:8000` o `http://192.168.1.25:8040`.

---

## 📱 App Móvil para Android & PWA

La aplicación cuenta con dos métodos de uso en dispositivos móviles Android:

### 1. App Nativa APK compilada con GitHub Actions
El repositorio incluye un proyecto nativo Android (`android/`) y un flujo de CI/CD en `.github/workflows/build-android.yml`:
- **Compilación automática**: Cada vez que subas cambios a `main`, GitHub Actions compila automáticamente el archivo APK (`DeficitTracker-v1.0.0.apk`).
- **Cómo descargar el APK**:
  1. Entra a tu repositorio en GitHub: `https://github.com/orquera10/proyecto_dieta/actions`.
  2. Haz clic en el workflow más reciente **"Build Android APK"**.
  3. En la sección **Artifacts**, descarga el archivo **`DeficitTracker-Android-APK`**.
  4. Pásalo a tu celular o descárgalo directamente desde el navegador de tu móvil e instálalo.

### 2. PWA (Instalación instantánea desde Chrome / Navegador)
- Al abrir `https://dieta.dario10.pw` o `http://192.168.1.25:8040` desde Chrome en tu Android:
  - Aparecerá el banner nativo: **"Instalar App en Android"**.
  - O en el menú de 3 puntos de Chrome: **"Instalar aplicación"** / **"Agregar a la pantalla principal"**.
- Se comportará al 100% como una app nativa, con icono en tu pantalla de inicio, modo pantalla completa sin barra de navegación del navegador, respuesta háptica táctil y funcionamiento offline con Service Worker.

