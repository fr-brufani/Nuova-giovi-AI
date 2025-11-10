# 📚 Documentazione API giovi_ai

**Ultimo aggiornamento:** 15 Gennaio 2025

Questa cartella contiene tutta la documentazione tecnica e di progetto per giovi_ai.

---

## 📋 **INDICE DOCUMENTAZIONE**

### **🏨 Integrazioni PMS**

#### **[README_SMOOBU_INTEGRATION.md](./README_SMOOBU_INTEGRATION.md)**
- **Stato:** ✅ **OPERATIVA** (Settembre 2024)
- **Tipo:** Webhook real-time
- **Contenuto:** Documentazione completa funzionamento integrazione Smoobu
- **Include:** Configurazione, webhook, mapping dati, troubleshooting

#### **[README_SCIDOO_INTEGRATION_PLAN.md](./README_SCIDOO_INTEGRATION_PLAN.md)**  
- **Stato:** ✅ **COMPLETATA** (15 Gennaio 2025)
- **Tipo:** Polling automatico ogni 10 minuti
- **Contenuto:** Piano implementazione e stato finale integrazione Scidoo
- **Include:** Architettura, polling system, endpoint, test guide

#### **[SCIDOO_API_DOC.md](./SCIDOO_API_DOC.md)**
- **Contenuto:** Documentazione completa API Scidoo (330 linee)
- **Include:** Endpoint, autenticazione, formati dati, esempi

### **📊 Stato Progetto**

#### **[PROJECT_STATUS_2025-01-15.md](./PROJECT_STATUS_2025-01-15.md)**
- **Data:** 15 Gennaio 2025
- **Contenuto:** Stato completo progetto giovi_ai
- **Include:** 
  - Panoramica architettura completa
  - Stato tutti i componenti (frontend, backend, database)
  - Dettagli tecnici implementazione PMS
  - Metriche, monitoring, logging
  - Roadmap futuro
  - Punti di attenzione e troubleshooting

### **🏗️ Analisi Architetturale**

#### **[TECHNICAL_ARCHITECTURE_ANALYSIS.md](./TECHNICAL_ARCHITECTURE_ANALYSIS.md)**  
- **Stato:** 📊 **ANALISI COMPLETA** (15 Gennaio 2025)
- **Tipo:** Valutazione architetturale strategica per senior developer
- **Contenuto:** Analisi completa architettura attuale + proposte evolutive/rivoluzionarie
- **Include:** Stack tecnologico, criticità, roadmap, decisioni strategiche
- **🏆 VERDETTO FINALE:** **CrewAI è superiore a LangChain/AutoGen per giovi_ai**
- **📋 Include:** Confronto dettagliato, ROI analysis, strategia migrazione 3 fasi

### **🔗 File Correlati**

#### **[smoobu/](./smoobu/)**
- Cartella con file specifici test Smoobu (se presente)

---

## 🎯 **QUICK REFERENCE**

### **Integrazioni PMS Disponibili**
| PMS | Stato | Tipo | Documentazione |
|-----|-------|------|----------------|
| **Smoobu** | ✅ Operativa | Webhook real-time | README_SMOOBU_INTEGRATION.md |
| **Scidoo** | ✅ Operativa | Polling 10min | README_SCIDOO_INTEGRATION_PLAN.md |
| KrossBooking | 🟡 Pianificata | TBD | - |
| Booking.com | 🟡 Pianificata | API Partner | - |
| Airbnb | 🟡 Pianificata | API Ufficiale | - |

### **Servizi Backend**
| Servizio | URL | Stato | Funzione |
|----------|-----|-------|----------|
| **pms-sync-service** | `https://pms-sync-service-zuxzockfdq-ew.a.run.app` | ✅ Attivo | Core backend PMS + CSV |
| **gemini-proxy-service** | TBD | ✅ Attivo | Proxy Gemini AI |
| **workflow-service** | TBD | ✅ Attivo | Orchestrazione |
| **functions** | Firebase | ✅ Attivo | Cloud Functions |

### **Database Collections**
| Collection | Tipo | Contenuto |
|------------|------|-----------|
| `users` | Documents | Host e clienti con ruoli |
| `reservations` | Documents | Prenotazioni unificate tutti PMS |
| `properties` | Subcollection | Proprietà/alloggi per host |

---

## 🚀 **Come Iniziare**

### **Per Developer**
1. Leggi **PROJECT_STATUS_2025-01-15.md** per overview completa
2. Per Smoobu: **README_SMOOBU_INTEGRATION.md**
3. Per Scidoo: **README_SCIDOO_INTEGRATION_PLAN.md**

### **Per Testing**
1. **PROJECT_STATUS_2025-01-15.md** → Sezione "Testing & Deployment"
2. **README_SCIDOO_INTEGRATION_PLAN.md** → Sezione "Come Testare l'Integrazione"

### **Per Troubleshooting**  
1. **PROJECT_STATUS_2025-01-15.md** → Sezione "Punti di Attenzione"
2. **README_SMOOBU_INTEGRATION.md** → Sezione "Troubleshooting"

---

## 📞 **Supporto**

Per domande o aggiornamenti:
- Controlla sempre il file **PROJECT_STATUS_[DATA].md** più recente
- Logs disponibili in Cloud Run per debugging
- Firebase Console per stato database

---

*Documentazione mantenuta automaticamente dal team giovi_ai* 