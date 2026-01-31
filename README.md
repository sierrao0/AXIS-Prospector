# 🕵️‍♂️ BusinesScraper: The Hunter Module

**BusinesScraper** es el núcleo de prospección inteligente de **AXIS**. No es un simple scraper; es un motor de inferencia asíncrono diseñado para descubrir, calificar y auditar prospectos B2B en tiempo real.

### 🚀 Overview

Este módulo automatiza el ciclo de vida inicial del lead: desde la extracción geográfica en Google Maps hasta la auditoría técnica de su presencia web mediante IA, filtrando el ruido para encontrar el 20% de clientes que generan el 80% del valor.

### 🧠 Core Features

* **Deep Extraction:** Ingesta masiva de datos desde Google Maps API/Apify con manejo de proxies residenciales.
* **Automated Audit:** Análisis de sitios web mediante **Playwright** para detectar tecnologías obsoletas o falta de presencia digital.
* **AI Scoring:** Calificación de leads basada en modelos de lenguaje (Gemini 1.5 Flash) para identificar "puntos de dolor" específicos.
* **Async Pipeline:** Arquitectura basada en **FastAPI** y `BackgroundTasks` para procesamiento no bloqueante.
* **Real-time Sync:** Persistencia y streaming de datos hacia **Supabase** para actualización inmediata del frontend.

### 🛠 Tech Stack

* **Language:** Python 3.12+
* **Framework:** FastAPI
* **Automation:** Playwright, Apify
* **AI/LLM:** Gemini Pro / Flash (Vertex AI)
* **Database:** Supabase (PostgreSQL)
* **Reliability:** Pydantic V2, Tenacity (Retries), Custom Exception Hierarchy

### 📂 Architecture

```text
BusinesScraper/
├── api/             # FastAPI Endpoints & Routes
├── services/        # Scraper, Analyzer & Database logic
├── schemas/         # Pydantic data validation
├── core/            # Configuration & AXIS-specific errors
└── agents/          # AI logic and Prompt engineering

```

---

> **Status:** Phase 1 of the AXIS Megaprocess.
> *“Transforming raw data into actionable business intelligence.”*