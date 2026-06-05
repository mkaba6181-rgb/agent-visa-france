# 🇫🇷 Agent Consulaire IA — Visa Étudiant France

> Analyse automatique de dossier de visa étudiant long séjour (VLS-TS) pour la France.  
> Basé sur la **liste officielle des documents du consulat de France en Guinée — Mai 2026**.

---

## Ce que fait l'agent

Tu déposez vos documents (PDF, photos), l'agent les lit et vous donne en quelques secondes :

- ✅ Un **inventaire** de chaque document fourni
- 🔍 Une **analyse** document par document : conforme, insuffisant ou manquant
- 📊 Une **note sur 10** avec points forts et points faibles
- ⚖️ Une **décision** : VISA ACCORDÉ ou VISA REFUSÉ avec motif
- 💡 Des **recommandations** pour corriger le dossier si besoin

---

## Documents analysés — Liste officielle consulat 2026

| # | Catégorie | Ce qu'il faut |
|---|-----------|---------------|
| 1 | Formulaire France-Visas | Formulaire rempli en ligne sur france-visas.gouv.fr |
| 2 | Preuves d'identité | Photo fond blanc + passeport **+15 mois** de validité + extrait de naissance |
| 3 | Objet du séjour | Attestation d'admission à l'université (accord préalable d'inscription) |
| 4 | Ressources financières | **Au choix :** compte bloqué 7 380 € OU garant en France OU attestation de bourse |
| 5 | Hébergement | **Au choix :** attestation hébergement OU contrat de bail OU attestation de logement |
| 6 | Assurance voyage | Couvre le 1er mois suivant l'arrivée en France |
| 7 | Justificatif de transport | Réservation des billets d'avion |

---

## Utilisation — Interface web (recommandé)

Aucune installation. Ouvre le lien dans ton navigateur :

👉 **[Lancer l'agent en ligne](https://agent-visa-france.streamlit.app)**

1. Entre ta clé API Groq dans la barre latérale
2. Dépose tes documents (PDF et/ou images)
3. Clique sur **Analyser mon dossier**
4. Lis le rapport et pose tes questions complémentaires

---

## Installation locale (pour développeurs)

### Prérequis

- Python 3.10 ou supérieur
- Un compte gratuit sur [console.groq.com](https://console.groq.com) pour obtenir une clé API

### Étapes

**1. Cloner le projet**
```bash
git clone https://github.com/TON_USERNAME/agent-visa-france.git
cd agent-visa-france
```

**2. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**3. Définir la clé API Groq**

Sur Windows (PowerShell) :
```powershell
$env:GROQ_API_KEY = "gsk_..."
```

Sur Mac/Linux :
```bash
export GROQ_API_KEY="gsk_..."
```

**4. Lancer l'interface web**
```bash
streamlit run app.py
```
L'application s'ouvre automatiquement dans votre navigateur.

**5. (Optionnel) Lancer la version terminal**
```bash
python agent_consulaire.py
```

---

## Activer l'OCR (documents scannés)

Pour analyser des PDFs scannés ou des photos de documents, installez Tesseract :

**Windows :** Télécharger depuis [github.com/UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) et installer avec la langue française cochée.

**Ubuntu/Debian :**
```bash
sudo apt install tesseract-ocr tesseract-ocr-fra
```

**Mac :**
```bash
brew install tesseract tesseract-lang
```

---

## Déployer sur Streamlit Cloud (gratuit)

1. Fork ce repo sur GitHub
2. Va sur [share.streamlit.io](https://share.streamlit.io) et connecte-toi avec GitHub
3. Clique **New app** → sélectionne ce repo → fichier principal : `app.py`
4. Dans **Advanced settings → Secrets**, ajoute :
```toml
GROQ_API_KEY = "gsk_ta_cle_api"
```
5. Clique **Deploy** → ton app est en ligne en 2-3 minutes

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Interface web | [Streamlit](https://streamlit.io) |
| Modèle IA | LLaMA 3.3 70B via [Groq](https://groq.com) |
| Lecture PDF | pdfplumber |
| OCR | Tesseract + PyMuPDF |

---

## Avertissement

> Ceci est une **simulation pédagogique**. Les résultats sont fournis à titre informatif uniquement.  
> Pour la procédure officielle, consultez : [france-visas.gouv.fr](https://france-visas.gouv.fr)