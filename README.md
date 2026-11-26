# MacroCompass (Edición Growth & Tech)

Brújula macroeconómica local + sistema de alertas automáticas calibrado para carteras con alta exposición a tecnología, semiconductores y *growth* de beta alta. Su objetivo es evitar comprar en euforia y vender en pánico, señalando con reglas objetivas y causales zonas de toma de beneficios (`> 80`) y zonas de compra escalonada (`< 20`).

---

## Arquitectura

- **Backend (`/backend`)**: Python 3.12+, FastAPI, `yfinance`, `fredapi` (con fallback automático al CSV público de FRED `fredgraph.csv`), `pandas`, `numpy` y caché local en **SQLite**.
- **Frontend (`/frontend`)**: Next.js (App Router), TypeScript, Tailwind CSS y Recharts con estética editorial clara (bandas horizontales roja `> 80` y verde `< 20`, KPIs grandes en negrita y notas interpretativas directas).
- **Configuración (`/config/weights.yaml`)**: Pesos de los 7 módulos, retardos de publicación causales, umbrales y textos del Playbook.
- **Alertas (`/backend/app/alerts.py`)**: Script diario programable al cierre de NY con envío por Telegram Bot y correo SMTP opcional, disparando únicamente ante cambios de régimen o activación de la *Alerta Temprana Tech*.

---

## Los 7 Módulos (0 = Capitulación / Compra · 100 = Euforia / Toma de beneficios)

1. **Liquidez Neta y Condiciones Financieras (20%)**: `WALCL − WTREGEN − RRPONTSYD` (en miles de millones USD), tasa de cambio a 3M y Chicago Fed `NFCI`.
2. **Tipos Reales y Ciclo Económico (15%)**: `DFII10` (nivel y variación en pb a 1M/3M), `T10Y2Y` y `SAHMREALTIME` con etiqueta de ciclo (*Expansión*, *Presión de Tipos*, *Alerta Recesión*).
3. **Sobreextensión Tech, Semis y Factor Growth (15%)**: Distancia `%` de `QQQ` y `SMH` a su SMA 200 y ratio `IWF / IWD` escalado 0–100 en su rango móvil de 2 años.
4. **Amplitud de Mercado — *"How Many Stocks Take Part"* (15%)**: `RSP / SPY` y `QQQE / QQQ` en base 100 con SMA 200 + `%` de los 11 ETFs sectoriales sobre su SMA 200 y detección de divergencia bajista.
5. **Volatilidad Nasdaq y Estructura Temporal (15%)**: `^VXN` y estructura `^VIX / ^VIX3M` (complacencia vs. *backwardation*).
6. **Precio del Riesgo — *"The Price of Risk"* (10%)**: `BAMLH0A0HYM2` (US HY OAS) y `BAMLC0A4CBBB` (US BBB OAS) en pb con cambios 1M/3M, percentil histórico, sparkline 5 años y alerta prioritaria de compra (`HY > 500 bp` o `BBB > 130 bp`).
7. **Cíclicos vs. Defensivos — *"Cyclicals Against Defensives"* (10%)**: Cesta equiponderada cíclicos (`XLY, XLI, XLF, XLK, XLB`) frente a defensivos (`XLP, XLU, XLV`) escalada 0–100 en su rango de 2 años con media de 5 días + percentil 2Y de `XLK / XLP`.

### Override Táctico: ⚠️ Riesgo de Techo Tech
Se activa independientemente del score global cuando coinciden al menos **3 de 4** condiciones:
1. `QQQ > +15%` o `SMH > +22%` sobre SMA 200.
2. `^VXN < 17.5`.
3. Liquidez neta cayendo en 3M (`< 0%`) o `DFII10` subiendo `> +30 pb` en 1–3M.
4. Divergencia negativa en `QQQE / QQQ` o `IWF / IWD > 85`.

---

## Puesta en Marcha Rápida

### 1. Variables de entorno (opcional)
```bash
cp .env.example .env
```
> La aplicación funciona de inmediato sin `FRED_API_KEY` gracias al fallback automático a los CSV públicos de FRED. Añadir una clave gratuita de FRED amplía el historial de spreads de crédito ICE BofA (`BAMLH0A0HYM2` y `BAMLC0A4CBBB`) de ~3 años a >15 años.

### 2. Backend (FastAPI)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Abre `http://localhost:3000`.

### 4. Tests automatizados (`pytest`)
```bash
cd backend
source .venv/bin/activate
pytest -v
```

### 5. Alertas diarias al cierre de NY (`alerts.py`)
```bash
cd backend
source .venv/bin/activate
python -m app.alerts --dry-run   # Previsualización sin enviar ni alterar estado
python -m app.alerts             # Envía solo si cambia el régimen o se activa Alerta Tech
```

Ejemplo de `cron` (Lunes–Viernes a las 22:15 hora Madrid, tras el cierre de Wall Street):
```cron
15 22 * * 1-5 cd /ruta/a/macrocompass/backend && .venv/bin/python -m app.alerts >> /tmp/macrocompass_alerts.log 2>&1
```
